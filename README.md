# AgentOS: FastAPI for Agents

AgentOS turns your agents into a production API: 80+ endpoints for runs, sessions, memory, knowledge, and evals. Build your product on top of it, connect your agents to AI apps like Claude and ChatGPT, and chat interfaces like Slack, WhatsApp, Telegram, and Discord.

## Get Started

Copy this prompt into Claude Code, Cursor, or Codex. It sets up the platform and builds your first agent with you:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-docker.git into a folder called agent-platform, cd in, and run the setup-platform skill.
```

Your coding agent drives the whole flow: it checks Docker, sets up `.env`, boots the platform, proves the MCP endpoint live, builds your first agent with you, and connects the AgentOS UI. Prefer to drive yourself? See [Manual Setup](#manual-setup).

## One AI backend for every frontend

1. **Your product.** Call the REST API from your app: run agents, stream responses, and manage sessions, memory, and knowledge.
2. **AgentOS UI.** Chat with agents, build new ones with AgentOS Studio, and inspect sessions, traces, memory, and evals from the AgentOS UI at [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-docker&utm_content=agentos-docker&utm_term=docker).
3. **Coding agents.** Manage the full agent development lifecycle (create, extend, improve, eval and review) using the skills in [`.agents/skills/`](.agents/skills/).
4. **AI apps.** MCP clients like Claude and ChatGPT can use your agents through the MCP server at `/mcp`.
5. **Chat interfaces.** Chat with your agents from Slack, WhatsApp, Telegram, and Discord.

<img width="3298" height="2412" alt="AgentOS" src="https://github.com/user-attachments/assets/40a53a42-d4d2-402b-8e92-742609207957" />

Built on [Agno](https://docs.agno.com). Everything runs on infrastructure you control, your data lives in your database.

## Built for agents

This codebase comes with:

- **Two platform agents** that help you build and run the platform from your favorite AI apps like Claude and ChatGPT. **Agent Builder** creates agents, teams, and workflows using the AgentOS Studio. **Platform Manager** understands, monitors, and explains the platform: codebase questions, eval history, deployment checks, schedules.
- **Coding-agent skills** let Claude Code, Codex, Cursor, and other coding agents build, test, and improve the platform automatically — see [Using the platform](#using-the-platform).

Trace data, agent code, evals, and system logs are all available to coding agents, so the platform can inspect and improve itself end to end.

## Manual Setup

### Step 1: Run locally

> **Prerequisite:** [Docker](https://www.docker.com/get-started/) installed and running.

```sh
git clone https://github.com/agno-agi/agentos-docker.git agentos
cd agentos

# Configure credentials
cp example.env .env
# Open .env and set OPENAI_API_KEY

# Run the platform on docker
docker compose up -d --build
```

Confirm your AgentOS is running at [http://localhost:8000/docs](http://localhost:8000/docs).

### Step 2: Connect the AgentOS UI

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-docker&utm_content=agentos-docker&utm_term=docker) and sign in.
2. Click **Connect OS**, enter `http://localhost:8000` as the URL, name it **Local AgentOS**, and connect.

### Step 3: Build your first agent

1. Click **Chat** under the **Agent Builder** agent and try the first prompt: "Build an agent that tracks AI news and writes a daily brief". Go through the agent development process.
2. Once created, click the **Refresh** button on the top right. You should now see the "Daily AI News Brief" agent in the **Agents** dropdown. Click the newly created agent.
3. Ask: "What's new with Anthropic?"

### Step 4: Check platform health

Click **Chat** under **Platform Manager** and ask: "How healthy is the platform?" It answers from the codebase and runtime data — eval history, deployment checks, schedules, and the component you just built.

## Run in production

This template carries no cloud-provider layer at all: production is the same Docker Compose you already ran locally, plus the [`compose.prod.yaml`](compose.prod.yaml) override — on any host you control. A VPS, a home server, an office box, this laptop. If you'd rather have a managed platform provision the database and the URL for you, use one of the cloud variants of this template ([agentos-railway](https://github.com/agno-agi/agentos-railway) is the reference).

> **Prerequisite:** a host with Docker (Compose v2.24.4 or newer — the prod override uses the `!reset`/`!override` merge tags), and a way for the internet to reach port 8000 on it — a domain with a reverse proxy, or a tunnel.

### 1. Get a public URL

The platform needs a public HTTPS URL for two things: hosted chat apps (Claude, ChatGPT) reaching `/mcp`, and `AGENTOS_URL` — the address the platform advertises as its own. Any of these work:

```sh
# Cloudflare Tunnel — free; quick tunnels get a random URL, named tunnels a stable one
cloudflared tunnel --url http://localhost:8000

# ngrok — reserved domains on paid plans
ngrok http 8000

# Tailscale Funnel — stable https URL on your tailnet's domain
tailscale funnel 8000
```

For a first run, an ephemeral cloudflared/ngrok URL is fine. For a real deployment, use something stable: a named Cloudflare tunnel, a reserved ngrok domain, or your own domain in front of a reverse proxy (Caddy, nginx) that forwards to port 8000.

### 2. Set up your production env

Production values live in `.env` on the host — the same file compose already reads:

```sh
OPENAI_API_KEY=sk-...
AGENTOS_URL=https://<your-public-url>
MCP_CONNECT_SECRET=<generate with: openssl rand -base64 32>
DB_PASS=<generate a strong one>
```

`AGENTOS_URL` is the address the platform advertises as its own. Left unset, the daily deployment check flags the platform as misconfigured, and anything that needs the public URL — chat-app connectors, hosted MCP clients — has nothing to point at. `MCP_CONNECT_SECRET` turns `/mcp` into its own OAuth 2.1 authorization server so claude.ai and ChatGPT (web) can connect; connecting asks for this secret once, on a consent page. It needs `AGENTOS_URL` for a stable public origin, and — because dev reads the same `.env` — it gates the local `/mcp` too. `DB_PASS` replaces the dev default (`ai`) — the override keeps Postgres bound to loopback, but a real password is still the floor for a production database.

One catch on a host that already ran the dev compose: Postgres reads the password only when the `pgdata` volume is first initialized, so changing `DB_PASS` in `.env` won't take on its own — the database keeps the old password and the API blocks waiting for it. Either change it in place to match — `docker compose exec agentos-db psql -U ai -c "ALTER USER ai WITH PASSWORD '<new>';"` — or reinitialize with `docker compose down -v` (wipes all platform data).

### 3. Production Auth

Token-Based Authorization is on by default. Without a `JWT_VERIFICATION_KEY` or `JWT_JWKS_FILE`, the app refuses to serve traffic in production. The platform's job is to keep your data private, so the safe default is "refuse to start" without an authentication token.

Token-Based Auth gives you three things:

1. **No public access.** The server rejects requests without a valid token.
2. **Per-request identity.** Middleware parses the token and extracts the `user_id`, `session_id`, and custom claims. Each request is tied to a user and session, giving you auditability and traceability.
3. **Granular permissions.** User tokens can run an agent and view their own sessions. Admin tokens read everyone's sessions and test any agent.

Mint the key at os.agno.com against your public URL:

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-docker&utm_content=agentos-docker&utm_term=docker), click **Connect OS** → **Live**, enter your public URL, and connect.
2. Name it **Live AgentOS**.
3. Go to **Settings** → **OS & Security**.
4. Turn **Token-Based Authorization (JWT)** on.
5. Copy the public key.
6. Paste it into `.env` **with quotes**, so Docker Compose reads the multi-line PEM as one value:

```sh
JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----"
```

> **Heads up.** Live AgentOS Connections are a paid feature. Use `PLATFORM30` to get 1 month off. We are working on a free trial so you don't have to pay to try.

### 4. Start in production mode

```sh
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

The override switches `RUNTIME_ENV` to `prd` (JWT auth on), drops the dev bind mount and hot reload so the container runs the code baked into the image, passes your `AGENTOS_URL` (and `MCP_CONNECT_SECRET`, if set) through, and rebinds Postgres to loopback so only this host — not the internet — can reach it. Both services carry `restart: unless-stopped`, so the platform survives reboots as long as Docker starts on boot.

Verify it's up and gated:

```sh
curl https://<your-public-url>/health   # 200 — /health and /docs stay public
curl https://<your-public-url>/agents   # 401 — everything else wants a token
```

Logs, when something looks off:

```sh
docker compose -f compose.yaml -f compose.prod.yaml logs -f agentos-api
```

### 5. Register your production AgentOS to MCP clients

Re-run `uvx agno connect`, this time pointed at your deployed domain, to connect Claude Code, Claude Desktop, Codex, and Cursor to your production platform:

```sh
uvx agno connect --url https://<your-public-url>
```

For **claude.ai and ChatGPT (web)**: add `https://<your-public-url>/mcp` as a custom connector in the chat app's connector settings. Leave the form's optional OAuth fields (client ID / client secret) empty. Click **Connect** and, on the consent page, enter the `MCP_CONNECT_SECRET` you set in `.env` in step 2.

### 6. Redeploy after code changes

```sh
git pull   # or edit in place
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

Env changes are the same command without `--build` — compose recreates the container with the new `.env` values.

### Opting out of JWT (not recommended)

Set `authorization=False` in [`app/main.py`](app/main.py) and restart. Use this only inside a private network behind another auth layer. Without it, anyone who finds your public URL can access your platform.

## Using the platform

This platform is designed so that coding agents can drive the entire **create → improve → evaluate → maintain** lifecycle for you.

### Create

Open your coding agent of choice (Claude Code, Codex, Cursor) and run:

```
/create-new-agent
```

It asks a few questions, generates the agent file in `agents/`, registers it in `app/main.py`, adds its description and quick prompts to `app/config.yaml`, restarts the container, and smoke-tests it live.

### Improve

Improve your agents by running the following skills:

- **`/extend-agent`** — Add a tool, add a capability, refine the instructions, fix a known bug.
- **`/improve-agent`** — Claude simulates scenarios from the agent's `INSTRUCTIONS`, runs them against the live container, judges the responses, and edits until they pass.

### Evaluate

Run the eval suite to check for regressions. The evals live in [`evals/cases.py`](evals/cases.py), and run history shows up at os.agno.com next to your sessions and traces.

The evals run on the host machine, so set up the venv with `./scripts/venv_setup.sh && source .venv/bin/activate`, then:

```sh
python -m evals --tag smoke      # fast checks of the self-driving surfaces
python -m evals --tag release    # broader pre-release confidence
python -m evals --name <case>    # one case while iterating
python -m evals -v               # stream the full run with rich panels
```

If a case fails, run **`/eval-and-improve`** — it diagnoses each failure, fixes what's in scope, and loops until green.

### Maintain

Because the repo is managed by coding agents, it moves fast. Run `/review-and-improve` before a release or after a refactor: it sweeps for drift between docs, code, and config, auto-fixes mechanical drift like stale paths and missing env vars, and flags anything bigger.

## Connect more frontends (optional)

AgentOS comes with an MCP server at `/mcp` (enabled by setting `mcp_server=True` in [`app/main.py`](app/main.py)), so any MCP client can call your agents, teams, and workflows through tools like `run_agent`, `run_team`, and `run_workflow`.

Register your AgentOS with the MCP clients on your machine:

```sh
uvx agno connect
```

It auto-detects Claude Code, Claude Desktop, Codex, and Cursor and registers `http://localhost:8000/mcp`. After a successful connection, open one of these apps and ask:

```text
can you access my agentos mcp?
```

**claude.ai and ChatGPT (web).** Hosted AI apps reach your platform over the internet and need an OAuth login. Set up production (above), add `https://<your-public-url>/mcp` as a remote connector, and approve the consent page with your connect secret.

> **Heads up.** Dev and prod share the same `.env` in this template, so once `MCP_CONNECT_SECRET` is set, the local `/mcp` is OAuth-gated too. Token bearers keep working: `uvx agno connect` mints a PAT, and `./scripts/mcp_check.sh` falls back to a short-lived probe service account it mints and deletes itself.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | yes | none | OpenAI key for models and embeddings. |
| `RUNTIME_ENV` | no | `prd` | `dev` disables JWT. `compose.yaml` sets it to `dev` for local; `compose.prod.yaml` sets `prd` — never hand-set `dev` on a production host, or the platform serves unauthenticated. |
| `JWT_VERIFICATION_KEY` | prd | none | Public key from os.agno.com. Required when `RUNTIME_ENV=prd`, unless `JWT_JWKS_FILE` is set. |
| `JWT_JWKS_FILE` | prd | none | Path to a JWKS file; alternative to `JWT_VERIFICATION_KEY` for production JWT verification. |
| `AGENTOS_URL` | no | `http://127.0.0.1:8000` | Scheduler base URL. In production, set it in `.env` to your public URL (domain or tunnel); `compose.prod.yaml` passes it through. Also the public origin OAuth metadata derives from when `MCP_CONNECT_SECRET` is set. |
| `MCP_CONNECT_SECRET` | no | none | If set (≥16 chars, e.g. `openssl rand -base64 32`), `/mcp` becomes its own OAuth 2.1 authorization server so claude.ai and ChatGPT (web) can connect; connecting asks for this secret on a consent page. Requires `AGENTOS_URL`. Set it in `.env` — dev reads the same file, so it gates the local `/mcp` too. PAT and JWT bearers keep working alongside. |
| `AGENTOS_MCP_SIGNING_KEY` | no | none | Optional high-entropy signing-key material (≥32 chars) for OAuth tokens. Unset, a strong key is generated and persisted in the database. Rotating it invalidates outstanding tokens. |
| `ENABLE_DEPLOY_CHECK` | no | `True` | The reference deployment-check cron runs daily by default. Set `False` to disable; the workflow is runnable on demand regardless. |
| `ENABLE_SCHEDULED_EVALS` | no | `False` | If `True`, schedules the run-evals workflow daily. Off by default because it uses model calls. |
| `EVALS_TAG` | no | `smoke` | Eval tag run by the run-evals workflow. |
| `EVALS_CASE_TIMEOUT_SECONDS` | no | `90` | Default per-case timeout for run-evals runs; applies only to cases that don't set their own `timeout_seconds`. |
| `EVALS_SUITE_TIMEOUT_SECONDS` | no | `900` | Whole-suite timeout for run-evals runs; per-case timeouts are the granular limit. The default bounds the `smoke` tag's worst case (incl. builder-case teardown). |
| `PARALLEL_API_KEY` | no | none | Authenticates the WebSearch Agent's Parallel SDK / MCP connection. |
| `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` | no | none | Both must be set to enable the Slack interface. |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | no | matches compose | Postgres connection. |
| `DB_DRIVER` | no | `postgresql+psycopg` | SQLAlchemy driver. |
| `AGNO_DEBUG` | no | `False` | If `True`, Agno emits verbose debug logs. Compose sets this for dev. |
| `WAIT_FOR_DB` | no | `False` | If `True`, the entrypoint blocks on the DB before starting. Compose sets this. |

## Learn more

- [Agno documentation](https://docs.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-docker&utm_content=agentos-docker&utm_term=docker)
- [AgentOS introduction](https://docs.agno.com/agent-os/introduction?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-docker&utm_content=agentos-docker&utm_term=docker)
- [Agno on GitHub](https://github.com/agno-agi/agno). Drop a star if this is useful.
