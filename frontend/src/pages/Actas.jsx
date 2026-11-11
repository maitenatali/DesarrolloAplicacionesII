import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetActasQuery } from '../api/api';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { shortDate } from '../lib/format';
import useToast from '../lib/useToast';
import '../styles/pages/15.css';

const ACTA_NAME = { FINAL: 'Acta Final', CURSADA: 'Acta de Cursada' };
const STATUS_TEXT = { GENERADA: 'Finalizada', ANULADA: 'Anulada' };

function SkeletonRows({ n }) {
  return Array.from({ length: n }, (_, i) => (
    <div className="skel-row" key={i}>
      <div className="skel" style={{ width: 130, height: 14 }} />
      <div className="skel" style={{ width: 160, height: 14 }} />
      <div className="skel" style={{ width: 70, height: 14 }} />
      <div className="skel" style={{ width: 90, height: 14 }} />
      <div className="skel" style={{ width: 90, height: 14, marginLeft: 'auto' }} />
    </div>
  ));
}

export default function Actas() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useGetActasQuery();
  const [search, setSearch] = useState('');
  const [periodo, setPeriodo] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sort, setSort] = useState({ col: 'fecha', dir: 'desc' });
  const [toast] = useToast();

  const actas = data?.items || [];
  const periods = [...new Set(actas.map((a) => a.period))];
  const term = search.trim().toLowerCase();
  const rows = actas
    .filter((a) => !periodo || a.period === periodo)
    .filter((a) => !term || `${ACTA_NAME[a.type]} ${a.number} ${a.subject} ${a.commission} ${a.period}`.toLowerCase().includes(term))
    .sort((x, y) => {
      const key = { fecha: (a) => a.date, numero: (a) => a.number, curso: (a) => a.subject }[sort.col];
      const r = key(x) < key(y) ? -1 : key(x) > key(y) ? 1 : 0;
      return sort.dir === 'asc' ? r : -r;
    });
  const setSortCol = (col) => setSort((s) => (s.col === col ? { col, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { col, dir: 'asc' }));
  const thCls = (col) => `sortable${sort.col === col ? ' sort-active' : ''}${sort.col === col && sort.dir === 'desc' ? ' sort-desc' : ''}`;
  const clear = () => {
    setSearch('');
    setPeriodo('');
  };
  const open = (a) => navigate(`/actas/${a.id}`);

  let state = null;
  if (isLoading) state = <SkeletonRows n={4} />;
  else if (isError)
    state = (
      <div className="state-block error">
        <span className="state-icon">
          <I.i3 />
        </span>
        <h3>No pudimos cargar las actas</h3>
        <p>Ocurrió un problema al obtener la información. Intentá nuevamente.</p>
        <button className="btn-secondary" onClick={refetch}>
          Reintentar
        </button>
      </div>
    );
  else if (!actas.length)
    state = (
      <div className="state-block">
        <span className="state-icon">
          <I.i19 />
        </span>
        <h3>No hay actas registradas</h3>
        <p>Todavía no se generaron actas para tus cursos.</p>
        <button className="btn-primary" onClick={() => navigate('/actas/nueva')}>
          <I.i51 />
          Nueva acta
        </button>
      </div>
    );
  else if (!rows.length)
    state = (
      <div className="state-block">
        <span className="state-icon">
          <I.i29 />
        </span>
        <h3>No encontramos actas</h3>
        <p>Probá modificando los filtros o el término de búsqueda.</p>
        <button className="btn-secondary" onClick={clear}>
          Limpiar filtros
        </button>
      </div>
    );

  return (
    <AppShell
      scope="15"
      active="actas"
      after={
        <div className={`toast${toast.show ? ' show' : ''}`}>
          <span className="toast-icon">
            <I.i55 />
          </span>
          <span>{toast.message}</span>
        </div>
      }
    >
      <p className="breadcrumb">
        <button onClick={() => navigate('/')}>Inicio</button>
        <span className="sep">/</span>
        <span className="current">Actas</span>
      </p>
      <div className="page-head">
        <div>
          <h1 className="page-title">Actas</h1>
          <p className="page-desc">Consultá y generá las actas académicas de tus cursos.</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/actas/nueva')}>
          <I.i51 />
          Nueva acta
        </button>
      </div>
      <div className="toolbar">
        <div className="search-field">
          <I.i29 />
          <input type="text" placeholder="Buscar acta..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <button className={`filters-toggle${filtersOpen ? ' active' : ''}`} onClick={() => setFiltersOpen((o) => !o)}>
          <I.i75 />
          Filtros
        </button>
      </div>
      <div className={`filters-row${filtersOpen ? ' open' : ''}`}>
        <select className="filter-select" value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
          <option value="">Todos los períodos</option>
          {periods.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button className={`clear-filters${search || periodo ? ' show' : ''}`} onClick={clear}>
          <I.i76 />
          Limpiar filtros
        </button>
      </div>
      <section className="panel">
        <div className="panel-head">
          <h2 className="panel-title">Listado de actas</h2>
          <span className="results-count">{!state ? `${rows.length} ${rows.length === 1 ? 'resultado' : 'resultados'}` : ''}</span>
        </div>
        <table className="actas-table">
          <thead>
            <tr>
              <th className={thCls('numero')} onClick={() => setSortCol('numero')}>
                Acta
                <I.i77 className="sort-ind" />
              </th>
              <th className={thCls('curso')} onClick={() => setSortCol('curso')}>
                Curso
                <I.i77 className="sort-ind" />
              </th>
              <th className="col-periodo">Período</th>
              <th className={thCls('fecha')} onClick={() => setSortCol('fecha')}>
                Fecha
                <I.i77 className="sort-ind" />
              </th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {state ? (
              <tr>
                <td colSpan={7} style={{ padding: 0 }}>
                  {state}
                </td>
              </tr>
            ) : (
              rows.map((a) => (
                <tr
                  key={a.id}
                  className="acta-row"
                  onClick={() => open(a)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      open(a);
                    }
                  }}
                  role="button"
                >
                  <td className="col-acta">
                    <div className="acta-name">{ACTA_NAME[a.type] || 'Acta'}</div>
                    <div className="acta-number">N.º {a.number}</div>
                  </td>
                  <td className="col-curso">
                    <div className="course-cell-name">{a.subject}</div>
                    <div className="course-cell-meta">Comisión {a.commission}</div>
                  </td>
                  <td className="col-periodo">{a.period}</td>
                  <td className="col-fecha">{shortDate(a.date)}</td>
                  <td className="col-estado">
                    <span className={`status-badge ${a.status === 'GENERADA' ? 'status-finalized' : 'status-pending'}`}>
                      {STATUS_TEXT[a.status] || a.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <div className="pagination" style={{ display: state ? 'none' : 'flex' }}>
          <span className="pagination-info">
            1–{rows.length} de {rows.length} actas
          </span>
          <div className="pagination-controls">
            <button className="page-btn" disabled aria-label="Página anterior">
              ‹ Anterior
            </button>
            <button className="page-btn active">1</button>
            <button className="page-btn" disabled aria-label="Página siguiente">
              Siguiente ›
            </button>
          </div>
          <span className="pagination-mobile">Anterior | Página 1 de 1 | Siguiente</span>
        </div>
      </section>
    </AppShell>
  );
}
