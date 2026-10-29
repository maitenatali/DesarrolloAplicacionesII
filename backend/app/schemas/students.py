"""Per-student views of one course, for the Student Portal (attendance and grades of a single student)."""

from __future__ import annotations

import datetime as dt

from app.constants import AttendanceStatus, Condition, ExamPhase, ExamStatus

from .common import ApiModel, GradeOut, Instant, Pct


class StudentClassAttendance(ApiModel):
    date: dt.date
    status: AttendanceStatus | None = None  # null = class recorded but this student was not marked
    note: str | None = None


class StudentAttendanceDto(ApiModel):
    student_id: str
    course_id: int
    threshold: Pct
    classes_recorded: int
    present: int
    justified: int
    absences: int
    attendance_percentage: Pct
    condition: Condition
    classes: list[StudentClassAttendance]


class StudentExamGrade(ApiModel):
    exam_id: int
    type: str
    name: str
    category: str | None = None  # from GET /exam-types; null when the type is not in the catalog
    date: dt.date
    status: ExamStatus
    phase: ExamPhase
    grade: GradeOut | None = None
    absent: bool
    passed: bool | None = None  # grade >= passingGrade; null without a numeric grade
    graded_at: Instant | None = None
    graded_by: str | None = None


class StudentGradesDto(ApiModel):
    student_id: str
    course_id: int
    passing_grade: GradeOut
    average: GradeOut | None = None
    exams: list[StudentExamGrade]
