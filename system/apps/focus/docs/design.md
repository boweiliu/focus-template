# Design notes

## Shape

```
browser  --  /  /setup  (static pages, no framework)
   |
Flask app (runner.py, 127.0.0.1:8123, threaded)
   |-- store.py    JSON files under DATA_DIR, one RLock, atomic replace
   |-- helper.py   prompts + answer cleaning
          |-- claude_p.py   `claude -p`, tools off, isolated cwd, model claude-sonnet-5-5
```

The pages are plain HTML with a small inline script each, and a second `<script type="module">` that connects to the
desktop shell (`/_static/app_contract.js`, `/_static/context_menu.js`, served from the shell's own static folder; the
app must be started from the workspace root for those paths to resolve; the page works without them).

## What the user sees, and why

- One thing and one list: the point is to remove choice. The main page never shows history, settings or anything else.
- The "Too big" link appears only on the first unfinished step (and only above depth 3), so there is always exactly one
  place to act. Splitting adds children under the step; a parent with children cannot be crossed out itself, it is
  done when all its children are (`store.all_done`).
- The helper's rules are in the prompts (`helper.py`): plain short words, no praise, at most one question per reply and
  two per conversation, a thing of under 12 words, 3 to 5 steps that each start with a verb, the first under 2 minutes
  and needing no decision. These are instructions to the model, not checks in code; the code only cleans the answer
  (strips, drops empties, caps steps at 8 and a split at 4).
- Nothing is sent without a person pressing a button: a proposal from the helper fills the Setup screen, and only
  "Save" changes the current focus.

## Data on disk

| File | Holds |
| --- | --- |
| `state.json` | `{"current": {id, thing, steps[], created_at, conversation_id, updated_at?}, "history": [...]}`; a step is `{id, text, done, children[]}`; history is newest first, each entry has `ended_at` and `outcome` (`done` when every leaf step is done, else `replaced`) |
| `conversations/<id>.json` | `{id, created_at, messages[{role: you/helper, text, proposal?, at}], calls[...]}`; `calls` hold the prompt, `raw_output`, `seconds`, `cost_usd`, `model` |
| `calls.jsonl` | The same record for calls outside a conversation (splits, and "smaller" without a conversation), one JSON object per line |
| `mirror.json` | Optional. If this file exists the app is read-only (every change is refused with a 409 naming `source`); nothing in this template creates it |

Saving the same thing again edits it in place and keeps the crossed-out state of steps whose text did not change;
saving a different thing moves the old one into history. Conversation ids are 12 hex characters and are checked
(`isalnum`) before a file is opened, so an id cannot point outside the folder.

## Raw data is kept

Every model answer is stored verbatim (`raw_output`) beside the cleaned version shown, and each saved focus links to
the conversation it came from, so the page can show the original answer and a change to the cleaning needs no re-run.

## Safety rules

- The server only binds to `127.0.0.1`; there is no login because the desktop's forwarding is the access control.
- With `mirror.json` present the app refuses every POST with 409 before any handler runs (`refuse_changes_on_a_copy`).
- The shell static files are served from a fixed allow-list of two names.
- The model runs with all tools disabled and in an empty temporary folder, so it cannot read the workspace or its
  instructions files.
- The model's name is a constant in `helper.py` (`HELPER_MODEL`).
