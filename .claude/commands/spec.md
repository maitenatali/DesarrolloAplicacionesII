---
description: Create a feature spec (WHAT + WHY, no implementation)
argument-hint: <feature-slug> <short description>
allowed-tools: Read, Write, Glob, Grep
---

Create `specs/<slug>/spec.md` from `specs/_templates/spec.md`.
Input: $ARGUMENTS (first word = slug, rest = description).

- Read `docs/ARCHITECTURE.md` only for vocabulary and affected areas. Do NOT design the solution.
- Focus on user-visible behavior, acceptance criteria (Given/When/Then), scope and non-goals.
- Every acceptance criterion must be testable.
- Put anything unclear in "Open questions" and ASK me before finishing — max 5 questions, multiple-choice when possible.
- Status: `draft`. I'll change it to `approved`.
