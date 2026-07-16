---
name: setup-platform
description: Set up this AgentOS from a fresh clone — confirm Docker, configure .env, boot the containers, prove the MCP endpoint live, build the user's first agent, then connect the AgentOS UI. Use when the user asks to set up the platform, get started, or bring this repo up on a new machine.
---

# Set Up the Platform

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/setup-platform`) or describe the task and it triggers automatically._

You are taking the user from a fresh clone to a running platform with their first agent live on it. The wow moment is Step 6 — watching their own agent get built and answer, minutes after cloning. Everything before it is setup; everything after it is where to reach what they built. Pace accordingly.

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

## 6. Build their first agent

Now the fun part — don't ask permission, roll straight in. Tell the user the platform is up and you're building their first agent right now (they can always run `/create-new-agent` later for more), and in the same message start [`create-new-agent`](../create-new-agent/SKILL.md): if they've hinted at an idea anywhere in the session, propose it; otherwise end with that skill's discovery question. Your boot report should close with the first build question — never with "ready?".

Then follow the skill through its smoke test: work out what to build, generate the agent, register it, and prove it live. Show the user their agent's first answer, then come back here — Steps 7 and 8 take over from that skill's own closing handoff.

If they push back or want to stop, that's fine — carry on and adapt the remaining steps.

## 7. Connect the AgentOS UI

Their agent is alive — now give them a place to chat with it: the AgentOS UI. Ask if you can open https://os.agno.com and walk them through connecting: **Connect OS** → enter `http://localhost:8000` → name it **Local AgentOS**. The new agent is in the Agents list next to the built-in ones — that's where they chat with it and inspect sessions, memory, and evals. If they'd rather skip this, move on — they can connect anytime.

## 8. Hand over the loop

Finish with a short summary of what you built together and the loop the user now owns:

- [`/extend-agent`](../extend-agent/SKILL.md) — change the agent: add a tool or source, add a capability, fix a known bug.
- [`/improve-agent`](../improve-agent/SKILL.md) — recursively improve it using simulations and probes.
- [`/create-new-agent`](../create-new-agent/SKILL.md) — whenever they want another.

Mention in one line that they can also connect the platform to coding agents (like yourself) with `uvx agno connect`, and to claude.ai / ChatGPT over OAuth once the platform is deployed with a public URL.
