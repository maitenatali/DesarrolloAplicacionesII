import { createSlice } from '@reduxjs/toolkit';

// Mensaje "flash" para mostrar un toast en la pantalla a la que se navega (p. ej. "Examen creado").
const uiSlice = createSlice({
  name: 'ui',
  initialState: { flash: null },
  reducers: {
    flash(state, { payload }) {
      state.flash = { id: Date.now(), type: 'success', ...(typeof payload === 'string' ? { message: payload } : payload) };
    },
    clearFlash(state) {
      state.flash = null;
    },
  },
});

export const { flash, clearFlash } = uiSlice.actions;
export default uiSlice.reducer;
