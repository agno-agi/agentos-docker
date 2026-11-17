"""Reach Super Agent through MCP and, when configured, Slack."""

from os import getenv

from agno.os import AgentOS, AgentOSBuiltinAuth, Authorization, MCPConfig


def mcp_auth(agentos_url: str) -> AgentOSBuiltinAuth | None:
    """Enable MCP OAuth when the MCP_CONNECT_SECRET is provided."""
    secret = getenv("MCP_CONNECT_SECRET")
    if not secret:
        return None
    return AgentOSBuiltinAuth(url=agentos_url, secret=secret)


def authorization() -> Authorization:
    """Give Slack members the slack-member role; os.agno.com sign-ins keep their token scopes."""
    authz = Authorization(trust_token_scopes=True)
    authz.define_role(
        "slack-member",
        [
            "agents:read",
            "agents:run",
            "teams:run",
            "workflows:run",
            "company:read",
            "products:read",
            "products:write",
            "routines:write",
            "projects:read",
            "projects:write",
            "tasks:read",
            "tasks:write",
            "wiki:read",
            "wiki:write",
            "sources:read",
            "sources:write",
            "decisions:read",
            "decisions:write",
            "components:read",
            "components:write",
            "registry:read",
            "schedules:read",
            "schedules:write",
            "config:read",
        ],
    )
    return authz


def attach_interfaces(agent_os: AgentOS) -> None:
    """Publish Super Agent alongside the built-in MCP tools; optionally attach Slack."""
    manager = agent_os.manager
    if manager is None:
        raise RuntimeError("Super Agent must be configured before attaching interfaces.")
    agent_os.mcp = MCPConfig(
        tools=[
            manager.as_tool(
                name="super_agent",
                title="Super Agent",
                description="Talk to Super Agent on this AgentOS.",
            )
        ],
        default_tools=True,
    )
    token, secret = getenv("SLACK_BOT_TOKEN"), getenv("SLACK_SIGNING_SECRET")
    if token and secret:
        from agno.os.interfaces.slack import Slack

        agent_os.interfaces.append(
            Slack(
                team=manager,
                token=token,
                streaming=True,
                signing_secret=secret,
                resolve_user_identity=True,
                default_role="slack-member",
                loading_text="Pulling the thread...",
            )
        )
