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
import useLockScroll from '../lib/useBodyClass';
import useToast from '../lib/useToast';
import '../styles/pages/09.css';

// Valor del input: número (coma o punto) o "A" = ausente. Vacío = sin nota.
const cellText = (g) => (!g ? '' : g.absent ? 'A' : g.grade == null ? '' : fmtGrade(g.grade));

function parseCell(text) {
  const v = text.trim();
  if (v === '') return { ok: true, value: { grade: null, absent: false } };
  if (/^a(usente)?$/i.test(v)) return { ok: true, value: { grade: null, absent: true } };
  const n = Number(v.replace(',', '.'));
  if (Number.isNaN(n)) return { ok: false, error: 'Ingresá una calificación válida.' };
  if (n < 0 || n > 10) return { ok: false, error: 'La calificación debe estar entre 0 y 10.' };
  return { ok: true, value: { grade: Math.round(n * 100) / 100, absent: false } };
}

function GradeInput({ value, original, label, disabled, onChange }) {
  const parsed = parseCell(value);
  const isDirty = value !== original;
  return (
    <>
      <input
        type="text"
        inputMode="decimal"
        className={`grade-input${value === '' ? ' empty' : ''}${!parsed.ok ? ' invalid' : ''}${isDirty && parsed.ok ? ' dirty' : ''}`}
        value={value}
        placeholder="—"
        maxLength={5}
        aria-label={label}
        title="Nota de 0 a 10, o A si estuvo ausente"
        disabled={disabled}
        onChange={(ev) => onChange(ev.target.value)}
      />
      {!parsed.ok && <span className="grade-error">{parsed.error}</span>}
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
  const [toast, showToast] = useToast(2800);
  useLockScroll(discardOpen);

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
  const changed = rows.flatMap((r) => exams.filter((e) => text(r, e) !== original(r, e)).map((e) => ({ r, e })));
  const invalid = changed.filter(({ r, e }) => !parseCell(text(r, e)).ok);
  const dirty = changed.length > 0;

  const average = (row) => {
    if (!exams.some((e) => edits[key(row.studentId, e.id)] !== undefined)) return row.average;
    const vals = exams.map((e) => parseCell(text(row, e))).filter((p) => p.ok && p.value.grade != null).map((p) => p.value.grade);
    return vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null;
  };

  const onSave = async () => {
    if (invalid.length) {
      document.querySelector('.pg-09 .grade-input.invalid')?.focus();
      return;
    }
    setSaveError(null);
    const byExam = new Map();
    changed.forEach(({ r, e }) => {
      const list = byExam.get(e.id) || [];
      list.push({ studentId: r.studentId, ...parseCell(text(r, e)).value });
      byExam.set(e.id, list);
    });
    try {
      for (const [examId, entries] of byExam) {
        // eslint-disable-next-line no-await-in-loop
        await save({ courseId, examId, entries }).unwrap();
      }
      setEdits({});
      showToast('Calificaciones actualizadas correctamente.');
    } catch (err) {
      setSaveError(toApiError(err).detail);
    }
  };

  const term = search.trim().toLowerCase();
  const filtered = rows.filter((r) => !term || r.studentName.toLowerCase().includes(term) || (r.fileNumber || '').toLowerCase().includes(term));

  const cell = (row, exam) => (
    <GradeInput
      value={text(row, exam)}
      original={original(row, exam)}
      label={`${examTypeLabel(exam.type, exam.name)} de ${row.studentName}`}
      disabled={readOnly}
      onChange={(v) => setEdits((m) => ({ ...m, [key(row.studentId, exam.id)]: v }))}
    />
  );

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
            <th style={{ textAlign: 'center' }}>Nota final</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => {
            const avg = average(r);
            return (
              <tr key={r.studentId}>
                <td className="col-student">
                  <p className="student-name">{r.studentName}</p>
                  <p className="student-legajo">Legajo {r.fileNumber}</p>
                </td>
                {exams.map((e) => (
                  <td className="grade-cell" key={e.id}>
                    {cell(r, e)}
                  </td>
                ))}
                <td className="avg-col">
                  <span className={`avg-cell${avg == null ? ' empty' : ''}`}>{fmtGrade(avg)}</span>
                </td>
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
              const avg = average(r);
              return (
                <div className="grade-card" key={r.studentId}>
                  <div className="grade-card-head">
                    <div>
                      <p className="student-name">{r.studentName}</p>
                      <p className="student-legajo">Legajo {r.fileNumber}</p>
                    </div>
                  </div>
                  {exams.map((e) => (
                    <div className="grade-card-row" key={e.id}>
                      <span className="eval-label">{examTypeLabel(e.type, e.name)}</span>
                      {cell(r, e)}
                    </div>
                  ))}
                  <div className="grade-card-summary">
                    <span className="eval-label">Nota final</span>
                    <span className={`avg-cell${avg == null ? ' empty' : ''}`}>{fmtGrade(avg)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
