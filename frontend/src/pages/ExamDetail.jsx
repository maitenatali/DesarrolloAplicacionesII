import { useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate, useParams } from 'react-router-dom';
import { useCancelExamMutation, useGetExamGradesQuery, useGetExamQuery } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseLoadState, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import { flash } from '../features/ui/uiSlice';
import { useCourse } from '../lib/courses';
import { EXAM_STATUS_LABEL, examStatus, MODALITY } from '../lib/domain';
import { grade, longDate, parseDay } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import useToast from '../lib/useToast';
import '../styles/pages/12.css';

function daysUntil(day) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.round((parseDay(day) - today) / 86400000));
}

export default function ExamDetail() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { examId } = useParams();
  const q = useCourse();
  const { courseId, course } = q;
  const examQ = useGetExamQuery({ courseId, examId });
  const grades = useGetExamGradesQuery({ courseId, examId });
  const [cancelExam, { isLoading: cancelling }] = useCancelExamMutation();
  const [modalOpen, setModalOpen] = useState(false);
  const [toast, showToast] = useToast(2800);
  useLockScroll(modalOpen);

  const exam = examQ.data;
  const trail = courseTrail(course, courseId, { label: 'Exámenes', to: `/cursos/${courseId}/examenes` }, { label: exam?.name || 'Examen' });

  if (!course || !exam) {
    const failing = !course ? q : examQ;
    return (
      <AppShell scope="12" active="cursos">
        <Breadcrumb trail={trail} />
        <CourseLoadState
          query={failing}
          notFoundText={!course ? undefined : 'El examen no existe o fue eliminado. Volvé al listado de exámenes del curso.'}
        />
      </AppShell>
    );
  }

  const status = examStatus(exam);
  const courseActive = course.raw.status !== 'FINALIZADO' && course.raw.status !== 'CANCELADO';
  const physical = exam.modality === 'PRESENCIAL';
  const d = daysUntil(exam.date);
  const s = grades.data?.summary;
  const loaded = s ? s.graded + s.absent : 0;
  const pct = s && s.enrolled ? Math.round((loaded / s.enrolled) * 100) : 0;

  const confirmCancel = async () => {
    try {
      await cancelExam({ courseId, examId }).unwrap();
      setModalOpen(false);
      dispatch(flash('Examen cancelado correctamente.'));
      navigate(`/cursos/${courseId}/examenes`);
    } catch (err) {
      setModalOpen(false);
      showToast(toApiError(err).detail, 'error');
    }
  };

  const goGrades = () => navigate(`/cursos/${courseId}/calificaciones`);

  return (
    <AppShell
      scope="12"
      active="cursos"
      after={
        <>
          <div className={`modal-overlay${modalOpen ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setModalOpen(false)}>
            <div className="modal-box">
              <div className="modal-icon">
                <I.i3 />
              </div>
              <h3 className="modal-title">¿Cancelar examen?</h3>
              <p className="modal-text">
                El examen será marcado como cancelado y dejará de aparecer como evaluación programada. ¿Querés continuar?
              </p>
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => setModalOpen(false)}>
                  Volver
                </button>
                <button className="btn-destructive" disabled={cancelling} onClick={confirmCancel}>
                  {cancelling ? 'Cancelando…' : 'Cancelar examen'}
                </button>
              </div>
            </div>
          </div>
          <div className={`toast${toast.show ? ' show' : ''}${toast.type === 'error' ? ' error' : ''}`}>
            <I.i73 />
            <span>{toast.message}</span>
          </div>
        </>
      }
    >
      <Breadcrumb trail={trail} />
      <div>
        <div className="cancel-alert" style={{ display: status === 'cancelado' ? 'flex' : 'none' }}>
          <I.i3 />
          <p>
            <strong>Examen cancelado</strong> Este examen fue cancelado y ya no se encuentra programado. La información se conserva a modo de
            referencia.
          </p>
        </div>
        <div className="exam-hero">
          <div className="exam-hero-top">
            <div>
              <div className="exam-hero-title-row">
                <h1 className="exam-hero-title">{exam.name}</h1>
                <span className={`badge ${status}`}>{EXAM_STATUS_LABEL[status]}</span>
              </div>
              <p className="exam-hero-sub">
                {course.name} · Comisión {course.com}
              </p>
              <div className="exam-hero-datetime">
                <I.i20 />
                <span>
                  {longDate(exam.date)} · {exam.startTime}–{exam.endTime}
                </span>
              </div>
              {status === 'proximo' && (
                <span className="upcoming-chip" style={{ display: 'inline-flex' }}>
                  <I.i67 />
                  <span>Próximo examen · Faltan {d === 1 ? '1 día' : `${d} días`}</span>
                </span>
              )}
            </div>
          </div>
          <div className="exam-actions">
            <button className="btn-secondary" onClick={() => navigate(`/cursos/${courseId}/examenes`)}>
              <I.i68 />
              Volver a exámenes
            </button>
            {courseActive && status === 'proximo' && (
              <button className="btn-secondary" onClick={() => navigate(`/cursos/${courseId}/examenes/${examId}/editar`)}>
                <I.i69 />
                Editar examen
              </button>
            )}
            {status !== 'cancelado' && (
              <button className="btn-primary" onClick={goGrades}>
                <I.i39 />
                Gestionar calificaciones
              </button>
            )}
            {courseActive && status !== 'cancelado' && (
              <button className="btn-destructive" onClick={() => setModalOpen(true)}>
                <I.i70 />
                Cancelar examen
              </button>
            )}
          </div>
        </div>
      </div>
      <div className="tabs"></div>
      <div className="detail-grid">
        <div className="col-main">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Información del examen</h2>
            </div>
            <div className="panel-body">
              <div className="info-grid exam-basic-info">
                <div className="info-field">
                  <p className="info-label">Nombre</p>
                  <p className="info-value">{exam.name}</p>
                </div>
                <div className="info-field">
                  <p className="info-label">Estado</p>
                  <p className="info-value">{EXAM_STATUS_LABEL[status]}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Fecha y horario</h2>
            </div>
            <div className="panel-body">
              <div className="datetime-highlight">
                <div className="dt-item date">
                  <I.i20 />
                  <div>
                    <p className="info-label">Fecha</p>
                    <p className="info-value">{longDate(exam.date)}</p>
                  </div>
                </div>
                <div className="dt-item">
                  <I.i67 />
                  <div>
                    <p className="info-label">Inicio</p>
                    <p className="info-value">{exam.startTime}</p>
                  </div>
                </div>
                <div className="dt-item">
                  <I.i67 />
                  <div>
                    <p className="info-label">Finalización</p>
                    <p className="info-value">{exam.endTime}</p>
                  </div>
                </div>
                <div className="dt-item">
                  <I.i71 />
                  <div>
                    <p className="info-label">Duración</p>
                    <p className="info-value">{exam.durationMinutes} minutos</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Ubicación y modalidad</h2>
            </div>
            <div className="panel-body">
              <div className="loc-grid">
                <div className="info-field">
                  <p className="info-label">Modalidad</p>
                  <p className="info-value">{MODALITY[exam.modality] || exam.modality}</p>
                </div>
                {physical && (
                  <>
                    <div className="info-field">
                      <p className="info-label">Aula</p>
                      <p className="info-value">{course.room}</p>
                    </div>
                    <div className="info-field">
                      <p className="info-label">Sede</p>
                      <p className="info-value">Sede {course.sede}</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Descripción</h2>
            </div>
            <div className="panel-body">
              <p className="description-text">{exam.description || 'Sin descripción.'}</p>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Calificaciones</h2>
            </div>
            <div className="panel-body">
              <div className="grades-summary">
                <div className="grade-stat">
                  <div className="gs-value">{s ? `${loaded} / ${s.enrolled}` : '—'}</div>
                  <div className="gs-label">Cargadas</div>
                </div>
                <div className="grade-stat">
                  <div className="gs-value">{s ? s.pending : '—'}</div>
                  <div className="gs-label">Pendientes</div>
                </div>
                <div className="grade-stat">
                  <div className="gs-value">{s ? grade(s.average) : '—'}</div>
                  <div className="gs-label">Promedio</div>
                </div>
                <div className="grade-stat aprobados">
                  <div className="gs-value">{s ? s.passed : '—'}</div>
                  <div className="gs-label">Aprobados</div>
                </div>
              </div>
              <div className="progress-row">
                <span>{s ? `${loaded} de ${s.enrolled} calificaciones cargadas` : 'Cargando calificaciones…'}</span>
                <span className="pct">{pct}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${pct}%` }} />
              </div>
              {status !== 'cancelado' && (
                <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={goGrades}>
                  <I.i39 />
                  Gestionar calificaciones
                </button>
              )}
            </div>
          </div>
        </div>
        <div className="col-side">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Curso</h2>
            </div>
            <div className="panel-body">
              <p className="course-card-title">{course.name}</p>
              <p className="course-card-sub">Comisión {course.com}</p>
              <p className="course-card-sub">{course.period}</p>
              <button className="btn-ghost" style={{ marginTop: '12px' }} onClick={() => navigate(`/cursos/${courseId}`)}>
                Ver curso
                <I.i72 />
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
