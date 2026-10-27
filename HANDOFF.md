# HANDOFF — Portal Docente UADEnet (checkpoint 2026-10-26)

## Estado actual
- Backend `backend/` (Flask `teacher-service`) alineado con: TPO (`data/TPO - DEA II 2Q 2026.pdf`, módulo 2 Portal del Docente),
  planillas de otros grupos (`data/*.xlsx`) y OpenAPI real de CORE (https://core-api-production-e458.up.railway.app/docs, `/docs-json`).
- Tests: **142/142 verdes**, cobertura 95 %, `ruff` limpio, **mypy 0 errores sobre todo `app/`** (`make lint` ahora corre `mypy app`).
- 3 tests integrales E2E con JWT reales: `backend/tests/integration/test_e2e_{1_auth,2_teacher_flow,3_integrations}.py`
  (2 y 3 verifican que se ejercita el 100 % de las rutas del servicio y del simulador CORE).
- Smoke real hecho: Postgres Docker + `flask db upgrade` + `flask seed` + gunicorn 2 workers → login/me/courses/actas/calendar/wallet 200.
- **Nada commiteado.** Rama `full_stack_integration`. `data/` y `CLAUDE.md` raíz sin trackear; `backend/CLAUDE.md` borrado (git rm).
- venv local: `backend/.venv` (gitignored), deps `pip install -e '.[dev]'`.

## Decisiones tomadas (importan para seguir)
- **Entrega actual SIN conexión con otros módulos** (decisión del usuario). Todo en mock, pero con shapes de contratos reales.
- **Simulador de CORE in-process** `backend/app/mock_core/` (`MOCK_CORE_ENABLED=true`): mismos paths/payloads que CORE:
  `POST /api/v1/auth/{login,refresh,logout}`, `GET /api/v1/auth/me`, `GET /.well-known/jwks.json`, `POST /internal/v1/service-auth/token`,
  `GET /api/v1/wallets/me`, `GET .../transactions`, `POST .../top-ups` (Idempotency-Key), `/api/v1/notifications` (+unread-count, PATCH, read-all),
  `POST /internal/v1/notifications`. Clave RS256 persistida en DB (tabla `mock_core_signing_key`), refresh cookie httpOnly rotativa.
- Auth: `AUTH_VERIFIER=jwt` (RS256 local vía JWKS; con simulador usa key resolver local). iss `uadenet-core`, aud `uadenet` (TODO confirmar con CORE).
- Roles CORE/Backoffice: `TEACHER`, `STUDENT`, `ACADEMIC_ADMIN`, `ADMIN_STAFF`, `ADMIN_IT`. Identidad docente = JWT `sub` = UUID Backoffice = GA `docenteId` (sin heurística email).
- IDs fixtures UUID: María Gómez `5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034` (curso 42), Carlos Díaz `7c2f1a90-…-0a1f4d6e2b34` (curso 43),
  Juan Pérez `ba310c57-a684-4dbf-a4a4-905fcfbefa08`, Lucas `c3a1e0d2-…4d57`, Ana `d4b2f1e3-…5e58`, admin `a0000000-0000-4000-8000-000000000001`.
- Usuarios demo (`flask seed`), pass `Uade2026!`: maria.gomez@, carlos.diaz@, juan.perez@, secretaria.academica@ (uade.edu.ar). Docentes arrancan con saldo 15000.00.
- Directorio alumnos/docentes = Backoffice `GET /api/v1/users/{userId}` (live adapter); usado en roster, `/me` (nombre, legajo) y `teacherName` de actas.
- Al publicar nota nueva/cambiada → notificación CORE al alumno (`TEACHER_EXAM_RESULT_PUBLISHED`, actionUrl `/student/courses/{c}/exams/{e}`) vía outbox `kind=NOTIFICATION`.
- Acta FINAL → evento por alumno `teacher.course-result-published.v1` (shape Analítica; `siteId` null, TODO GA).
- Envelope eventos: correlationId UUID obligatorio (X-Correlation-Id no-UUID se reemplaza), actor.type user|service|system, source `teacher`.
- `GET /calendar` (exámenes propios + turnos GA + eventos académicos + comedor) y `GET /purchases` (Tienda) con datos mock (`integrations/campus_mock.py`).
- Errores problem+json ahora incluyen `instance`.

## Archivos tocados (backend/)
- Nuevos: `app/mock_core/{__init__,keys,schemas,service,routes}.py`, `app/models/mock_core.py`, `migrations/versions/0003_mock_core_and_outbox_kind.py`,
  `app/integrations/{notifications,campus_mock}.py`, `app/{routes,schemas,services}/calendar*.py`, `tests/integration/test_e2e_*.py`.
- Modificados clave: `app/config.py` (jwt default, mock core, service_modules, notifications_mode), `app/security/{principal,decorators,course_access}.py`,
  `app/security/verifiers/{__init__,jwt,dev,introspect}.py`, `app/integrations/{base,factory,fixtures,student_directory_live,academic_live}.py`,
  `app/services/{event,grade,acta,course,attendance,exam}_service.py`, `app/models/{__init__,outbox}.py`, `app/errors.py`, `app/logging.py`,
  `app/__init__.py` (bug: `import logging` sombreado → `from logging import getLogger`; registra calendar + mock_core),
  `app/routes/_common.py` (`validated()` reemplaza `request.context`), todas las rutas, `app/seed.py` (+`load_mock_core_seed`), `app/cli.py`,
  `.env.example`, `docker-compose.yml` (seed al arrancar), `Makefile`, `README.md`, `docs/BACKEND_DESIGN.md` (§0.1 + D22–D26), `docs/openapi.json` (41 paths), tests existentes adaptados.
- Raíz: `CLAUDE.md` nuevo (movido desde backend y reescrito).
- Notas de trabajo: `~/.claude/jobs/d225f2a2/tmp/findings.md` (contratos CORE y de otros módulos resumidos); spec CORE en `.../tmp/core_openapi.json`.

## Tarea en curso
Ninguna abierta. Último trabajo: limpieza de mypy (36 → 0) con tests en verde.

## SIGUIENTE PASO
1. Confirmar con el usuario si commitear (rama `full_stack_integration`; incluir o no `data/`). Si sí: `git add` + commit con mensaje convencional.
2. Empezar **frontend en React JS** (carpeta `frontend/` en raíz). Leer primero `CLAUDE.md` raíz, `backend/docs/BACKEND_DESIGN.md` §0.1 y §17, y `mockup_pantallas/*.html` (pantallas a implementar).
   Base: Vite + React JS; proxy `/api/v1/teacher` → `http://localhost:8080/api/v1` (rewrite) y `/api/v1/auth|wallets|notifications` + `/.well-known` → `http://localhost:8080`.
   Backend local: `cd backend && cp .env.example .env && make up` (o venv + `flask db upgrade && flask seed && flask run -p 8080`). Swagger: `/apidocs`.
