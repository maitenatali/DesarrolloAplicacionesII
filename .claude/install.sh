#!/usr/bin/env bash
# Usage: bash install.sh /path/to/your/repo
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:?Usage: install.sh /path/to/repo}"
DEST="$(cd "$DEST" && pwd)"

echo "→ Installing SDD setup into $DEST"

copy() { # copy without overwriting existing files
  local rel="$1"
  if [ -e "$DEST/$rel" ]; then echo "  skip (exists): $rel"
  else mkdir -p "$(dirname "$DEST/$rel")"; cp "$SRC/$rel" "$DEST/$rel"; echo "  + $rel"; fi
}

for f in CLAUDE.md .mcp.json .claude/settings.json .claude/hooks/mark-docs-stale.sh \
         .claude/agents/repo-scout.md .claude/agents/architect.md \
         .claude/commands/map-repo.md .claude/commands/sync-docs.md \
         .claude/commands/spec.md .claude/commands/plan.md \
         .claude/commands/tasks.md .claude/commands/implement.md \
         specs/_templates/spec.md specs/_templates/plan.md specs/_templates/tasks.md; do
  copy "$f"
done
chmod +x "$DEST/.claude/hooks/mark-docs-stale.sh"
mkdir -p "$DEST/docs"

# gitignore local-only files
touch "$DEST/.gitignore"
for line in ".claude/settings.local.json" ".claude/.docs-stale"; do
  grep -qxF "$line" "$DEST/.gitignore" || echo "$line" >> "$DEST/.gitignore"
done

# --- Caveman (Claude Code plugin) ---
if command -v claude >/dev/null 2>&1; then
  echo "→ Installing Caveman plugin…"
  claude plugin marketplace add JuliusBrussee/caveman || true
  claude plugin install caveman@caveman || true
else
  echo "  ! 'claude' CLI not found. Install Caveman later with:"
  echo "    claude plugin marketplace add JuliusBrussee/caveman && claude plugin install caveman@caveman"
fi

cat <<'EOF'

✓ Done. Next:
  cd <repo> && claude
  1. /map-repo                 → generates docs/ARCHITECTURE.md + docs/SYSTEM-DESIGN.md
  2. Fill the TODOs in CLAUDE.md, then: /caveman:compress CLAUDE.md
  3. /spec my-feature "description" → /plan → /tasks → /implement
EOF
