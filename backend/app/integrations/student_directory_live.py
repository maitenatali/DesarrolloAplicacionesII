from __future__ import annotations

from collections.abc import Sequence

from app.errors import StudentDirectoryUnavailable, UpstreamError

from .base import StudentDirectoryClient, StudentProfile
from .http import HttpClient


class StudentDirectoryLive(StudentDirectoryClient):
    """TODO(directory owner): endpoint and DTO are [OPEN]; this assumes GET /students?ids=a,b -> [profile]."""

    def __init__(self, http: HttpClient):
        self.http = http

    def get_profiles(self, student_ids: Sequence[str]) -> dict[str, StudentProfile]:
        if not student_ids:
            return {}
        try:
            resp = self.http.request(
                "GET", "/students", params={"ids": ",".join(student_ids)}, template="/students"
            )
        except UpstreamError as e:
            raise StudentDirectoryUnavailable() from e
        if resp.status_code >= 400:
            raise StudentDirectoryUnavailable()
        out: dict[str, StudentProfile] = {}
        for p in resp.json() or []:
            sid = str(p.get("studentId") or p.get("alumnoId") or p.get("id"))
            first = p.get("firstName") or p.get("nombre") or ""
            last = p.get("lastName") or p.get("apellido") or ""
            out[sid] = StudentProfile(
                student_id=sid,
                first_name=first,
                last_name=last,
                full_name=p.get("fullName") or f"{first} {last}".strip() or sid,
                document=p.get("document") or p.get("dni"),
                file_number=str(p.get("fileNumber") or p.get("legajo") or "S/D"),
                email=p.get("email"),
            )
        return out
