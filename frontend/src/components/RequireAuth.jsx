import { useEffect } from 'react';
import { useDispatch, useSelector, useStore } from 'react-redux';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { refreshSession } from '../api/baseQuery';
import { checking, sessionEnded } from '../features/auth/authSlice';

/** Al abrir la app intenta recuperar la sesión con la cookie de refresh de CORE. */
export function useBootstrapSession() {
  const status = useSelector((s) => s.auth.status);
  const dispatch = useDispatch();
  const store = useStore();
  useEffect(() => {
    if (status !== 'idle') return;
    dispatch(checking());
    refreshSession({ dispatch, getState: store.getState }).catch(() => dispatch(sessionEnded()));
  }, [status, dispatch, store]);
  return status;
}

export default function RequireAuth() {
  const status = useBootstrapSession();
  const location = useLocation();
  if (status === 'idle' || status === 'checking') return <div className="boot-screen">Cargando…</div>;
  if (status !== 'authenticated') return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

/** Login y recuperación: si ya hay sesión, ir al inicio. */
export function PublicOnly() {
  const status = useBootstrapSession();
  if (status === 'idle' || status === 'checking') return <div className="boot-screen">Cargando…</div>;
  if (status === 'authenticated') return <Navigate to="/" replace />;
  return <Outlet />;
}
