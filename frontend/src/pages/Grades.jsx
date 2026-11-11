import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetGradeMatrixQuery, useSaveExamGradesMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseHero, CourseLoadState, CourseTabs, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import { useCourse } from '../lib/courses';
import { examTypeLabel } from '../lib/domain';
import { grade as fmtGrade } from '../lib/format';
import { examSlot, SLOT, situacionDesdeExamenes, STATUS_BADGE, STATUS_LABEL } from '../lib/grading';
import { filterStudents } from '../lib/studentSearch';
import useLockScroll from '../lib/useBodyClass';
import useToast from '../lib/useToast';
import '../styles/pages/09.css';

// Valor del input: número (coma o punto) o "A" = ausente. Vacío = sin nota.
const cellText = (g) => (!g ? '' : g.absent ? 'A' : g.grade == null ? '' : fmtGrade(g.grade));

function parseCell(text) {
  const v = text.trim();
  if (v === '') return { ok: true, value: { grade: null, absent: false } };
  if (/^a(usente)?$/i.test(v)) return { ok: true, value: { grade: null, absent: true } };
  if (!/^\d{1,2}([.,]\d{1,2})?$/.test(v)) return { ok: false, error: 'Ingresá una nota de 0 a 10 con hasta 2 decimales.' };
  const n = Number(v.replace(',', '.'));
  if (n < 0 || n > 10) return { ok: false, error: 'La calificación debe estar entre 0 y 10.' };
  return { ok: true, value: { grade: n, absent: false } };
}
const markOf = (text) => {
  const p = parseCell(text);
  return p.ok ? p.value : null;
};

// Orden de guardado: primero los parciales, al final recuperatorio y final (el backend valida que estén
// habilitados contra las notas YA guardadas de los demás exámenes).
const SAVE_ORDER = { [SLOT.P1]: 0, [SLOT.P2]: 1, [SLOT.RECUP]: 3, [SLOT.FINAL]: 4 };
const saveOrder = (exam) => SAVE_ORDER[examSlot(exam.type)] ?? 2;

const BLOCKED_MSG = {
  [SLOT.RECUP]: 'No corresponde recuperatorio: tiene que haber exactamente un parcial desaprobado o ausente.',
  [SLOT.FINAL]: 'El final requiere la cursada aprobada.',
};

/** ¿La celda de recuperatorio / final está habilitada para la situación dada? Los demás exámenes, siempre. */
const isEnabled = (slot, sit) =>
  slot === SLOT.RECUP ? sit.camposHabilitados.recuperatorio : slot === SLOT.FINAL ? sit.camposHabilitados.final : true;

function GradeInput({ value, original, label, disabled, blocked, hint, onChange }) {
  const parsed = parseCell(value);
  const isDirty = value !== original;
  const error = !parsed.ok ? parsed.error : blocked && value !== '' ? blocked : null;
  return (
    <>
      <input
        type="text"
        inputMode="decimal"
        className={`grade-input${value === '' ? ' empty' : ''}${error ? ' invalid' : ''}${isDirty && !error ? ' dirty' : ''}`}
        value={value}
        placeholder="—"
        maxLength={5}
        aria-label={label}
        title={blocked && value === '' ? blocked : 'Nota de 0 a 10, o A si estuvo ausente'}
        disabled={disabled}
        onChange={(ev) => onChange(ev.target.value)}
      />
      {error && <span className="grade-error">{error}</span>}
      {!error && hint && <span className="student-legajo">{hint}</span>}
    </>
  );
}

export default function Grades() {
  const navigate = useNavigate();
  const q = useCourse();
  const { courseId, course } = q;
  const matrix = useGetGradeMatrixQuery(courseId);
  const [save, { isLoading: saving }] = useSaveExamGradesMutation();
  const [edits, setEdits] = useState({}); // `${studentId}|${examId}` -> texto
  const [search, setSearch] = useState('');
  const [discardOpen, setDiscardOpen] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [confirm, setConfirm] = useState(null); // notas que una corrección deja sin efecto
  const [toast, showToast] = useToast(2800);
  useLockScroll(discardOpen || !!confirm);

  const exams = useMemo(() => (matrix.data?.exams || []).filter((e) => e.phase !== 'CANCELLED'), [matrix.data]);
  const rows = matrix.data?.rows || [];
  const readOnly = course?.raw.status === 'FINALIZADO' || course?.raw.status === 'CANCELADO';

  if (!course) {
    return (
      <AppShell scope="09" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId, { label: 'Calificaciones' })} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const key = (sid, eid) => `${sid}|${eid}`;
  const original = (row, exam) => cellText(row.grades[String(exam.id)]);
  const text = (row, exam) => edits[key(row.studentId, exam.id)] ?? original(row, exam);
  const isEdited = (row, exam) => text(row, exam) !== original(row, exam);
  const changed = rows.flatMap((r) => exams.filter((e) => isEdited(r, e)).map((e) => ({ r, e })));
  const dirty = changed.length > 0;

  // Misma función para la vista previa (con lo que está tipeado) y para validar al guardar.
  const situation = (row, read = text) =>
    situacionDesdeExamenes(exams, (e) => markOf(read(row, e)), { condition: row.condition });

  // Cargar recuperatorio / final a quien no le corresponde es un error del docente: bloquea el guardado.
  const blockedOf = (row, exam, sit = situation(row)) => {
    const slot = examSlot(exam.type);
    return isEnabled(slot, sit) ? null : BLOCKED_MSG[slot];
  };
  const invalid = changed.filter(({ r, e }) => !parseCell(text(r, e)).ok || (text(r, e) !== '' && blockedOf(r, e)));

  // Notas YA guardadas (no editadas) que una corrección deja sin efecto: se avisa y, si confirma, se borran.
  const invalidated = () =>
    rows.flatMap((r) => {
      if (!exams.some((e) => isEdited(r, e))) return [];
      const before = situation(r, original);
      const after = situation(r);
      return exams
        .filter((e) => !isEdited(r, e) && original(r, e) !== '')
        .flatMap((e) => {
          const slot = examSlot(e.type);
          if (slot !== SLOT.RECUP && slot !== SLOT.FINAL) return [];
          let reason = null;
          if (isEnabled(slot, before) && !isEnabled(slot, after)) {
            reason = slot === SLOT.RECUP ? 'ya no corresponde recuperatorio' : 'la cursada deja de estar aprobada';
          } else if (slot === SLOT.RECUP && before.recupera && after.recupera && before.recupera !== after.recupera) {
            reason = `el recuperatorio pasaría a reemplazar a ${after.recupera} en lugar de ${before.recupera}`;
          }
          return reason ? [{ r, e, reason }] : [];
        });
    });

  const doSave = async (toClear = []) => {
    setConfirm(null);
    setSaveError(null);
    const byExam = new Map();
    const add = (e, entry) => {
      if (!byExam.has(e.id)) byExam.set(e.id, { exam: e, entries: [] });
      byExam.get(e.id).entries.push(entry);
    };
    changed.forEach(({ r, e }) => add(e, { studentId: r.studentId, ...parseCell(text(r, e)).value }));
    toClear.forEach(({ r, e }) => add(e, { studentId: r.studentId, grade: null, absent: false }));
    const batches = [...byExam.values()].sort((a, b) => saveOrder(a.exam) - saveOrder(b.exam));
    try {
      for (const { exam, entries } of batches) {
        // eslint-disable-next-line no-await-in-loop
        await save({ courseId, examId: exam.id, entries }).unwrap();
      }
      setEdits({});
      showToast('Calificaciones actualizadas correctamente.');
    } catch (err) {
      setSaveError(toApiError(err).detail);
    }
  };

  const onSave = () => {
    if (invalid.length) {
      document.querySelector('.pg-09 .grade-input.invalid')?.focus();
      return;
    }
    const warnings = invalidated();
    if (warnings.length) setConfirm(warnings);
    else doSave();
  };

  const filtered = filterStudents(rows, search, (r) => ({ name: r.studentName, fileNumber: r.fileNumber }));

  const cell = (row, exam, sit) => {
    const value = text(row, exam);
    const blocked = blockedOf(row, exam, sit);
    const isRecup = examSlot(exam.type) === SLOT.RECUP;
    return (
      <GradeInput
        value={value}
        original={original(row, exam)}
        label={`${examTypeLabel(exam.type, exam.name)} de ${row.studentName}`}
        // Bloqueado si no corresponde; si ya tenía nota queda editable para poder borrarla.
        disabled={readOnly || (!!blocked && value === '')}
        blocked={blocked}
        hint={isRecup && sit.recupera ? `Recupera ${sit.recupera}` : null}
        onChange={(v) => setEdits((m) => ({ ...m, [key(row.studentId, exam.id)]: v }))}
      />
    );
  };

  const computed = (sit) => [
    { label: 'Cursada', value: sit.notaCursada },
    { label: 'Nota final', value: sit.notaFinal },
  ];
  const statusBadge = (sit) => <span className={`badge ${STATUS_BADGE[sit.estado]}`}>{STATUS_LABEL[sit.estado]}</span>;

  let matrixContent;
  if (matrix.isLoading) {
    matrixContent = <div className="skel" style={{ width: '100%', height: 120 }} />;
  } else if (matrix.isError) {
    matrixContent = (
      <div className="page-error-banner">
        <span className="state-icon">
          <I.i3 />
        </span>
        <p className="state-title">No pudimos cargar las calificaciones</p>
        <p className="state-desc">{toApiError(matrix.error).detail}</p>
        <button className="btn-primary" style={{ marginTop: 4 }} onClick={() => matrix.refetch()}>
          Reintentar
        </button>
      </div>
    );
  } else if (!exams.length) {
    matrixContent = (
      <div className="empty-state">
        <I.i39 />
        <p>No hay evaluaciones creadas</p>
        <p className="state-sub">Creá una evaluación para comenzar a cargar calificaciones.</p>
        <button className="btn-primary" style={{ marginTop: 8 }} onClick={() => navigate(`/cursos/${courseId}/examenes/nuevo`)}>
          <I.i51 />
          Nueva evaluación
        </button>
      </div>
    );
  } else if (!rows.length) {
    matrixContent = (
      <div className="empty-state">
        <I.i37 />
        <p>No hay estudiantes registrados</p>
        <p className="state-sub">No hay estudiantes disponibles para cargar calificaciones.</p>
      </div>
    );
  } else if (!filtered.length) {
    matrixContent = (
      <div className="empty-state">
        <I.i29 />
        <p>No encontramos resultados</p>
        <p className="state-sub">Probá modificando la búsqueda.</p>
        <button className="btn-secondary" style={{ marginTop: 8 }} onClick={() => setSearch('')}>
          Limpiar búsqueda
        </button>
      </div>
    );
  } else {
    matrixContent = (
      <table className="grades-table">
        <thead>
          <tr>
            <th className="col-student">Estudiante</th>
            {exams.map((e) => (
              <th className="eval-head" key={e.id}>
                {examTypeLabel(e.type, e.name)}
              </th>
            ))}
            <th style={{ textAlign: 'center' }}>Cursada</th>
            <th style={{ textAlign: 'center' }}>Nota final</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => {
            const sit = situation(r);
            return (
              <tr key={r.studentId}>
                <td className="col-student">
                  <p className="student-name">{r.studentName}</p>
                  <p className="student-legajo">Legajo {r.fileNumber}</p>
                </td>
                {exams.map((e) => (
                  <td className="grade-cell" key={e.id}>
                    {cell(r, e, sit)}
                  </td>
                ))}
                {computed(sit).map((c) => (
                  <td className="avg-col" key={c.label}>
                    <span className={`avg-cell${c.value == null ? ' empty' : ''}`}>{fmtGrade(c.value)}</span>
                  </td>
                ))}
                <td>{statusBadge(sit)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  const showTable = !matrix.isLoading && !matrix.isError && exams.length > 0;

  return (
    <AppShell
      scope="09"
      active="cursos"
      after={
        <>
          <div className={`modal-backdrop${discardOpen ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setDiscardOpen(false)}>
            <div className="modal-card">
              <div className="modal-body">
                <span className="modal-icon">
                  <I.i53 />
                </span>
                <p className="modal-title">¿Descartar cambios?</p>
                <p className="modal-text">Los cambios realizados todavía no fueron guardados. ¿Querés descartarlos?</p>
              </div>
              <div className="modal-foot">
                <button className="btn-secondary" onClick={() => setDiscardOpen(false)}>
                  Continuar editando
                </button>
                <button
                  className="btn-danger-ghost"
                  onClick={() => {
                    setEdits({});
                    setSaveError(null);
                    setDiscardOpen(false);
                  }}
                >
                  Descartar cambios
                </button>
              </div>
            </div>
          </div>
          <div className={`modal-backdrop${confirm ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setConfirm(null)}>
            <div className="modal-card">
              <div className="modal-body">
                <span className="modal-icon">
                  <I.i53 />
                </span>
                <p className="modal-title">Hay notas que quedan sin efecto</p>
                <p className="modal-text">Con los cambios que hiciste, estas notas ya cargadas dejan de corresponder:</p>
                <ul className="modal-text" style={{ textAlign: 'left', margin: '8px 0 0', paddingLeft: 18 }}>
                  {(confirm || []).map(({ r, e, reason }) => (
                    <li key={key(r.studentId, e.id)}>
                      {r.studentName} — {examTypeLabel(e.type, e.name)} ({original(r, e)}): {reason}.
                    </li>
                  ))}
                </ul>
                <p className="modal-text">Si continuás, se guardan tus cambios y esas notas se borran.</p>
              </div>
              <div className="modal-foot">
                <button className="btn-secondary" onClick={() => setConfirm(null)}>
                  Volver a editar
                </button>
                <button className="btn-danger-ghost" disabled={saving} onClick={() => doSave(confirm)}>
                  Guardar y borrar esas notas
                </button>
              </div>
            </div>
          </div>
          <div className={`toast${toast.show ? ' show' : ''}`}>
            <I.i46 />
            <span>{toast.message || 'Calificaciones actualizadas correctamente.'}</span>
          </div>
        </>
      }
    >
      <Breadcrumb trail={courseTrail(course, courseId, { label: 'Calificaciones' })} />
      <div>
        <CourseHero course={course} />
        <CourseTabs courseId={courseId} active="calificaciones" />
        <div className="section-head">
          <div className="section-head-main">
            <h2>Calificaciones</h2>
            <p>Gestioná las calificaciones de los estudiantes del curso.</p>
          </div>
          {!readOnly && (
            <button className="btn-primary" onClick={() => navigate(`/cursos/${courseId}/examenes/nuevo`)}>
              <I.i51 />
              Nueva evaluación
            </button>
          )}
        </div>
        {showTable && (
          <>
            <div className="summary-grid">
              <div className="summary-card">
                <span className="summary-value">{rows.length}</span>
                <span className="summary-label">Estudiantes</span>
              </div>
            </div>
            <div className="toolbar">
              <div className="search-wrap">
                <I.i29 />
                <input type="text" placeholder="Buscar estudiante..." value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <button className={`btn-ghost filters-clear${search ? ' show' : ''}`} onClick={() => setSearch('')}>
                <I.i52 />
                Limpiar búsqueda
              </button>
            </div>
          </>
        )}
        <div className={`unsaved-bar${dirty || saveError ? ' show' : ''}`}>
          <span className="unsaved-msg">
            <I.i3 />
            {saveError || 'Hay cambios sin guardar'}
          </span>
          <div className="unsaved-actions">
            <button className="btn-secondary" onClick={() => setDiscardOpen(true)}>
              Cancelar cambios
            </button>
            <button className="btn-primary" disabled={saving} onClick={onSave}>
              <I.i45 />
              <span>{saving ? 'Guardando cambios...' : 'Guardar cambios'}</span>
            </button>
          </div>
        </div>
        <div className="matrix-wrap">{matrixContent}</div>
        {showTable && rows.length > 0 && (
          <div className="grade-cards">
            {filtered.map((r) => {
              const sit = situation(r);
              return (
                <div className="grade-card" key={r.studentId}>
                  <div className="grade-card-head">
                    <div>
                      <p className="student-name">{r.studentName}</p>
                      <p className="student-legajo">Legajo {r.fileNumber}</p>
                    </div>
                    {statusBadge(sit)}
                  </div>
                  {exams.map((e) => (
                    <div className="grade-card-row" key={e.id}>
                      <span className="eval-label">{examTypeLabel(e.type, e.name)}</span>
                      {cell(r, e, sit)}
                    </div>
                  ))}
                  {computed(sit).map((c) => (
                    <div className="grade-card-summary" key={c.label}>
                      <span className="eval-label">{c.label}</span>
                      <span className={`avg-cell${c.value == null ? ' empty' : ''}`}>{fmtGrade(c.value)}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
