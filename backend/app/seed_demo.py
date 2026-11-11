"""Demo data (MOCK_DATASET=demo): a realistic 2Q 2026 up to late October, plus the closed 1Q course 30.

Deterministic (fixed random seed), so every PC gets the same rows. Matches `integrations/fixtures_demo`:
- course 42 (María, Mondays): 25 students, 10 classes, PARCIAL_1/PARCIAL_2/RECUPERATORIO graded, FINAL scheduled.
- course 43 (Carlos, Tuesdays): 20 students, 11 classes, PARCIAL_1/TP_1 graded, RECUPERATORIO cancelled,
  PARCIAL_2 and FINAL scheduled.
- course 30 (María, 1Q, closed): 16 students, 15 classes, all exams graded, actas 2026-001 CURSADA,
  2026-002 FINAL (ANULADA, typo) and 2026-003 FINAL; SENT outbox history for them.
- courses 45/46/47 (María, 2Q): 45 = listo para cerrar (todo cargado, SIN acta CURSADA: se genera en la demo),
  46 = a mitad de cursada, 47 = recién dado de alta (solo inscriptos).
Acta rows are computed with `services.rules` (same as `acta_service.generate_acta`), never typed by hand.
Idempotent: skipped if course 42 already has classes.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import select

from app.constants import EVENT_TYPES
from app.extensions import db
from app.integrations import fixtures_demo as fx
from app.models import Acta, ActaDetalle, Asistencia, Calificacion, Clase, Examen, OutboxEvent
from app.services import rules
from app.services.acta_service import _counts
from app.services.acta_sync_service import targets_for
from app.services.event_service import build_envelope

Grade = tuple[Decimal | None, bool]  # (nota, ausente)
HOLIDAYS = {date(2026, 4, 3), date(2026, 5, 1), date(2026, 8, 17), date(2026, 10, 12)}
JUSTIFICATIONS = ["Certificado médico", "Constancia laboral", "Trámite personal con constancia"]


def _weekly(first: date, last: date) -> list[date]:
    out, day = [], first
    while day <= last:
        if day not in HOLIDAYS:
            out.append(day)
        day += timedelta(days=7)
    return out


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=_settings().tz)


def _settings():
    return current_app.extensions["settings"]


def _iso_z(at: datetime) -> str:
    return at.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _grade(rng: random.Random, skill: float, bonus: float = 0.0) -> Decimal:
    return Decimal(max(1, min(10, round(skill + bonus + rng.uniform(-1.6, 1.6))))).quantize(Decimal("0.01"))


class _Course:
    def __init__(self, rng: random.Random, course_id: int, teacher: str, ids: list[str], days: list[date]):
        self.rng, self.id, self.teacher, self.ids, self.days = rng, course_id, teacher, ids, days
        self.skill = {sid: rng.uniform(3.5, 9.5) for sid in ids}
        self.marks: dict[str, list[str]] = {}
        self.exams: dict[str, Examen] = {}
        self.grades: dict[str, dict[str, tuple[Decimal | None, bool]]] = {}  # tipo -> sid -> (nota, ausente)

    # attendance ---------------------------------------------------------------------------------
    def attendance(self, forced: dict[str, tuple[int, int]], max_absences: int) -> None:
        """forced: sid -> (absences, justified). Others: 0..max_absences absences, sometimes one justified."""
        for sid in self.ids:
            absent, justified = forced.get(sid, (self.rng.choice([0, 0, 0, 1, 1, max_absences]), 0))
            if sid not in forced and self.rng.random() < 0.25:
                justified = 1
            row = ["PRESENTE"] * len(self.days)
            picks = self.rng.sample(range(len(self.days)), absent + justified)
            for n, idx in enumerate(picks):
                row[idx] = "JUSTIFICADO" if n < justified else "AUSENTE"
            self.marks[sid] = row
        for i, day in enumerate(self.days):
            clase = Clase(
                curso_id=self.id,
                fecha=day,
                creado_por=self.teacher,
                creado_en=_at(day, 20, 5),
                actualizado_en=_at(day, 20, 5),
            )
            for sid in self.ids:
                estado = self.marks[sid][i]
                note = self.rng.choice(JUSTIFICATIONS) if estado == "JUSTIFICADO" else None
                clase.asistencias.append(Asistencia(alumno_id=sid, estado=estado, observacion=note))
            db.session.add(clase)

    def condition(self, sid: str) -> str:
        row = self.marks[sid]
        _pct, cond = rules.regularity(
            row.count("PRESENTE"),
            row.count("JUSTIFICADO"),
            row.count("AUSENTE"),
            _settings().regular_threshold,
        )
        return cond.value

    # exams --------------------------------------------------------------------------------------
    def exam(self, tipo: str, nombre: str, day: date, start: time, minutes: int, **kw) -> Examen:
        e = Examen(
            curso_id=self.id,
            tipo=tipo,
            nombre=nombre,
            descripcion=kw.get("descripcion"),
            fecha=day,
            hora_inicio=start,
            duracion_minutos=minutes,
            modalidad=kw.get("modalidad", "PRESENCIAL"),
            estado=kw.get("estado", "PROGRAMADO"),
            creado_por=self.teacher,
            creado_en=_at(day - timedelta(days=21), 10),
            actualizado_en=_at(day - timedelta(days=21), 10),
        )
        db.session.add(e)
        self.exams[tipo] = e
        return e

    def grade(self, tipo: str, values: dict[str, tuple[Decimal | None, bool]], loaded: datetime) -> None:
        self.grades[tipo] = values
        for sid, (nota, ausente) in values.items():
            db.session.add(
                Calificacion(
                    examen_id=self.exams[tipo].id,
                    alumno_id=sid,
                    nota=nota,
                    ausente=ausente,
                    cargada_por=self.teacher,
                    cargada_en=loaded,
                )
            )

    def situation(self, sid: str) -> rules.Situation:
        """Situación de cursada (sin FINAL), con las mismas reglas que el acta CURSADA."""
        marks = [(t, rules.Mark(*g[sid])) for t, g in self.grades.items() if t != "FINAL" and sid in g]
        return rules.situation_from_marks(marks, passing_grade=_settings().passing_grade)

    def retake(self) -> list[str]:
        """Quienes tienen exactamente un parcial desaprobado/ausente (los únicos que rinden el recuperatorio)."""
        return [sid for sid in self.ids if self.situation(sid).recup_enabled]

    def random_grades(
        self, fixed: dict[str, tuple[Decimal | None, bool]], absent: int, bonus: float = 0.0, among=None
    ) -> dict[str, tuple[Decimal | None, bool]]:
        pool = [sid for sid in (among or self.ids) if sid not in fixed]
        missing = set(self.rng.sample(pool, min(absent, len(pool))))
        out = dict(fixed)
        for sid in pool:
            out[sid] = (None, True) if sid in missing else (_grade(self.rng, self.skill[sid], bonus), False)
        return out


def _roster(ids: list[str]) -> list[tuple[str, str, str]]:
    profiles = [fx.PROFILES[sid] for sid in ids]
    profiles.sort(key=lambda p: rules.roster_sort_key(p.student_id, p.file_number, p.full_name))
    return [(p.student_id, p.full_name, p.file_number) for p in profiles]


def _sent(event_type: str, subject: str, data: dict, actor: str, at: datetime) -> None:
    env = build_envelope(event_type, subject, data, actor, None)
    env["occurredAt"] = _iso_z(at)
    db.session.add(
        OutboxEvent(
            id=uuid.UUID(env["eventId"]),
            kind="EVENT",
            event_type=event_type,
            subject=subject,
            payload=env,
            status="SENT",
            attempts=1,
            next_attempt_at=at,
            created_at=at,
            sent_at=at + timedelta(seconds=2),
        )
    )


# --------------------------------------------------------------------------------------------------
def _course_42(rng: random.Random) -> None:
    c = _Course(rng, 42, fx.MARIA, fx.IDS_42, _weekly(date(2026, 8, 10), date(2026, 10, 26)))
    c.attendance({fx.JUAN: (0, 0), fx.LUCAS: (4, 0), fx.ANA: (0, 1), fx.IDS_42[-1]: (4, 0)}, max_absences=2)
    c.exam("PARCIAL_1", "Primer Parcial", date(2026, 9, 14), time(18), 120, descripcion="Unidades 1 a 3.")
    c.exam("PARCIAL_2", "Segundo Parcial", date(2026, 10, 19), time(18), 120, descripcion="Unidades 4 a 6.")
    c.exam("RECUPERATORIO", "Recuperatorio", date(2026, 10, 26), time(18), 120)
    c.exam("FINAL", "Final", date(2026, 12, 3), time(18), 180, descripcion="Turno final diciembre.")
    db.session.flush()
    p1 = c.random_grades(
        {fx.JUAN: (Decimal("8.00"), False), fx.LUCAS: (Decimal("5.00"), False), fx.ANA: (None, True)},
        absent=1,
    )
    c.grade("PARCIAL_1", p1, _at(date(2026, 9, 17), 21))
    p2 = c.random_grades(
        {
            fx.JUAN: (Decimal("9.00"), False),
            fx.LUCAS: (Decimal("4.00"), False),
            fx.ANA: (Decimal("7.00"), False),
        },
        absent=1,
        bonus=0.5,
    )
    c.grade("PARCIAL_2", p2, _at(date(2026, 10, 22), 21))
    retake = c.retake()  # unos recuperan P1 y otros P2, en el mismo examen
    c.grade(
        "RECUPERATORIO", c.random_grades({}, absent=1, bonus=1.0, among=retake), _at(date(2026, 10, 27), 20)
    )


def _course_43(rng: random.Random) -> None:
    c = _Course(rng, 43, fx.CARLOS, fx.IDS_43, _weekly(date(2026, 8, 11), date(2026, 10, 20)))
    c.attendance({fx.IDS_43[5]: (4, 0), fx.IDS_43[13]: (5, 1)}, max_absences=2)
    c.exam("PARCIAL_1", "Primer Parcial", date(2026, 9, 15), time(19), 120, descripcion="Unidades 1 a 3.")
    c.exam("TP_1", "TP1: API REST", date(2026, 10, 6), time(19), 120, descripcion="Entrega y defensa grupal.")
    c.exam(
        "RECUPERATORIO", "Recuperatorio", date(2026, 10, 20), time(19), 120, estado="CANCELADO",
        descripcion="Se reprograma por paro de transporte.",
    )  # fmt: skip
    c.exam("PARCIAL_2", "Segundo Parcial", date(2026, 11, 3), time(19), 120, modalidad="VIRTUAL")
    c.exam("FINAL", "Final", date(2026, 12, 9), time(19), 180, descripcion="Turno final diciembre.")
    db.session.flush()
    c.grade("PARCIAL_1", c.random_grades({}, absent=2), _at(date(2026, 9, 19), 11))
    c.grade("TP_1", c.random_grades({}, absent=1, bonus=1.2), _at(date(2026, 10, 10), 11))


def _course_30(rng: random.Random) -> None:
    detail = next(d for d in fx.ALL_COURSES if d.course.id == 30)
    c = _Course(rng, 30, fx.MARIA, fx.IDS_30, _weekly(date(2026, 3, 13), date(2026, 7, 3)))
    outcomes = fx.COURSE_30_OUTCOMES
    c.attendance({sid: (5, 0) for sid, (st, _g) in outcomes.items() if st == "LIBRE"}, max_absences=3)
    c.exam("PARCIAL_1", "Primer Parcial", date(2026, 4, 24), time(8), 120)
    c.exam("PARCIAL_2", "Segundo Parcial", date(2026, 6, 26), time(8), 120)
    c.exam("RECUPERATORIO", "Recuperatorio", date(2026, 7, 3), time(8), 120)
    final = c.exam("FINAL", "Final", date(2026, 7, 10), time(9), 180, descripcion="Turno final julio.")
    db.session.flush()
    # Quien cursó (no LIBRE en GA) tiene parciales >= 4: así la regla "asistencia + parciales" del acta
    # CURSADA reproduce exactamente lo que GA registró (ver guard al final).
    passing_ids = {sid for sid, (st, _g) in outcomes.items() if st != "LIBRE"}

    def floored(grades: dict[str, tuple[Decimal | None, bool]]) -> dict[str, tuple[Decimal | None, bool]]:
        return {
            sid: ((max(n, Decimal("4.00")) if n is not None and sid in passing_ids else n), a)
            for sid, (n, a) in grades.items()
        }

    p1 = floored(c.random_grades({}, absent=1, bonus=0.5))
    c.grade("PARCIAL_1", p1, _at(date(2026, 4, 28), 19))
    c.grade("PARCIAL_2", floored(c.random_grades({}, absent=0, bonus=0.8)), _at(date(2026, 6, 30), 19))
    c.grade(
        "RECUPERATORIO",
        floored(c.random_grades({}, absent=0, bonus=1.5, among=c.retake())),
        _at(date(2026, 7, 6), 19),
    )
    # FINAL grades straight from the GA outcome: REGULAR = regular who skipped it; LIBRE without grade = absent
    sat = {sid: g for sid, (st, g) in outcomes.items() if g is not None}
    c.grade(
        "FINAL",
        {sid: ((sat[sid], False) if sid in sat else (None, True)) for sid in fx.IDS_30 if sid in sat or outcomes[sid][0] == "REGULAR"},
        _at(date(2026, 7, 11), 10),
    )  # fmt: skip

    roster = _roster(fx.IDS_30)
    common = dict(
        curso_id=30,
        asignatura_id=detail.subject.id,
        periodo_id=detail.period.id,
        materia=detail.subject.name,
        comision=detail.course.code,
        periodo=detail.period.label,
        docente_id=fx.MARIA,
        docente_nombre=fx.TEACHER_NAME[fx.MARIA],
    )

    def acta(numero, tipo, day, generated, rows, **kw) -> Acta:
        a = Acta(numero=numero, tipo=tipo, fecha=day, generada_en=generated, **common, **kw)
        a.detalles = [
            ActaDetalle(orden=i, alumno_id=sid, alumno_nombre=n, alumno_legajo=leg, nota=g, resultado=r)
            for i, (sid, n, leg, g, r) in enumerate(rows, 1)
        ]
        a.sync_ok, a.sync_error, a.sync_en = len(targets_for(a)), 0, generated + timedelta(seconds=40)
        db.session.add(a)
        db.session.flush()
        _sent(
            EVENT_TYPES.acta_generated,
            f"acta/{a.id}",
            {
                "actaId": a.id,
                "number": a.numero,
                "type": a.tipo,
                "courseId": 30,
                "examId": a.examen_id,
                "teacherId": fx.MARIA,
                "status": "GENERADA",
                "date": day.isoformat(),
                "counts": _counts(a).model_dump(),
                "results": [
                    {"studentId": sid, "grade": float(g) if g is not None else None, "result": r}
                    for sid, _n, _l, g, r in rows
                ],
            },
            fx.MARIA,
            generated,
        )
        for sid, _n, _l, g, r in rows if tipo == "FINAL" else []:
            if r in ("APROBADO", "DESAPROBADO"):
                _sent(
                    EVENT_TYPES.course_result_published,
                    f"course/30/student/{sid}",
                    {
                        "studentId": sid,
                        "courseId": 30,
                        "subjectId": a.asignatura_id,
                        "periodId": a.periodo_id,
                        "siteId": None,
                        "teacherId": fx.MARIA,
                        "finalGrade": float(g) if g is not None else None,
                        "status": r,
                        "resultDate": day.isoformat(),
                        "actaNumber": a.numero,
                    },
                    fx.MARIA,
                    generated,
                )
        return a

    cursada = [
        (
            sid,
            n,
            leg,
            None,
            rules.cursada_result(condition=c.condition(sid), situation=c.situation(sid)).value,
        )
        for sid, n, leg in roster
    ]
    acta("2026-001", "CURSADA", date(2026, 7, 3), _at(date(2026, 7, 3), 10, 15), cursada)

    def final_rows(grades: dict[str, tuple[Decimal | None, bool]]):
        rows = []
        for sid, n, leg in roster:
            nota, ausente = grades.get(sid, (None, True))
            res = rules.final_result(
                grade=nota,
                absent=ausente,
                condition=c.condition(sid),
                passing_grade=_settings().passing_grade,
                requires_regular=_settings().final_requires_regular,
            ).value
            rows.append((sid, n, leg, None if res == "AUSENTE" else nota, res))
        return rows

    typo_student = fx.IDS_42[3]
    with_typo = dict(c.grades["FINAL"]) | {typo_student: (Decimal("3.00"), False)}
    reason = (
        f"Nota mal cargada para {fx.PROFILES[typo_student].full_name} (3 en lugar de 8). Se regenera el acta."
    )
    annulled_at = _at(date(2026, 7, 11), 9, 5)
    bad = acta(
        "2026-002", "FINAL", date(2026, 7, 10), _at(date(2026, 7, 10), 13, 30), final_rows(with_typo),
        examen_id=final.id, estado="ANULADA", anulada_en=annulled_at, motivo_anulacion=reason,
    )  # fmt: skip
    _sent(
        EVENT_TYPES.acta_annulled,
        f"acta/{bad.id}",
        {
            "actaId": bad.id,
            "number": bad.numero,
            "courseId": 30,
            "annulledAt": _iso_z(annulled_at),
            "reason": reason,
        },
        fx.MARIA,
        annulled_at,
    )
    rows = final_rows(c.grades["FINAL"])
    acta(
        "2026-003", "FINAL", fx.COURSE_30_RESULT_DATE, _at(fx.COURSE_30_RESULT_DATE, 10, 20), rows,
        examen_id=final.id, estado="GENERADA", observaciones="Reemplaza al acta 2026-002 (anulada).",
    )  # fmt: skip

    # Guard: GA's course 30 enrollments must equal what the actas synced (AUSENTE keeps the CURSADA result).
    cursada_by = {sid: r for sid, _n, _l, _g, r in cursada}
    for sid, _n, _l, _g, r in rows:
        synced = cursada_by[sid] if r == "AUSENTE" else r
        if synced != outcomes[sid][0]:
            raise RuntimeError(
                f"demo seed: course 30 {sid} -> {synced}, fixtures_demo says {outcomes[sid][0]}"
            )


def _course_45() -> None:
    """María, miércoles. LISTO PARA CERRAR: todo cargado, sin acta CURSADA (se genera en la demo).

    Tabla fija (sin azar). Resultado esperado del acta CURSADA con la regla
    "asistencia >= 75 % y P1/P2 efectivos >= 4" (el recuperatorio reemplaza al parcial que recupera;
    los TP no cuentan): REGULAR x7, DESAPROBADO x3, LIBRE x2.
    """
    ids = fx.IDS_45
    c = _Course(
        random.Random(0), 45, fx.MARIA, ids, _weekly(date(2026, 8, 12), date(2026, 10, 28))
    )  # 12 clases
    A: Grade = (None, True)  # ausente

    def g(n: str) -> Grade:
        return Decimal(n).quantize(Decimal("0.01")), False

    # (ausencias, justificadas), PARCIAL_1, PARCIAL_2, TP_1, RECUPERATORIO (None = no hay fila)
    plan: list[tuple[tuple[int, int], Grade, Grade, Grade, Grade | None]] = [
        ((0, 0), g("9"), g("8"), g("9"), None),  # regular, cursada 8.5
        ((1, 0), g("1"), g("4"), g("4"), g("6")),  # recupera P1 (1) con 6 -> cursada 5
        (
            (1, 1),
            g("3"),
            g("6"),
            g("5"),
            A,
        ),  # asistencia ok, no se presentó al recup -> RECURSA (DESAPROBADO)
        ((4, 0), g("9"), g("9"), g("10"), None),  # notas altas pero 66.7 % de asistencia -> LIBRE
        ((3, 0), g("4"), g("4"), g("4"), None),  # justo 75 % y justo 4 -> REGULAR
        ((3, 1), g("3"), g("4"), g("4"), g("5")),  # 75 % exacto, recupera P1 -> cursada 4.5 REGULAR
        ((2, 1), g("3"), g("4"), g("4"), g("3")),  # recupera y saca 3 -> RECURSA (DESAPROBADO)
        ((5, 0), A, A, A, None),  # abandonó: 58 % y sin notas -> LIBRE
        ((1, 0), g("7"), g("6"), g("8"), None),
        ((0, 0), g("10"), g("9"), g("10"), None),
        ((2, 0), A, g("5"), g("6"), g("5")),  # ausente en P1, recupera con 5 -> cursada 5 REGULAR
        ((2, 0), g("4"), g("3"), g("4"), None),  # debe recuperar P2 y no lo rindió aún -> DESAPROBADO
    ]
    c.attendance({sid: row[0] for sid, row in zip(ids, plan, strict=True)}, max_absences=0)
    c.exam(
        "PARCIAL_1",
        "Primer Parcial",
        date(2026, 9, 16),
        time(18),
        120,
        descripcion="Modelo relacional y SQL.",
    )
    c.exam("TP_1", "TP1: Modelado de datos", date(2026, 10, 7), time(18), 120, descripcion="Entrega grupal.")
    c.exam(
        "PARCIAL_2",
        "Segundo Parcial",
        date(2026, 10, 21),
        time(18),
        120,
        descripcion="Normalización y transacciones.",
    )
    c.exam("RECUPERATORIO", "Recuperatorio", date(2026, 10, 28), time(18), 120)
    c.exam("FINAL", "Final", date(2026, 12, 2), time(18), 180, descripcion="Turno final diciembre.")
    db.session.flush()
    by_exam: dict[str, dict[str, Grade]] = {"PARCIAL_1": {}, "PARCIAL_2": {}, "TP_1": {}, "RECUPERATORIO": {}}
    for sid, (_att, p1, p2, tp, recup) in zip(ids, plan, strict=True):
        by_exam["PARCIAL_1"][sid], by_exam["PARCIAL_2"][sid], by_exam["TP_1"][sid] = p1, p2, tp
        if recup is not None:
            by_exam["RECUPERATORIO"][sid] = recup
    loaded = {"PARCIAL_1": date(2026, 9, 19), "PARCIAL_2": date(2026, 10, 24),
              "TP_1": date(2026, 10, 10), "RECUPERATORIO": date(2026, 10, 31)}  # fmt: skip
    for tipo, values in by_exam.items():
        c.grade(tipo, values, _at(loaded[tipo], 21))


def _course_46(rng: random.Random) -> None:
    """María, jueves. A MITAD DE CURSADA: P1 y TP1 corregidos, P2 y FINAL por venir."""
    c = _Course(rng, 46, fx.MARIA, fx.IDS_46, _weekly(date(2026, 8, 13), date(2026, 11, 5)))
    c.attendance({fx.IDS_46[2]: (5, 0), fx.IDS_46[7]: (4, 1)}, max_absences=2)
    c.exam("PARCIAL_1", "Primer Parcial", date(2026, 9, 17), time(19), 120, descripcion="Unidades 1 a 3.")
    c.exam("TP_1", "TP1: API REST", date(2026, 10, 8), time(19), 120, descripcion="Entrega y defensa.")
    c.exam("PARCIAL_2", "Segundo Parcial", date(2026, 11, 26), time(19), 120, descripcion="Unidades 4 a 6.")
    c.exam("FINAL", "Final", date(2026, 12, 10), time(19), 180, descripcion="Turno final diciembre.")
    db.session.flush()
    c.grade("PARCIAL_1", c.random_grades({}, absent=1), _at(date(2026, 9, 21), 11))
    c.grade("TP_1", c.random_grades({}, absent=0, bonus=1.0), _at(date(2026, 10, 12), 11))


def load_demo_seed() -> bool:
    loaded = False
    if db.session.scalar(select(Clase.id).where(Clase.curso_id == 42)) is None:
        rng = random.Random(20262)
        _course_42(rng)
        _course_43(rng)
        _course_30(rng)
        loaded = True
    # María's extra demo courses (45 listo para cerrar, 46 a mitad de cursada; 47 solo inscriptos).
    # Separate check + rng so existing databases get them on the next `flask seed`.
    if db.session.scalar(select(Clase.id).where(Clase.curso_id == 45)) is None:
        _course_45()
        _course_46(random.Random(20263))
        loaded = True
    if loaded:
        db.session.commit()
    return loaded
