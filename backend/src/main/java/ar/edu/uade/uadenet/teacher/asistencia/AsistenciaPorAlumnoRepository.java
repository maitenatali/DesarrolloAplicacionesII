package ar.edu.uade.uadenet.teacher.asistencia;

import org.springframework.data.repository.Repository;

import java.util.List;
import java.util.Optional;

/** Solo lectura: la vista no admite escrituras. */
public interface AsistenciaPorAlumnoRepository extends Repository<AsistenciaPorAlumno, AsistenciaPorAlumnoId> {

    List<AsistenciaPorAlumno> findByCursoId(Long cursoId);

    Optional<AsistenciaPorAlumno> findByCursoIdAndAlumnoId(Long cursoId, String alumnoId);
}
