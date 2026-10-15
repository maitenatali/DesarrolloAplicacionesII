package ar.edu.uade.uadenet.teacher.acta;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ActaRepository extends JpaRepository<Acta, Long> {

    Optional<Acta> findByNumero(String numero);

    /** Listado de actas de un docente, la más reciente primero. */
    List<Acta> findByDocenteIdOrderByGeneradaEnDesc(String docenteId);

    /** Filtro por período de la pantalla de actas. */
    List<Acta> findByDocenteIdAndPeriodoIdOrderByGeneradaEnDesc(String docenteId, Long periodoId);

    List<Acta> findByCursoIdOrderByGeneradaEnDesc(Long cursoId);

    /**
     * Última acta del año, para calcular el próximo número:
     * {@code findTopByNumeroStartingWithOrderByNumeroDesc("2026-")} → "2026-007" → siguiente "2026-008".
     */
    Optional<Acta> findTopByNumeroStartingWithOrderByNumeroDesc(String prefijo);

    /**
     * Para validar "Ya existe un acta generada" antes de guardar.
     * En actas de cursada usar {@link #existsByCursoIdAndTipoAndExamenIsNullAndEstado}.
     */
    boolean existsByCursoIdAndTipoAndExamenIdAndEstado(Long cursoId, TipoActa tipo, Long examenId, EstadoActa estado);

    boolean existsByCursoIdAndTipoAndExamenIsNullAndEstado(Long cursoId, TipoActa tipo, EstadoActa estado);
}
