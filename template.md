---
title: "Focus"
description: "One screen with the single most important thing to work on now and its first small steps, with a Claude helper that picks it and breaks it down."
thumbnail: "template.svg"
version: v1
format: v2
---

# Focus

This file is the manifest for the **Focus** template (slug:
`focus`). It is the one document a future agent reads to understand,
present, and adapt this template. If you are an agent in a workspace that was
created from this template, this file is your script: read all of it, then
follow "How to adapt it" below.

## What it is

One screen with the single most important thing to work on now and its first small steps, with a Claude helper that picks it and breaks it down.

Focus is a one-screen app for people who procrastinate or get overwhelmed by a long list. It shows a single thing: the
most important thing to work on right now, in black text on white, and under it the first small steps to start it.
You click a step to cross it out. If the first open step still feels like too much, a "Too big" link next to it asks
a Claude helper to split it into two to four smaller steps. A second screen, Setup, is where the choosing happens: you
type what is on your mind, the helper asks at most two short questions, picks one thing and writes three to five tiny
first steps, and you edit anything and save. Past focuses are listed under "Before", each with the saved helper
conversation and the model's exact answers. The data is a few JSON files in the workspace; nothing is sent anywhere
except the prompt to Claude.

## How it works

The snapshot includes these paths (each is a repo-root-relative path copied
from the original agent onto a clean default-workspace-template base):

- `system/apps/focus`
- `system/supervisord.conf.d/focus.conf`

- `system/apps/focus` is the whole app, its own uv project (own `pyproject.toml` and `uv.lock`). `src/focus/runner.py`
  is a Flask server that serves two static pages (`/` and `/setup`) and a JSON API; `src/focus/store.py` keeps the state
  as JSON files under `data/.apps/focus/` (`state.json`, `conversations/<id>.json`, `calls.jsonl`) with one lock and
  atomic file replacement; `src/focus/helper.py` holds the prompts and cleans the model's answers;
  `src/focus/claude_p.py` is the workspace's keyless `claude -p` helper, run with all tools off in an empty temporary
  folder. `tests/` has 48 tests that fake the model. `docs/` has the setup, operations, design and test notes, and
  `app.toml` registers it as a desktop app (priority `user`, kept running with no window open).
- `system/supervisord.conf.d/focus.conf` is its supervisord program `focus`. It syncs the app's environment
  (`uv sync --locked`), registers the page with the desktop through `forward_port.py` on port 8123 and starts the
  `focus` command from the workspace root with `FOCUS_PORT=8123`.

At runtime the browser talks only to the Flask app on `127.0.0.1:8123`; the app talks to Claude only through the
`claude -p` command, and to the disk only under `data/.apps/focus/`.

## Recipe

This template is version `v1`. It is not a fork of the
workspace it came from -- it is DERIVED from it by a recipe: include these
paths, leave these out, apply these published-version rules. An update re-runs
the recipe against the current workspace and publishes the result as the next
version, so anything excluded stays excluded even though it still exists in the
source workspace.

The recipe is machine-read, so it lives in the sibling
[`template.toml`](template.toml) -- its `[recipe]` table -- along with
the structured requirements and the environment this template needs
installed. That file is authoritative for all of it; this one holds the prose.

## Requirements

Everything the adopting agent must deal with before this template is really
theirs. Two kinds of entry, handled at different times:

- **Activation** -- what must be SET UP before anything runs, in the
  machine-readable `requires_` forms below. The adopting agent acts on these
  ITSELF, first, before asking anything.
- **Adaptation** -- what must be DECIDED or REWIRED, in prose. Worked through
  interactively with the user, after activation.


- requires_llm: calls Claude keyless, through `claude -p` on the workspace's own sign-in, using the model
  `claude-sonnet-5-5` (the `HELPER_MODEL` constant in `src/focus/helper.py`); an adopter needs the workspace signed in
  to Claude, and on the keyed path (an `ANTHROPIC_API_KEY` with litellm) must switch the three helper calls per the
  use-ai-integration skill.

No latchkey permission and no secret is needed.

- Adaptation: the helper's model name is fixed in code; change `HELPER_MODEL` if the adopter wants another model.
- Adaptation: the prompts in `src/focus/helper.py` are written for one reader (short plain words, no praise, a first
  step under two minutes); the adopter should read them and adjust the voice and the step rules to their own taste.
- Adaptation: port 8123 is used; if it is taken, change it in both places in `system/supervisord.conf.d/focus.conf`.

## Environment

What this template needs INSTALLED, beyond what the template already has.
Declared in `template.toml`'s `[environment]` table; an adopting agent
converges it at ITS OWN pinned apt snapshot timestamp, so package versions come
out consistent with the rest of that agent's environment rather than frozen to
whatever this publisher happened to have.

Nothing extra -- runs on the stock workspace environment.

## How to adapt it

Instructions for the NEXT agent -- the one adapting this template into a
new agent. This is the `use-template` skill's template path; in short:

1. Read this entire file first, especially "Requirements" below. It holds two
   kinds of entry and they are handled at different times: the machine-readable
   `requires_` lines are ACTIVATION (set them up before anything runs), and
   the prose bullets are ADAPTATION (decide or rewire them afterwards).
2. Present the template to the user in plain, non-technical language: what
   it is, what it does, and what it needs from them (name the activation
   requirements).
3. Ask whether they want to use the same connectors (e.g. their own Slack).
   If YES: ACTIVATE FIRST -- initiate every `requires_permission` line NOW
   via a latchkey permission request (see the `connect-external-service` skill; the request
   opens the approval/login flow in the Imbue Studio app), wire up any
   `requires_secret` values, start the services, and get the app showing
   THE USER'S OWN DATA. Done for a data-backed app means the user can open it
   and see their own data -- NOT that a service starts or an endpoint returns
   200. Then tell them it is live and to take a look.
4. Only AFTER that (or immediately, if they chose different connectors -- the
   swap is then the first adaptation) ask: "How do you want to adapt it?"
5. Work through each requirement interactively, one at a time. Translate each
   into plain language, ask for a decision only when you genuinely need one,
   and resolve the obvious ones yourself.
6. When done, append a dated entry to "Adaptation history" below (never
   rewrite earlier entries) and commit.

## Publication history

This template's changelog: what each published version changed. The PUBLISHER
appends one entry per version (newest last); earlier entries are never rewritten.
This is distinct from "Adaptation history" below, which is the ADOPTERS' log.

### v1 (2026-11-05) -- first publication: the Focus app with its tests and docs, without any personal data.

## Adaptation history

Each agent that adapts this template appends one dated entry below. Earlier
entries are never rewritten.
