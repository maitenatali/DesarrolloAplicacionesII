# HANDOFF — Portal Docente UADEnet (checkpoint 2026-10-26, frontend)

## Estado actual
- Backend `backend/`: 142 tests verdes, ruff + mypy limpios. Ver checkpoint anterior en git history / `docs/BACKEND_DESIGN.md` §0.1.
- **Frontend `frontend/` hecho**: React 19 + Vite 6 + Redux Toolkit/RTK Query + React Router 7. Las 22 pantallas de
  `mockup_pantallas/` replicadas 1:1 y conectadas al backend (21 rutas; login y recuperar contraseña públicas).
  6 tests Vitest verdes, `npm run build` OK. Smoke en Chrome: las 21 rutas renderizan sin errores de consola;
  probados end-to-end: login, cargar saldo, guardar asistencia, crear examen, generar acta de cursada.
- **Nada commiteado.** Rama `full_stack_integration`.

## Decisiones tomadas
- CSS de cada mockup extraído y aislado bajo `.pg-<id>` (`tools/extract_mockups.py`, salida commiteada) → fidelidad 1:1 sin choques.
- Íconos SVG deduplicados en `src/components/icons.generated.jsx` (i1..i118, numeración estable).
- Header/sidebar comunes en `AppShell` (el markup era idéntico en todos los mockups).
- Simulador CORE: se agregó `POST /api/v1/auth/password/forgot` (existe en CORE real; 202 siempre). E2E 3 lo ejercita.
- Seed del simulador: 4 notificaciones demo por docente (`app/seed.py::TEACHER_DEMO_NOTIFICATIONS`).
- Perfil: datos de contacto y foto en localStorage (`TODO(Backoffice)`: no hay endpoint). Sedes: catálogo provisorio `TODO(GA)`.
- Nueva acta agrega tipo (FINAL/CURSADA) + examen final; detalle de acta agrega anular / reintentar sync / PDF (jsPDF, lazy).
- Docker: `frontend/Dockerfile` + `nginx.conf` (mismo proxy que Vite) y servicio `web` (puerto 3000) en `backend/docker-compose.yml`.

## Entorno de esta sesión (para limpiar)
- Entorno temporal de esta sesión ya limpiado (contenedor borrado; `backend/.env` eliminado, crearlo con `cp .env.example .env`).

## SIGUIENTE PASO
1. Confirmar con el usuario si commitear (incluir o no `data/`).
2. Revisión visual fina pantalla por pantalla contra los mockups (mobile incluido).
3. Fase 5: credenciales reales de CORE/GA (cambiar destino del proxy y `INTEGRATIONS_MODE=live`).
