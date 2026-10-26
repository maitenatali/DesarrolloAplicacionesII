"""Results per student for the Student Portal (service-to-service, design §10.10)."""

from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models import ResultadoPorAlumno
from app.schemas.results import ResultDto, ResultList


def _dto(r: ResultadoPorAlumno) -> ResultDto:
    return ResultDto(
        student_id=r.alumno_id,
        course_id=r.curso_id,
        subject_id=r.asignatura_id,
        period_id=r.periodo_id,
        subject=r.materia,
        commission=r.comision,
        period=r.periodo,
        grade=r.nota,
        result=r.resultado,
        acta_type=r.tipo_acta,
        acta_number=r.acta_numero,
        result_date=r.fecha_resultado,
    )


def student_results(student_id: str, course_id: int | None = None) -> ResultList:
    q = select(ResultadoPorAlumno).where(ResultadoPorAlumno.alumno_id == student_id)
    if course_id is not None:
        q = q.where(ResultadoPorAlumno.curso_id == course_id)
    return ResultList([_dto(r) for r in db.session.scalars(q.order_by(ResultadoPorAlumno.curso_id)).all()])


def course_results(course_id: int) -> ResultList:
    q = (
        select(ResultadoPorAlumno)
        .where(ResultadoPorAlumno.curso_id == course_id)
        .order_by(ResultadoPorAlumno.alumno_id)
    )
    return ResultList([_dto(r) for r in db.session.scalars(q).all()])
