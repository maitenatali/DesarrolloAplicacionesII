import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  useCreateActaMutation,
  useGetCourseExamsQuery,
  useGetCoursesQuery,
  useGetExamGradesQuery,
  useGetStudentsQuery,
} from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { grade, longDate } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/16.css';

const PASSING = 4;

export default function ActaNew() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const courses = useGetCoursesQuery();
  const [courseId, setCourseId] = useState(params.get('courseId') || '');
  const [type, setType] = useState('');
  const [examId, setExamId] = useState('');
  const [notes, setNotes] = useState('');
  const [step, setStep] = useState(1);
  const [unlocked, setUnlocked] = useState(1);
  const [errors, setErrors] = useState({});
  const [detailOpen, setDetailOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [touched, setTouched] = useState(false);
  const [modal, setModal] = useState(null); // confirm | leave | {success} | {error}
  const [createActa, { isLoading: generating }] = useCreateActaMutation();
  useLockScroll(!!modal);

  const eligible = (courses.data || []).filter((c) => c.status !== 'CANCELADO');
  const course = eligible.find((c) => String(c.id) === String(courseId));
  const exams = useGetCourseExamsQuery(courseId, { skip: !courseId });
  const finals = (exams.data || []).filter((e) => e.type === 'FINAL' && e.status !== 'CANCELADO');
  const effType = type || (finals.length ? 'FINAL' : 'CURSADA');
  const effExamId = examId || (finals[0] ? String(finals[0].id) : '');
  const students = useGetStudentsQuery(courseId, { skip: !courseId });
  const examGrades = useGetExamGradesQuery({ courseId, examId: effExamId }, { skip: effType !== 'FINAL' || !effExamId });

  // Vista previa calculada en el cliente con las mismas reglas que aplica el backend al generar
  // (rules.final_result): APROBADO exige nota >= 4 Y condición REGULAR (asistencia >= 75 %).
  const preview = useMemo(() => {
    if (effType === 'FINAL') {
      const condition = new Map((students.data || []).map((s) => [s.studentId, s.attendance?.condition]));
      return (examGrades.data?.entries || []).map((e) => {
        let tipo = 'sin_registrar';
        let texto = 'Sin registrar';
        if (e.absent) {
          tipo = 'ausente';
          texto = 'Ausente';
        } else if (e.grade != null) {
          if (Number(e.grade) < PASSING) {
            tipo = 'desaprobado';
            texto = `Desaprobado · ${grade(e.grade)}`;
          } else if (condition.get(e.studentId) !== 'REGULAR') {
            tipo = 'desaprobado';
            texto = `Libre (asistencia insuficiente) · ${grade(e.grade)}`;
          } else {
            tipo = 'aprobado';
            texto = `Aprobado · ${grade(e.grade)}`;
          }
        }
        return { id: e.studentId, nombre: e.studentName, legajo: e.fileNumber, tipo, texto };
      });
    }
    return (students.data || [])
      .filter((s) => s.enrollmentStatus !== 'BAJA')
      .map((s) => {
        const cond = s.attendance?.condition;
        return {
          id: s.studentId,
          nombre: s.profile?.fullName || s.studentId,
          legajo: s.profile?.fileNumber || 'S/D',
          tipo: cond === 'REGULAR' ? 'aprobado' : cond === 'LIBRE' ? 'desaprobado' : 'sin_registrar',
          texto: cond === 'REGULAR' ? 'Regular' : cond === 'LIBRE' ? 'Libre' : 'Sin registrar',
        };
      });
  }, [effType, examGrades.data, students.data]);

  const touch = (setter) => (e) => {
    setTouched(true);
    setter(e.target.value);
  };
  const continueToPreview = () => {
    const er = { curso: !courseId, examen: effType === 'FINAL' && !effExamId };
    setErrors(er);
    if (er.curso || er.examen) return;
    setUnlocked(3);
    setConfirmed(false);
    setStep(3);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const goToStep = (n) => {
    if (n > unlocked) return;
    setStep(n);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const cancel = () => (touched ? setModal('leave') : navigate('/actas'));

  const generate = async () => {
    try {
      const acta = await createActa({
        courseId: Number(courseId),
        type: effType,
        examId: effType === 'FINAL' ? Number(effExamId) : null,
        notes: notes.trim() || null,
      }).unwrap();
      setTouched(false);
      setModal({ success: acta });
    } catch (err) {
      setModal({ error: toApiError(err).detail });
    }
  };

  const okCount = preview.filter((s) => s.tipo === 'aprobado').length;
  const badCount = preview.filter((s) => s.tipo === 'desaprobado').length;
  const pending = preview.some((s) => s.tipo === 'sin_registrar');
  const isFinal = effType === 'FINAL';
  const today = new Date().toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' });
  const field = (name) => `field${errors[name] ? ' error' : ''}`;
  const FieldError = ({ name, children }) => (
    <span className="field-error" style={{ display: errors[name] ? 'flex' : 'none' }}>
      <I.i79 />
      {children}
    </span>
  );
  const isOpen = (k) => (typeof modal === 'string' ? modal === k : !!modal?.[k]);

  const modals = (
    <>
      <div className={`modal-overlay${isOpen('confirm') ? ' open' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon info">
            <I.i19 />
          </div>
          <h3 className="modal-title">¿Generar acta?</h3>
          <p className="modal-desc">
            Se generará el acta con la información ingresada y los estudiantes seleccionados. Verificá que todos los datos sean correctos antes de
            continuar.
          </p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setModal(null)}>
              Volver
            </button>
            <button className="btn-primary" disabled={generating} onClick={generate}>
              {generating ? (
                <>
                  <span className="spinner" /> Generando acta...
                </>
              ) : (
                'Generar acta'
              )}
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-overlay${isOpen('success') ? ' open' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon success">
            <I.i85 />
          </div>
          <h3 className="modal-title">Acta generada correctamente</h3>
          <p className="modal-desc">El acta fue generada y se encuentra disponible para su revisión.</p>
          <div className="modal-meta">N.º {modal?.success?.number} · Acta generada</div>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => navigate('/actas')}>
              Volver a actas
            </button>
            <button className="btn-primary" onClick={() => navigate(`/actas/${modal.success.id}`)}>
              Ver acta
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-overlay${isOpen('error') ? ' open' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon error">
            <I.i3 />
          </div>
          <h3 className="modal-title">No pudimos generar el acta</h3>
          <p className="modal-desc">{modal?.error || 'Ocurrió un problema al generar el acta. Verificá los datos e intentá nuevamente.'}</p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setModal(null)}>
              Cerrar
            </button>
            <button className="btn-primary" onClick={() => setModal('confirm')}>
              Reintentar
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-overlay${isOpen('leave') ? ' open' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon warn">
            <I.i82 />
          </div>
          <h3 className="modal-title">¿Salir sin guardar?</h3>
          <p className="modal-desc">Tenés información ingresada que todavía no fue guardada. Si salís ahora, perderás los cambios.</p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setModal(null)}>
              Continuar editando
            </button>
            <button className="btn-primary" style={{ background: 'var(--error-600)' }} onClick={() => navigate('/actas')}>
              Salir sin guardar
            </button>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <AppShell scope="16" active="actas" after={modals}>
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        /{' '}
        <a href="/actas" onClick={(e) => (e.preventDefault(), navigate('/actas'))}>
          Actas
        </a>{' '}
        / <span className="current">Nueva acta</span>
      </p>
      <div>
        <div className="page-head">
          <div>
            <h1 className="page-title">Nueva acta</h1>
            <p className="page-desc">Completá la información necesaria para generar una nueva acta académica.</p>
          </div>
          <button className="btn-secondary" onClick={cancel}>
            <I.i76 />
            Cancelar
          </button>
        </div>
        <div className="steps">
          <button className={`step${step === 1 ? ' active' : ''}${unlocked > 1 ? ' completed reachable' : ''}`} onClick={() => goToStep(1)}>
            <span className="step-circle">1</span>
            <span className="step-label">Información general</span>
          </button>
          <div className={`step-line${unlocked > 1 ? ' done' : ''}`} />
          <button className={`step${step === 3 ? ' active' : ''}${unlocked > 1 ? ' reachable' : ''}`} onClick={() => goToStep(3)}>
            <span className="step-circle">2</span>
            <span className="step-label">Vista previa</span>
          </button>
        </div>
        <div className={`section-block${step === 1 ? ' visible' : ''}`}>
          <div className="form-card">
            <div className="form-card-head">
              <h2 className="form-card-title">Información del acta</h2>
            </div>
            <div className="form-card-body">
              <div className="form-grid">
                <div className={field('curso')}>
                  <label>
                    Curso<span className="req">*</span>
                  </label>
                  <select
                    value={courseId}
                    onChange={(e) => {
                      touch(setCourseId)(e);
                      setType('');
                      setExamId('');
                      setErrors({});
                    }}
                  >
                    <option value="">{courses.isLoading ? 'Cargando cursos…' : 'Seleccionar curso'}</option>
                    {eligible.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.subject.name}
                      </option>
                    ))}
                  </select>
                  <FieldError name="curso">Seleccioná un curso.</FieldError>
                </div>
                <div className="field">
                  <label>
                    Comisión<span className="req">*</span>
                  </label>
                  <select disabled value={course?.code || ''}>
                    <option value={course?.code || ''}>{course?.code || 'Se completa automáticamente'}</option>
                  </select>
                </div>
                <div className="field">
                  <label>
                    Período académico<span className="req">*</span>
                  </label>
                  <select disabled value={course?.period.label || ''}>
                    <option value={course?.period.label || ''}>{course?.period.label || 'Se completa automáticamente'}</option>
                  </select>
                </div>
                <div className="field">
                  <label>Número de acta</label>
                  <div className="readonly-box">
                    <I.i79 />
                    Se generará automáticamente
                    <span className="code">N.º {new Date().getFullYear()}-XXX</span>
                  </div>
                </div>
                <div className="field">
                  <label>
                    Tipo de acta<span className="req">*</span>
                  </label>
                  <select value={effType} disabled={!courseId} onChange={touch(setType)}>
                    <option value="FINAL">Final (examen final)</option>
                    <option value="CURSADA">Cursada (regularidad)</option>
                  </select>
                </div>
                {isFinal && (
                  <div className={field('examen')}>
                    <label>
                      Examen final<span className="req">*</span>
                    </label>
                    <select value={effExamId} disabled={!courseId} onChange={touch(setExamId)}>
                      <option value="">{finals.length ? 'Seleccionar examen' : 'El curso no tiene exámenes finales'}</option>
                      {finals.map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.name} · {longDate(e.date)}
                        </option>
                      ))}
                    </select>
                    <FieldError name="examen">Seleccioná el examen final del acta.</FieldError>
                  </div>
                )}
                <div className="field span-2">
                  <label>Observaciones</label>
                  <textarea
                    placeholder="Ingresá observaciones adicionales sobre el acta..."
                    value={notes}
                    maxLength={1000}
                    onChange={touch(setNotes)}
                  />
                </div>
              </div>
            </div>
            <div className="form-card-foot">
              <button className="btn-primary" onClick={continueToPreview}>
                Continuar
                <I.i80 />
              </button>
            </div>
          </div>
        </div>
        <div className={`section-block${step === 3 ? ' visible' : ''}`}>
          <div className="form-card">
            <div className="form-card-head">
              <h2 className="form-card-title">Revisá la información</h2>
            </div>
            <div className="form-card-body">
              <div className="review-grid">
                <div className="review-row">
                  <span className="r-label">Curso</span>
                  <span className="r-value">{course?.subject.name || '—'}</span>
                </div>
                <div className="review-row">
                  <span className="r-label">Comisión</span>
                  <span className="r-value">{course?.code || '—'}</span>
                </div>
                <div className="review-row">
                  <span className="r-label">Período</span>
                  <span className="r-value">{course?.period.label || '—'}</span>
                </div>
                <div className="review-row">
                  <span className="r-label">Fecha</span>
                  <span className="r-value">{today}</span>
                </div>
              </div>
              <p className="form-card-title" style={{ marginBottom: '10px' }}>
                Estudiantes
              </p>
              <p className="students-count-line" style={{ marginBottom: '12px' }}>
                {preview.length} estudiantes incluidos
              </p>
              <div className="review-stats">
                <div className="stat-chip ok">
                  <div className="stat-value">{okCount}</div>
                  <div className="stat-label">{isFinal ? 'Aprobados' : 'Regulares'}</div>
                </div>
                <div className="stat-chip bad">
                  <div className="stat-value">{badCount}</div>
                  <div className="stat-label">{isFinal ? 'Desaprobados' : 'Libres'}</div>
                </div>
              </div>
              {pending && (
                <div className="alert warn" style={{ display: 'flex' }}>
                  <span className="alert-icon">
                    <I.i82 />
                  </span>
                  <div>
                    <p className="alert-title">Hay información pendiente</p>
                    <p className="alert-desc">
                      Algunos estudiantes todavía no tienen un resultado registrado. Revisá las calificaciones antes de generar el acta.
                    </p>
                    <button className="btn-secondary" onClick={() => navigate(`/cursos/${courseId}/calificaciones`)}>
                      Revisar calificaciones
                    </button>
                  </div>
                </div>
              )}
              <button className="toggle-link" onClick={() => setDetailOpen((o) => !o)}>
                <I.i84 />
                {detailOpen ? 'Ocultar estudiantes seleccionados' : 'Ver estudiantes seleccionados'}
              </button>
              <div className="review-students-detail" style={{ display: detailOpen ? 'block' : 'none' }}>
                {preview.map((s) => (
                  <div className="mini-row" key={s.id}>
                    <span>
                      <b>{s.nombre}</b> · Legajo {s.legajo}
                    </span>
                    <span>{s.texto}</span>
                  </div>
                ))}
              </div>
              <div className="confirm-row">
                <input type="checkbox" id="confirmChk" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
                <label htmlFor="confirmChk">Confirmo que revisé la información y que los datos ingresados son correctos.</label>
              </div>
            </div>
            <div className="form-card-foot" style={{ justifyContent: 'space-between' }}>
              <button className="btn-secondary" onClick={() => goToStep(1)}>
                <I.i83 />
                Volver
              </button>
            </div>
          </div>
        </div>
        <div className="action-bar">
          <div />
          <div className="action-bar-right">
            <button className="btn-primary" disabled={step !== 3 || !confirmed} onClick={() => setModal('confirm')}>
              Generar acta
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
