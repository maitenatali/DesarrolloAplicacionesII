from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.constants import AcademicStatus, Condition, ExamPhase, Result
from app.services import rules
from app.services.rules import final_result, regularity


def test_regularity_boundaries():
    pct, cond = regularity(3, 0, 1)  # 3 of 4
    assert pct == Decimal("75.00") and cond == Condition.REGULAR
    pct, cond = regularity(2, 0, 1)  # 2 of 3
    assert pct == Decimal("66.67") and cond == Condition.LIBRE


def test_justified_counts_as_attended():
    assert regularity(3, 1, 0)[1] == Condition.REGULAR
    assert regularity(0, 1, 3)[0] == Decimal("25.00")


def test_regularity_compares_unrounded():
    # 74.995 would round to 75.00 but must stay LIBRE
    assert regularity(14999, 0, 5001) == (Decimal("75.00"), Condition.LIBRE)
    pct, cond = regularity(1, 0, 0)
    assert cond == Condition.REGULAR and pct == Decimal("100.00")


def test_regularity_no_rows():
    assert regularity(0, 0, 0)[1] == Condition.LIBRE


@pytest.mark.parametrize(
    "grade,absent,cond,expected",
    [
        (Decimal("8"), False, "REGULAR", Result.APROBADO),
        (Decimal("4.00"), False, "REGULAR", Result.APROBADO),
        (Decimal("3.99"), False, "REGULAR", Result.DESAPROBADO),
        (Decimal("8"), False, "LIBRE", Result.LIBRE),
        (Decimal("8"), False, None, Result.LIBRE),
        (Decimal("3"), False, "LIBRE", Result.DESAPROBADO),
        (None, True, "REGULAR", Result.AUSENTE),
        (None, False, "REGULAR", Result.AUSENTE),
        (Decimal("9"), True, "REGULAR", Result.AUSENTE),
    ],
)
def test_final_result(grade, absent, cond, expected):
    assert final_result(grade=grade, absent=absent, condition=cond) == expected


def test_final_requires_regular_off():
    assert (
        final_result(grade=Decimal("8"), absent=False, condition="LIBRE", requires_regular=False)
        == Result.APROBADO
    )


def test_exam_phase():
    f, t = date(2026, 10, 19), time(18, 0)
    now = datetime(2026, 10, 19, 12, 0)
    assert rules.exam_phase("PROGRAMADO", date(2026, 10, 18), t, 120, now) == ExamPhase.COMPLETED
    assert rules.exam_phase("PROGRAMADO", f, t, 120, now) == ExamPhase.UPCOMING
    assert rules.exam_phase("PROGRAMADO", f, time(9, 0), 120, now) == ExamPhase.COMPLETED  # ended 11:00
    assert rules.exam_phase("PROGRAMADO", f, time(11, 0), 120, now) == ExamPhase.UPCOMING  # in progress
    assert rules.exam_phase("CANCELADO", date(2020, 1, 1), t, 60, now) == ExamPhase.CANCELLED


def test_exam_end_rolls_past_midnight():
    assert rules.exam_end(date(2026, 1, 1), time(23, 0), 120) == datetime(2026, 1, 2, 1, 0)


def test_acta_number_format():
    assert rules.format_acta_number(2026, 1) == "2026-001"
    assert rules.format_acta_number(2026, 1000) == "2026-1000"


def test_roster_sort_numeric_aware_and_missing_last():
    rows = [("b", "10", "Zeta"), ("a", "2", "Ana"), ("x", None, None), ("c", "2", "Álvaro")]
    rows.sort(key=lambda r: rules.roster_sort_key(*r))
    assert [r[0] for r in rows] == ["c", "a", "b", "x"]


def test_mean_round_half_up():
    assert rules.mean([Decimal("7"), Decimal("8")], 1) == Decimal("7.5")
    assert rules.mean([Decimal("6.25"), Decimal("6.25"), Decimal("6.30")], 1) == Decimal("6.3")
    assert rules.mean([], 1) is None


# ---------------------------------------------------------------- situación académica (Examen Final Obligatorio)
D = Decimal
AUS = "AUS"
S = AcademicStatus


def _mark(v):
    if v is None:
        return None
    return rules.Mark(absent=True) if v == AUS else rules.Mark(D(v))


def _sit(p1, p2, recup=None, final=None, **kw):
    return rules.academic_situation(_mark(p1), _mark(p2), _mark(recup), _mark(final), **kw)


# Tabla de aceptación (misma tabla en frontend/src/lib/grading.test.js).
# P1, P2, Recu, Final -> cursada, nota final, estado
@pytest.mark.parametrize(
    ("p1", "p2", "recup", "final", "cursada", "nota_final", "status"),
    [
        ("7", "8", None, None, "7.5", None, S.PENDIENTE_FINAL),
        ("2", "4", "4", "4", "4", "4", S.APROBADA),
        ("2", "4", "3", None, None, None, S.RECURSA),
        ("2", "3", None, None, None, None, S.RECURSA),
        ("5", "4", None, None, "4.5", None, S.PENDIENTE_FINAL),
        ("6", "5", None, "2", "5.5", None, S.FINAL_DESAPROBADO),
        (AUS, "6", "5", "6", "5.5", "5.75", S.APROBADA),
        ("8", "9", None, "9", "8.5", "8.75", S.APROBADA),
    ],
)
def test_academic_situation_table(p1, p2, recup, final, cursada, nota_final, status):
    s = _sit(p1, p2, recup, final)
    assert s.status == status
    assert s.cursada_grade == (None if cursada is None else D(cursada))
    assert s.final_grade == (None if nota_final is None else D(nota_final))


def test_recup_replaces_only_the_failed_parcial_and_says_which():
    s = _sit("2", "4", "4")
    assert (s.recovers, s.p1_effective, s.p2_effective) == ("P1", D("4"), D("4"))
    s = _sit("8", AUS, "6")
    assert (s.recovers, s.p1_effective, s.p2_effective) == ("P2", D("8"), D("6"))
    assert s.cursada_grade == D("7")  # (8 + 6) / 2: la nota del recu reemplaza, no se promedia con el ausente


def test_enabled_fields():
    s = _sit("2", "3")  # ambos desaprobados -> recursa, sin recuperatorio ni final
    assert (s.recup_enabled, s.final_enabled, s.recovers) == (False, False, None)
    s = _sit("7", "8")  # ambos aprobados -> el recu no sirve para levantar nota
    assert (s.recup_enabled, s.final_enabled) == (False, True)
    s = _sit("7", "3")
    assert (s.status, s.recup_enabled, s.final_enabled) == (S.DEBE_RECUPERAR_P2, True, False)
    s = _sit(AUS, "7")
    assert (s.status, s.recovers) == (S.DEBE_RECUPERAR_P1, "P1")
    s = _sit("7", "3", "5")  # recuperó: final habilitado, el recu sigue editable
    assert (s.status, s.recup_enabled, s.final_enabled) == (S.PENDIENTE_FINAL, True, True)


def test_states_without_grades_and_ignored_grades():
    assert _sit(None, None).status == S.CURSANDO
    assert _sit("2", None).status == S.CURSANDO  # falta P2: todavía no se sabe si recupera
    # recuperatorio cargado con ambos parciales aprobados (p. ej. tras una corrección): se ignora
    s = _sit("7", "8", "2")
    assert s.status == S.PENDIENTE_FINAL and s.cursada_grade == D("7.5")
    # final cargado sin cursada aprobada: se ignora, nunca se promedia lo que haya
    s = _sit("2", "3", None, "9")
    assert s.status == S.RECURSA and s.final_grade is None and s.cursada_grade is None


def test_absent_at_recup_or_final():
    assert _sit("2", "7", AUS).status == S.RECURSA
    s = _sit("7", "8", None, AUS)
    assert s.status == S.PENDIENTE_FINAL and s.final_grade is None


def test_boundaries_and_truncation():
    assert _sit("4", "4", None, "4").status == S.APROBADA
    assert _sit("3.99", "4").status == S.DEBE_RECUPERAR_P1
    assert _sit("4", "4", None, "3.99").status == S.FINAL_DESAPROBADO
    s = _sit("7.25", "8.5", None, "8")  # cursada 7.875 -> 7.87; final (7.875 + 8) / 2 = 7.9375 -> 7.93
    assert (s.cursada_grade, s.final_grade) == (D("7.87"), D("7.93"))


def test_libre_overrides_status():
    s = _sit("9", "9", None, "9", condition="LIBRE")
    assert s.status == S.LIBRE and s.final_grade is None and s.cursada_grade == D("9")
    assert _sit("9", "9", condition="REGULAR").status == S.PENDIENTE_FINAL
    assert _sit("9", "9", condition=None).status == S.PENDIENTE_FINAL  # sin asistencia registrada


def test_situation_from_marks_uses_slots_and_ignores_tps():
    m = rules.Mark
    marks = [("PARCIAL_1", m(D("2"))), ("TP_1", m(D("1"))), ("PARCIAL_2", m(D("6"))), ("RECUP_1", m(D("5")))]
    s = rules.situation_from_marks(marks)  # RECUP_1 (tipo viejo) = el recuperatorio
    assert (s.recovers, s.cursada_grade) == ("P1", D("5.5"))
    marks = [("PARCIAL_1", m(D("8"))), ("PARCIAL_2", m(absent=True)), ("RECUPERATORIO", m(D("6")))]
    marks.append(("FINAL", m(D("7"))))
    s = rules.situation_from_marks(marks)
    assert (s.recovers, s.status, s.final_grade) == ("P2", S.APROBADA, D("7"))


def test_exam_slot():
    assert [rules.exam_slot(t) for t in ("PARCIAL_1", "parcial_2", "RECUPERATORIO", "RECUP_2", "FINAL")] == [
        "P1", "P2", "RECUP", "RECUP", "FINAL",
    ]  # fmt: skip
    assert rules.exam_slot("TP_1") is None and rules.exam_slot("PARCIAL_3") is None
    assert rules.exam_slot("COLOQUIO", final_types=("COLOQUIO",)) == "FINAL"


def test_cursada_result_needs_attendance_and_both_parciales():
    r = rules.cursada_result
    assert r(condition="REGULAR", situation=_sit("4", "4")) == Result.REGULAR  # borde: justo 4
    assert r(condition="REGULAR", situation=_sit("2", "9")) == Result.DESAPROBADO  # promedio 5.5 no alcanza
    assert r(condition="REGULAR", situation=_sit("2", "9", "4")) == Result.REGULAR  # recuperó
    assert r(condition="REGULAR", situation=_sit(None, None)) == Result.DESAPROBADO  # sin notas
    assert (
        r(condition="LIBRE", situation=_sit("9", "9")) == Result.LIBRE
    )  # notas altas no salvan la asistencia
    assert r(condition=None, situation=_sit(None, None)) == Result.LIBRE


def test_final_acta_row():
    row = rules.final_acta_row
    reg = "REGULAR"
    assert row(situation=_sit("6", "8", None, "9"), final=_mark("9"), condition=reg) == (
        D("8"),
        Result.APROBADO,
    )
    assert row(situation=_sit("6", "8", None, "3"), final=_mark("3"), condition=reg) == (
        D("3"),
        Result.DESAPROBADO,
    )
    assert row(situation=_sit("6", "8"), final=_mark(AUS), condition=reg) == (None, Result.AUSENTE)
    assert row(situation=_sit("6", "8"), final=None, condition=reg) == (None, Result.AUSENTE)
    assert row(situation=_sit("8", "8", None, "8"), final=_mark("8"), condition="LIBRE") == (
        D("8"),
        Result.LIBRE,
    )
    libre_off = row(
        situation=_sit("8", "8", None, "8"), final=_mark("8"), condition="LIBRE", requires_regular=False
    )
    assert libre_off == (D("8"), Result.APROBADO)
