# teacher-service (Portal Docente · UADEnet) — Flask backend

Source of truth: docs/BACKEND_DESIGN.md. Read the section you are implementing before coding.
Language: code, identifiers, API keys in English. DB columns/enum VALUES stay Spanish (see design §2.7, §7.3).
User-facing error `detail` strings: Spanish. Explain things simply to the user; they are a student team.

## Commands
make up | make migrate | make seed | make test | make lint | make openapi | make outbox

## Rules
- Layering: routes (thin) → services (rules, transactions) → models; integrations only via ABCs in app/integrations/base.py.
- Routes never touch db.session or requests. Services never import flask.request. ORM objects never leave services.
- Never use float for grades; Decimal only. Serialise grades as JSON numbers at the schema boundary.
- Never call datetime.now()/date.today(); use app/time.py (APP_TIMEZONE for business dates).
- Every outbound HTTP call has a timeout. POST is never auto-retried.
- Network calls happen OUTSIDE write transactions. GA sync + event dispatch happen AFTER commit.
- Events: enqueue into outbox_event in the SAME transaction as the business change.
- DB changes: write an Alembic migration by hand (no blind autogenerate: partial/expression indexes and views).
  Keep tests/test_schema_matches_models.py green.
- Errors: raise AppError subclasses with a stable `code`; never return ad-hoc JSON errors.
- Do not invent behavior marked [OPEN] in the design doc; use the stated default and leave a TODO(<team>) comment.
- Tests use real PostgreSQL 16 (testcontainers). No SQLite.
- Every route has Pydantic request/response models and appears in Swagger.

## Definition of done (per endpoint)
Schema models · service function · route · OpenAPI docs · acceptance tests from design §15.3 · error codes from §13.3.
