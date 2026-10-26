from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import Field, RootModel

from app.constants import AttendanceStatus, Condition

from .common import ApiModel, Instant, Pct


class AttendanceRecord(ApiModel):
    student_id: Annotated[str, Field(min_length=1, max_length=50)]
    status: AttendanceStatus
    note: Annotated[str, Field(max_length=255)] | None = None


class AttendancePutRequest(ApiModel):
    notes: str | None = None
    records: Annotated[list[AttendanceRecord], Field(min_length=1, max_length=1000)]


class AttendanceDto(ApiModel):
    date: dt.date
    notes: str | None = None
    records: list[AttendanceRecord]


class AttendanceListItem(ApiModel):
    date: dt.date
    notes: str | None = None
    total: int
    present: int
    absent: int
    justified: int
    updated_at: Instant


class AttendanceList(RootModel[list[AttendanceListItem]]):
    pass


class StudentAttendanceSummary(ApiModel):
    student_id: str
    classes_recorded: int
    present: int
    justified: int
    absences: int
    attendance_percentage: Pct
    condition: Condition


class AttendanceSummaryDto(ApiModel):
    threshold: Pct
    students: list[StudentAttendanceSummary]
