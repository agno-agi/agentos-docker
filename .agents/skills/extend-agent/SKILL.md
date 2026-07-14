---
name: extend-agent
description: User-driven loop to change an existing agent in this AgentOS — add a tool/MCP server/toolkit, add a capability (knowledge base, memory, sub-agent, scheduled task), refine its instructions, or fix a specific known bug, verifying each change against the live container. Use whenever the user names a concrete change to an agent. For autonomous hardening with no specific change in mind, use improve-agent.
---

# Extend an Agent

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/extend-agent`) or describe the task and it triggers automatically._

You are recursively extending a target agent **with the user in the driver's seat**. Each iteration: the user names a change, you implement it with an Agno-aware eye (using the `agno-docs` MCP for any toolkit / API research), the change is verified against the live agent, then you ask if there's more to do. Stop when the user says they're done.

This is the user-driven half of the iteration loop. The autonomous half lives in [`improve-agent`](../improve-agent/SKILL.md) — Claude derives probes from the agent's `INSTRUCTIONS` and hardens behavior with no user input. Use this prompt to *change* the agent (add tools, add capabilities, refine the prompt, fix a known bug). Run the `improve-agent` skill afterward to confirm nothing else regressed.

The platform is on `http://localhost:8000` (`RUNTIME_ENV=dev`). Compose runs uvicorn with a scoped `--reload`, so code edits are picked up automatically; restart `agentos-api` for dependency changes or a guaranteed-clean state — Step 5 covers this.

## 0. Preconditions

- Live container reachable: `curl -sSf http://localhost:8000/health` returns 200. If not, ask the user to `docker compose up -d --build` first. (`docker compose ps` is unreliable from worktrees or alternate clones — trust the health probe.)
- Live container is bound to *this* checkout — otherwise restarts won't pick up your edits:

  ```bash
  docker inspect agentos-api --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' | grep -F "$(pwd)"
  ```

  Empty result = the container's `/app` is bound to a different repo path. Either `cd` to that repo or restart the container from this directory (`docker compose down && docker compose up -d --build`).
- Ask the user for the target agent **slug** (e.g. `web-search`).
- Recommend the user create a feature branch (`git checkout -b extend/<slug>-$(date +%Y%m%d)`) so any wrong turns are easy to revert.

## 1. Read the agent first

Open `agents/<slug>.py`. Capture:

- **Stated purpose** — the file's docstring + the `INSTRUCTIONS` string.
- **Tools** — what's wired and what each one does.
- **Pattern** — direct tools (like [`agents/web_search.py`](../../../agents/web_search.py)), context provider (the `codebase_context` wiring in [`agents/platform_manager.py`](../../../agents/platform_manager.py)), or a mix (Platform Manager also carries direct read-only runtime tools; Agent Builder is the Studio-tools pattern with delete-only confirmation gates).
- **Existing levers** — `enable_agentic_memory`, `num_history_runs`, `knowledge=`, model id.

Restate the agent's purpose to the user in 1-2 sentences before asking what to change. This catches "I thought it did X but actually it does Y" upfront.

## 2. Ask what to improve

Use the coding agent's structured user-input control when available (for example, Claude Code's `AskUserQuestion`, Codex's user-input tool, or an equivalent) with these branches. If no structured control is available, ask the same choices in concise plain text. Multi-select is fine if the user wants multiple changes in one pass — handle them sequentially in Steps 3-6, then loop:

- **Add a tool** — new MCP server, agno toolkit, or function tool.
- **Add a capability** — knowledge base (RAG), memory tweak, sub-agent / context provider, scheduled task.
- **Refine instructions** — clarify a rule, narrow scope, change tone, change format.
- **Fix a bug** — user has a specific failing prompt or wrong behavior in mind.
- **Something else** — free-form; let the user describe.

If the user picked "Fix a bug" or "Something else," ask a follow-up free-form question for the specifics (the failing prompt, the observed behavior, what they want instead).

## 3. Ground the change in agno docs

For any change touching agno surface area — toolkit imports, knowledge config, memory flags, scheduler, sub-agent patterns — search the **`agno-docs` MCP** (configured in [`.mcp.json`](../../../.mcp.json)) before writing code. Fall back to fetching <https://docs.agno.com/llms.txt> only if the MCP is unavailable.

What to capture per branch:

- **Add a tool** — import path (e.g. `from agno.tools.exa import ExaTools`), constructor args that matter for this agent, required env vars, pip dependencies. The toolkit's `Prerequisites` section lists deps and auth.
- **Add a capability**:
  - *Knowledge base* — `from db import create_knowledge`, instantiate with a name + table, pass via `knowledge=` on the Agent. Document load step (`.add_content_async()`) goes wherever ingestion lives.
  - *Memory* — flags on the Agent constructor: `enable_agentic_memory`, `enable_user_memories`, `add_history_to_context`, `num_history_runs`. Read agno's memory docs to pick the right one.
  - *Sub-agent / context provider* — mirror the `codebase_context` provider in [`agents/platform_manager.py`](../../../agents/platform_manager.py): instantiate the provider, spread `provider.get_tools()` into `tools=[...]`, and append `provider.instructions()` to `INSTRUCTIONS`. The parent sees one `query_<thing>(question)` tool; the sub-agent does the work. (Ignore that file's four runtime tools — they are plain direct tools, not part of the provider pattern.)
  - *Scheduled task* — see [agno scheduler docs](https://docs.agno.com/agent-os/scheduler) and the `scheduler=True` line in [`app/main.py`](../../../app/main.py).
- **Refine instructions** — no docs needed. Read the current `INSTRUCTIONS`, propose a minimal diff. Prefer narrowing ("on recent-events questions, follow up with a `web_fetch`") over forbidding.
- **Fix a bug** — first reproduce the failure on the live agent (see Step 6). Then identify the layer: `INSTRUCTIONS` (most common), tool (wrong tool wired or missing), model (under-capable), env (rate limit, missing key, MCP unreachable).

Don't guess any of these. If the agno-docs MCP returns nothing for a name the user gave (e.g. an MCP server they want to wire), tell them; offer to use generic `MCPTools(url=..., transport=...)` and ask for the URL.

## 4. Propose, then edit

Before editing, tell the user in 2-3 lines what you're about to change and why. Get a quick "yes" — most missteps come from misunderstanding the ask, not bad code.

Then edit. Files in scope:

- [`agents/<slug>.py`](../../../agents/) — instructions, tools, model, memory flags, knowledge.
- [`app/main.py`](../../../app/main.py) — only if registering a new sub-agent or changing interface wiring.
- [`app/config.yaml`](../../../app/config.yaml) — update the agent's manifest entry: refresh the `description` if the job changed, and add or update `quick_prompts` to exercise the new capability.
- [`pyproject.toml`](../../../pyproject.toml) — only if a toolkit needs new pip deps.

Keep edits surgical. One change per iteration of this loop — if the user asked for three things, do them one at a time so each can be smoke-tested independently.

## 5. Restart

- Restart after edits:

  ```bash
  docker compose restart agentos-api
  ```

- **Added pip deps in `pyproject.toml`** — regenerate the lockfile and rebuild:

  ```bash
  ./scripts/generate_requirements.sh
  docker compose up -d --build
  ```

After a restart or rebuild, poll `/health` until the API is back:

```bash
until curl -sSf http://localhost:8000/health > /dev/null; do sleep 0.5; done
```

Confirm the edit reached the container before smoke-testing:

```bash
docker exec agentos-api grep -c "<unique substring from your edit>" /app/agents/<slug>.py
```

`0` means the file in the container hasn't changed — almost always a bind-mount mismatch. Step 0 catches this earlier.

## 6. Smoke test the change

Pick a prompt that **exercises the change you just made**. For "Add a tool," the prompt should force the new tool to fire. For "Fix a bug," reuse the failing prompt the user described. For "Refine instructions," pick a prompt the rule was meant to handle.

> **Warning — smoke tests against `agent-builder` mutate the DB.** Its create / edit / publish / `set_current_version` Studio tools execute immediately (only the four delete tools pause for confirmation), so a prompt like "build an agent that…" creates and publishes a real component. Prefer a plan-only probe ("Which registry components would you pick for X? Do not create anything."), or snapshot component ids before the run and hard-delete anything new afterward — use `snapshot_component_ids()` / `delete_new_components()` from [`evals/cases.py`](../../../evals/cases.py). The same applies when reproducing a bug on `agent-builder` in Step 3.

```bash
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<the targeted prompt>" \
  -F "user_id=claude-extend-agent" \
  -F "stream=false" \
  -o /tmp/improve-out.json \
  -w "HTTP %{http_code} in %{time_total}s\n"

jq -r '.content // .' < /tmp/improve-out.json
```

Read tool calls from the container logs to confirm the right tool fired:

```bash
docker logs agentos-api --since 30s 2>&1 | grep -E "Running: \w+\(" | head -40
```

(`Running: <tool>(` is the line shape agno emits per tool call when `AGNO_DEBUG=True`, which compose sets for dev.)

Show the user the response and the tool calls. Did the change land?

- **Yes** — go to Step 7.
- **Almost** — one more edit pass. Iterate at most 2-3 times before stopping and asking the user how they want to proceed (revert, try a different approach, accept and move on).
- **No / made it worse** — surface what happened. Offer to revert only your last patch after showing `git diff agents/<slug>.py`; do not discard unrelated user edits.

## 7. Loop or wrap up

Ask the user (free-form): *"Anything else to improve, or are we done?"*

- **More to do** — go back to Step 2.
- **Done** — Step 8.

The recursion is the point: each iteration is one small, verified change. Drift shows up faster when changes are small and tested in isolation.

## 8. Report

Summarize for the user:

- One line per accepted change (which lever, what changed).
- `git diff --stat` plus a short `git diff` block for the agent file.
- Suggested commit message — `feat(<slug>): <one-line>` for new tools/capabilities, `fix(<slug>): <one-line>` for bug fixes, `chore(<slug>): refine instructions` for prompt-only edits. Combine if multiple types in one session.
- **Recommended next step** — run [`improve-agent`](../improve-agent/SKILL.md) to autonomously verify the agent still does what its `INSTRUCTIONS` say it does. The change you just made widened the agent's surface area; the autonomous loop catches anything that regressed.

A simple change (one tool, one prompt refinement) takes 5-10 minutes. A capability addition (knowledge base, sub-agent) usually 15-30. The loop scales linearly with how many changes the user wants to stack into one session — keep them small and verifiable.

---

## Worked example

Target: `web-search`. The user wants the agent to also be able to read PDFs from URLs.

**Step 2** — user picks "Add a tool."

**Step 3** — search the agno-docs MCP for "PDF" and "fetch." Find that `MCPTools` with the existing Parallel endpoint already covers `web_fetch` for HTML, but PDF parsing isn't included. Find `agno.tools.jina` (Jina Reader turns any URL, PDF, or HTML into clean markdown) — capture import, env var (`JINA_API_KEY`, optional — it works keyless, a key just raises the rate ceiling), pip dep (`jina`).

**Step 4** — propose: *"Add `JinaReaderTools` so `web-search` can fetch and parse PDFs. Needs `jina` in `pyproject.toml`; works keyless, set `JINA_API_KEY` for higher limits. Add a quick prompt that exercises a PDF URL."* User says yes.

Edit `agents/web_search.py` to import `JinaReaderTools` and add it to `tools=[web_tools, JinaReaderTools()]`. Add `jina` to `pyproject.toml` (and optionally `JINA_API_KEY=` to [`example.env`](../../../example.env)). Add a quick prompt to the agent's manifest entry in `app/config.yaml`:

```yaml
manifest:
  web-search:
    quick_prompts:
      - "Summarize the abstract of https://arxiv.org/pdf/2501.12948"
```

**Step 5** — pip deps changed: `./scripts/generate_requirements.sh && docker compose up -d --build`. Poll `/health`.

**Step 6** — cURL the agent with the quick prompt. Logs show `Running: read_url(` against the arxiv URL. Response is grounded in the PDF content.

**Step 7** — user says "no, that's it."

**Step 8** — diff summary, commit `feat(web-search): add JinaReaderTools for PDF fetching`, recommend the `improve-agent` skill to harden the broader behavior.

That's the loop. Most sessions are smaller — one tool, one rule, one bug.
