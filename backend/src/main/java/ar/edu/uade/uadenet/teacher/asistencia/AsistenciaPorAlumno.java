package ar.edu.uade.uadenet.teacher.asistencia;

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

/** Regularidad por asistencia de cada alumno en un curso. Vista {@code asistencia_por_alumno} (solo lectura). */
@Entity
@Immutable
@Table(name = "asistencia_por_alumno")
@IdClass(AsistenciaPorAlumnoId.class)
@Getter
@NoArgsConstructor
public class AsistenciaPorAlumno {

    @Id
    @Column(name = "curso_id")
    private Long cursoId;

    @Id
    @Column(name = "alumno_id")
    private String alumnoId;

    @Column(name = "clases_registradas")
    private Integer clasesRegistradas;

    @Column(name = "presentes")
    private Integer presentes;

    @Column(name = "justificados")
    private Integer justificados;

    @Column(name = "inasistencias")
    private Integer inasistencias;

    @Column(name = "porcentaje_asistencia", precision = 5, scale = 2)
    private BigDecimal porcentajeAsistencia;

    @Enumerated(EnumType.STRING)
    @Column(name = "condicion")
    private CondicionAsistencia condicion;
}
