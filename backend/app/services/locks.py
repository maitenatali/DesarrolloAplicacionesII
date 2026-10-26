"""Locks while a valid acta exists (design §11.9, LOCK_AFTER_ACTA)."""

from __future__ import annotations

from flask import current_app
from sqlalchemy import exists, select

from app.extensions import db
from app.models import Acta


def _enabled() -> bool:
    return current_app.extensions["settings"].lock_after_acta


def exam_has_valid_acta(exam_id: int) -> bool:
    if not _enabled():
        return False
    return bool(
        db.session.scalar(select(exists().where(Acta.examen_id == exam_id, Acta.estado == "GENERADA")))
    )


def course_has_valid_cursada_acta(course_id: int) -> bool:
    if not _enabled():
        return False
    return bool(
        db.session.scalar(
            select(
                exists().where(Acta.curso_id == course_id, Acta.tipo == "CURSADA", Acta.estado == "GENERADA")
            )
        )
    )
