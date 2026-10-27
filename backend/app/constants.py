"""Domain constants. Event types follow CORE naming `source.entity-action.v1` (see CORE /docs) and must be
registered in CORE's catalog before going live - single edit point."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from types import SimpleNamespace


class AttendanceStatus(StrEnum):
    PRESENTE = "PRESENTE"
    AUSENTE = "AUSENTE"
    JUSTIFICADO = "JUSTIFICADO"


class Condition(StrEnum):
    REGULAR = "REGULAR"
    LIBRE = "LIBRE"


class Modality(StrEnum):
    PRESENCIAL = "PRESENCIAL"
    VIRTUAL = "VIRTUAL"


class ExamStatus(StrEnum):
    PROGRAMADO = "PROGRAMADO"
    CANCELADO = "CANCELADO"


class ExamPhase(StrEnum):
    UPCOMING = "UPCOMING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ActaType(StrEnum):
    CURSADA = "CURSADA"
    FINAL = "FINAL"


class ActaStatus(StrEnum):
    GENERADA = "GENERADA"
    ANULADA = "ANULADA"


class Result(StrEnum):
    APROBADO = "APROBADO"
    DESAPROBADO = "DESAPROBADO"
    REGULAR = "REGULAR"
    LIBRE = "LIBRE"
    AUSENTE = "AUSENTE"


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


COURSE_CANCELLED_STATUS = "CANCELADO"
ENROLLMENT_DROPPED_STATUS = "BAJA"

# Defaults; the effective values come from Settings (env).
PASSING_GRADE = Decimal("4.0")
REGULAR_THRESHOLD = Decimal("75.0")

EVENT_TYPES = SimpleNamespace(
    attendance_recorded="teacher.attendance-recorded.v1",
    grade_published="teacher.grade-published.v1",
    exam_created="teacher.exam-created.v1",
    acta_generated="teacher.acta-generated.v1",
    acta_annulled="teacher.acta-annulled.v1",
    course_result_published="teacher.course-result-published.v1",
)

EXAM_TYPE_CATALOG = [
    {"type": "PARCIAL_1", "name": "Parcial 1", "category": "PARCIAL"},
    {"type": "PARCIAL_2", "name": "Parcial 2", "category": "PARCIAL"},
    {"type": "RECUP_1", "name": "Recuperatorio Parcial 1", "category": "RECUPERATORIO"},
    {"type": "RECUP_2", "name": "Recuperatorio Parcial 2", "category": "RECUPERATORIO"},
    {"type": "TP_1", "name": "TP1", "category": "INTEGRADOR"},
    {"type": "TP_2", "name": "TP2", "category": "INTEGRADOR"},
    {"type": "FINAL", "name": "Final", "category": "FINAL"},
]

DEGRADED_HEADER = "X-Degraded"
MISSING_FILE_NUMBER = "S/D"
