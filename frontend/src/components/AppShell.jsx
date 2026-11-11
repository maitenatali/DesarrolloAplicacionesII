import { Fragment, useEffect, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { useGetMeQuery, useGetUnreadCountQuery, useGetWalletQuery, useLogoutMutation } from '../api/api';
import { sessionEnded } from '../features/auth/authSlice';
import { initials, money } from '../lib/format';
import * as I from './icons.generated';

const NAV = [
  [
    { key: 'inicio', to: '/', label: 'Inicio', icon: I.i17 },
    { key: 'cursos', to: '/cursos', label: 'Mis cursos', icon: I.i18 },
    { key: 'actas', to: '/actas', label: 'Actas', icon: I.i19 },
    { key: 'calendario', to: '/calendario', label: 'Calendario académico', icon: I.i20 },
    { key: 'notificaciones', to: '/notificaciones', label: 'Notificaciones', icon: I.i11 },
  ],
  [
    { key: 'compras', to: '/compras', label: 'Mis compras', icon: I.i21 },
    { key: 'cuenta', to: '/cuenta', label: 'Cuenta institucional', icon: I.i15 },
  ],
];

/** Datos del docente logueado para el header (nombre desde Backoffice vía GET /me). */
export function useCurrentTeacher() {
  const { data: me } = useGetMeQuery();
  const fullName = me?.fullName || me?.email || '';
  return { me, fullName, firstName: me?.firstName || fullName.split(' ')[0] || '', initials: initials(fullName) };
}

export function useLogout() {
  const [logout] = useLogoutMutation();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  return async () => {
    try {
      await logout().unwrap();
    } catch {
      /* la sesión se cierra igual en el cliente */
    }
    dispatch(sessionEnded());
    navigate('/login', { replace: true });
  };
}

/**
 * Header + sidebar comunes a todas las pantallas autenticadas (mismo markup que los mockups).
 * `scope` es el id de la pantalla: su CSS está aislado bajo `.pg-<scope>`.
 */
export default function AppShell({ scope, active, children, after, onBalanceClick, onNotificationsClick, className = '' }) {
  const navigate = useNavigate();
  const doLogout = useLogout();
  const { fullName, initials: ini } = useCurrentTeacher();
  const { data: wallet } = useGetWalletQuery();
  const { data: unread } = useGetUnreadCountQuery(undefined, { pollingInterval: 30000 });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  const go = (to) => (e) => {
    e?.preventDefault?.();
    setSidebarOpen(false);
    setMenuOpen(false);
    navigate(to);
  };

  return (
    <div className={`pg pg-${scope} ${className}`}>
      <header className="app-header">
        <div className="header-left">
          <button
            className="hamburger"
            aria-label="Abrir menú"
            aria-expanded={String(sidebarOpen)}
            onClick={() => setSidebarOpen((o) => !o)}
          >
            <I.i9 />
          </button>
          <button className="brand-mark" aria-label="UADEnet — ir a Inicio" onClick={go('/')}>
            <span className="brand-glyph">
              <I.i10 />
            </span>
            <span className="brand-word">
              UADE<span className="accent">net</span>
            </span>
          </button>
        </div>
        <div className="header-right">
          <button className="icon-btn" aria-label="Notificaciones" onClick={onNotificationsClick || go('/notificaciones')}>
            <I.i11 />
            {unread?.count > 0 && <span className="badge-dot" />}
          </button>
          <button
            className="balance-chip"
            aria-label="Saldo institucional — ir a Cuenta institucional"
            onClick={onBalanceClick || go('/cuenta')}
          >
            <I.i12 />
            <span className="amount">{wallet ? money(wallet.balance) : '—'}</span>
            <span className="label">Saldo</span>
          </button>
          <div className="user-menu-wrap" ref={menuRef}>
            <button
              className={`user-menu${menuOpen ? ' active-menu' : ''}`}
              aria-label="Menú de usuario"
              onClick={() => setMenuOpen((o) => !o)}
            >
              <span className="avatar">{ini}</span>
              <span className="user-meta">
                <span className="name">{fullName}</span>
                <span className="role">Docente</span>
              </span>
              <I.i13 style={{ color: 'var(--text-400)' }} />
            </button>
            <div className={`user-dropdown${menuOpen ? ' open' : ''}`}>
              <button onClick={go('/perfil')}>
                <I.i14 />
                Mi perfil
              </button>
              <button onClick={go('/cuenta')}>
                <I.i15 />
                Cuenta institucional
              </button>
              <div className="dd-divider" />
              <button className="logout" onClick={doLogout}>
                <I.i16 />
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
      </header>
      <div className={`sidebar-backdrop${sidebarOpen ? ' open' : ''}`} onClick={() => setSidebarOpen(false)} />
      <nav className={`sidebar${sidebarOpen ? ' open' : ''}`} aria-label="Navegación principal">
        {NAV.map((group, gi) => (
          <Fragment key={gi}>
            <div className="nav-group">
              {group.map((item) => (
                <a
                  key={item.key}
                  href={item.to}
                  className={`nav-item${active === item.key ? ' active' : ''}`}
                  aria-current={active === item.key ? 'page' : undefined}
                  onClick={go(item.to)}
                >
                  <item.icon />
                  {item.label}
                </a>
              ))}
            </div>
            <div className="nav-divider" />
          </Fragment>
        ))}
        <div className="nav-group">
          <a
            href="/perfil"
            className={`nav-item${active === 'perfil' ? ' active' : ''}`}
            aria-current={active === 'perfil' ? 'page' : undefined}
            onClick={go('/perfil')}
          >
            <I.i14 />
            Perfil
          </a>
          <a
            href="/login"
            className="nav-item logout"
            onClick={(e) => {
              e.preventDefault();
              doLogout();
            }}
          >
            <I.i22 />
            Cerrar sesión
          </a>
        </div>
      </nav>
      <div className="app-body">
        <main className="main">{children}</main>
      </div>
      {after}
    </div>
  );
}
