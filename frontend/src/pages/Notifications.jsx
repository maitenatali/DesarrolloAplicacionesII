import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetNotificationsQuery, useMarkAllNotificationsReadMutation, useMarkNotificationMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { isoLongDate, isoTime } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import useToast from '../lib/useToast';
import '../styles/pages/20.css';

const PAGE_SIZE = 8;
const ICONS = { examen: I.i56, feriado: I.i23, evento: I.i25, comedor: I.i24 };
const CAT_LABEL = { examen: 'Examen', feriado: 'Feriado nacional', comedor: 'Comedor', evento: 'Evento académico', cuenta: 'Cuenta institucional' };
const MODULE_LABEL = { academic: 'Gestión Académica', events: 'Eventos', dining: 'Comedor', core: 'Cuenta institucional', store: 'Tienda' };

/** Tipo de notificación de CORE -> categoría visual del mockup. */
function category(n) {
  const t = `${n.type} ${n.sourceModule}`.toUpperCase();
  if (t.includes('EXAM') || t.includes('GRADE') || t.includes('ACTA')) return 'examen';
  if (t.includes('DINING')) return 'comedor';
  if (t.includes('HOLIDAY')) return 'feriado';
  return 'evento';
}

export default function Notifications() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useGetNotificationsQuery();
  const [markOne] = useMarkNotificationMutation();
  const [markAll, { isLoading: markingAll }] = useMarkAllNotificationsReadMutation();
  const [filter, setFilter] = useState('todas');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('recent');
  const [page, setPage] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [toast, showToast] = useToast(3000);
  useLockScroll(confirmOpen || !!detail);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setDetail(null);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const all = (data?.items || []).map((n) => ({ ...n, cat: category(n), unread: !n.readAt }));
  const term = search.trim().toLowerCase();
  const list = all
    .filter((n) => filter === 'todas' || n.unread)
    .filter((n) => !term || `${n.title} ${n.message}`.toLowerCase().includes(term))
    .sort((a, b) => (sort === 'recent' ? b.createdAt.localeCompare(a.createdAt) : a.createdAt.localeCompare(b.createdAt)));
  const totalPages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
  const current = Math.min(page, totalPages);
  const pageList = list.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const when = (n) => `${isoLongDate(n.createdAt)} · ${isoTime(n.createdAt)}`;
  const context = (n) => MODULE_LABEL[n.sourceModule] || CAT_LABEL[n.cat];

  const open = (n) => {
    setDetail(n);
    if (n.unread) markOne({ id: n.id, read: true });
  };
  const doMarkAll = async () => {
    try {
      await markAll().unwrap();
      setConfirmOpen(false);
      showToast('Todas las notificaciones fueron marcadas como leídas.');
    } catch (err) {
      setConfirmOpen(false);
      showToast(toApiError(err).detail);
    }
  };
  const changePage = (p) => {
    setPage(Math.max(1, p));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  let content;
  if (isLoading) {
    content = (
      <div className="notif-list">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skel" style={{ width: '100%', height: 72, marginBottom: 8, borderRadius: 10 }} />
        ))}
      </div>
    );
  } else if (isError) {
    content = (
      <div className="list-state">
        <span className="icon">
          <I.i3 />
        </span>
        <p>No pudimos cargar tus notificaciones</p>
        <span className="sub">{toApiError(error).detail}</span>
        <button className="btn-secondary" onClick={refetch}>
          Reintentar
        </button>
      </div>
    );
  } else if (!list.length) {
    content = (
      <div className="list-state">
        <span className="icon">
          <I.i103 />
        </span>
        <p>{all.length ? 'No hay notificaciones que coincidan' : 'No tenés notificaciones'}</p>
        <span className="sub">
          {all.length ? 'Probá con otro filtro o término de búsqueda.' : 'Cuando otros módulos te envíen avisos, aparecerán acá.'}
        </span>
      </div>
    );
  } else {
    content = (
      <div className="notif-list">
        {pageList.map((n) => {
          const Icon = ICONS[n.cat];
          return (
            <div key={n.id} className={`notif-item ${n.unread ? 'unread' : 'read'}`} onClick={() => open(n)}>
              <span className={`unread-dot${n.unread ? '' : ' hidden'}`} />
              <span className={`notif-icon ${n.cat}`}>
                <Icon />
              </span>
              <div className="notif-main">
                <div className="notif-top-row">
                  <p className="notif-title">{n.title}</p>
                </div>
                <p className="notif-desc">{n.message}</p>
                <div className="notif-bottom-row">
                  <span className="notif-context">{context(n)}</span>
                  <span className="notif-time">{when(n)}</span>
                  {n.unread && <span className="status-tag">No leída</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  const DetailIcon = detail ? ICONS[detail.cat] : null;
  const modals = (
    <>
      <div className={`modal-backdrop${confirmOpen ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setConfirmOpen(false)}>
        <div className="modal">
          <div className="modal-icon">
            <I.i101 />
          </div>
          <h3>¿Marcar todas como leídas?</h3>
          <p>Todas las notificaciones pendientes pasarán a estado leído.</p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setConfirmOpen(false)}>
              Cancelar
            </button>
            <button className="btn-primary" disabled={markingAll} onClick={doMarkAll}>
              Marcar como leídas
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-backdrop${detail ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setDetail(null)}>
        {detail && (
          <div className="modal notification-detail-modal" role="dialog" aria-modal="true" aria-labelledby="notificationDetailTitle">
            <div className="notification-detail-head">
              <span className={`modal-icon notification-detail-icon ${detail.cat}`}>
                <DetailIcon />
              </span>
              <button className="modal-close" aria-label="Cerrar" onClick={() => setDetail(null)}>
                <I.i76 />
              </button>
            </div>
            <p className="notification-detail-category">{context(detail)}</p>
            <h3 id="notificationDetailTitle">{detail.title}</h3>
            <p>{detail.message}</p>
            <div className="notification-detail-meta">
              <div>
                <span>Fecha</span>
                <strong>{when(detail)}</strong>
              </div>
              <div>
                <span>Tipo</span>
                <strong>{CAT_LABEL[detail.cat]}</strong>
              </div>
            </div>
            {detail.actionUrl?.startsWith('/') && !detail.actionUrl.startsWith('/student') && (
              <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => navigate(detail.actionUrl)}>
                Ver más
              </button>
            )}
          </div>
        )}
      </div>
      <div className={`toast${toast.show ? ' show' : ''}`}>
        <I.i102 />
        <span>{toast.message}</span>
      </div>
    </>
  );

  return (
    <AppShell scope="20" active="notificaciones" after={modals}>
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        / Notificaciones
      </p>
      <div className="page-head-row">
        <div>
          <h1 className="page-title">Notificaciones</h1>
          <p className="page-desc">Consultá todas tus notificaciones.</p>
        </div>
        <button className="btn-secondary" disabled={!all.some((n) => n.unread)} onClick={() => setConfirmOpen(true)}>
          <I.i100 />
          Marcar todas como leídas
        </button>
      </div>
      <div className="quick-filters">
        <button className={`pill${filter === 'todas' ? ' active' : ''}`} onClick={() => (setFilter('todas'), setPage(1))}>
          Todas <span className="count">{all.length}</span>
        </button>
        <button className={`pill${filter === 'noleidas' ? ' active' : ''}`} onClick={() => (setFilter('noleidas'), setPage(1))}>
          No leídas <span className="count">{all.filter((n) => n.unread).length}</span>
        </button>
      </div>
      <div className="toolbar-row">
        <div className="search-wrap">
          <I.i29 className="leading" />
          <input
            type="text"
            placeholder="Buscar por título o contenido..."
            value={search}
            onChange={(e) => (setSearch(e.target.value), setPage(1))}
          />
        </div>
      </div>
      <div className="sort-row">
        <label htmlFor="sortSelect">Ordenar por</label>
        <select className="sort-select" id="sortSelect" value={sort} onChange={(e) => (setSort(e.target.value), setPage(1))}>
          <option value="recent">Más recientes</option>
          <option value="oldest">Más antiguas</option>
        </select>
      </div>
      <div>{content}</div>
      <div className="pagination" aria-label="Paginación de notificaciones">
        {list.length > 0 && totalPages > 1 && (
          <>
            <button className="page-btn" disabled={current === 1} aria-label="Página anterior" onClick={() => changePage(current - 1)}>
              <I.i83 />
            </button>
            <span className="page-ellipsis">
              Página {current} de {totalPages}
            </span>
            <button className="page-btn" disabled={current === totalPages} aria-label="Página siguiente" onClick={() => changePage(current + 1)}>
              <I.i104 />
            </button>
          </>
        )}
      </div>
    </AppShell>
  );
}
