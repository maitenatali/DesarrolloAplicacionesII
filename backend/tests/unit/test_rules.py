from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.constants import Condition, ExamPhase, Result
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
