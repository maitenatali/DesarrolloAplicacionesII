# Portal Docente · UADEnet (TPO Desarrollo de Aplicaciones II, 2Q 2026)

Módulo 2 "Portal del Docente". Repo = `backend/` (Flask, este servicio `teacher-service`) + `frontend/` (React JS, próximo)
+ `mockup_pantallas/` (mocks HTML 1ª entrega) + `data/` (enunciado TPO y planillas de flujo de datos de los otros grupos).

## Alcance de la entrega actual
- Backend + frontend + DB funcionando **SIN conexión con los demás módulos**. Toda integración corre en `mock`,
  pero con los contratos reales (CORE `/docs`, planillas de Backoffice, Gestión Académica, Eventos, Comedor, Analítica).
- CORE se simula localmente (`backend/app/mock_core`, `MOCK_CORE_ENABLED=true`): login, JWKS, refresh, wallet,
  notificaciones, service tokens. Mismos paths/payloads que CORE → pasar a CORE real = cambiar URL/config.
- Usuarios demo (`flask seed`): `maria.gomez@uade.edu.ar` (docente, curso 42), `carlos.diaz@uade.edu.ar` (docente, curso 43),
  `juan.perez@uade.edu.ar` (alumno), `secretaria.academica@uade.edu.ar` (ACADEMIC_ADMIN). Password: `Uade2026!`.

## Fuentes de verdad (orden)
1. `data/TPO - DEA II 2Q 2026.pdf` (requisitos).
2. CORE OpenAPI: https://core-api-production-e458.up.railway.app/docs (auth, wallet, eventos, notificaciones, gateway).
3. Planillas `data/*.xlsx` (contratos de otros módulos). 4. `backend/docs/BACKEND_DESIGN.md` (§0.1 = últimos cambios).

## Contrato con el ecosistema (no inventar otro)
- IDs de personas = UUID de Backoffice = `sub` del JWT = `docenteId` en GA. Nunca email/legajo como clave.
- Roles: `TEACHER`, `STUDENT`, `ACADEMIC_ADMIN`, `ADMIN_STAFF`, `ADMIN_IT`. Permisos `{modulo}:{recurso}:{accion}`.
- Tokens: JWT RS256, validación local por JWKS. Service tokens `kind=service` (`/internal/v1/service-auth/token`).
- Gateway CORE: `/api/v1/teacher/*` → nuestro `/api/v1/*`. Eventos: `POST /internal/v1/events`, envelope CORE
  (`correlationId` UUID, `source=teacher`, tipos `teacher.<entidad>-<accion>.v1` en `app/constants.py`).
- Dinero: string decimal `"1500.00"` + `currency`. Notas: número JSON (Decimal internamente). Fechas ISO 8601.
- Errores: `application/problem+json` con `code` estable, `detail` en español, `correlationId`, `instance`.

## Backend — comandos (desde `backend/`)
`make up` (docker compose: db + api + worker; migra y seedea) · `make migrate` · `make seed` · `make test` · `make lint` · `make openapi` · `make outbox`
Local sin Docker para la API: `python -m venv .venv && .venv/bin/pip install -e '.[dev]'`, copiar `.env.example` a `.env`.
Tests: PostgreSQL 16 real vía testcontainers (necesita Docker). E2E: `pytest tests/integration/test_e2e_*.py`.

## Reglas de código (backend)
- Código, identificadores y claves de API en inglés. Columnas DB y VALORES de enums en español (`APROBADO`, `PRESENTE`).
- Capas: routes (finas) → services (reglas, transacciones) → models; integraciones solo vía ABCs en `app/integrations/base.py`.
- Routes no tocan `db.session` ni `requests`. Services no importan `flask.request`. Objetos ORM no salen de services.
- Nunca `float` para notas ni dinero; `Decimal`. Nunca `datetime.now()`/`date.today()`: usar `app/time.py`.
- Toda llamada HTTP saliente con timeout; POST nunca se reintenta automáticamente.
- Red FUERA de transacciones de escritura. Sync GA y despacho de eventos DESPUÉS del commit.
- Eventos y notificaciones: encolar en `outbox_event` en la MISMA transacción del cambio de negocio.
- Cambios de DB: migración Alembic escrita a mano (índices parciales, vistas). Mantener verde `tests/test_schema_matches_models.py`.
- Errores: lanzar subclases de `AppError` con `code` estable; nunca JSON de error ad-hoc.
- Comportamiento marcado [OPEN] en el diseño: usar el default indicado y dejar `TODO(<equipo>)`.
- Toda ruta tiene modelos Pydantic de request/response y aparece en Swagger (`/apidocs`).
- `app/mock_core` es un simulador: no agregar lógica de negocio docente ahí.
- Explicar simple al usuario: es un equipo de estudiantes.

## Definition of done (por endpoint)
Schema · service · route · OpenAPI · tests de aceptación (diseño §15.3) · códigos de error (§13.3) · cubierto por los E2E.

## Frontend (próximo, React JS)
Consumirá `/api/v1/teacher/*` (proxy de Vite → `http://localhost:8080/api/v1`) y CORE (`/api/v1/auth`, `/wallets`,
`/notifications`; en esta entrega los sirve el simulador en el mismo backend). Ver diseño §17. Tipos desde `backend/docs/openapi.json`.
