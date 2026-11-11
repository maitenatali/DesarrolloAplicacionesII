---
description: Analyze the whole repo and generate docs/ARCHITECTURE.md + docs/SYSTEM-DESIGN.md
argument-hint: [optional: subpath to limit scope]
---

Goal: build a durable mental model of this repo and write it to `docs/ARCHITECTURE.md` and `docs/SYSTEM-DESIGN.md`, so future sessions read those docs instead of re-exploring code.

Scope: ${ARGUMENTS:-entire repo}

## Phase 1 — Inventory (you, cheap)
1. `git ls-files | wc -l`, then `git ls-files | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -60` to see the directory weight map.
2. Read ONLY: README, root manifests (package.json / pyproject / go.mod / Cargo.toml / pom), Dockerfile, docker-compose, CI config, infra (terraform/k8s/serverless) — skimming.
3. Identify the stack, the deployables, and split the repo into 4–10 analysis scopes (by top-level module/service/package). Ignore vendored, generated, lockfiles, fixtures.
4. Print the scope list (one line each) before continuing.

## Phase 2 — Parallel scouting (subagents)
Launch one `repo-scout` subagent PER SCOPE, in parallel. Give each: its path, the stack, and "return the standard format". Do NOT read those directories yourself.

## Phase 3 — Cross-cutting pass (you)
With the scout reports only:
- Resolve OPEN QUESTIONS with targeted Grep + ranged reads — not full file reads.
- Trace 2–3 critical flows end to end (e.g. main request path, main write path, main async job).
- Build the dependency graph between scopes.

## Phase 4 — Write docs
Write `docs/ARCHITECTURE.md`:
1. Overview (what the system does, 3–5 lines)
2. Tech stack table (layer | tech | version if found)
3. Repository layout (tree, 2 levels, with one-line purpose per dir)
4. Modules / components: responsibility, public interface, dependencies, owner path
5. Module dependency diagram (Mermaid `graph LR`)
6. Architectural patterns & conventions actually in use (cite files)
7. Boundaries & rules (what may import what)
8. Build, test, run (exact commands)
9. Known issues / tech debt (from SMELLS/RISKS)

Write `docs/SYSTEM-DESIGN.md`:
1. Context: actors, external systems (Mermaid C4-style or `graph`)
2. Deployables & runtime topology (processes, containers, environments)
3. Critical flows as Mermaid `sequenceDiagram` (the 2–3 you traced)
4. Data model: entities, stores, ownership, key schemas
5. Integrations: APIs, queues, third parties, auth
6. Cross-cutting: authn/authz, config & secrets, observability, error handling, caching
7. Non-functional: scaling approach, failure modes, bottlenecks you can infer
8. Key design decisions (inferred ADRs: decision → evidence → trade-off)
9. Open questions for the team

Rules:
- Every claim is grounded: cite `path` or `path:symbol`. Mark inferences as _(inferred)_.
- Prefer tables and diagrams over prose. No marketing language.
- Target ≤ 600 lines each. These files are loaded often — density matters.
- If the docs already exist, UPDATE them preserving human-written sections marked `<!-- keep -->`.

Finish by deleting `.claude/.docs-stale` if it exists and reporting: scopes analyzed, flows traced, open questions count.
