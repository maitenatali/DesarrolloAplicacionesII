"""Publish acta results to Gestión Académica after commit (design §11.7).

Worker threads receive plain values only and never touch db.session.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.constants import ActaType, Result
from app.integrations.factory import get_integrations
from app.models import Acta
from app.time import now_utc

log = logging.getLogger("app.acta_sync")

_FINAL_SENT = {Result.APROBADO, Result.DESAPROBADO, Result.LIBRE}  # AUSENTE is never sent [OPEN: GA]
_CURSADA_SENT = {Result.REGULAR, Result.LIBRE}


@dataclass(frozen=True)
class SyncTarget:
    student_id: str
    status: str
    final_grade: Decimal | None


@dataclass(frozen=True)
class SyncOutcome:
    ok: int
    error: int
    at: datetime


def targets_for(acta: Acta) -> list[SyncTarget]:
    out = []
    for r in acta.detalles:
        res = Result(r.resultado)
        if acta.tipo == ActaType.FINAL and res in _FINAL_SENT:
            out.append(SyncTarget(r.alumno_id, res.value, r.nota))
        elif acta.tipo == ActaType.CURSADA and res in _CURSADA_SENT:
            out.append(SyncTarget(r.alumno_id, res.value, None))
    return out


def run_sync(
    course_id: int, result_date: date, targets: list[SyncTarget], *, deadline_s: float = 20, workers: int = 4
) -> SyncOutcome:
    """Counters describe THIS attempt only. Unfinished calls count as errors (they are retriable)."""
    academic = get_integrations().academic
    ok = err = 0
    if targets:
        pool = ThreadPoolExecutor(workers)
        try:
            futures = {
                pool.submit(
                    academic.update_enrollment_result,
                    course_id,
                    t.student_id,
                    status=t.status,
                    final_grade=t.final_grade,
                    result_date=result_date,
                ): t
                for t in targets
            }
            done, not_done = wait(futures, timeout=deadline_s)
            for f in done:
                exc = f.exception()
                if exc is None:
                    ok += 1
                else:
                    err += 1
                    log.warning(
                        "acta_sync_failed",
                        extra={"studentId": futures[f].student_id, "error": str(exc)[:200]},
                    )
            err += len(not_done)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    return SyncOutcome(ok, err, now_utc())
