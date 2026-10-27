import { useState } from 'react';
import { useGetStudentsQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseLoadState, CourseTabs, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import Pagination, { paginate } from '../components/Pagination';
import { useCourse } from '../lib/courses';
import { dni, initials } from '../lib/format';
import '../styles/pages/06.css';

const PAGE_SIZE = 10;
const ALL = 'Toda condición';
const COND_LABEL = { regular: 'Regular', libre: 'Libre' };

export default function Students() {
  const q = useCourse();
  const { courseId, course } = q;
  const students = useGetStudentsQuery(courseId);
  const [search, setSearch] = useState('');
  const [cond, setCond] = useState(ALL);
  const [page, setPage] = useState(1);

  if (!course) {
    return (
      <AppShell scope="06" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId, { label: 'Estudiantes' })} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const list = (students.data || [])
    .map((s) => ({
      id: s.studentId,
      name: s.profile?.fullName || s.studentId,
      dni: dni(s.profile?.document),
      legajo: s.profile?.fileNumber || 'S/D',
      email: s.profile?.email || '—',
      cond: s.attendance?.condition === 'LIBRE' ? 'libre' : 'regular',
    }))
    .sort((a, b) => a.name.localeCompare(b.name, 'es'));

  const term = search.trim().toLowerCase();
  const filtered = list.filter(
    (s) =>
      (!term || s.name.toLowerCase().includes(term) || s.dni.includes(term) || s.dni.replace(/\./g, '').includes(term)) &&
      (cond === ALL || COND_LABEL[s.cond] === cond),
  );
  const pager = paginate(filtered, page, PAGE_SIZE);
  const text = students.isLoading
    ? 'Cargando estudiantes…'
    : pager.total
      ? `Mostrando ${pager.start}–${pager.end} de ${pager.total} estudiantes`
      : 'Mostrando 0 estudiantes';
  const dirty = term !== '' || cond !== ALL;

  let message = null;
  if (students.isLoading) message = 'Cargando estudiantes…';
  else if (students.isError) message = toApiError(students.error).detail;
  else if (!filtered.length) message = list.length ? 'No hay estudiantes que coincidan con la búsqueda.' : 'No hay estudiantes inscriptos en el curso.';

  return (
    <AppShell scope="06" active="cursos">
      <Breadcrumb trail={courseTrail(course, courseId, { label: 'Estudiantes' })} />
      <div className="course-context">
        <div>
          <h1 className="course-context-title">{course.name}</h1>
          <p className="course-context-sub">
            <span>Comisión {course.com}</span>
            <span>{course.period}</span>
          </p>
        </div>
        <div className="course-context-count">
          <div className="count-value">{students.data ? students.data.length : course.students}</div>
          <div className="count-label">estudiantes</div>
        </div>
      </div>
      <CourseTabs courseId={courseId} active="estudiantes" />
      <div className="page-title-row">
        <div>
          <h2 className="page-title">Estudiantes</h2>
          <p className="page-desc">Listado de estudiantes inscriptos en el curso.</p>
        </div>
      </div>
      <div className="toolbar">
        <div className="search-wrap">
          <I.i29 className="leading" />
          <input
            type="text"
            placeholder="Buscar estudiante por nombre, apellido o DNI..."
            value={search}
            onChange={(e) => (setSearch(e.target.value), setPage(1))}
          />
        </div>
        <select className="filter-select" value={cond} onChange={(e) => (setCond(e.target.value), setPage(1))}>
          <option>{ALL}</option>
          <option>Regular</option>
          <option>Libre</option>
        </select>
        <button
          className={`clear-filters${dirty ? ' show' : ''}`}
          onClick={() => {
            setSearch('');
            setCond(ALL);
            setPage(1);
          }}
        >
          <I.i30 />
          Limpiar filtros
        </button>
        <button className="btn-secondary filters-btn-mobile" onClick={() => document.querySelector('.pg-06 .search-wrap input')?.focus()}>
          <I.i31 />
          Filtros
        </button>
      </div>
      <div className="list-meta-row">
        <span className="result-count">{text}</span>
      </div>
      <div className="table-panel">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th className="sortable">
                  Estudiante
                  <I.i32 className="sort-icon" />
                </th>
                <th>DNI</th>
                <th className="sortable">
                  Legajo
                  <I.i32 className="sort-icon" />
                </th>
                <th>Email</th>
                <th className="col-condicion">Condición</th>
              </tr>
            </thead>
            <tbody>
              {message ? (
                <tr>
                  <td colSpan={5} className="muted-cell" style={{ textAlign: 'center', padding: '28px 16px' }}>
                    {message}
                  </td>
                </tr>
              ) : (
                pager.items.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <div className="student-cell">
                        <span className="student-avatar">{initials(s.name)}</span>
                        <div>
                          <div className="student-name">{s.name}</div>
                        </div>
                      </div>
                    </td>
                    <td className="muted-cell">{s.dni}</td>
                    <td className="muted-cell">{s.legajo}</td>
                    <td className="muted-cell email-cell" title={s.email}>
                      {s.email}
                    </td>
                    <td className="col-condicion">
                      <span className={`badge ${s.cond}`}>{COND_LABEL[s.cond]}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <span className="pagination-info">{text}</span>
          <Pagination pager={pager} onChange={setPage} />
        </div>
      </div>
      <div className="student-cards">
        {message && <p className="result-count">{message}</p>}
        {!message &&
          pager.items.map((s) => (
            <div className="student-card" key={s.id}>
              <div className="student-card-top">
                <div className="student-card-id">
                  <span className="student-avatar">{initials(s.name)}</span>
                  <div>
                    <p className="student-card-name">{s.name}</p>
                    <p className="student-card-legajo">Legajo {s.legajo}</p>
                  </div>
                </div>
              </div>
              <p className="student-card-email">{s.email}</p>
              <div className="student-card-bottom">
                <span className={`badge ${s.cond}`}>{COND_LABEL[s.cond]}</span>
              </div>
            </div>
          ))}
      </div>
    </AppShell>
  );
}
