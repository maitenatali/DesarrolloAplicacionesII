# teacher-service (Portal Docente · UADEnet)

Flask 3 · SQLAlchemy 2 · Alembic · PostgreSQL · Pydantic v2 · SpecTree. Owns **attendance, exams, grades and actas**.
Full design: [docs/BACKEND_DESIGN.md](docs/BACKEND_DESIGN.md). Working rules for contributors: [CLAUDE.md](CLAUDE.md).

## Quick start

```bash
cp .env.example .env            # defaults: dev auth + mock integrations
docker compose up --build       # postgres + api (runs migrations) + outbox-worker
curl localhost:8080/api/v1/health/ready
```

Without Docker: `pip install -e ".[dev]"`, point `DATABASE_URL` at any PostgreSQL ≥ 15, then
`flask db upgrade && flask seed && flask run -p 8080` (use `gunicorn wsgi:app` on Linux).

- Swagger UI: `/apidocs` · OpenAPI JSON: `/apidocs/openapi.json` (`make openapi` writes `docs/openapi.json`).
- Local auth (`AUTH_VERIFIER=dev`): send `X-Dev-User: docente-123` (optional `X-Dev-Roles`).
  Service routes accept `Authorization: Bearer <one of SERVICE_TOKENS>`.
- Existing Supabase DB created from `schema.sql`: run `flask db stamp 0001` once, then `flask db upgrade`.
- Run exactly **one** `flask outbox-worker` (events are delivered at-least-once; consumers dedupe on `eventId`).

## Tests

Tests need a real PostgreSQL (partial indexes, views, advisory locks, `ON CONFLICT`). The suite uses, in order:
`$TEST_DATABASE_URL` → testcontainers (`postgres:16`, needs Docker) → `pixeltable-pgserver` (pip-installable embedded
Postgres, for machines without Docker).

```bash
pip install -e ".[dev]" pixeltable-pgserver   # last one only if you have no Docker
make test        # pytest --cov (gate: 85 %)
make lint
```

## Status vs. the roadmap (design §18)

| Phase | State |
|---|---|
| 0 Skeleton (config, models, migrations, errors, logging, health, Swagger, docker) | done |
| 1 Auth + integrations (introspection/dev/JWT verifiers, mock + live adapters, courses/roster endpoints) | done |
| 2 Exams, attendance, grades, outbox + dispatcher | done |
| 3 Actas (numbering, FINAL/CURSADA, sync, retry, annulment, locks, results) | done |
| 4 Frontend cutover; BFF placeholders (`/calendar`, `/profile`, …) | **not started** (outside this repo) |
| 5 Go live (real CORE/GA/directory credentials, gateway HMAC, JWT claims) | blocked on the [OPEN] items in design §19 |

`[OPEN]` items use the documented defaults and carry a `TODO(<team>)` comment in code (grep for `TODO(`).
`0001_baseline` was reconstructed from the design's models/constraints because `db/schema.sql` was not available:
diff it against the real `schema.sql` before running it on an existing database.
