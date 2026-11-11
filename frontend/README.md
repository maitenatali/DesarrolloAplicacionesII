# teacher-portal (frontend · Portal Docente UADEnet)

React 19 + Vite 6 + Redux Toolkit (RTK Query) + React Router 7. Replica 1:1 las pantallas de `../mockup_pantallas`
y consume el backend `teacher-service` (y CORE, que en esta entrega simula el mismo backend).

## Levantar

```bash
npm install
npm run dev                                   # http://localhost:5173 (backend en http://localhost:8080)
BACKEND_URL=http://localhost:8090 npm run dev # si el backend corre en otro puerto
npm test                                      # Vitest
npm run build                                 # build de producción en dist/
```

Usuarios demo (password `Uade2026!`): `maria.gomez@uade.edu.ar`, `carlos.diaz@uade.edu.ar`.
Ver `../ejecucion.md` para levantar todo junto (también con Docker: servicio `web` en http://localhost:3000).

## Cómo está armado

| Carpeta | Qué hay |
|---|---|
| `src/api/` | `api.js`: todos los endpoints con RTK Query (caché + invalidación por tags). `baseQuery.js`: agrega el Bearer, renueva el token con la cookie de refresh ante un 401 y normaliza errores `problem+json`. |
| `src/features/` | `auth` (access token solo en memoria) y `ui` (mensajes "flash" entre pantallas). |
| `src/pages/` | Una pantalla por archivo (Login, Dashboard, MyCourses, CourseDetail, Students, Attendance, AttendanceHistory, Grades, Exams, ExamForm, ExamDetail, Actas, ActaNew, ActaDetail, Calendar, Notifications, Purchases, PurchaseDetail, Account, TopUp, Profile). |
| `src/components/` | `AppShell` (header + sidebar), `CourseNav` (breadcrumb, hero, tabs del curso), `Pagination`, `icons.generated.jsx`. |
| `src/styles/pages/` | CSS de cada mockup, **aislado** bajo `.pg-<id>` (ej. `.pg-07`) para que no choquen entre pantallas. |
| `tools/extract_mockups.py` | Genera `styles/pages/*.css` e `icons.generated.jsx` desde los HTML de los mockups. **No editar esos archivos a mano**: corregir el mockup y correr `npm run extract-mockups`. |

Rutas: `/login`, `/recuperar-contrasena`, `/`, `/cursos`, `/cursos/:id` (+ `/estudiantes`, `/asistencia`,
`/asistencia/historial`, `/calificaciones`, `/examenes`, `/examenes/nuevo`, `/examenes/:examId`, `/examenes/:examId/editar`),
`/actas`, `/actas/nueva`, `/actas/:id`, `/calendario`, `/notificaciones`, `/compras`, `/compras/:id`, `/cuenta`,
`/cuenta/cargar-saldo`, `/perfil`.

Proxy (Vite en dev, nginx en Docker): `/api/v1/teacher/*` → backend `/api/v1/*`; `/api/v1/*` y `/.well-known/*` → CORE
(hoy el simulador del mismo backend). Pasar a CORE real = cambiar el destino del proxy.

## Diferencias con los mockups (a propósito)

- Los datos salen de la API; donde el mockup tenía datos que **ningún módulo publica** (fecha de nacimiento, domicilio,
  departamento, menú del comedor, etc.) se muestran los que sí existen. Perfil: correo personal, teléfono y foto se
  guardan en el navegador hasta que Backoffice publique un endpoint (`TODO(Backoffice)` en `pages/Profile.jsx`).
- Nueva acta pide el **tipo** (Final/Cursada) y el **examen final**, como exige el backend (diseño §17.3).
- Detalle de acta agrega **Anular acta** y **Reintentar sincronización**; "Descargar PDF" genera un PDF real (jsPDF).
- Calificaciones: una columna por examen del curso; `A` en una celda = ausente.
- Cargar saldo: la tarjeta nunca sale del navegador; a CORE solo va un token simulado. Tarjeta terminada en `0002` =
  rechazada, en `0004` = pendiente.
- Sedes: GA todavía no publica el catálogo; `lib/domain.js` usa uno provisorio (`TODO(GA)`).
