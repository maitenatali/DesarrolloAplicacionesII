-- =====================================================================
-- Portal Docente (UADEnet) — datos de prueba
-- Ejecutar en Supabase después de schema.sql.
--
-- Los ids externos coinciden con el contrato de Gestión Académica:
-- curso 42 (DDA2-A), asignatura 15, período 8 (2° cuatrimestre 2026),
-- docente-123.
-- =====================================================================

-- Clases con asistencia tomada
insert into clase (curso_id, fecha, observaciones, creado_por) values
  (42, '2026-08-11', null,                                 'docente-123'),
  (42, '2026-08-18', null,                                 'docente-123'),
  (42, '2026-08-25', 'Primer parcial en la segunda mitad', 'docente-123'),
  (42, '2026-09-01', null,                                 'docente-123');

-- alumno-456: 4 presentes (100%, REGULAR)
-- alumno-457: 2 ausentes de 4 (50%, LIBRE)
-- alumno-458: 1 justificado y 3 presentes (100%, REGULAR)
insert into asistencia (clase_id, alumno_id, estado, observacion)
select c.id, v.alumno_id, v.estado, v.observacion
from (values
  ('2026-08-11'::date, 'alumno-456', 'PRESENTE',    null),
  ('2026-08-11'::date, 'alumno-457', 'PRESENTE',    null),
  ('2026-08-11'::date, 'alumno-458', 'PRESENTE',    null),
  ('2026-08-18'::date, 'alumno-456', 'PRESENTE',    null),
  ('2026-08-18'::date, 'alumno-457', 'AUSENTE',     null),
  ('2026-08-18'::date, 'alumno-458', 'JUSTIFICADO', 'Certificado médico'),
  ('2026-08-25'::date, 'alumno-456', 'PRESENTE',    null),
  ('2026-08-25'::date, 'alumno-457', 'AUSENTE',     null),
  ('2026-08-25'::date, 'alumno-458', 'PRESENTE',    null),
  ('2026-09-01'::date, 'alumno-456', 'PRESENTE',    null),
  ('2026-09-01'::date, 'alumno-457', 'PRESENTE',    null),
  ('2026-09-01'::date, 'alumno-458', 'PRESENTE',    null)
) as v (fecha, alumno_id, estado, observacion)
join clase c on c.curso_id = 42 and c.fecha = v.fecha;

-- Exámenes
insert into examen (curso_id, tipo, nombre, descripcion, fecha, hora_inicio, duracion_minutos, modalidad, estado, creado_por) values
  (42, 'PARCIAL_1', 'Primer Parcial',  'Unidades 1 a 4', '2026-08-25', '18:00', 120, 'PRESENCIAL', 'PROGRAMADO', 'docente-123'),
  (42, 'PARCIAL_2', 'Segundo Parcial', null,             '2026-10-14', '18:00', 120, 'PRESENCIAL', 'PROGRAMADO', 'docente-123'),
  (42, 'FINAL',     'Examen final',    null,             '2026-12-03', '18:00', 180, 'PRESENCIAL', 'PROGRAMADO', 'docente-123');

-- Notas del primer parcial
insert into calificacion (examen_id, alumno_id, nota, ausente, cargada_por, cargada_en)
select e.id, v.alumno_id, v.nota, v.ausente, 'docente-123', v.cargada_en
from (values
  ('alumno-456', 8.00, false, '2026-09-01 10:15-03'::timestamptz),
  ('alumno-457', 5.00, false, '2026-09-01 10:16-03'::timestamptz),
  ('alumno-458', null, true,  '2026-09-01 10:16-03'::timestamptz)
) as v (alumno_id, nota, ausente, cargada_en)
join examen e on e.curso_id = 42 and e.tipo = 'PARCIAL_1';

-- Acta del examen final, ya enviada a Gestión Académica.
-- sync_ok = 2: se enviaron los dos alumnos con nota; el ausente no se envía.
-- Se aprueba con 4 o más (mismo criterio que el frontend).
insert into acta (numero, tipo, curso_id, asignatura_id, periodo_id, examen_id,
                  materia, comision, periodo, docente_id, docente_nombre,
                  fecha, observaciones, estado, generada_en, sync_ok, sync_error, sync_en)
select '2026-001', 'FINAL', 42, 15, 8, e.id,
       'Desarrollo de Aplicaciones II', 'DDA2-A', '2° Cuatrimestre 2026', 'docente-123', 'María Gómez',
       '2026-12-03', 'Acta correspondiente al examen final del segundo cuatrimestre de 2026.',
       'GENERADA', '2026-12-03 19:42-03', 2, 0, '2026-12-03 19:43-03'
from examen e
where e.curso_id = 42 and e.tipo = 'FINAL';

insert into acta_detalle (acta_id, orden, alumno_id, alumno_nombre, alumno_legajo, nota, resultado)
select a.id, v.orden, v.alumno_id, v.alumno_nombre, v.alumno_legajo, v.nota, v.resultado
from (values
  (1, 'alumno-456', 'Juan Pérez',      '123456', 8.00, 'APROBADO'),
  (2, 'alumno-457', 'Lucas Fernández', '123458', 3.00, 'DESAPROBADO'),
  (3, 'alumno-458', 'Ana Rodríguez',   '123459', null, 'AUSENTE')
) as v (orden, alumno_id, alumno_nombre, alumno_legajo, nota, resultado)
join acta a on a.numero = '2026-001';
