import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetTransactionsQuery, useGetWalletQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { dateTimeParts, isoShortDate, isoTime, money } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/25.css';

const PAGE_SIZE = 8;
// TODO(CORE): catálogo de conceptos de wallet; los no listados se muestran tal cual.
const CONCEPT = {
  TOP_UP: 'Recarga institucional',
  STORE_PURCHASE: 'Compra en tienda virtual',
  DINING_RESERVATION: 'Reserva de comedor',
  EVENT_REGISTRATION: 'Inscripción a evento',
  REFUND: 'Reintegro',
};
const signed = (t) => (t.type === 'DEBIT' ? -1 : 1) * Number(t.amount);
const sMoney = (n) => `${n < 0 ? '−' : '+'}${money(Math.abs(n))}`;
const DirIcon = ({ amount }) => (amount >= 0 ? <I.i107 /> : <I.i108 />);

export default function Account() {
  const navigate = useNavigate();
  const wallet = useGetWalletQuery();
  const txs = useGetTransactionsQuery();
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('recientes');
  const [typeDraft, setTypeDraft] = useState('todos');
  const [type, setType] = useState('todos');
  const [panelOpen, setPanelOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState(null);
  const panelRef = useRef(null);
  const balanceRef = useRef(null);
  useLockScroll(!!detail);

  useEffect(() => {
    const close = (e) => panelRef.current && !panelRef.current.contains(e.target) && setPanelOpen(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  const movs = (txs.data?.items || []).map((t) => {
    const amount = signed(t);
    const concept = CONCEPT[t.concept] || t.concept;
    return {
      ...t,
      amount,
      concept,
      opNumber: `MOV-${t.transactionId.slice(0, 8).toUpperCase()}`,
      date: isoShortDate(t.createdAt),
      time: isoTime(t.createdAt),
      typeLabel: `${amount >= 0 ? 'Ingreso' : 'Egreso'}${t.status === 'PENDING' ? ' (pendiente)' : ''}`,
      prevBalance: Number(t.balanceAfter) - (t.status === 'POSTED' ? amount : 0),
    };
  });
  const thisMonth = dateTimeParts(new Date().toISOString()).day.slice(0, 7);
  const monthMovs = movs.filter((m) => m.status === 'POSTED' && dateTimeParts(m.createdAt).day.startsWith(thisMonth));
  const income = monthMovs.filter((m) => m.amount > 0).reduce((s, m) => s + m.amount, 0);
  const expense = monthMovs.filter((m) => m.amount < 0).reduce((s, m) => s + m.amount, 0);

  const term = search.trim().toLowerCase();
  const filtered = movs
    .filter((m) => type === 'todos' || (type === 'ingreso' ? m.amount >= 0 : m.amount < 0))
    .filter((m) => !term || `${m.concept} ${m.opNumber}`.toLowerCase().includes(term))
    .sort(
      {
        recientes: (a, b) => b.createdAt.localeCompare(a.createdAt),
        antiguos: (a, b) => a.createdAt.localeCompare(b.createdAt),
        mayor: (a, b) => Math.abs(b.amount) - Math.abs(a.amount),
        menor: (a, b) => Math.abs(a.amount) - Math.abs(b.amount),
      }[sort],
    );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, totalPages);
  const items = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const dirty = type !== 'todos' || !!term;
  const clear = () => {
    setTypeDraft('todos');
    setType('todos');
    setSearch('');
    setPage(1);
  };

  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || Math.abs(i - current) <= 1) pages.push(i);
    else if (Math.abs(i - current) === 2) pages.push(`e${i}`);
  }

  const modal = (
    <div className={`modal-backdrop${detail ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setDetail(null)}>
      {detail && (
        <div className="modal-card">
          <div className="modal-head">
            <h3>Detalle del movimiento</h3>
            <button className="modal-close" aria-label="Cerrar" onClick={() => setDetail(null)}>
              <I.i52 />
            </button>
          </div>
          <div className="modal-body">
            <div className="modal-concept-row">
              <span className={`mov-dir-icon ${detail.amount >= 0 ? 'in' : 'out'}`}>
                <DirIcon amount={detail.amount} />
              </span>
              <div>
                <p className="modal-concept-name">{detail.concept}</p>
                <p className="modal-concept-type">{detail.typeLabel}</p>
              </div>
            </div>
            <div className="modal-stat-row">
              <span>Número de operación</span>
              <span>{detail.opNumber}</span>
            </div>
            <div className="modal-stat-row">
              <span>Fecha</span>
              <span>
                {detail.date} · {detail.time}
              </span>
            </div>
            <div className="modal-stat-row">
              <span>Importe</span>
              <span style={{ color: detail.amount >= 0 ? 'var(--success-600)' : 'var(--error-600)' }}>{sMoney(detail.amount)}</span>
            </div>
            <div className="modal-stat-row">
              <span>Saldo anterior</span>
              <span>{money(detail.prevBalance)}</span>
            </div>
            <div className="modal-stat-row">
              <span>Saldo resultante</span>
              <span>{money(detail.balanceAfter)}</span>
            </div>
            {detail.externalReference && (
              <div className="modal-related-box">
                <p className="mr-label">Referencia</p>
                <p className="mr-value">{detail.externalReference}</p>
              </div>
            )}
          </div>
          <div className="modal-foot">
            <button className="btn-secondary" onClick={() => setDetail(null)}>
              Cerrar
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <AppShell
      scope="25"
      active="cuenta"
      onBalanceClick={() => balanceRef.current?.scrollIntoView({ behavior: 'smooth' })}
      after={modal}
    >
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        / <span className="current">Cuenta institucional</span>
      </p>
      <div>
        <div className="page-head">
          <div>
            <h1>Cuenta institucional</h1>
            <p>Consultá tu saldo disponible y el historial de movimientos de tu cuenta institucional.</p>
          </div>
        </div>
        <div className="balance-card" ref={balanceRef}>
          <div className="balance-card-top">
            <div>
              <p className="balance-label">Saldo disponible</p>
              <p className="balance-amount">{wallet.data ? money(wallet.data.balance) : wallet.isError ? '—' : '…'}</p>
            </div>
          </div>
          <div className="quick-actions-row">
            <button className="btn-primary" onClick={() => navigate('/cuenta/cargar-saldo')}>
              <I.i64 />
              Cargar saldo
            </button>
            <button className="btn-secondary" onClick={() => navigate('/compras')}>
              Ver mis compras
            </button>
          </div>
        </div>
        <div className="indicators-grid two">
          <div className="indicator-card">
            <span className="indicator-value up">{sMoney(income)}</span>
            <span className="indicator-label">Ingresos este mes</span>
          </div>
          <div className="indicator-card">
            <span className="indicator-value down">{sMoney(expense)}</span>
            <span className="indicator-label">Gastos este mes</span>
          </div>
        </div>
        <div className="section-head">
          <h2>Movimientos</h2>
          <p>Historial de operaciones de tu cuenta institucional.</p>
        </div>
        <div className="panel">
          <div className="toolbar">
            <div className="search-wrap">
              <I.i29 />
              <input
                type="text"
                placeholder="Buscar por concepto o número de operación"
                value={search}
                onChange={(e) => (setSearch(e.target.value), setPage(1))}
              />
            </div>
            <select className="sort-select" value={sort} onChange={(e) => (setSort(e.target.value), setPage(1))}>
              <option value="recientes">Ordenar: Más recientes</option>
              <option value="antiguos">Ordenar: Más antiguos</option>
              <option value="mayor">Ordenar: Mayor importe</option>
              <option value="menor">Ordenar: Menor importe</option>
            </select>
            <div className="filters-btn-wrap" ref={panelRef}>
              <button className="btn-secondary" onClick={() => setPanelOpen((o) => !o)}>
                <I.i31 />
                Filtros
              </button>
              <div className={`filters-panel${panelOpen ? ' show' : ''}`}>
                <div className="field">
                  <label htmlFor="typeFilter">Tipo de movimiento</label>
                  <select id="typeFilter" value={typeDraft} onChange={(e) => setTypeDraft(e.target.value)}>
                    <option value="todos">Todos</option>
                    <option value="ingreso">Ingresos</option>
                    <option value="egreso">Egresos</option>
                  </select>
                </div>
                <div className="filters-panel-actions">
                  <button className="btn-secondary" onClick={clear}>
                    Limpiar filtros
                  </button>
                  <button
                    className="btn-primary"
                    onClick={() => {
                      setType(typeDraft);
                      setPanelOpen(false);
                      setPage(1);
                    }}
                  >
                    Aplicar filtros
                  </button>
                </div>
              </div>
            </div>
            <button className={`btn-ghost filters-clear${dirty ? ' show' : ''}`} onClick={clear}>
              <I.i52 style={{ width: '14px', height: '14px' }} />
              Limpiar filtros
            </button>
          </div>
          <div className="table-panel">
            {txs.isLoading ? (
              <div className="skel" style={{ width: '100%', height: 160 }} />
            ) : txs.isError ? (
              <div className="empty-state">
                <I.i3 />
                <p>No pudimos cargar los movimientos</p>
                <p className="state-sub">{toApiError(txs.error).detail}</p>
                <button className="btn-secondary" style={{ marginTop: 8 }} onClick={() => txs.refetch()}>
                  Reintentar
                </button>
              </div>
            ) : !filtered.length ? (
              <div className="empty-state">
                <I.i29 />
                <p>No encontramos movimientos</p>
                <p className="state-sub">Probá modificando los filtros o realizando otra búsqueda.</p>
                <button className="btn-secondary" style={{ marginTop: 8 }} onClick={clear}>
                  Limpiar filtros
                </button>
              </div>
            ) : (
              <table className="mov-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Concepto</th>
                    <th>Tipo</th>
                    <th>Importe</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((m) => {
                    const dir = m.amount >= 0 ? 'in' : 'out';
                    return (
                      <tr key={m.transactionId} onClick={() => setDetail(m)}>
                        <td>
                          <p className="mov-date">{m.date}</p>
                          <p className="mov-time">{m.time}</p>
                        </td>
                        <td>
                          <div className="mov-concept-row">
                            <span className={`mov-dir-icon ${dir}`}>
                              <DirIcon amount={m.amount} />
                            </span>
                            <span className="mov-concept">{m.concept}</span>
                          </div>
                        </td>
                        <td>{m.typeLabel}</td>
                        <td className={`mov-amount ${dir}`}>{sMoney(m.amount)}</td>
                        <td>
                          <button
                            className="detail-link"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDetail(m);
                            }}
                          >
                            Ver detalle
                            <I.i34 />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <div className="mov-cards">
            {filtered.length > 0 &&
              items.map((m) => {
                const dir = m.amount >= 0 ? 'in' : 'out';
                return (
                  <div className="mov-card" key={m.transactionId} onClick={() => setDetail(m)}>
                    <p className="mov-card-date">
                      {m.date} · {m.time}
                    </p>
                    <div className="mov-card-concept">
                      <span className={`mov-dir-icon ${dir}`}>
                        <DirIcon amount={m.amount} />
                      </span>
                      <span className="mov-concept">{m.concept}</span>
                    </div>
                    <p className="mov-card-type">{m.typeLabel}</p>
                    <p className={`mov-card-amount ${dir}`}>{sMoney(m.amount)}</p>
                    <div className="mov-card-foot">
                      <button className="detail-link">
                        Ver detalle
                        <I.i34 />
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
          <div className="pagination" style={{ display: filtered.length ? 'flex' : 'none' }}>
            <span className="pagination-info">
              Mostrando {Math.min((current - 1) * PAGE_SIZE + 1, filtered.length)}–{Math.min(current * PAGE_SIZE, filtered.length)} de{' '}
              {filtered.length} movimientos
            </span>
            <div className="pagination-controls">
              <button className="page-btn" disabled={current === 1} aria-label="Página anterior" onClick={() => setPage(current - 1)}>
                <I.i33 />
              </button>
              {pages.map((p) =>
                typeof p === 'number' ? (
                  <button key={p} className={`page-btn${p === current ? ' active' : ''}`} onClick={() => setPage(p)}>
                    {p}
                  </button>
                ) : (
                  <span key={p} className="page-ellipsis">
                    …
                  </span>
                ),
              )}
              <button
                className="page-btn"
                disabled={current === totalPages}
                aria-label="Página siguiente"
                onClick={() => setPage(current + 1)}
              >
                <I.i34 />
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
