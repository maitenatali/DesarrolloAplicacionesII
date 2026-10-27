import { Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { toApiError } from '../api/baseQuery';
import * as I from './icons.generated';

const TABS = [
  { key: 'info', label: 'Información general', icon: I.i36, path: '' },
  { key: 'estudiantes', label: 'Estudiantes', icon: I.i37, path: '/estudiantes' },
  { key: 'asistencia', label: 'Asistencia', icon: I.i38, path: '/asistencia' },
  { key: 'calificaciones', label: 'Calificaciones', icon: I.i39, path: '/calificaciones' },
  { key: 'examenes', label: 'Exámenes', icon: I.i40, path: '/examenes' },
];

export function CourseTabs({ courseId, active }) {
  const navigate = useNavigate();
  return (
    <div className="tabs" aria-label="Navegación del curso">
      {TABS.map((t) => (
        <button
          key={t.key}
          className={`tab-item${active === t.key ? ' active' : ''}`}
          onClick={active === t.key ? undefined : () => navigate(`/cursos/${courseId}${t.path}`)}
        >
          <t.icon />
          {t.label}
        </button>
      ))}
    </div>
  );
}

/** Breadcrumb "Inicio / Mis cursos / <curso> / ...". `trail`: [{label, to?}], el último sin `to` es el actual. */
export function Breadcrumb({ trail, id }) {
  const navigate = useNavigate();
  const link = (to) => (e) => {
    e.preventDefault();
    navigate(to);
  };
  return (
    <p className="breadcrumb" id={id}>
      {trail.map((t, i) => (
        <Fragment key={i}>
          {i > 0 && ' / '}
          {t.to ? (
            <a href={t.to} onClick={link(t.to)}>
              {t.label}
            </a>
          ) : (
            <span className="current">{t.label}</span>
          )}
        </Fragment>
      ))}
    </p>
  );
}

export const courseTrail = (course, courseId, ...rest) => [
  { label: 'Inicio', to: '/' },
  { label: 'Mis cursos', to: '/cursos' },
  rest.length ? { label: course?.name || 'Curso', to: `/cursos/${courseId}` } : { label: course?.name || 'Curso' },
  ...rest,
];

export function CourseHero({ course, children, badge }) {
  return (
    <div className="course-hero">
      <div className="course-hero-main">
        <div className="course-hero-title-row">
          <h1 className="course-hero-title">{course.name}</h1>
          {badge}
        </div>
        <p className="course-hero-sub">
          Comisión {course.com} · {course.period}
        </p>
      </div>
      {children}
    </div>
  );
}

/** Estados de carga / error / no encontrado de una pantalla de curso (mismo markup que los mockups). */
export function CourseLoadState({ query, notFoundText = 'Seleccioná un curso desde Mis cursos para consultar su detalle.' }) {
  const navigate = useNavigate();
  if (query.isLoading) {
    return (
      <>
        <div className="course-hero" style={{ alignItems: 'center' }}>
          <div style={{ width: '100%' }}>
            <div className="skel" style={{ width: 280, height: 24, marginBottom: 10 }} />
            <div className="skel" style={{ width: 220, height: 14 }} />
          </div>
        </div>
        <div className="two-col">
          <div className="panel">
            <div className="panel-body">
              {Array.from({ length: 5 }, (_, i) => (
                <div key={i} className="skel" style={{ width: '100%', height: 16, marginBottom: 14 }} />
              ))}
            </div>
          </div>
          <div className="panel">
            <div className="panel-body">
              <div className="skel" style={{ width: '100%', height: 60 }} />
            </div>
          </div>
        </div>
      </>
    );
  }
  const err = toApiError(query.error);
  const notFound = err?.status === 404 || err?.status === 403;
  return (
    <div className="page-error-banner">
      <span className="state-icon">{notFound ? <I.i41 /> : <I.i3 />}</span>
      <p className="state-title">{notFound ? 'Curso no encontrado' : 'No pudimos cargar la información del curso'}</p>
      <p className="state-desc">{notFound ? notFoundText : err?.detail || 'Ocurrió un problema al obtener los datos. Intentá nuevamente.'}</p>
      {notFound ? (
        <button className="btn-primary" style={{ marginTop: 4 }} onClick={() => navigate('/cursos')}>
          Volver a Mis cursos
        </button>
      ) : (
        <button className="btn-primary" style={{ marginTop: 4 }} onClick={() => query.refetch()}>
          Reintentar
        </button>
      )}
    </div>
  );
}
