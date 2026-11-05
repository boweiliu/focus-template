# Focus

One screen that says the most important thing to work on right now, and the first small steps to start it. Black text on white, nothing else. For people who procrastinate or get overwhelmed by a long list: you see one thing and one next step.

- **Main screen** (`/`): the one thing, and its steps as a numbered list. Click a step to cross it out. "Too big" next to the first unfinished step asks the helper to split it into 2 to 4 smaller steps, shown under it (up to three levels deep).
- **Setup screen** (`/setup`): type what is on your mind and the helper (Claude, through `claude -p`) asks at most two short questions, picks one thing and writes 3 to 5 first steps. Edit anything, "Make steps smaller" rewrites the list in smaller pieces, then Save. Past focuses are listed under "Before", each with its saved helper conversation.

## How it works

A small Flask app (`src/focus/runner.py`) serves two static pages and a JSON API on port 8123. State is plain JSON files (`src/focus/store.py`). The helper (`src/focus/helper.py`) builds a prompt, calls `claude -p` with all tools off (`src/focus/claude_p.py`, the workspace's keyless Claude helper) and reads a JSON answer. Every model answer is stored raw next to what was shown.

Data lives in `data/.apps/focus/` (override with `FOCUS_DATA_DIR`): `state.json`, `conversations/<id>.json` (with the model's raw output), `calls.jsonl`. Port 8123 (`FOCUS_PORT`), bound to `127.0.0.1`.

## Run and test

The supervisord program `focus` (`system/supervisord.conf.d/focus.conf`) syncs this folder's own environment and starts the app from the workspace root. To test:

```bash
cd system/apps/focus
uv sync --locked
.venv/bin/python -m pytest -q     # 48 tests, about a second, no real model
```

## Where things are

| Path | What |
| --- | --- |
| `src/focus/` | `runner.py` (routes), `store.py` (files), `helper.py` (prompts and answer cleaning), `claude_p.py` (the `claude -p` call), `assets/` (pages and style) |
| `tests/` | Tests; the model is always faked |
| `docs/` | Setup, operations, design, tests |

See `docs/setup.md` to get going.
