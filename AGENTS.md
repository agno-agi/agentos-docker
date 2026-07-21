# AgentOS — Docker template

This file is the source of truth for any agent (Claude Code, Codex, others) working in this repo. `CLAUDE.md` is a symlink to this file — edit one, both update.

## Project Overview

**AgentOS: FastAPI for agents — one AI backend for every frontend.** AgentOS is an agent server built on [Agno](https://docs.agno.com) that turns your agents into a production API that attaches to any client: **REST API** for programmatic use, **chat interfaces** for humans (Slack is wired in; WhatsApp/Telegram/Discord mirror the same pattern), and **MCP** at `/mcp` for AI apps (claude.ai, ChatGPT, Cursor, Claude Code) — which work *through* the platform, not just on it. The repo itself is designed for coding agents to build and extend. It comes with six coding agent skills that manage platform setup and the full agent development lifecycle and two platform agents — Agent Builder (creates agents, teams, and workflows) and Platform Manager (understands, monitors, and explains the platform) — plus WebSearch as the simplest sample agent to copy. Postgres (pgvector) handles persistence for sessions, memory, and knowledge. Runs locally via Docker; this template also runs production with Docker — on any host you control, with no cloud provider in between — and is the self-hosted sibling of the `agentos-*` deployment family — see [Portable core vs. deploy layer](#portable-core-vs-deploy-layer).

## Architecture

```
AgentOS  (app/main.py)
├── WebSearch    (agents/web_search.py)   — Parallel SDK or keyless MCPTools
├── Platform Manager (agents/platform_manager.py) — WorkspaceContextProvider + read-only runtime tools
├── Agent Builder (agents/agent_builder.py) — Agno docs MCP + StudioTools
├── DeployCheck  (workflows/deployment_check.py) — deterministic readiness workflow
└── RunEvals     (workflows/run_evals.py) — opt-in eval suite workflow
```

Shared:
- PostgreSQL + pgvector for sessions, memory, knowledge.
- `app.settings.default_model()` returns `OpenAIResponses(id="gpt-5.6-sol")` — bump the model in one place.
- `app.registry.registry` exposes the safe Studio registry Agent Builder can use: Agno docs MCP, web search, reasoning tools, utility functions, the default model, the shared DB, and the reference agents (web-search, platform-manager).
- Scheduler enabled by default (`scheduler=True`); `app/schedules.py` registers schedules from the lifespan. Deployment check runs daily **on** by default — set `ENABLE_DEPLOY_CHECK=False` to disable it. Scheduled evals are **off** by default — set `ENABLE_SCHEDULED_EVALS=True` to schedule the run-evals workflow.
- Slack interface lights up automatically when both `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` are set.
- MCP server on by default (`mcp_server=True`) at `/mcp` — see [MCP interface](#mcp-interface).
- MCP OAuth lights up when `MCP_CONNECT_SECRET` is set (built-in authorization server) — how claude.ai and ChatGPT (web) connect; see [MCP interface](#mcp-interface).
- JWT auth on whenever `RUNTIME_ENV` is anything but `dev` (so production deploys, which default to `prd`, are gated by default).

## Key Files

| File | Purpose |
|------|---------|
| [`app/main.py`](app/main.py) | AgentOS entrypoint — lifespan hook, conditional Slack, conditional MCP OAuth, JWT gate. |
| [`app/settings.py`](app/settings.py) | `default_model()` factory. |
| [`app/registry.py`](app/registry.py) | Safe Studio registry used by Agent Builder — docs MCP, web tools, utility functions, reference agents. |
| [`app/config.yaml`](app/config.yaml) | UI manifest per component (keyed by `id`): description + quick prompts. |
| [`agents/web_search.py`](agents/web_search.py) | Reference agent — direct tools (Parallel SDK or MCP). |
| [`agents/platform_manager.py`](agents/platform_manager.py) | Flagship agent — codebase context provider + read-only runtime tools (eval history, deployment-check reports + on-demand diagnostic run, schedules, components). |
| [`agents/agent_builder.py`](agents/agent_builder.py) | Reference agent — creates, edits, and publishes agents, teams, and workflows through StudioTools immediately; only deletes keep a HITL confirmation gate. |
| [`workflows/deployment_check.py`](workflows/deployment_check.py) | Reference workflow — a deterministic `Step` that checks DB, auth, scheduler URL, MCP reachability, Slack config, schedule flags, and component imports; imported into `app/main.py` and passed to `AgentOS(workflows=[...])`. |
| [`workflows/run_evals.py`](workflows/run_evals.py) | Optional workflow — runs a tagged subset of the eval suite and returns a compact report. Registered but not scheduled unless `ENABLE_SCHEDULED_EVALS=True`. |
| [`app/schedules.py`](app/schedules.py) | `register_schedules()` — cron registration, called from the lifespan (idempotent, fail-soft). |
| [`db/session.py`](db/session.py) | `get_postgres_db()`, `create_knowledge()`. |
| [`db/url.py`](db/url.py) | Builds the database URL from env. |
| [`evals/cases.py`](evals/cases.py) | Eval cases (each is a `Case` with optional judge + reliability checks). |
| [`evals/__main__.py`](evals/__main__.py) | `python -m evals` — thin entrypoint over agno's eval suite runner (`agno.eval.cli`). |
| [`.agents/skills/`](.agents/skills/) | Dev-time **coding-agent workflows** (`setup-platform`, `create-new-agent`, `extend-agent`, `improve-agent`, `eval-and-improve`, `review-and-improve`) — slash commands coding agents run *on this repo*. `.claude/skills` is a committed symlink into it — see [Working with coding agents](#working-with-coding-agents). |
| [`README.md`](README.md) | Public entry point — its Get Started prompt hands a coding agent to the `setup-platform` skill (clone to first agent). |
| [`compose.yaml`](compose.yaml) | Docker Compose for local development. |
| [`compose.prod.yaml`](compose.prod.yaml) | Production override — `RUNTIME_ENV=prd` (JWT on), no bind mount or hot reload, `AGENTOS_URL` and `MCP_CONNECT_SECRET` from `.env`. |

## Development Setup

### Local with Docker

```bash
cp example.env .env
# Edit .env and set OPENAI_API_KEY

docker compose up -d --build
```

`compose.yaml` sets `RUNTIME_ENV=dev`, `AGNO_DEBUG=True`, and `WAIT_FOR_DB=True` so JWT is off and the API blocks on the DB before serving. It runs uvicorn with a scoped `--reload` (watching `agents/`, `app/`, `db/`, `evals/`, `workflows/`), so code edits hot-reload in a second or two. Restart `agentos-api` after dependency or env changes, or whenever you want a guaranteed-clean state.

### Format & Validate

The format / validate / eval scripts run on the host, so they need a venv. Set one up once:

```bash
./scripts/venv_setup.sh
source .venv/bin/activate
```

Then:

```bash
./scripts/format.sh     # ruff format + import sort
./scripts/validate.sh   # ruff check + mypy (runs both, summarizes)
```

CI installs the same pinned `requirements.txt` and runs the same `scripts/validate.sh` — local and CI never drift.

## Conventions

### Agent pattern

Every agent file has the same shape:

```python
"""
<Title> Agent
=============
"""

from agno.agent import Agent

from app.settings import default_model
from db import get_postgres_db

INSTRUCTIONS = """\
<one short paragraph: what the agent does, which tools it uses, the
rules to follow when answering>
"""

my_agent = Agent(
    id="my-agent",
    name="My Agent",
    model=default_model(),
    db=get_postgres_db(),
    tools=[...],
    instructions=INSTRUCTIONS,
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)
```

Three patterns to copy from:

- **Direct tools** — see [`agents/web_search.py`](agents/web_search.py). The agent sees each tool individually. Best when the user knows which tools the agent needs.
- **Context provider** — see [`agents/platform_manager.py`](agents/platform_manager.py). The agent sees one `query_<thing>` tool that hands off to a sub-agent. Best for one-source agents and when collapsing many tools into one keeps the model focused. Platform Manager also shows combining a provider with direct read-only tools — two lenses on one domain.
- **Studio builder** — see [`agents/agent_builder.py`](agents/agent_builder.py). The agent sees StudioTools, a safe `Registry`, Agno docs MCP, and delete-only confirmation gates: create/edit/publish execute immediately (every mutation lands in the DB as a versioned component — inspectable and reversible), while deletes pause for human approval. Best when the user should create or refine components from the AgentOS UI, Slack, or an MCP frontend.

### Database

```python
# Plain agent — sessions, memory, agentic memory live here
from db import get_postgres_db
agent_db = get_postgres_db()

# Agent with a Knowledge base (RAG) — pass through `knowledge=`
from db import create_knowledge
my_kb = create_knowledge("My Knowledge", "my_vectors")
```

Knowledge bases use PgVector with `SearchType.hybrid` and `text-embedding-3-small`. Document contents go into `<table_name>_contents`.

## Adding a new agent

Two options:

1. **Hand it to Claude Code** — run the `/create-new-agent` skill (or just ask to "create a new agent") in a Claude Code session pointed at this repo. Claude asks the user what the agent should do, generates the file, registers it, smoke-tests it. See [Working with coding agents](#working-with-coding-agents).
2. **Do it manually** — create `agents/<slug>.py`, register in `app/main.py`, add its manifest entry (description + quick prompts) to `app/config.yaml`. The scoped uvicorn reload picks the changes up automatically; restart `agentos-api` if you changed dependencies or env.

## Iterating on an agent

Two recursive loops over the same agent. Use them together.

- **`/extend-agent`** ([`.agents/skills/extend-agent`](.agents/skills/extend-agent/SKILL.md)) — **you drive.** Add a tool, add a capability, refine the prompt, fix a known bug. Claude is the Agno-aware pair-programmer (uses the `agno-docs` MCP for any toolkit research). Loop: change → smoke-test → "anything else?".
- **`/improve-agent`** ([`.agents/skills/improve-agent`](.agents/skills/improve-agent/SKILL.md)) — **Claude drives.** Derives probes from the agent's `INSTRUCTIONS`, judges, edits, re-runs. No user input needed. Loop: probe → judge → edit → re-probe.

Use `/extend-agent` to *change* the agent; use `/improve-agent` to *harden* it against its stated intent. Most fixes from either loop are one sentence in `INSTRUCTIONS`.

## Evals

The eval suite lives in [`evals/`](evals/) and runs on agno's eval suite runner (`agno.eval`): the template declares `Case`s, agno runs them. Each case wraps agno's [`AgentAsJudgeEval`](https://docs.agno.com/evals/agent-as-judge) (LLM judge against a rubric, binary pass/fail) and/or [`ReliabilityEval`](https://docs.agno.com/evals/reliability) (tool-call assertion). Any case whose agent can reach the ungated create/edit/publish Studio tools (anything probing `agent-builder`) must set the snapshot-diff hooks from `evals/cases.py` (`setup=snapshot_component_ids, teardown=cleanup_new_components`) — setup records the Studio component ids before the case and teardown hard-deletes any new ones afterwards, even on timeout. Cases carry tags:

- `smoke` — fast checks that prove the template's self-driving surfaces still work.
- `release` — broader checks for pre-release confidence.
- `live` — current web/source checks that are useful but should not be deterministic release gates.

Run with `python -m evals --tag smoke`, `python -m evals --tag release`, or `python -m evals --name <case>`. Add `--json-output out.json` when a workflow or coding agent needs machine-readable results. Results log to Postgres via `db=eval_db` so history is visible at os.agno.com.

To diagnose failures and fix in scope, run the `/eval-and-improve` skill ([`.agents/skills/eval-and-improve`](.agents/skills/eval-and-improve/SKILL.md)) in Claude Code.

## Reviewing the repo

Run the `/review-and-improve` skill ([`.agents/skills/review-and-improve`](.agents/skills/review-and-improve/SKILL.md)). A recurring sweep that diffs docs against code: every agent registered, every env var documented, every path in a doc still exists, every script behaves as advertised. Auto-fixes mechanical drift; flags anything bigger. Best run before a public-facing release or after a refactor.

## Working with coding agents

Dev-time **coding-agent workflows** live in [`.agents/skills/`](.agents/skills/) — the vendor-neutral home for coding-agent assets, mirroring how `CLAUDE.md` symlinks to `AGENTS.md`. `.claude/skills` is a committed symlink into it, so Claude Code picks the skills up on every clone with no setup step; other harnesses (Codex, Cursor, …) can symlink the same folder. (Windows needs developer mode or `core.symlinks=true` for the symlink to materialize.) Claude-specific config like `.claude/settings.json` stays a real file in `.claude/`.

These workflows cover platform setup and the agent-development lifecycle in this template:

- **`/setup-platform`** — take a fresh clone to a running platform with a first agent live on it: Docker check, `.env`, boot, MCP proof, the AgentOS UI connect, then a `create-new-agent` handoff. The README's Get Started prompt and the os.agno.com onboarding prompt both drive it.
- **`/create-new-agent`** — scaffold a new agent: guided discovery or from a concrete idea → generate `agents/<slug>.py`, register it, smoke-test it live.
- **`/extend-agent`** — you drive. Add a tool/source, refine `INSTRUCTIONS`, fix a known bug. Uses the `agno-docs` MCP for grounded toolkit research.
- **`/improve-agent`** — Claude drives. Derives probes from the agent's `INSTRUCTIONS`, judges, edits, re-runs. No user input needed.
- **`/eval-and-improve`** — run the eval suite, diagnose failures, fix in scope until green.
- **`/review-and-improve`** — repo-wide drift sweep (docs vs code vs config).

Invoke a skill by name (`/extend-agent`) or just describe the task — Claude Code matches it from the skill's `description`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | yes | — | OpenAI key for models + embeddings. |
| `RUNTIME_ENV` | no | `prd` | `dev` disables JWT. `compose.yaml` sets it to `dev` for local; `compose.prod.yaml` sets `prd` — never hand-set `dev` on a production host, or the platform serves unauthenticated. |
| `JWT_VERIFICATION_KEY` | prd | — | Public key from os.agno.com. Required when `RUNTIME_ENV=prd` and `authorization=True`, unless `JWT_JWKS_FILE` is set. |
| `JWT_JWKS_FILE` | prd | — | Path to a JWKS file; alternative to `JWT_VERIFICATION_KEY` for production JWT verification. |
| `AGENTOS_URL` | no | `http://127.0.0.1:8000` | Scheduler base URL — cron triggers reach AgentOS over this. In production, set it in `.env` to your public URL (domain or tunnel); `compose.prod.yaml` passes it through. Left at the localhost default in prod, the daily deployment check flags the platform as misconfigured and hosted chat apps have no connector URL to point at. Also the public origin OAuth metadata derives from when `MCP_CONNECT_SECRET` is set. |
| `MCP_CONNECT_SECRET` | no | — | If set (≥16 chars, e.g. `openssl rand -base64 32`), `/mcp` becomes its own OAuth 2.1 authorization server (built-in tier) so claude.ai and ChatGPT (web) can connect; connecting asks for this secret on a consent page. Requires `AGENTOS_URL`. PAT and JWT bearers keep working alongside. Set it by hand in `.env` — dev and prod share that file here, so it gates the local `/mcp` too. |
| `AGENTOS_MCP_SIGNING_KEY` | no | — | Optional high-entropy signing-key material (≥32 chars) for OAuth tokens. Unset, a strong key is generated and persisted in the database. Rotating it invalidates outstanding tokens. |
| `ENABLE_DEPLOY_CHECK` | no | `True` | The reference deployment-check cron (`app/schedules.py`) runs daily by default. Set `False` to disable; the workflow stays runnable on demand regardless. |
| `ENABLE_SCHEDULED_EVALS` | no | `False` | If `True`, schedules the run-evals workflow daily. Off by default because it uses model calls. |
| `EVALS_TAG` | no | `smoke` | Eval tag run by the run-evals workflow. |
| `EVALS_CASE_TIMEOUT_SECONDS` | no | `90` | Default per-case timeout for run-evals runs; applies only to cases that don't set their own `timeout_seconds`. |
| `EVALS_SUITE_TIMEOUT_SECONDS` | no | `900` | Whole-suite timeout for run-evals runs; per-case timeouts are the granular limit. The default bounds the `smoke` tag's worst case (incl. builder-case teardown). |
| `PARALLEL_API_KEY` | no | — | Authenticates the WebSearch Agent's Parallel SDK / MCP connection (raises rate ceiling). |
| `SLACK_BOT_TOKEN` | no | — | Bot token. Set with signing secret to enable the Slack interface. |
| `SLACK_SIGNING_SECRET` | no | — | Signing secret. Both it and the bot token must be set for the interface to load. |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | no | matches compose | Postgres connection. |
| `DB_DRIVER` | no | `postgresql+psycopg` | SQLAlchemy driver. |
| `AGNO_DEBUG` | no | `False` | If `True`, agno emits verbose debug logs. Compose sets this for dev. |
| `WAIT_FOR_DB` | no | `False` | If `True`, the entrypoint blocks on the DB before starting. Compose sets this. |

## Ports

- API: `8000`
- Database: `5432`

## Scheduler

`scheduler=True` is on in [`app/main.py`](app/main.py). A schedule is a cron expression + an HTTP endpoint (a workflow or agent run); the poller fires due jobs in the background. Registration lives in [`app/schedules.py`](app/schedules.py)'s `register_schedules()`, called from the lifespan — idempotent (`if_exists="update"`, safe on every boot) and fail-soft (a bad schedule logs a warning rather than crashing startup).

**Reference examples.** [`workflows/deployment_check.py`](workflows/deployment_check.py) is a one-step, **deterministic** workflow — no LLM, no token cost — that returns a deployment readiness report. It checks DB connectivity and tables, JWT config, scheduler URL, MCP endpoint reachability, Slack env consistency, schedule flags, and reference component imports. [`app/schedules.py`](app/schedules.py) registers a daily cron that hits its endpoint (`POST /workflows/deployment-check/runs`). Because it's deterministic and free, the cron runs **on** by default (daily at 13:00 UTC); disable it with `ENABLE_DEPLOY_CHECK=False`.

[`workflows/run_evals.py`](workflows/run_evals.py) runs a tagged subset of the eval suite and returns a compact report. It is registered in AgentOS for on-demand use, but its cron is **off** by default because it uses model calls. Set `ENABLE_SCHEDULED_EVALS=True` to schedule the smoke-tagged cases daily at 14:00 UTC.

To add your own: define a `Workflow` in `workflows/`, import it into [`app/main.py`](app/main.py) and add it to `AgentOS(workflows=[...])`, and register a schedule for it in `register_schedules()`. Other common uses: **maintenance** (purge old sessions, vacuum tables), **periodic re-evaluation** (run `python -m evals` weekly to catch regressions).

See [agno scheduler docs](https://docs.agno.com/agent-os/scheduler) for the cron API.

## Platform Manager

The platform's ops surface is the Platform Manager agent ([`agents/platform_manager.py`](agents/platform_manager.py)) — read-only by design. It combines the codebase context provider (how the platform is wired) with runtime tools over Postgres (eval history, deployment-check reports — plus running the deployment check on demand when none exists — schedules, runtime-built components), diagnoses issues across both lenses, and hands off fixes: code changes go to coding agents via the skills in [`.agents/skills/`](.agents/skills/), component changes go to Agent Builder.

Keep it read-only. Least privilege is the point: an ops surface that only reads can't misfire, needs no confirmation gates, and stays safe to expose from any frontend. **Diagnostics are the one sanctioned trigger**: Platform Manager may run observations that are deterministic, free, idempotent, and non-mutating — `run_deployment_check` qualifies (it re-points the same checks the daily cron runs, and the run persists so report history stays coherent); run-evals does not (model spend), and anything that writes platform state never does. Future read tools (trace summaries, `git diff` inspection) belong here; mutations belong with coding agents through git, or behind Agent Builder's delete gate — which an MCP client can now approve in-chat via `continue_run`.

## MCP interface

`mcp_server=True` in [`app/main.py`](app/main.py) mounts an MCP server (streamable HTTP) at `/mcp`, on the same port as the REST API. This is the platform's second interface: chat apps (claude.ai and ChatGPT connectors) and coding agents (Claude Code, Cursor) drive the agents, teams, and workflows through it. The README's setup prompt hands a fresh machine to the [`setup-platform`](.agents/skills/setup-platform/SKILL.md) skill, which takes it from clone to first agent — proving `/mcp` end to end along the way (`scripts/mcp_check.sh`).

- **Tools are generic, not per-agent — eight of them.** `get_agentos_config` (how clients discover valid ids), `run_agent(agent_id, message, session_id)`, `run_team`, `run_workflow`, `continue_run`, `cancel_run`, `get_sessions`, and `get_session_runs`. Sessions are read-only over MCP and there is no memory CRUD. `run_agent` returns a trimmed ToolResult: `content[0].text` is the plain answer, and `structuredContent` carries `{run_id, session_id, status}`. The server needs the `fastmcp` package, which ships with the pinned `agno` dependency.
- **Auth mirrors the REST API, with first-class service accounts.** Dev (`RUNTIME_ENV=dev`) is open (unless MCP OAuth is on — next bullet). In prd the same middleware protects `/mcp`; clients send `Authorization: Bearer <token>`. Two token types work side by side: JWTs minted at os.agno.com, and opaque service-account PATs (`agno_pat_…`) minted via `POST /service-accounts` (the route auto-enables once a db is set). A PAT's default scopes — `agents:run`, `teams:run`, `workflows:run`, `sessions:read`, `config:read` — cover all eight tools, and it attributes as `sa:<name>`. The verified token subject overrides any caller-supplied `user_id`, so identity cannot be spoofed. `uvx agno connect` mints a PAT and registers `/mcp` in Claude Code / Claude Desktop / Codex / Cursor.
- **OAuth for the web chat apps — set `MCP_CONNECT_SECRET` and `/mcp` becomes its own OAuth 2.1 authorization server.** claude.ai and ChatGPT (web) connectors authenticate over OAuth only, so this is what lets them connect to a secured platform: paste `https://<public-url>/mcp` as a custom connector (the form's optional client ID/secret fields stay empty — DCR registers the app), then approve the consent page with the connect secret. The built-in server (`AgentOSBuiltinAuth(url=agentos_url, secret=MCP_CONNECT_SECRET)` in [`app/main.py`](app/main.py), mirroring the Slack conditional) stores clients, single-use codes, and rotating refresh tokens hashed in Postgres; DCR is public-client + PKCE only; tokenless calls get the `401` + `WWW-Authenticate` challenge connectors use for discovery, and `/info`'s `mcp.oauth` block carries the OAuth discovery details (`auth_mode` keeps describing the REST plane). Existing PAT/JWT bearers keep working on the same endpoint (`MultiAuth`), so enabling OAuth never breaks `agno connect` clients. Gates `/mcp` in dev too — the OAuth flow needs a stable public origin (`AGENTOS_URL`) — and dev and prod share `.env` in this template, so setting the secret gates the local `/mcp` as well.
- **HITL pauses resume over MCP via `continue_run`.** A paused `run_agent` returns immediately with `status=PAUSED` and unresolved `requirements` dicts in `structuredContent`; the client sets the resolution field (e.g. `confirmation: true`) and passes them back through `continue_run(run_id, agent_id, session_id, requirements)`. So a confirmation gate is no longer a dead end from chat frontends — this is what lets Agent Builder keep the delete gate usable over MCP.

Local smoke check: `./scripts/mcp_check.sh` — handshake, tool count, and one quick tool-free `run_agent` call through `/mcp` (finishes in seconds; pass your own question as an argument), executed inside the container. When `/mcp` is auth-gated (OAuth on, or prd JWT), it retries with a short-lived probe service account that it mints and deletes itself. To register the endpoint, run `uvx agno connect` (auto-detects Claude Code / Claude Desktop / Codex / Cursor and verifies with a real handshake); the manual fallback for Claude Code is `claude mcp add --transport http agentos http://localhost:8000/mcp`.

## Slack

Set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` and restart. The default wiring in `app/main.py` routes Slack messages to `agent_builder` so users can request new components from chat. Change the `agent=` arg to point at another agent. See the [agno Slack interface docs](https://docs.agno.com/agent-os/interfaces/overview) for the Slack-side app setup.

For Discord, Telegram, WhatsApp, and custom UIs, mirror the Slack conditional pattern with the relevant agno interface — see [agno interfaces overview](https://docs.agno.com/agent-os/interfaces/overview).

## Portable core vs. deploy layer

This repo is the self-hosted Docker sibling of the `agentos-*` deployment family ([agentos-railway](https://github.com/agno-agi/agentos-railway) is the reference). Everything that defines the platform is **portable core — identical across the family**: `agents/`, `app/`, `db/`, `workflows/`, `evals/`, the MCP server wiring, the interfaces, and the coding-agent skills in `.agents/skills/`. `Dockerfile`, `compose.yaml`, and `scripts/entrypoint.sh` are shared local-dev/runtime infra, also not deployment-specific.

The **Docker-specific deploy layer** — what a sibling template swaps out — is exactly:

- [`compose.prod.yaml`](compose.prod.yaml)
- the "Running in production on your own host" prose here and the README's "Run in production" section

This is the family's smallest deploy layer — there is no provider CLI, no provisioning script, and nothing to tear down. Siblings that target a cloud swap in a provider config plus `scripts/<provider>/{up,env-sync,redeploy}.sh`.

When editing, keep that boundary crisp: platform behavior belongs in the core, production-hosting mechanics belong in the deploy layer, and nothing in the core should import from or depend on it.

## Running in production on your own host

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

The [`compose.prod.yaml`](compose.prod.yaml) override switches `RUNTIME_ENV` to `prd` (JWT auth on), drops the dev bind mount and hot reload so the container runs the code baked into the image, reads `AGENTOS_URL` (and `MCP_CONNECT_SECRET`, if set) from `.env`, and rebinds Postgres to loopback so the database is not internet-reachable (set a real `DB_PASS` in `.env` — the dev default is `ai`). Both services already carry `restart: unless-stopped`, so the platform survives reboots as long as Docker starts on boot. The override uses the `!reset`/`!override` merge tags, which need Docker Compose v2.24.4+.

JWT auth is on by default in prd and the app refuses to serve without a key. Mint one at os.agno.com (Connect OS → Live with your public URL, name it `Live AgentOS`, then Settings → OS & Security → Token-Based Authorization (JWT)) and paste the PEM into `.env` **quoted**, so Docker Compose reads the multi-line value as one variable:

```sh
JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----"
```

Live AgentOS Connections are a paid feature; use `PLATFORM30` to get 1 month off. `/health` and `/docs` stay public in prd (they are on the auth middleware's excluded-route list); everything else requires a token.

The public URL comes from whatever you put in front of the host — a domain + reverse proxy, or a tunnel (cloudflared, ngrok, `tailscale funnel`). Set it as `AGENTOS_URL` in `.env` so the scheduler can reach the platform, and use `https://<public-url>/mcp` as the connector URL in chat apps — with `MCP_CONNECT_SECRET` set in `.env`, `/mcp` serves its own OAuth so claude.ai and ChatGPT (web) can connect (see [MCP interface](#mcp-interface)). The full walkthrough lives in the README's [Run in production](README.md#run-in-production) section.

## Common Tasks

```bash
# Add a dependency
# 1. Edit pyproject.toml
./scripts/generate_requirements.sh   # keeps existing pins; add `upgrade` to refresh every pin
docker compose up -d --build

# Bump agno (alpha, rc, and final releases are the same flow)
# 1. Edit the agno pin in pyproject.toml
./scripts/generate_requirements.sh agnoctl   # agno follows the pin; agnoctl must be named — agno only floors it at the previous release
docker compose up -d --build
./scripts/validate.sh && python -m evals --tag smoke

# Build a multi-arch image (maintainer-only)
./scripts/build_image.sh

# Tail production logs (same host, prod override)
docker compose -f compose.yaml -f compose.prod.yaml logs -f agentos-api
```

## Documentation Links

- [Agno docs](https://docs.agno.com) — full framework reference.
- [Agno LLM-friendly docs](https://docs.agno.com/llms.txt) — concise overview, good for fetching.
- [AgentOS introduction](https://docs.agno.com/agent-os/introduction).
- [Agno tools / toolkits](https://docs.agno.com/tools/toolkits) — 100+ integrations.
- [Agno model providers](https://docs.agno.com/models) — OpenAI, Anthropic, Google, Ollama, Bedrock, Azure, etc.
- [Agno teams](https://docs.agno.com/teams/overview) — multi-agent routing/coordination.
- [Agno workflows](https://docs.agno.com/workflows/overview) — deterministic step-by-step pipelines.
- [Agno interfaces](https://docs.agno.com/agent-os/interfaces/overview) — Slack, Discord, Telegram, WhatsApp, custom UIs.
