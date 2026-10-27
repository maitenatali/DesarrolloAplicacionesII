"""Sample data equal to db/seed.sql (design Appendix B). Idempotent: skipped if course 42 already has data."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Acta, ActaDetalle, Asistencia, Calificacion, Clase, Examen

COURSE = 42
TEACHER = "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
DAYS = [date(2026, 8, 11), date(2026, 8, 18), date(2026, 8, 25), date(2026, 9, 1)]
# 456: 4 present (REGULAR 100%); 457: 2 absences (LIBRE 50%); 458: 1 justified + 3 present (REGULAR 100%)
MARKS = {
    "ba310c57-a684-4dbf-a4a4-905fcfbefa08": ["PRESENTE"] * 4,
    "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57": ["PRESENTE", "AUSENTE", "PRESENTE", "AUSENTE"],
    "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58": ["PRESENTE", "JUSTIFICADO", "PRESENTE", "PRESENTE"],
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
        ("ba310c57-a684-4dbf-a4a4-905fcfbefa08", Decimal("8.00"), False),
        ("c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", Decimal("5.00"), False),
        ("d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58", None, True),
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
                ("ba310c57-a684-4dbf-a4a4-905fcfbefa08", "Juan Pérez", "123456", Decimal("8.00"), "APROBADO"),
                (
                    "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57",
                    "Lucas Fernández",
                    "123458",
                    Decimal("3.00"),
                    "DESAPROBADO",
                ),
                ("d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58", "Ana Rodríguez", "123459", None, "AUSENTE"),
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


# ── Local CORE simulator (MOCK_CORE_ENABLED=true): login users + wallets ──────────────────────
MOCK_PASSWORD = "Uade2026!"
TEACHER_PERMISSIONS = [
    "wallet:read:self",
    "wallet:credit:self",
    "teacher:courses:read",
    "teacher:courses:write",
    "notifications:read:self",
]
STUDENT_PERMISSIONS = ["wallet:read:self", "wallet:credit:self", "notifications:read:self"]
ADMIN_ID = "a0000000-0000-4000-8000-000000000001"


def load_mock_core_seed() -> int:
    """Create the simulator's identities (same UUIDs as the GA/Backoffice fixtures). Idempotent."""
    from werkzeug.security import generate_password_hash

    from app.integrations import fixtures
    from app.mock_core.service import post_tx
    from app.models import MockCoreUser

    pwd = generate_password_hash(MOCK_PASSWORD)
    people: list[tuple[str, str, str, str, list[str], list[str]]] = []
    for p in fixtures.TEACHER_PROFILES.values():
        people.append(
            (p.student_id, p.email or "", p.first_name, p.last_name, ["TEACHER"], TEACHER_PERMISSIONS)
        )
    for sid, p in fixtures.PROFILES.items():
        if sid not in fixtures.TEACHER_PROFILES:
            people.append((sid, p.email or "", p.first_name, p.last_name, ["STUDENT"], STUDENT_PERMISSIONS))
    people.append(
        (
            ADMIN_ID,
            "secretaria.academica@uade.edu.ar",
            "Laura",
            "Suárez",
            ["ACADEMIC_ADMIN"],
            ["wallet:read:self"],
        )
    )
    created = 0
    for uid, email, first, last, roles, perms in people:
        if db.session.get(MockCoreUser, uid) is not None:
            continue
        db.session.add(
            MockCoreUser(
                id=uid,
                email=email,
                password_hash=pwd,
                first_name=first,
                last_name=last,
                roles=roles,
                permissions=perms,
                career_ids=["a77c1e40-0000-4000-8000-000000000001"] if "STUDENT" in roles else [],
                status="ACTIVE",
            )
        )
        db.session.flush()
        if "TEACHER" in roles:
            post_tx(
                uid,
                type_="CREDIT",
                concept="TOP_UP",
                amount=Decimal("15000.00"),
                source_module="core",
                external_reference=f"seed/{uid}",
            )
        created += 1
    db.session.commit()
    return created
