import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetPurchasesQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import Pagination, { paginate } from '../components/Pagination';
import { isoShortDate, isoTime, money } from '../lib/format';
import { purchaseCode, purchaseName } from '../lib/purchases';
import '../styles/pages/22.css';

const PAGE_SIZE = 8;
const SORTS = {
  'Más recientes': (a, b) => b.createdAt.localeCompare(a.createdAt),
  'Más antiguas': (a, b) => a.createdAt.localeCompare(b.createdAt),
  'Mayor importe': (a, b) => Number(b.total) - Number(a.total),
  'Menor importe': (a, b) => Number(a.total) - Number(b.total),
};

export default function Purchases() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useGetPurchasesQuery();
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('Más recientes');
  const [page, setPage] = useState(1);

  const purchases = (data || []).map((p) => ({ ...p, code: purchaseCode(p), name: purchaseName(p) }));
  const term = search.trim().toLowerCase();
  const filtered = purchases
    .filter((p) => !term || `${p.code} ${p.items.map((i) => i.productName).join(' ')}`.toLowerCase().includes(term))
    .sort(SORTS[sort]);
  const pager = paginate(filtered, page, PAGE_SIZE);
  const text = `Mostrando ${pager.start} a ${pager.end} de ${pager.total} compras`;
  const open = (p) => navigate(`/compras/${p.purchaseId}`);

  let message = null;
  if (isLoading) message = 'Cargando compras…';
  else if (isError) message = toApiError(error).detail;
  else if (!filtered.length) message = purchases.length ? 'No encontramos compras con esa búsqueda.' : 'Todavía no realizaste compras.';

  return (
    <AppShell scope="22" active="compras">
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        / <span className="current">Mis compras</span>
      </p>
      <div className="page-header-row">
        <div>
          <h1 className="page-title">Mis compras</h1>
          <p className="page-desc">Consultá el historial de tus compras y consumos realizados desde el Portal del Docente.</p>
        </div>
      </div>
      <div>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{purchases.length}</span>
            <span className="stat-label">Compras realizadas</span>
          </div>
        </div>
        <div className="toolbar">
          <div className="search-wrap">
            <I.i29 className="leading" />
            <input
              type="text"
              placeholder="Buscar por producto o número de compra"
              value={search}
              onChange={(e) => (setSearch(e.target.value), setPage(1))}
            />
          </div>
          <div className="filters-wrap" />
          <select className="filter-select" value={sort} onChange={(e) => (setSort(e.target.value), setPage(1))}>
            {Object.keys(SORTS).map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="list-meta-row">
          <span className="result-count">{text}</span>
        </div>
        <div className="table-panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Compra</th>
                  <th>Importe</th>
                </tr>
              </thead>
              <tbody>
                {message ? (
                  <tr>
                    <td colSpan={3} style={{ textAlign: 'center', padding: '28px 16px', color: 'var(--text-600)' }}>
                      {message}
                    </td>
                  </tr>
                ) : (
                  pager.items.map((p) => (
                    <tr key={p.purchaseId} onClick={() => open(p)} style={{ cursor: 'pointer' }}>
                      <td className="date-cell">
                        <p className="date-main">{isoShortDate(p.createdAt)}</p>
                        <p className="date-time">{isoTime(p.createdAt)}</p>
                      </td>
                      <td className="purchase-cell">
                        <p className="purchase-name">{p.name}</p>
                        <p className="purchase-id">{p.code}</p>
                      </td>
                      <td className="amount-cell">{money(p.total)}</td>
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
        <div className="purchase-cards">
          {!message &&
            pager.items.map((p) => (
              <div className="purchase-card" key={p.purchaseId} onClick={() => open(p)} style={{ cursor: 'pointer' }}>
                <div className="purchase-card-top">
                  <div>
                    <p className="purchase-card-id">{p.code}</p>
                    <p className="purchase-card-name">{p.name}</p>
                  </div>
                </div>
                <p className="purchase-card-date">
                  {isoShortDate(p.createdAt)} · {isoTime(p.createdAt)}
                </p>
                <div className="purchase-card-amount-row">
                  <p className="purchase-card-amount">{money(p.total)}</p>
                </div>
              </div>
            ))}
        </div>
      </div>
    </AppShell>
  );
}
