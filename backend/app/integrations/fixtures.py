"""Mock data (design Appendix B). Ids match db/seed.sql and the GA contract examples."""

from __future__ import annotations

from datetime import date, time

from .base import (
    CourseDetail,
    CourseSummary,
    Enrollment,
    ExamTurn,
    Period,
    Prerequisite,
    Schedule,
    StudentProfile,
    Subject,
    TeacherAssignment,
)

PERIOD_7 = Period(
    id=7,
    year=2026,
    number=1,
    start=date(2026, 3, 1),
    end=date(2026, 7, 15),
    enroll_from=date(2026, 2, 1),
    enroll_until=date(2026, 2, 28),
)
PERIOD_8 = Period(
    id=8,
    year=2026,
    number=2,
    start=date(2026, 8, 1),
    end=date(2026, 11, 30),
    enroll_from=date(2026, 7, 1),
    enroll_until=date(2026, 7, 31),
)

SUBJECT_15 = Subject(15, "DDA2", "Desarrollo de Aplicaciones II")
SUBJECT_16 = Subject(16, "BD1", "Bases de Datos I")


def _enr(i: int, sid: str, status: str = "CURSANDO") -> Enrollment:
    return Enrollment(i, sid, date(2026, 7, 15), status, None, None)


COURSE_42 = CourseDetail(
    course=CourseSummary(
        id=42,
        code="DDA2-A",
        subject_id=15,
        period_id=8,
        campus_id=2,
        modality="PRESENCIAL",
        status="EN_CURSO",
        max_seats=45,
        start=date(2026, 8, 10),
        end=date(2026, 11, 30),
        active_enrolled=3,
    ),
    subject=SUBJECT_15,
    period=PERIOD_8,
    teachers=[TeacherAssignment(3, "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "TITULAR")],
    enrollments=[
        _enr(71, "ba310c57-a684-4dbf-a4a4-905fcfbefa08"),
        _enr(72, "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57"),
        _enr(73, "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58"),
    ],
    schedule=[Schedule(9, 4, "MONDAY", time(18, 0), time(20, 0))],
)

# Extra volume: students 00000000-0000-4000-a000-000000000101..120 (frontend scheme alumno-{100+i}).
_EXTRA_IDS = [f"00000000-0000-4000-a000-{100 + i:012d}" for i in range(1, 21)]

COURSE_43 = CourseDetail(  # another teacher
    course=CourseSummary(
        43,
        "DDA2-B",
        15,
        8,
        2,
        "PRESENCIAL",
        "EN_CURSO",
        45,
        date(2026, 8, 10),
        date(2026, 11, 30),
        len(_EXTRA_IDS),
    ),
    subject=SUBJECT_15,
    period=PERIOD_8,
    teachers=[TeacherAssignment(4, "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b34", "TITULAR")],
    enrollments=[_enr(200 + i, sid) for i, sid in enumerate(_EXTRA_IDS)],
    schedule=[Schedule(10, 5, "TUESDAY", time(19, 0), time(21, 0))],
)

COURSE_44 = CourseDetail(  # cancelled course of 5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034
    course=CourseSummary(
        44, "BD1-A", 16, 8, 1, "VIRTUAL", "CANCELADO", 30, date(2026, 8, 10), date(2026, 11, 30), 0
    ),
    subject=SUBJECT_16,
    period=PERIOD_8,
    teachers=[TeacherAssignment(5, "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "TITULAR")],
    enrollments=[],
    schedule=[],
)

COURSE_30 = CourseDetail(  # previous period
    course=CourseSummary(
        30, "BD1-B", 16, 7, 1, "PRESENCIAL", "FINALIZADO", 30, date(2026, 3, 10), date(2026, 7, 15), 2
    ),
    subject=SUBJECT_16,
    period=PERIOD_7,
    teachers=[TeacherAssignment(6, "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "ADJUNTO")],
    enrollments=[
        _enr(300, "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "APROBADO"),
        _enr(301, "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "REGULAR"),
    ],
    schedule=[Schedule(11, 2, "FRIDAY", time(8, 0), time(10, 0))],
)

ALL_COURSES = [COURSE_42, COURSE_43, COURSE_44, COURSE_30]

PROFILES: dict[str, StudentProfile] = {
    "ba310c57-a684-4dbf-a4a4-905fcfbefa08": StudentProfile(
        "ba310c57-a684-4dbf-a4a4-905fcfbefa08",
        "Juan",
        "Pérez",
        "Juan Pérez",
        "40123456",
        "123456",
        "juan.perez@uade.edu.ar",
    ),
    "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57": StudentProfile(
        "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57",
        "Lucas",
        "Fernández",
        "Lucas Fernández",
        "40123458",
        "123458",
        "lucas.fernandez@uade.edu.ar",
    ),
    "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58": StudentProfile(
        "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58",
        "Ana",
        "Rodríguez",
        "Ana Rodríguez",
        "40123459",
        "123459",
        "ana.rodriguez@uade.edu.ar",
    ),
}
for _i, _sid in enumerate(_EXTRA_IDS, start=1):
    PROFILES[_sid] = StudentProfile(
        _sid,
        f"Alumno{_i}",
        f"Apellido{_i:02d}",
        f"Alumno{_i} Apellido{_i:02d}",
        str(41000000 + _i),
        str(200000 + _i),
        f"alumno{_i}@uade.edu.ar",
    )

# Backoffice directory also holds teachers (same endpoint GET /api/v1/users/{userId}).
TEACHER_PROFILES: dict[str, StudentProfile] = {
    "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034": StudentProfile(
        "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034",
        "María",
        "Gómez",
        "María Gómez",
        "28123456",
        "D-1001",
        "maria.gomez@uade.edu.ar",
    ),
    "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b34": StudentProfile(
        "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b34",
        "Carlos",
        "Díaz",
        "Carlos Díaz",
        "27123457",
        "D-1002",
        "carlos.diaz@uade.edu.ar",
    ),
}
PROFILES.update(TEACHER_PROFILES)

EXAM_TURN_7 = ExamTurn(
    7, "Turno final diciembre", date(2026, 12, 1), date(2026, 12, 15), date(2026, 11, 10), date(2026, 11, 25)
)
EXAM_TURNS = [EXAM_TURN_7]
PERIODS = [PERIOD_7, PERIOD_8]
PREREQS_15 = [Prerequisite(5, 15, 12, "APROBADA"), Prerequisite(6, 15, 13, "REGULAR")]
TEACHER_NAME = {
    "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034": "María Gómez",
    "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b34": "Carlos Díaz",
}
