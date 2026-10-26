from __future__ import annotations

import datetime as dt
import re
from typing import Annotated

from pydantic import Field, RootModel, field_validator

from app.constants import ExamPhase, ExamStatus, Modality

from .common import ApiModel, HHmm, Instant

_TYPE_RE = re.compile(r"^[A-Z0-9_]{1,50}$")


def normalize_exam_type(value: str) -> str:
    v = re.sub(r"[\s\-]+", "_", value.strip().upper())
    if not _TYPE_RE.match(v):
        raise ValueError("El tipo solo admite letras, números y guiones bajos (máx. 50).")
    return v


class ExamCreateRequest(ApiModel):
    type: str
    name: Annotated[str, Field(max_length=100)] | None = None
    description: Annotated[str, Field(max_length=500)] | None = None
    date: dt.date
    start_time: dt.time
    duration_minutes: Annotated[int, Field(ge=1, le=600)]
    modality: Modality

    @field_validator("type")
    @classmethod
    def _norm(cls, v: str) -> str:
        return normalize_exam_type(v)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None


class ExamPatchRequest(ApiModel):
    type: str | None = None
    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    description: Annotated[str, Field(max_length=500)] | None = None
    date: dt.date | None = None
    start_time: dt.time | None = None
    duration_minutes: Annotated[int, Field(ge=1, le=600)] | None = None
    modality: Modality | None = None

    @field_validator("type")
    @classmethod
    def _norm(cls, v: str | None) -> str | None:
        return normalize_exam_type(v) if v is not None else None


class CancelRequest(ApiModel):
    reason: Annotated[str, Field(max_length=500)] | None = None


class ExamDto(ApiModel):
    id: int
    course_id: int
    type: str
    name: str
    description: str | None = None
    date: dt.date
    start_time: HHmm
    duration_minutes: int
    end_time: HHmm
    modality: Modality
    status: ExamStatus
    phase: ExamPhase
    graded_count: int
    created_at: Instant
    updated_at: Instant


class ExamList(RootModel[list[ExamDto]]):
    pass


class GradingProgress(ApiModel):
    enrolled: int
    graded: int
    absent: int
    pending: int


class ExamDetailDto(ExamDto):
    grading_progress: GradingProgress


class CourseRef(ApiModel):
    id: int
    code: str
    subject_name: str


class ExamWithCourseDto(ExamDto):
    course: CourseRef


class ExamWithCourseList(RootModel[list[ExamWithCourseDto]]):
    pass


class ExamQuery(ApiModel):
    from_: dt.date | None = Field(default=None, alias="from")
    to: dt.date | None = None
    phase: ExamPhase | None = None
    include_cancelled: bool = False
    limit: Annotated[int, Field(ge=1, le=50)] | None = None
