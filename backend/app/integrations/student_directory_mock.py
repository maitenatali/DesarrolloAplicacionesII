from __future__ import annotations

from collections.abc import Sequence
from types import ModuleType

from app.errors import StudentDirectoryUnavailable

from . import fixtures
from .base import StudentDirectoryClient, StudentProfile


class StudentDirectoryMock(StudentDirectoryClient):
    def __init__(self, data: ModuleType = fixtures) -> None:  # data: fixtures | fixtures_demo
        self.profiles: dict[str, StudentProfile] = dict(data.PROFILES)
        self.down = False

    def get_profiles(self, student_ids: Sequence[str]) -> dict[str, StudentProfile]:
        if self.down:
            raise StudentDirectoryUnavailable()
        return {sid: self.profiles[sid] for sid in student_ids if sid in self.profiles}
