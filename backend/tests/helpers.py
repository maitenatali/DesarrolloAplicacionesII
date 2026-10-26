from __future__ import annotations

SERVICE_TOKEN = "svc-token-1"


def as_teacher(user: str = "docente-123") -> dict[str, str]:
    return {"X-Dev-User": user}


def as_other_teacher() -> dict[str, str]:
    return {"X-Dev-User": "docente-999"}


def as_service() -> dict[str, str]:
    return {"Authorization": f"Bearer {SERVICE_TOKEN}"}


def as_admin() -> dict[str, str]:
    return {"X-Dev-User": "admin-1", "X-Dev-Roles": "ROLE_ADMINISTRATIVO"}


ROSTER_42 = ["alumno-456", "alumno-457", "alumno-458"]


def attendance_body(marks: dict[str, str] | None = None, notes: str | None = None) -> dict:
    marks = marks or {sid: "PRESENTE" for sid in ROSTER_42}
    return {"notes": notes, "records": [{"studentId": s, "status": st} for s, st in marks.items()]}


def exam_body(**over) -> dict:
    body = {
        "type": "parcial_2",
        "name": "Segundo Parcial",
        "date": "2026-10-25",
        "startTime": "18:00",
        "durationMinutes": 120,
        "modality": "PRESENCIAL",
    }
    body.update(over)
    return body
