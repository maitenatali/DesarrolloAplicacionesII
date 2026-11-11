from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field

from app.constants import AcademicStatus, Condition, ExamPhase

from .common import ApiModel, GradeIn, GradeOut, Instant

if TYPE_CHECKING:
    from app.services.rules import Situation


class GradeEntry(ApiModel):
    student_id: Annotated[str, Field(min_length=1, max_length=50)]
    grade: GradeIn | None = None
    absent: bool = False


class GradesUpsertRequest(ApiModel):
    entries: Annotated[list[GradeEntry], Field(min_length=1, max_length=500)]


class GradeEntryOut(ApiModel):
    student_id: str
    student_name: str
    file_number: str
    grade: GradeOut | None = None
    absent: bool
    graded_at: Instant | None = None
    graded_by: str | None = None


class GradesSummary(ApiModel):
    enrolled: int
    graded: int
    absent: int
    pending: int
    average: GradeOut | None = None
    passed: int
    failed: int


class GradesResponse(ApiModel):
    exam_id: int
    entries: list[GradeEntryOut]
    summary: GradesSummary


class SavedGradeEntry(ApiModel):
    student_id: str
    grade: GradeOut | None = None
    absent: bool


class GradesUpsertResponse(ApiModel):
    saved: int
    cleared: int
    entries: list[SavedGradeEntry]


class MatrixExam(ApiModel):
    id: int
    type: str
    name: str
    date: dt.date
    phase: ExamPhase


class MatrixCell(ApiModel):
    grade: GradeOut | None = None
    absent: bool


class AcademicSituationDto(ApiModel):
    """Situación del alumno (régimen de Examen Final Obligatorio). Notas truncadas a 2 decimales."""

    p1_effective: GradeOut | None = None  # P1 o, si lo recuperó, la nota del recuperatorio
    p2_effective: GradeOut | None = None
    recovers: Literal["P1", "P2"] | None = None  # a qué parcial aplica el recuperatorio de este alumno
    cursada_grade: GradeOut | None = None  # (P1 ef. + P2 ef.) / 2; null si la cursada no está aprobada
    final_grade: GradeOut | None = None  # (cursada + final) / 2; null salvo APROBADA
    status: AcademicStatus
    recup_enabled: bool  # se puede cargar el recuperatorio
    final_enabled: bool  # se puede cargar el final (cursada aprobada)

    @classmethod
    def of(cls, s: Situation) -> AcademicSituationDto:
        return cls(
            p1_effective=s.p1_effective,
            p2_effective=s.p2_effective,
            recovers=s.recovers,  # type: ignore[arg-type]
            cursada_grade=s.cursada_grade,
            final_grade=s.final_grade,
            status=s.status,
            recup_enabled=s.recup_enabled,
            final_enabled=s.final_enabled,
        )


class MatrixRow(ApiModel):
    student_id: str
    student_name: str
    file_number: str
    grades: dict[str, MatrixCell]
    average: GradeOut | None = None  # = situation.cursadaGrade (se mantiene por compatibilidad)
    condition: Condition | None = None  # por asistencia; null = sin clases registradas
    situation: AcademicSituationDto


class GradeMatrix(ApiModel):
    exams: list[MatrixExam]
    rows: list[MatrixRow]
