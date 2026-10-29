# AgentOS: The self-driving agent platform

Build agents for your company, product, or customers. Run them as durable
services on AgentOS. Put them to work automating company operations.

- **Build** agents with the Agno, Claude Agent, or Codex SDKs. Combine agents into
  teams and workflows.
- **Run** agents as durable services with built-in API and MCP. AgentOS handles
  authentication, role-based access, human approvals, scheduling, and durable execution.
- **Automate** company operations with CompanyOS. Give agents responsibilities,
  organize work into projects and tasks, and configure recurring routines. People set
  direction and review results; agents own and execute.

Built with [Agno](https://github.com/agno-agi/agno), this template gives you a working
agent platform that you can run locally or deploy to self-hosted Docker.

Use your agents in:

1. **Your product:** call them through the REST API.
2. **Claude and ChatGPT:** connect through the MCP server.
3. **Slack:** connect a Slack app to talk to OS Manager from your workspace.

Run your platform in your own cloud and keep your data in your own PostgreSQL database.
Use the [AgentOS UI](https://os.agno.com) to review conversations, inspect traces,
manage knowledge, and track your agents' work. Build agents with code, use Studio,
or chat with OS Manager.

## Get started

Give this prompt to your coding agent:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-docker into a folder called agent-platform,
cd into it, and follow .agents/skills/setup-platform/SKILL.md.
```

It checks Docker, helps you add your API key, starts the platform, and walks you
through building your first agent. Already cloned the repo? Ask your coding agent
to run the `/setup-platform` skill.

## Coding agents

The platform includes **Claude Engineer** and **Codex Engineer**, disabled by default.
They can read code, make changes, and run commands. Enable them in `app/main.py`.
Follow the [harness setup guide](docs/harnesses.md) for the steps.

Once enabled, chat with a coding agent in AgentOS or ask OS Manager to use one:

> Ask Codex Engineer to review this project and suggest improvements. Don't change any files yet.

Without a sandbox, coding agents run on the API host with its file and credential
access. For isolation and checkpoint recovery, set up a
[Docker or AgentCore sandbox](docs/harnesses.md#sandboxes-and-checkpoints).

## Run locally

You'll need Git, Docker with Compose, and an OpenAI API key.
Make sure Docker is running, then run the commands below in your terminal.

### 1. Start the platform

```sh
git clone https://github.com/agno-agi/agentos-docker agent-platform
cd agent-platform
cp example.env .env
```

Open `.env` and set `OPENAI_API_KEY`, then start the platform:

```sh
docker compose up -d --build
```

The first build can take a few minutes. When it's ready, open
[http://localhost:8000/docs](http://localhost:8000/docs) to see the API.

Check that AI apps can connect through MCP:

```sh
./scripts/mcp_check.sh
```

The check should report `9 tools; required tools available`.

### 2. Connect the UI

1. Open [os.agno.com](https://os.agno.com) and sign in.
2. Choose **Connect OS**, select a local connection, and enter `http://localhost:8000`.
3. Name it **Local AgentOS**, then open the chat for **OS Manager**.

### 3. Build your first agent

Tell OS Manager what you want to build. For example:

> Help me build a daily briefing agent about the companies and topics I follow. Here's what I care about: …

Review what it proposes, then ask it to build and publish the agent.
Refresh the Agents list and try it out. You can chat with your new agent directly
or ask OS Manager to run it for you.

## Build and improve your agents

You can keep working through OS Manager, use Studio, or edit Python files in this repo.
The repo includes instructions, called skills, for common coding tasks.
Ask your coding agent to follow the relevant skill:

| What you want to do | Skill |
| --- | --- |
| Build an agent | [/create-agent](.agents/skills/create-agent/SKILL.md) |
| Add a tool, change behavior, or fix a bug | [/extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Write tests for your agent's answers | [/create-evals](.agents/skills/create-evals/SKILL.md) |
| Harden an agent with simulations and targeted fixes | [/improve](.agents/skills/improve/SKILL.md) |
| Check the repo before sharing or releasing it | [/review-and-improve](.agents/skills/review-and-improve/SKILL.md) |

If you write an agent in Python, put it in `agents/` and add it to
[app/main.py](app/main.py) so the platform can run it. Set its description and
suggested prompts in [app/config.yaml](app/config.yaml). To make a tool or model
available in Studio, add it to [app/registry.py](app/registry.py).

You can give agents documents to search, a notebook to keep notes, and memory
to remember each user.

## Company

CompanyOS organizes the work you delegate to agents. A Product defines an ongoing
area of responsibility, a Project groups related work toward a goal, and a Task
describes a specific job to complete. Routines give agents instructions to carry
out on a schedule.

This template includes an `AgentOS` Product for improving the platform itself,
with a daily review Routine configured for 09:00 UTC and **disabled by default**.
Open Company in AgentOS, review its instructions and schedule, then enable it when
you want recurring reviews. Company Manager reads the code and Agno release notes,
then proposes up to three Tasks. Automatic acceptance is off; you choose what to
approve and implement.

Scheduled reviews use your model API keys and incur usage costs. Check the saved
schedule and run history in Company. Upgrading an existing platform preserves its
saved Routine state; pause it in the UI if you want to stop scheduled reviews.

[app/company.py](app/company.py) sets the initial review instructions and schedule.
Once they're saved in the database, update the saved Routine to change them;
editing the Python file alone won't change an existing Routine.

## Make it yours

To save your work in your own GitHub repository, create an empty private repo.
From a fresh clone of this template, run the commands below with your repo URL.
This makes `origin` your repo and keeps the original template as `upstream`:

```sh
git remote rename origin upstream
git remote add origin https://github.com/YOUR-ORG/YOUR-REPO.git
git push -u origin HEAD
```

Future pushes go to your repository. You can still fetch updates from `upstream`
and review them before merging.

If you use sandboxes, also set the repository URL and branch in
[the sandbox configuration](docs/harnesses.md#sandboxes-and-checkpoints).

<a id="deploy-in-production"></a>

## Deploy in production

Ask your coding agent to follow [deploy-platform](.agents/skills/deploy-platform/SKILL.md),
or use the steps below.

You'll need Docker Compose 2.24.4 or newer and a stable public HTTPS URL routed
to port 8000 on your host. Use a reverse proxy on the host or an HTTPS tunnel.

### 1. Configure the host

Production Compose reads `.env`. Set `OPENAI_API_KEY`, `AGENTOS_URL` to your
public HTTPS URL, a strong `DB_PASS`, and `MCP_CONNECT_SECRET` (generate one with
`openssl rand -base64 32`). For Claude Engineer, set `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN`. Compose passes the file through unchanged, so delete
any `sk-***` placeholder line you are not filling in: a placeholder reaches the
container as a real value and the matching engineer fails on authentication.

For an existing database, changing `DB_PASS` in `.env` does not change the database
password. Update the database password separately; do not delete the data volume.

### 2. Set up authentication

Open [os.agno.com](https://os.agno.com), choose **Connect OS → Live**, enter your
public URL, and enable token-based authorization. Save the public verification
key in `.env` as `JWT_VERIFICATION_KEY`, with the entire multiline value in quotes.

### 3. Start the production services

```sh
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

The production override turns on token checks and runs the code built into the
image. Keep one API container. The API and database ports bind to loopback; your
reverse proxy or tunnel must reach the API from the host.

Check `/health` and `/docs` on your public URL. Confirm `/agents` rejects requests
without a token, then connect through the AgentOS UI with a valid token.

### Connect your AI apps

Use your public URL followed by `/mcp` as the connector URL in an AI app.
When prompted, enter the `MCP_CONNECT_SECRET` saved in your production env file.
For a supported coding client, run:

```sh
uvx agno connect --url https://YOUR-DOMAIN
```

Try asking OS Manager about the platform to check that the connection works.

### Update or stop the deployment

Run the same `up -d --build` command after changing code or settings. View logs or
stop the services with:

```sh
docker compose -f compose.yaml -f compose.prod.yaml logs -f agentos-api
docker compose -f compose.yaml -f compose.prod.yaml down
```

`down` keeps the database volume. Adding `-v` deletes it and all stored data.

### Sandbox storage

The API service needs no attached disk. Conversations, memories and Company work
are stored in PostgreSQL. Without a sandbox, engineers run inside the API container;
their edited files and native sessions can be lost on redeploy or replacement.
Database conversation history does not reconstruct that working directory.

For durable, isolated engineering, configure [AWS AgentCore and S3](docs/harnesses.md#aws-agentcore-sandbox).
S3 stores the last saved workspace and native-session checkpoint. Recovery does
not preserve unfinished edits at the instant of a crash or replay external actions
safely. AWS is optional for getting started. Local Docker isolation is also
available in the [sandbox guide](docs/harnesses.md#local-docker-sandbox).

Before running multiple API instances, follow [Scaling](docs/scaling.md).

### Coding agent backend

Production Compose selects `agentcore` and removes all development mounts, including
the Docker socket. Put the host settings from `scripts/aws.py status` in `.env`, then
recreate with `docker compose -f compose.yaml -f compose.prod.yaml up -d --build`.
Do not select Docker there without deliberately configuring trusted daemon access.

Enable coding agents and `SANDBOX_ENABLED` in code only after completing the
[harness setup](docs/harnesses.md); retain production JWT settings.

## Verify and develop

To check your Python code and test agent responses, install [uv](https://docs.astral.sh/uv/)
and run these commands from the project folder. Keep the local platform running.
If another Python environment is active, run `deactivate` first.

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
./scripts/validate.sh
python -m evals --tag smoke
```

`validate.sh` checks Python formatting, lint rules, and types. The smoke tests ask
OS Manager to explain setup, check platform health, and explain agent memory.
They use your model API keys and save results in the database for review in the UI.
PostgreSQL must be running, even when you only want to list the tests.

Add your own cases in [evals/cases.py](evals/cases.py), or use
[/create-evals](.agents/skills/create-evals/SKILL.md). To save a report, add
`--json-output tmp/evals.json`. To run one case, use `--name CASE_NAME`.
Evals use your application's database and workspace; agents can call tools during a test.

Change dependencies in `pyproject.toml`, then run `./scripts/generate_requirements.sh`.
Commit the updated `requirements.txt` and rebuild the API and any sandbox image you use.
See [AGENTS.md](AGENTS.md) for the code layout and development conventions.

## Configuration

[example.env](example.env) shows the main settings. Start with `OPENAI_API_KEY`;
add the others when you need them. Docker Compose reads `.env` for both local and production runs.

| Setting | What it's for |
| --- | --- |
| `OPENAI_API_KEY` | OS Manager, embeddings, and Codex Engineer. |
| `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` | Claude Engineer. |
| `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` | Connect OS Manager to Slack. Set both. |
| `PARALLEL_API_KEY` | Optional web search key. Without it, search uses Parallel's MCP server without an API key. |
| `JWT_VERIFICATION_KEY` or `JWT_JWKS_FILE` | Check login tokens in production. A JWKS file must be available on the server. |
| `AGENTOS_URL` | Public URL used by scheduled jobs and MCP. Set it to your public HTTPS URL. |
| `MCP_CONNECT_SECRET` | Connect browser MCP clients. Generate it before deployment. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_DATABASE` | PostgreSQL connection settings. Local Compose configures these for you. |
| `RUNTIME_ENV` | `prd` by default. Local Compose uses `dev`, which disables token checks. |

## Learn more

- [Agno documentation](https://docs.agno.com)
- [Agno on GitHub](https://github.com/agno-agi/agno)
- [AgentOS UI](https://os.agno.com)
