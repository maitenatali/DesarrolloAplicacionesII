from __future__ import annotations

import datetime as dt

from pydantic import RootModel

from .common import ApiModel, GradeOut, HHmm, Pct


class MeDto(ApiModel):
    user_id: str
    email: str | None = None
    roles: list[str]
    permissions: list[str] = []
    teacher_ids: list[str]
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    file_number: str | None = None


class PeriodDto(ApiModel):
    id: int
    year: int
    number: int
    label: str
    start_date: dt.date
    end_date: dt.date
    enrollment_from: dt.date | None = None
    enrollment_until: dt.date | None = None


class PeriodList(RootModel[list[PeriodDto]]):
    pass


class ExamTurnDto(ApiModel):
    id: int
    name: str
    start_date: dt.date
    end_date: dt.date
    enrollment_from: dt.date
    enrollment_until: dt.date


class ExamTurnList(RootModel[list[ExamTurnDto]]):
    pass


class SubjectDto(ApiModel):
    id: int
    code: str
    name: str


class ScheduleDto(ApiModel):
    room_id: int | None = None
    weekday: str
    start_time: HHmm
    end_time: HHmm


class TeacherDto(ApiModel):
    teacher_id: str
    role: str


class CourseDto(ApiModel):
    id: int
    code: str
    subject: SubjectDto
    period: PeriodDto
    campus_id: int | None = None
    modality: str
    status: str
    max_seats: int
    enrolled: int
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    schedule: list[ScheduleDto]
    teachers: list[TeacherDto]


class CourseList(RootModel[list[CourseDto]]):
    pass


class StudentProfileDto(ApiModel):
    first_name: str
    last_name: str
    full_name: str
    document: str | None = None
    file_number: str
    email: str | None = None


class AttendanceStatsDto(ApiModel):
    classes_recorded: int
    present: int
    justified: int
    absences: int
    attendance_percentage: Pct
    condition: str


class FinalResultDto(ApiModel):
    grade: GradeOut | None = None
    result: str
    acta_number: str
    date: dt.date


class RosterStudentDto(ApiModel):
    student_id: str
    profile: StudentProfileDto | None = None
    enrollment_status: str
    attendance: AttendanceStatsDto | None = None
    final_result: FinalResultDto | None = None


class RosterList(RootModel[list[RosterStudentDto]]):
    pass


class PrerequisiteDto(ApiModel):
    id: int
    prerequisite_subject_id: int
    kind: str


class PrerequisiteList(RootModel[list[PrerequisiteDto]]):
    pass


class ExamTypeDto(ApiModel):
    type: str
    name: str
    category: str


class ExamTypeList(RootModel[list[ExamTypeDto]]):
    pass


class PeriodQuery(ApiModel):
    period_id: int | None = None
