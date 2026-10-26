"""Course ownership (design §8.4)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from flask import current_app

from app.errors import Forbidden
from app.integrations.base import CourseDetail
from app.integrations.factory import get_integrations
from app.security.principal import Principal


@dataclass(frozen=True)
class CourseAccess:
    detail: CourseDetail
    teacher_id: str  # matched GA docenteId (fallback: principal.user_id for admin read flows)


def _is_admin(principal: Principal) -> bool:
    return bool(principal.roles & set(current_app.extensions["settings"].admin_roles))


def teacher_keys(principal: Principal) -> list[str]:
    return principal.docente_keys(current_app.extensions["settings"].docente_id_claims)


def authorize_course(
    principal: Principal, course_id: int, *, write: bool = False, fresh: bool = False
) -> CourseAccess:
    detail = get_integrations().academic.get_course(course_id, fresh=fresh)
    keys = set(teacher_keys(principal))
    matched = [t.teacher_id for t in detail.teachers if t.teacher_id in keys]
    if matched:
        return CourseAccess(detail, matched[0])
    if not write and _is_admin(principal):
        return CourseAccess(detail, principal.user_id)
    raise Forbidden("No estás asignado a este curso.", code="COURSE_NOT_ASSIGNED")


def teacher_name(principal: Principal, teacher_id: str) -> str:
    """Snapshot name: `name` claim -> derived from email (frontend nameFromEmail) -> id. TODO(directory): authoritative."""
    if principal.name:
        return principal.name
    if principal.email and "@" in principal.email:
        local = principal.email.split("@", 1)[0]
        parts = [p for p in re.split(r"[._\-]+", local) if p]
        if parts:
            return " ".join(p.capitalize() for p in parts)
    return teacher_id
