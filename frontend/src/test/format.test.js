import { describe, expect, it } from 'vitest';
import { calendarCategory, examStatus } from '../lib/domain';
import { dni, grade, initials, longDate, money, shortDate } from '../lib/format';

describe('format', () => {
  it('formatea dinero como en los mockups', () => {
    expect(money('15000.00')).toBe('$15.000');
    expect(money('1500.50')).toBe('$1.500,50');
    expect(money(-4500, { sign: true })).toBe('− $4.500');
  });
  it('formatea fechas YYYY-MM-DD sin corrimiento de zona horaria', () => {
    expect(longDate('2026-10-14')).toBe('14 de octubre de 2026');
    expect(shortDate('2026-08-05')).toBe('05/08/2026');
  });
  it('formatea notas, DNI e iniciales', () => {
    expect(grade(8)).toBe('8');
    expect(grade(7.5)).toBe('7,5');
    expect(grade(null)).toBe('—');
    expect(dni('40123456')).toBe('40.123.456');
    expect(initials('María Gómez')).toBe('MG');
  });
});

describe('domain', () => {
  it('deriva el estado visible del examen', () => {
    expect(examStatus({ status: 'CANCELADO', phase: 'UPCOMING' })).toBe('cancelado');
    expect(examStatus({ status: 'PROGRAMADO', phase: 'UPCOMING' })).toBe('proximo');
    expect(examStatus({ status: 'PROGRAMADO', phase: 'COMPLETED' })).toBe('realizado');
  });
  it('mapea los ítems del calendario a las categorías del mockup', () => {
    expect(calendarCategory({ kind: 'EXAM' })).toBe('examen');
    expect(calendarCategory({ kind: 'DINING_RESERVATION' })).toBe('comedor');
    expect(calendarCategory({ kind: 'ACADEMIC_EVENT' })).toBe('evento');
  });
});
