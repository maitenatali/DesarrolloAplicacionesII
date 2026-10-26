from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, pk


class Examen(Base):
    __tablename__ = "examen"
    __table_args__ = (
        CheckConstraint("duracion_minutos > 0", name="examen_duracion_ck"),
        CheckConstraint("modalidad in ('PRESENCIAL','VIRTUAL')", name="examen_modalidad_ck"),
        CheckConstraint("estado in ('PROGRAMADO','CANCELADO')", name="examen_estado_ck"),
        Index(
            "examen_curso_tipo_activo_uk",
            "curso_id",
            "tipo",
            unique=True,
            postgresql_where=text("estado <> 'CANCELADO'"),
        ),
        Index("examen_curso_idx", "curso_id"),
    )

    id: Mapped[int] = pk()
    curso_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    modalidad: Mapped[str] = mapped_column(String(15), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, server_default="PROGRAMADO")
    creado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Calificacion(Base):
    __tablename__ = "calificacion"
    __table_args__ = (
        UniqueConstraint("examen_id", "alumno_id", name="calificacion_examen_alumno_uk"),
        CheckConstraint("nota between 0 and 10", name="calificacion_nota_ck"),
        CheckConstraint("not (ausente and nota is not null)", name="calificacion_ausente_sin_nota_ck"),
        Index("calificacion_alumno_idx", "alumno_id"),
    )

    id: Mapped[int] = pk()
    examen_id: Mapped[int] = mapped_column(ForeignKey("examen.id"), nullable=False)
    alumno_id: Mapped[str] = mapped_column(String(50), nullable=False)
    nota: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    ausente: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    cargada_por: Mapped[str] = mapped_column(String(50), nullable=False)
    cargada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
