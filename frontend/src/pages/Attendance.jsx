import { Fragment, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetAttendanceQuery, useGetStudentsQuery, useSaveAttendanceMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseHero, CourseLoadState, CourseTabs, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import { useCourse } from '../lib/courses';
import { todayDay } from '../lib/format';
import useToast from '../lib/useToast';
import '../styles/pages/07.css';

const OPTS = [
  ['presente', 'Presente', 'PRESENTE', I.i47],
  ['ausente', 'Ausente', 'AUSENTE', I.i48],
  ['justificado', 'Justif.', 'JUSTIFICADO', I.i49],
];
const FROM_API = { PRESENTE: 'presente', AUSENTE: 'ausente', JUSTIFICADO: 'justificado' };
const TO_API = Object.fromEntries(OPTS.map(([v, , api]) => [v, api]));

function SegControl({ s, onSet }) {
  return (
    <div className={`seg-control${s.state === 'unset' ? ' unset' : ''}`} role="group" aria-label={`Estado de asistencia de ${s.name}`}>
      {OPTS.map(([val, label, , Icon]) => (
        <button
          key={val}
          type="button"
          className={`seg-btn ${val} ${s.state === val ? `active ${val}` : ''}`}
          aria-pressed={s.state === val}
          onClick={() => onSet(s.id, val)}
        >
          <Icon />
          {label}
        </button>
      ))}
    </div>
  );
}

export default function Attendance() {
  const navigate = useNavigate();
  const q = useCourse();
  const { courseId, course } = q;
  const [day, setDay] = useState(todayDay());
  const roster = useGetStudentsQuery(courseId);
  const record = useGetAttendanceQuery({ courseId, day }, { skip: !day });
  const [save, { isLoading: saving }] = useSaveAttendanceMutation();
  const [rows, setRows] = useState({});
  const [search, setSearch] = useState('');
  const [banner, setBanner] = useState(null);
  const [toast, showToast] = useToast(2800);

  const isNew = toApiError(record.error)?.code === 'ATTENDANCE_NOT_RECORDED' || toApiError(record.error)?.status === 404;
  const recordReady = !record.isFetching && (record.data || isNew);

  // Estado editable de la clase: lo registrado o "sin completar" si la clase es nueva.
  useEffect(() => {
    if (!roster.data || !recordReady) return;
    const saved = new Map((record.data && !isNew ? record.data.records : []).map((r) => [r.studentId, r]));
    setRows(
      Object.fromEntries(
        roster.data.map((s) => {
          const r = saved.get(s.studentId);
          return [s.studentId, { state: r ? FROM_API[r.status] : 'unset', obs: r?.note || '', obsOpen: !!r?.note }];
        }),
      ),
    );
    setBanner(null);
  }, [roster.data, record.data, recordReady, isNew]);

  const students = useMemo(
    () =>
      (roster.data || [])
        .filter((s) => s.enrollmentStatus !== 'BAJA')
        .map((s) => ({
          id: s.studentId,
          name: s.profile?.fullName || s.studentId,
          legajo: s.profile?.fileNumber || 'S/D',
          ...(rows[s.studentId] || { state: 'unset', obs: '', obsOpen: false }),
        }))
        .sort((a, b) => a.name.localeCompare(b.name, 'es')),
    [roster.data, rows],
  );

  if (!course) {
    return (
      <AppShell scope="07" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId, { label: 'Asistencia' })} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const patch = (id, change) => setRows((r) => ({ ...r, [id]: { ...r[id], ...change } }));
  const setState = (id, val) => {
    patch(id, val === 'justificado' ? { state: val, obsOpen: true } : { state: val });
    setBanner(null);
  };
  const markAll = (val) => {
    setRows((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, { ...v, state: val }])));
    setBanner(null);
  };
  const confirmAllAbsent = () => {
    if (window.confirm('¿Marcar a todos los estudiantes como ausentes? Esta acción sobrescribirá el estado actual.')) markAll('ausente');
  };

  const onSave = async () => {
    if (students.some((s) => s.state === 'unset')) {
      setBanner('Completá el estado de asistencia de todos los estudiantes antes de guardar.');
      document.querySelector('.pg-07 .validation-banner')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    try {
      await save({
        courseId,
        day,
        body: { records: students.map((s) => ({ studentId: s.id, status: TO_API[s.state], note: s.obs.trim() || null })) },
      }).unwrap();
      showToast('Asistencia guardada correctamente.');
    } catch (err) {
      setBanner(toApiError(err).detail);
    }
  };

  const term = search.trim().toLowerCase();
  const filtered = students.filter((s) => !term || s.name.toLowerCase().includes(term) || s.legajo.includes(term));
  const count = (st) => students.filter((s) => s.state === st).length;
  const loadingTable = roster.isLoading || record.isFetching;
  const obsLabel = (s) => (s.state === 'justificado' ? 'Justificación' : 'Observación');

  return (
    <AppShell
      scope="07"
      active="cursos"
      after={
        <div className={`toast${toast.show ? ' show' : ''}`}>
          <I.i46 />
          <span>{toast.message || 'Asistencia guardada correctamente.'}</span>
        </div>
      }
    >
      <Breadcrumb trail={courseTrail(course, courseId, { label: 'Asistencia' })} />
      <div>
        <CourseHero course={course} />
        <CourseTabs courseId={courseId} active="asistencia" />
        <div className="section-head">
          <div className="section-head-main">
            <h2>Gestión de asistencia</h2>
            <p>Registrá y consultá la asistencia de los estudiantes del curso.</p>
          </div>
          <button className="btn-ghost" onClick={() => navigate(`/cursos/${courseId}/asistencia/historial`)}>
            <I.i44 />
            Ver historial de asistencia
          </button>
        </div>
        <div className="panel selector-panel">
          <div className="selector-grid">
            <div className="field">
              <label htmlFor="classDate">Fecha de la clase</label>
              <div className="input-wrap">
                <I.i20 className="field-icon" />
                <input type="date" id="classDate" value={day} max={todayDay()} onChange={(e) => setDay(e.target.value)} />
              </div>
            </div>
          </div>
        </div>
        <div className="summary-grid">
          <div className="summary-card">
            <span className="summary-value">{students.length}</span>
            <span className="summary-label">Total de estudiantes</span>
          </div>
          <div className="summary-card presentes">
            <span className="summary-value">{count('presente')}</span>
            <span className="summary-label">Presentes</span>
          </div>
          <div className="summary-card ausentes">
            <span className="summary-value">{count('ausente')}</span>
            <span className="summary-label">Ausentes</span>
          </div>
        </div>
        <div className="validation-banner" style={{ display: banner ? 'flex' : 'none' }}>
          <I.i3 />
          <span>{banner}</span>
        </div>
        <div className="toolbar">
          <div className="quick-actions">
            <button className="btn-quick all-present" onClick={() => markAll('presente')}>
              Todos presentes
            </button>
            <button className="btn-quick all-absent" onClick={confirmAllAbsent}>
              Todos ausentes
            </button>
          </div>
          <div className="search-wrap">
            <I.i29 />
            <input type="text" placeholder="Buscar estudiante..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        <div className="panel table-panel">
          {!loadingTable && !students.length ? (
            <div className="empty-state">
              <I.i37 />
              <p>No hay estudiantes registrados</p>
              <p className="state-sub">No hay estudiantes disponibles para registrar asistencia en este curso.</p>
            </div>
          ) : (
            <table className="att-table">
              <thead>
                <tr>
                  <th style={{ width: '32%' }}>Estudiante</th>
                  <th style={{ width: '16%' }}>Legajo</th>
                  <th style={{ width: '34%' }}>Estado</th>
                  <th style={{ width: '10%' }} />
                </tr>
              </thead>
              <tbody>
                {loadingTable
                  ? Array.from({ length: 3 }, (_, i) => (
                      <tr key={i}>
                        <td colSpan={4}>
                          <div className="skel" style={{ width: '100%', height: 18 }} />
                        </td>
                      </tr>
                    ))
                  : filtered.map((s) => (
                      <Fragment key={s.id}>
                        <tr className={s.state === 'unset' ? 'row-incomplete' : ''}>
                          <td>
                            <p className="student-name">{s.name}</p>
                          </td>
                          <td>
                            <p className="student-legajo">Legajo: {s.legajo}</p>
                          </td>
                          <td>
                            <SegControl s={s} onSet={setState} />
                          </td>
                          <td>
                            <button
                              className={`obs-btn${s.obs ? ' has-note' : ''}`}
                              aria-label="Agregar observación"
                              onClick={() => patch(s.id, { obsOpen: !s.obsOpen })}
                            >
                              <I.i50 />
                            </button>
                          </td>
                        </tr>
                        <tr className={`obs-row${s.obsOpen ? '' : ' hidden'}`}>
                          <td colSpan={5}>
                            <p className="obs-label">{obsLabel(s)}</p>
                            <input
                              type="text"
                              placeholder={s.state === 'justificado' ? 'Ej: presentó certificado médico' : 'Ej: llegó tarde, retiro anticipado...'}
                              value={s.obs}
                              maxLength={500}
                              onChange={(e) => patch(s.id, { obs: e.target.value })}
                            />
                          </td>
                        </tr>
                      </Fragment>
                    ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="att-cards">
          {!loadingTable &&
            filtered.map((s) => (
              <div key={s.id} className={`att-card${s.state === 'unset' ? ' row-incomplete' : ''}`}>
                <div className="att-card-head">
                  <div>
                    <p className="student-name">{s.name}</p>
                    <p className="student-legajo">Legajo {s.legajo}</p>
                  </div>
                  <button
                    className={`obs-btn${s.obs ? ' has-note' : ''}`}
                    aria-label="Agregar observación"
                    onClick={() => patch(s.id, { obsOpen: !s.obsOpen })}
                  >
                    <I.i50 />
                  </button>
                </div>
                <SegControl s={s} onSet={setState} />
                <div className={`att-card-field${s.obsOpen ? '' : ' hidden'}`} style={s.obsOpen ? undefined : { display: 'none' }}>
                  <label>{obsLabel(s)}</label>
                  <input
                    type="text"
                    placeholder={s.state === 'justificado' ? 'Ej: presentó certificado médico' : 'Ej: llegó tarde...'}
                    value={s.obs}
                    maxLength={500}
                    onChange={(e) => patch(s.id, { obs: e.target.value })}
                  />
                </div>
              </div>
            ))}
        </div>
        <div className="form-actions">
          <button className="btn-secondary" onClick={() => navigate(`/cursos/${courseId}`)}>
            Cancelar
          </button>
          <button className="btn-primary" disabled={saving || loadingTable || !students.length} onClick={onSave}>
            <I.i45 />
            <span>{saving ? 'Guardando asistencia...' : isNew ? 'Guardar asistencia' : 'Guardar cambios'}</span>
          </button>
        </div>
      </div>
    </AppShell>
  );
}
