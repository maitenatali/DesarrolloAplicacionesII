package ar.edu.uade.uadenet.teacher.examen;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

/** Nota de un alumno en un examen. Tabla {@code calificacion}. */
@Entity
@Table(name = "calificacion")
@Getter
@Setter
@NoArgsConstructor
public class Calificacion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "examen_id", nullable = false)
    private Examen examen;

    /** Referencia al alumno en el módulo propietario. */
    @Column(name = "alumno_id", nullable = false, length = 50)
    private String alumnoId;

    /** Entre 0 y 10. Vacía si el alumno estuvo ausente. */
    @Column(name = "nota", precision = 4, scale = 2)
    private BigDecimal nota;

    @Column(name = "ausente", nullable = false)
    private Boolean ausente = false;

    /** Id del docente que cargó la nota. */
    @Column(name = "cargada_por", nullable = false, length = 50)
    private String cargadaPor;

    /** Se actualiza cada vez que se guarda la nota. */
    @UpdateTimestamp
    @Column(name = "cargada_en", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime cargadaEn;
}
