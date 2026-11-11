"""Pure business rules (no Flask, no DB). Mirrors design §11 and is unit-tested directly."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.constants import AcademicStatus, Condition, ExamPhase, ExamStatus, Result


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


def cursada_result(*, condition: str | None, situation: Situation) -> Result:
    """Acta CURSADA: cursada aprobada = asistencia REGULAR Y los dos parciales efectivos >= nota mínima.

    - sin asistencia suficiente -> LIBRE (aunque tenga buenas notas)
    - asistencia ok pero cursada no aprobada (recursa, debe recuperar, faltan notas) -> DESAPROBADO
    """
    if condition != Condition.REGULAR:
        return Result.LIBRE
    return Result.REGULAR if situation.cursada_approved else Result.DESAPROBADO


def final_acta_row(
    *,
    situation: Situation,
    final: Mark | None,
    condition: str | None,
    passing_grade: Decimal = Decimal("4.0"),
    requires_regular: bool = True,
) -> tuple[Decimal | None, Result]:
    """Fila de un acta FINAL: (nota, resultado). La nota de un APROBADO es la nota final de la MATERIA
    ((cursada + final) / 2); la de un DESAPROBADO es la del examen final.

    Ausente / sin nota -> AUSENTE: el acta se cierra igual y el alumno queda "Pendiente de final"
    (no se le manda resultado a GA, que es quien bloquea las correlativas).
    """
    if final is None or final.absent or final.grade is None:
        return None, Result.AUSENTE
    if final.grade < passing_grade or not situation.cursada_approved:
        # TODO(gestion-academica): un final cargado sin cursada aprobada solo puede venir de datos viejos
        # (hoy se rechaza al cargar con FINAL_NOT_ALLOWED); lo informamos DESAPROBADO.
        return final.grade, Result.DESAPROBADO
    if requires_regular and condition != Condition.REGULAR:
        return situation.final_grade, Result.LIBRE
    return situation.final_grade, Result.APROBADO


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


# ---------------------------------------------------------------- situación académica (Examen Final Obligatorio)
# Reglas UADE:
# - 2 parciales (P1, P2), se aprueban con >= 4. Ausente = desaprobado.
# - UN recuperatorio por cursada, solo si exactamente un parcial está desaprobado/ausente. Su nota
#   REEMPLAZA a la del parcial que recupera (no se promedia). Recuperatorio < 4 o ausente -> recursa.
# - Ambos parciales desaprobados -> recursa (sin recuperatorio ni final).
# - Cursada = (P1 efectivo + P2 efectivo) / 2. Final habilitado solo con cursada aprobada.
# - Nota final = (cursada + final) / 2, solo si final >= 4. Final < 4 -> "Final desaprobado", sin nota.
# - Los TP (y cualquier otro tipo) se cargan pero NO entran al cálculo.
#   TODO(docentes): definir si los TP pesan en la cursada.
# Las notas calculadas se TRUNCAN a 2 decimales (no se redondean).

SLOT_P1, SLOT_P2, SLOT_RECUP, SLOT_FINAL = "P1", "P2", "RECUP", "FINAL"
_TRUNC = Decimal("0.01")


@dataclass(frozen=True)
class Mark:
    """Una calificación cargada: nota o ausente. `None` en su lugar = todavía no cargada."""

    grade: Decimal | None = None
    absent: bool = False

    @property
    def loaded(self) -> bool:
        return self.absent or self.grade is not None


@dataclass(frozen=True)
class Situation:
    p1_effective: Decimal | None
    p2_effective: Decimal | None
    recovers: str | None  # "P1" / "P2": a qué parcial aplica el recuperatorio de ESTE alumno
    cursada_grade: Decimal | None
    final_grade: Decimal | None
    status: AcademicStatus
    recup_enabled: bool
    final_enabled: bool

    @property
    def cursada_approved(self) -> bool:
        return self.cursada_grade is not None


def exam_slot(tipo: str, final_types: Iterable[str] = ("FINAL",)) -> str | None:
    """Qué lugar ocupa un tipo de examen en el cálculo. RECUP_1/RECUP_2 son tipos viejos = el recuperatorio."""
    t = tipo.upper()
    if t == "PARCIAL_1":
        return SLOT_P1
    if t == "PARCIAL_2":
        return SLOT_P2
    if t.startswith("RECUP"):
        return SLOT_RECUP
    if t in {f.upper() for f in final_types}:
        return SLOT_FINAL
    return None


def _trunc(v: Decimal) -> Decimal:
    return v.quantize(_TRUNC, rounding=ROUND_DOWN)


def _passed(m: Mark, passing: Decimal) -> bool:
    return not m.absent and m.grade is not None and m.grade >= passing


def academic_situation(
    p1: Mark | None,
    p2: Mark | None,
    recup: Mark | None,
    final: Mark | None,
    *,
    condition: str | None = None,
    passing_grade: Decimal = Decimal("4.0"),
) -> Situation:
    """Única fuente del cálculo (el frontend tiene un espejo en `src/lib/grading.js`, mismos casos de test).

    `condition` = condición por asistencia; None = desconocida (sin clases registradas), no cambia el estado.
    """
    p1 = p1 if p1 is not None and p1.loaded else None
    p2 = p2 if p2 is not None and p2.loaded else None
    recup = recup if recup is not None and recup.loaded else None
    final = final if final is not None and final.loaded else None
    p1e = p1.grade if p1 else None
    p2e = p2.grade if p2 else None

    def result(
        status: AcademicStatus,
        *,
        recovers: str | None = None,
        cursada: Decimal | None = None,
        final_grade: Decimal | None = None,
    ) -> Situation:
        if condition == Condition.LIBRE:
            status, final_grade = AcademicStatus.LIBRE, None
        return Situation(
            p1_effective=p1e,
            p2_effective=p2e,
            recovers=recovers,
            cursada_grade=None if cursada is None else _trunc(cursada),
            final_grade=None if final_grade is None else _trunc(final_grade),
            status=status,
            recup_enabled=recovers is not None,
            final_enabled=cursada is not None,
        )

    if p1 is None or p2 is None:
        return result(AcademicStatus.CURSANDO)
    ok1, ok2 = _passed(p1, passing_grade), _passed(p2, passing_grade)
    if not ok1 and not ok2:
        return result(AcademicStatus.RECURSA)
    if not (ok1 and ok2):
        recovers = SLOT_P1 if not ok1 else SLOT_P2
        if recup is None:
            owes = (
                AcademicStatus.DEBE_RECUPERAR_P1 if recovers == SLOT_P1 else AcademicStatus.DEBE_RECUPERAR_P2
            )
            return result(owes, recovers=recovers)
        if not _passed(recup, passing_grade):
            return result(AcademicStatus.RECURSA, recovers=recovers)
        if recovers == SLOT_P1:
            p1e = recup.grade
        else:
            p2e = recup.grade
    else:
        recovers = None  # ambos aprobados: el recuperatorio no sirve para levantar nota (se ignora)
    if p1e is None or p2e is None:  # no pasa: aprobado implica nota numérica (narrowing para mypy)
        return result(AcademicStatus.CURSANDO)
    cursada = (p1e + p2e) / 2
    if final is None or final.absent or final.grade is None:
        return result(AcademicStatus.PENDIENTE_FINAL, recovers=recovers, cursada=cursada)
    if final.grade < passing_grade:
        return result(AcademicStatus.FINAL_DESAPROBADO, recovers=recovers, cursada=cursada)
    subject = (cursada + final.grade) / 2
    return result(AcademicStatus.APROBADA, recovers=recovers, cursada=cursada, final_grade=subject)


def situation_from_marks(
    marks: Iterable[tuple[str, Mark]],
    *,
    final_types: Iterable[str] = ("FINAL",),
    condition: str | None = None,
    passing_grade: Decimal = Decimal("4.0"),
) -> Situation:
    """`marks` = (tipo de examen, calificación) de exámenes NO cancelados de un alumno."""
    slots: dict[str, Mark] = {}
    for tipo, m in marks:
        slot = exam_slot(tipo, final_types)
        if slot is not None and m.loaded and slot not in slots:
            slots[slot] = m
    return academic_situation(
        slots.get(SLOT_P1),
        slots.get(SLOT_P2),
        slots.get(SLOT_RECUP),
        slots.get(SLOT_FINAL),
        condition=condition,
        passing_grade=passing_grade,
    )


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
