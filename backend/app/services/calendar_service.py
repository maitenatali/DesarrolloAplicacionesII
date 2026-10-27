"""Teacher calendar (own exams + GA exam turns + academic events + dining reservations) and store purchases.

BFF aggregation (design §10.11). Each external source is optional: if one fails, its items are left out and
its name is listed in `degraded` instead of failing the whole calendar.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.errors import UpstreamError
from app.integrations.factory import get_integrations
from app.schemas.calendar import (
    CalendarDto,
    CalendarItemDto,
    CalendarQuery,
    PurchaseDto,
    PurchaseItemDto,
    PurchaseList,
)
from app.schemas.exams import ExamQuery
from app.security.principal import Principal
from app.services import exam_service
from app.time import _tz, today_local

log = logging.getLogger("app.calendar")


def calendar(principal: Principal, q: CalendarQuery) -> CalendarDto:
    start = q.from_ or today_local().replace(day=1)
    end = q.to or (start + timedelta(days=62))
    items: list[CalendarItemDto] = []
    degraded: list[str] = []
    integ = get_integrations()

    try:
        exams = exam_service.list_my_exams(principal, ExamQuery.model_validate({"from": start, "to": end}))
        for e in exams.root:
            starts = datetime.combine(e.date, e.start_time)
            ends = starts + timedelta(minutes=e.duration_minutes)
            items.append(
                CalendarItemDto(
                    id=f"exam-{e.id}",
                    kind="EXAM",
                    title=f"{e.name} · {e.course.subject_name}",
                    start=starts.replace(tzinfo=_tz()),
                    end=ends.replace(tzinfo=_tz()),
                    location=e.modality,
                    source="teacher",
                    reference={"courseId": e.course_id, "examId": e.id, "phase": e.phase.value},
                )
            )
    except UpstreamError:
        degraded.append("academic")

    try:
        for t in integ.academic.list_exam_turns():
            if t.end < start or t.start > end:
                continue
            items.append(
                CalendarItemDto(
                    id=f"exam-turn-{t.id}",
                    kind="EXAM_TURN",
                    title=t.name,
                    start_date=t.start,
                    end_date=t.end,
                    source="academic",
                    reference={"examTurnId": t.id},
                )
            )
    except UpstreamError:
        if "academic" not in degraded:
            degraded.append("academic")

    try:
        for ev in integ.campus.list_academic_events(principal.user_id, start, end):
            items.append(
                CalendarItemDto(
                    id=f"event-{ev.id}",
                    kind="ACADEMIC_EVENT",
                    title=ev.title,
                    start=ev.start,
                    end=ev.end,
                    location=f"{ev.location_name} — {ev.site_name}",
                    source="events",
                    reference={"eventId": ev.id, "registered": ev.registered, "price": ev.price},
                )
            )
    except UpstreamError:
        degraded.append("events")

    try:
        for r in integ.campus.list_dining_reservations(principal.user_id, start, end):
            items.append(
                CalendarItemDto(
                    id=f"dining-{r.reservation_id}",
                    kind="DINING_RESERVATION",
                    title=f"Turno de comedor · {r.site_name}",
                    start=r.slot_at,
                    end=r.slot_at + timedelta(minutes=60),
                    location=r.site_name,
                    source="dining",
                    reference={"reservationId": r.reservation_id, "amount": r.amount, "status": r.status},
                )
            )
    except UpstreamError:
        degraded.append("dining")

    def _key(i: CalendarItemDto):
        if i.start is not None:
            return i.start.astimezone(UTC)
        assert i.start_date is not None
        return datetime.combine(i.start_date, datetime.min.time(), tzinfo=UTC)

    items.sort(key=_key)
    return CalendarDto.model_validate({"from": start, "to": end, "items": items, "degraded": degraded})


def purchases(principal: Principal) -> PurchaseList:
    return PurchaseList(
        [
            PurchaseDto(
                purchase_id=p.purchase_id,
                created_at=p.created_at,
                total=p.total,
                currency=p.currency,
                status=p.status,
                site_id=p.site_id,
                items=[
                    PurchaseItemDto(
                        product_id=i.product_id,
                        product_name=i.product_name,
                        category=i.category,
                        quantity=i.quantity,
                        unit_price=i.unit_price,
                        subtotal=i.subtotal,
                    )
                    for i in p.items
                ],
            )
            for p in get_integrations().campus.list_purchases(principal.user_id)
        ]
    )
