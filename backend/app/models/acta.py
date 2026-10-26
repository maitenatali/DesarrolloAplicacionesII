from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, pk


class Acta(Base):
    __tablename__ = "acta"
    __table_args__ = (
        CheckConstraint("tipo in ('CURSADA','FINAL')", name="acta_tipo_ck"),
        CheckConstraint("estado in ('GENERADA','ANULADA')", name="acta_estado_ck"),
        CheckConstraint("(tipo = 'FINAL') = (examen_id is not null)", name="acta_examen_segun_tipo_ck"),
        CheckConstraint("(estado = 'ANULADA') = (anulada_en is not null)", name="acta_anulacion_ck"),
        Index(
            "acta_vigente_uk",
            "curso_id",
            "tipo",
            text("coalesce(examen_id, 0)"),
            unique=True,
            postgresql_where=text("estado = 'GENERADA'"),
        ),
        Index("acta_curso_idx", "curso_id"),
        Index("acta_periodo_idx", "periodo_id"),
        Index("acta_docente_idx", "docente_id"),
    )

    id: Mapped[int] = pk()
    numero: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    curso_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    asignatura_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    periodo_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    examen_id: Mapped[int | None] = mapped_column(ForeignKey("examen.id"))
    materia: Mapped[str] = mapped_column(String(150), nullable=False)
    comision: Mapped[str] = mapped_column(String(50), nullable=False)
    periodo: Mapped[str] = mapped_column(String(50), nullable=False)
    docente_id: Mapped[str] = mapped_column(String(50), nullable=False)
    docente_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, server_default="GENERADA")
    generada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    sync_ok: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sync_error: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sync_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detalles: Mapped[list[ActaDetalle]] = relationship(
        back_populates="acta",
        cascade="all, delete-orphan",
        order_by="ActaDetalle.orden",
        passive_deletes=True,
    )


class ActaDetalle(Base):
    __tablename__ = "acta_detalle"
    __table_args__ = (
        UniqueConstraint("acta_id", "alumno_id", name="acta_detalle_alumno_uk"),
        UniqueConstraint("acta_id", "orden", name="acta_detalle_orden_uk"),
        CheckConstraint("orden > 0", name="acta_detalle_orden_ck"),
        CheckConstraint("nota between 0 and 10", name="acta_detalle_nota_ck"),
        CheckConstraint(
            "resultado in ('APROBADO','DESAPROBADO','REGULAR','LIBRE','AUSENTE')",
            name="acta_detalle_resultado_ck",
        ),
        Index("acta_detalle_alumno_idx", "alumno_id"),
    )

    id: Mapped[int] = pk()
    acta_id: Mapped[int] = mapped_column(ForeignKey("acta.id", ondelete="CASCADE"), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    alumno_id: Mapped[str] = mapped_column(String(50), nullable=False)
    alumno_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    alumno_legajo: Mapped[str] = mapped_column(String(20), nullable=False)
    nota: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    resultado: Mapped[str] = mapped_column(String(15), nullable=False)
    acta: Mapped[Acta] = relationship(back_populates="detalles")


class ResultadoPorAlumno(Base):  # VIEW - read-only
    __tablename__ = "resultado_por_alumno"
    __table_args__ = {"info": {"is_view": True}}

    alumno_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    curso_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asignatura_id: Mapped[int] = mapped_column(BigInteger)
    periodo_id: Mapped[int] = mapped_column(BigInteger)
    materia: Mapped[str] = mapped_column(String)
    comision: Mapped[str] = mapped_column(String)
    periodo: Mapped[str] = mapped_column(String)
    nota: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    resultado: Mapped[str] = mapped_column(String)
    tipo_acta: Mapped[str] = mapped_column(String)
    acta_numero: Mapped[str] = mapped_column(String)
    fecha_resultado: Mapped[date] = mapped_column(Date)
