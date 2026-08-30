## AgentOS: Serve agents over API, MCP, and interfaces like Slack

AgentOS is a durable agent runtime that serves agents over API, MCP, and chat interfaces like Slack. Build customer-facing agents and serve them to your users from your product, through AI apps like Claude and ChatGPT, or interfaces like Slack. AgentOS gives you one agent backend for every frontend.

**Three ways to build agents.**

1. **Coding agent.** Point a coding agent at the skills in [`.agents/skills/`](.agents/skills/) and it can create, improve and evaluate your agents for you.
2. **Natural language.** Ask the built-in Platform Builder to build agents for you.
3. **No-code Studio.** Build agents visually using the [AgentOS Studio](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-docker).

**Three ways to serve your agents to your users.**

1. **Your product.** Call the AgentOS REST API from your product.
2. **AI apps.** Connect your agents to Claude and ChatGPT using the AgentOS MCP server.
3. **Chat interfaces.** Distribute your agents through Slack, WhatsApp (and more) using AgentOS Interfaces.

**Monitor and govern your agents.**

The [AgentOS Control Plane](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-docker) gives you a unified view of your agent platform. Trace every action. Enforce agent- and tool-level permissions.

<img width="3298" height="2412" alt="AgentOS" src="https://github.com/user-attachments/assets/40a53a42-d4d2-402b-8e92-742609207957" />

<p align="center"><em>Everything runs on infrastructure you control, your data lives in your database.</em></p>

## Get Started

Copy this prompt into your favorite coding agent. It sets up the platform and builds your first agent for you:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-docker into a folder called agent-platform, cd in, and run the setup-platform skill (in .agents/skills/).
```

Your coding agent checks Docker, sets up `.env`, boots the platform, verifies the MCP endpoint, connects to the AgentOS UI, then builds your first agent. Prefer to drive yourself? See [Manual Setup](#manual-setup).

## Manual Setup

### Step 1: Run locally

> **Prerequisite:** [Docker](https://www.docker.com/get-started/) installed and running.

```sh
git clone https://github.com/agno-agi/agentos-docker agentos
cd agentos

# Configure credentials
cp example.env .env
# Open .env and set OPENAI_API_KEY

# Run the platform on docker
docker compose up -d --build
```

Confirm your AgentOS is running at [http://localhost:8000/docs](http://localhost:8000/docs).

### Step 2: Connect the AgentOS UI

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-docker) and sign in.
2. Click **Connect OS**, enter `http://localhost:8000` as the URL, name it **Local AgentOS**, and connect.

### Step 3: Build your first agent using natural language

1. Click **Chat** under the **Agno** team and tell it what you're working on: "Help me build an agent for my product".
2. Give it the docs URL for your product, or for a product you like — `docs.agno.com`, say.
3. Click the **Refresh** button on the top right. You should now see your new agent in the **Agents** dropdown. Chat with it directly, or just ask Agno to run it for you.

## Make the platform yours

Your cloned repo points at this public template. Create your own GitHub repo and point your platform at it:

```sh
git remote rename origin upstream    # keep the template connected for updates
git remote add origin <your-private-repo-url>
git push -u origin main
```

> **Heads up.** Create the private repo first ([github.com/new](https://github.com/new), or `gh repo create <name> --private`). Keep `upstream` connected, so that `git pull upstream main` brings in template updates in the future.

## Run in production

This template carries no cloud-provider layer at all: production is the same Docker Compose you already ran locally, plus the [`compose.prod.yaml`](compose.prod.yaml) override — on any host you control. A VPS, a home server, an office box, this laptop. A coding-agent skill, [`/deploy-platform`](.agents/skills/deploy-platform/SKILL.md), guides you through it. If you'd rather have a managed platform provision the database and the URL for you, use one of the cloud variants of this template ([agentos-railway](https://github.com/agno-agi/agentos-railway) is the reference).

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
3. **Granular permissions.** Scopes on the token decide what each caller can do — run agents, read sessions, manage the platform. Admin tokens can do everything; scoped tokens get exactly what their claims grant.

Mint the key at os.agno.com against your public URL:

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-docker), click **Connect OS** → **Live**, and enter your public URL.
2. Name it **Live AgentOS**, flip **Token-Based Authorization (JWT)** on and connect. The UI generates your public key. (Ran into an issue? Go to **Settings** → **OS & Security** → **Token-Based Authorization (JWT)** to get the key from the settings page.)
3. Copy the public key.
4. Paste it into `.env` **with quotes**, so Docker Compose reads the multi-line PEM as one value:

```sh
JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----"
```

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

### 5. Connect your AgentOS to MCP clients

AgentOS comes with an MCP server at `/mcp` (wired via `mcp=MCPConfig(...)` in [`app/main.py`](app/main.py)), where Agno itself is published as a first-class `agno` tool — clients just call it, no id discovery. There are two ways to connect your AgentOS to MCP clients:

1. **AI Apps like Claude and ChatGPT** connect to your AgentOS over the internet using OAuth. Add `https://<your-public-url>/mcp` as a custom connector in the chat app's connector settings. Leave the form's optional OAuth fields (client ID / client secret) empty. Click **Connect** and, on the consent page, enter the `MCP_CONNECT_SECRET` you set in `.env` in step 2.
2. **Coding agents like Claude Code, Claude Desktop, Codex, and Cursor** connect to your AgentOS via the MCP URL. Register your AgentOS with the MCP clients on your machine:

```sh
uvx agno connect --url https://<your-public-url>
```

After a successful connection, open one of these apps and ask:

```text
can you access my agentos mcp?
```

### 6. Redeploy after code changes

```sh
git pull   # or edit in place
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

Env changes are the same command without `--build` — compose recreates the container with the new `.env` values.

### Opting out of JWT (not recommended)

Change `authorization=runtime_env != "dev"` to `authorization=False` in [`app/main.py`](app/main.py) and restart. Use this only inside a private network behind another auth layer. Without it, anyone who finds your public URL can access your platform.

## Using the platform

This platform is designed so that coding agents can drive the entire **create → improve → evaluate → maintain** lifecycle for you.

### Create

Open your coding agent of choice (Claude Code, Codex, Cursor) and run:

```
/create-agent
```

It asks a few questions, generates the agent file in `agents/`, registers it in `app/main.py`, adds its description and quick prompts to `app/config.yaml`, restarts the container, and smoke-tests it for you.

### Improve

Improve your agents by running the following skills:

- **`/extend-agent`** — Add a tool, add a capability, refine the instructions, fix a known bug.
- **`/improve-agent`** — Claude simulates scenarios from the agent's `INSTRUCTIONS` and its real usage recorded in the database, runs them against the live container, judges the responses, and edits until they pass.

### Evaluate

Run the eval suite to check for regressions. The evals live in [`evals/cases.py`](evals/cases.py), and run history shows up in the AgentOS UI next to your sessions and traces.

The evals run on the host machine, so set up the venv with `./scripts/venv_setup.sh && source .venv/bin/activate`, then run:

```sh
python -m evals --tag smoke      # fast checks of the self-driving surfaces
python -m evals --tag release    # broader pre-release confidence
python -m evals --name <case>    # one case while iterating
python -m evals -v               # stream the full run with rich panels
```

If a case fails, run **`/eval-and-improve`** — it diagnoses each failure, fixes what's in scope, and loops until green.

### Maintain

Because the repo is managed by coding agents, it moves fast. Run `/review-and-improve` before a release or after a refactor: it sweeps for drift between docs, code, and config, auto-fixes mechanical drift like stale paths and missing env vars, and flags anything bigger.

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
| `ENABLE_DEPLOY_CHECK` | no | `True` | The reference deployment-check cron runs daily by default. This env var owns the schedule's toggle (re-asserted on every boot); the workflow is runnable on demand regardless. |
| `EVALS_TAG` | no | `smoke` | Eval tag run by the run-evals workflow. |
| `EVALS_CASE_TIMEOUT_SECONDS` | no | `90` | Default per-case timeout for run-evals runs; applies only to cases that don't set their own `timeout_seconds`. |
| `EVALS_SUITE_TIMEOUT_SECONDS` | no | derived | Whole-suite timeout for run-evals runs; per-case timeouts are the granular limit. Unset, it is derived from the cases the tag selects. Set it to override. |
| `PARALLEL_API_KEY` | no | none | Authenticates Agno's and the Studio registry's web search tools (Parallel SDK when set; keyless MCP fallback). Also the fast route for ingesting a product's docs — clean markdown per page, JS-rendered pages and PDFs included; without it ingestion still works, page by page, just slower. |
| `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` | no | none | Both must be set to enable the Slack interface. The bot token also lights up the registry's send-only Slack toolkit for built agents. |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | no | matches compose | Postgres connection. |
| `DB_DRIVER` | no | `postgresql+psycopg` | SQLAlchemy driver. |
| `AGNO_DEBUG` | no | `False` | If `True`, Agno emits verbose debug logs. Compose sets this for dev. |
| `WAIT_FOR_DB` | no | `False` | If `True`, the entrypoint blocks on the DB before starting. Compose sets this. |

## Learn more

- [Agno documentation](https://docs.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-docker)
- [AgentOS introduction](https://docs.agno.com/agent-os/introduction?utm_source=github&utm_medium=template&utm_campaign=agentos-docker)
- [Agno on GitHub](https://github.com/agno-agi/agno). Drop a star if this is useful.
