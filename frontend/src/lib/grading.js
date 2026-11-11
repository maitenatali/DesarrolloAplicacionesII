// Situación académica del alumno (régimen de Examen Final Obligatorio, UADE).
// ESPEJO de `backend/app/services/rules.py::academic_situation`: mismas reglas y mismos casos de test
// (src/test/grading.test.js). El backend es la fuente de verdad: vuelve a validar al guardar.
//
// - 2 parciales, se aprueban con >= 4. Ausente = desaprobado.
// - UN recuperatorio, solo si exactamente un parcial está desaprobado/ausente. Su nota REEMPLAZA a la del
//   parcial que recupera. Recuperatorio < 4 o ausente -> recursa. Ambos parciales desaprobados -> recursa.
// - Cursada = (P1 ef. + P2 ef.) / 2. El final se habilita solo con la cursada aprobada.
// - Nota final = (cursada + final) / 2, solo si final >= 4. Si falta algo -> null ("—"), nunca un promedio parcial.
// - TP y otros tipos no entran al cálculo. TODO(docentes): definir si los TP pesan en la cursada.
// - Las notas calculadas se TRUNCAN a 2 decimales.

export const SLOT = { P1: 'P1', P2: 'P2', RECUP: 'RECUP', FINAL: 'FINAL' };

export const STATUS = {
  CURSANDO: 'CURSANDO',
  DEBE_RECUPERAR_P1: 'DEBE_RECUPERAR_P1',
  DEBE_RECUPERAR_P2: 'DEBE_RECUPERAR_P2',
  RECURSA: 'RECURSA',
  LIBRE: 'LIBRE',
  PENDIENTE_FINAL: 'PENDIENTE_FINAL',
  FINAL_DESAPROBADO: 'FINAL_DESAPROBADO',
  APROBADA: 'APROBADA',
};

export const STATUS_LABEL = {
  CURSANDO: 'Cursando',
  DEBE_RECUPERAR_P1: 'Debe recuperar P1',
  DEBE_RECUPERAR_P2: 'Debe recuperar P2',
  RECURSA: 'Recursa',
  LIBRE: 'Libre por asistencia',
  PENDIENTE_FINAL: 'Pendiente de final',
  FINAL_DESAPROBADO: 'Final desaprobado',
  APROBADA: 'Aprobada',
};

/** Clase del badge de la pantalla 09 (aprobado | desaprobado | pendiente). */
export const STATUS_BADGE = {
  CURSANDO: 'pendiente',
  DEBE_RECUPERAR_P1: 'pendiente',
  DEBE_RECUPERAR_P2: 'pendiente',
  PENDIENTE_FINAL: 'pendiente',
  RECURSA: 'desaprobado',
  LIBRE: 'desaprobado',
  FINAL_DESAPROBADO: 'desaprobado',
  APROBADA: 'aprobado',
};

const PASSING_CENTS = 400;

/** Qué lugar ocupa un tipo de examen en el cálculo (RECUP_1/RECUP_2 = tipos viejos del recuperatorio). */
export function examSlot(type, finalTypes = ['FINAL']) {
  const t = String(type || '').toUpperCase();
  if (t === 'PARCIAL_1') return SLOT.P1;
  if (t === 'PARCIAL_2') return SLOT.P2;
  if (t.startsWith('RECUP')) return SLOT.RECUP;
  if (finalTypes.map((f) => f.toUpperCase()).includes(t)) return SLOT.FINAL;
  return null;
}

const loaded = (m) => m != null && (m.absent || m.grade != null);
// Las notas tienen hasta 2 decimales: se calcula en centésimos enteros para no arrastrar errores de float.
const cents = (grade) => Math.round(Number(grade) * 100);
const passed = (m) => !m.absent && m.grade != null && cents(m.grade) >= PASSING_CENTS;

/**
 * @param {{p1?: Mark, p2?: Mark, recup?: Mark, final?: Mark}} alumno  Mark = {grade: number|null, absent: bool} | null
 * @param {{condition?: 'REGULAR'|'LIBRE'|null}} [opts]  condición por asistencia; null = desconocida
 * @returns {{p1Efectivo, p2Efectivo, recupera, notaCursada, notaFinal, estado, camposHabilitados: {recuperatorio, final}}}
 */
export function calcularSituacion(alumno, { condition = null } = {}) {
  const p1 = loaded(alumno.p1) ? alumno.p1 : null;
  const p2 = loaded(alumno.p2) ? alumno.p2 : null;
  const recup = loaded(alumno.recup) ? alumno.recup : null;
  const final = loaded(alumno.final) ? alumno.final : null;
  let p1e = p1 && p1.grade != null ? cents(p1.grade) : null;
  let p2e = p2 && p2.grade != null ? cents(p2.grade) : null;

  const result = (estado, { recupera = null, cursadaX2 = null, finalX4 = null } = {}) => {
    let est = estado;
    let notaFinal = finalX4 == null ? null : Math.floor(finalX4 / 4) / 100;
    if (condition === 'LIBRE') {
      est = STATUS.LIBRE;
      notaFinal = null;
    }
    return {
      p1Efectivo: p1e == null ? null : p1e / 100,
      p2Efectivo: p2e == null ? null : p2e / 100,
      recupera,
      notaCursada: cursadaX2 == null ? null : Math.floor(cursadaX2 / 2) / 100,
      notaFinal,
      estado: est,
      camposHabilitados: { recuperatorio: recupera != null, final: cursadaX2 != null },
    };
  };

  if (!p1 || !p2) return result(STATUS.CURSANDO);
  const ok1 = passed(p1);
  const ok2 = passed(p2);
  if (!ok1 && !ok2) return result(STATUS.RECURSA);
  let recupera = null;
  if (!(ok1 && ok2)) {
    recupera = ok1 ? SLOT.P2 : SLOT.P1;
    if (!recup) return result(recupera === SLOT.P1 ? STATUS.DEBE_RECUPERAR_P1 : STATUS.DEBE_RECUPERAR_P2, { recupera });
    if (!passed(recup)) return result(STATUS.RECURSA, { recupera });
    if (recupera === SLOT.P1) p1e = cents(recup.grade);
    else p2e = cents(recup.grade);
  }
  const cursadaX2 = p1e + p2e;
  if (!final || final.absent || final.grade == null) return result(STATUS.PENDIENTE_FINAL, { recupera, cursadaX2 });
  if (cents(final.grade) < PASSING_CENTS) return result(STATUS.FINAL_DESAPROBADO, { recupera, cursadaX2 });
  // (cursada + final) / 2 = (cursadaX2 / 2 + final) / 2 = (cursadaX2 + 2 * final) / 4
  return result(STATUS.APROBADA, { recupera, cursadaX2, finalX4: cursadaX2 + 2 * cents(final.grade) });
}

/**
 * Situación a partir de los exámenes NO cancelados del curso (en orden de fecha) y una función que devuelve
 * la calificación del alumno en cada uno. Si hay más de un examen por lugar, cuenta el primero con nota.
 */
export function situacionDesdeExamenes(exams, markOf, opts) {
  const alumno = {};
  const key = { P1: 'p1', P2: 'p2', RECUP: 'recup', FINAL: 'final' };
  exams.forEach((e) => {
    const slot = examSlot(e.type);
    const m = markOf(e);
    if (slot && loaded(m) && !alumno[key[slot]]) alumno[key[slot]] = m;
  });
  return calcularSituacion(alumno, opts);
}
