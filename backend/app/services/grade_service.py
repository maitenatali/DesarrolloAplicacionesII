"""Grades (design §10.7)."""

from __future__ import annotations

from decimal import Decimal

from flask import current_app
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.constants import EVENT_TYPES, ExamPhase, ExamStatus
from app.errors import BadRequest, Conflict, ValidationFailed
from app.extensions import db
from app.integrations.base import roster_of
from app.models import Calificacion, Examen
from app.schemas.grades import (
    GradeEntryOut,
    GradeMatrix,
    GradesResponse,
    GradesSummary,
    GradesUpsertRequest,
    GradesUpsertResponse,
    MatrixCell,
    MatrixExam,
    MatrixRow,
    SavedGradeEntry,
)
from app.security.course_access import authorize_course
from app.security.principal import Principal
from app.services import event_service, locks, rules
from app.services.course_service import load_roster
from app.services.exam_service import load_exam
from app.time import now_local

_Q = Decimal("0.01")


def _q(v: Decimal | None) -> Decimal | None:
    return None if v is None else v.quantize(_Q)


def get_exam_grades(principal: Principal, course_id: int, exam_id: int) -> GradesResponse:
    access = authorize_course(principal, course_id)
    load_exam(course_id, exam_id)
    passing = current_app.extensions["settings"].passing_grade
    roster = load_roster(access.detail)
    rows = {
        r.alumno_id: r
        for r in db.session.scalars(select(Calificacion).where(Calificacion.examen_id == exam_id))
    }
    entries, graded, absent = [], [], 0
    for e in roster.entries:
        r = rows.get(e.student_id)
        entries.append(
            GradeEntryOut(
                student_id=e.student_id,
                student_name=e.name,
                file_number=e.file_number,
                grade=r.nota if r else None,
                absent=bool(r and r.ausente),
                graded_at=r.cargada_en if r else None,
                graded_by=r.cargada_por if r else None,
            )
        )
        if r is not None:
            if r.nota is not None:
                graded.append(r.nota)
            elif r.ausente:
                absent += 1
    enrolled = len(roster.entries)
    summary = GradesSummary(
        enrolled=enrolled,
        graded=len(graded),
        absent=absent,
        pending=max(enrolled - len(graded) - absent, 0),
        average=rules.mean(graded, 2),
        passed=sum(1 for g in graded if g >= passing),
        failed=sum(1 for g in graded if g < passing),
    )
    return GradesResponse(exam_id=exam_id, entries=entries, summary=summary)


def upsert_grades(
    principal: Principal, course_id: int, exam_id: int, body: GradesUpsertRequest
) -> GradesUpsertResponse:
    cfg = current_app.extensions["settings"]
    access = authorize_course(principal, course_id, write=True)
    exam = load_exam(course_id, exam_id)
    if exam.estado == ExamStatus.CANCELADO:
        raise Conflict("El examen está cancelado.", code="EXAM_CANCELLED")
    if locks.exam_has_valid_acta(exam_id):
        raise Conflict("Hay un acta vigente que cubre este examen.", code="EXAM_LOCKED_BY_ACTA")

    seen: set[str] = set()
    for i, ent in enumerate(body.entries):
        if ent.grade is not None and ent.absent:
            raise BadRequest(
                "No se puede cargar nota a un alumno ausente.",
                code="GRADE_WITH_ABSENT",
                errors=[
                    {
                        "field": f"entries[{i}].grade",
                        "code": "GRADE_WITH_ABSENT",
                        "message": "Nota y ausente son excluyentes.",
                    }
                ],
            )
        if ent.student_id in seen:
            raise BadRequest(
                "Hay alumnos repetidos en la solicitud.",
                code="DUPLICATE_STUDENT",
                errors=[
                    {
                        "field": f"entries[{i}].studentId",
                        "code": "DUPLICATE_STUDENT",
                        "message": f"{ent.student_id} está repetido.",
                    }
                ],
            )
        seen.add(ent.student_id)

    roster_ids = {e.student_id for e in roster_of(access.detail)}
    offenders = [(i, e.student_id) for i, e in enumerate(body.entries) if e.student_id not in roster_ids]
    if offenders:
        raise BadRequest(
            "Hay alumnos que no están inscriptos en el curso.",
            code="STUDENT_NOT_ENROLLED",
            errors=[
                {
                    "field": f"entries[{i}].studentId",
                    "code": "STUDENT_NOT_ENROLLED",
                    "message": f"{sid} no está inscripto.",
                }
                for i, sid in offenders
            ],
        )

    existing = {
        r.alumno_id: r
        for r in db.session.scalars(
            select(Calificacion).where(
                Calificacion.examen_id == exam_id, Calificacion.alumno_id.in_(list(seen))
            )
        )
    }

    to_set, to_clear, changed_grades = [], [], []
    for ent in body.entries:
        if ent.grade is None and not ent.absent:
            to_clear.append(ent.student_id)
            continue
        grade = _q(ent.grade)
        to_set.append(
            {
                "examen_id": exam_id,
                "alumno_id": ent.student_id,
                "nota": grade,
                "ausente": ent.absent,
                "cargada_por": access.teacher_id,
            }
        )
        if grade is not None:
            prev = existing.get(ent.student_id)
            if prev is None or prev.nota is None or _q(prev.nota) != grade:
                changed_grades.append((ent.student_id, grade))

    if to_set:
        stmt = pg_insert(Calificacion).values(to_set)
        stmt = stmt.on_conflict_do_update(
            constraint="calificacion_examen_alumno_uk",
            set_={
                "nota": stmt.excluded.nota,
                "ausente": stmt.excluded.ausente,
                "cargada_por": stmt.excluded.cargada_por,
                "cargada_en": func.now(),
            },
        )
        db.session.execute(stmt)
    if to_clear:
        db.session.execute(
            delete(Calificacion).where(
                Calificacion.examen_id == exam_id, Calificacion.alumno_id.in_(to_clear)
            )
        )
    if changed_grades:
        event_service.enqueue(
            db.session,
            EVENT_TYPES.grade_published,
            f"exam/{exam_id}",
            {
                "courseId": course_id,
                "examId": exam_id,
                "examType": exam.tipo,
                "grades": [
                    {
                        "studentId": sid,
                        "grade": float(g),
                        "status": "APROBADO" if g >= cfg.passing_grade else "DESAPROBADO",
                    }
                    for sid, g in changed_grades
                ],
            },
            actor_id=access.teacher_id,
        )
    db.session.commit()

    entries = [
        SavedGradeEntry(student_id=r["alumno_id"], grade=r["nota"], absent=r["ausente"]) for r in to_set
    ]
    entries += [SavedGradeEntry(student_id=sid, grade=None, absent=False) for sid in to_clear]
    return GradesUpsertResponse(saved=len(to_set), cleared=len(to_clear), entries=entries)


def course_matrix(principal: Principal, course_id: int) -> GradeMatrix:
    access = authorize_course(principal, course_id)
    exams = db.session.scalars(
        select(Examen)
        .where(Examen.curso_id == course_id, Examen.estado != "CANCELADO")
        .order_by(Examen.fecha, Examen.hora_inicio, Examen.id)
    ).all()
    roster = load_roster(access.detail)
    by_exam: dict[tuple[int, str], Calificacion] = {}
    if exams:
        for r in db.session.scalars(
            select(Calificacion).where(Calificacion.examen_id.in_([e.id for e in exams]))
        ):
            by_exam[(r.examen_id, r.alumno_id)] = r
    now = now_local()
    rows = []
    for s in roster.entries:
        cells, nums = {}, []
        for e in exams:
            r = by_exam.get((e.id, s.student_id))
            if r is not None:
                cells[str(e.id)] = MatrixCell(grade=r.nota, absent=r.ausente)
                if r.nota is not None:
                    nums.append(r.nota)
        rows.append(
            MatrixRow(
                student_id=s.student_id,
                student_name=s.name,
                file_number=s.file_number,
                grades=cells,
                average=rules.mean(nums, 1),
            )
        )
    return GradeMatrix(
        exams=[
            MatrixExam(
                id=e.id,
                type=e.tipo,
                name=e.nombre,
                date=e.fecha,
                phase=rules.exam_phase(e.estado, e.fecha, e.hora_inicio, e.duracion_minutos, now),
            )
            for e in exams
        ],
        rows=rows,
    )


_ = (ValidationFailed, ExamPhase)  # re-exported for callers/tests
