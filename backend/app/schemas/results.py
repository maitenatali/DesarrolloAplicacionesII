from __future__ import annotations

import datetime as dt

from pydantic import RootModel

from .common import ApiModel, GradeOut


class ResultDto(ApiModel):
    student_id: str
    course_id: int
    subject_id: int
    period_id: int
    subject: str
    commission: str
    period: str
    grade: GradeOut | None = None
    result: str
    acta_type: str
    acta_number: str
    result_date: dt.date


class ResultList(RootModel[list[ResultDto]]):
    pass


class ResultQuery(ApiModel):
    course_id: int | None = None
