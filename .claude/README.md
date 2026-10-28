# Setup de Claude Code para Spec-Driven Development

Setup listo para copiar en tu repo: Claude mapea todo el código, genera `docs/ARCHITECTURE.md` y `docs/SYSTEM-DESIGN.md`, y trabajás cada feature con el flujo **spec → plan → tasks → implement**, con varias capas de ahorro de tokens.

## Instalación

```bash
bash install.sh /ruta/a/tu/repo
```

No pisa archivos que ya existan. Instala el plugin Caveman.

Requisitos: Claude Code CLI, `git`.

## Estructura

```
CLAUDE.md                      # memoria corta del proyecto (se carga SIEMPRE)
.claude/
  settings.json                # permisos, deny de carpetas pesadas, hook
  hooks/mark-docs-stale.sh     # marca cuando cambia algo estructural
  agents/
    repo-scout.md              # explorador read-only en Haiku (barato)
    architect.md               # diseña planes en Opus
  commands/
    map-repo.md                # /map-repo  → ARCHITECTURE.md + SYSTEM-DESIGN.md
    sync-docs.md               # /sync-docs → actualiza solo lo que cambió
    spec.md  plan.md  tasks.md  implement.md
specs/
  _templates/                  # spec.md, plan.md, tasks.md
  <feature>/                   # se crea uno por feature
docs/                          # acá se generan los dos docs
```

## Uso

**1. Primera vez — entender el repo**
```
claude
/map-repo
```
`/map-repo` hace un inventario barato, divide el repo en 4–10 scopes, lanza un `repo-scout` (Haiku) **en paralelo por scope** y después sintetiza. Así el contexto principal recibe resúmenes, no miles de líneas de código. Para un subdirectorio: `/map-repo packages/api`.

**2. Por cada feature**
```
/spec checkout-v2 "permitir pago en cuotas con Mercado Pago"
  → revisás y cambiás status: approved
/plan checkout-v2
  → revisás decisiones y cambiás status: approved
/tasks checkout-v2
/implement checkout-v2          # siguiente tarea
/implement checkout-v2 all      # todas hasta terminar o bloquearse
```

**3. Mantener los docs al día**
```
/sync-docs
```
Mucho más barato que volver a correr `/map-repo`: mira el `git diff` y edita solo las secciones afectadas. El hook te deja un archivo `.claude/.docs-stale` cuando tocás manifests, schemas, rutas, etc.

## Optimización de tokens — qué hace cada capa

| Capa | Qué ahorra | Cómo |
|------|-----------|------|
| **Docs como caché** | Lo más grande: no re-explorar el repo cada sesión | `CLAUDE.md` le dice que lea ARCHITECTURE/SYSTEM-DESIGN primero |
| **Subagentes** | Contexto principal: la exploración vive en otro contexto | `repo-scout` devuelve un resumen fijo de ~400 palabras |
| **Modelos por tarea** | Costo: Haiku explora, Sonnet hace tasks, Opus diseña | `model:` en el frontmatter de agents/commands |
| **Permisos deny** | Evita leer `node_modules`, lockfiles, builds, `.min.js` | `.claude/settings.json` |
| **Caveman** | Output: respuestas telegráficas | `/caveman` (niveles lite/full/ultra) |
| **caveman-compress** | Input: `CLAUDE.md` más corto en cada sesión | `/caveman:compress CLAUDE.md` (guarda backup `.original.md`) |
| **Límites de output** | Comandos/MCP que escupen demasiado | `BASH_MAX_OUTPUT_LENGTH`, `MAX_MCP_OUTPUT_TOKENS` |

Expectativas realistas sobre Caveman: el repo promete ~65–75% menos tokens de **output**, pero el output es una fracción chica de lo que consume una sesión de Claude Code (la mayoría es input: archivos leídos, contexto). En pruebas independientes el ahorro real total ronda el 15–25% o menos. Las capas que más mueven la aguja son los docs-caché y los subagentes. Caveman suma, pero no es lo principal.

Recomendación: no uses Caveman en nivel `ultra` mientras generás specs o planes (querés claridad para revisar). Activalo en `/implement` y en sesiones de debugging.

## Hábitos que también ahorran
- `/clear` entre features; `/compact` cuando la sesión se alarga.
- Un feature por sesión. El estado vive en `specs/<feature>/tasks.md`, no en el chat.
- Mantené `CLAUDE.md` por debajo de ~60 líneas; lo detallado va en `docs/`.
- Los prompts de los commands están en inglés a propósito: tokeniza más compacto. Claude te responde en español igual.

## Personalizar
- Completá los `TODO` de `CLAUDE.md` (comandos de test/lint, convenciones).
- Agregá rutas propias al `deny` de `settings.json` (p. ej. `Read(./data/**)`).
