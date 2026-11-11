# Ejecución local — Portal Docente UADEnet

Cómo levantar en tu máquina todos los servicios del proyecto, con Docker o con comandos sueltos.

> **Estado de esta entrega:** el proyecto corre **sin conexión con los demás módulos**. CORE (login, JWKS, wallet,
> notificaciones) lo simula el propio backend (`MOCK_CORE_ENABLED=true`) y todas las integraciones
> (Gestión Académica, Backoffice, Eventos, Comedor, Tienda) están en modo `mock`. No hace falta ninguna credencial externa.
>
> El frontend (React JS) está en `frontend/`; ver [§6](#6-frontend).

---

## 1. Servicios del proyecto

| Servicio | Qué es | Puerto | Obligatorio |
|---|---|---|---|
| `db` | PostgreSQL 16 | 5432 | Sí |
| `api` | Backend Flask `teacher-service` + simulador de CORE (gunicorn) | 8080 | Sí |
| `outbox-worker` | Proceso que despacha eventos y notificaciones encolados en `outbox_event` | — | No en local (ver nota) |
| `web` | Frontend React (Vite en desarrollo, nginx en Docker) | 5173 (dev) / 3000 (Docker) | Sí, para usar la app |

Nota sobre el worker: con `EVENTS_INLINE_DISPATCH=true` (default de `.env.example`) la API intenta despachar
los eventos apenas hace commit, así que en local podés no correrlo. Si lo corrés, que sea **una sola instancia**.

## 2. Requisitos

- **Opción Docker:** Docker Engine + Docker Compose v2 (`docker compose version`).
- **Opción sin Docker:** Python **3.12 o superior**, PostgreSQL **15 o superior** (o Docker solo para la base), `make` (opcional).
- **Frontend sin Docker:** Node.js **20 o superior** y npm.
- Puertos libres: `5432` (Postgres) y `8080` (API).

Todos los comandos de este documento se corren desde la carpeta `backend/`, salvo que se indique otra cosa.

```bash
cd backend
cp .env.example .env     # solo la primera vez; los defaults ya sirven para local
```

---

## 3. Opción A — Todo con Docker (recomendada)

Levanta base de datos, API, worker y frontend. La API aplica las migraciones y carga los datos demo (`flask seed`) al arrancar.
Al terminar, abrí **http://localhost:3000** e ingresá con un usuario demo.

```bash
cd backend
cp .env.example .env          # si no lo hiciste antes
make up                       # equivale a: docker compose up --build
```

Variantes útiles:

```bash
docker compose up --build -d              # en segundo plano
docker compose logs -f api                # ver logs de la API
docker compose logs -f outbox-worker      # ver logs del worker
docker compose up --build db api          # sin el worker ni el frontend
docker compose logs -f web                # ver logs del frontend (nginx)
docker compose ps                         # estado de los contenedores
```

Apagar:

```bash
docker compose down        # apaga y conserva los datos
docker compose down -v     # apaga y BORRA la base (próximo `up` arranca de cero)
```

> En Docker, `DATABASE_URL` se sobreescribe automáticamente para apuntar al contenedor `db`;
> el valor de `.env` (con `localhost`) solo se usa en la opción sin Docker.

Seguí en [§5 Verificar que todo funciona](#5-verificar-que-todo-funciona).

---

## 4. Opción B — Comandos individuales (sin Docker para la API)

### 4.1 Base de datos

Elegí una:

**a) Postgres en Docker (lo más simple):**

```bash
docker run -d --name teacher-db \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=teacher \
  -p 5432:5432 postgres:16
```

o, usando el compose del proyecto, solo el servicio de base: `docker compose up -d db`.

**b) Postgres instalado en tu máquina:**

```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres createdb teacher
```

En ambos casos queda accesible con el `DATABASE_URL` por defecto de `.env`:
`postgresql+psycopg://postgres:postgres@localhost:5432/teacher`. Si usás otro usuario/clave/base, editá esa línea.

### 4.2 Entorno de Python

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]' python-dotenv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

`python-dotenv` hace que `flask` lea `.env` solo. Si preferís no instalarlo, exportá las variables a mano
en cada terminal antes de correr los comandos:

```bash
set -a; source .env; set +a
```

### 4.3 Migraciones y datos demo

```bash
flask db upgrade      # crea/actualiza las tablas (make migrate)
flask seed            # usuarios demo, cursos, exámenes, saldo, clave RS256 del simulador (make seed)
```

`flask seed --no-acta` carga lo mismo pero sin generar el acta de ejemplo.

**Qué datos carga** depende de `MOCK_DATASET` (también define qué devuelven los mocks de GA y Backoffice):

| `MOCK_DATASET` | Uso | Contenido |
|---|---|---|
| `base` (default) | tests | Curso 42 con 3 alumnos, 4 clases, acta FINAL `2026-001` (Apéndice B del diseño). |
| `demo` (docker compose) | demostraciones | 2° cuatrimestre 2026 hasta fines de octubre: curso 42 (María, 25 alumnos, 10 clases, parciales y recuperatorio corregidos, final programado), curso 43 (Carlos, 20 alumnos, 11 clases, parcial y TP corregidos, un examen cancelado) y curso 30 del 1° cuatrimestre cerrado (16 alumnos, actas `2026-001` CURSADA, `2026-002` FINAL anulada y `2026-003` FINAL). Todos los alumnos pueden loguearse con `nombre.apellido@uade.edu.ar` / `Uade2026!`. |

El dataset demo es determinístico (mismos datos en cualquier PC).

Cambiar de dataset (la base y los mocks tienen que usar el mismo, así que se borra la base):

```bash
cd backend
docker compose down -v                          # borra la base actual
MOCK_DATASET=base docker compose up -d --build  # o sin la variable: usa demo
```

Sin Docker: `MOCK_DATASET=base` o `MOCK_DATASET=demo` en `.env`, recrear la base y correr `flask db upgrade && flask seed`.
Si la base ya tenía datos, `flask seed` no hace nada.

### 4.4 API

Modo desarrollo (recarga automática al editar código):

```bash
flask run -p 8080 --debug
```

Modo "como producción" (Linux/macOS):

```bash
gunicorn -b 0.0.0.0:8080 -w 2 --timeout 60 wsgi:app
```

### 4.5 Worker de outbox (opcional, en otra terminal)

```bash
cd backend && source .venv/bin/activate
flask outbox-worker   # loop continuo; Ctrl+C para cortar
```

Otros comandos del outbox:

```bash
flask outbox-once              # despacha una sola tanda y termina (make outbox)
flask outbox-requeue --failed  # vuelve a encolar los eventos FAILED
flask outbox-prune --days 30   # borra eventos ya enviados con más de N días
```

### 4.6 Frontend

```bash
cd frontend
npm install                 # solo la primera vez
npm run dev                 # http://localhost:5173
```

El proxy de Vite manda `/api/v1/teacher/*` al backend (`/api/v1/*`) y `/api/v1/*` + `/.well-known/*` a CORE
(hoy el simulador del mismo backend). Por defecto apunta a `http://localhost:8080`; si la API corre en otro puerto:

```bash
BACKEND_URL=http://localhost:8090 npm run dev
```

(o copiá `frontend/.env.example` a `frontend/.env` y cambiá `BACKEND_URL`).

### 4.7 Resumen (4 terminales)

```bash
# Terminal 1 — base
docker compose up db

# Terminal 2 — API
cd backend && source .venv/bin/activate
flask db upgrade && flask seed && flask run -p 8080 --debug

# Terminal 3 — frontend
cd frontend && npm install && npm run dev

# Terminal 4 — worker (opcional)
cd backend && source .venv/bin/activate
flask outbox-worker
```

---

## 5. Verificar que todo funciona

```bash
curl localhost:8080/api/v1/health          # la API responde
curl localhost:8080/api/v1/health/ready    # la API + la base (incluye contadores del outbox)
```

Login contra el simulador de CORE y llamada a la API docente con el token:

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"maria.gomez@uade.edu.ar","password":"Uade2026!"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')

curl -H "Authorization: Bearer $TOKEN" localhost:8080/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" localhost:8080/api/v1/courses
curl -H "Authorization: Bearer $TOKEN" localhost:8080/api/v1/wallets/me
```

### URLs útiles

| Qué | URL |
|---|---|
| Swagger UI | http://localhost:8080/apidocs |
| OpenAPI JSON | http://localhost:8080/apidocs/openapi.json |
| Health | http://localhost:8080/api/v1/health/ready |
| JWKS del simulador | http://localhost:8080/.well-known/jwks.json |

En Swagger: hacé login en `POST /api/v1/auth/login`, copiá el `accessToken` y pegalo en **Authorize** como `Bearer <token>`.

### Usuarios demo (password `Uade2026!`)

| Email | Rol | Datos |
|---|---|---|
| `maria.gomez@uade.edu.ar` | TEACHER | Curso 42, saldo 15000.00 |
| `carlos.diaz@uade.edu.ar` | TEACHER | Curso 43, saldo 15000.00 |
| `juan.perez@uade.edu.ar` | STUDENT | Alumno (recibe notificaciones de notas) |
| `secretaria.academica@uade.edu.ar` | ACADEMIC_ADMIN | Lectura de cualquier curso |

---

## 6. Frontend

React 19 + Vite + Redux Toolkit (RTK Query) + React Router. Replica 1:1 las pantallas de `mockup_pantallas/`.

| Modo | Comando | URL |
|---|---|---|
| Docker (con todo lo demás) | `cd backend && make up` | http://localhost:3000 |
| Desarrollo | `cd frontend && npm install && npm run dev` | http://localhost:5173 |
| Build de producción | `cd frontend && npm run build && npm run preview` | http://localhost:4173 |

Entrá con `maria.gomez@uade.edu.ar` / `Uade2026!`. Recorrido sugerido: Inicio → Mis cursos → curso
"Desarrollo de Aplicaciones II" → Asistencia / Calificaciones / Exámenes → Actas → Nueva acta → Cuenta
institucional → Cargar saldo.

Cargar saldo es simulado: la tarjeta guardada se aprueba; con "Otra tarjeta", un número terminado en `0002` se
rechaza y uno terminado en `0004` queda pendiente.

Más detalle de la estructura en `frontend/README.md`.

---

## 7. Tests y calidad de código

Frontend (desde `frontend/`): `npm test` (Vitest) y `npm run build`.

Backend: desde `backend/` con el venv activo. Los tests usan un PostgreSQL real; lo levantan solos vía testcontainers
(**necesita Docker corriendo**). Sin Docker: `pip install pixeltable-pgserver` o definir `TEST_DATABASE_URL`.

```bash
make test                               # 142 tests + cobertura (mínimo 85 %)
pytest tests/integration/test_e2e_*.py  # los 3 tests end-to-end con JWT reales
make lint                               # ruff + formato + mypy
make openapi                            # regenera docs/openapi.json
```

---

## 8. Problemas comunes

| Síntoma | Causa / solución |
|---|---|
| `port is already allocated` / `address already in use` en 5432 | Ya tenés otro Postgres. Pará ese servicio o cambiá el puerto (`-p 5433:5432` y `DATABASE_URL=...@localhost:5433/teacher`). |
| Mismo error en 8080 | Otro proceso usa el puerto: `lsof -i :8080`. Cambiá con `flask run -p 8081` y levantá el frontend con `BACKEND_URL=http://localhost:8081 npm run dev`. |
| El frontend queda en "Cargando…" o da error de conexión | La API no está levantada o `BACKEND_URL` apunta a otro puerto. Probá `curl localhost:8080/api/v1/health`. |
| Puerto 3000 ocupado (Docker) | Cambiá `ports: ["3000:80"]` del servicio `web` en `backend/docker-compose.yml`. |
| `connection refused` al hacer `flask db upgrade` | La base no está levantada o `DATABASE_URL` apunta mal. Probá `docker compose ps`. |
| La app falla al arrancar listando variables | `.env` no se cargó o tiene un valor inválido. Instalá `python-dotenv` o `set -a; source .env; set +a`. |
| `401` en todas las llamadas | Falta el header `Authorization: Bearer <token>` o el token venció (15 min). Volvé a hacer login o usá `POST /api/v1/auth/refresh`. |
| Login devuelve error / no hay cursos | No se corrió `flask seed`. |
| Quiero empezar de cero | Docker: `docker compose down -v && make up`. Manual: borrar y recrear la base, después `flask db upgrade && flask seed`. |
| Tests fallan con error de Docker | testcontainers necesita el daemon de Docker activo y tu usuario en el grupo `docker`. |
