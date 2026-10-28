---
description: Incrementally update ARCHITECTURE.md / SYSTEM-DESIGN.md from recent changes (cheap vs /map-repo)
argument-hint: [git ref to diff against, default: last docs commit]
allowed-tools: Read, Edit, Grep, Glob, Bash(git:*), Bash(cat:*), Bash(rm:*)
---

1. Base ref: `${ARGUMENTS}` or, if empty, `git log -1 --format=%H -- docs/ARCHITECTURE.md docs/SYSTEM-DESIGN.md`.
2. `git diff --stat <base>..HEAD` plus `cat .claude/.docs-stale 2>/dev/null`.
3. Ignore changes that do not affect structure (pure logic inside existing functions, tests, styling).
4. For structural changes (new/removed modules, new deps, new endpoints, schema changes, new integrations, new deployables) inspect only those symbols (Grep + ranged reads).
5. Edit ONLY the affected sections of the two docs. Do not rewrite untouched sections.
6. `rm -f .claude/.docs-stale`. Report what changed in ≤5 bullets.
