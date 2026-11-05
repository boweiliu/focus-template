# Tests

From `system/apps/focus`, in the app's own environment:

```bash
uv sync --locked
.venv/bin/python -m pytest -q
```

Result on 2026-11-05 (Python 3.12): **48 passed in about 0.3 s**.

| File | What it covers |
| --- | --- |
| `tests/test_store.py` | Saving, toggling, in-place edits that keep progress, moving a focus to history as done or replaced, splitting, damaged files, conversation id checks, the call log |
| `tests/test_helper.py` | Reading model answers (JSON inside other words, empty, missing steps), cleaning and caps (4 for a split, 8 for a list), what goes into each prompt |
| `tests/test_runner.py` | Every route through Flask's test client: pages, save, toggle, split, chat, smaller, saved conversations, the view-only refusal, the allow-list for shell files |
| `tests/test_claude_p.py` | Result parsing and failure reporting of the `claude -p` wrapper, run against a stub program |

What is faked: the model. `tests/conftest.py` makes any call to the real `claude -p` fail the test, and the `fake_model`
fixture queues canned answers and records each prompt. Each test gets its own temporary data folder, so no test touches
`data/.apps/focus/`, the network or any real agent. This is why the tests are safe to run on a machine with live data.

Not covered: the two pages' scripts (checked by hand with a browser on 2026-11-05).
