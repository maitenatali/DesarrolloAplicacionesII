"""Attendance (design §10.8, §11.1)."""

from __future__ import annotations

from datetime import date

from flask import current_app
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from app.constants import EVENT_TYPES, AttendanceStatus
from app.errors import BadRequest, Conflict, NotFound
from app.extensions import db
from app.integrations.base import roster_of
from app.models import Asistencia, AsistenciaPorAlumno, Clase
from app.schemas.attendance import (
    AttendanceDto,
    AttendanceList,
    AttendanceListItem,
    AttendancePutRequest,
    AttendanceRecord,
    AttendanceSummaryDto,
    StudentAttendanceSummary,
)
from app.security.course_access import authorize_course
from app.security.principal import Principal
from app.services import event_service, locks
from app.time import today_local


def _dto(clase: Clase) -> AttendanceDto:
    recs = sorted(clase.asistencias, key=lambda a: a.alumno_id)
    return AttendanceDto(
        date=clase.fecha,
        notes=clase.observaciones,
        records=[
            AttendanceRecord(student_id=a.alumno_id, status=AttendanceStatus(a.estado), note=a.observacion)
            for a in recs
        ],
    )


def list_attendances(principal: Principal, course_id: int) -> AttendanceList:
    authorize_course(principal, course_id)
    rows = db.session.execute(
        select(
            Clase.fecha,
            Clase.observaciones,
            Clase.actualizado_en,
            func.count(Asistencia.id),
            func.count(case((Asistencia.estado == "PRESENTE", 1))),
            func.count(case((Asistencia.estado == "AUSENTE", 1))),
            func.count(case((Asistencia.estado == "JUSTIFICADO", 1))),
        )
        .outerjoin(Asistencia, Asistencia.clase_id == Clase.id)
        .where(Clase.curso_id == course_id)
        .group_by(Clase.id)
        .order_by(Clase.fecha.desc())
    ).all()
    return AttendanceList(
        [
            AttendanceListItem(
                date=r[0], notes=r[1], updated_at=r[2], total=r[3], present=r[4], absent=r[5], justified=r[6]
            )
            for r in rows
        ]
    )


def _find_clase(course_id: int, day: date, *, lock: bool = False) -> Clase | None:
    q = select(Clase).where(Clase.curso_id == course_id, Clase.fecha == day)
    if lock:
        q = q.with_for_update()
    return db.session.scalar(q)


def get_attendance(principal: Principal, course_id: int, day: date) -> AttendanceDto:
    authorize_course(principal, course_id)
    clase = _find_clase(course_id, day)
    if clase is None:
        raise NotFound("No hay asistencia registrada para esa fecha.", code="ATTENDANCE_NOT_RECORDED")
    return _dto(clase)


def put_attendance(
    principal: Principal, course_id: int, day: date, body: AttendancePutRequest
) -> tuple[AttendanceDto, bool]:
    access = authorize_course(principal, course_id, write=True)
    if day > today_local():
        raise BadRequest("La fecha no puede ser futura.", code="DATE_IN_FUTURE")
    if locks.course_has_valid_cursada_acta(course_id):
        raise Conflict(
            "Hay un acta de cursada vigente; anulala para editar la asistencia.",
            code="ATTENDANCE_LOCKED_BY_ACTA",
        )

    seen: set[str] = set()
    for i, r in enumerate(body.records):
        if r.student_id in seen:
            raise BadRequest(
                "Hay alumnos repetidos en la solicitud.",
                code="DUPLICATE_STUDENT",
                errors=[
                    {
                        "field": f"records[{i}].studentId",
                        "code": "DUPLICATE_STUDENT",
                        "message": f"{r.student_id} está repetido.",
                    }
                ],
            )
        seen.add(r.student_id)
    roster_ids = {e.student_id for e in roster_of(access.detail)}
    unknown = [(i, r.student_id) for i, r in enumerate(body.records) if r.student_id not in roster_ids]
    if unknown:
        raise BadRequest(
            "Hay alumnos que no están inscriptos en el curso.",
            code="STUDENT_NOT_ENROLLED",
            errors=[
                {
                    "field": f"records[{i}].studentId",
                    "code": "STUDENT_NOT_ENROLLED",
                    "message": f"{sid} no está inscripto.",
                }
                for i, sid in unknown
            ],
        )
    missing = sorted(roster_ids - seen)
    if missing:
        raise BadRequest(
            "La asistencia debe incluir a todos los alumnos del curso.",
            code="INCOMPLETE_ROSTER",
            errors=[
                {"field": "records", "code": "INCOMPLETE_ROSTER", "message": f"Falta {sid}."}
                for sid in missing
            ],
        )

    clase = created = None
    for attempt in (1, 2):
        clase = _find_clase(course_id, day, lock=True)
        created = clase is None
        if created:
            clase = Clase(curso_id=course_id, fecha=day, creado_por=access.teacher_id)
            db.session.add(clase)
        try:
            db.session.flush()
            break
        except IntegrityError:  # two concurrent creates of the same date: the unique index serialised them
            db.session.rollback()
            if attempt == 2:
                raise
    assert clase is not None

    clase.observaciones = body.notes
    incoming = {r.student_id: r for r in body.records}
    existing = {a.alumno_id: a for a in clase.asistencias}
    for sid, a in list(existing.items()):
        if sid not in incoming:
            clase.asistencias.remove(a)  # delete-orphan
    for sid, r in incoming.items():
        a = existing.get(sid)
        if a is None:
            a = Asistencia(alumno_id=sid)
            clase.asistencias.append(a)
        a.estado, a.observacion = r.status.value, r.note
    clase.actualizado_en = func.now()

    counts = {s: sum(1 for r in body.records if r.status == s) for s in AttendanceStatus}
    event_service.enqueue(
        db.session,
        EVENT_TYPES.attendance_recorded,
        f"course/{course_id}/attendance/{day.isoformat()}",
        {
            "courseId": course_id,
            "date": day.isoformat(),
            "counts": {
                "present": counts[AttendanceStatus.PRESENTE],
                "absent": counts[AttendanceStatus.AUSENTE],
                "justified": counts[AttendanceStatus.JUSTIFICADO],
            },
            "records": [{"studentId": r.student_id, "status": r.status.value} for r in body.records],
        },
        actor_id=access.teacher_id,
    )
    db.session.commit()
    db.session.refresh(clase)
    return _dto(clase), bool(created)


def attendance_summary(principal: Principal, course_id: int) -> AttendanceSummaryDto:
    authorize_course(principal, course_id)
    rows = db.session.scalars(
        select(AsistenciaPorAlumno)
        .where(AsistenciaPorAlumno.curso_id == course_id)
        .order_by(AsistenciaPorAlumno.alumno_id)
    ).all()
    return AttendanceSummaryDto(
        threshold=current_app.extensions["settings"].regular_threshold,
        students=[
            StudentAttendanceSummary(
                student_id=r.alumno_id,
                classes_recorded=r.clases_registradas,
                present=r.presentes,
                justified=r.justificados,
                absences=r.inasistencias,
                attendance_percentage=r.porcentaje_asistencia,
                condition=r.condicion,
            )
            for r in rows
        ],
    )
