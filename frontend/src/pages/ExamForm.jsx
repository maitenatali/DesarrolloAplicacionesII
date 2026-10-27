import { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate, useParams } from 'react-router-dom';
import { useCreateExamMutation, useGetCourseExamsQuery, useGetExamQuery, useGetExamTypesQuery, useUpdateExamMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseLoadState, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import { flash } from '../features/ui/uiSlice';
import { useCourse } from '../lib/courses';
import { examTypeLabel } from '../lib/domain';
import { longDate } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/11.css';

const DURATIONS = [30, 60, 90, 120, 180];

function addMinutes(hhmm, minutes) {
  if (!hhmm) return '';
  const [h, m] = hhmm.split(':').map(Number);
  const t = h * 60 + m + Number(minutes);
  return `${String(Math.floor(t / 60) % 24).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
}

export default function ExamForm() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { examId } = useParams();
  const editing = !!examId;
  const q = useCourse();
  const { courseId, course } = q;
  const types = useGetExamTypesQuery();
  const courseExams = useGetCourseExamsQuery(courseId);
  const exam = useGetExamQuery({ courseId, examId }, { skip: !editing });
  const [create, createState] = useCreateExamMutation();
  const [update, updateState] = useUpdateExamMutation();
  const saving = createState.isLoading || updateState.isLoading;

  const [form, setForm] = useState({ type: '', description: '', date: '', startTime: '', duration: '120', modality: 'PRESENCIAL' });
  const [errors, setErrors] = useState({});
  const [modal, setModal] = useState(null); // 'discard' | { error }
  const [touched, setTouched] = useState(false);
  useLockScroll(!!modal);

  const courseStart = course?.raw.schedule?.[0]?.startTime || '';
  useEffect(() => {
    if (editing && exam.data) {
      setForm({
        type: exam.data.type,
        description: exam.data.description || '',
        date: exam.data.date,
        startTime: exam.data.startTime,
        duration: String(exam.data.durationMinutes),
        modality: exam.data.modality,
      });
    } else if (!editing && courseStart) {
      setForm((f) => (f.startTime ? f : { ...f, startTime: courseStart }));
    }
  }, [editing, exam.data, courseStart]);

  if (!course) {
    return (
      <AppShell scope="11" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId, { label: 'Exámenes', to: `/cursos/${courseId}/examenes` }, { label: 'Nuevo examen' })} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const set = (field) => (e) => {
    setTouched(true);
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setErrors((er) => ({ ...er, [field]: false, duplicate: field === 'type' ? false : er.duplicate }));
  };
  const duplicate =
    !!form.type &&
    (courseExams.data || []).some((e) => e.type === form.type && e.status !== 'CANCELADO' && String(e.id) !== String(examId || ''));
  const end = form.type && form.duration ? addMinutes(form.startTime, form.duration) : '';
  const horario = form.startTime && end ? `${form.startTime} a ${end}` : '—';
  const virtual = form.modality === 'VIRTUAL';
  const typeName = form.type ? examTypeLabel(form.type, (types.data || []).find((t) => t.type === form.type)?.name) : 'Seleccioná un tipo';
  const backToList = () => navigate(`/cursos/${courseId}/examenes`);

  const guardar = async () => {
    const er = { type: !form.type, date: !form.date, startTime: !form.startTime, duration: !form.duration, modality: !form.modality };
    setErrors({ ...er, duplicate });
    if (Object.values(er).some(Boolean) || duplicate) return;
    const body = {
      type: form.type,
      name: typeName,
      description: form.description.trim() || null,
      date: form.date,
      startTime: form.startTime,
      durationMinutes: Number(form.duration),
      modality: form.modality,
    };
    try {
      if (editing) {
        await update({ courseId, examId, body }).unwrap();
        dispatch(flash('Examen actualizado correctamente.'));
        navigate(`/cursos/${courseId}/examenes/${examId}`);
      } else {
        const created = await create({ courseId, body }).unwrap();
        dispatch(flash('Examen creado correctamente.'));
        navigate(`/cursos/${courseId}/examenes/${created.id}`);
      }
    } catch (err) {
      const apiErr = toApiError(err);
      if (apiErr.code === 'EXAM_TYPE_ALREADY_EXISTS') setErrors((x) => ({ ...x, duplicate: true }));
      else setModal({ error: apiErr.detail });
    }
  };

  const cancel = () => (touched ? setModal('discard') : editing ? navigate(`/cursos/${courseId}/examenes/${examId}`) : backToList());
  const fieldCls = (name, extra = '') => `field${extra}${errors[name] ? ' error' : ''}`;
  const ErrorMsg = ({ name, children }) => (
    <span className="error-msg" style={{ display: errors[name] ? 'flex' : 'none' }}>
      <I.i57 />
      {children}
    </span>
  );
  const title = editing ? 'Editar examen' : 'Nuevo examen';

  const modals = (
    <>
      <div className={`modal-overlay${modal === 'discard' ? ' show' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon warn">
            <I.i65 />
          </div>
          <h3>¿Descartar cambios?</h3>
          <p>Los cambios realizados todavía no fueron guardados. ¿Querés descartarlos?</p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setModal(null)}>
              Continuar editando
            </button>
            <button className="btn-primary danger" onClick={backToList}>
              Descartar cambios
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-overlay${modal?.error ? ' show' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon error">
            <I.i57 />
          </div>
          <h3>No pudimos guardar el examen</h3>
          <p>{modal?.error || 'Ocurrió un problema al guardar la información. Intentá nuevamente.'}</p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setModal(null)}>
              Cerrar
            </button>
            <button
              className="btn-primary"
              onClick={() => {
                setModal(null);
                guardar();
              }}
            >
              Reintentar
            </button>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <AppShell scope="11" active="cursos" after={modals}>
      <Breadcrumb
        trail={courseTrail(course, courseId, { label: 'Exámenes', to: `/cursos/${courseId}/examenes` }, { label: title })}
      />
      <div className="page-head">
        <div>
          <div className="page-head-title-row">
            <h1 className="page-title">{title}</h1>
          </div>
          <p className="page-sub">
            {editing ? 'Modificá la información del examen.' : 'Completá la información para programar un nuevo examen.'}
          </p>
        </div>
      </div>
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          guardar();
        }}
      >
        <div className="form-layout">
          <div className="form-main">
            <div className="card">
              <div className="card-head">
                <h2>Información general</h2>
              </div>
              <div className="card-body">
                <div className="field-grid">
                  <div className={fieldCls('type', ' full')}>
                    <label htmlFor="tipo">
                      Tipo de examen<span className="req">*</span>
                    </label>
                    <select id="tipo" value={form.type} onChange={set('type')}>
                      <option value="">Seleccioná un tipo</option>
                      {(types.data || []).map((t) => (
                        <option key={t.type} value={t.type}>
                          {examTypeLabel(t.type, t.name)}
                        </option>
                      ))}
                    </select>
                    <span
                      className="duplicate-msg"
                      style={{ display: duplicate || errors.duplicate ? 'block' : 'none', color: 'var(--error-600)', fontSize: '12px', marginTop: '6px' }}
                    >
                      Ya existe un examen de este tipo para este curso.
                    </span>
                    <ErrorMsg name="type">Seleccioná un tipo de examen.</ErrorMsg>
                  </div>
                  <div className="field full">
                    <label htmlFor="descripcion">Descripción</label>
                    <textarea
                      id="descripcion"
                      placeholder="Agregá una descripción o información adicional sobre el examen..."
                      value={form.description}
                      maxLength={1000}
                      onChange={set('description')}
                    />
                    <span className="hint">Campo opcional.</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-head">
                <h2>Fecha y horario</h2>
              </div>
              <div className="card-body">
                <div className="field-grid">
                  <div className={fieldCls('date')}>
                    <label htmlFor="fecha">
                      Fecha del examen<span className="req">*</span>
                    </label>
                    <input type="date" id="fecha" value={form.date} onChange={set('date')} />
                    <ErrorMsg name="date">Seleccioná una fecha.</ErrorMsg>
                  </div>
                  <div className={fieldCls('startTime')}>
                    <label htmlFor="hora">
                      Hora de inicio<span className="req">*</span>
                    </label>
                    <input type="time" id="hora" value={form.startTime} onChange={set('startTime')} readOnly={!!courseStart} />
                    <ErrorMsg name="startTime">No se pudo determinar el horario del curso.</ErrorMsg>
                  </div>
                  <div className={fieldCls('duration')}>
                    <label htmlFor="duracion">
                      Duración<span className="req">*</span>
                    </label>
                    <select id="duracion" value={form.duration} onChange={set('duration')}>
                      {DURATIONS.map((d) => (
                        <option key={d} value={String(d)}>
                          {d} minutos
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-head">
                <h2>Modalidad</h2>
              </div>
              <div className="card-body">
                <div className={fieldCls('modality')}>
                  <label htmlFor="modalidad">
                    Modalidad<span className="req">*</span>
                  </label>
                  <select id="modalidad" value={form.modality} onChange={set('modality')}>
                    <option value="PRESENCIAL">Presencial</option>
                    <option value="VIRTUAL">Virtual</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
          <div className="form-side">
            <div className="card">
              <div className="card-head">
                <h2>Curso</h2>
              </div>
              <div className="course-ctx-body">
                <div className="course-ctx-row">
                  <span className="course-ctx-label">Curso</span>
                  <span className="course-ctx-value">{course.name}</span>
                </div>
                <div className="course-ctx-row">
                  <span className="course-ctx-label">Comisión</span>
                  <span className="course-ctx-value">{course.com}</span>
                </div>
                <div className="course-ctx-row">
                  <span className="course-ctx-label">Período</span>
                  <span className="course-ctx-value">{course.period}</span>
                </div>
                <div className="course-ctx-note">
                  <I.i58 />
                  Solo lectura. Para crear un examen en otro curso, volvé al listado de cursos.
                </div>
              </div>
            </div>
            <div className="card">
              <h3 className="summary-title">Resumen</h3>
              <div className="summary-list">
                <div className="summary-line">
                  <I.i59 /> {typeName}
                </div>
                <div className="summary-line">
                  <I.i60 /> {form.date ? longDate(form.date) : '—'}
                </div>
                <div className="summary-line">
                  <I.i61 /> {horario}
                </div>
                {!virtual && (
                  <>
                    <div className="summary-line">
                      <I.i62 /> Aula {course.room}
                    </div>
                    <div className="summary-line">
                      <I.i63 /> {course.sede}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="form-actions">
          <button type="button" className="btn-secondary" disabled={saving} onClick={cancel}>
            Cancelar
          </button>
          <button type="submit" className="btn-primary" disabled={saving || (editing && !exam.data)}>
            <I.i64 />
            <span>{saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear examen'}</span>
          </button>
        </div>
      </form>
    </AppShell>
  );
}
