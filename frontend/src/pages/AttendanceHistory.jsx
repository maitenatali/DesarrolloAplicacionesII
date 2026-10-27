import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetAttendanceQuery, useGetAttendancesQuery, useGetStudentsQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseHero, CourseLoadState, CourseTabs, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import Pagination, { paginate } from '../components/Pagination';
import { useCourse } from '../lib/courses';
import { ATTENDANCE_LABEL } from '../lib/domain';
import { initials, MONTHS, percent, shortDate } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/08.css';

const PAGE_SIZE = 10;
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/** Fila del historial individual: trae el detalle de esa clase y muestra el estado del alumno. */
function StudentDayRow({ courseId, day, studentId, filter }) {
  const { data } = useGetAttendanceQuery({ courseId, day });
  const rec = data?.records.find((r) => r.studentId === studentId);
  if (!rec) return null;
  const cls = rec.status.toLowerCase();
  if (filter !== 'todos' && filter !== cls) return null;
  return (
    <tr>
      <td>{shortDate(day)}</td>
      <td>
        <span className={`badge ${cls}`}>{ATTENDANCE_LABEL[rec.status]}</span>
      </td>
      <td>{rec.note || '—'}</td>
    </tr>
  );
}

function DetailModal({ courseId, row, course, onClose }) {
  const { data, isFetching } = useGetAttendanceQuery({ courseId, day: row?.date }, { skip: !row });
  const roster = useGetStudentsQuery(courseId);
  useLockScroll(!!row);
  const names = new Map((roster.data || []).map((s) => [s.studentId, s.profile?.fullName || s.studentId]));
  const notes = (data?.records || []).filter((r) => r.note);
  const sched = course?.raw.schedule?.[0];
  return (
    <div className={`modal-backdrop${row ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && onClose()}>
      {row && (
        <div className="modal-card">
          <div className="modal-head">
            <h3>Detalle de asistencia</h3>
            <button className="modal-close" aria-label="Cerrar" onClick={onClose}>
              <I.i52 />
            </button>
          </div>
          <div className="modal-body">
            <p className="modal-meta">
              {shortDate(row.date)}
              {sched ? ` · ${sched.startTime}–${sched.endTime}` : ''}
            </p>
            <p className="modal-meta-sub">Aula {course?.room}</p>
            <div className="modal-stat-row">
              <span>Presentes</span>
              <span className="n count-presente">{row.present}</span>
            </div>
            <div className="modal-stat-row">
              <span>Ausentes</span>
              <span className="n count-ausente">{row.absent}</span>
            </div>
            <div className="modal-stat-row">
              <span>Justificados</span>
              <span className="n count-justificado">{row.justified}</span>
            </div>
            {(row.notes || notes.length > 0) && (
              <div className="modal-obs">
                <p>Observaciones</p>
                <ul>
                  {row.notes && <li>{row.notes}</li>}
                  {notes.map((r) => (
                    <li key={r.studentId}>
                      {names.get(r.studentId)}: {r.note}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {isFetching && <p className="modal-meta-sub">Cargando…</p>}
          </div>
          <div className="modal-foot">
            <button className="btn-secondary" onClick={onClose}>
              Cerrar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AttendanceHistory() {
  const navigate = useNavigate();
  const q = useCourse();
  const { courseId, course } = q;
  const history = useGetAttendancesQuery(courseId);
  const roster = useGetStudentsQuery(courseId);
  const [month, setMonth] = useState('todo');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [student, setStudent] = useState(null);
  const [filter, setFilter] = useState('todos');
  const [detail, setDetail] = useState(null);

  const rows = useMemo(() => [...(history.data || [])].sort((a, b) => b.date.localeCompare(a.date)), [history.data]);
  const months = useMemo(() => [...new Set(rows.map((r) => r.date.slice(0, 7)))].sort(), [rows]);

  if (!course) {
    return (
      <AppShell scope="08" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId, { label: 'Historial' })} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const filtered = rows.filter((r) => month === 'todo' || r.date.startsWith(month));
  const pager = paginate(filtered, page, PAGE_SIZE);
  const term = search.trim().toLowerCase();
  const results = term
    ? (roster.data || []).filter((s) => (s.profile?.fullName || '').toLowerCase().includes(term) || (s.profile?.fileNumber || '').includes(term)).slice(0, 6)
    : [];

  const openStudent = (s) => {
    setStudent(s);
    setFilter('todos');
    setSearch('');
    setSearchOpen(false);
  };

  return (
    <AppShell scope="08" active="cursos" after={<DetailModal courseId={courseId} row={detail} course={course} onClose={() => setDetail(null)} />}>
      <Breadcrumb trail={courseTrail(course, courseId, { label: 'Asistencia', to: `/cursos/${courseId}/asistencia` }, { label: 'Historial' })} />
      <div>
        <CourseHero course={course} />
        <CourseTabs courseId={courseId} active="asistencia" />
        <div className="subnav">
          <button className="subnav-item" onClick={() => navigate(`/cursos/${courseId}/asistencia`)}>
            Registrar asistencia
          </button>
          <button className="subnav-item active">Historial</button>
        </div>
        <div className="section-head">
          <div className="section-head-main">
            <h2>Historial de asistencia</h2>
            <p>Consultá los registros de asistencia de las clases del curso.</p>
          </div>
          <button className="btn-primary" onClick={() => navigate(`/cursos/${courseId}/asistencia`)}>
            <I.i51 />
            Registrar asistencia
          </button>
        </div>
        <div className="panel filters-panel">
          <div className="filters-row">
            <div className="field field-period">
              <label htmlFor="periodSelect">Período</label>
              <div className="input-wrap">
                <I.i20 className="field-icon" />
                <select id="periodSelect" value={month} onChange={(e) => (setMonth(e.target.value), setPage(1))}>
                  <option value="todo">Todo el período</option>
                  {months.map((m) => (
                    <option key={m} value={m}>
                      {capital(MONTHS[Number(m.slice(5, 7)) - 1])} {m.slice(0, 4)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-secondary filters-toggle" onClick={() => document.getElementById('periodSelect')?.focus()}>
              <I.i31 />
              Filtros
            </button>
            <button className={`btn-ghost filters-clear${month !== 'todo' ? ' show' : ''}`} onClick={() => setMonth('todo')}>
              <I.i52 />
              Limpiar filtros
            </button>
          </div>
        </div>
        <div className="summary-grid">
          <div className="summary-card">
            <span className="summary-value">{filtered.length}</span>
            <span className="summary-label">Clases registradas</span>
          </div>
        </div>
        <div className="student-search-row">
          <div className="search-wrap">
            <I.i29 />
            <input
              type="text"
              placeholder="Buscar estudiante..."
              value={search}
              onChange={(e) => (setSearch(e.target.value), setSearchOpen(true))}
              onFocus={() => setSearchOpen(true)}
              onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
            />
            <div className={`search-results${searchOpen && results.length ? ' show' : ''}`}>
              {results.map((s) => (
                <div key={s.studentId} className="search-result-item" onMouseDown={() => openStudent(s)}>
                  <span className="sr-avatar">{initials(s.profile?.fullName)}</span>
                  <span className="sr-name">{s.profile?.fullName}</span>
                  <span className="sr-legajo">Legajo {s.profile?.fileNumber}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        {student ? (
          <div className="panel student-panel">
            <div className="student-panel-head">
              <div className="student-id-row">
                <span className="avatar">{initials(student.profile?.fullName)}</span>
                <div>
                  <p className="student-id-name">{student.profile?.fullName}</p>
                  <p className="student-id-legajo">Legajo {student.profile?.fileNumber}</p>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div className="student-pct">
                  <div className="val">{percent(student.attendance?.attendancePercentage)}</div>
                  <div className="lab">Asistencia</div>
                </div>
                <button className="student-panel-close" onClick={() => setStudent(null)}>
                  <I.i52 />
                  Cerrar
                </button>
              </div>
            </div>
            <div className="status-filter-row">
              {[
                ['todos', 'Todos'],
                ['presente', 'Presentes'],
                ['ausente', 'Ausentes'],
                ['justificado', 'Justificados'],
              ].map(([k, l]) => (
                <button key={k} className={`status-chip${filter === k ? ' active' : ''}`} onClick={() => setFilter(k)}>
                  {l}
                </button>
              ))}
            </div>
            <table className="student-hist-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Estado</th>
                  <th>Observación</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <StudentDayRow key={r.date} courseId={courseId} day={r.date} studentId={student.studentId} filter={filter} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div>
            <div className="panel table-panel">
              <table className="hist-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Presentes</th>
                    <th>Ausentes</th>
                  </tr>
                </thead>
                <tbody>
                  {history.isLoading && (
                    <tr>
                      <td colSpan={3}>
                        <div className="skel" style={{ width: '100%', height: 18 }} />
                      </td>
                    </tr>
                  )}
                  {history.isError && (
                    <tr>
                      <td colSpan={3}>
                        <p className="cell-date">{toApiError(history.error).detail}</p>
                      </td>
                    </tr>
                  )}
                  {!history.isLoading && !history.isError && !filtered.length && (
                    <tr>
                      <td colSpan={3}>
                        <p className="cell-date">No hay clases registradas en el período seleccionado.</p>
                      </td>
                    </tr>
                  )}
                  {pager.items.map((r) => (
                    <tr key={r.date} onClick={() => setDetail(r)} style={{ cursor: 'pointer' }}>
                      <td>
                        <p className="cell-date">{shortDate(r.date)}</p>
                      </td>
                      <td>
                        <p className="cell-count present-count">{r.present}</p>
                      </td>
                      <td>
                        <p className="cell-count absent-count">{r.absent}</p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="hist-cards">
              {pager.items.map((r) => (
                <div className="hist-card" key={r.date} onClick={() => setDetail(r)}>
                  <div className="hist-card-head">
                    <p className="cell-date" style={{ fontSize: '14.5px' }}>
                      {shortDate(r.date)}
                    </p>
                  </div>
                  <div className="hist-card-counts">
                    <div>
                      <span className="n count-presente">{r.present}</span>
                      <span className="l">Presentes</span>
                    </div>
                    <div>
                      <span className="n count-ausente">{r.absent}</span>
                      <span className="l">Ausentes</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="pagination" style={{ display: filtered.length ? 'flex' : 'none' }}>
              <span className="pagination-info">
                {filtered.length ? `Mostrando ${pager.start}–${pager.end} de ${pager.total} clases` : 'Mostrando 0 clases'}
              </span>
              <Pagination pager={pager} onChange={setPage} iconArrows />
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

