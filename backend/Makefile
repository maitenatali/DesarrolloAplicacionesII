PY ?= python

.PHONY: up migrate seed test lint openapi outbox
up:
	docker compose up --build
migrate:
	flask db upgrade
seed:
	flask seed
test:
	$(PY) -m pytest --cov=app --cov-fail-under=85
lint:
	ruff check . && ruff format --check . && mypy app/services app/security app/integrations
openapi:
	flask openapi --out docs/openapi.json
outbox:
	flask outbox-once
