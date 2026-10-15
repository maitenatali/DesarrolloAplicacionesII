package ar.edu.uade.uadenet.teacher.examen;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CalificacionRepository extends JpaRepository<Calificacion, Long> {

    List<Calificacion> findByExamenId(Long examenId);

    /** Todas las notas de un curso (pantalla de calificaciones). */
    List<Calificacion> findByExamenCursoId(Long cursoId);

    Optional<Calificacion> findByExamenIdAndAlumnoId(Long examenId, String alumnoId);
}
