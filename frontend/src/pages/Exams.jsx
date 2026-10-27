import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetCourseExamsQuery, useGetExamTypesQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseHero, CourseLoadState, CourseTabs, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import { useCourse } from '../lib/courses';
import { EXAM_STATUS_LABEL, examStatus, examTimeRange, examTypeLabel } from '../lib/domain';
import { longDate } from '../lib/format';
import useToast from '../lib/useToast';
import '../styles/pages/10.css';

const CATEGORY_LABEL = { PARCIAL: 'Parcial', RECUPERATORIO: 'Recuperatorio', INTEGRADOR: 'TP', FINAL: 'Final' };
const STATUS_FILTER = { Próximos: 'proximo', Realizados: 'realizado', Cancelados: 'cancelado' };
const ALL_STATUS = 'Todos los estados';
const ALL_TYPES = 'Todos los tipos';

export default function Exams() {
  const navigate = useNavigate();
  const q = useCourse();
  const { courseId, course } = q;
  const exams = useGetCourseExamsQuery(courseId);
  const types = useGetExamTypesQuery();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState(ALL_STATUS);
  const [type, setType] = useState(ALL_TYPES);
  const [toast] = useToast();

  if (!course) {
    return (
      <AppShell scope="10" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId, { label: 'Exámenes' })} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const category = Object.fromEntries((types.data || []).map((t) => [t.type, t.category]));
  const list = [...(exams.data || [])]
    .sort((a, b) => `${a.date}${a.startTime}`.localeCompare(`${b.date}${b.startTime}`))
    .map((e) => ({
      ...e,
      st: examStatus(e),
      typeText: examTypeLabel(e.type, e.name),
      cat: (category[e.type] || (e.type === 'FINAL' ? 'FINAL' : 'PARCIAL')).toLowerCase(),
    }));
  const term = search.trim().toLowerCase();
  const filtered = list.filter(
    (e) =>
      (!term || e.name.toLowerCase().includes(term) || e.typeText.toLowerCase().includes(term)) &&
      (status === ALL_STATUS || STATUS_FILTER[status] === e.st) &&
      (type === ALL_TYPES || CATEGORY_LABEL[e.cat.toUpperCase()] === type),
  );
  const dirty = term !== '' || status !== ALL_STATUS || type !== ALL_TYPES;
  const count = (st) => list.filter((e) => e.st === st).length;
  const open = (e) => navigate(`/cursos/${courseId}/examenes/${e.id}`);
  const canCreate = course.raw.status !== 'FINALIZADO' && course.raw.status !== 'CANCELADO';

  let message = null;
  if (exams.isLoading) message = 'Cargando exámenes…';
  else if (exams.isError) message = toApiError(exams.error).detail;
  else if (!filtered.length) message = list.length ? 'No hay exámenes que coincidan con los filtros.' : 'Todavía no hay exámenes creados para este curso.';

  return (
    <AppShell
      scope="10"
      active="cursos"
      after={
        <div className={`toast${toast.show ? ' show' : ''}`}>
          <I.i55 />
          <span>{toast.message}</span>
        </div>
      }
    >
      <Breadcrumb trail={courseTrail(course, courseId, { label: 'Exámenes' })} />
      <CourseHero course={course} />
      <CourseTabs courseId={courseId} active="examenes" />
      <div className="page-title-row">
        <div>
          <h2 className="page-title">Exámenes</h2>
          <p className="page-desc">Consultá y gestioná los exámenes.</p>
        </div>
        {canCreate && (
          <button className="btn-primary" onClick={() => navigate(`/cursos/${courseId}/examenes/nuevo`)}>
            <I.i51 />
            Nuevo examen
          </button>
        )}
      </div>
      <div>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{list.length}</span>
            <span className="stat-label">Total de exámenes</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{count('proximo')}</span>
            <span className="stat-label">Próximos</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{count('realizado')}</span>
            <span className="stat-label">Realizados</span>
          </div>
        </div>
        <div className="toolbar">
          <div className="search-wrap">
            <I.i29 className="leading" />
            <input type="text" placeholder="Buscar examen..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="filter-select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option>{ALL_STATUS}</option>
            <option>Próximos</option>
            <option>Realizados</option>
            <option>Cancelados</option>
          </select>
          <select className="filter-select" value={type} onChange={(e) => setType(e.target.value)}>
            <option>{ALL_TYPES}</option>
            <option>Parcial</option>
            <option>Recuperatorio</option>
            <option>TP</option>
            <option>Final</option>
          </select>
          <button
            className={`clear-filters${dirty ? ' show' : ''}`}
            onClick={() => {
              setSearch('');
              setStatus(ALL_STATUS);
              setType(ALL_TYPES);
            }}
          >
            <I.i30 />
            Limpiar filtros
          </button>
          <button className="btn-secondary filters-btn-mobile" onClick={() => document.querySelector('.pg-10 .search-wrap input')?.focus()}>
            <I.i31 />
            Filtros
          </button>
        </div>
        <div className="list-header-row">
          <h3 className="section-title">Listado de exámenes</h3>
          <span className="result-count">
            Mostrando {filtered.length} examen{filtered.length === 1 ? '' : 'es'}
          </span>
        </div>
        <div className="table-panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th className="sortable">
                    Examen
                    <I.i32 className="sort-icon" />
                  </th>
                  <th>Tipo</th>
                  <th className="sortable">
                    Fecha y horario
                    <I.i32 className="sort-icon" />
                  </th>
                  <th className="sortable">
                    Estado
                    <I.i32 className="sort-icon" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {message ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '28px 16px', color: 'var(--text-600)' }}>
                      {message}
                    </td>
                  </tr>
                ) : (
                  filtered.map((e) => (
                    <tr
                      key={e.id}
                      className={`exam-row-clickable${e.st === 'cancelado' ? ' is-cancelado' : ''}`}
                      onClick={() => open(e)}
                      onKeyDown={(ev) => ev.key === 'Enter' && open(e)}
                      tabIndex={0}
                      role="button"
                    >
                      <td className="exam-name-cell">
                        <p className="exam-name">{e.name}</p>
                      </td>
                      <td>
                        <span className={`badge tipo ${e.cat}`}>{e.typeText}</span>
                      </td>
                      <td className="date-cell">
                        <p className="date-main">{longDate(e.date)}</p>
                        <p className="date-time">{examTimeRange(e)}</p>
                      </td>
                      <td>
                        <span className={`badge ${e.st}`}>{EXAM_STATUS_LABEL[e.st]}</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span className="pagination-info">
              {filtered.length ? `Mostrando 1–${filtered.length} de ${filtered.length} exámenes` : 'Mostrando 0 exámenes'}
            </span>
            <div className="pagination-controls">
              <button className="page-btn" disabled aria-label="Página anterior">
                <I.i33 />
              </button>
              <button className="page-btn active">1</button>
              <button className="page-btn" disabled aria-label="Página siguiente">
                <I.i34 />
              </button>
            </div>
          </div>
        </div>
        <div className="exam-cards">
          {!message &&
            filtered.map((e) => (
              <div
                key={e.id}
                className={`exam-card exam-row-clickable${e.st === 'cancelado' ? ' is-cancelado' : ''}`}
                onClick={() => open(e)}
                tabIndex={0}
                role="button"
              >
                <div className="exam-card-top">
                  <div>
                    <p className="exam-card-name">{e.name}</p>
                    <span className={`badge tipo ${e.cat} exam-card-type`}>{e.typeText}</span>
                  </div>
                </div>
                <div className="exam-card-meta">
                  <div className="exam-card-meta-row">
                    <I.i56 />
                    {longDate(e.date)}
                  </div>
                  <div className="exam-card-meta-row">
                    <I.i36 />
                    {examTimeRange(e)}
                  </div>
                </div>
                <div className="exam-card-badges">
                  <span className={`badge ${e.st}`}>{EXAM_STATUS_LABEL[e.st]}</span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </AppShell>
  );
}
