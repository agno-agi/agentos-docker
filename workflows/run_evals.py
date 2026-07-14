"""
Run Evals
=========

Workflow that runs a tagged subset of the eval suite and returns a compact report.
"""

import asyncio
from os import getenv

from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from db import get_postgres_db


def _int_env(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _format_summary(payload: dict) -> str:
    summary = payload.get("summary", {})
    status = summary.get("status", "FAIL")
    lines = [
        "# Evals",
        "",
        f"Overall: **{status}** ({summary.get('passed', 0)}/{summary.get('total', 0)} passed)",
        "",
    ]
    for case in payload.get("cases", []):
        result = "PASS" if case.get("passed") else "FAIL"
        duration = case.get("duration_seconds", 0)
        detail = f"{result} `{case.get('name')}` ({duration}s)"
        if case.get("error"):
            detail += f" — {case['error']}"
        lines.append(f"- {detail}")
    return "\n".join(lines)


async def run_evals_step(_step_input: StepInput) -> StepOutput:
    """Run the configured eval tag in-process and return a markdown summary."""
    # Imported lazily so the eval suite only loads when the workflow actually runs.
    from agno.eval import arun_cases

    from evals.cases import CASES, eval_db

    tag = getenv("EVALS_TAG", "smoke")
    case_timeout_seconds = _int_env("EVALS_CASE_TIMEOUT_SECONDS", 90)
    # 900 bounds the smoke tag's worst case: per-case ceilings sum past 600s
    # now that builder cases add snapshot/teardown DB calls and a timeout grace.
    suite_timeout_seconds = _int_env("EVALS_SUITE_TIMEOUT_SECONDS", 900)

    try:
        suite = await asyncio.wait_for(
            arun_cases(CASES, tag=tag, default_timeout=case_timeout_seconds, db=eval_db),
            timeout=suite_timeout_seconds,
        )
    except TimeoutError:
        return StepOutput(
            content=(
                "# Evals\n\n"
                f"Overall: **FAIL** — `{tag}` cases exceeded {suite_timeout_seconds}s "
                "(EVALS_SUITE_TIMEOUT_SECONDS)."
            ),
            success=False,
        )

    return StepOutput(
        content=_format_summary(suite.to_dict()),
        success=suite.status == "PASS",
    )


run_evals = Workflow(
    id="run-evals",
    name="Run Evals",
    db=get_postgres_db(),
    steps=[Step(name="run-evals", executor=run_evals_step)],
)
