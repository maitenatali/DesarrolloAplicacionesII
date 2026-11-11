from __future__ import annotations

import logging
import time

import click
from flask import Flask

log = logging.getLogger("app.cli")


def register_cli(app: Flask) -> None:
    from app.services import event_service

    @app.cli.command("outbox-worker")
    def outbox_worker() -> None:
        """Loop: deliver due outbox events forever (run ONE of these)."""
        poll = app.extensions["settings"].outbox_poll_seconds
        log.info("outbox_worker_started")
        while True:
            try:
                stats = event_service.dispatch_due()
                if any(stats.values()):
                    log.info("outbox_pass", extra=stats)
            except Exception:
                log.exception("outbox_pass_failed")
            time.sleep(poll)

    @app.cli.command("outbox-once")
    def outbox_once() -> None:
        """Single dispatch pass (cron / tests)."""
        click.echo(event_service.dispatch_due())

    @app.cli.command("outbox-requeue")
    @click.option("--failed", is_flag=True, required=True, help="Reset FAILED events to PENDING.")
    def outbox_requeue(failed: bool) -> None:
        click.echo(f"requeued={event_service.requeue_failed()}")

    @app.cli.command("outbox-prune")
    @click.option("--days", default=30, show_default=True)
    def outbox_prune(days: int) -> None:
        """Delete SENT events older than N days."""
        click.echo(f"deleted={event_service.prune_sent(days)}")

    @app.cli.command("seed")
    @click.option("--no-acta", is_flag=True, help="Skip the sample FINAL acta (it locks the FINAL exam).")
    def seed(no_acta: bool) -> None:
        """Load the sample data. MOCK_DATASET=base: course 42 of Appendix B; demo: realistic semester."""
        from app.seed import load_mock_core_seed, load_seed
        from app.seed_demo import load_demo_seed

        settings = app.extensions["settings"]
        if settings.mock_dataset == "demo":
            click.echo("demo seeded" if load_demo_seed() else "already seeded")
        else:
            click.echo("seeded" if load_seed(include_acta=not no_acta) else "already seeded")
        if settings.mock_core_enabled:
            click.echo(f"mock CORE users created: {load_mock_core_seed(settings.mock_dataset)}")

    @app.cli.command("openapi")
    @click.option("--out", default="docs/openapi.json", show_default=True)
    def openapi(out: str) -> None:
        """Dump the OpenAPI spec (source for generated frontend types)."""
        import json
        from pathlib import Path

        from app.extensions import spec

        Path(out).write_text(json.dumps(spec.spec, indent=2, ensure_ascii=False), encoding="utf-8")
        click.echo(f"wrote {out}")
