package ar.edu.uade.uadenet.teacher.asistencia;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

/** Clase en la que se tomó asistencia. Tabla {@code clase}. */
@Entity
@Table(name = "clase")
@Getter
@Setter
@NoArgsConstructor
public class Clase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Referencia al curso en Gestión Académica. */
    @Column(name = "curso_id", nullable = false)
    private Long cursoId;

    @Column(name = "fecha", nullable = false)
    private LocalDate fecha;

    @Column(name = "observaciones", columnDefinition = "text")
    private String observaciones;

    /** Id del docente que registró la asistencia. */
    @Column(name = "creado_por", nullable = false, length = 50)
    private String creadoPor;

    @CreationTimestamp
    @Column(name = "creado_en", nullable = false, updatable = false, columnDefinition = "timestamptz")
    private OffsetDateTime creadoEn;

    @UpdateTimestamp
    @Column(name = "actualizado_en", nullable = false, columnDefinition = "timestamptz")
    private OffsetDateTime actualizadoEn;

    @OneToMany(mappedBy = "clase", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Asistencia> asistencias = new ArrayList<>();

    /** Agrega una asistencia manteniendo los dos lados de la relación. */
    public void agregarAsistencia(Asistencia asistencia) {
        asistencias.add(asistencia);
        asistencia.setClase(this);
    }
}
