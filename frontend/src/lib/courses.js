import { useParams } from 'react-router-dom';
import { useGetCourseQuery } from '../api/api';
import { campusName, courseRoom } from './domain';

const WD_SHORT = { MONDAY: 'Lun', TUESDAY: 'Mar', WEDNESDAY: 'Mié', THURSDAY: 'Jue', FRIDAY: 'Vie', SATURDAY: 'Sáb', SUNDAY: 'Dom' };
const WD_LONG = {
  MONDAY: 'Lunes', TUESDAY: 'Martes', WEDNESDAY: 'Miércoles', THURSDAY: 'Jueves', FRIDAY: 'Viernes', SATURDAY: 'Sábado', SUNDAY: 'Domingo',
};
const WD_INDEX = { SUNDAY: 0, MONDAY: 1, TUESDAY: 2, WEDNESDAY: 3, THURSDAY: 4, FRIDAY: 5, SATURDAY: 6 };

/** "Lun 18:00–20:00" (varios bloques separados por " · "). */
export function courseSchedule(course, long = false) {
  const blocks = course?.schedule || [];
  if (!blocks.length) return '—';
  return blocks
    .map((s) => `${(long ? WD_LONG : WD_SHORT)[s.weekday] || s.weekday} ${s.startTime}–${s.endTime}`)
    .join(' · ');
}

/** Días de la semana (0=domingo) en que se dicta el curso. */
export const courseWeekdays = (course) => (course?.schedule || []).map((s) => WD_INDEX[s.weekday]).filter((d) => d != null);

/** Datos del curso de la URL (/cursos/:courseId/...) con los campos que muestran los mockups. */
export function useCourse() {
  const { courseId } = useParams();
  const q = useGetCourseQuery(courseId);
  const c = q.data;
  const view = c
    ? {
        id: c.id,
        name: c.subject.name,
        com: c.code,
        period: c.period.label,
        sede: campusName(c.campusId),
        room: courseRoom(c),
        horario: courseSchedule(c),
        students: c.enrolled,
        raw: c,
      }
    : null;
  return { courseId, course: view, ...q };
}
