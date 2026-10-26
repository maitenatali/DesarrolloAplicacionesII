"""Pure business rules (no Flask, no DB). Mirrors design §11 and is unit-tested directly."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.constants import Condition, ExamPhase, ExamStatus, Result


def regularity(
    present: int, justified: int, absences: int, threshold: Decimal = Decimal("75")
) -> tuple[Decimal, Condition]:
    """§11.1. JUSTIFICADO counts as attended. Condition compares the UNROUNDED percentage."""
    total = present + justified + absences
    if total == 0:
        return Decimal("0.00"), Condition.LIBRE
    attended = Decimal(present + justified)
    raw = Decimal(100) * attended / Decimal(total)
    condition = Condition.REGULAR if raw >= threshold else Condition.LIBRE
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), condition


def final_result(
    *,
    grade: Decimal | None,
    absent: bool,
    condition: str | None,
    passing_grade: Decimal = Decimal("4.0"),
    requires_regular: bool = True,
) -> Result:
    """§11.3 ordered rules for one student in a FINAL acta."""
    if absent or grade is None:
        return Result.AUSENTE
    if grade < passing_grade:
        return Result.DESAPROBADO
    if requires_regular and condition != Condition.REGULAR:
        return Result.LIBRE
    return Result.APROBADO


def exam_end(fecha: date, hora_inicio: time, duracion_minutos: int) -> datetime:
    return datetime.combine(fecha, hora_inicio) + timedelta(minutes=duracion_minutos)


def exam_phase(
    estado: str, fecha: date, hora_inicio: time, duracion_minutos: int, now_local: datetime
) -> ExamPhase:
    """§11.2 - `now_local` is injected so it can be frozen in tests."""
    if estado == ExamStatus.CANCELADO:
        return ExamPhase.CANCELLED
    end = exam_end(fecha, hora_inicio, duracion_minutos)
    return ExamPhase.COMPLETED if end <= now_local.replace(tzinfo=None) else ExamPhase.UPCOMING


def format_acta_number(year: int, n: int) -> str:
    return f"{year}-{n:03d}"


def round_half_up(value: Decimal, places: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def mean(values: Iterable[Decimal], places: int) -> Decimal | None:
    vals = list(values)
    if not vals:
        return None
    return round_half_up(sum(vals, Decimal(0)) / Decimal(len(vals)), places)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def natural_key(value: str) -> tuple:
    """Numeric-aware ('2' < '10')."""
    return tuple(
        (0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.split(r"(\d+)", value.casefold()) if t
    )


def roster_sort_key(student_id: str, file_number: str | None, full_name: str | None) -> tuple:
    """§11.4: fileNumber (numeric-aware) then name (es-ish collation); students without profile last, by id."""
    if file_number is None or full_name is None:
        return (1, (), "", student_id)
    return (0, natural_key(file_number), _strip_accents(full_name).casefold(), student_id)
