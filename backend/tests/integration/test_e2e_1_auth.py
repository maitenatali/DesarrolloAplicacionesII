"""E2E 1/3 — Authentication & authorization with real RS256 JWTs (local CORE simulator).

Covers: login / me / refresh rotation / logout, JWKS, invalid / tampered / expired / refresh-as-access
tokens, role gate (student vs teacher), course ownership, service-to-service tokens on /results.
"""

from __future__ import annotations

import jwt as pyjwt
from freezegun import freeze_time

from tests.conftest import SERVICE_TOKEN, STUDENT_CLIENT

TEACHER = ("maria.gomez@uade.edu.ar", "Uade2026!")
TEACHER_ID = "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
OTHER_TEACHER = ("carlos.diaz@uade.edu.ar", "Uade2026!")
STUDENT = ("juan.perez@uade.edu.ar", "Uade2026!")
STUDENT_ID = "ba310c57-a684-4dbf-a4a4-905fcfbefa08"


def login(c, creds):
    r = c.post("/api/v1/auth/login", json={"email": creds[0], "password": creds[1]})
    assert r.status_code == 200, r.get_json()
    return r


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_e2e_authentication_and_authorization(e2e_app, seeded_with_acta):
    c = e2e_app.test_client()

    # ── public, no auth ───────────────────────────────────────────────────────────────
    assert c.get("/api/v1/health").status_code == 200
    jwks = c.get("/.well-known/jwks.json").get_json()
    assert jwks["keys"][0]["kty"] == "RSA" and jwks["keys"][0]["alg"] == "RS256"

    # ── login failures (CORE error codes, problem+json) ──────────────────────────────
    bad = c.post("/api/v1/auth/login", json={"email": TEACHER[0], "password": "wrong"})
    assert bad.status_code == 401 and bad.mimetype == "application/problem+json"
    assert bad.get_json()["code"] == "AUTH_INVALID_CREDENTIALS"
    assert c.post("/api/v1/auth/login", json={"email": TEACHER[0]}).status_code == 400

    # ── login OK: CORE response shape + httpOnly refresh cookie ───────────────────────
    r = login(c, TEACHER)
    body = r.get_json()
    assert body["expiresIn"] == 900 and body["user"]["id"] == TEACHER_ID
    assert body["user"]["roles"] == ["TEACHER"] and body["user"]["status"] == "ACTIVE"
    set_cookie = r.headers.get("Set-Cookie", "")
    assert "refreshToken=" in set_cookie and "HttpOnly" in set_cookie
    token = body["accessToken"]
    header = pyjwt.get_unverified_header(token)
    claims = pyjwt.decode(token, options={"verify_signature": False})
    assert header["alg"] == "RS256" and header["kid"] == jwks["keys"][0]["kid"]
    assert claims["sub"] == TEACHER_ID and claims["kind"] == "user" and claims["typ"] == "access"

    me_core = c.get("/api/v1/auth/me", headers=bearer(token)).get_json()
    assert me_core["id"] == TEACHER_ID and "wallet:read:self" in me_core["permissions"]
    me = c.get("/api/v1/me", headers=bearer(token)).get_json()
    assert me["userId"] == TEACHER_ID and me["teacherIds"] == [TEACHER_ID]
    assert me["fullName"] == "María Gómez" and me["fileNumber"] == "D-1001"  # Backoffice directory

    # ── token problems → 401 ─────────────────────────────────────────────────────────
    assert c.get("/api/v1/courses").get_json()["code"] == "TOKEN_INVALID"
    assert c.get("/api/v1/courses", headers=bearer("not-a-jwt")).status_code == 401
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert c.get("/api/v1/courses", headers=bearer(tampered)).status_code == 401
    with freeze_time("2026-10-19 16:00:00"):  # access token lives 15 min
        expired = c.get("/api/v1/courses", headers=bearer(token))
        assert expired.status_code == 401 and expired.get_json()["code"] == "TOKEN_EXPIRED"

    # ── authorization: role gate + course ownership ──────────────────────────────────
    assert c.get("/api/v1/courses", headers=bearer(token)).status_code == 200
    student_token = login(c, STUDENT).get_json()["accessToken"]
    forbidden = c.get("/api/v1/courses", headers=bearer(student_token))
    assert forbidden.status_code == 403 and forbidden.get_json()["code"] == "FORBIDDEN"
    other = login(c, OTHER_TEACHER).get_json()["accessToken"]
    not_mine = c.get("/api/v1/courses/42", headers=bearer(other))
    assert not_mine.status_code == 403 and not_mine.get_json()["code"] == "COURSE_NOT_ASSIGNED"
    assert c.get("/api/v1/courses/43", headers=bearer(other)).status_code == 200

    # ── refresh rotation + logout ─────────────────────────────────────────────────────
    c2 = e2e_app.test_client()
    login(c2, TEACHER)
    old_cookie = c2.get_cookie("refreshToken", path="/api/v1/auth").value
    rr = c2.post("/api/v1/auth/refresh")
    assert rr.status_code == 200 and rr.get_json()["user"]["id"] == TEACHER_ID
    new_token = rr.get_json()["accessToken"]
    assert c2.get("/api/v1/me", headers=bearer(new_token)).status_code == 200
    # refresh tokens are single use: replaying the old one fails
    c3 = e2e_app.test_client()
    c3.set_cookie("refreshToken", old_cookie, path="/api/v1/auth")
    assert c3.post("/api/v1/auth/refresh").get_json()["code"] == "AUTH_REFRESH_INVALID"
    # a refresh token is never accepted as an access token
    assert c2.get("/api/v1/me", headers=bearer(old_cookie)).status_code == 401
    assert c2.post("/api/v1/auth/logout", headers=bearer(new_token)).status_code == 204
    assert c2.post("/api/v1/auth/refresh").status_code == 401

    # ── service-to-service (/results is for the Student Portal) ───────────────────────
    bad_client = c.post(
        "/internal/v1/service-auth/token", json={"clientId": STUDENT_CLIENT[0], "clientSecret": "nope"}
    )
    assert bad_client.status_code == 401
    svc = c.post(
        "/internal/v1/service-auth/token",
        json={"clientId": STUDENT_CLIENT[0], "clientSecret": STUDENT_CLIENT[1]},
    ).get_json()
    assert svc["tokenType"] == "Bearer" and svc["expiresIn"] == 900
    results = c.get(f"/api/v1/students/{STUDENT_ID}/results", headers=bearer(svc["accessToken"]))
    assert results.status_code == 200
    assert results.get_json()[0]["result"] == "APROBADO" and results.get_json()[0]["actaNumber"] == "2026-001"
    assert c.get("/api/v1/courses/42/results", headers=bearer(svc["accessToken"])).status_code == 200
    assert c.get(f"/api/v1/students/{STUDENT_ID}/results", headers=bearer(token)).status_code == 403
    assert c.get(f"/api/v1/students/{STUDENT_ID}/results", headers=bearer(SERVICE_TOKEN)).status_code == 200
    # a service token is not a teacher
    assert c.get("/api/v1/courses", headers=bearer(svc["accessToken"])).status_code == 403
    # internal notification endpoint needs a service token, not a user token
    note = {
        "userId": STUDENT_ID,
        "type": "TEST",
        "title": "t",
        "message": "m",
        "sourceModule": "student",
        "sourceReference": "x/1",
    }
    assert c.post("/internal/v1/notifications", json=note, headers=bearer(token)).status_code == 403
    assert (
        c.post("/internal/v1/notifications", json=note, headers=bearer(svc["accessToken"])).status_code == 201
    )
    dup = c.post("/internal/v1/notifications", json=note, headers=bearer(svc["accessToken"]))
    assert dup.status_code == 409
