"""Mock data of Eventos Académicos, Comedor and Tienda for the teacher portal (no live connection in
this delivery). Field names follow each module's data-flow sheet so a live adapter is a drop-in."""

from __future__ import annotations

from datetime import UTC, date, datetime

from .base import AcademicEvent, CampusClient, DiningReservation, Purchase, PurchaseItem

SITE_MONSERRAT = "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90"


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(UTC)


EVENTS = [
    AcademicEvent(
        "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03",
        "Charla: Arquitectura de Software",
        "Charla abierta sobre patrones de arquitectura.",
        "Aula Magna",
        "Monserrat",
        _dt("2026-10-29T18:00:00-03:00"),
        _dt("2026-10-29T20:00:00-03:00"),
        False,
        None,
        True,
    ),
    AcademicEvent(
        "65a783d1-d407-442d-8d09-a6d2abfe9321",
        "Jornada de Ingeniería",
        "Jornada anual de la Facultad de Ingeniería.",
        "Aula Magna - Sede Monserrat",
        "Monserrat",
        _dt("2026-11-12T18:00:00-03:00"),
        _dt("2026-11-12T21:00:00-03:00"),
        True,
        "1800.00",
        False,
    ),
]

RESERVATIONS = [
    DiningReservation(
        "58df9fe3-4883-4dca-9d9f-4770c81543cf",
        SITE_MONSERRAT,
        "Sede Monserrat",
        _dt("2026-10-27T13:00:00-03:00"),
        "1500.00",
        "ARS",
        "CONFIRMED",
    ),
    DiningReservation(
        "6a1c2e44-0d55-4f1f-8a6b-1f2a3b4c5d6e",
        SITE_MONSERRAT,
        "Sede Monserrat",
        _dt("2026-11-03T13:00:00-03:00"),
        "1500.00",
        "ARS",
        "CONFIRMED",
    ),
]

PURCHASES = [
    Purchase(
        "93b28f67-e111-4a0d-b857-fdd015c4d3f1",
        _dt("2026-09-12T15:20:00-03:00"),
        "3500.00",
        "ARS",
        "COMPLETED",
        SITE_MONSERRAT,
        [
            PurchaseItem(
                "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
                "Buzo UADE azul",
                "Indumentaria",
                1,
                "3500.00",
                "3500.00",
            )
        ],
    ),
    Purchase(
        "b1f0e9d8-7c6b-4a59-8e3d-2c1b0a9f8e7d",
        _dt("2026-10-02T10:05:00-03:00"),
        "2400.00",
        "ARS",
        "COMPLETED",
        SITE_MONSERRAT,
        [
            PurchaseItem(
                "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e", "Cuaderno A4 UADE", "Librería", 2, "900.00", "1800.00"
            ),
            PurchaseItem(
                "3c4d5e6f-7a8b-4c9d-8e1f-2a3b4c5d6e7f",
                "Lapicera institucional",
                "Librería",
                2,
                "300.00",
                "600.00",
            ),
        ],
    ),
]


class CampusMock(CampusClient):
    """Same data for every user (enough for the portal demo). Filters by the requested window."""

    def __init__(self) -> None:
        self.events = list(EVENTS)
        self.reservations = list(RESERVATIONS)
        self.purchases = list(PURCHASES)

    @staticmethod
    def _in(d: datetime, start: date, end: date) -> bool:
        return start <= d.date() <= end

    def list_academic_events(self, user_id: str, start: date, end: date) -> list[AcademicEvent]:
        return [e for e in self.events if self._in(e.start, start, end) or self._in(e.end, start, end)]

    def list_dining_reservations(self, user_id: str, start: date, end: date) -> list[DiningReservation]:
        return [r for r in self.reservations if self._in(r.slot_at, start, end)]

    def list_purchases(self, user_id: str) -> list[Purchase]:
        return sorted(self.purchases, key=lambda p: p.created_at, reverse=True)
