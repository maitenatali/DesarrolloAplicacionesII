package ar.edu.uade.uadenet.teacher.asistencia;

/** Valores del check de {@code asistencia.estado}. */
public enum EstadoAsistencia {
    PRESENTE,
    AUSENTE,
    /** No cuenta como inasistencia para la regularidad. */
    JUSTIFICADO
}
