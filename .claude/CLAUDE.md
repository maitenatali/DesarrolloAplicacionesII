# CLAUDE.md

<!-- Keep this file SHORT. It loads every session. Run /caveman:compress CLAUDE.md after editing. -->

## Context sources (read in this order, only what you need)
1. `docs/ARCHITECTURE.md` — modules, boundaries, dependencies. Read FIRST before exploring code.
2. `docs/SYSTEM-DESIGN.md` — data flow, runtime, integrations, decisions.
3. `specs/<feature>/` — active spec, plan, tasks.
Do NOT re-explore the repo if these docs answer the question.

## Code navigation
- Use Grep to locate symbols before reading whole files.
- Read file ranges, not full files, when possible.
- Delegate wide searches to the `repo-scout` subagent; it returns conclusions, not dumps.

## Spec-driven workflow
`/spec <feature>` → `/plan <feature>` → `/tasks <feature>` → `/implement <feature>`
- No code without an approved `spec.md` + `plan.md`.
- Spec says WHAT/WHY. Plan says HOW. Tasks are small, ordered, testable.
- If implementation diverges from the plan, update the plan first.
- After merging structural changes, run `/sync-docs`.

## Commands
- Install: backend `cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'` · frontend `cd frontend && npm install`
- Run all (Docker): `cd backend && cp .env.example .env && make up` → http://localhost:3000
- Test: backend `cd backend && make test` (needs Docker for testcontainers) · frontend `cd frontend && npm test`
- Lint/typecheck: `cd backend && make lint` (ruff + mypy) · frontend `npm run build`

## Conventions
- Project rules (layers, Decimal, `app/time.py`, outbox, problem+json, mockups 1:1): root `CLAUDE.md`.
- Known tech debt to address via specs: `docs/ARCHITECTURE.md` §9; open questions: `docs/SYSTEM-DESIGN.md` §9.
