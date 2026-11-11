import { createApi } from '@reduxjs/toolkit/query/react';
import { baseQueryWithReauth } from './baseQuery';

// Portal Docente vía gateway de CORE: /api/v1/teacher/* -> teacher-service /api/v1/* (proxy de Vite en local).
const T = '/api/v1/teacher';

export const api = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['Me', 'Course', 'Students', 'Exam', 'Grades', 'Attendance', 'Acta', 'Wallet', 'Notification', 'Calendar'],
  endpoints: (b) => ({
    // ── CORE: auth ──────────────────────────────────────────
    login: b.mutation({ query: (body) => ({ url: '/api/v1/auth/login', method: 'POST', body }) }),
    logout: b.mutation({ query: () => ({ url: '/api/v1/auth/logout', method: 'POST' }) }),
    forgotPassword: b.mutation({ query: (body) => ({ url: '/api/v1/auth/password/forgot', method: 'POST', body }) }),

    // ── Portal Docente ─────────────────────────────────────
    getMe: b.query({ query: () => `${T}/me`, providesTags: ['Me'] }),
    getPeriods: b.query({ query: () => `${T}/periods` }),
    getExamTypes: b.query({ query: () => `${T}/exam-types` }),
    getExamTurns: b.query({ query: () => `${T}/exam-turns` }),
    getCourses: b.query({ query: () => `${T}/courses`, providesTags: ['Course'] }),
    getCourse: b.query({ query: (id) => `${T}/courses/${id}`, providesTags: (r, e, id) => [{ type: 'Course', id }] }),
    getStudents: b.query({
      query: (id) => `${T}/courses/${id}/students`,
      providesTags: (r, e, id) => [{ type: 'Students', id }],
    }),
    getPrerequisites: b.query({ query: (id) => `${T}/courses/${id}/prerequisites` }),

    getCourseExams: b.query({
      query: (id) => `${T}/courses/${id}/exams`,
      providesTags: (r, e, id) => [{ type: 'Exam', id: `course-${id}` }],
    }),
    getMyExams: b.query({ query: (params = {}) => ({ url: `${T}/exams`, params }), providesTags: [{ type: 'Exam', id: 'mine' }] }),
    getExam: b.query({
      query: ({ courseId, examId }) => `${T}/courses/${courseId}/exams/${examId}`,
      providesTags: (r, e, { examId }) => [{ type: 'Exam', id: examId }],
    }),
    createExam: b.mutation({
      query: ({ courseId, body }) => ({ url: `${T}/courses/${courseId}/exams`, method: 'POST', body }),
      invalidatesTags: (r, e, { courseId }) => examTags(courseId),
    }),
    updateExam: b.mutation({
      query: ({ courseId, examId, body }) => ({ url: `${T}/courses/${courseId}/exams/${examId}`, method: 'PATCH', body }),
      invalidatesTags: (r, e, { courseId, examId }) => [...examTags(courseId), { type: 'Exam', id: examId }],
    }),
    cancelExam: b.mutation({
      query: ({ courseId, examId, reason }) => ({
        url: `${T}/courses/${courseId}/exams/${examId}/cancellation`,
        method: 'POST',
        body: { reason: reason || null },
      }),
      invalidatesTags: (r, e, { courseId, examId }) => [...examTags(courseId), { type: 'Exam', id: examId }],
    }),

    getExamGrades: b.query({
      query: ({ courseId, examId }) => `${T}/courses/${courseId}/exams/${examId}/grades`,
      providesTags: (r, e, { examId }) => [{ type: 'Grades', id: `exam-${examId}` }],
    }),
    saveExamGrades: b.mutation({
      query: ({ courseId, examId, entries }) => ({
        url: `${T}/courses/${courseId}/exams/${examId}/grades`,
        method: 'PUT',
        body: { entries },
      }),
      invalidatesTags: (r, e, { courseId, examId }) => [
        { type: 'Grades', id: `exam-${examId}` },
        { type: 'Grades', id: `course-${courseId}` },
        { type: 'Exam', id: examId },
        ...examTags(courseId),
        { type: 'Students', id: String(courseId) },
      ],
    }),
    getGradeMatrix: b.query({
      query: (id) => `${T}/courses/${id}/grades`,
      providesTags: (r, e, id) => [{ type: 'Grades', id: `course-${id}` }],
    }),

    getAttendances: b.query({
      query: (id) => `${T}/courses/${id}/attendances`,
      providesTags: (r, e, id) => [{ type: 'Attendance', id: `course-${id}` }],
    }),
    getAttendance: b.query({
      query: ({ courseId, day }) => `${T}/courses/${courseId}/attendances/${day}`,
      providesTags: (r, e, { courseId, day }) => [{ type: 'Attendance', id: `${courseId}-${day}` }],
    }),
    saveAttendance: b.mutation({
      query: ({ courseId, day, body }) => ({ url: `${T}/courses/${courseId}/attendances/${day}`, method: 'PUT', body }),
      invalidatesTags: (r, e, { courseId, day }) => [
        { type: 'Attendance', id: `course-${courseId}` },
        { type: 'Attendance', id: `${courseId}-${day}` },
        { type: 'Attendance', id: `summary-${courseId}` },
        { type: 'Students', id: String(courseId) },
      ],
    }),
    getAttendanceSummary: b.query({
      query: (id) => `${T}/courses/${id}/attendance-summary`,
      providesTags: (r, e, id) => [{ type: 'Attendance', id: `summary-${id}` }],
    }),

    getActas: b.query({ query: (params = {}) => ({ url: `${T}/actas`, params: { limit: 200, ...params } }), providesTags: ['Acta'] }),
    getActa: b.query({ query: (id) => `${T}/actas/${id}`, providesTags: (r, e, id) => [{ type: 'Acta', id }] }),
    createActa: b.mutation({
      query: (body) => ({ url: `${T}/actas`, method: 'POST', body }),
      invalidatesTags: ['Acta', 'Students', 'Exam', 'Grades'],
    }),
    annulActa: b.mutation({
      query: ({ id, reason }) => ({ url: `${T}/actas/${id}/annulment`, method: 'POST', body: { reason } }),
      invalidatesTags: ['Acta', 'Students', 'Exam', 'Grades'],
    }),
    syncActa: b.mutation({
      query: (id) => ({ url: `${T}/actas/${id}/sync`, method: 'POST' }),
      invalidatesTags: (r, e, id) => ['Acta', { type: 'Acta', id }],
    }),

    getCalendar: b.query({ query: (params) => ({ url: `${T}/calendar`, params }), providesTags: ['Calendar'] }),
    getPurchases: b.query({ query: () => `${T}/purchases` }),

    // ── CORE: wallet y notificaciones ───────────────────────
    getWallet: b.query({ query: () => '/api/v1/wallets/me', providesTags: ['Wallet'] }),
    getTransactions: b.query({
      query: (params = {}) => ({ url: '/api/v1/wallets/me/transactions', params: { limit: 100, ...params } }),
      providesTags: ['Wallet'],
    }),
    topUp: b.mutation({
      query: ({ idempotencyKey, ...body }) => ({
        url: '/api/v1/wallets/me/top-ups',
        method: 'POST',
        body,
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
      invalidatesTags: ['Wallet'],
    }),
    getNotifications: b.query({
      query: (params = {}) => ({ url: '/api/v1/notifications', params: { limit: 100, ...params } }),
      providesTags: ['Notification'],
    }),
    getUnreadCount: b.query({ query: () => '/api/v1/notifications/unread-count', providesTags: ['Notification'] }),
    markNotification: b.mutation({
      query: ({ id, read }) => ({ url: `/api/v1/notifications/${id}`, method: 'PATCH', body: { read } }),
      invalidatesTags: ['Notification'],
    }),
    markAllNotificationsRead: b.mutation({
      query: () => ({ url: '/api/v1/notifications/read-all', method: 'POST' }),
      invalidatesTags: ['Notification'],
    }),
  }),
});

function examTags(courseId) {
  return [
    { type: 'Exam', id: `course-${courseId}` },
    { type: 'Exam', id: 'mine' },
    { type: 'Grades', id: `course-${courseId}` },
    'Calendar',
  ];
}

export const {
  useLoginMutation,
  useLogoutMutation,
  useForgotPasswordMutation,
  useGetMeQuery,
  useGetPeriodsQuery,
  useGetExamTypesQuery,
  useGetExamTurnsQuery,
  useGetCoursesQuery,
  useGetCourseQuery,
  useGetStudentsQuery,
  useGetPrerequisitesQuery,
  useGetCourseExamsQuery,
  useGetMyExamsQuery,
  useGetExamQuery,
  useCreateExamMutation,
  useUpdateExamMutation,
  useCancelExamMutation,
  useGetExamGradesQuery,
  useSaveExamGradesMutation,
  useGetGradeMatrixQuery,
  useGetAttendancesQuery,
  useGetAttendanceQuery,
  useSaveAttendanceMutation,
  useGetAttendanceSummaryQuery,
  useGetActasQuery,
  useGetActaQuery,
  useCreateActaMutation,
  useAnnulActaMutation,
  useSyncActaMutation,
  useGetCalendarQuery,
  useGetPurchasesQuery,
  useGetWalletQuery,
  useGetTransactionsQuery,
  useTopUpMutation,
  useGetNotificationsQuery,
  useGetUnreadCountQuery,
  useMarkNotificationMutation,
  useMarkAllNotificationsReadMutation,
} = api;
