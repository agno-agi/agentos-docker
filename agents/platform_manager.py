"""
Platform Manager Agent
======================
"""

import json
from pathlib import Path
from typing import Any, cast

from agno.agent import Agent
from agno.context.workspace import WorkspaceContextProvider
from agno.db.base import SessionType

from app.settings import default_model
from db import get_postgres_db

REPO_ROOT = Path(__file__).resolve().parents[1]

codebase_context = WorkspaceContextProvider(
    id="my-codebase",
    name="My Codebase",
    root=REPO_ROOT,
    model=default_model(),
)

_db = get_postgres_db()


def _eval_status(eval_data: Any) -> str | None:
    """Compact PASS/FAIL from an eval run's stored payload."""
    if not isinstance(eval_data, dict):
        return None
    results = eval_data.get("results")
    if isinstance(results, list):
        verdicts = [bool(item.get("passed")) for item in results if isinstance(item, dict) and "passed" in item]
        if verdicts:
            return "PASS" if all(verdicts) else "FAIL"
    status = eval_data.get("eval_status")
    return str(status) if status else None


def get_eval_history(limit: int = 20) -> str:
    """Recent eval runs with name, evaluated component, eval type, PASS/FAIL, and timestamp.

    Args:
        limit: Maximum number of eval runs to return, newest first.
    """
    # deserialize=False always returns (rows, count); the annotation is a union.
    runs, total = cast(
        tuple[list[dict[str, Any]], int],
        _db.get_eval_runs(limit=limit, sort_by="created_at", sort_order="desc", deserialize=False),
    )
    rows = [
        {
            "name": run.get("name"),
            "component": run.get("evaluated_component_name") or run.get("agent_id") or run.get("workflow_id"),
            "eval_type": run.get("eval_type"),
            "status": _eval_status(run.get("eval_data")),
            "created_at": run.get("created_at"),
        }
        for run in runs
    ]
    return json.dumps({"total": total, "runs": rows}, default=str)


def get_deployment_check_report(limit: int = 3) -> str:
    """The latest deployment-check reports: readiness of DB, auth, scheduler URL, Slack, and components.

    Args:
        limit: Maximum number of past workflow runs to return, newest first.
    """
    # deserialize=False always returns (rows, count); the annotation is a union.
    sessions, _ = cast(
        tuple[list[dict[str, Any]], int],
        _db.get_sessions(
            session_type=SessionType.WORKFLOW,
            component_id="deployment-check",
            limit=limit,
            sort_by="created_at",
            sort_order="desc",
            deserialize=False,
        ),
    )
    reports = []
    for session in sessions:
        for run in session.get("runs") or []:
            if isinstance(run, dict) and run.get("content"):
                reports.append(
                    {
                        "status": run.get("status"),
                        "created_at": run.get("created_at"),
                        "report": run.get("content"),
                    }
                )
    if not reports:
        return json.dumps(
            {
                "reports": [],
                "note": "No deployment-check runs recorded yet. It can be run on demand: "
                "POST /workflows/deployment-check/runs",
            }
        )
    return json.dumps({"reports": reports[:limit]}, default=str)


def list_schedules(limit: int = 100) -> str:
    """Registered cron schedules with cadence, endpoint, enabled state, and next run time.

    Args:
        limit: Maximum number of schedules to return.
    """
    schedules, total = _db.get_schedules(limit=limit)
    rows = [
        {
            key: schedule.get(key)
            for key in ("id", "name", "cron_expr", "timezone", "endpoint", "enabled", "next_run_at")
        }
        for schedule in schedules
    ]
    return json.dumps({"total": total, "schedules": rows}, default=str)


async def run_deployment_check() -> str:
    """Run the deployment-check workflow now and return the fresh readiness report.

    A diagnostic, not a mutation: deterministic, free (no model calls), and idempotent —
    it observes DB connectivity, auth config, scheduler URL, MCP reachability, Slack env,
    schedule state, and component imports. The run persists like any workflow run, so
    get_deployment_check_report and the UI history see it immediately.
    """
    # Imported lazily: the workflow module is only needed when the diagnostic runs.
    from workflows.deployment_check import deployment_check

    output = await deployment_check.arun(input="On-demand deployment check (Platform Manager).")
    content = getattr(output, "content", None)
    return str(content) if content else "Deployment check completed but produced no report."


def list_platform_components(limit: int = 50) -> str:
    """Agents, teams, and workflows built at runtime by Agent Builder, with type and current version.

    Args:
        limit: Maximum number of components to return.
    """
    components, total = _db.list_components(limit=limit)
    rows = [
        {key: component.get(key) for key in ("component_id", "component_type", "name", "current_version", "created_at")}
        for component in components
    ]
    return json.dumps({"total": total, "components": rows}, default=str)


INSTRUCTIONS = """\
You are Platform Manager. You understand, monitor, and explain this AgentOS, and you
recommend what to do next. You are read-only: never claim to change code, components, schedules, or data.

You have two lenses; pick by question, combine them when diagnosing:
- `query_my_codebase` — how the platform is wired: agents, workflows, registry, schedules,
  env vars, skills. Be specific and grounded; quote real file paths and line numbers.
- Runtime tools — how it is doing: `get_eval_history` (eval PASS/FAIL over time),
  `get_deployment_check_report` (readiness of DB, auth, scheduler, Slack, components),
  `run_deployment_check` (fresh readiness report on demand), `list_schedules` (crons and
  next runs), `list_platform_components` (components built at runtime by Agent Builder).

Diagnostics are within your read-only mandate: `run_deployment_check` is deterministic,
free, and non-mutating — when no deployment-check report exists or the latest looks stale,
run it and answer from the fresh result instead of telling the user how to run it.

For broad questions about the platform — which agents, workflows, schedules, or skills it
ships and how to use it — ask the workspace for `AGENTS.md` (the repo's source-of-truth
overview) and answer from it, reading other files only for specifics it doesn't cover. When
onboarding someone, keep the tour compact — a handful of sections, not a handbook: open with
the coding-agent skills lifecycle in `.agents/skills/` (all five skills by name), then Agent
Builder creating agents, teams, and workflows from the AgentOS UI, Slack, or any MCP frontend
via the safe Studio registry, then a few concrete first prompts or commands to try — and touch
the platform basics in a line each: the registered agents, Postgres persistence (sessions,
memory, knowledge), the scheduler with its deployment-check, and the Slack and JWT gates. Skip
exhaustive file-by-file or endpoint-by-endpoint detail unless asked.

When something the user asks about does not exist in the platform — a function, file, agent,
or table — say so plainly and stop. Do not enumerate incidental text mentions of the name
(eval fixtures, scratch files under tmp/, session logs) unless the user asks where the string
appears.

When something looks wrong, diagnose the likely cause across both lenses, then hand off:
code or prompt fixes go to a coding agent (name the matching skill — /eval-and-improve for
failing evals, /extend-agent or /improve-agent for agent behavior); new or changed components
go to Agent Builder; anything else, state the exact command or action for the human to take.

If a request is off-topic — not answerable from the platform's files or runtime data,
including creative writing and general tech trivia unrelated to this platform — say so
plainly and offer what you can answer instead.\
"""


platform_manager = Agent(
    id="platform-manager",
    name="Platform Manager",
    model=default_model(),
    db=_db,
    tools=[
        *codebase_context.get_tools(),
        get_eval_history,
        get_deployment_check_report,
        run_deployment_check,
        list_schedules,
        list_platform_components,
    ],
    instructions=INSTRUCTIONS + codebase_context.instructions(),
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
