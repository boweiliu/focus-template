"""Focus's saved state: the current focus, past focuses, and the helper conversations.

Everything lives under DATA_DIR as plain JSON:
  state.json                   current focus and history (newest first)
  conversations/<id>.json      each talk with the helper, with the model's raw output
  calls.jsonl                  every other helper call (splitting steps), raw output included
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("FOCUS_DATA_DIR", "data/.apps/focus"))
_LOCK = threading.RLock()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return round(time.time(), 3)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def load_state() -> dict[str, Any]:
    with _LOCK:
        state = _read_json(DATA_DIR / "state.json", None)
        if not isinstance(state, dict):
            state = {"current": None, "history": []}
        state.setdefault("current", None)
        state.setdefault("history", [])
        return state


def save_state(state: dict[str, Any]) -> None:
    with _LOCK:
        _write_json(DATA_DIR / "state.json", state)


def make_step(text: str) -> dict[str, Any]:
    return {"id": new_id(), "text": text.strip(), "done": False, "children": []}


def find_step(steps: list[dict[str, Any]], step_id: str) -> dict[str, Any] | None:
    for step in steps:
        if step["id"] == step_id:
            return step
        found = find_step(step.get("children", []), step_id)
        if found:
            return found
    return None


def all_done(steps: list[dict[str, Any]]) -> bool:
    if not steps:
        return False
    for step in steps:
        children = step.get("children") or []
        if children:
            if not all_done(children):
                return False
        elif not step.get("done"):
            return False
    return True


def toggle_step(step_id: str) -> dict[str, Any] | None:
    with _LOCK:
        state = load_state()
        current = state["current"]
        if not current:
            return None
        step = find_step(current["steps"], step_id)
        if step is None or step.get("children"):
            return None
        step["done"] = not step.get("done")
        save_state(state)
        return state


def set_children(step_id: str, texts: list[str]) -> dict[str, Any] | None:
    with _LOCK:
        state = load_state()
        current = state["current"]
        if not current:
            return None
        step = find_step(current["steps"], step_id)
        if step is None:
            return None
        step["children"] = [make_step(t) for t in texts if t.strip()]
        step["done"] = False
        save_state(state)
        return state


def save_focus(thing: str, step_texts: list[str], conversation_id: str | None) -> dict[str, Any]:
    """Make this the current focus.

    Saving the same thing again edits it in place and keeps the progress on steps
    whose words did not change. A different thing moves the old one into history.
    """
    thing = thing.strip()
    texts = [t.strip() for t in step_texts if t.strip()]
    with _LOCK:
        state = load_state()
        current = state["current"]
        if current and current["thing"] == thing:
            old = {s["text"]: s for s in current["steps"]}
            current["steps"] = [old.get(t) or make_step(t) for t in texts]
            if conversation_id:
                current["conversation_id"] = conversation_id
            current["updated_at"] = now()
        else:
            if current:
                current["ended_at"] = now()
                current["outcome"] = "done" if all_done(current["steps"]) else "replaced"
                state["history"].insert(0, current)
            state["current"] = {
                "id": new_id(),
                "thing": thing,
                "steps": [make_step(t) for t in texts],
                "created_at": now(),
                "conversation_id": conversation_id,
            } if thing else None
        save_state(state)
        return state


def load_conversation(conversation_id: str) -> dict[str, Any] | None:
    if not conversation_id.isalnum():
        return None
    return _read_json(DATA_DIR / "conversations" / f"{conversation_id}.json", None)


def save_conversation(conversation: dict[str, Any]) -> None:
    with _LOCK:
        _write_json(DATA_DIR / "conversations" / f"{conversation['id']}.json", conversation)


def log_call(record: dict[str, Any]) -> None:
    with _LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with (DATA_DIR / "calls.jsonl").open("a") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
