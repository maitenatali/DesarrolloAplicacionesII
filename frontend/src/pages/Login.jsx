import { useState } from 'react';
import { useDispatch } from 'react-redux';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLoginMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import * as I from '../components/icons.generated';
import { sessionStarted } from '../features/auth/authSlice';
import '../styles/pages/01.css';

const PORTAL_ROLES = ['TEACHER', 'ACADEMIC_ADMIN', 'ADMIN_STAFF'];
const isInstitutionalEmail = (v) => /^[^\s@]+@uade\.edu\.ar$/i.test(v.trim());

const EyeOff = () => (
  <svg viewBox="0 0 20 20" fill="none">
    <path d="M2.5 2.5L17.5 17.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    <path
      d="M8.3 8.4A2.3 2.3 0 0 0 10 12.3c.6 0 1.15-.22 1.57-.58M5.6 5.7C3.4 7.1 1.5 10 1.5 10s3 6 8.5 6c1.5 0 2.83-.42 3.97-1.05M15.9 13.9C17.4 12.6 18.5 10 18.5 10s-1.2-2.4-3.3-4.2M11.7 4.2C11.15 4.07 10.58 4 10 4c-.5 0-.98.05-1.44.14"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({ email: false, password: false });
  const [alert, setAlert] = useState(null);
  const [redirecting, setRedirecting] = useState(false);
  const [login, { isLoading }] = useLoginMutation();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();

  const onSubmit = async (e) => {
    e.preventDefault();
    setAlert(null);
    const next = { email: !isInstitutionalEmail(email), password: !password };
    setErrors(next);
    if (next.email || next.password) {
      document.getElementById(next.email ? 'email' : 'password')?.focus();
      return;
    }
    try {
      const res = await login({ email: email.trim(), password }).unwrap();
      if (!res.user?.roles?.some((r) => PORTAL_ROLES.includes(r))) {
        setAlert('Tu cuenta no tiene acceso al Portal del Docente.');
        return;
      }
      setRedirecting(true);
      dispatch(sessionStarted({ accessToken: res.accessToken, user: res.user }));
      navigate(location.state?.from || '/', { replace: true });
    } catch (err) {
      const apiErr = toApiError(err);
      setAlert(apiErr.status === 401 || apiErr.status === 400 ? 'El email o la contraseña son incorrectos.' : apiErr.detail);
    }
  };

  const loading = isLoading || redirecting;

  return (
    <div className="pg pg-01">
      <div className="screen">
        <div className="net-motif" aria-hidden="true">
          <I.i1 />
        </div>
        <main className="login-card" role="main">
          <div className="brand">
            <button className="brand-mark" type="button" aria-label="UADEnet — ir al inicio">
              <span className="brand-glyph">
                <I.i2 />
              </span>
              <span className="brand-word">
                UADE<span className="accent">net</span>
              </span>
            </button>
            <h1 className="title">Portal del Docente</h1>
            <p className="subtitle">Ingresá con tu cuenta institucional</p>
          </div>
          <div className={`form-alert${alert ? ' show' : ''}`} role="alert">
            <I.i3 />
            <span>{alert || 'El email o la contraseña son incorrectos.'}</span>
          </div>
          <form noValidate onSubmit={onSubmit}>
            <div className={`field${errors.email ? ' error' : ''}`}>
              <label htmlFor="email">Email institucional</label>
              <div className="input-wrap">
                <span className="leading-icon">
                  <I.i4 />
                </span>
                <input
                  type="email"
                  id="email"
                  name="email"
                  placeholder="Ingresá tu email"
                  autoComplete="username"
                  className={errors.email ? 'has-error' : ''}
                  value={email}
                  disabled={loading}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="field-error">
                <I.i3 />
                <span>Ingresá un email institucional válido.</span>
              </div>
            </div>
            <div className={`field${errors.password ? ' error' : ''}`}>
              <label htmlFor="password">Contraseña</label>
              <div className="input-wrap password-wrap">
                <span className="leading-icon">
                  <I.i5 />
                </span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  placeholder="Ingresá tu contraseña"
                  autoComplete="current-password"
                  className={errors.password ? 'has-error' : ''}
                  value={password}
                  disabled={loading}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="toggle-visibility"
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  aria-pressed={String(showPassword)}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  {showPassword ? <EyeOff /> : <I.i6 />}
                </button>
              </div>
              <div className="field-error">
                <I.i3 />
                <span>La contraseña es obligatoria.</span>
              </div>
            </div>
            <div className="row-between">
              <a
                href="/recuperar-contrasena"
                className="link"
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/recuperar-contrasena');
                }}
              >
                ¿Olvidaste tu contraseña?
              </a>
            </div>
            <button type="submit" className={`btn-primary${loading ? ' loading' : ''}`} disabled={loading}>
              <span className="spinner" />
              <span className="btn-label">{redirecting ? 'Redirigiendo…' : 'Iniciar sesión'}</span>
            </button>
          </form>
          <p className="foot-note">© 2026 Universidad Argentina de la Empresa</p>
        </main>
      </div>
    </div>
  );
}
