# Setting up Focus

Focus needs no outside account, no secret and no device. It needs the workspace's Claude sign-in, because the helper
runs `claude -p`. Steps marked *seen* were run on 2026-11-05 in the workspace this template was cut from.

## 1. Before you start

- A workspace with `uv` and `supervisord` (any current one has both).
- Claude reachable through `claude -p` on the workspace's own sign-in; the helper never uses an API key.
- Port 8123 free. To use another, change both `--url http://localhost:8123` and `FOCUS_PORT=8123` in
  `system/supervisord.conf.d/focus.conf`.

## 2. Start it

The template already contains the app (`system/apps/focus/`) and its program file. Start it:

```bash
supervisorctl reread && supervisorctl update
```

The program builds the app's own environment (`uv sync --locked`), registers the page with the desktop and starts it.
Check: `supervisorctl status focus` is RUNNING and `curl -s localhost:8123/health` prints `{"status":"ok"}`.

## 3. Try it

Open Focus from the desktop. With no data it says "Nothing chosen yet." with a "Choose one thing" link.

1. Open "Choose one thing", type what is on your mind and press "Help me choose".
2. The helper answers within a few seconds with a short reason, a one-sentence thing and 3 to 5 first steps
   (*seen*: 8.4 s for a first answer, 3.0 s to split a step, on 2026-11-05).
3. Edit anything, then Save. The main screen now shows the one thing and its steps; click a step to cross it out, and
   "Too big" on the first unfinished step splits it.

If the helper fails, the page shows "The helper did not answer: ..." with the program's error text; the usual cause is
that `claude -p` is signed out in this workspace.

## 4. Check the data

`data/.apps/focus/state.json` holds the current focus and history; `conversations/<id>.json` holds each helper
conversation with the model's raw answers. These are personal: do not publish them.
