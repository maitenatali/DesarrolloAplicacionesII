import { createSlice } from '@reduxjs/toolkit';

// El access token vive solo en memoria (Redux). El refresh token es una cookie httpOnly que maneja CORE.
const initialState = {
  status: 'idle', // idle | checking | authenticated | anonymous
  accessToken: null,
  user: null, // { id, email, roles, permissions }
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    checking(state) {
      state.status = 'checking';
    },
    sessionStarted(state, { payload }) {
      state.status = 'authenticated';
      state.accessToken = payload.accessToken;
      state.user = payload.user ?? state.user;
    },
    sessionEnded(state) {
      state.status = 'anonymous';
      state.accessToken = null;
      state.user = null;
    },
  },
});

export const { checking, sessionStarted, sessionEnded } = authSlice.actions;
export default authSlice.reducer;

export const selectAuth = (s) => s.auth;
export const selectIsTeacher = (s) => (s.auth.user?.roles ?? []).includes('TEACHER');
