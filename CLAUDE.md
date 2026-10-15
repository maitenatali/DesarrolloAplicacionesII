# CLAUDE.md — Portal Docente (UADEnet)

Contexto del proyecto para retomar el trabajo. Última actualización: 14/10/2026.

## Qué es

TPO de **Desarrollo de Aplicaciones II** (UADE, prof. Joaquín Timerman). Todo el curso construye **UADEnet**, una plataforma de microservicios; cada grupo hace un módulo. **Este grupo hace el Portal Docente** (microservicio `teacher`).

El docente entra con su mail, gestiona sus cursos (no los crea: los da de alta Gestión Académica), toma asistencia, crea exámenes, carga notas, genera actas, ve el calendario académico, sus notificaciones, compras y saldo.

**Entregas:**
1. ✅ Mocks de cada vista + flujo de datos (`mockup_pantallas/`).
2. ⏳ **Módulo funcional con integraciones mockeadas** ← estamos acá.
3. Módulo integrado al resto + README + diagrama de arquitectura.

Comunicación con el usuario: en español, explicaciones simples; no da por sabidos conceptos técnicos.

## Estructura del repo

```
mockup_pantallas/   prototipos HTML de la primera entrega
db/                 schema.sql (tablas + vistas) y seed.sql (datos de prueba) para Supabase
backend/            microservicio Spring Boot (teacher-service)
docs/               modelo de datos, guía de entities, plan de la segunda entrega
```

Documentos clave:
- [docs/plan-segunda-entrega.md](docs/plan-segunda-entrega.md): checklist por módulo de todo lo pendiente.
- [docs/modelo-de-datos.md](docs/modelo-de-datos.md): diagrama ER y decisiones de datos.
- [docs/guia-backend-entities.md](docs/guia-backend-entities.md): mapeo tabla → entity, convenciones.
- [backend/README.md](backend/README.md): cómo correr el backend.

Fuera del repo:
- **Frontend** React + TypeScript + Vite: `C:\Users\Admin\Downloads\portal-docente-uadenet.zip` (todavía no subido). Hoy guarda asistencia, notas, exámenes y actas en localStorage; `src/store/teacherStore.ts` marca cada punto a reemplazar por el backend. `src/api/endpoints.ts` lista cada integración (`live` / `contract` / `placeholder`).
- **Contrato de Gestión Académica**: `C:\Users\Admin\Downloads\CONTRATO_PORTALES_ALUMNOS_Y_DOCENCIA.md`.
- **API de CORE** (Swagger): https://core-api-production-e458.up.railway.app/docs — spec JSON en `/docs-json`.
- **Pendientes con Gestión Académica** (doc compartido): https://claude.ai/code/artifact/a97b2d02-827f-426f-976a-0f5101196435

## Stack y comandos

- Java 21 (`C:\Program Files\Java\jdk-21.0.12.1`), Spring Boot 3.5.6, Maven, Lombok, springdoc (Swagger).
- Base: PostgreSQL en **Supabase** (Session pooler, región `aws-1-ca-central-1`).
- IDE: IntelliJ con la raíz del repo abierta; importa `backend/pom.xml` como módulo `teacher-service`.
- Maven **no está instalado** en el sistema: el usuario usa el de IntelliJ. `JAVA_HOME` no está definido; para usar Maven por terminal hay que exportarlo.

```bash
# desde backend/
mvn spring-boot:run          # levanta en :8080, Swagger en /swagger-ui.html
mvn clean package            # compila y genera target/teacher-service-0.1.0.jar
```

Configuración: `backend/.env` (no se sube; tiene la contraseña de Supabase). `application.yml` lo importa desde `backend/.env` o `.env`, según desde dónde se arranque. Plantilla en `backend/.env.example`.

## Decisiones tomadas

- **Un solo microservicio `teacher-service`**, separado por paquetes de dominio (`asistencia`, `examen`, `acta`). El gateway de CORE envía `/api/v1/teacher/X` a nuestro `/api/v1/X`.
- **Datos propios:** asistencia, exámenes, calificaciones y **actas**. Las actas son la **fuente oficial de nota final y condición** del alumno: Gestión Académica no quiere hacerse cargo. Igual se les envía el resultado con su `PUT .../inscripciones/{alumnoId}` (ya existe); si falla, el acta queda y se registra en `sync_error`.
- **El docente no crea cursos** (corrección del profe en la primera entrega).
- **Regularidad:** 75% de asistencia mínima; `JUSTIFICADO` no cuenta como falta; se calcula en la vista `asistencia_por_alumno` sobre las clases registradas.
- **Tipo de examen:** texto libre (`PARCIAL_1`, `TP_1`, `FINAL`...) + `nombre` para mostrar. Un examen activo por tipo y curso.
- **Aprobación:** nota ≥ 4.
- **Actas:** número `AÑO-correlativo` (`2026-001`); una vigente por curso y tipo; no se editan, se anulan con motivo y se genera otra. Copian materia, comisión, período, docente y nombre/legajo de cada alumno.
- **Ids externos:** `curso_id`, `asignatura_id`, `periodo_id` son `bigint` (Gestión Académica); `alumno_id`, `docente_id` son `varchar(50)` (ej. `alumno-456`). Sin claves foráneas.

## Convenciones del backend

- Las tablas las crea `db/schema.sql`. Hibernate está en `ddl-auto: validate`: **si cambia una tabla, primero el SQL y después la entity**.
- Fechas con hora: `OffsetDateTime` + `columnDefinition = "timestamptz"` (sin eso, la validación falla).
- Lombok: solo `@Getter`, `@Setter` y constructores. Nunca `@Data` en entities.
- Relaciones con cascada: `Clase` → `Asistencia` y `Acta` → `ActaDetalle`; usar `agregarAsistencia` y `agregarDetalle`. `Examen` no carga sus calificaciones: se piden por `CalificacionRepository`.
- Vistas `asistencia_por_alumno` y `resultado_por_alumno`: entities `@Immutable` con `@IdClass`, repositorios de solo lectura.
- **Las entities no salen por la API:** controllers con DTOs (`record`).
- Reglas únicas de la base → validar en el service antes de guardar; si se escapa, `DataIntegrityViolationException` → **409**.

## Resultados verificados (14/10/2026)

- `mvn clean package` compila sin errores.
- Prueba integral contra PostgreSQL 16 embebido (zonky), fuera del repo: `schema.sql` + `seed.sql` corren; la app arranca leyendo `.env` y pasa `validate`; crear examen + nota, rechazo de examen duplicado, asistencia en cascada con la vista recalculada, acta de cursada, sincronización y anulación, e historial que ignora actas anuladas. Todo OK.
- Conexión a Supabase: funciona fuera del Wi-Fi de UADE. **El Wi-Fi "UADE" (proxy) bloquea los puertos 5432 y 6543**: el TCP abre pero no responde. En la facu, usar hotspot del celular. También bloqueó la descarga de imágenes de Docker.

## Integraciones (estado)

| Módulo | Estado | Notas |
| --- | --- | --- |
| CORE: login, sesión, saldo, notificaciones | Real (en el frontend) | `/api/v1/auth/*`, `/api/v1/wallets/me*`, `/api/v1/notifications*` |
| CORE: eventos | Pendiente (backend) | `POST /internal/v1/events` con token de servicio (`POST /internal/v1/service-auth/token`, 15 min). `source: "teacher"`. Los tipos de evento deben estar dados de alta en el catálogo de CORE |
| CORE: validar token | Pendiente | JWKS en `/.well-known/jwks.json` |
| Gestión Académica | Contrato | Rutas `/planificacion/cursos`, `/periodos`, `/turnos-examen`, correlatividades. Sin filtro por docente. Prefijo final a confirmar (`/api/` vs `/api/v1/`) |
| Comedor, Tienda, Eventos, perfiles de alumno y docente | Inventadas (placeholder) | Faltan sus contratos; el profe marcó las rutas actuales como inexistentes |

Eventos que publicaremos (nombres provisorios, sin confirmar): `teacher.attendance-recorded.v1`, `teacher.grade-published.v1`, `teacher.exam-created.v1`, `teacher.acta-generated.v1`.

## Próximos pasos

### Ahora: services (en este orden)

Un paquete `dto/` por dominio con `record`s de entrada y salida. Services con `@Transactional`, que reciben el id del docente como parámetro (después saldrá del token).

1. **`ExamenService`**: listar por curso; crear (validar tipo duplicado con `existsByCursoIdAndTipoAndEstadoNot`); editar; cancelar (no borrar).
2. **`AsistenciaService`**: listar clases de un curso; guardar la asistencia de una fecha (crea o reemplaza la clase con sus asistencias); regularidad por curso (vista).
3. **`CalificacionService`**: notas de un examen y de un curso; guardar en lote (crear o actualizar por examen + alumno); validar 0–10 y ausente sin nota; no cargar notas en exámenes cancelados.
4. **`ActaService`**: listar (por docente y período); detalle; generar (próximo número, una vigente por curso y tipo, renglones en cascada, resultado según nota ≥ 4); anular con motivo; resultados por alumno (vista) para el Portal del Estudiante.
5. **Integraciones mock** (`integration/`): interfaces `AcademicClient`, `CoreEventsClient`, `StudentDirectoryClient` con implementación `mock` (datos del contrato) y `live`, elegidas con `app.integrations.mode`. `ActaService` usa `AcademicClient` para sincronizar y `CoreEventsClient` para publicar.
6. **Manejo de errores:** excepciones propias (no encontrado → 404, regla de negocio → 409, validación → 400) + `@RestControllerAdvice` con cuerpo JSON uniforme.

### Después: controllers

- Decidir los nombres de las rutas antes de empezar. La clase de APIs pide recursos en inglés, plural y minúscula, keys JSON en inglés `lowerCamelCase` y API versionada (`/api/v1/...`). El código y la base están en español: **pendiente decidir** si la API sigue la guía de la clase (recomendado, porque el profe la evalúa) o queda en español. Ejemplo en inglés: `GET /api/v1/courses/{courseId}/exams`, `PUT /api/v1/courses/{courseId}/attendances/{date}`, `POST /api/v1/actas`.
- Validación con `@Valid` en los DTOs de entrada.
- Documentar en Swagger (`@Operation`, `@Tag`).
- Seguridad con el token de CORE (`spring-boot-starter-oauth2-resource-server`).

### Pendientes del repo y del equipo

- `.gitignore` en la raíz con `.idea/`; commitear `backend/` (sin `.env`).
- Subir el frontend del zip al repo y conectarlo al backend.
- Borrar `holaaaa.txt` (archivo de prueba) y actualizar el README de la raíz.
- Corregir y subir el documento de flujo de datos (correcciones del profe).
- Pedidos a otros equipos: ver bloques 4 a 7 de [docs/plan-segunda-entrega.md](docs/plan-segunda-entrega.md).
