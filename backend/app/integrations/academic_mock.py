from __future__ import annotations

import copy
import logging
from datetime import date
from decimal import Decimal

from app.errors import CourseNotFound, UpstreamError

from . import fixtures
from .base import AcademicClient, CourseDetail, CourseSummary, ExamTurn, Period, Prerequisite

log = logging.getLogger("app.integrations.academic.mock")


class AcademicMock(AcademicClient):
    """In-memory GA. Tests can mutate `courses`, set `down`, or `fail_for`."""

    def __init__(self) -> None:
        self.courses: dict[int, CourseDetail] = {c.course.id: copy.copy(c) for c in fixtures.ALL_COURSES}
        self.periods: list[Period] = [fixtures.PERIOD_7, fixtures.PERIOD_8]
        self.turns: list[ExamTurn] = [fixtures.EXAM_TURN_7]
        self.prerequisites: list[Prerequisite] = list(fixtures.PREREQS_15)
        self.down = False
        self.fail_for: set[str] = set()
        self.updates: list[dict] = []

    def _check(self) -> None:
        if self.down:
            raise UpstreamError("academic", "Gestión Académica no disponible.", status=504)

    def list_periods(self) -> list[Period]:
        self._check()
        return list(self.periods)

    def list_exam_turns(self) -> list[ExamTurn]:
        self._check()
        return list(self.turns)

    def list_courses(self, period_id: int | None = None) -> list[CourseSummary]:
        self._check()
        return [
            c.course for c in self.courses.values() if period_id is None or c.course.period_id == period_id
        ]

    def get_course(self, course_id: int, *, fresh: bool = False) -> CourseDetail:
        self._check()
        try:
            return self.courses[course_id]
        except KeyError:
            raise CourseNotFound(course_id) from None

    def list_courses_for_teacher(
        self, teacher_keys: set[str], period_id: int | None = None
    ) -> list[CourseDetail]:
        self._check()
        return [
            c
            for c in self.courses.values()
            if (period_id is None or c.course.period_id == period_id)
            and any(t.teacher_id in teacher_keys for t in c.teachers)
        ]

    def list_prerequisites(self, subject_id: int) -> list[Prerequisite]:
        self._check()
        return [p for p in self.prerequisites if p.subject_id == subject_id]

    def update_enrollment_result(
        self, course_id: int, student_id: str, *, status: str, final_grade: Decimal | None, result_date: date
    ) -> None:
        self._check()
        if student_id in self.fail_for:
            raise UpstreamError("academic", f"Fallo simulado para {student_id}.")
        self.updates.append(
            {
                "course_id": course_id,
                "student_id": student_id,
                "status": status,
                "final_grade": final_grade,
                "result_date": result_date,
            }
        )
        log.info(
            "mock_update_enrollment", extra={"courseId": course_id, "studentId": student_id, "status": status}
        )
