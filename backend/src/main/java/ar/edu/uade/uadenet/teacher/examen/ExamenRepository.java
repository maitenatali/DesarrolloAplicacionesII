package ar.edu.uade.uadenet.teacher.examen;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ExamenRepository extends JpaRepository<Examen, Long> {

    /** Exámenes de un curso en orden cronológico (incluye cancelados). */
    List<Examen> findByCursoIdOrderByFechaAscHoraInicioAsc(Long cursoId);

    /**
     * Para validar "Ya existe un examen de este tipo para este curso":
     * {@code existsByCursoIdAndTipoAndEstadoNot(cursoId, tipo, EstadoExamen.CANCELADO)}.
     */
    boolean existsByCursoIdAndTipoAndEstadoNot(Long cursoId, String tipo, EstadoExamen estado);
}
