"""
AgentOS Registry
================

The tools, functions, models, databases, and agents available to AgentOS Studio.
"""

from os import getenv

from agno.registry import Registry
from agno.tools.mcp import MCPTools
from agno.tools.parallel import ParallelTools
from agno.tools.reasoning import ReasoningTools

from agents.chief import chief
from agents.platform_manager import platform_manager
from app.settings import default_model
from db import get_postgres_db

AGNO_DOCS_MCP_URL = "https://docs.agno.com/mcp"


def get_agno_docs_tools() -> list[MCPTools]:
    return [MCPTools(transport="streamable-http", url=AGNO_DOCS_MCP_URL, name="agno_docs")]


def get_parallel_tools() -> list[ParallelTools | MCPTools]:
    if getenv("PARALLEL_API_KEY"):
        return [ParallelTools()]
    # timeout_seconds: web_fetch page extraction regularly exceeds the 10s MCP default.
    return [
        MCPTools(
            url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
        )
    ]


def route_component_type(request: str) -> str:
    """Suggest agent, team, or workflow from a plain-language request."""
    lower = request.lower()
    if any(word in lower for word in ("daily", "schedule", "pipeline", "approval", "steps", "workflow")):
        return "workflow"
    if any(word in lower for word in ("team", "specialists", "debate", "reviewers", "coordinate")):
        return "team"
    return "agent"


def score_eval_status(passed: int, total: int) -> str:
    """Return PASS only when every selected eval case passed."""
    if total <= 0:
        return "FAIL"
    return "PASS" if passed == total else "FAIL"


registry = Registry(
    name="AgentOS Registry",
    tools=[
        *get_agno_docs_tools(),
        *get_parallel_tools(),
        ReasoningTools(add_instructions=True),
    ],
    models=[default_model()],
    dbs=[get_postgres_db()],
    functions=[route_component_type, score_eval_status],
    agents=[chief, platform_manager],
)
