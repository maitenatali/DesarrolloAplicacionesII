import { configureStore } from '@reduxjs/toolkit';
import { api } from '../api/api';
import authReducer, { sessionEnded } from '../features/auth/authSlice';
import uiReducer from '../features/ui/uiSlice';

export function makeStore(preloadedState) {
  const store = configureStore({
    reducer: { auth: authReducer, ui: uiReducer, [api.reducerPath]: api.reducer },
    middleware: (gDM) => gDM().concat(api.middleware),
    preloadedState,
  });
  return store;
}

export const store = makeStore();

// Al cerrar sesión se descarta toda la caché de datos del usuario anterior.
let lastStatus = store.getState().auth.status;
store.subscribe(() => {
  const status = store.getState().auth.status;
  if (status === lastStatus) return;
  const wasLoggedIn = lastStatus === 'authenticated';
  lastStatus = status;
  if (wasLoggedIn && status === 'anonymous') store.dispatch(api.util.resetApiState());
});

export { sessionEnded };
