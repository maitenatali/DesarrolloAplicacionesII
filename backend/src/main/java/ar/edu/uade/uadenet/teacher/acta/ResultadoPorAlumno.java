package ar.edu.uade.uadenet.teacher.acta;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Último resultado oficial de un alumno en un curso, según el acta vigente más reciente.
 * Vista {@code resultado_por_alumno} (solo lectura). La consume el Portal del Estudiante.
 */
@Entity
@Immutable
@Table(name = "resultado_por_alumno")
@IdClass(ResultadoPorAlumnoId.class)
@Getter
@NoArgsConstructor
public class ResultadoPorAlumno {

    @Id
    @Column(name = "alumno_id")
    private String alumnoId;

    @Id
    @Column(name = "curso_id")
    private Long cursoId;

    @Column(name = "asignatura_id")
    private Long asignaturaId;

    @Column(name = "periodo_id")
    private Long periodoId;

    @Column(name = "materia")
    private String materia;

    @Column(name = "comision")
    private String comision;

    @Column(name = "periodo")
    private String periodo;

    @Column(name = "nota", precision = 4, scale = 2)
    private BigDecimal nota;

    @Enumerated(EnumType.STRING)
    @Column(name = "resultado")
    private ResultadoActa resultado;

    @Enumerated(EnumType.STRING)
    @Column(name = "tipo_acta")
    private TipoActa tipoActa;

    @Column(name = "acta_numero")
    private String actaNumero;

    @Column(name = "fecha_resultado")
    private LocalDate fechaResultado;
}
