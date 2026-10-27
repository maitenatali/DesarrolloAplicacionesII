import { fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { sessionEnded, sessionStarted } from '../features/auth/authSlice';

/** Error normalizado a partir de application/problem+json (CORE y teacher-service usan el mismo formato). */
export function toApiError(error) {
  if (!error) return null;
  const data = error.data && typeof error.data === 'object' ? error.data : {};
  const status = typeof error.status === 'number' ? error.status : 0;
  let detail = data.detail || data.title;
  if (!detail) {
    detail = status === 0 || error.status === 'FETCH_ERROR'
      ? 'No se pudo conectar con el servidor. Verificá tu conexión e intentá nuevamente.'
      : 'Ocurrió un error inesperado. Intentá nuevamente.';
  }
  return { status, code: data.code || null, detail, correlationId: data.correlationId || null, errors: data.errors || null };
}

const rawBaseQuery = fetchBaseQuery({
  baseUrl: '',
  credentials: 'include',
  prepareHeaders: (headers, { getState }) => {
    const token = getState().auth.accessToken;
    if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
    return headers;
  },
});

let refreshing = null;

/** Pide un access token nuevo con la cookie de refresh. Comparte la promesa si hay varios 401 a la vez. */
export function refreshSession(api) {
  if (!refreshing) {
    refreshing = Promise.resolve(rawBaseQuery({ url: '/api/v1/auth/refresh', method: 'POST' }, api, {}))
      .then((res) => {
        if (res.data?.accessToken) {
          api.dispatch(sessionStarted({ accessToken: res.data.accessToken, user: res.data.user }));
          return true;
        }
        api.dispatch(sessionEnded());
        return false;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

const NO_RETRY = ['/api/v1/auth/login', '/api/v1/auth/refresh', '/api/v1/auth/logout', '/api/v1/auth/password/forgot'];

export async function baseQueryWithReauth(args, api, extra) {
  let result = await rawBaseQuery(args, api, extra);
  const url = typeof args === 'string' ? args : args.url;
  if (result.error?.status === 401 && !NO_RETRY.includes(url)) {
    if (await refreshSession(api)) result = await rawBaseQuery(args, api, extra);
  }
  return result;
}
