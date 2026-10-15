package ar.edu.uade.uadenet.teacher.acta;

import lombok.AllArgsConstructor;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/** Clave compuesta de {@link ResultadoPorAlumno}. */
@Getter
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode
public class ResultadoPorAlumnoId implements Serializable {

    private String alumnoId;
    private Long cursoId;
}
