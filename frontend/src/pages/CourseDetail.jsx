import { useNavigate } from 'react-router-dom';
import { useGetCourseExamsQuery } from '../api/api';
import AppShell from '../components/AppShell';
import { Breadcrumb, CourseHero, CourseLoadState, CourseTabs, courseTrail } from '../components/CourseNav';
import * as I from '../components/icons.generated';
import { useCourse, courseSchedule } from '../lib/courses';
import { COURSE_STATUS, examStatus } from '../lib/domain';
import { parseDay, MONTHS } from '../lib/format';
import '../styles/pages/05.css';

const STATUS_CLASS = { EN_CURSO: 'activo', PROGRAMADO: 'proximo', FINALIZADO: 'finalizado', CANCELADO: 'finalizado' };

export default function CourseDetail() {
  const navigate = useNavigate();
  const q = useCourse();
  const { courseId, course } = q;
  const exams = useGetCourseExamsQuery(courseId);

  if (!course) {
    return (
      <AppShell scope="05" active="cursos">
        <Breadcrumb trail={courseTrail(null, courseId)} />
        <CourseLoadState query={q} />
      </AppShell>
    );
  }

  const statusBadge = (
    <span className={`badge ${STATUS_CLASS[course.raw.status] || 'activo'}`}>{COURSE_STATUS[course.raw.status] || course.raw.status}</span>
  );
  const upcoming = (exams.data || [])
    .filter((e) => examStatus(e) === 'proximo')
    .sort((a, b) => `${a.date}${a.startTime}`.localeCompare(`${b.date}${b.startTime}`));
  const goStudents = () => navigate(`/cursos/${courseId}/estudiantes`);
  const sched = course.raw.schedule?.[0];

  return (
    <AppShell scope="05" active="cursos">
      <Breadcrumb trail={courseTrail(course, courseId)} />
      <div>
        <CourseHero course={course} badge={statusBadge}>
          <div className="course-hero-actions">
            <button className="btn-secondary" onClick={() => navigate('/cursos')}>
              <I.i35 />
              Volver a Mis cursos
            </button>
          </div>
        </CourseHero>
        <CourseTabs courseId={courseId} active="info" />
        <div className="two-col">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Información general</h2>
            </div>
            <div className="panel-body">
              <div className="info-list">
                <div className="info-row">
                  <span className="info-label">Materia</span>
                  <span className="info-value">{course.name}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Comisión</span>
                  <span className="info-value">{course.com}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Período académico</span>
                  <span className="info-value">{course.period}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Estado</span>
                  {statusBadge}
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Horario y ubicación</h2>
            </div>
            <div className="panel-body" style={{ paddingTop: '14px' }}>
              <div className="schedule-item">
                <span className="schedule-icon">
                  <I.i20 />
                </span>
                <div className="schedule-main">
                  <p className="schedule-day">
                    {sched ? `${courseSchedule({ schedule: [sched] }, true).split(' ')[0]} — ${sched.startTime} a ${sched.endTime}` : 'Sin horario asignado'}
                  </p>
                  <p className="schedule-detail">
                    Sede {course.sede} · Aula {course.room}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="two-col">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Estudiantes</h2>
              <button className="panel-link" onClick={goStudents}>
                Ver todos →
              </button>
            </div>
            <div className="panel-body">
              {course.students > 0 ? (
                <>
                  <p className="students-count">{course.students} estudiantes inscriptos</p>
                  <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={goStudents}>
                    Ver todos los estudiantes
                  </button>
                </>
              ) : (
                <div className="empty-state">
                  <I.i37 />
                  <p>No hay estudiantes registrados</p>
                  <p className="state-sub">Los estudiantes asociados al curso aparecerán aquí.</p>
                  <button className="btn-secondary" style={{ marginTop: 4 }} onClick={goStudents}>
                    Ver estudiantes
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Próximos exámenes</h2>
              <button className="panel-link" onClick={() => navigate(`/cursos/${courseId}/examenes`)}>
                Ver todos →
              </button>
            </div>
            <div className="panel-body" style={{ paddingTop: '2px' }}>
              {exams.isLoading ? (
                <div className="skel" style={{ width: '100%', height: 60, marginTop: 12 }} />
              ) : upcoming.length ? (
                upcoming.slice(0, 3).map((e) => {
                  const d = parseDay(e.date);
                  return (
                    <button className="exam-item" key={e.id} onClick={() => navigate(`/cursos/${courseId}/examenes/${e.id}`)}>
                      <span className="exam-icon">
                        <I.i40 />
                      </span>
                      <span className="exam-main">
                        <p className="exam-name">{e.name}</p>
                        <p className="exam-meta">
                          {d.getDate()} de {MONTHS[d.getMonth()]} · {e.startTime}
                        </p>
                      </span>
                      <span className="badge programado">Programado</span>
                      <I.i34 className="exam-chev" />
                    </button>
                  );
                })
              ) : (
                <div className="empty-state">
                  <I.i42 />
                  <p>No hay exámenes próximos</p>
                  <p className="state-sub">Los próximos exámenes asociados a {course.name} aparecerán aquí.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
