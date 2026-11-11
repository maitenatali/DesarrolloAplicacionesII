import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForgotPasswordMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import * as I from '../components/icons.generated';
import '../styles/pages/01b.css';

const isInstitutionalEmail = (v) => /^[^\s@]+@uade\.edu\.ar$/i.test(v.trim());

export default function RecoverPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [error, setError] = useState(null);
  const [sentTo, setSentTo] = useState(null);
  const [cooldown, setCooldown] = useState(0);
  const [forgot, { isLoading }] = useForgotPasswordMutation();

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  // CORE responde 202 exista o no la cuenta (no revela qué emails están registrados).
  const send = async (value) => {
    await forgot({ email: value.trim() }).unwrap();
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!isInstitutionalEmail(email)) {
      setError('Ingresá un email institucional válido.');
      document.getElementById('email')?.focus();
      return;
    }
    setError(null);
    try {
      await send(email);
      setSentTo(email.trim());
    } catch (err) {
      setError(toApiError(err).detail);
    }
  };

  const resend = async () => {
    if (cooldown > 0) return;
    setCooldown(30);
    try {
      await send(sentTo);
    } catch {
      /* se puede reintentar al terminar el contador */
    }
  };

  const goLogin = () => navigate('/login');

  return (
    <div className="pg pg-01b">
      <div className="screen">
        <div className="net-motif" aria-hidden="true">
          <I.i1 />
        </div>
        <main className="login-card" role="main">
          <button className="back-link" type="button" onClick={goLogin}>
            <I.i7 />
            Volver a iniciar sesión
          </button>
          <div className={`view${sentTo ? '' : ' active'}`}>
            <div className="brand">
              <button className="brand-mark" type="button" aria-label="UADEnet — ir al inicio">
                <span className="brand-glyph">
                  <I.i2 />
                </span>
                <span className="brand-word">
                  UADE<span className="accent">net</span>
                </span>
              </button>
              <h1 className="title">Recuperar contraseña</h1>
              <p className="subtitle">
                Ingresá tu email institucional y te enviaremos un enlace para restablecer tu contraseña.
              </p>
            </div>
            <form noValidate onSubmit={onSubmit}>
              <div className={`field${error ? ' error' : ''}`}>
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
                    className={error ? 'has-error' : ''}
                    value={email}
                    disabled={isLoading}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <div className="field-error">
                  <I.i3 />
                  <span>{error || 'Ingresá un email institucional válido.'}</span>
                </div>
              </div>
              <button type="submit" className={`btn-primary${isLoading ? ' loading' : ''}`} disabled={isLoading}>
                <span className="spinner" />
                <span className="btn-label">Enviar enlace</span>
              </button>
            </form>
            <p className="foot-note">© 2026 Universidad Argentina de la Empresa</p>
          </div>
          <div className={`view${sentTo ? ' active' : ''}`}>
            <div className="brand">
              <div className="icon-badge success">
                <I.i8 />
              </div>
              <h1 className="title">Revisá tu email</h1>
              <p className="subtitle">
                Si <strong>{sentTo || 'tu email'}</strong> corresponde a una cuenta registrada, vas a recibir un enlace para
                restablecer tu contraseña en los próximos minutos.
              </p>
            </div>
            <button type="button" className="btn-secondary" onClick={goLogin}>
              Volver a iniciar sesión
            </button>
            <p className="resend-row">
              ¿No te llegó el email?{' '}
              <button type="button" disabled={cooldown > 0} onClick={resend}>
                {cooldown > 0 ? `Reenviar enlace (${cooldown}s)` : 'Reenviar enlace'}
              </button>
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
