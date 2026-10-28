---
description: Generate the technical plan (HOW) for an approved spec
argument-hint: <feature-slug>
---

Feature: `specs/$ARGUMENTS/`

1. Read `specs/$ARGUMENTS/spec.md`. If status ≠ `approved`, stop and tell me.
2. Delegate to the `architect` subagent with: the spec path, `docs/ARCHITECTURE.md`, `docs/SYSTEM-DESIGN.md`, and `specs/_templates/plan.md`.
3. Write the result to `specs/$ARGUMENTS/plan.md`.
4. Check: every acceptance criterion in the spec maps to at least one plan item. List any gap.
5. Show me a ≤10-line summary + the decisions I need to approve.
