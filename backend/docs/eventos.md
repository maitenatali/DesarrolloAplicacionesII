# Eventos del Portal Docente (Módulo 2)

Eventos que publicamos en el bus de CORE (`POST /internal/v1/events`), para que cada grupo los simule en su mock.
Las rutas y sus respuestas están en [`openapi.json`](openapi.json). Por el gateway de CORE son `/api/v1/teacher/...`.

| `eventType` | Cuándo sale | Campos de `data` | Qué volver a leer |
|---|---|---|---|
| `teacher.attendance-recorded.v1` | Al guardar la asistencia de una clase | `courseId, date, counts{present, absent, justified}, records[]{studentId, status}` | `GET /students/{studentId}/courses/{courseId}/attendance` |
| `teacher.grade-published.v1` | Al cargar o cambiar notas (solo las que cambiaron) | `courseId, examId, examType, grades[]{studentId, grade, status}` | `GET /students/{studentId}/courses/{courseId}/grades` |
| `teacher.course-result-published.v1` | Al generar un acta FINAL, uno por alumno `APROBADO` o `DESAPROBADO` | `studentId, courseId, subjectId, periodId, siteId, teacherId, finalGrade, status, resultDate, actaNumber` | `GET /students/{studentId}/results?courseId={courseId}` |
| `teacher.acta-generated.v1` | Al generar un acta | `actaId, number, type, courseId, examId, teacherId, status, date, counts, results[]{studentId, grade, result}` | `GET /courses/{courseId}/results` |
| `teacher.acta-annulled.v1` | Al anular un acta | `actaId, number, courseId, annulledAt, reason` | `GET /courses/{courseId}/results` (el acta anulada ya no cuenta) |
| `teacher.exam-created.v1` | Al crear un examen | `courseId, examId, type, name, date, startTime, durationMinutes, modality` | Sin ruta para servicios: el evento trae los datos |

## Qué pueden consultar otros módulos (solo lectura)

Con un service token de un módulo habilitado (`SERVICE_MODULES`: hoy `student`, `analytics`, `academic`). Escribir sigue siendo solo del docente.

| Dato | Ruta (gateway: `/api/v1/teacher/...`) |
|---|---|
| Resultado final de un alumno / de todo un curso | `GET /students/{studentId}/results?courseId=` · `GET /courses/{courseId}/results` |
| Asistencia y notas de un alumno en un curso | `GET /students/{studentId}/courses/{courseId}/attendance` · `.../grades` |
| Clases y asistencia de un curso (porcentaje y condición REGULAR/LIBRE por alumno) | `GET /courses/{courseId}/attendances` · `.../attendances/{fecha}` · `.../attendance-summary` |
| Exámenes de un curso y sus notas | `GET /courses/{courseId}/exams` · `.../exams/{examId}` · `.../exams/{examId}/grades` |
| Planilla de notas completa del curso | `GET /courses/{courseId}/grades` |
| Actas de cursada y de final (con resultados por alumno) | `GET /actas?courseId=&periodId=&studentId=&type=&status=` · `GET /actas/{actaId}` |

## A tener en cuenta

- **Permisos para releer:** esas rutas piden un service token de un módulo habilitado. Si otro grupo las necesita, avísennos y lo sumamos a `SERVICE_MODULES`.
- **Cambios en exámenes:** hoy no publicamos evento al editar o cancelar un examen, solo al crearlo. Si alguien lo necesita, avísenos.
- **Nombres provisorios:** los `eventType` todavía pueden cambiar hasta confirmarlos en el catálogo de CORE.
