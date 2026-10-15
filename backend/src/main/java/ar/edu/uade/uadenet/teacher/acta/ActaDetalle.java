package ar.edu.uade.uadenet.teacher.acta;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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

import java.math.BigDecimal;

/** Renglón del acta: un alumno con su nota y resultado. Tabla {@code acta_detalle}. */
@Entity
@Table(name = "acta_detalle")
@Getter
@Setter
@NoArgsConstructor
public class ActaDetalle {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "acta_id", nullable = false)
    private Acta acta;

    /** Número de renglón (1, 2, 3...). */
    @Column(name = "orden", nullable = false)
    private Integer orden;

    @Column(name = "alumno_id", nullable = false, length = 50)
    private String alumnoId;

    /** Copia al generar el acta. */
    @Column(name = "alumno_nombre", nullable = false, length = 150)
    private String alumnoNombre;

    /** Copia al generar el acta. */
    @Column(name = "alumno_legajo", nullable = false, length = 20)
    private String alumnoLegajo;

    @Column(name = "nota", precision = 4, scale = 2)
    private BigDecimal nota;

    @Enumerated(EnumType.STRING)
    @Column(name = "resultado", nullable = false, length = 15)
    private ResultadoActa resultado;

    public ActaDetalle(Integer orden, String alumnoId, String alumnoNombre, String alumnoLegajo,
                       BigDecimal nota, ResultadoActa resultado) {
        this.orden = orden;
        this.alumnoId = alumnoId;
        this.alumnoNombre = alumnoNombre;
        this.alumnoLegajo = alumnoLegajo;
        this.nota = nota;
        this.resultado = resultado;
    }
}
