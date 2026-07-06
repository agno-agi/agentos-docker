"""
WebSearch Agent
===============
"""

from os import getenv

from agno.agent import Agent
from agno.tools.mcp import MCPTools
from agno.tools.parallel import ParallelTools

from app.settings import default_model
from db import get_postgres_db

# When PARALLEL_API_KEY is set, use the parallel-web SDK.
# Without a key, fall back to the keyless MCP endpoint.
# AgentOS handles MCP connect/close as part of its lifespan.
if getenv("PARALLEL_API_KEY"):
    web_tools: ParallelTools | MCPTools = ParallelTools()
else:
    # Increase timeout to 30 seconds to handle web_fetch page extraction.
    web_tools = MCPTools(
        url="https://search.parallel.ai/mcp", transport="streamable-http", name="parallel_tools", timeout_seconds=30
    )


WEB_SEARCH_INSTRUCTIONS = """\
Search the web for current information. Keep your answers grounded in the information you find. Don't over-search.

Workflow:
1. Use the search tool to find candidate sources for the question.
2. For recent-event, 'latest', or 'recently' questions, answer only from search results you actually found in this run; do not infer newer publications, titles, or dates beyond what the results support.
3. When the user asks about specific pages, or when search snippets are too thin to safely summarize a recent claim, follow up with the extract / fetch tool to read the most relevant URLs before answering.
4. Cite the sources you used as plain URLs. Prefer recent, authoritative pages. If you cannot find a good answer, say so plainly.
5. If search or fetch fails or returns nothing usable, say so and stop — never substitute an answer from prior knowledge, even with caveats. Offer to retry or let the user paste the content instead.\
"""


web_search = Agent(
    id="web-search",
    name="WebSearch",
    model=default_model(),
    db=get_postgres_db(),
    tools=[web_tools],
    instructions=WEB_SEARCH_INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
