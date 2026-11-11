# Portal del Docente · UADEnet

TPO Desarrollo de Aplicaciones II — 2° cuatrimestre 2026 — **Módulo 2: Portal del Docente**.

Integrantes: Gorrini Rech, Tomas (1165821) · Natali, Maite (1197675) · Poggi Toledo, Dahiana Romina (1151380) ·
Regueira, Tomas (1150229) · Suazo Verger, Juan (1152309) · Varone, Maximo (1152377).

## Qué contiene

| Carpeta | Qué es |
|---|---|
| `backend/` | API REST en Python/Flask (`teacher-service`) + PostgreSQL 16. Incluye un **simulador de CORE** (login, JWKS, wallet, notificaciones). |
| `frontend/` | Aplicación web en React 19 + Vite + Redux Toolkit (RTK Query). Replica las pantallas de los mockups. |
| `mockup_pantallas/` | Mockups HTML de la 1ª entrega (se abren directo en el navegador). |
| `docs/` | Arquitectura y diseño del sistema. |
| `ejecucion.md` | Guía detallada de ejecución, variables, tests y problemas comunes. |

> **Importante:** en esta entrega el módulo corre **sin conexión con los demás módulos**. CORE y las integraciones
> (Gestión Académica, Backoffice, Eventos, Comedor) se simulan localmente con los mismos contratos.
> No hace falta ninguna credencial externa.

---

## Opción A — Con Docker (recomendada)

**Requisitos:** Docker Desktop (o Docker Engine + Docker Compose v2). Puertos libres: `3000`, `8080` y `5432`.

```bash
cd backend
cp .env.example .env          # Windows (PowerShell): copy .env.example .env
docker compose up --build     # o: make up
```

La primera vez tarda unos minutos (descarga imágenes e instala dependencias). La API aplica las migraciones
y carga los datos demo sola. Cuando termine:

- **Aplicación:** http://localhost:3000
- **Swagger de la API:** http://localhost:8080/apidocs

Para apagar: `docker compose down` (conserva los datos) o `docker compose down -v` (borra la base).

---

## Opción B — Sin Docker (modo desarrollo)

**Requisitos:** Python 3.12+, Node.js 20+ y npm, PostgreSQL 15+ (o Docker solo para la base).

**1. Base de datos** (una base `teacher`, usuario `postgres`, clave `postgres`, puerto 5432):

```bash
docker run -d --name teacher-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=teacher -p 5432:5432 postgres:16
```

**2. Backend** (terminal 1):

```bash
cd backend
cp .env.example .env
python -m venv .venv
# Linux/macOS:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate
pip install -e ".[dev]" python-dotenv
flask db upgrade          # crea las tablas
flask seed                # carga usuarios y datos demo
flask run -p 8080 --debug
```

**3. Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173
```

---

## Usuarios de prueba

Contraseña para todos: **`Uade2026!`**

| Email | Rol |
|---|---|
| `maria.gomez@uade.edu.ar` | Docente (curso "Desarrollo de Aplicaciones II") |
| `carlos.diaz@uade.edu.ar` | Docente (otro curso) |
| `secretaria.academica@uade.edu.ar` | Administración académica (lectura de todos los cursos) |
| `juan.perez@uade.edu.ar` | Alumno (no tiene acceso al portal docente) |

Recorrido sugerido: Inicio → Mis cursos → Desarrollo de Aplicaciones II → Asistencia / Calificaciones / Exámenes →
Actas → Nueva acta → Cuenta institucional → Cargar saldo.

## Verificar que la API funciona

```bash
curl http://localhost:8080/api/v1/health/ready
```

## Tests

```bash
cd backend && make test       # o: pytest   (necesita Docker corriendo: usa PostgreSQL real)
cd frontend && npm test
```

Más detalle (worker de eventos, datasets demo, problemas comunes): ver [`ejecucion.md`](ejecucion.md).
