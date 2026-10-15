package ar.edu.uade.uadenet.teacher.asistencia;

import lombok.AllArgsConstructor;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/** Clave compuesta de {@link AsistenciaPorAlumno}. */
@Getter
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode
public class AsistenciaPorAlumnoId implements Serializable {

    private Long cursoId;
    private String alumnoId;
}
