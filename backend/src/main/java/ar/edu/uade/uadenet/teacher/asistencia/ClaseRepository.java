package ar.edu.uade.uadenet.teacher.asistencia;

import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface ClaseRepository extends JpaRepository<Clase, Long> {

    /** Historial de asistencia de un curso, la clase más reciente primero. */
    List<Clase> findByCursoIdOrderByFechaDesc(Long cursoId);

    Optional<Clase> findByCursoIdAndFecha(Long cursoId, LocalDate fecha);

    boolean existsByCursoIdAndFecha(Long cursoId, LocalDate fecha);
}
