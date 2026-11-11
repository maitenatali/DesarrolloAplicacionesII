// Búsqueda y orden de alumnos: la MISMA regla en todos los buscadores del portal
// (Estudiantes, Calificaciones, Asistencia, Historial de asistencia). Tests: src/test/studentSearch.test.js.
//
// - Texto: cada término tiene que coincidir con el INICIO de alguna palabra del nombre/apellido
//   ("lu fer" -> Lucas Fernández; "s" NO encuentra "Lucas" por la "s" final). Sin tildes ni mayúsculas.
// - Numérico ("44212", "44.212"): inicio del legajo o del DNI, ignorando puntos y espacios.
// - Vacío: todos.

/** "Fernández" -> "fernandez" (NFD separa la tilde de la letra y se descarta la marca). */
export const normalizeText = (s) =>
  String(s ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

const onlyDigits = (s) => String(s ?? '').replace(/\D/g, '');
const words = (s) => normalizeText(s).split(/[\s'’-]+/).filter(Boolean);

const isNumericQuery = (q) => /^[\d.\s]+$/.test(q) && /\d/.test(q);

/**
 * @param {{name?: string, firstName?: string, lastName?: string, fileNumber?: string, document?: string}} student
 * @param {string} query
 */
export function matchesStudent(student, query) {
  const q = String(query ?? '').trim();
  if (!q) return true;
  if (isNumericQuery(q)) {
    const d = onlyDigits(q);
    return [student.fileNumber, student.document].some((v) => onlyDigits(v).startsWith(d));
  }
  const nameWords = words([student.name, student.firstName, student.lastName].filter(Boolean).join(' '));
  return words(q).every((term) => nameWords.some((w) => w.startsWith(term)));
}

/** `toSearchable(item)` adapta cada pantalla a {name, firstName, lastName, fileNumber, document}. */
export const filterStudents = (list, query, toSearchable = (s) => s) =>
  list.filter((s) => matchesStudent(toSearchable(s), query));

const collator = new Intl.Collator('es', { sensitivity: 'base' });

/** Orden apellido, nombre (sin distinguir tildes ni mayúsculas). Sin apellido, usa el nombre completo. */
export function compareBySurname(a, b) {
  const key = (s) => [s.lastName || s.name || '', s.lastName ? s.firstName || '' : ''];
  const [la, fa] = key(a);
  const [lb, fb] = key(b);
  return collator.compare(la, lb) || collator.compare(fa, fb);
}
