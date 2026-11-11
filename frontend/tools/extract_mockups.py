"""Extrae de mockup_pantallas/*.html lo necesario para replicarlas 1:1 en React.

- CSS de cada pantalla -> src/styles/pages/<id>.css, aislado bajo la clase `.pg-<id>`
  (`:root`, `html` y `body` pasan a ser el contenedor de la pantalla; @keyframes se renombran).
- Todos los <svg> (markup + strings de los <script>) -> src/components/icons.generated.jsx, deduplicados.
- Opcional (--views DIR): vista JSX de referencia de cada <body> con los íconos ya reemplazados.

Uso (desde frontend/): python3 tools/extract_mockups.py [--views /tmp/views]
Herramienta de desarrollo: su salida se commitea, el build no la necesita.
"""

from __future__ import annotations

import hashlib
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCKUPS = ROOT.parent / "mockup_pantallas"
CSS_OUT = ROOT / "src" / "styles" / "pages"
ICONS_OUT = ROOT / "src" / "components" / "icons.generated.jsx"


def page_id(path: Path) -> str:
    return re.match(r"pantalla-(\w+?)-", path.name).group(1)


# ───────────────────────────── CSS ─────────────────────────────
def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_blocks(css: str, i: int = 0, top: bool = True):
    """Devuelve lista de (prelude, body|list) hasta la llave de cierre. Ignora llaves de cierre sueltas."""
    out, buf = [], ""
    while i < len(css):
        c = css[i]
        if c == "{":
            prelude = buf.strip()
            buf = ""
            if prelude.startswith("@media") or prelude.startswith("@supports"):
                children, i = parse_blocks(css, i + 1, top=False)
                out.append((prelude, children))
            else:
                depth, j = 1, i + 1
                while depth:
                    depth += {"{": 1, "}": -1}.get(css[j], 0)
                    j += 1
                out.append((prelude, css[i + 1 : j - 1]))
                i = j - 1
        elif c == "}":
            if top:  # "}" sobrante en el mockup: se descarta y se sigue
                buf = ""
                i += 1
                continue
            return out, i
        elif c == ";" and buf.strip().startswith("@"):
            out.append((buf.strip(), None))
            buf = ""
        else:
            buf += c
        i += 1
    return out, i


def scope_selector(sel: str, scope: str) -> str:
    sel = sel.strip()
    m = re.match(r"^(:root|html|body)(?![\w-])((?:\s*(?:html|body)(?![\w-]))*)(.*)$", sel, re.S)
    if m:
        rest = m.group(3)
        return scope + rest
    return f"{scope} {sel}"


def split_selectors(prelude: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in prelude:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p for p in parts if p.strip()]


def emit(blocks, scope: str, kf: dict[str, str], indent: str = "") -> str:
    out = []
    for prelude, body in blocks:
        if body is None:
            continue  # @import/@charset sueltos
        if isinstance(body, list):
            out.append(f"{indent}{prelude}{{\n{emit(body, scope, kf, indent + '  ')}{indent}}}")
        elif prelude.startswith("@keyframes"):
            name = prelude.split()[1]
            out.append(f"{indent}@keyframes {kf[name]}{{{body.strip()}}}")
        elif prelude.startswith("@font-face"):
            out.append(f"{indent}{prelude}{{{body.strip()}}}")
        else:
            decl = body.strip()
            if not decl:
                continue
            for old, new in kf.items():
                decl = re.sub(rf"(animation(?:-name)?\s*:[^;]*?)\b{re.escape(old)}\b", rf"\g<1>{new}", decl)
            sels = ",".join(scope_selector(s, scope) for s in split_selectors(prelude))
            out.append(f"{indent}{sels}{{{decl}}}")
    return "\n".join(out) + "\n"


def convert_css(css: str, pid: str) -> str:
    css = strip_comments(css)
    scope = f".pg-{pid}"
    kf = {n: f"{n}-{pid}" for n in re.findall(r"@keyframes\s+([\w-]+)", css)}
    blocks, _ = parse_blocks(css)
    header = f"/* Generado por tools/extract_mockups.py desde mockup_pantallas (pantalla {pid}). No editar a mano. */\n"
    return header + emit(blocks, scope, kf)


# ───────────────────────────── SVG / JSX ─────────────────────────────
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
ATTR_MAP = {"class": "className", "for": "htmlFor", "tabindex": "tabIndex", "readonly": "readOnly",
            "maxlength": "maxLength", "minlength": "minLength", "colspan": "colSpan", "rowspan": "rowSpan",
            "autocomplete": "autoComplete", "autofocus": "autoFocus", "inputmode": "inputMode",
            "novalidate": "noValidate", "enterkeyhint": "enterKeyHint", "spellcheck": "spellCheck",
            "xlink:href": "xlinkHref", "xml:space": "xmlSpace", "viewbox": "viewBox", "contenteditable": "contentEditable",
            "datetime": "dateTime", "srcset": "srcSet", "crossorigin": "crossOrigin"}
SVG_KEEP = {"viewBox"}


def camel(name: str) -> str:
    if name.startswith(("aria-", "data-")):
        return name
    if name in ATTR_MAP:
        return ATTR_MAP[name]
    return re.sub(r"[-:]([a-z])", lambda m: m.group(1).upper(), name)


def style_obj(style: str) -> str:
    items = []
    for decl in style.split(";"):
        if ":" not in decl:
            continue
        k, v = decl.split(":", 1)
        k, v = k.strip(), v.strip()
        if not k:
            continue
        key = k if k.startswith("--") else re.sub(r"-([a-z])", lambda m: m.group(1).upper(), k)
        items.append(f"{key!r}: {v!r}".replace("'", '"') if k.startswith("--") else f"{key}: {v!r}".replace("'", '"'))
    return "{{" + ", ".join(items) + "}}"


def jsx_attrs(attrs) -> str:
    out = []
    for k, v in attrs:
        if k == "style" and v is not None:
            out.append(f"style={style_obj(v)}")
            continue
        if k.startswith("on"):
            go = re.search(r"__uadenetGo\('([^']+)'\)", v or "")
            out.append(f'data-go="{go.group(1)}"' if go else f'data-{k}="{html.escape(v or "")}"')
            continue
        name = camel(k)
        if v is None or v == "":
            if k in ("disabled", "checked", "selected", "hidden", "required", "readonly", "multiple", "open", "autofocus"):
                out.append(name)
            else:
                out.append(f'{name}=""')
        else:
            out.append(f'{name}="{v.replace(chr(34), "&quot;")}"' if "{" not in v else f"{name}={{{v!r}}}")
    return (" " + " ".join(out)) if out else ""


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, attrs, parent, []


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Node("#root", [])
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)

    def handle_entityref(self, name):
        self.cur.children.append(f"&{name};")

    def handle_charref(self, name):
        self.cur.children.append(f"&#{name};")

    def handle_comment(self, data):
        self.cur.children.append(("#comment", data))


def raw_svg(n: Node, top: bool = True) -> str:
    attrs = n.attrs if not top else [(k, v) for k, v in n.attrs if k not in ("class", "style", "id") and not k.startswith("aria-")]
    a = jsx_attrs(attrs)
    if not n.children:
        return f"<{n.tag}{a}/>"
    inner = "".join(raw_svg(c, False) if isinstance(c, Node) else (c.strip() if isinstance(c, str) else "") for c in n.children)
    return f"<{n.tag}{a}>{inner}</{n.tag}>"


ICONS: dict[str, str] = {}  # key -> jsx
ICON_IDS: dict[str, str] = {}


def icon_name(n: Node) -> str:
    jsx = raw_svg(n)
    key = hashlib.sha1(jsx.encode()).hexdigest()
    if key not in ICON_IDS:
        ICON_IDS[key] = f"i{len(ICON_IDS) + 1}"
        ICONS[ICON_IDS[key]] = jsx
    return ICON_IDS[key]


def to_jsx(n, depth=0) -> str:
    pad = "  " * depth
    if isinstance(n, tuple):
        return f"{pad}{{/* {n[1].strip()} */}}\n"
    if isinstance(n, str):
        t = n.strip()
        if not t:
            return ""
        t = t.replace("{", "&#123;").replace("}", "&#125;")
        return f"{pad}{' '.join(t.split())}\n"
    if n.tag in ("script", "style"):
        return ""
    if n.tag == "svg":
        props = [(k, v) for k, v in n.attrs if k in ("class", "style", "id") or k.startswith("aria-")]
        return f"{pad}<I.{icon_name(n)}{jsx_attrs(props)} />\n"
    a = jsx_attrs(n.attrs)
    if n.tag in VOID or not n.children:
        return f"{pad}<{n.tag}{a} />\n"
    kids = "".join(to_jsx(c, depth + 1) for c in n.children)
    if not kids.strip():
        return f"{pad}<{n.tag}{a}></{n.tag}>\n"
    return f"{pad}<{n.tag}{a}>\n{kids}{pad}</{n.tag}>\n"


def svgs_in_scripts(src: str):
    for m in re.finditer(r"<svg\b.*?</svg>", src, re.S):
        frag = m.group(0)
        if "${" in frag:
            continue
        tb = TreeBuilder()
        tb.feed(frag)
        for c in tb.root.children:
            if isinstance(c, Node) and c.tag == "svg":
                props = [(k, v) for k, v in c.attrs if k in ("class", "style", "id") or k.startswith("aria-")]
                yield frag, icon_name(c) + jsx_attrs(props)


def compress_script(js: str) -> str:
    """Vista legible del JS: recorta literales de datos largos y marca los SVG por nombre de ícono."""
    for frag, name in list(svgs_in_scripts(js)):
        js = js.replace(frag, f"<I.{name} />")
    js = re.sub(r"(\[\{.{400}).*?(\}\];)", r"\1 …(datos recortados)… \2", js, flags=re.S)
    return js


def main():
    views = None
    if "--views" in sys.argv:
        views = Path(sys.argv[sys.argv.index("--views") + 1])
        views.mkdir(parents=True, exist_ok=True)
    CSS_OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(MOCKUPS.glob("pantalla-*.html")):
        pid = page_id(path)
        src = path.read_text(encoding="utf-8")
        css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", src, re.S))
        (CSS_OUT / f"{pid}.css").write_text(convert_css(css, pid), encoding="utf-8")
        body = re.search(r"<body[^>]*>(.*)</body>", src, re.S).group(1)
        tb = TreeBuilder()
        tb.feed(body)
        jsx = "".join(to_jsx(c) for c in tb.root.children)
        scripts = [compress_script(s) for s in re.findall(r"<script[^>]*>(.*?)</script>", body, re.S)]
        if views:
            (views / f"{pid}.jsx.txt").write_text(jsx, encoding="utf-8")
            (views / f"{pid}.js.txt").write_text("\n/* ---- script ---- */\n".join(scripts), encoding="utf-8")
    lines = ["/* Generado por tools/extract_mockups.py: íconos SVG de mockup_pantallas, deduplicados. No editar a mano. */",
             "/* eslint-disable */", ""]
    for name, jsx in ICONS.items():
        tag_end = jsx.index(">") if not jsx.startswith("<svg/>") else 4
        opened = jsx[:tag_end].rstrip("/")
        rest = jsx[tag_end:]
        lines.append(f"export const {name} = (p) => {opened} {{...p}}{rest};")
    ICONS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pages={len(list(MOCKUPS.glob('pantalla-*.html')))} icons={len(ICONS)}")


if __name__ == "__main__":
    main()
