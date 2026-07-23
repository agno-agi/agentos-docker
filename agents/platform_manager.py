"""
Platform Manager Agent
======================
"""

import json
from datetime import datetime, timezone
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


def _iso(timestamp: Any) -> Any:
    """Epoch seconds → ISO 8601 UTC; anything else passes through untouched."""
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    return timestamp


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
    # Reliability evals store PASSED/FAILED; normalize to the judge branch's vocabulary.
    return {"PASSED": "PASS", "FAILED": "FAIL"}.get(str(status), str(status)) if status else None


def _fail_reason(eval_data: Any) -> str | None:
    """The judge's written reason (or reliability's missed-tool info) for a failed run."""
    if not isinstance(eval_data, dict):
        return None
    results = eval_data.get("results")
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict) and not item.get("passed", True):
                reason = item.get("reason") or item.get("failed_tool_calls")
                if reason:
                    return str(reason)[:200]
    return None


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
    rows = []
    for run in runs:
        status = _eval_status(run.get("eval_data"))
        row: dict[str, Any] = {
            "name": run.get("name"),
            "component": run.get("evaluated_component_name") or run.get("agent_id") or run.get("workflow_id"),
            "eval_type": run.get("eval_type"),
            "status": status,
            "created_at": _iso(run.get("created_at")),
        }
        if status == "FAIL":
            row["reason"] = _fail_reason(run.get("eval_data"))
        rows.append(row)
    if not rows:
        return json.dumps(
            {
                "total": 0,
                "runs": [],
                "note": "No eval runs recorded yet — expected on a fresh platform, since the "
                "run-evals schedule ships disabled. Run `python -m evals --tag smoke` from a "
                "coding agent, or enable the run-evals schedule from the AgentOS UI.",
            }
        )
    return json.dumps({"total": total, "runs": rows}, default=str)


def get_deployment_check_report(limit: int = 3) -> str:
    """The latest deployment-check reports: readiness of DB, auth, scheduler URL, MCP
    reachability, Slack, schedule state, and component imports.

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
                "note": "No deployment-check runs recorded yet. Call run_deployment_check to "
                "produce one now (humans can POST /workflows/deployment-check/runs).",
            }
        )
    reports.sort(key=lambda report: report["created_at"] or 0, reverse=True)
    for report in reports:
        report["created_at"] = _iso(report["created_at"])
    return json.dumps({"reports": reports[:limit]}, default=str)


def list_schedules(limit: int = 100) -> str:
    """Registered cron schedules with cadence, endpoint, enabled state, next run time,
    and each schedule's most recent trigger outcome (status, error) — so a schedule that
    fires but fails is visible, not just one that is due.

    Args:
        limit: Maximum number of schedules to return.
    """
    schedules, total = _db.get_schedules(limit=limit)
    rows = []
    for schedule in schedules:
        row = {
            key: schedule.get(key)
            for key in ("id", "name", "cron_expr", "timezone", "endpoint", "enabled", "description")
        }
        row["next_run_at"] = _iso(schedule.get("next_run_at"))
        schedule_runs = _db.get_schedule_runs(str(schedule.get("id")), limit=1)
        runs_list = schedule_runs[0] if isinstance(schedule_runs, tuple) else schedule_runs
        if runs_list:
            last = runs_list[0]
            last_run = last if isinstance(last, dict) else last.to_dict()
            row["last_run"] = {
                "status": last_run.get("status"),
                "status_code": last_run.get("status_code"),
                "error": last_run.get("error"),
                "completed_at": _iso(last_run.get("completed_at")),
            }
        rows.append(row)
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
    rows = []
    for component in components:
        row = {key: component.get(key) for key in ("component_id", "component_type", "name", "current_version")}
        row["created_at"] = _iso(component.get("created_at"))
        row["updated_at"] = _iso(component.get("updated_at"))
        rows.append(row)
    return json.dumps({"total": total, "components": rows}, default=str)


INSTRUCTIONS = """\
You are Platform Manager. You understand, monitor, and explain this AgentOS, and you
recommend what to do next. You are read-only: never claim to change code, components, schedules, or data.

You have two lenses; pick by question, combine them when diagnosing:
- `query_my_codebase` — how the platform is wired: agents, workflows, registry, schedules,
  env vars, skills. Be specific and grounded; quote real file paths and line numbers.
- Runtime tools — how it is doing: `get_eval_history` (eval PASS/FAIL over time, with the
  judge's reason on failures), `get_deployment_check_report` (readiness of DB, auth,
  scheduler URL, MCP reachability, Slack, schedule state, component imports),
  `run_deployment_check` (fresh readiness report on demand), `list_schedules` (crons,
  next runs, and each schedule's last trigger outcome), `list_platform_components`
  (components built at runtime by Agent Builder).

The run-evals schedule ships disabled by design — it spends model calls — so
`enabled=false` on it is not a fault: enabling it is a UI action (or
POST /schedules/{id}/enable), never a code change.

Diagnostics are within your read-only mandate: `run_deployment_check` is deterministic,
free, and non-mutating — when no deployment-check report exists or the latest looks stale,
run it and answer from the fresh result instead of telling the user how to run it.

For broad questions about the platform — which agents, workflows, schedules, or skills it
ships and how to use it — ask the workspace for `AGENTS.md` (the repo's source-of-truth
overview) and answer from it, reading other files only for specifics it doesn't cover. When
onboarding someone, keep the tour compact — a handful of sections, not a handbook: open with
the coding-agent skills in `.agents/skills/`, each by name, framed as the arc they form
(build → iterate → eval → deploy), then Agent Builder creating agents, teams, and workflows
from the AgentOS UI, Slack, or any MCP frontend via the safe Studio registry, then a few
concrete first prompts or commands to try — and touch the platform basics in a line each: the
registered agents, Postgres persistence (sessions, memory, knowledge), the scheduler with its
deployment-check, the MCP endpoint at `/mcp` (claude.ai, ChatGPT, Claude Code, and Cursor
connect there), and the Slack and JWT gates. Skip exhaustive file-by-file or
endpoint-by-endpoint detail unless asked.

When something the user asks about does not exist in the platform — a function, file, agent,
or table — say so plainly and stop. Do not enumerate incidental text mentions of the name
(eval fixtures, scratch files under tmp/, session logs) unless the user asks where the string
appears.

When something looks wrong, diagnose the likely cause across both lenses, then hand off:
code or prompt fixes go to a coding agent (name the matching skill — /eval-and-improve for
failing evals, /extend-agent or /improve-agent for agent behavior, /deploy-platform for
production and deploy-layer issues, /review-and-improve when docs and code disagree); new or
changed components go to Agent Builder; anything else, state the exact command or action for
the human to take.

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
