"""Sample data equal to db/seed.sql (design Appendix B). Idempotent: skipped if course 42 already has data."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Acta, ActaDetalle, Asistencia, Calificacion, Clase, Examen

COURSE = 42
TEACHER = "docente-123"
DAYS = [date(2026, 8, 11), date(2026, 8, 18), date(2026, 8, 25), date(2026, 9, 1)]
# 456: 4 present (REGULAR 100%); 457: 2 absences (LIBRE 50%); 458: 1 justified + 3 present (REGULAR 100%)
MARKS = {
    "alumno-456": ["PRESENTE"] * 4,
    "alumno-457": ["PRESENTE", "AUSENTE", "PRESENTE", "AUSENTE"],
    "alumno-458": ["PRESENTE", "JUSTIFICADO", "PRESENTE", "PRESENTE"],
}


def load_seed(*, include_acta: bool = True) -> bool:
    if db.session.scalar(select(Clase.id).where(Clase.curso_id == COURSE)) is not None:
        return False
    for i, day in enumerate(DAYS):
        clase = Clase(curso_id=COURSE, fecha=day, creado_por=TEACHER)
        for sid, marks in MARKS.items():
            note = "Certificado médico" if marks[i] == "JUSTIFICADO" else None
            clase.asistencias.append(Asistencia(alumno_id=sid, estado=marks[i], observacion=note))
        db.session.add(clase)

    exams = {}
    for tipo, nombre, fecha in (
        ("PARCIAL_1", "Primer Parcial", date(2026, 8, 25)),
        ("PARCIAL_2", "Segundo Parcial", date(2026, 10, 14)),
        ("FINAL", "Final", date(2026, 12, 3)),
    ):
        e = Examen(
            curso_id=COURSE,
            tipo=tipo,
            nombre=nombre,
            fecha=fecha,
            hora_inicio=time(18, 0),
            duracion_minutos=120,
            modalidad="PRESENCIAL",
            estado="PROGRAMADO",
            creado_por=TEACHER,
        )
        db.session.add(e)
        exams[tipo] = e
    db.session.flush()

    for sid, nota, ausente in (
        ("alumno-456", Decimal("8.00"), False),
        ("alumno-457", Decimal("5.00"), False),
        ("alumno-458", None, True),
    ):
        db.session.add(
            Calificacion(
                examen_id=exams["PARCIAL_1"].id,
                alumno_id=sid,
                nota=nota,
                ausente=ausente,
                cargada_por=TEACHER,
            )
        )

    if include_acta:
        acta = Acta(
            numero="2026-001",
            tipo="FINAL",
            curso_id=COURSE,
            asignatura_id=15,
            periodo_id=8,
            examen_id=exams["FINAL"].id,
            materia="Desarrollo de Aplicaciones II",
            comision="DDA2-A",
            periodo="2° Cuatrimestre 2026",
            docente_id=TEACHER,
            docente_nombre="María Gómez",
            fecha=date(2026, 12, 3),
            observaciones="Acta correspondiente al examen final.",
            estado="GENERADA",
            generada_en=datetime(2026, 12, 3, 22, 42, tzinfo=UTC),
            sync_ok=2,
            sync_error=0,
            sync_en=datetime(2026, 12, 3, 22, 43, tzinfo=UTC),
        )
        for orden, (sid, nombre, leg, nota, res) in enumerate(
            (
                ("alumno-456", "Juan Pérez", "123456", Decimal("8.00"), "APROBADO"),
                ("alumno-457", "Lucas Fernández", "123458", Decimal("3.00"), "DESAPROBADO"),
                ("alumno-458", "Ana Rodríguez", "123459", None, "AUSENTE"),
            ),
            start=1,
        ):
            acta.detalles.append(
                ActaDetalle(
                    orden=orden,
                    alumno_id=sid,
                    alumno_nombre=nombre,
                    alumno_legajo=leg,
                    nota=nota,
                    resultado=res,
                )
            )
        db.session.add(acta)
    db.session.commit()
    return True
