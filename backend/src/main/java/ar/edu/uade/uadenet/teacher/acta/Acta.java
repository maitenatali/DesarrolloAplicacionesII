package ar.edu.uade.uadenet.teacher.acta;

import ar.edu.uade.uadenet.teacher.examen.Examen;
import jakarta.persistence.CascadeType;
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
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderBy;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Encabezado del acta. Tabla {@code acta}.
 * <p>
 * Es la fuente oficial de la nota final y la condición del alumno. Materia,
 * comisión, período y docente se copian como texto al generarla para que el
 * documento no cambie si cambian los datos en otro módulo.
 */
@Entity
@Table(name = "acta")
@Getter
@Setter
@NoArgsConstructor
public class Acta {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Formato AÑO-correlativo, ej. 2026-001. Lo genera el service. */
    @Column(name = "numero", nullable = false, unique = true, length = 20)
    private String numero;

    @Enumerated(EnumType.STRING)
    @Column(name = "tipo", nullable = false, length = 10)
    private TipoActa tipo;

    // ── Referencias a Gestión Académica ──
    @Column(name = "curso_id", nullable = false)
    private Long cursoId;

    @Column(name = "asignatura_id", nullable = false)
    private Long asignaturaId;

    @Column(name = "periodo_id", nullable = false)
    private Long periodoId;

    /** Examen final que origina el acta. Solo en actas FINAL; null en las de cursada. */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "examen_id")
    private Examen examen;

    // ── Copias al momento de generar ──
    /** Ej. "Desarrollo de Aplicaciones II". */
    @Column(name = "materia", nullable = false, length = 150)
    private String materia;

    /** Ej. "DDA2-A". */
    @Column(name = "comision", nullable = false, length = 50)
    private String comision;

    /** Ej. "2° Cuatrimestre 2026". */
    @Column(name = "periodo", nullable = false, length = 50)
    private String periodo;

    @Column(name = "docente_id", nullable = false, length = 50)
    private String docenteId;

    @Column(name = "docente_nombre", nullable = false, length = 150)
    private String docenteNombre;

    // ── Datos del acta ──
    @Column(name = "fecha", nullable = false)
    private LocalDate fecha;

    @Column(name = "observaciones", columnDefinition = "text")
    private String observaciones;

    @Enumerated(EnumType.STRING)
    @Column(name = "estado", nullable = false, length = 10)
    private EstadoActa estado = EstadoActa.GENERADA;

    @CreationTimestamp
    @Column(name = "generada_en", nullable = false, updatable = false, columnDefinition = "timestamptz")
    private OffsetDateTime generadaEn;

    @Column(name = "anulada_en", columnDefinition = "timestamptz")
    private OffsetDateTime anuladaEn;

    @Column(name = "motivo_anulacion", columnDefinition = "text")
    private String motivoAnulacion;

    // ── Envío de resultados a Gestión Académica ──
    @Column(name = "sync_ok", nullable = false)
    private Integer syncOk = 0;

    @Column(name = "sync_error", nullable = false)
    private Integer syncError = 0;

    @Column(name = "sync_en", columnDefinition = "timestamptz")
    private OffsetDateTime syncEn;

    @OneToMany(mappedBy = "acta", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("orden ASC")
    private List<ActaDetalle> detalles = new ArrayList<>();

    /** Agrega un renglón manteniendo los dos lados de la relación. */
    public void agregarDetalle(ActaDetalle detalle) {
        detalles.add(detalle);
        detalle.setActa(this);
    }

    /** Anula el acta. La base exige fecha de anulación cuando el estado es ANULADA. */
    public void anular(String motivo) {
        this.estado = EstadoActa.ANULADA;
        this.anuladaEn = OffsetDateTime.now();
        this.motivoAnulacion = motivo;
    }

    /** Registra el resultado del envío de notas a Gestión Académica. */
    public void registrarSincronizacion(int ok, int error) {
        this.syncOk = ok;
        this.syncError = error;
        this.syncEn = OffsetDateTime.now();
    }
}
