"""Exams (design §10.6, §11.2)."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.constants import (
    COURSE_CANCELLED_STATUS,
    EVENT_TYPES,
    EXAM_TYPE_CATALOG,
    ExamPhase,
    ExamStatus,
)
from app.errors import Conflict, NotFound
from app.extensions import db
from app.integrations.base import roster_of
from app.models import Calificacion, Examen
from app.schemas.exams import (
    CancelRequest,
    CourseRef,
    ExamCreateRequest,
    ExamDetailDto,
    ExamDto,
    ExamList,
    ExamPatchRequest,
    ExamQuery,
    ExamWithCourseDto,
    ExamWithCourseList,
    GradingProgress,
)
from app.security.course_access import authorize_course
from app.security.principal import Principal
from app.services import event_service, locks, rules
from app.services.course_service import list_my_course_details
from app.time import now_local, today_local

log = logging.getLogger("app.exams")


def exam_dto(e: Examen, graded_count: int) -> ExamDto:
    end = rules.exam_end(e.fecha, e.hora_inicio, e.duracion_minutos)
    return ExamDto(
        id=e.id,
        course_id=e.curso_id,
        type=e.tipo,
        name=e.nombre,
        description=e.descripcion,
        date=e.fecha,
        start_time=e.hora_inicio,
        duration_minutes=e.duracion_minutos,
        end_time=end.time(),
        modality=e.modalidad,
        status=e.estado,
        phase=rules.exam_phase(e.estado, e.fecha, e.hora_inicio, e.duracion_minutos, now_local()),
        graded_count=graded_count,
        created_at=e.creado_en,
        updated_at=e.actualizado_en,
    )


def _graded_counts(exam_ids: list[int]) -> dict[int, int]:
    if not exam_ids:
        return {}
    rows = db.session.execute(
        select(Calificacion.examen_id, func.count())
        .where(Calificacion.examen_id.in_(exam_ids), Calificacion.nota.is_not(None))
        .group_by(Calificacion.examen_id)
    )
    return {r[0]: r[1] for r in rows}


def load_exam(course_id: int, exam_id: int) -> Examen:
    exam = db.session.get(Examen, exam_id)
    if exam is None or exam.curso_id != course_id:
        raise NotFound("El examen no existe en este curso.", code="EXAM_NOT_FOUND")
    return exam


def _active_exam_of_type(course_id: int, tipo: str, exclude_id: int | None = None) -> bool:
    q = select(Examen.id).where(
        Examen.curso_id == course_id, Examen.tipo == tipo, Examen.estado != "CANCELADO"
    )
    if exclude_id is not None:
        q = q.where(Examen.id != exclude_id)
    return db.session.scalar(q) is not None


def _dup_error() -> Conflict:
    return Conflict("Ya existe un examen activo de este tipo en el curso.", code="EXAM_TYPE_ALREADY_EXISTS")


def _default_name(tipo: str) -> str:
    for t in EXAM_TYPE_CATALOG:
        if t["type"] == tipo:
            return t["name"]
    return tipo.replace("_", " ").title()


def list_exams(principal: Principal, course_id: int) -> ExamList:
    authorize_course(principal, course_id)
    exams = db.session.scalars(
        select(Examen)
        .where(Examen.curso_id == course_id)
        .order_by(Examen.fecha, Examen.hora_inicio, Examen.id)
    ).all()
    counts = _graded_counts([e.id for e in exams])
    return ExamList([exam_dto(e, counts.get(e.id, 0)) for e in exams])


def create_exam(principal: Principal, course_id: int, body: ExamCreateRequest) -> ExamDto:
    access = authorize_course(principal, course_id, write=True)
    if access.detail.course.status == COURSE_CANCELLED_STATUS:
        raise Conflict("El curso está cancelado.", code="COURSE_CANCELLED")
    if body.date < today_local():
        from app.errors import ValidationFailed

        raise ValidationFailed(
            [{"field": "date", "code": "DATE_IN_PAST", "message": "La fecha no puede ser anterior a hoy."}],
            detail="La fecha no puede ser anterior a hoy.",
        )
    if _active_exam_of_type(course_id, body.type):
        raise _dup_error()
    exam = Examen(
        curso_id=course_id,
        tipo=body.type,
        nombre=body.name or _default_name(body.type),
        descripcion=body.description,
        fecha=body.date,
        hora_inicio=body.start_time,
        duracion_minutos=body.duration_minutes,
        modalidad=body.modality.value,
        estado=ExamStatus.PROGRAMADO.value,
        creado_por=access.teacher_id,
    )
    db.session.add(exam)
    try:
        db.session.flush()
        event_service.enqueue(
            db.session,
            EVENT_TYPES.exam_created,
            f"exam/{exam.id}",
            {
                "courseId": course_id,
                "examId": exam.id,
                "type": exam.tipo,
                "name": exam.nombre,
                "date": exam.fecha.isoformat(),
                "startTime": exam.hora_inicio.strftime("%H:%M"),
                "durationMinutes": exam.duracion_minutos,
                "modality": exam.modalidad,
            },
            actor_id=access.teacher_id,
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise _dup_error() from None
    db.session.refresh(exam)
    return exam_dto(exam, 0)


def get_exam(principal: Principal, course_id: int, exam_id: int) -> ExamDetailDto:
    access = authorize_course(principal, course_id)
    exam = load_exam(course_id, exam_id)
    roster_ids = {e.student_id for e in roster_of(access.detail)}
    rows = db.session.scalars(select(Calificacion).where(Calificacion.examen_id == exam_id)).all()
    graded = sum(1 for r in rows if r.nota is not None and r.alumno_id in roster_ids)
    absent = sum(1 for r in rows if r.ausente and r.alumno_id in roster_ids)
    enrolled = len(roster_ids)
    base = exam_dto(exam, sum(1 for r in rows if r.nota is not None))
    return ExamDetailDto(
        **base.model_dump(),
        grading_progress=GradingProgress(
            enrolled=enrolled, graded=graded, absent=absent, pending=max(enrolled - graded - absent, 0)
        ),
    )


def patch_exam(principal: Principal, course_id: int, exam_id: int, body: ExamPatchRequest) -> ExamDto:
    access = authorize_course(principal, course_id, write=True)
    exam = load_exam(course_id, exam_id)
    if exam.estado == ExamStatus.CANCELADO:
        raise Conflict("El examen está cancelado y no puede modificarse.", code="EXAM_CANCELLED")
    changes = body.model_fields_set
    if "type" in changes and body.type is not None and body.type != exam.tipo:
        if db.session.scalar(
            select(func.count()).select_from(Calificacion).where(Calificacion.examen_id == exam.id)
        ):
            raise Conflict(
                "No se puede cambiar el tipo de un examen con calificaciones.", code="EXAM_HAS_GRADES"
            )
        if locks.exam_has_valid_acta(exam.id):
            raise Conflict("El examen tiene un acta vigente.", code="EXAM_HAS_ACTA")
        if _active_exam_of_type(course_id, body.type, exclude_id=exam.id):
            raise _dup_error()
        exam.tipo = body.type
    if "name" in changes and body.name is not None:
        exam.nombre = body.name
    if "description" in changes:
        exam.descripcion = body.description
    if "date" in changes and body.date is not None:  # no past-date check on edit (matches frontend)
        exam.fecha = body.date
    if "start_time" in changes and body.start_time is not None:
        exam.hora_inicio = body.start_time
    if "duration_minutes" in changes and body.duration_minutes is not None:
        exam.duracion_minutos = body.duration_minutes
    if "modality" in changes and body.modality is not None:
        exam.modalidad = body.modality.value
    exam.actualizado_en = func.now()
    # TODO(CORE): an EXAM_UPDATED notification is mentioned in the Excel but unconfirmed -> no event on edit.
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise _dup_error() from None
    db.session.refresh(exam)
    log.info("exam_updated", extra={"examId": exam_id, "by": access.teacher_id})
    return exam_dto(exam, _graded_counts([exam.id]).get(exam.id, 0))


def cancel_exam(principal: Principal, course_id: int, exam_id: int, body: CancelRequest) -> ExamDto:
    access = authorize_course(principal, course_id, write=True)
    exam = load_exam(course_id, exam_id)
    if exam.estado != ExamStatus.CANCELADO:
        if locks.exam_has_valid_acta(exam.id):
            raise Conflict("El examen tiene un acta vigente; anulala primero.", code="EXAM_HAS_ACTA")
        exam.estado = ExamStatus.CANCELADO.value
        exam.actualizado_en = func.now()
        db.session.commit()
        db.session.refresh(exam)
        # The schema has no column for the reason: it is accepted and logged only.
        log.info("exam_cancelled", extra={"examId": exam_id, "by": access.teacher_id, "reason": body.reason})
    return exam_dto(exam, _graded_counts([exam.id]).get(exam.id, 0))


def list_my_exams(principal: Principal, q: ExamQuery) -> ExamWithCourseList:
    details = {d.course.id: d for d in list_my_course_details(principal)}
    if not details:
        return ExamWithCourseList([])
    date_from: date | None = q.from_
    if date_from is None and q.phase == ExamPhase.UPCOMING:
        date_from = today_local()
    stmt = select(Examen).where(Examen.curso_id.in_(list(details)))
    if date_from is not None:
        stmt = stmt.where(Examen.fecha >= date_from)
    if q.to is not None:
        stmt = stmt.where(Examen.fecha <= q.to)
    if not q.include_cancelled:
        stmt = stmt.where(Examen.estado != "CANCELADO")
    exams = db.session.scalars(stmt.order_by(Examen.fecha, Examen.hora_inicio, Examen.id)).all()
    counts = _graded_counts([e.id for e in exams])
    out: list[ExamWithCourseDto] = []
    for e in exams:
        dto = exam_dto(e, counts.get(e.id, 0))
        if q.phase is not None and dto.phase != q.phase:
            continue
        d = details[e.curso_id]
        out.append(
            ExamWithCourseDto(
                **dto.model_dump(),
                course=CourseRef(id=d.course.id, code=d.course.code, subject_name=d.subject.name),
            )
        )
        if q.limit and len(out) >= q.limit:
            break
    return ExamWithCourseList(out)
