import { describe, expect, it } from 'vitest';
import { calcularSituacion, examSlot, situacionDesdeExamenes, STATUS } from '../lib/grading';
import { grade } from '../lib/format';

const AUS = 'AUS';
const mark = (v) => (v == null ? null : v === AUS ? { grade: null, absent: true } : { grade: v, absent: false });
const sit = (p1, p2, recup = null, final = null, opts) =>
  calcularSituacion({ p1: mark(p1), p2: mark(p2), recup: mark(recup), final: mark(final) }, opts);

// Misma tabla que backend/tests/unit/test_rules.py::test_academic_situation_table
describe('calcularSituacion — tabla de aceptación', () => {
  it.each([
    [7, 8, null, null, '7,5', '—', STATUS.PENDIENTE_FINAL],
    [2, 4, 4, 4, '4', '4', STATUS.APROBADA],
    [2, 4, 3, null, '—', '—', STATUS.RECURSA],
    [2, 3, null, null, '—', '—', STATUS.RECURSA],
    [5, 4, null, null, '4,5', '—', STATUS.PENDIENTE_FINAL],
    [6, 5, null, 2, '5,5', '—', STATUS.FINAL_DESAPROBADO],
    [AUS, 6, 5, 6, '5,5', '5,75', STATUS.APROBADA],
    [8, 9, null, 9, '8,5', '8,75', STATUS.APROBADA],
  ])('P1 %s · P2 %s · Recu %s · Final %s → cursada %s, final %s, %s', (p1, p2, recup, final, cursada, notaFinal, estado) => {
    const s = sit(p1, p2, recup, final);
    expect(s.estado).toBe(estado);
    expect(grade(s.notaCursada)).toBe(cursada);
    expect(grade(s.notaFinal)).toBe(notaFinal);
  });
});

describe('calcularSituacion — reglas', () => {
  it('el recuperatorio reemplaza solo al parcial desaprobado e indica cuál', () => {
    expect(sit(2, 4, 4)).toMatchObject({ recupera: 'P1', p1Efectivo: 4, p2Efectivo: 4 });
    expect(sit(8, AUS, 6)).toMatchObject({ recupera: 'P2', p1Efectivo: 8, p2Efectivo: 6, notaCursada: 7 });
  });

  it('habilita campos según las reglas', () => {
    expect(sit(2, 3).camposHabilitados).toEqual({ recuperatorio: false, final: false });
    expect(sit(7, 8).camposHabilitados).toEqual({ recuperatorio: false, final: true });
    expect(sit(7, 3)).toMatchObject({ estado: STATUS.DEBE_RECUPERAR_P2, camposHabilitados: { recuperatorio: true, final: false } });
    expect(sit(AUS, 7)).toMatchObject({ estado: STATUS.DEBE_RECUPERAR_P1, recupera: 'P1' });
    expect(sit(7, 3, 5).camposHabilitados).toEqual({ recuperatorio: true, final: true });
  });

  it('sin notas, faltantes o notas que ya no corresponden', () => {
    expect(sit(null, null).estado).toBe(STATUS.CURSANDO);
    expect(sit(2, null).estado).toBe(STATUS.CURSANDO);
    expect(sit(7, 8, 2)).toMatchObject({ estado: STATUS.PENDIENTE_FINAL, notaCursada: 7.5 }); // recu ignorado
    expect(sit(2, 3, null, 9)).toMatchObject({ estado: STATUS.RECURSA, notaFinal: null, notaCursada: null });
  });

  it('ausente en recuperatorio o final', () => {
    expect(sit(2, 7, AUS).estado).toBe(STATUS.RECURSA);
    expect(sit(7, 8, null, AUS)).toMatchObject({ estado: STATUS.PENDIENTE_FINAL, notaFinal: null });
  });

  it('bordes y truncado a 2 decimales (sin redondear)', () => {
    expect(sit(4, 4, null, 4).estado).toBe(STATUS.APROBADA);
    expect(sit(3.99, 4).estado).toBe(STATUS.DEBE_RECUPERAR_P1);
    expect(sit(4, 4, null, 3.99).estado).toBe(STATUS.FINAL_DESAPROBADO);
    const s = sit(7.25, 8.5, null, 8); // cursada 7,875 -> 7,87; final 7,9375 -> 7,93
    expect([grade(s.notaCursada), grade(s.notaFinal)]).toEqual(['7,87', '7,93']);
  });

  it('LIBRE por asistencia le gana al estado de notas', () => {
    expect(sit(9, 9, null, 9, { condition: 'LIBRE' })).toMatchObject({ estado: STATUS.LIBRE, notaFinal: null, notaCursada: 9 });
    expect(sit(9, 9, null, null, { condition: 'REGULAR' }).estado).toBe(STATUS.PENDIENTE_FINAL);
  });
});

describe('situacionDesdeExamenes', () => {
  it('ubica cada examen por tipo e ignora los TP', () => {
    const exams = [
      { id: 1, type: 'PARCIAL_1' },
      { id: 2, type: 'TP_1' },
      { id: 3, type: 'PARCIAL_2' },
      { id: 4, type: 'RECUPERATORIO' },
      { id: 5, type: 'FINAL' },
    ];
    const marks = { 1: mark(8), 2: mark(1), 3: mark(AUS), 4: mark(6), 5: mark(7) };
    const s = situacionDesdeExamenes(exams, (e) => marks[e.id]);
    expect(s).toMatchObject({ recupera: 'P2', estado: STATUS.APROBADA, notaFinal: 7 });
    expect([examSlot('RECUP_2'), examSlot('TP_1'), examSlot('parcial_1')]).toEqual(['RECUP', null, 'P1']);
  });
});
