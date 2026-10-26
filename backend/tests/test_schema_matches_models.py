"""Drift guard: the migrated DB must satisfy every ORM model (Python equivalent of ddl-auto: validate)."""

from sqlalchemy import inspect, text

from app.extensions import db


def test_models_match_migrated_schema(app):
    with app.app_context():
        insp = inspect(db.engine)
        problems = []
        for table in db.metadata.sorted_tables:
            is_view = table.info.get("is_view")
            names = set(insp.get_view_names()) if is_view else set(insp.get_table_names())
            if table.name not in names:
                problems.append(f"missing {'view' if is_view else 'table'} {table.name}")
                continue
            cols = {c["name"]: c for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in cols:
                    problems.append(f"{table.name}.{col.name} missing in DB")
                    continue
                if not is_view and cols[col.name]["nullable"] != col.nullable and not col.primary_key:
                    problems.append(f"{table.name}.{col.name} nullability differs")
        assert not problems, problems


def test_partial_unique_indexes_exist(app):
    with app.app_context():
        rows = (
            db.session.execute(text("select indexname from pg_indexes where schemaname='public'"))
            .scalars()
            .all()
        )
    for name in ("examen_curso_tipo_activo_uk", "acta_vigente_uk", "outbox_event_due_idx"):
        assert name in rows


def test_views_are_security_invoker(app):
    with app.app_context():
        opts = db.session.execute(
            text(
                "select relname, reloptions from pg_class where relname in "
                "('asistencia_por_alumno','resultado_por_alumno')"
            )
        ).all()
    assert len(opts) == 2 and all("security_invoker=true" in (o[1] or []) for o in opts)


def test_migration_roundtrip(app):
    from flask_migrate import downgrade, upgrade

    from app import MIGRATIONS_DIR

    with app.app_context():
        downgrade(directory=MIGRATIONS_DIR, revision="base")
        names = set(inspect(db.engine).get_table_names())
        assert "acta" not in names and "outbox_event" not in names
        upgrade(directory=MIGRATIONS_DIR)
        assert "outbox_event" in set(inspect(db.engine).get_table_names())
