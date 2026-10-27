"""Courses / roster: BFF over Gestión Académica + own attendance and result views (design §10.2-10.5, §11.4)."""

from __future__ import annotations

from dataclasses import dataclass

from flask import current_app
from sqlalchemy import select

from app.constants import EXAM_TYPE_CATALOG, MISSING_FILE_NUMBER
from app.errors import UpstreamError
from app.extensions import db
from app.integrations.base import CourseDetail, Period, StudentProfile, roster_of
from app.integrations.factory import get_integrations
from app.models import AsistenciaPorAlumno, ResultadoPorAlumno
from app.schemas.courses import (
    AttendanceStatsDto,
    CourseDto,
    CourseList,
    ExamTurnDto,
    ExamTurnList,
    ExamTypeList,
    FinalResultDto,
    MeDto,
    PeriodDto,
    PeriodList,
    PrerequisiteDto,
    PrerequisiteList,
    RosterList,
    RosterStudentDto,
    ScheduleDto,
    StudentProfileDto,
    SubjectDto,
    TeacherDto,
)
from app.security.course_access import authorize_course, teacher_keys
from app.security.principal import Principal
from app.services.rules import _strip_accents, roster_sort_key


@dataclass(frozen=True)
class RosterEntry:
    student_id: str
    enrollment_status: str
    profile: StudentProfile | None

    @property
    def name(self) -> str:
        return self.profile.full_name if self.profile else self.student_id

    @property
    def file_number(self) -> str:
        return self.profile.file_number if self.profile else MISSING_FILE_NUMBER


@dataclass(frozen=True)
class RosterResult:
    entries: list[RosterEntry]
    degraded: bool  # student directory failed (profiles absent)


def period_dto(p: Period) -> PeriodDto:
    return PeriodDto(
        id=p.id,
        year=p.year,
        number=p.number,
        label=p.label,
        start_date=p.start,
        end_date=p.end,
        enrollment_from=p.enroll_from,
        enrollment_until=p.enroll_until,
    )


def course_dto(d: CourseDetail) -> CourseDto:
    c = d.course
    return CourseDto(
        id=c.id,
        code=c.code,
        subject=SubjectDto(id=d.subject.id, code=d.subject.code, name=d.subject.name),
        period=period_dto(d.period),
        campus_id=c.campus_id,
        modality=c.modality,
        status=c.status,
        max_seats=c.max_seats,
        enrolled=c.active_enrolled,
        start_date=c.start,
        end_date=c.end,
        schedule=[
            ScheduleDto(room_id=s.room_id, weekday=s.weekday, start_time=s.start, end_time=s.end)
            for s in d.schedule
        ],
        teachers=[TeacherDto(teacher_id=t.teacher_id, role=t.role) for t in d.teachers],
    )


def load_roster(detail: CourseDetail, *, strict: bool = False) -> RosterResult:
    """Roster (non-BAJA) sorted per §11.4. strict=True propagates directory failures (used for actas)."""
    enrollments = roster_of(detail)
    ids = [e.student_id for e in enrollments]
    profiles: dict[str, StudentProfile] = {}
    degraded = False
    if ids:
        try:
            profiles = get_integrations().directory.get_profiles(ids)
        except UpstreamError:
            if strict:
                raise
            degraded = True
    entries = [RosterEntry(e.student_id, e.status, profiles.get(e.student_id)) for e in enrollments]
    entries.sort(
        key=lambda r: roster_sort_key(
            r.student_id,
            r.profile.file_number if r.profile else None,
            r.profile.full_name if r.profile else None,
        )
    )
    return RosterResult(entries, degraded)


def attendance_by_student(course_id: int) -> dict[str, AsistenciaPorAlumno]:
    rows = db.session.scalars(
        select(AsistenciaPorAlumno).where(AsistenciaPorAlumno.curso_id == course_id)
    ).all()
    return {r.alumno_id: r for r in rows}


# --- use cases ------------------------------------------------------------------
def me(principal: Principal) -> MeDto:
    keys = teacher_keys(principal)
    matched: list[str] = []
    try:
        for d in get_integrations().academic.list_courses_for_teacher(set(keys)):
            matched.extend(t.teacher_id for t in d.teachers if t.teacher_id in keys)
    except UpstreamError:
        pass
    profile: StudentProfile | None = None
    try:  # "Falta consumir los datos del usuario logueado (Backoffice)" -> directory by userId
        profile = get_integrations().directory.get_profiles([principal.user_id]).get(principal.user_id)
    except UpstreamError:
        profile = None
    return MeDto(
        user_id=principal.user_id,
        email=principal.email or (profile.email if profile else None),
        roles=sorted(principal.roles),
        permissions=sorted(principal.permissions),
        teacher_ids=sorted(set(matched)) or keys,
        first_name=profile.first_name if profile else None,
        last_name=profile.last_name if profile else None,
        full_name=profile.full_name if profile else principal.name,
        file_number=profile.file_number if profile else None,
    )


def list_periods() -> PeriodList:
    return PeriodList([period_dto(p) for p in get_integrations().academic.list_periods()])


def list_exam_turns() -> ExamTurnList:
    return ExamTurnList(
        [
            ExamTurnDto(
                id=t.id,
                name=t.name,
                start_date=t.start,
                end_date=t.end,
                enrollment_from=t.enroll_from,
                enrollment_until=t.enroll_until,
            )
            for t in get_integrations().academic.list_exam_turns()
        ]
    )


def exam_types() -> ExamTypeList:
    return ExamTypeList(list(EXAM_TYPE_CATALOG))  # type: ignore[arg-type]


def list_my_course_details(principal: Principal, period_id: int | None = None) -> list[CourseDetail]:
    return get_integrations().academic.list_courses_for_teacher(set(teacher_keys(principal)), period_id)


def list_courses(principal: Principal, period_id: int | None) -> CourseList:
    details = list_my_course_details(principal, period_id)
    # period desc (year, number), then subject name
    details.sort(key=lambda d: _strip_accents(d.subject.name).casefold())
    details.sort(key=lambda d: (d.period.year, d.period.number), reverse=True)
    return CourseList([course_dto(d) for d in details])


def get_course(principal: Principal, course_id: int) -> CourseDto:
    return course_dto(authorize_course(principal, course_id).detail)


def prerequisites(principal: Principal, course_id: int) -> PrerequisiteList:
    access = authorize_course(principal, course_id)
    rows = get_integrations().academic.list_prerequisites(access.detail.subject.id)
    return PrerequisiteList(
        [PrerequisiteDto(id=p.id, prerequisite_subject_id=p.prerequisite_id, kind=p.kind) for p in rows]
    )


def students(principal: Principal, course_id: int) -> tuple[RosterList, bool]:
    detail = authorize_course(principal, course_id).detail
    roster = load_roster(detail)
    att = attendance_by_student(course_id)
    results = {
        r.alumno_id: r
        for r in db.session.scalars(
            select(ResultadoPorAlumno).where(ResultadoPorAlumno.curso_id == course_id)
        ).all()
    }
    out = []
    for e in roster.entries:
        a = att.get(e.student_id)
        r = results.get(e.student_id)
        out.append(
            RosterStudentDto(
                student_id=e.student_id,
                profile=StudentProfileDto(
                    first_name=e.profile.first_name,
                    last_name=e.profile.last_name,
                    full_name=e.profile.full_name,
                    document=e.profile.document,
                    file_number=e.profile.file_number,
                    email=e.profile.email,
                )
                if e.profile
                else None,
                enrollment_status=e.enrollment_status,
                attendance=AttendanceStatsDto(
                    classes_recorded=a.clases_registradas,
                    present=a.presentes,
                    justified=a.justificados,
                    absences=a.inasistencias,
                    attendance_percentage=a.porcentaje_asistencia,
                    condition=a.condicion,
                )
                if a
                else None,
                final_result=FinalResultDto(
                    grade=r.nota, result=r.resultado, acta_number=r.acta_numero, date=r.fecha_resultado
                )
                if r
                else None,
            )
        )
    return RosterList(out), roster.degraded


def settings():
    return current_app.extensions["settings"]
