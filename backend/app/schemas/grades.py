from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import Field

from app.constants import ExamPhase

from .common import ApiModel, GradeIn, GradeOut, Instant


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


class MatrixRow(ApiModel):
    student_id: str
    student_name: str
    file_number: str
    grades: dict[str, MatrixCell]
    average: GradeOut | None = None


class GradeMatrix(ApiModel):
    exams: list[MatrixExam]
    rows: list[MatrixRow]
