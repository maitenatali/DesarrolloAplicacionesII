import { Fragment, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetCoursesQuery } from '../api/api';
import AppShell, { useCurrentTeacher } from '../components/AppShell';
import * as I from '../components/icons.generated';
import { isActiveCourse } from '../lib/domain';
import useLockScroll from '../lib/useBodyClass';
import useToast from '../lib/useToast';
import '../styles/pages/27.css';

// TODO(Backoffice): no hay endpoint para editar datos de contacto ni foto del docente. Mientras tanto se
// guardan en el navegador (localStorage), por usuario. Los datos personales vienen de GET /me (Backoffice).
const storeKey = (id) => `uadenet.profile.${id}`;
function loadLocal(id) {
  try {
    return JSON.parse(localStorage.getItem(storeKey(id)) || '{}');
  } catch {
    return {};
  }
}
function saveLocal(id, data) {
  try {
    localStorage.setItem(storeKey(id), JSON.stringify(data));
    return true;
  } catch {
    return false;
  }
}

const validEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
const validPhone = (v) => v.trim().length >= 8;
const NOT_AVAILABLE = '—';

export default function Profile() {
  const navigate = useNavigate();
  const { me, fullName, initials } = useCurrentTeacher();
  const courses = useGetCoursesQuery();
  const [local, setLocal] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ emailPersonal: '', phone: '' });
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState(null);
  const [modal, setModal] = useState(null); // photo | discard
  const [photoDraft, setPhotoDraft] = useState(null);
  const [photoError, setPhotoError] = useState(null);
  const [toast, showToast] = useToast();
  useLockScroll(!!modal);

  const data = local ?? (me ? loadLocal(me.userId) : {});
  const active = (courses.data || []).filter(isActiveCourse);

  const persist = (next) => {
    const ok = saveLocal(me.userId, next);
    if (ok) setLocal(next);
    return ok;
  };
  const enterEdit = () => {
    setDraft({ emailPersonal: data.emailPersonal || '', phone: data.phone || '' });
    setErrors({});
    setBanner(null);
    setEditing(true);
  };
  const dirty = editing && (draft.emailPersonal !== (data.emailPersonal || '') || draft.phone !== (data.phone || ''));
  const cancelEdit = () => (dirty ? setModal('discard') : setEditing(false));
  const save = () => {
    const er = { emailPersonal: !validEmail(draft.emailPersonal), phone: !validPhone(draft.phone) };
    setErrors(er);
    setBanner(null);
    if (er.emailPersonal || er.phone) return;
    if (persist({ ...data, emailPersonal: draft.emailPersonal.trim(), phone: draft.phone.trim() })) {
      setBanner('success');
      showToast('Cambios guardados correctamente.');
      setEditing(false);
    } else setBanner('error');
  };
  const pickPhoto = (e) => {
    const file = e.target.files?.[0];
    setPhotoError(null);
    if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) return setPhotoError('Formato no permitido. Usá JPG o PNG.');
    if (file.size > 5 * 1024 * 1024) return setPhotoError('La imagen supera los 5 MB.');
    const reader = new FileReader();
    reader.onload = () => setPhotoDraft(reader.result);
    reader.readAsDataURL(file);
  };
  const avatarStyle = (src) =>
    src ? { backgroundImage: `url(${src})`, backgroundSize: 'cover', backgroundPosition: 'center', color: 'transparent' } : undefined;

  const Field = ({ label, value, readonly = true }) => (
    <div className={`info-field${readonly ? ' readonly' : ''}`}>
      <p className="info-label">{label}</p>
      <p className="info-value">{value || NOT_AVAILABLE}</p>
    </div>
  );

  const modals = (
    <>
      <div className={`modal-overlay${modal === 'photo' ? ' open' : ''}`}>
        <div className="modal-box">
          <h3 className="modal-title">Cambiar foto de perfil</h3>
          <p className="modal-text">Actualizá tu foto de perfil. Se reflejará en tu perfil.</p>
          <div className="photo-preview-row">
            <span className="photo-preview" style={avatarStyle(photoDraft ?? data.photo)}>
              {initials}
            </span>
            <div className="file-drop">
              <label className="btn-secondary" style={{ cursor: 'pointer' }}>
                <I.i117 />
                Seleccionar archivo
                <input type="file" accept="image/jpeg,image/png" hidden onChange={pickPhoto} />
              </label>
              <p>{photoError || 'Formatos: JPG, PNG · Tamaño máximo: 5 MB'}</p>
            </div>
          </div>
          <div className="modal-actions spread">
            <button
              className="btn-destructive"
              onClick={() => {
                persist({ ...data, photo: null });
                setPhotoDraft(null);
                setModal(null);
              }}
            >
              Eliminar foto
            </button>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                className="btn-secondary"
                onClick={() => {
                  setPhotoDraft(null);
                  setModal(null);
                }}
              >
                Cancelar
              </button>
              <button
                className="btn-primary"
                disabled={!photoDraft}
                onClick={() => {
                  if (persist({ ...data, photo: photoDraft })) showToast('Foto actualizada correctamente.');
                  else showToast('No pudimos guardar la foto (espacio insuficiente).');
                  setPhotoDraft(null);
                  setModal(null);
                }}
              >
                Guardar foto
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className={`modal-overlay${modal === 'discard' ? ' open' : ''}`}>
        <div className="modal-box">
          <div className="modal-icon warn">
            <I.i3 />
          </div>
          <h3 className="modal-title">¿Descartar cambios?</h3>
          <p className="modal-text">Los cambios realizados no se guardarán.</p>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setModal(null)}>
              Seguir editando
            </button>
            <button
              className="btn-destructive"
              onClick={() => {
                setModal(null);
                setEditing(false);
              }}
            >
              Descartar cambios
            </button>
          </div>
        </div>
      </div>
      <div className={`toast${toast.show ? ' show' : ''}`}>
        <I.i73 />
        <span>{toast.message}</span>
      </div>
    </>
  );

  return (
    <AppShell scope="27" active="perfil" after={modals}>
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        / <span className="current">Mi perfil</span>
      </p>
      <div className="page-head">
        <h1 className="page-title">Mi perfil</h1>
        <p className="page-sub">Consultá y administrá tus datos personales e institucionales.</p>
      </div>
      <div className="profile-grid">
        <div className="col-identity">
          <div className="panel identity-card">
            <div className="panel-body">
              <span className="avatar-lg" style={avatarStyle(data.photo)}>
                {initials}
              </span>
              <p className="identity-name">{fullName}</p>
              <p className="identity-role">Docente</p>
              <span className="identity-id">Legajo docente: {me?.fileNumber || NOT_AVAILABLE}</span>
              <p className="identity-stat">
                <strong>{active.length}</strong> cursos activos
              </p>
              <button className="btn-secondary" onClick={() => setModal('photo')}>
                <I.i113 />
                Cambiar foto
              </button>
            </div>
          </div>
          <div className="panel mini-panel">
            <div className="panel-head">
              <h2 className="panel-title" style={{ fontFamily: 'var(--font-body)', fontSize: '13px' }}>
                Estado de cuenta
              </h2>
            </div>
            <div className="panel-body">
              <span className="badge activo">Activa</span>
            </div>
          </div>
        </div>
        <div className="col-info">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Información personal</h2>
              <span className="section-note">
                <I.i114 />
                Solo lectura
              </span>
            </div>
            <div className="panel-body">
              <div className="info-grid">
                <Field label="Nombre completo" value={fullName} />
                <Field label="Nombre" value={me?.firstName} />
                <Field label="Apellido" value={me?.lastName} />
                <Field label="Roles" value={(me?.roles || []).includes('TEACHER') ? 'Docente' : me?.roles?.join(', ')} />
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Datos de contacto</h2>
              {!editing && (
                <button className="btn-ghost" onClick={enterEdit}>
                  <I.i69 />
                  Editar
                </button>
              )}
            </div>
            <div className="panel-body">
              {!editing ? (
                <div>
                  <div className="info-grid">
                    <Field label="Correo institucional" value={me?.email} />
                    <Field label="Correo personal" value={data.emailPersonal} readonly={false} />
                    <Field label="Teléfono" value={data.phone} readonly={false} />
                  </div>
                  {banner === 'success' && (
                    <div className="save-banner success" style={{ display: 'flex' }}>
                      <I.i73 />
                      <p>
                        <strong>Cambios guardados correctamente</strong> Tu información fue actualizada.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <div className="info-grid">
                    <div className="field-static-inline">
                      <p className="info-label">Correo institucional</p>
                      <p className="static-value">{me?.email}</p>
                    </div>
                    <div className={`form-field${errors.emailPersonal ? ' has-error' : ''}`}>
                      <label htmlFor="inputEmailPersonal">Correo personal</label>
                      <input
                        type="email"
                        id="inputEmailPersonal"
                        value={draft.emailPersonal}
                        onChange={(e) => setDraft((d) => ({ ...d, emailPersonal: e.target.value }))}
                      />
                      <span className="field-error">
                        <I.i115 />
                        Ingresá un correo electrónico válido.
                      </span>
                    </div>
                    <div className={`form-field${errors.phone ? ' has-error' : ''}`}>
                      <label htmlFor="inputPhone">Teléfono</label>
                      <input
                        type="tel"
                        id="inputPhone"
                        value={draft.phone}
                        onChange={(e) => setDraft((d) => ({ ...d, phone: e.target.value }))}
                      />
                      <span className="field-error">
                        <I.i115 />
                        Ingresá un número de teléfono válido.
                      </span>
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn-secondary" onClick={cancelEdit}>
                      Cancelar
                    </button>
                    <button className="btn-primary" onClick={save}>
                      <span>Guardar cambios</span>
                    </button>
                  </div>
                  {banner === 'error' && (
                    <div className="save-banner error" style={{ display: 'flex' }}>
                      <I.i3 />
                      <p>
                        <strong>No pudimos guardar los cambios</strong> Intentá nuevamente.
                        <span className="retry-inline">
                          <button className="btn-secondary" onClick={save}>
                            Intentar nuevamente
                          </button>
                        </span>
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Información institucional</h2>
              <span className="section-note">
                <I.i114 />
                Solo lectura
              </span>
            </div>
            <div className="panel-body">
              <div className="info-grid">
                <Field label="Legajo docente" value={me?.fileNumber} />
                <Field label="Cargo" value="Docente" />
                <Field label="ID de usuario" value={me?.userId} />
                <Field label="Estado" value="Activo" />
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Cursos a cargo</h2>
            </div>
            <div className="panel-body" style={{ padding: '8px 10px 12px' }}>
              <div className="course-list">
                {courses.isLoading && <div className="skel" style={{ width: '100%', height: 48 }} />}
                {!courses.isLoading && !active.length && <p className="course-row-meta">No tenés cursos activos.</p>}
                {active.map((c, i) => (
                  <Fragment key={c.id}>
                    {i > 0 && <div className="course-divider" />}
                    <button className="course-row" onClick={() => navigate(`/cursos/${c.id}`)}>
                      <span className="course-row-icon">
                        <I.i116 />
                      </span>
                      <span className="course-row-main">
                        <p className="course-row-name">{c.subject.name}</p>
                        <p className="course-row-meta">
                          Comisión {c.code} · {c.period.label}
                        </p>
                      </span>
                      <I.i27 className="course-chev" />
                    </button>
                  </Fragment>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
