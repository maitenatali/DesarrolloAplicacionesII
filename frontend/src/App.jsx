import { Navigate, Route, Routes } from 'react-router-dom';
import RequireAuth, { PublicOnly } from './components/RequireAuth';
import Account from './pages/Account';
import ActaDetail from './pages/ActaDetail';
import ActaNew from './pages/ActaNew';
import Actas from './pages/Actas';
import Calendar from './pages/Calendar';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';
import PurchaseDetail from './pages/PurchaseDetail';
import Purchases from './pages/Purchases';
import TopUp from './pages/TopUp';
import Attendance from './pages/Attendance';
import AttendanceHistory from './pages/AttendanceHistory';
import CourseDetail from './pages/CourseDetail';
import Dashboard from './pages/Dashboard';
import ExamDetail from './pages/ExamDetail';
import ExamForm from './pages/ExamForm';
import Exams from './pages/Exams';
import Grades from './pages/Grades';
import Login from './pages/Login';
import MyCourses from './pages/MyCourses';
import RecoverPassword from './pages/RecoverPassword';
import Students from './pages/Students';

export default function App() {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<Login />} />
        <Route path="/recuperar-contrasena" element={<RecoverPassword />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cursos" element={<MyCourses />} />
        <Route path="/cursos/:courseId" element={<CourseDetail />} />
        <Route path="/cursos/:courseId/estudiantes" element={<Students />} />
        <Route path="/cursos/:courseId/asistencia" element={<Attendance />} />
        <Route path="/cursos/:courseId/asistencia/historial" element={<AttendanceHistory />} />
        <Route path="/cursos/:courseId/calificaciones" element={<Grades />} />
        <Route path="/cursos/:courseId/examenes" element={<Exams />} />
        <Route path="/cursos/:courseId/examenes/nuevo" element={<ExamForm />} />
        <Route path="/cursos/:courseId/examenes/:examId" element={<ExamDetail />} />
        <Route path="/cursos/:courseId/examenes/:examId/editar" element={<ExamForm />} />
        <Route path="/actas" element={<Actas />} />
        <Route path="/actas/nueva" element={<ActaNew />} />
        <Route path="/actas/:actaId" element={<ActaDetail />} />
        <Route path="/calendario" element={<Calendar />} />
        <Route path="/notificaciones" element={<Notifications />} />
        <Route path="/compras" element={<Purchases />} />
        <Route path="/compras/:purchaseId" element={<PurchaseDetail />} />
        <Route path="/cuenta" element={<Account />} />
        <Route path="/cuenta/cargar-saldo" element={<TopUp />} />
        <Route path="/perfil" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
