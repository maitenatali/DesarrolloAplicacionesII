import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetCoursesQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { campusName, COURSE_STATUS } from '../lib/domain';
import { courseSchedule } from '../lib/courses';
import '../styles/pages/03.css';

const PAGE_SIZE = 6;
const STATUS_CLASS = { EN_CURSO: 'activo', PROGRAMADO: 'proximo', FINALIZADO: 'finalizado', CANCELADO: 'finalizado' };
const ALL_PERIODS = 'Todos los períodos';
const ALL_STATUS = 'Todos los estados';

export default function MyCourses() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useGetCoursesQuery();
  const [q, setQ] = useState('');
  const [period, setPeriod] = useState(ALL_PERIODS);
  const [status, setStatus] = useState(ALL_STATUS);
  const [page, setPage] = useState(1);

  const courses = useMemo(
    () =>
      (data || []).map((c) => ({
        id: c.id,
        name: c.subject.name,
        com: c.code,
        period: c.period.label,
        sede: campusName(c.campusId),
        horario: courseSchedule(c),
        students: c.enrolled,
        statusClass: STATUS_CLASS[c.status] || 'finalizado',
        statusLabel: COURSE_STATUS[c.status] || c.status,
      })),
    [data],
  );
  const periods = [...new Set(courses.map((c) => c.period))];
  const statuses = [...new Set(courses.map((c) => c.statusLabel))];

  const filtered = courses.filter((c) => {
    const term = q.trim().toLowerCase();
    const matchesSearch = !term || [c.name, c.com, c.period, c.sede, c.horario].some((v) => String(v).toLowerCase().includes(term));
    return matchesSearch && (period === ALL_PERIODS || c.period === period) && (status === ALL_STATUS || c.statusLabel === status);
  });
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, totalPages);
  const pageCourses = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const start = filtered.length ? (current - 1) * PAGE_SIZE + 1 : 0;
  const end = Math.min(current * PAGE_SIZE, filtered.length);
  const countText = isLoading
    ? 'Cargando cursos…'
    : filtered.length === 0
      ? 'Mostrando 0 cursos'
      : `Mostrando ${start}–${end} de ${filtered.length} cursos`;
  const dirty = q.trim() !== '' || period !== ALL_PERIODS || status !== ALL_STATUS;

  const open = (id) => navigate(`/cursos/${id}`);
  const keyOpen = (id) => (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      open(id);
    }
  };
  const changePage = (p) => {
    if (p < 1 || p > totalPages) return;
    setPage(p);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const resetPage = (setter) => (e) => {
    setter(e.target.value);
    setPage(1);
  };

  let message = null;
  if (isLoading) message = 'Cargando cursos…';
  else if (isError) message = toApiError(error).detail;
  else if (!filtered.length) message = courses.length ? 'No hay cursos que coincidan con los filtros.' : 'No tenés cursos asignados.';

  return (
    <AppShell scope="03" active="cursos">
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        / Mis cursos
      </p>
      <div className="page-head-row">
        <div>
          <h1 className="page-title">Mis cursos</h1>
          <p className="page-desc">Consultá y gestioná los cursos a tu cargo.</p>
        </div>
      </div>
      <div className="toolbar">
        <div className="search-wrap">
          <I.i29 className="leading" />
          <input type="text" placeholder="Buscar curso..." value={q} onChange={resetPage(setQ)} />
        </div>
        <select className="filter-select" value={period} onChange={resetPage(setPeriod)}>
          <option>{ALL_PERIODS}</option>
          {periods.map((p) => (
            <option key={p}>{p}</option>
          ))}
        </select>
        <select className="filter-select" value={status} onChange={resetPage(setStatus)}>
          <option>{ALL_STATUS}</option>
          {statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <button
          className={`clear-filters${dirty ? ' show' : ''}`}
          onClick={() => {
            setQ('');
            setPeriod(ALL_PERIODS);
            setStatus(ALL_STATUS);
            setPage(1);
          }}
        >
          <I.i30 />
          Limpiar filtros
        </button>
        <button className="btn-secondary filters-btn-mobile" onClick={() => document.querySelector('.pg-03 .search-wrap input')?.focus()}>
          <I.i31 />
          Filtros
        </button>
      </div>
      <div className="list-meta-row">
        <span className="result-count">{countText}</span>
      </div>
      <div className="table-panel">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th className="sortable">
                  Materia
                  <I.i32 className="sort-icon" />
                </th>
                <th>Comisión</th>
                <th className="sortable">
                  Período
                  <I.i32 className="sort-icon" />
                </th>
                <th className="col-sede">Sede</th>
                <th>Horario</th>
                <th className="sortable">
                  Estudiantes
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
                  <td colSpan={7} className="muted-cell" style={{ textAlign: 'center', padding: '28px 16px' }}>
                    {message}
                    {isError && (
                      <>
                        {' '}
                        <button className="clear-filters show" style={{ display: 'inline-flex' }} onClick={refetch}>
                          Reintentar
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ) : (
                pageCourses.map((c) => (
                  <tr className="course-row" key={c.id} onClick={() => open(c.id)} tabIndex={0} onKeyDown={keyOpen(c.id)} role="button">
                    <td>
                      <div className="course-name">{c.name}</div>
                    </td>
                    <td className="muted-cell">{c.com}</td>
                    <td className="muted-cell">{c.period}</td>
                    <td className="muted-cell col-sede">{c.sede}</td>
                    <td className="muted-cell">{c.horario}</td>
                    <td className="muted-cell">{c.students}</td>
                    <td>
                      <span className={`badge ${c.statusClass}`}>{c.statusLabel}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <span className="pagination-info">{countText}</span>
          <div className="pagination-controls">
            <button className="page-btn" disabled={current === 1} aria-label="Página anterior" onClick={() => changePage(current - 1)}>
              <I.i33 />
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} className={`page-btn${i + 1 === current ? ' active' : ''}`} onClick={() => changePage(i + 1)}>
                {i + 1}
              </button>
            ))}
            <button
              className="page-btn"
              disabled={current === totalPages}
              aria-label="Página siguiente"
              onClick={() => changePage(current + 1)}
            >
              <I.i34 />
            </button>
          </div>
        </div>
      </div>
      <div className="course-cards">
        {message && <p className="result-count">{message}</p>}
        {!message &&
          pageCourses.map((c) => (
            <div
              key={c.id}
              className="course-card course-card-clickable"
              onClick={() => open(c.id)}
              tabIndex={0}
              onKeyDown={keyOpen(c.id)}
              role="button"
            >
              <div className="course-card-top">
                <div>
                  <p className="course-card-name">{c.name}</p>
                </div>
                <span className={`badge ${c.statusClass}`}>{c.statusLabel}</span>
              </div>
              <div className="course-card-meta">
                <div className="meta-item">
                  <span className="meta-label">Comisión</span>
                  <span className="meta-value">{c.com}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Período</span>
                  <span className="meta-value">{c.period}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Horario</span>
                  <span className="meta-value">{c.horario}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Estudiantes</span>
                  <span className="meta-value">{c.students}</span>
                </div>
              </div>
            </div>
          ))}
      </div>
    </AppShell>
  );
}
