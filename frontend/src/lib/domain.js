// Traducciones de valores de la API (enums en español/inglés) a textos de la UI de los mockups.
import { dateTimeParts } from './format';

// TODO(GA): Gestión Académica todavía no publica el catálogo de sedes/aulas; mientras tanto se usa este.
const CAMPUS = { 1: 'Belgrano', 2: 'Monserrat', 3: 'Recoleta', 4: 'Pinamar', 5: 'Costa Argentina' };
export const campusName = (id) => (id == null ? '—' : CAMPUS[id] || `Sede ${id}`);
export const roomLabel = (roomId) => (roomId == null ? '—' : String(roomId));

export const courseRoom = (course) => roomLabel(course?.schedule?.[0]?.roomId);

export const COURSE_STATUS = {
  EN_CURSO: 'Activo',
  PROGRAMADO: 'Próximo',
  FINALIZADO: 'Finalizado',
  CANCELADO: 'Cancelado',
};
export const isActiveCourse = (c) => c?.status === 'EN_CURSO';

export const MODALITY = { PRESENCIAL: 'Presencial', VIRTUAL: 'Virtual', HIBRIDA: 'Híbrida' };

/** Nombre corto del tipo de examen como en los mockups (Parcial 1, Recuperatorio Parcial 1, TP1, Final). */
export const EXAM_TYPE_LABEL = {
  PARCIAL_1: 'Parcial 1',
  PARCIAL_2: 'Parcial 2',
  RECUP_1: 'Recuperatorio Parcial 1',
  RECUP_2: 'Recuperatorio Parcial 2',
  TP_1: 'TP1',
  TP_2: 'TP2',
  FINAL: 'Final',
};
export const examTypeLabel = (type, fallback) => EXAM_TYPE_LABEL[type] || fallback || type;

/** Estado visible del examen: cancelado > próximo > realizado. */
export function examStatus(exam) {
  if (!exam) return 'proximo';
  if (exam.status === 'CANCELADO') return 'cancelado';
  return exam.phase === 'UPCOMING' || exam.phase === 'IN_PROGRESS' ? 'proximo' : 'realizado';
}
export const EXAM_STATUS_LABEL = { proximo: 'Próximo', realizado: 'Realizado', cancelado: 'Cancelado' };

export const examTimeRange = (exam) => (exam ? `${exam.startTime} – ${exam.endTime}` : '—');

export const ATTENDANCE_LABEL = { PRESENTE: 'Presente', AUSENTE: 'Ausente', JUSTIFICADO: 'Justificado' };

export const RESULT_LABEL = {
  APROBADO: 'Aprobado',
  DESAPROBADO: 'Desaprobado',
  AUSENTE: 'Ausente',
  REGULAR: 'Regular',
  LIBRE: 'Libre',
};

export const ACTA_TYPE_LABEL = { CURSADA: 'Cursada', FINAL: 'Final' };
export const ACTA_STATUS_LABEL = { GENERADA: 'Generada', ANULADA: 'Anulada' };

/** Ítem de GET /calendar -> categoría de los mockups (examen | evento | comedor | feriado). */
export function calendarCategory(item) {
  switch (item.kind) {
    case 'EXAM':
      return 'examen';
    case 'DINING_RESERVATION':
      return 'comedor';
    case 'HOLIDAY':
      return 'feriado';
    default:
      return 'evento';
  }
}

export const CATEGORY_LABEL = { examen: 'Examen', feriado: 'Feriado nacional', comedor: 'Comedor', evento: 'Evento académico' };

/** Día (YYYY-MM-DD) y hora local de un ítem del calendario (los turnos de examen vienen como rango de días). */
export function calendarItemTimes(item) {
  if (item.start) {
    const s = dateTimeParts(item.start);
    const e = item.end ? dateTimeParts(item.end) : null;
    return { day: s.day, time: s.time, endTime: e?.time || null, endDay: e?.day || s.day };
  }
  return { day: item.startDate, time: null, endTime: null, endDay: item.endDate || item.startDate };
}
