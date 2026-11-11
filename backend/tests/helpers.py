from __future__ import annotations

SERVICE_TOKEN = "svc-token-1"


def as_teacher(user: str = "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034") -> dict[str, str]:
    return {"X-Dev-User": user}


def as_other_teacher() -> dict[str, str]:
    return {"X-Dev-User": "99999999-9999-4999-8999-999999999999"}


def as_service() -> dict[str, str]:
    return {"Authorization": f"Bearer {SERVICE_TOKEN}"}


def as_admin() -> dict[str, str]:
    return {"X-Dev-User": "a0000000-0000-4000-8000-000000000001", "X-Dev-Roles": "ACADEMIC_ADMIN"}


ROSTER_42 = [
    "ba310c57-a684-4dbf-a4a4-905fcfbefa08",
    "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57",
    "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58",
]


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
