from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from app.errors import StudentDirectoryUnavailable, UpstreamError

from .base import StudentDirectoryClient, StudentProfile
from .http import HttpClient


class StudentDirectoryLive(StudentDirectoryClient):
    """Backoffice user directory (module 8): GET {BACKOFFICE}/api/v1/users/{userId}, service token.

    Response: {userId, email, firstName, lastName, documentId, fileNumber, roles, status, siteId, careerId}.
    Backoffice has no batch-by-ids endpoint, so ids are fetched in parallel; 404 = unknown id (absent).
    """

    def __init__(self, http: HttpClient, concurrency: int = 6):
        self.http = http
        self.concurrency = concurrency

    def _one(self, sid: str) -> StudentProfile | None:
        resp = self.http.request("GET", f"/api/v1/users/{sid}", template="/api/v1/users/{userId}")
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise StudentDirectoryUnavailable()
        p = resp.json() or {}
        first, last = p.get("firstName") or "", p.get("lastName") or ""
        return StudentProfile(
            student_id=str(p.get("userId") or sid),
            first_name=first,
            last_name=last,
            full_name=f"{first} {last}".strip() or sid,
            document=p.get("documentId"),
            file_number=str(p.get("fileNumber") or "S/D"),
            email=p.get("email"),
        )

    def get_profiles(self, student_ids: Sequence[str]) -> dict[str, StudentProfile]:
        ids = list(dict.fromkeys(student_ids))
        if not ids:
            return {}
        try:
            with ThreadPoolExecutor(max_workers=min(self.concurrency, len(ids))) as pool:
                found = list(pool.map(self._one, ids))
        except UpstreamError as e:
            raise StudentDirectoryUnavailable() from e
        return {p.student_id: p for p in found if p is not None}
