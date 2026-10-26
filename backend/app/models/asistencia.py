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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, pk


class Clase(Base):
    __tablename__ = "clase"
    __table_args__ = (UniqueConstraint("curso_id", "fecha", name="clase_curso_fecha_uk"),)

    id: Mapped[int] = pk()
    curso_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text)
    creado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    asistencias: Mapped[list[Asistencia]] = relationship(
        back_populates="clase", cascade="all, delete-orphan", passive_deletes=True
    )


class Asistencia(Base):
    __tablename__ = "asistencia"
    __table_args__ = (
        UniqueConstraint("clase_id", "alumno_id", name="asistencia_clase_alumno_uk"),
        CheckConstraint("estado in ('PRESENTE','AUSENTE','JUSTIFICADO')", name="asistencia_estado_ck"),
        Index("asistencia_alumno_idx", "alumno_id"),
    )

    id: Mapped[int] = pk()
    clase_id: Mapped[int] = mapped_column(ForeignKey("clase.id", ondelete="CASCADE"), nullable=False)
    alumno_id: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(255))
    clase: Mapped[Clase] = relationship(back_populates="asistencias")


class AsistenciaPorAlumno(Base):  # VIEW - read-only
    __tablename__ = "asistencia_por_alumno"
    __table_args__ = {"info": {"is_view": True}}

    curso_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alumno_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    clases_registradas: Mapped[int] = mapped_column(Integer)
    presentes: Mapped[int] = mapped_column(Integer)
    justificados: Mapped[int] = mapped_column(Integer)
    inasistencias: Mapped[int] = mapped_column(Integer)
    porcentaje_asistencia: Mapped[Decimal] = mapped_column(Numeric)
    condicion: Mapped[str] = mapped_column(String)
