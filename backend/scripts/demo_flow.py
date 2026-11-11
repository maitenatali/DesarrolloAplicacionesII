#!/usr/bin/env python3
"""Demo didáctica del Portal Docente: un flujo corto contra el stack LEVANTADO.

Qué hace
--------
Le pega por HTTP real (no usa el test client de Flask) al stack de docker compose y muestra en la
terminal cada REQUEST completa y cada RESPONSE completa, para ver cómo "habla" el frontend con el backend:

    1. Login (CORE simulado)         -> access token + cookie de refresh
    2. Listar cursos del docente
    3. Planilla de notas del curso   -> trae los alumnos y los exámenes (sus IDs)
    4. Ver clases con asistencia     -> para elegir una fecha de clase existente
    5. Tomar asistencia de esa clase
    6. Cargar la nota de un alumno en un examen
    7. Releer las notas              -> comprobar el efecto + contadores del outbox
    8. Error intencional (nota 11)   -> ver el formato problem+json

OJO: los pasos 5 y 6 MODIFICAN datos demo (asistencia de la última clase y la nota de un alumno).
Es idempotente: correrlo de nuevo deja el mismo estado.

Todos los IDs (curso, alumnos, examen, fecha) salen de las responses anteriores: no hay nada hardcodeado
salvo el email y el password demo.

Qué URL usamos (gateway vs. directo)
------------------------------------
El backend (Flask) escucha en el puerto 8080 y expone sus rutas como /api/v1/*. Pero la app real NO le
habla directo: pasa por un "gateway" que imita al de CORE. En docker compose ese gateway es el nginx del
servicio `web` (puerto 3000), que reenvía:

    /api/v1/teacher/*   ->  teacher-service  /api/v1/*      (rutas del Portal Docente)
    /api/v1/auth|wallets|notifications  ->  CORE (hoy simulado dentro del mismo backend)

Usamos el gateway (http://localhost:3000) porque es exactamente el camino del frontend y del CORE real:
el día que se conecte CORE de verdad solo cambia la URL base. Por eso las rutas docentes llevan el
prefijo /api/v1/teacher y el login va a /api/v1/auth/login. (Directo al backend serían
http://localhost:8080/api/v1/courses, sin "teacher/"; se puede probar con --base-url
http://localhost:8080 --teacher-prefix /api/v1.)

Uso
---
    cd backend && make up                    # si el stack no está levantado
    python scripts/demo_flow.py              # flujo completo con colores
    python scripts/demo_flow.py --pause      # espera Enter entre pasos (para exponer)
    python scripts/demo_flow.py --full       # bodies JSON completos (por defecto se recortan a 60 líneas)
    python scripts/demo_flow.py --no-color   # sin colores (también si no es TTY o NO_COLOR está seteada)

Requiere solo la librería estándar + requests.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import urlsplit

import requests

# Regla del repo: TODA llamada HTTP saliente lleva timeout.
TIMEOUT_SECONDS = 15
WIDTH = 78
DEFAULT_EMAIL = "maria.gomez@uade.edu.ar"
DEFAULT_PASSWORD = "Uade2026!"
DEFAULT_COURSE_ID = 42  # curso del seed; si la docente no lo tiene se usa el primero de la lista
GRADE_TO_SET = 8.5  # nota que se carga; si ya era esa, se carga otra para que el cambio se note
INVALID_GRADE = 11  # fuera de rango 0-10: dispara el error de validación a propósito


# --------------------------------------------------------------------------------------------------
# Colores
# --------------------------------------------------------------------------------------------------
class Palette:
    """Códigos ANSI. Si los colores están apagados, todos los métodos devuelven el texto tal cual."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return self._wrap("1", text)

    def dim(self, text: str) -> str:
        return self._wrap("2", text)

    def cyan(self, text: str) -> str:
        return self._wrap("36", text)

    def blue(self, text: str) -> str:
        return self._wrap("1;34", text)

    def green(self, text: str) -> str:
        return self._wrap("32", text)

    def yellow(self, text: str) -> str:
        return self._wrap("33", text)

    def red(self, text: str) -> str:
        return self._wrap("1;31", text)

    def magenta(self, text: str) -> str:
        return self._wrap("1;35", text)

    def gray(self, text: str) -> str:
        return self._wrap("90", text)

    def paint(self, code: str, text: str) -> str:
        """Color arbitrario (código ANSI crudo), para los casos puntuales."""
        return self._wrap(code, text)

    def for_method(self, method: str, text: str) -> str:
        """Un color por verbo HTTP: GET azul, POST verde, PUT amarillo, DELETE rojo."""
        codes = {"GET": "1;34", "POST": "1;32", "PUT": "1;33", "PATCH": "1;33", "DELETE": "1;31"}
        return self._wrap(codes.get(method.upper(), "1"), text)

    def for_status(self, status: int, text: str) -> str:
        """Verde 2xx, amarillo 4xx, rojo 5xx (el resto, sin color)."""
        if 200 <= status < 300:
            return self._wrap("1;32", text)
        if 400 <= status < 500:
            return self._wrap("1;33", text)
        if status >= 500:
            return self._wrap("1;31", text)
        return text


def colors_enabled(no_color_flag: bool) -> bool:
    """Colores solo si hay terminal (TTY), no se pidió --no-color y NO_COLOR no está seteada."""
    return not no_color_flag and sys.stdout.isatty() and "NO_COLOR" not in os.environ


# Se reemplazan en main() según los argumentos.
C = Palette(enabled=False)
MAX_BODY_LINES = 60  # 0 = sin límite (--full). Solo recorta lo que se MUESTRA; los headers siempre salen completos.


# --------------------------------------------------------------------------------------------------
# Impresión de request / response
# --------------------------------------------------------------------------------------------------
def mask_token(value: str) -> str:
    """Deja visibles solo los primeros y últimos caracteres de un token: 'eyJhbG...x9Q'."""
    return f"{value[:6]}...{value[-3:]}" if len(value) > 12 else "***"


def mask_header(name: str, value: str) -> str:
    """Enmascara el access token del header Authorization (solo en lo que se muestra)."""
    if name.lower() == "authorization" and " " in value:
        scheme, token = value.split(" ", 1)
        return f"{scheme} {mask_token(token)}   (token recortado solo para mostrarlo)"
    if name.lower() == "cookie":
        return "; ".join(f"{k}={mask_token(v)}" for k, v in (c.split("=", 1) for c in value.split("; ") if "=" in c))
    return value


SECRET_KEYS = {"password"}
TOKEN_KEYS = {"accesstoken", "refreshtoken"}


def mask_body(data: Any) -> Any:
    """Copia del body JSON con password y tokens ocultos. Se ENVÍA/RECIBE el real; esto es solo para mostrar."""
    if isinstance(data, dict):
        return {k: mask_value(k, v) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_body(v) for v in data]
    return data


def mask_value(key: str, value: Any) -> Any:
    if key.lower() in SECRET_KEYS:
        return "********"
    if key.lower() in TOKEN_KEYS and isinstance(value, str):
        return f"{mask_token(value)}   (token recortado solo para mostrarlo)"
    return mask_body(value)


def title_case_header(name: str) -> str:
    return "-".join(part.capitalize() for part in name.split("-"))


def print_section(label: str) -> None:
    if label == "REQUEST":
        print(C.paint("1;36", ">>> REQUEST") + C.gray("   (equivalente en curl)"))
    else:
        print(C.paint("1;34", f"<<< {label}"))


# Headers que agrega curl solo (o que no aportan al ejemplo): no se muestran para que el comando quede limpio.
IMPORTANT_RESPONSE_HEADERS = {
    "content-type", "set-cookie", "location", "x-correlation-id", "x-request-id", "www-authenticate", "retry-after",
}
CURL_HIDDEN_HEADERS = {"user-agent", "accept-encoding", "connection", "content-length"}
# Claves del JSON que se resaltan con un color propio (según sea una respuesta OK o un error).
OK_KEYS = {"accessToken": "1;32", "refreshToken": "1;32", "grade": "1;32", "status": "1;35"}
ERROR_KEYS = {"code": "1;31", "detail": "1;33", "title": "1;33", "correlationId": "1;35", "field": "1;31"}
JSON_TOKEN = re.compile(r'("(?:\\.|[^"\\])*")(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?')
JSON_KEY_LINE = re.compile(r'^(\s*)"([^"]+)":\s(.*?)(,?)$')


def colorize_json_line(line: str, error: bool) -> str:
    """Pinta una línea de JSON: claves en cian, strings en verde, números en amarillo, true/false/null en magenta.
    Las claves importantes (code, detail, accessToken, grade...) resaltan TODO su valor en negrita."""
    match = JSON_KEY_LINE.match(line)
    if match:
        pad, key, value, comma = match.groups()
        code = (ERROR_KEYS if error else OK_KEYS).get(key)
        if code and not value.startswith(("{", "[")):
            return f'{pad}{C.cyan(chr(34) + key + chr(34))}: {C.paint(code, value)}{comma}'

    def paint(token: re.Match[str]) -> str:
        text, colon = token.group(1), token.group(2)
        if text is not None:
            return C.cyan(text) + colon if colon else C.green(text)
        value = token.group(0)
        return C.magenta(value) if value in ("true", "false", "null") else C.yellow(value)

    return JSON_TOKEN.sub(paint, line)


def print_request(prepared: requests.PreparedRequest) -> None:
    """Muestra la request EFECTIVAMENTE enviada (la 'prepared request') como un comando curl."""
    method = prepared.method or "GET"
    print_section("REQUEST")
    cont = C.gray(" \\")
    parts = urlsplit(prepared.url or "")
    shown_url = f"{parts.scheme}://{C.gray(parts.netloc)}{C.paint('1;36', parts.path)}"
    if parts.query:
        shown_url += C.yellow("?" + parts.query)
    print(f"{C.bold('curl')} {C.yellow('-i')} {C.yellow('-X')} {C.for_method(method, method)} '{shown_url}'{cont}")
    for name, value in prepared.headers.items():
        if name.lower() in CURL_HIDDEN_HEADERS:
            continue
        header = f"{title_case_header(name)}: {mask_header(name, str(value))}"
        key, _, rest = header.partition(": ")
        print(f"  {C.yellow('-H')} '{C.cyan(key)}: {C.paint('1', rest)}'{cont}")
    if not prepared.body:
        print(C.gray("  # (sin body)"))
        return
    raw = prepared.body.decode() if isinstance(prepared.body, bytes) else str(prepared.body)
    try:
        shown = json.dumps(mask_body(json.loads(raw)), indent=2, ensure_ascii=False)
    except ValueError:
        shown = raw
    lines = shown.splitlines()
    notice = None
    if MAX_BODY_LINES and len(lines) > MAX_BODY_LINES:
        notice = f"... ({len(lines) - MAX_BODY_LINES} líneas más; usá --full para ver el body completo)"
        lines = lines[:MAX_BODY_LINES]
    out = [colorize_json_line(line, False) for line in lines]
    if notice:
        out.append(C.gray(f"  {notice}"))
        out.append("'")
    else:
        out[-1] += "'"  # la comilla de cierre va pegada a la última llave, como en un curl real: -d '{ ... }'
    out[0] = f"  {C.yellow('-d')} '{out[0]}"
    print("\n".join(out))
    print(C.gray("# Se omiten User-Agent, Accept-Encoding, Connection y Content-Length (curl los agrega solo)."))


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


def print_body(text: str, *, error: bool = False, is_json: bool = True) -> None:
    """Imprime un body con sangría y colores. Los bodies muy largos (p. ej. 25 alumnos) se recortan salvo con --full."""
    lines = text.splitlines()
    notice = None
    if MAX_BODY_LINES and len(lines) > MAX_BODY_LINES:
        notice = f"... ({len(lines) - MAX_BODY_LINES} líneas más; usá --full para ver el body completo)"
        lines = lines[:MAX_BODY_LINES]
    for line in lines:
        print("    " + (colorize_json_line(line, error) if is_json else line))
    if notice:
        print("    " + C.gray(notice))


def mask_set_cookie(cookie: str) -> str:
    """Recorta el valor de una cookie 'nombre=valor; atributos' (solo para mostrarla)."""
    name, _, rest = cookie.partition("=")
    value, _, attrs = rest.partition(";")
    return f"{name}={mask_token(value)};{attrs}"


def set_cookie_lines(response: requests.Response) -> list[str]:
    """Todos los headers Set-Cookie (requests los junta en uno solo; el crudo los separa bien)."""
    raw = getattr(response.raw, "headers", None)
    if raw is not None and hasattr(raw, "getlist"):
        return list(raw.getlist("Set-Cookie"))
    value = response.headers.get("Set-Cookie")
    return [value] if value else []


def print_response(response: requests.Response, elapsed_ms: float) -> None:
    """Muestra status, tiempo, TODOS los headers, cookies y body (JSON con indent, o texto)."""
    status = response.status_code
    status_text = f"HTTP {status} {response.reason}"
    print()
    print_section("RESPONSE")
    print(f"{C.for_status(status, status_text)}   {C.gray(f'({elapsed_ms:.0f} ms)')}")
    print(C.bold("  Headers:"))
    for name, value in response.raw.headers.items() if hasattr(response.raw, "headers") else response.headers.items():
        shown = mask_set_cookie(value) if name.lower() == "set-cookie" else value
        if name.lower() in IMPORTANT_RESPONSE_HEADERS:
            print(f"    {C.cyan(name)}: {C.paint('1', shown)}")
        else:
            print(f"    {C.gray(name + ':')} {C.gray(shown)}")
    cookies = set_cookie_lines(response)
    if cookies:
        print(C.bold("  Cookies (Set-Cookie):"))
        for cookie in cookies:
            name, _, rest = cookie.partition("=")
            value, _, attrs = rest.partition(";")
            print(f"    nombre : {C.paint('1;35', name)}")
            print(f"    valor  : {C.green(mask_token(value))}   {C.gray('(recortado solo para mostrarlo)')}")
            print(f"    attrs  :{C.yellow(attrs)}")
    else:
        print(f"{C.bold('  Cookies (Set-Cookie):')} {C.gray('(ninguna)')}")
    if not response.content:
        print(f"{C.bold('  Body   :')} {C.gray('(vacío)')}")
        return
    is_error = status >= 400
    try:
        pretty = json.dumps(mask_body(response.json()), indent=2, ensure_ascii=False)
        print(C.bold("  Body (JSON):") + (C.red("   <-- error en formato problem+json") if is_error else ""))
        print_body(pretty, error=is_error)
    except ValueError:
        print(C.bold("  Body (texto, no es JSON):"))
        print_body(response.text, is_json=False)


# --------------------------------------------------------------------------------------------------
# Ejecución de pasos
# --------------------------------------------------------------------------------------------------
class DemoError(Exception):
    """Falla inesperada del flujo (se muestra en español y corta con exit code != 0)."""


@dataclass
class StepResult:
    number: int
    method: str
    path: str
    status: int
    elapsed_ms: float


@dataclass
class Demo:
    """Estado compartido del flujo: sesión HTTP, pasos hechos y opciones de la línea de comandos."""

    base_url: str
    teacher_prefix: str
    total_steps: int
    pause: bool
    session: requests.Session = field(default_factory=requests.Session)
    results: list[StepResult] = field(default_factory=list)

    def teacher(self, path: str) -> str:
        return f"{self.base_url}{self.teacher_prefix}{path}"


def print_step_header(number: int, total: int, title: str, why: str) -> None:
    print()
    print(C.paint("1;35", "=" * WIDTH))
    print(C.paint("1;35", f"[PASO {number}/{total}]") + " " + C.paint("1;97", title))
    print(C.gray("-" * WIDTH))
    for line in wrap(why):
        print(line)
    print(C.gray("-" * WIDTH))


def note(text: str) -> None:
    """Línea de 'qué aprendimos de esta response' (sale en verde para que se distinga del JSON)."""
    print(f"\n  {C.green('->')} {C.paint('1;32', text)}")


def wrap(text: str, width: int = WIDTH) -> list[str]:
    """Corte de línea simple para las explicaciones."""
    lines, current = [], ""
    for word in text.split():
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    return lines + ([current] if current else [])


def step(
    demo: Demo,
    title: str,
    why: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    headers: dict[str, str] | None = None,
    expected: tuple[int, ...] = (200,),
) -> requests.Response:
    """Arma, envía y muestra UN paso. Si el status no es el esperado, corta el flujo con DemoError."""
    number = len(demo.results) + 1
    if demo.pause and number > 1:
        input(C.dim("\n[--pause] Enter para continuar al siguiente paso... "))
    print_step_header(number, demo.total_steps, title, why)

    # Preparamos la request a mano para poder mostrar EXACTAMENTE lo que viaja (headers y body finales).
    request = requests.Request(method, url, params=params, json=json_body, headers=headers or {})
    prepared = demo.session.prepare_request(request)
    print_request(prepared)

    started = time.perf_counter()
    try:
        response = demo.session.send(prepared, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        raise DemoError(f"No se pudo completar {method} {url}: {exc}") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000

    print_response(response, elapsed_ms)
    demo.results.append(StepResult(number, method, urlsplit(url).path, response.status_code, elapsed_ms))
    if response.status_code not in expected:
        raise DemoError(
            f"El paso {number} devolvió {response.status_code} y se esperaba {' o '.join(map(str, expected))}."
        )
    return response


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------------------------------
# El flujo
# --------------------------------------------------------------------------------------------------
def check_stack(base_url: str) -> None:
    """Chequeo previo: si el stack no responde, avisamos cómo levantarlo en vez de mostrar un traceback."""
    try:
        requests.get(f"{base_url}/api/v1/health", timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException:
        raise DemoError(
            f"No hay respuesta en {base_url}. El stack no parece estar levantado.\n"
            "Levantalo con:  cd backend && make up   (esperá a que termine de migrar y cargar los datos demo)\n"
            "Si usás otra URL, pasala con --base-url."
        ) from None


def run_flow(demo: Demo, email: str, password: str) -> None:
    # PASO 1 -------------------------------------------------------------------------------------
    login = step(
        demo,
        "Login contra CORE (simulado)",
        "Se envía email y password a CORE. Responde con un access token JWT (vive en memoria del cliente, "
        "dura poco) y deja una cookie httpOnly 'refreshToken' para renovarlo. Todas las llamadas siguientes "
        "llevan ese token en el header Authorization: Bearer.",
        "POST",
        f"{demo.base_url}/api/v1/auth/login",
        json_body={"email": email, "password": password},
        headers={"Accept": "application/json"},
    ).json()
    token = login["accessToken"]
    auth = auth_header(token)
    note(f"El 'sub' del JWT / id de la persona es {login['user']['id']} (UUID de Backoffice, no el email).")

    # PASO 2 -------------------------------------------------------------------------------------
    courses = step(
        demo,
        "Listar cursos del docente",
        "El Portal Docente usa el token para saber quién es la docente y devuelve SOLO sus cursos. "
        "De acá sale el id del curso con el que trabajan los pasos siguientes.",
        "GET",
        demo.teacher("/courses"),
        headers=auth,
    ).json()
    if not courses:
        raise DemoError("La docente no tiene cursos. ¿Se cargó el seed? Probá: cd backend && make seed")
    course = next((c for c in courses if c["id"] == DEFAULT_COURSE_ID), courses[0])
    course_id = course["id"]
    note(f"Curso elegido: id={course_id} ({course['subject']['name']}, {course['code']}).")

    # PASO 3 -------------------------------------------------------------------------------------
    matrix = step(
        demo,
        "Ver alumnos y exámenes del curso (planilla de notas)",
        "La planilla de notas trae en una sola respuesta los alumnos inscriptos (studentId = UUID) y los "
        "exámenes del curso (id numérico y fase). Los usamos para saber a quién tomar asistencia y qué "
        "examen calificar.",
        "GET",
        demo.teacher(f"/courses/{course_id}/grades"),
        headers=auth,
    ).json()
    students = matrix["rows"]
    exam = pick_exam(matrix["exams"])
    student = students[0]
    note(
        f"{len(students)} alumnos inscriptos. Examen elegido: id={exam['id']} "
        f"({exam['name']}, {exam['date']}). Alumno elegido: {student['studentName']}."
    )

    # PASO 4 -------------------------------------------------------------------------------------
    attendances = step(
        demo,
        "Ver las clases con asistencia ya registrada",
        "Para tomar asistencia hay que indicar el día de la clase. Consultamos las clases ya registradas y "
        "elegimos la más reciente; así podemos volver a tomarla sin ensuciar los datos demo (la operación es "
        "idempotente: el mismo PUT repetido da el mismo resultado).",
        "GET",
        demo.teacher(f"/courses/{course_id}/attendances"),
        headers=auth,
    ).json()
    day = attendances[0]["date"] if attendances else date.today().isoformat()
    note(f"Clase elegida: {day}.")

    # PASO 5 -------------------------------------------------------------------------------------
    records = [
        {"studentId": s["studentId"], "status": "AUSENTE" if i == 0 else "PRESENTE"} for i, s in enumerate(students)
    ]
    step(
        demo,
        f"Tomar asistencia de la clase del {day}",
        "PUT reemplaza la asistencia de esa fecha. La regla de negocio exige enviar a TODOS los alumnos del "
        "curso (si falta alguno responde 400 INCOMPLETE_ROSTER). Acá todos PRESENTE salvo el primero, AUSENTE. "
        "Si la clase ya existía responde 200; si se crea, 201. Además se encola un evento en el outbox.",
        "PUT",
        demo.teacher(f"/courses/{course_id}/attendances/{day}"),
        json_body={"notes": "Asistencia cargada por demo_flow.py", "records": records},
        headers=auth,
        expected=(200, 201),
    )

    # PASO 6 -------------------------------------------------------------------------------------
    current = student["grades"].get(str(exam["id"]), {}).get("grade")
    new_grade = GRADE_TO_SET if current != GRADE_TO_SET else 9
    step(
        demo,
        f"Cargar la nota de {student['studentName']} en el examen {exam['id']}",
        "PUT carga o actualiza notas en lote. La nota viaja como número JSON entre 0 y 10 con hasta 2 "
        "decimales (el backend la guarda como Decimal, nunca como float). Se encola el evento "
        "'teacher.grade-published.v1' en la misma transacción.",
        "PUT",
        demo.teacher(f"/courses/{course_id}/exams/{exam['id']}/grades"),
        json_body={"entries": [{"studentId": student["studentId"], "grade": new_grade}]},
        headers=auth,
    )

    # PASO 7 -------------------------------------------------------------------------------------
    grades = step(
        demo,
        "Releer las notas del examen (efecto del cambio)",
        "Volvemos a pedir las notas del examen para comprobar que la nota quedó guardada y que el resumen "
        "(promedio, aprobados, pendientes) se recalculó.",
        "GET",
        demo.teacher(f"/courses/{course_id}/exams/{exam['id']}/grades"),
        headers=auth,
    ).json()
    saved = next((e for e in grades["entries"] if e["studentId"] == student["studentId"]), None)
    note(f"Nota guardada para {student['studentName']}: {saved['grade'] if saved else '?'}.")

    # PASO 8 -------------------------------------------------------------------------------------
    step(
        demo,
        "Error intencional: nota fuera de rango (problem+json)",
        f"Enviamos una nota de {INVALID_GRADE} (el máximo es 10) para ver cómo responde el backend ante un "
        "error. Los errores siempre son 'application/problem+json': 'code' estable (para programar contra "
        "él), 'detail' en español (para mostrar al usuario), 'errors' con el campo que falló y "
        "'correlationId' para rastrear en logs. Este paso devuelve 400 A PROPÓSITO y NO cuenta como fallo.",
        "PUT",
        demo.teacher(f"/courses/{course_id}/exams/{exam['id']}/grades"),
        json_body={"entries": [{"studentId": student["studentId"], "grade": INVALID_GRADE}]},
        headers=auth,
        expected=(400, 422),
    )


def pick_exam(exams: list[dict[str, Any]]) -> dict[str, Any]:
    """Elige el examen ya rendido (COMPLETED) más reciente; si no hay, el primero disponible."""
    if not exams:
        raise DemoError("El curso no tiene exámenes cargados. ¿Se cargó el seed demo?")
    completed = [e for e in exams if e.get("phase") == "COMPLETED"]
    return (completed or exams)[-1]


# --------------------------------------------------------------------------------------------------
# Resumen y main
# --------------------------------------------------------------------------------------------------
def print_summary(results: list[StepResult]) -> None:
    print()
    print(C.paint("1;35", "=" * WIDTH))
    print(C.paint("1;97", "RESUMEN"))
    print(C.gray("-" * WIDTH))
    print(C.bold(f"{'Paso':<5} {'Método':<7} {'Path':<50} {'Status':<7} {'ms':>6}"))
    for r in results:
        status = C.for_status(r.status, f"{r.status:<7}")
        method = C.for_method(r.method, f"{r.method:<7}")
        print(f"{r.number:<5} {method} {r.path:<50} {status} {C.gray(f'{r.elapsed_ms:>6.0f}')}")
    print(C.gray("-" * WIDTH))
    print(f"Total de requests: {C.bold(str(len(results)))}")
    print(C.paint("1;35", "=" * WIDTH))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flujo corto del Portal Docente contra el stack levantado, mostrando cada request y response."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="URL del gateway (nginx del servicio web). Default: %(default)s. "
        "Directo al backend: http://localhost:8080",
    )
    parser.add_argument(
        "--teacher-prefix",
        default="/api/v1/teacher",
        help="Prefijo de las rutas docentes. Default: %(default)s (con el backend directo usar /api/v1).",
    )
    parser.add_argument("--no-color", action="store_true", help="Desactiva los colores ANSI.")
    parser.add_argument(
        "--full",
        action="store_true",
        help=f"Muestra los bodies completos (por defecto se recortan a {MAX_BODY_LINES} líneas para que se lea bien).",
    )
    parser.add_argument("--pause", action="store_true", help="Espera Enter entre pasos (útil para exponer).")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Email del docente. Default: %(default)s")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Password del docente (demo).")
    return parser.parse_args()


def main() -> int:
    global C, MAX_BODY_LINES
    args = parse_args()
    if args.full:
        MAX_BODY_LINES = 0
    C = Palette(colors_enabled(args.no_color))
    base_url = args.base_url.rstrip("/")
    demo = Demo(base_url, args.teacher_prefix.rstrip("/"), total_steps=8, pause=args.pause)

    print(C.paint("1;35", "=" * WIDTH))
    print(C.paint("1;97", "Portal Docente - demo de flujo HTTP"))
    print(f"Backend/gateway : {C.cyan(base_url)}")
    print(f"Docente         : {C.cyan(args.email)}")
    print(C.gray("Los tokens y el password se recortan solo al MOSTRARLOS; en la red viajan completos."))
    print(C.paint("1;35", "=" * WIDTH))

    try:
        check_stack(base_url)
        run_flow(demo, args.email, args.password)
    except DemoError as exc:
        print(f"\n{C.for_status(500, 'ERROR')}: {exc}", file=sys.stderr)
        if demo.results:
            print_summary(demo.results)
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        return 130
    print_summary(demo.results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
