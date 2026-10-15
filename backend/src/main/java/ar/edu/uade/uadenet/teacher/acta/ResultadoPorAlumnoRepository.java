package ar.edu.uade.uadenet.teacher.acta;

import org.springframework.data.repository.Repository;

import java.util.List;
import java.util.Optional;

/** Solo lectura: la vista no admite escrituras. */
public interface ResultadoPorAlumnoRepository extends Repository<ResultadoPorAlumno, ResultadoPorAlumnoId> {

    /** Historial de materias de un alumno (Portal del Estudiante). */
    List<ResultadoPorAlumno> findByAlumnoIdOrderByFechaResultadoDesc(String alumnoId);

    List<ResultadoPorAlumno> findByCursoId(Long cursoId);

    Optional<ResultadoPorAlumno> findByAlumnoIdAndCursoId(String alumnoId, Long cursoId);
}
