"""
AgentOS Schedules
==================
"""

from os import getenv
from typing import Any

from agno.scheduler import ScheduleManager
from agno.utils.log import log_info, log_warning

from db import get_postgres_db


def env_flag(name: str, default: bool) -> bool:
    """Read a boolean env var, accepting 1/true/yes (any casing) as true."""
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes")


def _register(
    manager: ScheduleManager,
    *,
    name: str,
    cron: str,
    endpoint: str,
    payload: dict[str, Any],
    description: str,
    enabled: bool = True,
) -> None:
    """Create or update a schedule; failures log a warning instead of crashing the app."""
    try:
        schedule = manager.create(
            name=name,
            cron=cron,
            endpoint=endpoint,
            payload=payload,
            description=description,
            if_exists="update",
        )
        # A new schedule lands in the DB with updated_at unset; follow-on writes
        # (updates, enable/disable) set it. Unset means this boot created the row.
        created = schedule.updated_at is None
        if created and not enabled:
            disabled = manager.disable(schedule.id)
            if disabled is None or disabled.enabled:
                raise RuntimeError("created enabled but could not be disabled — will retry next boot")
    except Exception as exc:
        log_warning(f"schedules: could not register '{name}': {exc}")
    else:
        if created and not enabled:
            log_info(f"schedules: registered '{name}' (disabled — enable it from the AgentOS UI)")
        else:
            log_info(f"schedules: registered '{name}'")


def register_schedules() -> None:
    """Register schedules (idempotent and fail-soft).

    The deployment check runs daily by default. Run-evals is registered but
    disabled because it uses model calls. Turn it on from the AgentOS UI.
    """
    if getenv("ENABLE_SCHEDULED_EVALS") is not None:
        log_warning(
            "schedules: ENABLE_SCHEDULED_EVALS is no longer read — the run-evals schedule is "
            "always registered and its enabled state is managed from the AgentOS UI or the "
            "/schedules API."
        )

    try:
        manager = ScheduleManager(get_postgres_db())
    except Exception as exc:
        log_warning(f"schedules: could not initialize ScheduleManager: {exc}")
        return

    if env_flag("ENABLE_DEPLOY_CHECK", default=True):
        _register(
            manager,
            name="deployment-check",
            cron="0 13 * * *",  # 13:00 UTC daily
            endpoint="/workflows/deployment-check/runs",
            payload={"message": "Scheduled deployment check."},
            description="Daily: verify platform wiring and readiness.",
        )
    else:
        log_info("schedules: deployment-check disabled (ENABLE_DEPLOY_CHECK=False)")

    _register(
        manager,
        name="run-evals",
        cron="0 14 * * *",  # 14:00 UTC daily
        endpoint="/workflows/run-evals/runs",
        payload={"message": "Scheduled eval run."},
        description="Daily: run the eval suite and report regressions.",
        enabled=False,
    )
