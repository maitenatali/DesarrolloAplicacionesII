import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetCalendarQuery, useGetCoursesQuery } from '../api/api';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { calendarCategory, calendarItemTimes, campusName, CATEGORY_LABEL, courseRoom } from '../lib/domain';
import { longDate, money, MONTHS, parseDay, toDay, WEEKDAYS } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/18.css';

const CATS = [
  ['examen', 'Exámenes'],
  ['evento', 'Eventos académicos'],
  ['feriado', 'Feriados'],
  ['comedor', 'Comedor'],
];
const ICON = { examen: I.i94, evento: I.i60, feriado: I.i98, comedor: I.i99 };
const COLOR = (cat) => `var(--${cat}-c)`;
const BG = (cat) => `var(--${cat}-bg)`;
const HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
const WEEKDAY_SHORT = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const monthName = (i) => capital(MONTHS[i]);

function startOfWeek(d) {
  const r = new Date(d);
  const day = r.getDay();
  r.setDate(r.getDate() + ((day === 0 ? -6 : 1) - day));
  return r;
}
function addDays(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export default function Calendar() {
  const navigate = useNavigate();
  const today = useMemo(() => {
    const t = new Date();
    t.setHours(0, 0, 0, 0);
    return t;
  }, []);
  const [view, setView] = useState('month');
  const [viewDate, setViewDate] = useState(today);
  const [active, setActive] = useState(() => new Set(CATS.map(([c]) => c)));
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [dayList, setDayList] = useState(null);
  const filtersRef = useRef(null);
  useLockScroll(!!selected || !!dayList);

  useEffect(() => {
    const close = (e) => filtersRef.current && !filtersRef.current.contains(e.target) && setFiltersOpen(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  // Rango que necesita la vista actual (la API devuelve los ítems de [from, to]).
  const gridStart = useMemo(() => startOfWeek(new Date(viewDate.getFullYear(), viewDate.getMonth(), 1)), [viewDate]);
  const range = useMemo(() => {
    if (view === 'month') return { from: toDay(gridStart), to: toDay(addDays(gridStart, 41)) };
    if (view === 'week') {
      const s = startOfWeek(viewDate);
      return { from: toDay(s), to: toDay(addDays(s, 6)) };
    }
    if (view === 'day') return { from: toDay(viewDate), to: toDay(viewDate) };
    return { from: toDay(today), to: toDay(addDays(today, 120)) };
  }, [view, viewDate, gridStart, today]);
  const cal = useGetCalendarQuery(range);
  const upcoming = useGetCalendarQuery({ from: toDay(today), to: toDay(addDays(today, 120)) });
  const courses = useGetCoursesQuery();
  const courseById = useMemo(() => new Map((courses.data || []).map((c) => [c.id, c])), [courses.data]);

  const toEvent = (it) => {
    const t = calendarItemTimes(it);
    const cat = calendarCategory(it);
    const course = it.reference?.courseId ? courseById.get(it.reference.courseId) : null;
    return { id: it.id, it, cat, date: t.day, time: t.time, end: t.endTime, endDay: t.endDay, title: it.title.replace(' · ', ' — '), course };
  };
  const events = useMemo(
    () =>
      (cal.data?.items || [])
        .filter((it) => !(it.kind === 'EXAM' && it.reference?.phase === 'CANCELLED'))
        .map(toEvent)
        .filter((e) => active.has(e.cat)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cal.data, active, courseById],
  );
  const nowTs = Date.now();
  const nextEvent = useMemo(
    () =>
      (upcoming.data?.items || [])
        .filter((it) => !(it.kind === 'EXAM' && it.reference?.phase === 'CANCELLED'))
        .map(toEvent)
        .filter((e) => new Date(e.it.start || `${e.date}T23:59`).getTime() > nowTs)
        .sort((a, b) => `${a.date}${a.time || ''}`.localeCompare(`${b.date}${b.time || ''}`))[0],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [upcoming.data, courseById],
  );

  const isPast = (e) => new Date(e.it.end || e.it.start || `${e.date}T23:59`).getTime() < nowTs;
  const byDay = (day) => events.filter((e) => e.date === day);

  const change = (delta) => {
    const d = new Date(viewDate);
    if (view === 'day') d.setDate(d.getDate() + delta);
    else if (view === 'week') d.setDate(d.getDate() + delta * 7);
    else d.setMonth(d.getMonth() + delta, 1);
    setViewDate(d);
  };

  let label;
  if (view === 'month' || view === 'agenda') label = `${monthName(viewDate.getMonth())} ${viewDate.getFullYear()}`;
  else if (view === 'week') {
    const s = startOfWeek(viewDate);
    const e = addDays(s, 6);
    label = `${s.getDate()}–${e.getDate()} de ${MONTHS[e.getMonth()]} ${e.getFullYear()}`;
  } else label = `${viewDate.getDate()} de ${MONTHS[viewDate.getMonth()]} ${viewDate.getFullYear()}`;

  const relLabel = (e) => {
    const d = parseDay(e.date);
    const diff = Math.round((d - today) / 86400000);
    const when = diff === 0 ? 'Hoy' : diff === 1 ? 'Mañana' : longDate(e.date);
    const where = e.cat === 'examen' ? (e.course ? `Aula ${courseRoom(e.course)}` : e.it.location) : e.it.location;
    return [when, e.time, where].filter(Boolean).join(' · ');
  };

  const Chip = ({ e }) => (
    <button className={`ev-chip ${e.cat}${e.time && isPast(e) ? ' past' : ''}`} onClick={() => setSelected(e)}>
      {e.time && <span>{e.time}</span>}
      <span className="ev-label">{e.title}</span>
    </button>
  );

  let body;
  if (cal.isLoading) {
    body = (
      <div className="cal-panel" style={{ padding: '16px' }}>
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="skel" style={{ width: '100%', height: 70, marginBottom: 8, borderRadius: 8 }} />
        ))}
      </div>
    );
  } else if (cal.isError) {
    body = (
      <div className="cal-state error">
        <span className="icon">
          <I.i3 />
        </span>
        <p>No pudimos cargar el calendario.</p>
        <button className="retry-btn" onClick={() => cal.refetch()}>
          Reintentar
        </button>
      </div>
    );
  } else if (active.size === 0) {
    body = (
      <div className="cal-state">
        <span className="icon">
          <I.i29 />
        </span>
        <p>No encontramos eventos con los filtros seleccionados.</p>
        <button className="retry-btn" onClick={() => setActive(new Set(CATS.map(([c]) => c)))}>
          Limpiar filtros
        </button>
      </div>
    );
  } else if (view === 'month') {
    body = (
      <div className="cal-panel">
        <div className="weekday-row">
          {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((d) => (
            <div className="weekday-cell" key={d}>
              {d}
            </div>
          ))}
        </div>
        <div className="month-grid">
          {Array.from({ length: 42 }, (_, i) => {
            const cellDate = addDays(gridStart, i);
            const day = toDay(cellDate);
            const dayEvents = byDay(day);
            const holidayOnly = dayEvents.some((e) => e.cat === 'feriado') && dayEvents.every((e) => e.cat === 'feriado');
            return (
              <div key={day} className={`day-cell${cellDate.getMonth() === viewDate.getMonth() ? '' : ' other-month'}`}>
                <div className="day-num-row">
                  <span className={`day-num${day === toDay(today) ? ' today' : ''}`}>{cellDate.getDate()}</span>
                </div>
                <div className="day-events">
                  {dayEvents.slice(0, 2).map((e) => (
                    <Chip key={e.id} e={e} />
                  ))}
                  {dayEvents.length > 2 && (
                    <button className="ev-more" onClick={() => setDayList({ date: cellDate, events: dayEvents })}>
                      +{dayEvents.length - 2} eventos
                    </button>
                  )}
                  {holidayOnly && <div className="no-activities-tag">Sin actividades académicas</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  } else if (view === 'week') {
    const days = Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(viewDate), i));
    body = (
      <div className="timeline-panel">
        <div className="week-head">
          <div className="week-head-cell" />
          {days.map((d) => (
            <div className="week-head-cell" key={d.toISOString()}>
              <div className="week-head-day">{WEEKDAY_SHORT[d.getDay()]}</div>
              <div className={`week-head-num${toDay(d) === toDay(today) ? ' today' : ''}`}>{d.getDate()}</div>
            </div>
          ))}
        </div>
        <div className="week-body">
          {HOURS.map((h) => [
            <div className="hour-label" key={`h${h}`}>
              {String(h).padStart(2, '0')}:00
            </div>,
            ...days.map((d) => (
              <div className="hour-cell" key={`${h}-${toDay(d)}`}>
                {byDay(toDay(d))
                  .filter((e) => e.time && parseInt(e.time, 10) === h)
                  .map((e) => (
                    <div key={e.id} className={`week-ev ${e.cat}`} onClick={() => setSelected(e)}>
                      {e.title}
                    </div>
                  ))}
              </div>
            )),
          ])}
        </div>
      </div>
    );
  } else if (view === 'day') {
    const dayEvents = byDay(toDay(viewDate)).filter((e) => e.time);
    body = (
      <div className="timeline-panel">
        <div className="day-view-title">
          {capital(WEEKDAYS[viewDate.getDay()])} {viewDate.getDate()} de {MONTHS[viewDate.getMonth()]} de {viewDate.getFullYear()}
        </div>
        <div className="day-timeline">
          {HOURS.map((h) => (
            <div className="day-hour-row" key={h}>
              <div className="day-hour-label">{String(h).padStart(2, '0')}:00</div>
              <div className="day-hour-body">
                {dayEvents
                  .filter((e) => parseInt(e.time, 10) === h)
                  .map((e) => (
                    <div key={e.id} className={`day-ev ${e.cat}`} onClick={() => setSelected(e)}>
                      <div>
                        <p className="day-ev-title">{e.title}</p>
                        <p className="day-ev-sub">
                          {e.it.location || ''}
                          {e.end ? ` · ${e.time}–${e.end}` : ''}
                        </p>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  } else {
    const groups = {};
    [...events]
      .sort((a, b) => a.date.localeCompare(b.date) || (a.time || '').localeCompare(b.time || ''))
      .forEach((e) => (groups[e.date] = groups[e.date] || []).push(e));
    const dates = Object.keys(groups).slice(0, 10);
    body = dates.length ? (
      <div>
        {dates.map((day) => {
          const d = parseDay(day);
          const diff = Math.round((d - today) / 86400000);
          const prefix = diff === 0 ? 'Hoy' : diff === 1 ? 'Mañana' : capital(WEEKDAYS[d.getDay()]);
          return (
            <div className="agenda-day" key={day}>
              <p className="agenda-day-title">
                {prefix} — {d.getDate()} de {MONTHS[d.getMonth()]}
              </p>
              <div className="agenda-items">
                {groups[day].map((e) => {
                  const Icon = ICON[e.cat];
                  return (
                    <div key={e.id} className={`agenda-item ${e.cat}`} onClick={() => setSelected(e)}>
                      <span className="agenda-time">{e.time || '—'}</span>
                      <span className={`agenda-icon ${e.cat}`}>
                        <Icon />
                      </span>
                      <div className="agenda-main">
                        <p className="agenda-item-title">
                          {CATEGORY_LABEL[e.cat]} — {e.title}
                        </p>
                        <p className="agenda-item-sub">{e.it.location || ''}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    ) : (
      <div className="cal-state">
        <span className="icon">
          <I.i96 />
        </span>
        <p>No hay eventos para este período.</p>
      </div>
    );
  }

  const Row = ({ l, v }) => (
    <div className="modal-row">
      <span className="lbl">{l}</span>
      <span className="val">{v || '—'}</span>
    </div>
  );
  const ModalIcon = selected ? ICON[selected.cat] : null;
  const ref = selected?.it.reference || {};

  const modals = (
    <>
      <div className={`modal-backdrop${selected ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setSelected(null)}>
        {selected && (
          <div className="modal">
            <div className="modal-header">
              <div>
                <span className="modal-header-icon" style={{ background: BG(selected.cat), color: COLOR(selected.cat) }}>
                  <ModalIcon />
                </span>
                <p className="modal-eyebrow" style={{ color: COLOR(selected.cat) }}>
                  {selected.cat === 'comedor' ? 'Turno de comedor' : CATEGORY_LABEL[selected.cat]}
                </p>
                <p className="modal-title">{selected.title}</p>
              </div>
              <button className="modal-close" onClick={() => setSelected(null)}>
                <I.i95 />
              </button>
            </div>
            <div className="modal-body">
              {selected.cat === 'comedor' ? (
                <>
                  <div className="menu-section">
                    <p className="menu-label">Fecha</p>
                    <p className="menu-value">{longDate(selected.date)}</p>
                  </div>
                  <div className="menu-section">
                    <p className="menu-label">Horario</p>
                    <p className="menu-value">
                      {selected.time}–{selected.end}
                    </p>
                  </div>
                  <div className="menu-section">
                    <p className="menu-label">Estado de la reserva</p>
                    <p className="menu-value">{ref.status === 'CONFIRMED' ? 'Confirmada' : ref.status}</p>
                  </div>
                  <div className="menu-section">
                    <p className="menu-label">Importe</p>
                    <p className="menu-value">{ref.amount ? money(ref.amount) : '—'}</p>
                  </div>
                  <div className="menu-section">
                    <p className="menu-label">Ubicación</p>
                    <p className="menu-value">{selected.it.location}</p>
                  </div>
                </>
              ) : selected.cat === 'examen' ? (
                <>
                  <Row l="Fecha" v={longDate(selected.date)} />
                  <Row l="Horario" v={`${selected.time}–${selected.end}`} />
                  <Row l="Sede" v={campusName(selected.course?.campusId)} />
                  <Row l="Aula" v={courseRoom(selected.course)} />
                  <Row l="Comisión" v={selected.course?.code} />
                  <Row l="Tipo" v={selected.it.title.split(' · ')[0]} />
                </>
              ) : selected.cat === 'feriado' ? (
                <p className="modal-desc">No habrá actividades académicas.</p>
              ) : (
                <>
                  <Row
                    l="Fecha"
                    v={selected.endDay && selected.endDay !== selected.date ? `${longDate(selected.date)} al ${longDate(selected.endDay)}` : longDate(selected.date)}
                  />
                  {selected.time && <Row l="Horario" v={`${selected.time}${selected.end ? `–${selected.end}` : ''}`} />}
                  {selected.it.location && <Row l="Lugar" v={selected.it.location} />}
                  {'registered' in ref && <Row l="Inscripción" v={ref.registered ? 'Inscripto' : 'No inscripto'} />}
                  {'price' in ref && <Row l="Costo" v={ref.price ? money(ref.price) : 'Gratuito'} />}
                </>
              )}
            </div>
            <div className="modal-footer">
              {selected.cat === 'examen' && (
                <button type="button" className="btn-primary" onClick={() => navigate(`/cursos/${ref.courseId}/examenes/${ref.examId}`)}>
                  Ver examen
                </button>
              )}
            </div>
          </div>
        )}
      </div>
      <div className={`modal-backdrop${dayList ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setDayList(null)}>
        {dayList && (
          <div className="modal">
            <div className="modal-header">
              <div>
                <p className="modal-title">
                  {dayList.date.getDate()} de {MONTHS[dayList.date.getMonth()]}
                </p>
              </div>
              <button className="modal-close" onClick={() => setDayList(null)}>
                <I.i95 />
              </button>
            </div>
            <div className="modal-body">
              {dayList.events.map((e) => {
                const Icon = ICON[e.cat];
                return (
                  <div
                    key={e.id}
                    className="day-list-item"
                    onClick={() => {
                      setDayList(null);
                      setSelected(e);
                    }}
                  >
                    <span className="day-list-icon" style={{ background: BG(e.cat), color: COLOR(e.cat) }}>
                      <Icon />
                    </span>
                    <div>
                      <p style={{ margin: 0, fontSize: '13px', fontWeight: 700, color: 'var(--text-900)' }}>
                        {e.time ? `${e.time} — ` : ''}
                        {CATEGORY_LABEL[e.cat]}
                      </p>
                      <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-600)' }}>{e.title}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </>
  );

  return (
    <AppShell scope="18" active="calendario" after={modals}>
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        / Calendario académico
      </p>
      <div className="page-head-row">
        <div>
          <h1 className="page-title">Calendario académico</h1>
          <p className="page-desc">Consultá los turnos de comedor, eventos y exámenes.</p>
        </div>
      </div>
      {nextEvent && (
        <div className="next-event-card" id="nextEventCard">
          <span className="next-event-icon">
            <I.i94 />
          </span>
          <div className="next-event-main">
            <p className="next-event-eyebrow">Próximo evento</p>
            <p className="next-event-title">{nextEvent.title}</p>
            <p className="next-event-meta">{relLabel(nextEvent)}</p>
          </div>
          <button className="btn-secondary" onClick={() => setSelected(nextEvent)}>
            Ver detalle
          </button>
        </div>
      )}
      <div className="cal-toolbar">
        <div className="month-nav">
          <button className="nav-arrow" aria-label="Mes anterior" onClick={() => change(-1)}>
            <I.i33 />
          </button>
          <span className="month-label">{label}</span>
          <button className="nav-arrow" aria-label="Mes siguiente" onClick={() => change(1)}>
            <I.i34 />
          </button>
        </div>
        <div className="toolbar-right">
          <div className="view-switch">
            {[
              ['month', 'Mes'],
              ['week', 'Semana'],
              ['day', 'Día'],
              ['agenda', 'Agenda'],
            ].map(([v, l]) => (
              <button key={v} className={`view-btn${view === v ? ' active' : ''}`} onClick={() => setView(v)}>
                {l}
              </button>
            ))}
          </div>
          <button className="btn-secondary" onClick={() => setViewDate(new Date(today))}>
            Hoy
          </button>
        </div>
      </div>
      <div className="filters-row">
        <div className="filters-wrap" ref={filtersRef}>
          <button className="btn-secondary" onClick={() => setFiltersOpen((o) => !o)}>
            <I.i31 />
            Categorías
          </button>
          <div className={`filters-panel${filtersOpen ? ' open' : ''}`}>
            <p className="filters-panel-title">Categorías</p>
            {CATS.map(([cat, l]) => (
              <label className="filter-check" key={cat}>
                <input
                  type="checkbox"
                  checked={active.has(cat)}
                  onChange={(e) =>
                    setActive((s) => {
                      const n = new Set(s);
                      if (e.target.checked) n.add(cat);
                      else n.delete(cat);
                      return n;
                    })
                  }
                />
                <span className="dot" style={{ background: COLOR(cat) }} />
                {l}
              </label>
            ))}
          </div>
        </div>
      </div>
      <div className="legend">
        {CATS.map(([cat, l]) => (
          <span className="legend-item" key={cat}>
            <span className="legend-dot" style={{ background: COLOR(cat) }} />
            {l}
          </span>
        ))}
      </div>
      <div>{body}</div>
    </AppShell>
  );
}
