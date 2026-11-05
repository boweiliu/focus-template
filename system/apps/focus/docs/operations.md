# Operating Focus

## Where things are

| What | Where |
| --- | --- |
| Program | supervisord program `focus` (`supervisorctl status focus`) |
| Logs | `/var/log/supervisor/focus-stdout.log` (request log) and `focus-stderr.log`; 10 MB, 3 backups |
| Data | `data/.apps/focus/` in the workspace root (`FOCUS_DATA_DIR` overrides): `state.json`, `conversations/<id>.json`, `calls.jsonl` |
| Port | 8123 (`FOCUS_PORT`); listens on `127.0.0.1` only, the desktop forwards it |
| Health | `GET /health` returns `{"status":"ok"}` |

The data is the user's own: what they wrote, what the helper answered and the model's raw output for every call.

## Restart

`supervisorctl restart focus` after a change. The program re-syncs the app's environment on every start.

## What the messages mean

| Message on the page | Cause | What to do |
| --- | --- | --- |
| "The helper did not answer: claude -p exited N: ..." | The `claude -p` call failed (signed out, over limit, no network). The typed message is not kept in the conversation | Fix the Claude sign-in; send it again |
| "The helper's answer had no JSON in it." / "was not readable." | The model answered in another form | Send it again; the raw answer is in `calls.jsonl` or the conversation's `calls` |
| "The helper gave no steps." / "empty answer" | Valid JSON with nothing usable | Same |
| "That step is no longer on the list. Reload the page." | The page is stale: another window replaced the focus | Reload |
| "Write the most important thing first." / "Add at least one first step." | Save pressed with nothing entered | Fill them in |
| "This is a view-only copy. Make changes on ..." | A file `data/.apps/focus/mirror.json` exists, which makes the app read-only | Delete the file if this copy should accept changes |

## Safe limits

- One writer: all writes go through a lock inside one process and replace files atomically. Two processes on the same
  data folder are not supported.
- Each helper call is one `claude -p` run with tools off and an isolated working folder. Measured 2026-11-05 on one run
  each: choosing 8.4 s ($0.012), splitting a step 3.0 s ($0.004); the cost is in `cost_usd` of every raw record. There
  is no cap on calls per day.
- Past focuses are kept forever (the setup screen shows the newest 30).

## Model

The helper's model is one constant, `HELPER_MODEL` in `src/focus/helper.py` (`claude-sonnet-5-5`). Change it there and
restart.

## Backing up or moving the data

Copy `data/.apps/focus/` (plain JSON).
