---
description: Break an approved plan into small, ordered, testable tasks
argument-hint: <feature-slug>
allowed-tools: Read, Write
model: sonnet
---

Read `specs/$ARGUMENTS/spec.md` and `specs/$ARGUMENTS/plan.md` (plan must be `approved`).
Write `specs/$ARGUMENTS/tasks.md` using `specs/_templates/tasks.md`.

Rules:
- Each task: ≤ ~1h of work, touches few files, has a verification step (test or command).
- Order by dependency. Mark parallelizable tasks with `[P]`.
- Tests come before or with the code they cover.
- Reference the acceptance criterion (AC-n) each task serves.
- Last task: run `/sync-docs` if the plan changed structure.
