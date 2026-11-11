"""Demo dataset (MOCK_DATASET=demo): realistic volume for showing the portal. Tests keep using `fixtures`.

Same ids as `fixtures` for teachers, courses 42/43/44/30 and the Appendix B students, so logins and URLs
do not change between datasets. Only the GA/Backoffice side lives here; `app/seed_demo.py` writes the
teacher-service rows (classes, attendance, exams, grades, actas) that match it.
"""

from __future__ import annotations

import unicodedata
from dataclasses import replace
from datetime import date, time
from decimal import Decimal

from .base import (
    CourseDetail,
    CourseSummary,
    Enrollment,
    ExamTurn,
    Schedule,
    StudentProfile,
    Subject,
    TeacherAssignment,
)
from .fixtures import (
    COURSE_44,
    EXAM_TURN_7,
    PERIOD_7,
    PERIOD_8,
    PERIODS,
    PREREQS_15,
    SUBJECT_15,
    SUBJECT_16,
    TEACHER_NAME,
    TEACHER_PROFILES,
)
from .fixtures import PROFILES as _BASE_PROFILES

MARIA = "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
CARLOS = "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b34"
JUAN = "ba310c57-a684-4dbf-a4a4-905fcfbefa08"
LUCAS = "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57"
ANA = "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58"

_NAMES_42 = [
    ("Sofía", "Martínez"), ("Mateo", "González"), ("Valentina", "López"), ("Santiago", "Romero"),
    ("Camila", "Sosa"), ("Benjamín", "Álvarez"), ("Martina", "Torres"), ("Tomás", "Ruiz"),
    ("Lucía", "Ramírez"), ("Joaquín", "Flores"), ("Emilia", "Benítez"), ("Facundo", "Acosta"),
    ("Florencia", "Medina"), ("Nicolás", "Herrera"), ("Agustina", "Aguirre"), ("Franco", "Pereyra"),
    ("Micaela", "Gutiérrez"), ("Ignacio", "Giménez"), ("Julieta", "Molina"), ("Lautaro", "Silva"),
    ("Catalina", "Castro"), ("Thiago", "Rojas"),
]  # fmt: skip
_NAMES_43 = [
    ("Delfina", "Ortiz"), ("Bautista", "Núñez"), ("Renata", "Luna"), ("Felipe", "Cabrera"),
    ("Abril", "Ríos"), ("Gonzalo", "Morales"), ("Paula", "Domínguez"), ("Maximiliano", "Vega"),
    ("Rocío", "Ferreyra"), ("Ezequiel", "Godoy"), ("Milagros", "Peralta"), ("Federico", "Correa"),
    ("Antonella", "Quiroga"), ("Matías", "Vera"), ("Carolina", "Paz"), ("Leandro", "Figueroa"),
    ("Brenda", "Cáceres"), ("Damián", "Ledesma"), ("Josefina", "Ibarra"), ("Alejo", "Navarro"),
]  # fmt: skip


def _profile(sid: str, first: str, last: str, document: str, legajo: str) -> StudentProfile:
    plain = "".join(
        c for c in unicodedata.normalize("NFD", f"{first}.{last}") if unicodedata.category(c) != "Mn"
    )
    email = plain.lower() + "@uade.edu.ar"
    return StudentProfile(sid, first, last, f"{first} {last}", document, legajo, email)


PROFILES: dict[str, StudentProfile] = {sid: _BASE_PROFILES[sid] for sid in (JUAN, LUCAS, ANA)}
IDS_42 = [JUAN, LUCAS, ANA]
for _i, (_first, _last) in enumerate(_NAMES_42, start=1):
    _sid = f"00000000-0000-4000-b000-{300 + _i:012d}"
    PROFILES[_sid] = _profile(_sid, _first, _last, str(44210000 + 137 * _i), str(124100 + 7 * _i))
    IDS_42.append(_sid)
# Course 43 keeps the base ids 00000000-0000-4000-a000-000000000101..120 (tests/URLs), with real names.
IDS_43 = []
for _i, (_first, _last) in enumerate(_NAMES_43, start=1):
    _sid = f"00000000-0000-4000-a000-{100 + _i:012d}"
    PROFILES[_sid] = _profile(_sid, _first, _last, str(43870000 + 211 * _i), str(200000 + _i))
    IDS_43.append(_sid)
PROFILES.update(TEACHER_PROFILES)

# Course 30 (1Q 2026, closed). Enrollment as GA recorded it after both actas synced (status, final grade).
# CURSADA sent REGULAR/LIBRE; FINAL sent APROBADO/DESAPROBADO/LIBRE (AUSENTE is not sent, so it stays REGULAR).
# `app/seed_demo.py` derives attendance and grades from this table, so the actas reproduce it exactly.
IDS_30 = [JUAN, LUCAS, *IDS_42[3:13], *IDS_43[:4]]
COURSE_30_OUTCOMES: dict[str, tuple[str, Decimal | None]] = {
    JUAN: ("APROBADO", Decimal("9.00")),
    LUCAS: ("DESAPROBADO", Decimal("3.00")),
    IDS_42[3]: ("APROBADO", Decimal("8.00")),  # Sofía: the annulled acta had a typo (3.00) for her
    IDS_42[4]: ("APROBADO", Decimal("7.00")),
    IDS_42[5]: ("APROBADO", Decimal("6.00")),
    IDS_42[6]: ("APROBADO", Decimal("10.00")),
    IDS_42[7]: ("REGULAR", None),  # regular, absent at the final
    IDS_42[8]: ("APROBADO", Decimal("4.00")),
    IDS_42[9]: ("LIBRE", Decimal("6.00")),  # attendance < 75 %; sat the final anyway -> LIBRE
    IDS_42[10]: ("APROBADO", Decimal("7.50")),
    IDS_42[11]: ("DESAPROBADO", Decimal("2.00")),
    IDS_42[12]: ("APROBADO", Decimal("8.50")),
    IDS_43[0]: ("APROBADO", Decimal("6.50")),
    IDS_43[1]: ("LIBRE", None),  # attendance < 75 %, did not sit the final
    IDS_43[2]: ("APROBADO", Decimal("9.50")),
    IDS_43[3]: ("REGULAR", None),  # regular, absent at the final
}
COURSE_30_RESULT_DATE = date(2026, 7, 13)


def _enrollments(first_id: int, ids: list[str]) -> list[Enrollment]:
    return [
        Enrollment(first_id + n, sid, date(2026, 7, 15), "CURSANDO", None, None) for n, sid in enumerate(ids)
    ]


COURSE_42 = CourseDetail(
    course=CourseSummary(
        42,
        "DDA2-A",
        15,
        8,
        2,
        "PRESENCIAL",
        "EN_CURSO",
        45,
        date(2026, 8, 10),
        date(2026, 11, 30),
        len(IDS_42),
    ),
    subject=SUBJECT_15,
    period=PERIOD_8,
    teachers=[TeacherAssignment(3, MARIA, "TITULAR")],
    enrollments=_enrollments(71, IDS_42),
    schedule=[Schedule(9, 4, "MONDAY", time(18, 0), time(20, 0))],
)
COURSE_43 = CourseDetail(
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
        len(IDS_43),
    ),
    subject=SUBJECT_15,
    period=PERIOD_8,
    teachers=[TeacherAssignment(4, CARLOS, "TITULAR")],
    enrollments=_enrollments(200, IDS_43),
    schedule=[Schedule(10, 5, "TUESDAY", time(19, 0), time(21, 0))],
)
COURSE_30 = CourseDetail(
    course=CourseSummary(
        30,
        "BD1-B",
        16,
        7,
        1,
        "PRESENCIAL",
        "FINALIZADO",
        30,
        date(2026, 3, 10),
        date(2026, 7, 15),
        len(IDS_30),
    ),
    subject=SUBJECT_16,
    period=PERIOD_7,
    teachers=[TeacherAssignment(6, MARIA, "ADJUNTO")],
    enrollments=[
        replace(
            e,
            status=COURSE_30_OUTCOMES[e.student_id][0],
            final_grade=COURSE_30_OUTCOMES[e.student_id][1],
            result_date=COURSE_30_RESULT_DATE,
        )
        for e in _enrollments(300, IDS_30)
    ],
    schedule=[Schedule(11, 2, "FRIDAY", time(8, 0), time(10, 0))],
)

# --- María's 3 extra demo courses (2Q 2026) -------------------------------------------------------------
# 45: ready to close (everything loaded, NO cursada acta yet: the demo generates it live).
# 46: mid-semester.  47: just created (enrolled students only).
SUBJECT_17 = Subject(17, "IS2", "Ingeniería de Software II")

_NAMES_45 = [
    ("Pedro", "Salazar"), ("Clara", "Bustos"), ("Hugo", "Méndez"), ("Irene", "Campos"),
    ("Julián", "Arce"), ("Noelia", "Fuentes"), ("Ramiro", "Suárez"), ("Tamara", "Villalba"),
    ("Esteban", "Coronel"), ("Luciana", "Robles"), ("Axel", "Mansilla"), ("Dana", "Escobar"),
]  # fmt: skip
_NAMES_46 = [
    ("Kevin", "Barrios"), ("Ailén", "Maidana"), ("Bruno", "Lescano"), ("Celeste", "Duarte"),
    ("Dylan", "Sandoval"), ("Evelyn", "Montes"), ("Gael", "Pizarro"), ("Hilda", "Bravo"),
    ("Iván", "Zárate"), ("Jazmín", "Olivera"),
]  # fmt: skip
_NAMES_47 = [
    ("Karina", "Soria"), ("Lisandro", "Funes"), ("Mora", "Arias"), ("Nahuel", "Cardozo"),
    ("Olivia", "Bazán"), ("Priscila", "Coria"), ("Quimey", "Rivas"), ("Rodrigo", "Palacios"),
]  # fmt: skip


def _extra_ids(block: int, names: list[tuple[str, str]], doc_base: int, legajo_base: int) -> list[str]:
    ids = []
    for i, (first, last) in enumerate(names, start=1):
        sid = f"00000000-0000-4000-b000-{block + i:012d}"
        PROFILES[sid] = _profile(sid, first, last, str(doc_base + 173 * i), str(legajo_base + 11 * i))
        ids.append(sid)
    return ids


IDS_45 = _extra_ids(400, _NAMES_45, 41230000, 310000)
IDS_46 = _extra_ids(500, _NAMES_46, 42340000, 320000)
IDS_47 = _extra_ids(600, _NAMES_47, 43450000, 330000)


def _maria_course(
    cid: int, code: str, subject: Subject, ids: list[str], first_ref: int, weekday: str, start: time, end: time,
    first_day: date, seats: int,
) -> CourseDetail:  # fmt: skip
    return CourseDetail(
        course=CourseSummary(
            cid,
            code,
            subject.id,
            8,
            2,
            "PRESENCIAL",
            "EN_CURSO",
            seats,
            first_day,
            date(2026, 11, 30),
            len(ids),
        ),
        subject=subject,
        period=PERIOD_8,
        teachers=[TeacherAssignment(cid - 38, MARIA, "TITULAR")],
        enrollments=_enrollments(first_ref, ids),
        schedule=[Schedule(cid - 33, 4, weekday, start, end)],
    )


COURSE_45 = _maria_course(
    45, "BD1-C", SUBJECT_16, IDS_45, 400, "WEDNESDAY", time(18), time(20), date(2026, 8, 10), 30
)
COURSE_46 = _maria_course(
    46, "DDA2-C", SUBJECT_15, IDS_46, 500, "THURSDAY", time(19), time(21), date(2026, 8, 10), 45
)
COURSE_47 = _maria_course(
    47, "IS2-A", SUBJECT_17, IDS_47, 600, "FRIDAY", time(18), time(20), date(2026, 11, 6), 35
)

ALL_COURSES = [COURSE_42, COURSE_43, COURSE_44, COURSE_30, COURSE_45, COURSE_46, COURSE_47]

EXAM_TURN_6 = ExamTurn(
    6, "Turno final julio", date(2026, 7, 6), date(2026, 7, 17), date(2026, 6, 22), date(2026, 7, 3)
)
EXAM_TURNS = [EXAM_TURN_6, EXAM_TURN_7]

__all__ = [
    "ALL_COURSES",
    "COURSE_30_OUTCOMES",
    "EXAM_TURNS",
    "PERIODS",
    "PREREQS_15",
    "PROFILES",
    "TEACHER_NAME",
    "TEACHER_PROFILES",
]
