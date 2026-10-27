import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetCalendarQuery, useGetCoursesQuery } from '../api/api';
import AppShell, { useCurrentTeacher } from '../components/AppShell';
import * as I from '../components/icons.generated';
import { calendarCategory, calendarItemTimes, campusName, CATEGORY_LABEL, courseRoom, isActiveCourse } from '../lib/domain';
import { longDate, toDay } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/02.css';

const ICON = { feriado: I.i23, comedor: I.i24, evento: I.i25, examen: I.i26 };

function clock(t) {
  return t.time ? (t.endTime ? `${t.time}–${t.endTime}` : t.time) : '';
}

function SkeletonList({ rows }) {
  return Array.from({ length: rows }, (_, i) => (
    <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '12px 10px' }}>
      <div className="skel" style={{ width: 38, height: 38, borderRadius: 9, flexShrink: 0 }} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div className="skel" style={{ width: '70%', height: 12 }} />
        <div className="skel" style={{ width: '45%', height: 11 }} />
      </div>
    </div>
  ));
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { firstName } = useCurrentTeacher();
  const courses = useGetCoursesQuery();
  const range = useMemo(() => {
    const from = new Date();
    const to = new Date();
    to.setDate(to.getDate() + 120);
    return { from: toDay(from), to: toDay(to) };
  }, []);
  const calendar = useGetCalendarQuery(range);
  const [selected, setSelected] = useState(null);
  useLockScroll(!!selected);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setSelected(null);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const courseById = useMemo(() => new Map((courses.data || []).map((c) => [c.id, c])), [courses.data]);

  // Igual que el mockup: las 4 actividades futuras más cercanas del mismo conjunto que alimenta el Calendario.
  const activities = useMemo(() => {
    const now = Date.now();
    return (calendar.data?.items || [])
      .filter((it) => !(it.kind === 'EXAM' && it.reference?.phase === 'CANCELLED'))
      .map((it) => {
        const t = calendarItemTimes(it);
        const ts = new Date(it.start || `${t.day}T12:00:00`).getTime();
        const cat = calendarCategory(it);
        const course = it.reference?.courseId ? courseById.get(it.reference.courseId) : null;
        return { it, t, ts, cat, course };
      })
      .filter((a) => a.ts > now)
      .sort((a, b) => a.ts - b.ts)
      .slice(0, 4);
  }, [calendar.data, courseById]);

  const activeCount = (courses.data || []).filter(isActiveCourse).length;
  const today = new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });

  const activityName = (a) => (a.cat === 'examen' ? a.it.title.replace(' · ', ' — ') : a.it.title);

  let body;
  if (calendar.isLoading) body = <SkeletonList rows={3} />;
  else if (calendar.isError)
    body = (
      <div className="error-state">
        <I.i3 />
        <p>No pudimos cargar esta información.</p>
        <button className="retry-btn" onClick={() => calendar.refetch()}>
          Reintentar
        </button>
      </div>
    );
  else if (!activities.length)
    body = (
      <div className="empty-state">
        <I.i28 />
        <p>No hay actividades próximas.</p>
      </div>
    );
  else
    body = (
      <div className="activities-list">
        {activities.map((a) => {
          const Icon = ICON[a.cat];
          const date = longDate(a.t.day);
          const extra =
            a.cat === 'examen' ? `Comisión ${a.course?.code || '—'}` : a.cat === 'feriado' ? 'Sin actividades académicas' : '';
          return (
            <button type="button" className="activity-item" key={a.it.id} onClick={() => setSelected(a)}>
              <span className={`activity-icon ${a.cat}`}>
                <Icon />
              </span>
              <span className="activity-main">
                <span className="activity-top">
                  <span className={`activity-type ${a.cat}`}>{CATEGORY_LABEL[a.cat]}</span>
                </span>
                <p className="activity-name">{activityName(a)}</p>
                <p className="activity-meta">{a.t.time ? `${date} · ${clock(a.t)}` : date}</p>
                {extra && <p className="activity-extra">{extra}</p>}
              </span>
              <I.i27 className="chev" />
            </button>
          );
        })}
      </div>
    );

  const Row = ({ label, value }) => (
    <div className="dashboard-modal-row">
      <span className="lbl">{label}</span>
      <span className="val">{value || '—'}</span>
    </div>
  );

  const modal = (
    <div
      className={`dashboard-modal-backdrop${selected ? ' show' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dashboardModalTitle"
      onClick={(e) => e.target === e.currentTarget && setSelected(null)}
    >
      {selected && (
        <div className="dashboard-modal">
          <div className="dashboard-modal-head">
            <div>
              <p className={`dashboard-modal-kicker ${selected.cat}`}>{CATEGORY_LABEL[selected.cat]}</p>
              <p className="dashboard-modal-title" id="dashboardModalTitle">
                {activityName(selected)}
              </p>
            </div>
            <button type="button" className="dashboard-modal-close" aria-label="Cerrar" onClick={() => setSelected(null)}>
              ✕
            </button>
          </div>
          <div className="dashboard-modal-body">
            <Row label="Fecha" value={longDate(selected.t.day)} />
            {selected.cat === 'examen' && (
              <>
                <Row label="Horario" value={clock(selected.t)} />
                <Row label="Sede" value={campusName(selected.course?.campusId)} />
                <Row label="Aula" value={courseRoom(selected.course)} />
                <Row label="Comisión" value={selected.course?.code} />
                <Row label="Tipo" value={selected.it.title.split(' · ')[0]} />
              </>
            )}
            {selected.cat === 'comedor' && (
              <>
                <Row label="Horario" value={clock(selected.t)} />
                <Row label="Ubicación" value={selected.it.location} />
              </>
            )}
            {selected.cat === 'evento' && selected.it.location && <Row label="Ubicación" value={selected.it.location} />}
          </div>
          <div className="dashboard-modal-footer">
            {selected.cat === 'examen' && (
              <button
                type="button"
                className="btn-primary"
                onClick={() => navigate(`/cursos/${selected.it.reference.courseId}/examenes/${selected.it.reference.examId}`)}
              >
                Ver examen
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <AppShell scope="02" active="inicio" after={modal}>
      <div className="page-head">
        <p className="breadcrumb">Inicio</p>
        <h1 className="greeting">¡Hola, {firstName}!</h1>
        <div className="greeting-sub">
          <span className="today-chip">{today}</span>
        </div>
      </div>
      <section className="summary-grid" aria-label="Resumen rápido">
        {courses.isLoading ? (
          <div className="summary-card" style={{ cursor: 'default' }}>
            <div className="skel" style={{ width: 38, height: 38, borderRadius: 10 }} />
            <div className="skel" style={{ width: '50%', height: 22 }} />
            <div className="skel" style={{ width: '70%', height: 12 }} />
          </div>
        ) : (
          <button className="summary-card" onClick={() => navigate('/cursos')}>
            <span className="summary-icon blue">
              <I.i18 />
            </span>
            <span className="summary-value">{activeCount}</span>
            <span className="summary-label">Cursos activos</span>
          </button>
        )}
      </section>
      <section style={{ marginBottom: '28px' }}>
        <h2 className="section-title">Accesos rápidos</h2>
        <div className="quick-grid">
          <button className="quick-card" onClick={() => navigate('/actas/nueva')}>
            <span className="quick-icon">
              <I.i19 />
            </span>
            <span className="quick-label">Nueva acta</span>
          </button>
          <button className="quick-card" onClick={() => navigate('/calendario')}>
            <span className="quick-icon">
              <I.i20 />
            </span>
            <span className="quick-label">Ver calendario</span>
          </button>
        </div>
      </section>
      <section className="two-col single-panel">
        <div className="panel">
          <div className="panel-head">
            <h2 className="panel-title">Notificaciones recientes</h2>
          </div>
          <div className="panel-body">{body}</div>
          <div className="activities-footer">
            <button type="button" className="activities-all" onClick={() => navigate('/notificaciones')}>
              Ver todas las notificaciones <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
