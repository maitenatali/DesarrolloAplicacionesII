from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import Field, field_validator

from app.constants import ActaStatus, ActaType, Result

from .common import ApiModel, GradeOut, Instant


class ActaCreateRequest(ApiModel):
    course_id: int
    type: ActaType
    exam_id: int | None = None
    notes: str | None = None


class AnnulRequest(ApiModel):
    reason: Annotated[str, Field(min_length=10, max_length=1000)]

    @field_validator("reason")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("El motivo debe tener al menos 10 caracteres.")
        return v


class ActaSync(ApiModel):
    ok: int
    error: int
    last_attempt_at: Instant | None = None


class ActaCounts(ApiModel):
    approved: int
    failed: int
    absent: int
    regular: int
    free: int


class ActaRow(ApiModel):
    order: int
    student_id: str
    student_name: str
    student_file_number: str
    grade: GradeOut | None = None
    result: Result


class ActaSummaryDto(ApiModel):
    id: int
    number: str
    type: ActaType
    status: ActaStatus
    course_id: int
    subject_id: int
    period_id: int
    exam_id: int | None = None
    subject: str
    commission: str
    period: str
    teacher_id: str
    teacher_name: str
    date: dt.date
    notes: str | None = None
    generated_at: Instant
    annulled_at: Instant | None = None
    annulment_reason: str | None = None
    sync: ActaSync
    counts: ActaCounts


class ActaDto(ActaSummaryDto):
    rows: list[ActaRow]


class ActaCreatedDto(ActaDto):
    warnings: list[str] = []


class ActaPage(ApiModel):
    items: list[ActaSummaryDto]
    total: int
    limit: int
    offset: int


class ActaQuery(ApiModel):
    course_id: int | None = None
    period_id: int | None = None
    type: ActaType | None = None
    status: ActaStatus | None = None
    limit: Annotated[int, Field(ge=1, le=200)] = 50
    offset: Annotated[int, Field(ge=0)] = 0


class SyncResponse(ApiModel):
    sync: ActaSync
