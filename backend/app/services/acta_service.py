"""Actas: generation, annulment, retrieval (design §10.9, §11.5-11.8)."""

from __future__ import annotations

import logging
from decimal import Decimal

from flask import current_app
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.constants import (
    COURSE_CANCELLED_STATUS,
    EVENT_TYPES,
    ActaStatus,
    ActaType,
    Condition,
    ExamStatus,
    Result,
)
from app.errors import BadRequest, Conflict, Forbidden, NotFound
from app.extensions import db
from app.models import Acta, ActaDetalle, Calificacion, Examen
from app.schemas.actas import (
    ActaCounts,
    ActaCreatedDto,
    ActaCreateRequest,
    ActaDto,
    ActaPage,
    ActaQuery,
    ActaRow,
    ActaSummaryDto,
    ActaSync,
    AnnulRequest,
    SyncResponse,
)
from app.security.course_access import authorize_course, teacher_keys, teacher_name
from app.security.decorators import is_admin
from app.security.principal import Principal
from app.services import acta_sync_service, event_service, rules
from app.services.course_service import attendance_by_student, load_roster
from app.time import now_utc, today_local

log = logging.getLogger("app.actas")


# --- mapping --------------------------------------------------------------------
def _counts(acta: Acta) -> ActaCounts:
    c = {r: 0 for r in Result}
    for d in acta.detalles:
        c[Result(d.resultado)] += 1
    return ActaCounts(
        approved=c[Result.APROBADO],
        failed=c[Result.DESAPROBADO],
        absent=c[Result.AUSENTE],
        regular=c[Result.REGULAR],
        free=c[Result.LIBRE],
    )


def _summary_fields(a: Acta) -> dict:
    return dict(
        id=a.id,
        number=a.numero,
        type=a.tipo,
        status=a.estado,
        course_id=a.curso_id,
        subject_id=a.asignatura_id,
        period_id=a.periodo_id,
        exam_id=a.examen_id,
        subject=a.materia,
        commission=a.comision,
        period=a.periodo,
        teacher_id=a.docente_id,
        teacher_name=a.docente_nombre,
        date=a.fecha,
        notes=a.observaciones,
        generated_at=a.generada_en,
        annulled_at=a.anulada_en,
        annulment_reason=a.motivo_anulacion,
        sync=ActaSync(ok=a.sync_ok, error=a.sync_error, last_attempt_at=a.sync_en),
        counts=_counts(a),
    )


def acta_summary_dto(a: Acta) -> ActaSummaryDto:
    return ActaSummaryDto(**_summary_fields(a))


def acta_dto(a: Acta) -> ActaDto:
    rows = [
        ActaRow(
            order=d.orden,
            student_id=d.alumno_id,
            student_name=d.alumno_nombre,
            student_file_number=d.alumno_legajo,
            grade=d.nota,
            result=Result(d.resultado),
        )
        for d in a.detalles
    ]
    return ActaDto(**_summary_fields(a), rows=rows)


# --- numbering ------------------------------------------------------------------
def next_number(year: int) -> str:
    """§11.5: transaction-scoped advisory lock serialises numbering per year; taken late to keep it short."""
    db.session.execute(text("select pg_advisory_xact_lock(hashtext(:k))"), {"k": f"acta-number-{year}"})
    last = (
        db.session.scalar(
            text(
                "select max(substring(numero from '^[0-9]{4}-([0-9]+)$')::int) from acta where numero like :p"
            ),
            {"p": f"{year}-%"},
        )
        or 0
    )
    return rules.format_acta_number(year, last + 1)


# --- visibility -----------------------------------------------------------------
def _load_acta(principal: Principal, acta_id: int, *, write: bool = False) -> Acta:
    a = db.session.scalar(select(Acta).where(Acta.id == acta_id).options(selectinload(Acta.detalles)))
    if a is None:
        raise NotFound("El acta no existe.", code="ACTA_NOT_FOUND")
    owner = a.docente_id in set(teacher_keys(principal))
    if not owner and (write or not is_admin(principal)):
        # 404 (not 403): don't leak the existence of other teachers' actas
        raise NotFound("El acta no existe.", code="ACTA_NOT_FOUND")
    return a


def get_acta(principal: Principal, acta_id: int) -> ActaDto:
    return acta_dto(_load_acta(principal, acta_id))


def list_actas(principal: Principal, q: ActaQuery) -> ActaPage:
    stmt = select(Acta)
    if not is_admin(principal):
        stmt = stmt.where(Acta.docente_id.in_(teacher_keys(principal)))
    for col, val in (
        (Acta.curso_id, q.course_id),
        (Acta.periodo_id, q.period_id),
        (Acta.tipo, q.type.value if q.type else None),
        (Acta.estado, q.status.value if q.status else None),
    ):
        if val is not None:
            stmt = stmt.where(col == val)
    total = db.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.session.scalars(
        stmt.options(selectinload(Acta.detalles))
        .order_by(Acta.generada_en.desc(), Acta.id.desc())
        .limit(q.limit)
        .offset(q.offset)
    ).all()
    return ActaPage(items=[acta_summary_dto(a) for a in rows], total=total, limit=q.limit, offset=q.offset)


# --- generation -----------------------------------------------------------------
def _existing_valid(course_id: int, tipo: str, exam_id: int | None) -> Acta | None:
    return db.session.scalar(
        select(Acta).where(
            Acta.curso_id == course_id,
            Acta.tipo == tipo,
            Acta.estado == "GENERADA",
            func.coalesce(Acta.examen_id, 0) == (exam_id or 0),
        )
    )


def _already_exists(existing_id: int) -> Conflict:
    return Conflict(
        "Ya existe un acta generada para este curso y tipo.",
        code="ACTA_ALREADY_EXISTS",
        existingActaId=existing_id,
    )


def generate_acta(principal: Principal, body: ActaCreateRequest) -> ActaCreatedDto:
    cfg = current_app.extensions["settings"]

    # A. pre-flight: network allowed, no write transaction open ------------------------
    if body.type == ActaType.FINAL and body.exam_id is None:
        raise BadRequest(
            "examId es obligatorio para un acta FINAL.",
            code="VALIDATION_ERROR",
            errors=[{"field": "examId", "code": "REQUIRED", "message": "Obligatorio para FINAL."}],
        )
    if body.type == ActaType.CURSADA and body.exam_id is not None:
        raise BadRequest(
            "examId no corresponde a un acta CURSADA.",
            code="VALIDATION_ERROR",
            errors=[{"field": "examId", "code": "NOT_ALLOWED", "message": "No permitido en CURSADA."}],
        )
    access = authorize_course(principal, body.course_id, write=True, fresh=True)
    detail = access.detail
    if detail.course.status == COURSE_CANCELLED_STATUS:
        raise Conflict("El curso está cancelado.", code="COURSE_CANCELLED")
    roster = load_roster(detail, strict=True)  # directory failure -> 502, nothing persisted
    if not roster.entries:
        raise Conflict("El curso no tiene alumnos inscriptos.", code="NO_STUDENTS")
    warnings = [f"PROFILE_MISSING:{e.student_id}" for e in roster.entries if e.profile is None]
    teacher_id = access.teacher_id
    t_name = teacher_name(principal, teacher_id)

    # B. transaction -------------------------------------------------------------
    existing = _existing_valid(body.course_id, body.type.value, body.exam_id)
    if existing is not None:
        raise _already_exists(existing.id)

    attendance = attendance_by_student(body.course_id)
    rows: list[tuple[str, str, str, Decimal | None, Result]] = []  # id, name, legajo, grade, result
    if body.type == ActaType.FINAL:
        exam = db.session.get(Examen, body.exam_id)
        if exam is None or exam.curso_id != body.course_id:
            raise NotFound("El examen no existe en este curso.", code="EXAM_NOT_FOUND")
        if exam.estado == ExamStatus.CANCELADO:
            raise Conflict("El examen está cancelado.", code="EXAM_CANCELLED")
        if exam.tipo not in cfg.final_exam_types:
            raise Conflict("El examen no es de tipo final.", code="EXAM_NOT_FINAL_TYPE")
        cals = {
            c.alumno_id: c
            for c in db.session.scalars(select(Calificacion).where(Calificacion.examen_id == exam.id))
        }
        numeric = 0
        for e in roster.entries:
            cal = cals.get(e.student_id)
            grade = cal.nota if cal else None
            if grade is not None:
                numeric += 1
            att = attendance.get(e.student_id)
            res = rules.final_result(
                grade=grade,
                absent=cal is None or cal.ausente,
                condition=att.condicion if att else None,
                passing_grade=cfg.passing_grade,
                requires_regular=cfg.final_requires_regular,
            )
            rows.append((e.student_id, e.name, e.file_number, None if res == Result.AUSENTE else grade, res))
        if numeric == 0:
            raise Conflict("No hay calificaciones cargadas para este examen.", code="NO_GRADES")
        exam_id: int | None = exam.id
    else:
        if not attendance:
            raise Conflict("No hay clases con asistencia registrada.", code="NO_ATTENDANCE_RECORDED")
        for e in roster.entries:
            att = attendance.get(e.student_id)  # no attendance rows => LIBRE; exam grades are NOT consulted
            res = Result.REGULAR if att and att.condicion == Condition.REGULAR else Result.LIBRE
            rows.append((e.student_id, e.name, e.file_number, None, res))
        exam_id = None

    day = today_local()
    try:
        acta = Acta(
            numero=next_number(day.year),
            tipo=body.type.value,
            curso_id=body.course_id,
            asignatura_id=detail.subject.id,
            periodo_id=detail.period.id,
            examen_id=exam_id,
            materia=detail.subject.name,
            comision=detail.course.code,
            periodo=detail.period.label,
            docente_id=teacher_id,
            docente_nombre=t_name,
            fecha=day,
            observaciones=body.notes,
            estado=ActaStatus.GENERADA.value,
            generada_en=now_utc(),  # app clock (testable); the DB default stays as safety net
            sync_ok=0,
            sync_error=0,
        )
        acta.detalles = [
            ActaDetalle(
                orden=i, alumno_id=sid, alumno_nombre=name, alumno_legajo=leg, nota=grade, resultado=res.value
            )
            for i, (sid, name, leg, grade, res) in enumerate(rows, 1)
        ]
        db.session.add(acta)
        db.session.flush()
        counts = _counts(acta)
        event_service.enqueue(
            db.session,
            EVENT_TYPES.acta_generated,
            f"acta/{acta.id}",
            {
                "actaId": acta.id,
                "number": acta.numero,
                "type": acta.tipo,
                "courseId": acta.curso_id,
                "examId": acta.examen_id,
                "teacherId": teacher_id,
                "status": "GENERADA",
                "date": day.isoformat(),
                "counts": counts.model_dump(),
                "results": [
                    {"studentId": sid, "grade": float(g) if g is not None else None, "result": res.value}
                    for sid, _n, _l, g, res in rows
                ],
            },
            actor_id=teacher_id,
        )
        # Analítica (tasa de aprobación por materia/docente/cuatrimestre) consumes one result per student
        # and course; the acta is the official source, so the teacher module publishes it.
        if acta.tipo == ActaType.FINAL.value:
            for sid, _n, _l, g, res in rows:
                if res.value not in (Result.APROBADO.value, Result.DESAPROBADO.value):
                    continue
                event_service.enqueue(
                    db.session,
                    EVENT_TYPES.course_result_published,
                    f"course/{acta.curso_id}/student/{sid}",
                    {
                        "studentId": sid,
                        "courseId": acta.curso_id,
                        "subjectId": acta.asignatura_id,
                        "periodId": acta.periodo_id,
                        "siteId": None,  # TODO(GA): backofficeSiteId of the course's sede (GET /planificacion/sedes)
                        "teacherId": teacher_id,
                        "finalGrade": float(g) if g is not None else None,
                        "status": res.value,
                        "resultDate": day.isoformat(),
                        "actaNumber": acta.numero,
                    },
                    actor_id=teacher_id,
                )
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        dup = _existing_valid(body.course_id, body.type.value, body.exam_id)
        if dup is not None:
            raise _already_exists(dup.id) from e
        raise

    # C. after commit: publish to GA, then record the outcome in a second short transaction ----
    outcome = acta_sync_service.run_sync(acta.curso_id, acta.fecha, acta_sync_service.targets_for(acta))
    _store_outcome(acta, outcome)
    dto = acta_dto(acta)
    return ActaCreatedDto(**dto.model_dump(), warnings=warnings)


def _store_outcome(acta: Acta, outcome: acta_sync_service.SyncOutcome) -> None:
    acta.sync_ok, acta.sync_error, acta.sync_en = outcome.ok, outcome.error, outcome.at
    db.session.commit()
    db.session.refresh(acta)


# --- sync retry & annulment -------------------------------------------------------
def resync_acta(principal: Principal, acta_id: int) -> SyncResponse:
    acta = _load_acta(principal, acta_id, write=True)
    if acta.estado != ActaStatus.GENERADA:
        raise Conflict("El acta está anulada.", code="ACTA_ANNULLED")
    outcome = acta_sync_service.run_sync(acta.curso_id, acta.fecha, acta_sync_service.targets_for(acta))
    _store_outcome(acta, outcome)
    return SyncResponse(sync=ActaSync(ok=acta.sync_ok, error=acta.sync_error, last_attempt_at=acta.sync_en))


def annul_acta(principal: Principal, acta_id: int, body: AnnulRequest) -> ActaDto:
    cfg = current_app.extensions["settings"]
    acta = _load_acta(principal, acta_id, write=True)
    if acta.estado == ActaStatus.ANULADA:
        raise Conflict("El acta ya está anulada.", code="ACTA_ALREADY_ANNULLED")
    now = now_utc()
    acta.estado, acta.anulada_en, acta.motivo_anulacion = ActaStatus.ANULADA.value, now, body.reason
    if cfg.annul_reverts_academic:  # TODO(GA): [OPEN] whether annulment must revert the enrollment record
        log.warning("annul_reverts_academic_not_implemented", extra={"actaId": acta.id})
    event_service.enqueue(
        db.session,
        EVENT_TYPES.acta_annulled,
        f"acta/{acta.id}",
        {
            "actaId": acta.id,
            "number": acta.numero,
            "courseId": acta.curso_id,
            "annulledAt": now.isoformat().replace("+00:00", "Z"),
            "reason": body.reason,
        },
        actor_id=acta.docente_id,
    )
    db.session.commit()
    db.session.refresh(acta)
    return acta_dto(acta)


_ = Forbidden  # noqa: F841
