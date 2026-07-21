---
name: setup-platform
description: Set up this AgentOS from a fresh clone — confirm Docker, configure .env, boot the containers, prove the MCP endpoint live, connect the AgentOS UI, then build the user's first agent. Use when the user asks to set up the platform, get started, or bring this repo up on a new machine.
---

# Set Up the Platform

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/setup-platform`) or describe the task and it triggers automatically._

You are taking the user from a fresh clone to a running platform with their first agent live on it. The wow moment is Step 7 — watching their own agent get built and answer, minutes after cloning, then appear in the UI they connected moments earlier. Everything before it is setup; everything after it is handing over the loop. Pace accordingly.

**Be self-driving:** anything you can do — open a file, open a URL, launch an app — do it. Stop when you need a human: typing a secret, installing software, signing in to a website. When you do stop, tell the user exactly what to do. Never print or echo secret values.

## 1. Read the manual

Read [`AGENTS.md`](../../../AGENTS.md) end to end — it is the source of truth for how this platform works and answers most questions you'll hit along the way.

## 2. Docker

Confirm Docker is installed and running (`docker info` succeeds). If it's installed but not running, start it (`open -a Docker` on macOS) and poll until it's up. Stop for the user only if Docker isn't installed — give them the steps to install Docker Desktop and wait.

## 3. Environment

Run `cp example.env .env`, then help the user set their `OPENAI_API_KEY`:

- If it's already set in their shell, say you found one and offer to copy it in — move the value across without reading or printing it.
- Otherwise open `.env` in their editor (cursor, code, etc.) and ask them to paste the key in. Never open a terminal editor like vim or nano from your own shell — it will hang the session.

## 4. Boot

Start the platform with `docker compose up -d --build`, then poll http://localhost:8000/docs until it returns 200 (the first build takes a few minutes). If it never comes up, read `docker compose logs agentos-api` and fix what you find.

## 5. Prove it

Run `./scripts/mcp_check.sh` — it should print "MCP OK" and a real agent answer. Show the user that answer: it's their platform talking.

## 6. Connect the AgentOS UI

Their platform is live — connect it to the AgentOS UI before building anything, so their first agent lands somewhere they can watch. Most users arrive from the Agno onboarding with the **Connect your OS** screen still open, showing "Awaiting connection". Tell them their AgentOS is up and to flip back to that tab: keep **Local** selected, the endpoint already reads `http://localhost:8000`, the default name is fine — hit **Connect OS**. If they don't have that screen open, open https://os.agno.com, have them sign in, and walk them through the same form: **Connect OS** → **Local** → endpoint `http://localhost:8000` → name it **Local AgentOS** → hit **Connect OS**. Either way, the UI is where they chat with their agents and inspect sessions, memory, and evals.

Don't gate on the click — deliver the connect instructions and the first build question (Step 7) in the same message, so the platform connects while you're already talking about what to build. If they'd rather skip the UI, carry on — they can connect anytime.

## 7. Build their first agent

Now the fun part — don't ask permission, roll straight in. In the same message as the connect instructions, say you're building their first agent right now (they can always run `/create-new-agent` later for more), and start [`create-new-agent`](../create-new-agent/SKILL.md): if they've hinted at an idea anywhere in the session, propose it; otherwise end with that skill's discovery question — and, unlike a bare `/create-new-agent` run, offer a few example handoffs alongside it so a brand-new user has somewhere to start. Use the structured choice control when available, always with room for a free-form answer, e.g.:

- research content for my blog posts
- draft tweets from ideas I have
- watch Hacker News for topics I care about
- keep an eye on what competitors ship

The options are calibration, not a menu — the pick is their first discovery answer, create-new-agent's follow-up dig still applies, and their own words always beat an option. Your live-and-connect message should close with the first build move — the discovery question, or your build proposal if they've already hinted at an idea — never with "ready?" or "connected yet?".

Then follow the skill through its smoke test: work out what to build, generate the agent, register it, and prove it live. Show the user their agent's first answer — and if they connected in Step 6, tell them to hit **Refresh** in the UI: their agent is now in the Agents list next to the built-in ones. Then come back here — Step 8 takes over from that skill's own closing handoff.

If they push back or want to stop, that's fine — carry on and adapt the remaining steps.

## 8. Hand over the loop

Finish with a short summary of what you built together and the loop the user now owns:

- [`/extend-agent`](../extend-agent/SKILL.md) — change the agent: add a tool or source, add a capability, fix a known bug.
- [`/improve-agent`](../improve-agent/SKILL.md) — recursively improve it using simulations and probes.
- [`/create-new-agent`](../create-new-agent/SKILL.md) — whenever they want another.

Mention in one line that they can also connect the platform to coding agents (like yourself) with `uvx agno connect`, and to claude.ai / ChatGPT over OAuth once the platform is deployed with a public URL.
