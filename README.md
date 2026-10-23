# AgentOS: The Agent Platform That Builds Itself

AgentOS is a durable agent runtime that serves agents over API, MCP, and chat interfaces like Slack.
Build agents for your product, your team, or yourself. Run them in your own cloud,
keep their data in your own database, and manage them from [AgentOS](https://os.agno.com).

Built with [Agno](https://github.com/agno-agi/agno), this template gives you a working
agent platform that you can run locally or deploy to your own Docker host.

**Three ways to build agents.**

1. **Use a coding agent.** Open the repo in Claude Code, Codex, or Cursor. The included
   skills help it create, test, and improve your agents.
2. **Describe what you need.** Chat with OS Manager, the built-in agent that helps you
   manage the platform and build new agents.
3. **Use Studio.** Build agents visually in [AgentOS Studio](https://os.agno.com).

**Three ways to use your agents.**

1. **In your product.** Call your agents through the REST API.
2. **In AI apps.** Connect apps such as Claude and ChatGPT through MCP.
3. **In Slack.** Connect a Slack app to talk to OS Manager from your workspace.

The AgentOS UI lets you chat with your agents, review past conversations, and see
the steps an agent took. Your PostgreSQL database stores conversations, memories,
and Company work.

## Get started

Copy this prompt into your coding agent:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-docker into a folder called agent-platform,
cd into it, and follow .agents/skills/setup-platform/SKILL.md.
```

It checks Docker, helps you add your API key, starts the platform, and walks you
through building your first agent. Already cloned the repo? Ask your coding agent
to follow [setup-platform](.agents/skills/setup-platform/SKILL.md) in that folder.

Prefer to set it up yourself? Follow the steps below.

## Run locally

You'll need Git, Docker with Compose, and an OpenAI API key. Make sure Docker is running.
Run the commands below in a terminal.

### 1. Start the platform

```sh
git clone https://github.com/agno-agi/agentos-docker agent-platform
cd agent-platform
[ -f .env ] || cp example.env .env
```

Open `.env` and set `OPENAI_API_KEY`. Then start the platform:

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

If the platform doesn't start, check `docker compose logs agentos-api agentos-db`.
Local development doesn't require login tokens. The API and database are only exposed
on your machine; [production requires authentication](#deploy-in-production).

### 2. Connect the UI

1. Open [os.agno.com](https://os.agno.com) and sign in.
2. Choose **Connect OS**, select a local connection, and enter `http://localhost:8000`.
3. Name it **Local AgentOS**, then open the chat for **OS Manager**.

### 3. Build your first agent

Tell OS Manager what you want to build. For example:

> Help me build an agent that answers questions about my product. Here's the documentation URL: …

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
| Fix failing tests or try more scenarios | [/eval-and-improve](.agents/skills/eval-and-improve/SKILL.md) |
| Check the repo before sharing or releasing it | [/review-and-improve](.agents/skills/review-and-improve/SKILL.md) |

If you write an agent in Python, put it in `agents/` and add it to
[app/main.py](app/main.py) so the platform can run it. Set its description and
suggested prompts in [app/config.yaml](app/config.yaml). To make a tool or model
available in Studio, add it to [app/registry.py](app/registry.py).

You can give agents documents to search, a notebook to keep notes, and memory
to remember each user. Keep a product's documentation in its own knowledge base,
separate from the platform's documents.

## Company

Company organizes ongoing work. A **Product** is what you're working on, a
**Project** groups related work, and a **Task** is one piece of work to complete.
A **Routine** is a set of instructions that can run on a schedule.

This template includes an **AgentOS** Product for improving the platform itself.
To get started, ask OS Manager:

> Review this codebase and recent Agno releases. Suggest the most useful improvements.

It also includes a daily review at **09:00 UTC**. Company Manager reads the code
and Agno release notes, then proposes up to three Tasks for you to review.
The review is instructed to suggest work and leave approval and execution to you.
Automatic acceptance is off.

Scheduled reviews use your model API keys and incur usage costs. Check the saved
schedule and run history in Company to see when a review will run and what it did.

[app/company.py](app/company.py) sets the initial review instructions and schedule.
Once they're saved in the database, update the saved Routine to change them;
editing the Python file alone won't change an existing Routine.

## Engineers

The platform includes **Claude Engineer** and **Codex Engineer**. They can read your
code, make changes, and run commands.

Chat with either engineer in AgentOS, or ask OS Manager to use one:

> Ask Codex Engineer to review this project and suggest improvements. Don't change any files yet.

Codex uses the `OPENAI_API_KEY` you added during setup. To use Claude, add
`ANTHROPIC_API_KEY` to `.env`. After changing `.env`, run `docker compose up -d` again.

By default, engineers work in this project's folder. When running locally with
Docker Compose, their file changes appear in your local checkout. Review those
changes before committing them.

You don't need to configure a sandbox or repository URL to get started.

To have engineers work on a separate copy of your repository, follow the
[sandbox setup guide](docs/sandboxes.md) for Docker or AWS AgentCore.

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
[the sandbox configuration](docs/sandboxes.md#choose-your-repository).

<a id="deploy-in-production"></a>

## Deploy in production

Ask your coding agent to follow [deploy-platform](.agents/skills/deploy-platform/SKILL.md),
or use the steps below. For an existing deployment, read the [upgrade guide](docs/upgrading.md) first.

You'll need Docker Compose 2.24.4 or newer and a stable public HTTPS URL routed
to port 8000 on your host. Use a reverse proxy on the host or an HTTPS tunnel.

### 1. Configure the host

Production Compose reads `.env`. Set `OPENAI_API_KEY`, `AGENTOS_URL` to your
public HTTPS URL, a strong `DB_PASS`, and `MCP_CONNECT_SECRET` (generate one with
`openssl rand -base64 32`).

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

Local Docker sandbox instructions are in the [sandbox guide](docs/sandboxes.md).
The production deployment does not provision sandbox checkpoint storage.
Before enabling AWS AgentCore, configure persistent storage mounted at `/data`
on the API service and give it AWS access. If your deployment cannot provide
that mount, leave AgentCore disabled. Keep one API instance.

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
