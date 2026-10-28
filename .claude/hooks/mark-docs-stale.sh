#!/usr/bin/env bash
# PostToolUse hook: if a structural file changed (new module, config, schema, routes),
# drop a marker so you remember to run /sync-docs. Cheap: no tokens, no output to Claude.
input="$(cat)"
file="$(printf '%s' "$input" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
[ -z "$file" ] && exit 0

case "$file" in
  *docs/ARCHITECTURE.md|*docs/SYSTEM-DESIGN.md|*specs/*) exit 0 ;;
  *package.json|*pyproject.toml|*go.mod|*Cargo.toml|*docker-compose*|*Dockerfile*|\
  *schema*|*migration*|*routes*|*router*|*/api/*|*index.ts|*main.*|*app.*|*.proto|*.graphql)
    mkdir -p "$CLAUDE_PROJECT_DIR/.claude"
    echo "$file" >> "$CLAUDE_PROJECT_DIR/.claude/.docs-stale"
    ;;
esac
exit 0
