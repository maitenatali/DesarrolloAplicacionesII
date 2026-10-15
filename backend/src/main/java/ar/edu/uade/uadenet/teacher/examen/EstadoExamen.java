package ar.edu.uade.uadenet.teacher.examen;

/**
 * Valores del check de {@code examen.estado}.
 * "Próximo" y "Realizado" no son estados: se calculan comparando la fecha con hoy.
 */
public enum EstadoExamen {
    PROGRAMADO,
    CANCELADO
}
