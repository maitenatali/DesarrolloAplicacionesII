---
description: Implement the next pending task(s) of a feature
argument-hint: <feature-slug> [task-id | all]
---

Feature: first word of `$ARGUMENTS`. Target: second word (default: next unchecked task).

Context budget: read `specs/<slug>/tasks.md`, then only the plan section for the current task. Do not reread spec/plan in full each time. Use Grep to locate code; read files by range.

Loop per task:
1. State the task id + 1-line intent.
2. Write/adjust the test first when the task has one.
3. Implement the minimal change described in the plan.
4. Run the task's verification command. Fix until green.
5. Tick the checkbox in `tasks.md` and append `→ <files changed>`.
6. If reality diverges from the plan: STOP, propose a plan edit, wait for me.

When the target is `all`, continue until done or blocked. At the end, give a ≤5-line summary and remind me about `/sync-docs` if `.claude/.docs-stale` exists.
