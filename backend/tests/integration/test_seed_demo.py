from sqlalchemy import func, select

from app.extensions import db
from app.integrations import fixtures_demo as fx
from app.models import Acta, Asistencia, Calificacion, Clase, Examen, MockCoreUser, OutboxEvent
from app.seed import load_mock_core_seed
from app.seed_demo import load_demo_seed
from tests.conftest import make_app
from tests.helpers import as_teacher


def _count(model, *where):
    return db.session.scalar(select(func.count()).select_from(model).where(*where))


def test_demo_seed_is_consistent_and_usable(database_url):
    app = make_app(database_url, MOCK_DATASET="demo")
    with app.app_context():
        assert load_demo_seed() is True
        assert load_demo_seed() is False  # idempotent
        assert load_mock_core_seed("demo") == len(fx.PROFILES) + 1  # + secretaría académica
        assert _count(MockCoreUser) == len(fx.PROFILES) + 1

        assert _count(Clase, Clase.curso_id == 42) == 10
        assert _count(Clase, Clase.curso_id == 43) == 11
        assert _count(Clase, Clase.curso_id == 30) == 15
        assert _count(Asistencia) == 10 * 25 + 11 * 20 + 15 * 16
        assert _count(Examen) == 13
        assert _count(Calificacion) > 100

        actas = {a.numero: a for a in db.session.scalars(select(Acta))}
        assert {n: (a.tipo, a.estado) for n, a in actas.items()} == {
            "2026-001": ("CURSADA", "GENERADA"),
            "2026-002": ("FINAL", "ANULADA"),
            "2026-003": ("FINAL", "GENERADA"),
        }
        cursada = {d.alumno_id: d.resultado for d in actas["2026-001"].detalles}
        for d in actas["2026-003"].detalles:
            status, grade = fx.COURSE_30_OUTCOMES[d.alumno_id]
            assert (cursada[d.alumno_id] if d.resultado == "AUSENTE" else d.resultado) == status
            if d.resultado != "AUSENTE":
                assert d.nota == grade
        assert _count(OutboxEvent, OutboxEvent.status != "SENT") == 0
        assert _count(OutboxEvent, OutboxEvent.event_type == "teacher.acta-annulled.v1") == 1

    c = app.test_client()
    students = c.get("/api/v1/courses/42/students", headers=as_teacher()).get_json()
    assert len(students) == 25 and {s["profile"]["fullName"] for s in students} >= {
        "Juan Pérez",
        "Sofía Martínez",
    }
    carlos = as_teacher(fx.CARLOS)
    r = c.post("/api/v1/actas", headers=carlos, json={"courseId": 43, "type": "CURSADA"})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["number"] == "2026-004"
