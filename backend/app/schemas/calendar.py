from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from pydantic import Field, RootModel, model_validator

from .common import ApiModel, Instant


class CalendarQuery(ApiModel):
    from_: dt.date | None = Field(default=None, alias="from")
    to: dt.date | None = None

    @model_validator(mode="after")
    def _range(self) -> CalendarQuery:
        if self.from_ and self.to and self.to < self.from_:
            raise ValueError("`to` debe ser posterior o igual a `from`.")
        if self.from_ and self.to and (self.to - self.from_).days > 366:
            raise ValueError("El rango máximo es de un año.")
        return self


class CalendarItemDto(ApiModel):
    """One entry of the teacher calendar (TPO §2: turnos de comedor, eventos y exámenes)."""

    id: str
    kind: Literal["EXAM", "EXAM_TURN", "ACADEMIC_EVENT", "DINING_RESERVATION"]
    title: str
    start: Instant | None = None  # timed items
    end: Instant | None = None
    start_date: dt.date | None = None  # all-day / multi-day items (exam turns)
    end_date: dt.date | None = None
    location: str | None = None
    source: Literal["teacher", "academic", "events", "dining"]
    reference: dict[str, str | int | float | bool | None] = {}


class CalendarDto(ApiModel):
    from_: dt.date = Field(alias="from")
    to: dt.date
    items: list[CalendarItemDto]
    degraded: list[str] = []  # sources that failed (their items are missing)


class PurchaseItemDto(ApiModel):
    product_id: str
    product_name: str
    category: str
    quantity: int
    unit_price: Annotated[str, Field(examples=["3500.00"])]
    subtotal: str


class PurchaseDto(ApiModel):
    purchase_id: str
    created_at: Instant
    total: str
    currency: str
    status: str
    site_id: str | None = None
    items: list[PurchaseItemDto]


class PurchaseList(RootModel[list[PurchaseDto]]):
    pass
