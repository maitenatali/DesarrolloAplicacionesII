import pytest

from app.config import ConfigError, Settings
from app.security.principal import Principal, principal_from_me


def test_config_lists_all_problems_at_once():
    with pytest.raises(ConfigError) as e:
        Settings.from_env(
            environ={"APP_ENV": "production", "AUTH_VERIFIER": "dev", "PORT": "abc", "PASSING_GRADE": "x"}
        )
    msg = str(e.value)
    assert (
        "AUTH_VERIFIER=dev is refused" in msg
        and "PORT" in msg
        and "PASSING_GRADE" in msg
        and "DATABASE_URL" in msg
    )


def test_live_mode_requires_urls():
    with pytest.raises(ConfigError) as e:
        Settings.from_env(environ={"DATABASE_URL": "x", "INTEGRATIONS_MODE": "live"})
    assert "ACADEMIC_BASE_URL" in str(e.value)


def test_per_integration_override():
    s = Settings.from_env(
        environ={
            "DATABASE_URL": "x",
            "INTEGRATIONS_MODE": "live",
            "ACADEMIC_MODE": "mock",
            "STUDENT_DIRECTORY_MODE": "mock",
            "CORE_JWKS_URL": "https://core.test/.well-known/jwks.json",
        }
    )
    assert (s.academic_mode, s.core_events_mode, s.student_directory_mode) == ("mock", "live", "mock")


def test_docente_keys_is_the_core_user_id():
    """CORE `sub` = Backoffice userId = GA docenteId; email is never used as a key."""
    p = Principal(user_id="5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", email="maria.gomez@uade.edu.ar")
    assert p.docente_keys() == ["5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"]
    assert Principal(user_id="").docente_keys() == []


def test_principal_from_me():
    p = principal_from_me(
        {
            "id": "9f",
            "email": "a@b.c",
            "roles": [{"name": "TEACHER"}, "ROLE_X"],
            "permissions": ["p"],
            "status": "ACTIVE",
        }
    )
    assert p.user_id == "9f" and p.roles == {"TEACHER", "ROLE_X"} and p.status == "ACTIVE"
