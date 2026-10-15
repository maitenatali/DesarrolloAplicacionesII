package ar.edu.uade.uadenet.teacher.examen;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalTime;
import java.time.OffsetDateTime;

/**
 * Evaluación de un curso. Tabla {@code examen}.
 * <p>
 * Las calificaciones no se cargan desde acá: se consultan con
 * {@link CalificacionRepository#findByExamenId(Long)}.
 */
@Entity
@Table(name = "examen")
@Getter
@Setter
@NoArgsConstructor
public class Examen {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Referencia al curso en Gestión Académica. */
    @Column(name = "curso_id", nullable = false)
    private Long cursoId;

    /** Texto libre a propósito (PARCIAL_1, TP_1, FINAL, ...). */
    @Column(name = "tipo", nullable = false, length = 50)
    private String tipo;

    /** Nombre para mostrar, ej. "Primer Parcial". */
    @Column(name = "nombre", nullable = false, length = 100)
    private String nombre;

    @Column(name = "descripcion", length = 500)
    private String descripcion;

    @Column(name = "fecha", nullable = false)
    private LocalDate fecha;

    @Column(name = "hora_inicio", nullable = false)
    private LocalTime horaInicio;

    @Column(name = "duracion_minutos", nullable = false)
    private Integer duracionMinutos;

    @Enumerated(EnumType.STRING)
    @Column(name = "modalidad", nullable = false, length = 15)
    private ModalidadExamen modalidad;

    @Enumerated(EnumType.STRING)
    @Column(name = "estado", nullable = false, length = 15)
    private EstadoExamen estado = EstadoExamen.PROGRAMADO;

    /** Id del docente que creó el examen. */
    @Column(name = "creado_por", nullable = false, length = 50)
    private String creadoPor;

    @CreationTimestamp
    @Column(name = "creado_en", nullable = false, updatable = false, columnDefinition = "timestamptz")
    private OffsetDateTime creadoEn;

    @UpdateTimestamp
    @Column(name = "actualizado_en", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime actualizadoEn;

    /** Hora de fin calculada; no se guarda. */
    public LocalTime getHoraFin() {
        return horaInicio == null || duracionMinutos == null ? null : horaInicio.plusMinutes(duracionMinutos);
    }

    public boolean isCancelado() {
        return estado == EstadoExamen.CANCELADO;
    }
}
