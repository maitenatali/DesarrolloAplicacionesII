import { describe, expect, it } from 'vitest';
import { compareBySurname, filterStudents, matchesStudent, normalizeText } from '../lib/studentSearch';

const st = (firstName, lastName, fileNumber, document) => ({
  firstName,
  lastName,
  name: `${firstName} ${lastName}`,
  fileNumber,
  document,
});

// Nombres con "s" en el medio o al final (Lucas, Tomás, Rosa...) que NO tienen que aparecer al buscar "s".
const LIST = [
  st('Camila', 'Sosa', '124107', '44210137'),
  st('Lautaro', 'Silva', '124114', '44210274'),
  st('Lucas', 'Fernández', '124121', '44212411'),
  st('Joaquín', 'Pérez', '124128', '44210548'),
  st('Tomás', 'Benítez', '124135', '44210685'),
  st('Rosa', 'Castro', '124142', '44210822'),
  st('Agustina', 'Ramos', '124149', '44210959'),
];
const names = (query) => filterStudents(LIST, query).map((s) => s.name);

describe('matchesStudent — texto', () => {
  it('matchea por inicio de palabra, no por substring', () => {
    expect(names('s')).toEqual(['Camila Sosa', 'Lautaro Silva']);
    expect(names('sil')).toEqual(['Lautaro Silva']);
    expect(names('ilva')).toEqual([]);
  });
  it('cada término tiene que matchear el inicio de alguna palabra', () => {
    expect(names('lu fer')).toEqual(['Lucas Fernández']);
    expect(names('fer lu')).toEqual(['Lucas Fernández']);
    expect(names('lu sil')).toEqual([]);
  });
  it('ignora tildes y mayúsculas, en la búsqueda y en el nombre', () => {
    expect(names('fernandez')).toEqual(['Lucas Fernández']);
    expect(names('joaquin')).toEqual(['Joaquín Pérez']);
    expect(names('PÉREZ')).toEqual(['Joaquín Pérez']);
    expect(normalizeText('Benítez')).toBe('benitez');
  });
  it('búsqueda vacía o solo espacios -> todos', () => {
    expect(names('')).toHaveLength(LIST.length);
    expect(names('   ')).toHaveLength(LIST.length);
    expect(matchesStudent(LIST[0], undefined)).toBe(true);
  });
  it('funciona con solo el nombre completo (Calificaciones / Asistencia)', () => {
    expect(matchesStudent({ name: 'Lucas Fernández' }, 'lu fer')).toBe(true);
    expect(matchesStudent({ name: 'Lucas Fernández' }, 's')).toBe(false);
  });
});

describe('matchesStudent — numérico', () => {
  it('busca por inicio de legajo o DNI ignorando los puntos', () => {
    expect(names('44212')).toEqual(['Lucas Fernández']);
    expect(names('44.212')).toEqual(names('44212'));
    expect(matchesStudent({ name: 'X', document: '44.212.411' }, '44212')).toBe(true);
    expect(names('12412')).toEqual(['Lucas Fernández', 'Joaquín Pérez']); // legajo
    expect(names('212')).toEqual([]); // no es inicio de ningún legajo ni DNI
  });
});

describe('compareBySurname', () => {
  it('ordena por apellido y después por nombre, sin importar tildes', () => {
    const sorted = [...LIST, st('Ana', 'Pérez', '1', '1')].sort(compareBySurname).map((s) => s.name);
    expect(sorted).toEqual([
      'Tomás Benítez',
      'Rosa Castro',
      'Lucas Fernández',
      'Ana Pérez',
      'Joaquín Pérez',
      'Agustina Ramos',
      'Lautaro Silva',
      'Camila Sosa',
    ]);
  });
});
