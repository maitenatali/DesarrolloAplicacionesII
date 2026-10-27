# teacher-service (Portal Docente · UADEnet)

Flask 3 · SQLAlchemy 2 · Alembic · PostgreSQL · Pydantic v2 · SpecTree. Owns **attendance, exams, grades and actas**.
Full design: [docs/BACKEND_DESIGN.md](docs/BACKEND_DESIGN.md). Working rules for contributors: [../CLAUDE.md](../CLAUDE.md).
This delivery runs **without the other UADEnet modules**: every integration is mocked with the real contracts and a
local CORE simulator (`MOCK_CORE_ENABLED=true`) provides login/JWKS/wallet/notifications (design §0.1).

## Quick start

```bash
cp .env.example .env            # defaults: JWT auth + local CORE simulator + mock integrations
docker compose up --build       # postgres + api (migrations + seed) + outbox-worker
curl localhost:8080/api/v1/health/ready
# log in like with CORE and call the teacher API with the token
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"maria.gomez@uade.edu.ar","password":"Uade2026!"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
curl -H "Authorization: Bearer $TOKEN" localhost:8080/api/v1/courses
```

Without Docker: `pip install -e ".[dev]"`, point `DATABASE_URL` at any PostgreSQL ≥ 15, then
`flask db upgrade && flask seed && flask run -p 8080` (use `gunicorn wsgi:app` on Linux).

- Swagger UI: `/apidocs` · OpenAPI JSON: `/apidocs/openapi.json` (`make openapi` writes `docs/openapi.json`).
- Demo users (password `Uade2026!`): `maria.gomez@uade.edu.ar` (TEACHER, course 42), `carlos.diaz@uade.edu.ar`
  (TEACHER, course 43), `juan.perez@uade.edu.ar` (STUDENT), `secretaria.academica@uade.edu.ar` (ACADEMIC_ADMIN).
- Service routes (`/results`): CORE service token from `POST /internal/v1/service-auth/token` with a client of
  `MOCK_CORE_SERVICE_CLIENTS`, or a static `SERVICE_TOKENS` value.
- Unit/integration tests still use `AUTH_VERIFIER=dev` (`X-Dev-User: <uuid>`); the E2E tests use real JWTs.
- Existing Supabase DB created from `schema.sql`: run `flask db stamp 0001` once, then `flask db upgrade`.
- Run exactly **one** `flask outbox-worker` (events are delivered at-least-once; consumers dedupe on `eventId`).

## Tests

Tests need a real PostgreSQL (partial indexes, views, advisory locks, `ON CONFLICT`). The suite uses, in order:
`$TEST_DATABASE_URL` → testcontainers (`postgres:16`, needs Docker) → `pixeltable-pgserver` (pip-installable embedded
Postgres, for machines without Docker).

```bash
pip install -e ".[dev]" pixeltable-pgserver   # last one only if you have no Docker
make test        # pytest --cov (gate: 85 %) — 142 tests, ~95 % coverage
pytest tests/integration/test_e2e_*.py   # the 3 end-to-end tests (auth / every teacher endpoint / events+notifications+wallet)
make lint
```

## Status vs. the roadmap (design §18)

| Phase | State |
|---|---|
| 0 Skeleton (config, models, migrations, errors, logging, health, Swagger, docker) | done |
| 1 Auth (RS256 JWT via JWKS; introspection/dev alternatives) + integrations (mock + live adapters) | done |
| 2 Exams, attendance, grades, outbox + dispatcher | done |
| 3 Actas (numbering, FINAL/CURSADA, sync, retry, annulment, locks, results) | done |
| 4 BFF `/calendar`, `/purchases`; local CORE simulator; student notifications | done (mock data) |
| 4b Frontend (React JS, `../frontend`) | done |
| 5 Go live (real CORE/GA/directory credentials, gateway HMAC, JWT claims) | blocked on the [OPEN] items in design §19 |

`[OPEN]` items use the documented defaults and carry a `TODO(<team>)` comment in code (grep for `TODO(`).
`0001_baseline` was reconstructed from the design's models/constraints because `db/schema.sql` was not available:
diff it against the real `schema.sql` before running it on an existing database.
