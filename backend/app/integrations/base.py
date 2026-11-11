"""Integration ABCs and internal DTOs (design §9.2). Services depend on these only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal


@dataclass(frozen=True)
class Subject:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class Period:
    id: int
    year: int
    number: int
    start: date
    end: date
    enroll_from: date | None = None  # GA /planificacion/periodos does not publish enrollment dates
    enroll_until: date | None = None

    @property
    def label(self) -> str:
        return f"{self.number}° Cuatrimestre {self.year}"


@dataclass(frozen=True)
class CourseSummary:
    id: int
    code: str
    subject_id: int
    period_id: int
    campus_id: int | None
    modality: str
    status: str
    max_seats: int
    start: date | None
    end: date | None
    active_enrolled: int


@dataclass(frozen=True)
class TeacherAssignment:
    id: int
    teacher_id: str
    role: str  # TITULAR | ADJUNTO | AUXILIAR


@dataclass(frozen=True)
class Enrollment:
    id: int
    student_id: str
    enrolled_on: date | None
    status: str
    final_grade: Decimal | None
    result_date: date | None


@dataclass(frozen=True)
class Schedule:
    id: int
    room_id: int | None
    weekday: str
    start: time
    end: time


@dataclass(frozen=True)
class CourseDetail:
    course: CourseSummary
    subject: Subject
    period: Period
    teachers: list[TeacherAssignment] = field(default_factory=list)
    enrollments: list[Enrollment] = field(default_factory=list)
    schedule: list[Schedule] = field(default_factory=list)


@dataclass(frozen=True)
class Prerequisite:
    id: int
    subject_id: int
    prerequisite_id: int
    kind: str  # REGULAR | APROBADA


@dataclass(frozen=True)
class ExamTurn:
    id: int
    name: str
    start: date
    end: date
    enroll_from: date
    enroll_until: date


@dataclass(frozen=True)
class StudentProfile:
    student_id: str
    first_name: str
    last_name: str
    full_name: str
    document: str | None
    file_number: str
    email: str | None


class AcademicClient(ABC):
    @abstractmethod
    def list_periods(self) -> list[Period]: ...

    @abstractmethod
    def list_exam_turns(self) -> list[ExamTurn]: ...

    @abstractmethod
    def list_courses(self, period_id: int | None = None) -> list[CourseSummary]: ...

    @abstractmethod
    def get_course(self, course_id: int, *, fresh: bool = False) -> CourseDetail:
        """Raises CourseNotFound."""

    @abstractmethod
    def list_courses_for_teacher(
        self, teacher_keys: set[str], period_id: int | None = None
    ) -> list[CourseDetail]: ...

    @abstractmethod
    def list_prerequisites(self, subject_id: int) -> list[Prerequisite]: ...

    @abstractmethod
    def update_enrollment_result(
        self, course_id: int, student_id: str, *, status: str, final_grade: Decimal | None, result_date: date
    ) -> None:
        """Idempotent PUT. Raises UpstreamError on failure."""


class CoreEventsClient(ABC):
    @abstractmethod
    def publish(self, envelope: dict) -> None:
        """Raises PublishError (with a retryable flag)."""


class StudentDirectoryClient(ABC):
    @abstractmethod
    def get_profiles(self, student_ids: Sequence[str]) -> dict[str, StudentProfile]:
        """Ids the directory does not know are absent from the result. Raises UpstreamError if it fails."""


def roster_of(detail: CourseDetail) -> list[Enrollment]:
    """Non-BAJA enrollments, de-duplicated by student id (design §11.4)."""
    seen: set[str] = set()
    out: list[Enrollment] = []
    for e in detail.enrollments:
        if e.status == "BAJA" or e.student_id in seen:
            continue
        seen.add(e.student_id)
        out.append(e)
    return out


class NotificationsClient(ABC):
    """CORE POST /internal/v1/notifications (service token). Body: userId, type, title, message,
    actionUrl?, sourceModule, sourceReference, expiresAt?."""

    @abstractmethod
    def create(self, payload: dict) -> None:
        """Raises PublishError (with a retryable flag). A duplicate (409) counts as success."""


# ── Calendar / purchases sources (TPO §2: calendario con turnos de comedor, eventos y exámenes;
#    historial de compras de la Tienda). Shapes follow each module's data-flow sheet. ───────────
@dataclass(frozen=True)
class AcademicEvent:  # Eventos Académicos: GET /api/v1/eventos
    id: str
    title: str
    description: str | None
    location_name: str
    site_name: str
    start: datetime
    end: datetime
    is_paid: bool
    price: str | None  # money as string decimal
    registered: bool


@dataclass(frozen=True)
class DiningReservation:  # Comedor: dining.reservation.created.v1
    reservation_id: str
    site_id: str
    site_name: str
    slot_at: datetime
    amount: str
    currency: str
    status: str  # CONFIRMED | CANCELLED | ATTENDED


@dataclass(frozen=True)
class PurchaseItem:
    product_id: str
    product_name: str
    category: str
    quantity: int
    unit_price: str
    subtotal: str


@dataclass(frozen=True)
class Purchase:  # Tienda: store.purchase.completed.v1
    purchase_id: str
    created_at: datetime
    total: str
    currency: str
    status: str
    site_id: str | None
    items: list[PurchaseItem] = field(default_factory=list)


class CampusClient(ABC):
    """Read-only data of other campus modules shown in the teacher portal (mock in this delivery)."""

    @abstractmethod
    def list_academic_events(self, user_id: str, start: date, end: date) -> list[AcademicEvent]: ...

    @abstractmethod
    def list_dining_reservations(self, user_id: str, start: date, end: date) -> list[DiningReservation]: ...

    @abstractmethod
    def list_purchases(self, user_id: str) -> list[Purchase]: ...
