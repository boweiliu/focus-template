"""Serves Focus: the one thing to work on now and its first steps, plus the setup screen."""
import json
import os
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, jsonify, request, send_file
from werkzeug.serving import run_simple

from focus import helper, store

ASSETS = Path(__file__).parent / "assets"
PORT = int(os.environ.get("FOCUS_PORT", "8123"))
# The shell's page modules, served from this origin (a module import is a cookie-less fetch).
SHELL_STATIC_MODULES_DIR = Path("system/apps/system_interface/imbue/system_interface/static/_static")
SHELL_STATIC_MODULE_NAMES = ("app_contract.js", "context_menu.js")

app = Flask("focus", static_folder=None)


def _body() -> dict[str, Any]:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _error(detail: str, status: int) -> tuple[Response, int]:
    return jsonify(detail=detail), status


def _mirror() -> dict[str, Any] | None:
    """A mirror.json in the data folder marks this copy as following another one; such a copy is view-only."""
    try:
        value = json.loads((store.DATA_DIR / "mirror.json").read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


@app.before_request
def refuse_changes_on_a_copy() -> tuple[Response, int] | None:
    mirror = _mirror()
    if request.method == "POST" and mirror is not None:
        return _error(f"This is a view-only copy. Make changes on {mirror.get('source', 'the main machine')}'s Focus.", 409)
    return None


@app.get("/")
def index() -> Response:
    return send_file(ASSETS / "index.html", max_age=0)


@app.get("/setup")
def setup() -> Response:
    return send_file(ASSETS / "setup.html", max_age=0)


@app.get("/style.css")
def style() -> Response:
    return send_file(ASSETS / "style.css", max_age=0)


@app.get("/health")
def health() -> Response:
    return jsonify(status="ok")


@app.get("/api/state")
def get_state() -> Response:
    """The current focus with its steps, and past focuses (newest first); ``mirror`` is set on a view-only copy."""
    mirror = _mirror()
    copy = {"source": mirror.get("source"), "url": mirror.get("source_url"), "pulled_at": mirror.get("pulled_at")} if mirror else None
    return jsonify({**store.load_state(), "mirror": copy})


@app.post("/api/steps/<step_id>/toggle")
def toggle(step_id: str) -> Response | tuple[Response, int]:
    """Cross a step out, or bring it back."""
    state = store.toggle_step(step_id)
    if state is None:
        return _error("That step is no longer on the list. Reload the page.", 404)
    return jsonify(state)


@app.post("/api/steps/<step_id>/split")
def split(step_id: str) -> Response | tuple[Response, int]:
    """Ask the helper to break one step into smaller steps, shown under it."""
    state = store.load_state()
    current = state["current"]
    step = store.find_step(current["steps"], step_id) if current else None
    if step is None:
        return _error("That step is no longer on the list. Reload the page.", 404)
    try:
        texts, record = helper.split(current["thing"], step["text"])
    except Exception as exc:  # the helper is a separate program; any failure is reported, not raised
        return _error(f"The helper could not break it down: {exc}", 502)
    store.log_call({"kind": "split", "step_id": step_id, **record})
    updated = store.set_children(step_id, texts)
    if updated is None:
        return _error("That step is no longer on the list. Reload the page.", 404)
    return jsonify(updated)


@app.post("/api/focus")
def save_focus() -> Response | tuple[Response, int]:
    """Make this the current focus. Body: {thing, steps: [text], conversation_id}."""
    body = _body()
    thing = str(body.get("thing") or "").strip()
    steps = [str(s) for s in body.get("steps") or [] if str(s).strip()]
    if not thing:
        return _error("Write the most important thing first.", 400)
    if not steps:
        return _error("Add at least one first step.", 400)
    conversation_id = body.get("conversation_id") or None
    return jsonify(store.save_focus(thing, steps, conversation_id))


@app.post("/api/helper/chat")
def helper_chat() -> Response | tuple[Response, int]:
    """Send a message to the helper. Body: {conversation_id?, text}. Answers {conversation_id, reply, proposal}."""
    body = _body()
    text = str(body.get("text") or "").strip()
    if not text:
        return _error("Write something first.", 400)
    conversation_id = str(body.get("conversation_id") or "")
    conversation = store.load_conversation(conversation_id) if conversation_id else None
    if conversation is None:
        conversation = {"id": store.new_id(), "created_at": store.now(), "messages": [], "calls": []}
    conversation["messages"].append({"role": "you", "text": text, "at": store.now()})
    store.save_conversation(conversation)
    try:
        answer, record = helper.choose(conversation["messages"], store.load_state()["current"])
    except Exception as exc:  # reported to the page; the person's message stays saved
        conversation["messages"].pop()
        store.save_conversation(conversation)
        return _error(f"The helper did not answer: {exc}", 502)
    conversation["calls"].append(record)
    conversation["messages"].append({"role": "helper", "text": answer["reply"], "proposal": answer["proposal"], "at": store.now()})
    store.save_conversation(conversation)
    return jsonify(conversation_id=conversation["id"], **answer)


@app.post("/api/helper/smaller")
def helper_smaller() -> Response | tuple[Response, int]:
    """Ask the helper to make every step smaller. Body: {thing, steps: [text], conversation_id?}."""
    body = _body()
    thing = str(body.get("thing") or "").strip()
    steps = [str(s) for s in body.get("steps") or [] if str(s).strip()]
    if not thing or not steps:
        return _error("Write the thing and at least one step first.", 400)
    try:
        texts, record = helper.smaller(thing, steps)
    except Exception as exc:
        return _error(f"The helper could not make them smaller: {exc}", 502)
    conversation = store.load_conversation(str(body.get("conversation_id") or "x-"))
    if conversation is not None:
        conversation["calls"].append({"kind": "smaller", **record})
        conversation["messages"].append({"role": "helper", "text": "Smaller version.", "proposal": {"thing": thing, "steps": texts}, "at": store.now()})
        store.save_conversation(conversation)
    else:
        store.log_call({"kind": "smaller", **record})
    return jsonify(steps=texts)


@app.get("/api/conversations/<conversation_id>")
def get_conversation(conversation_id: str) -> Response:
    """One saved talk with the helper, including exactly what the model answered."""
    conversation = store.load_conversation(conversation_id)
    if conversation is None:
        abort(404)
    return Response(json.dumps(conversation, indent=2, ensure_ascii=False), mimetype="application/json")


@app.get("/_static/<basename>")
def shell_module(basename: str) -> Response:
    if basename not in SHELL_STATIC_MODULE_NAMES:
        abort(404)
    return send_file(SHELL_STATIC_MODULES_DIR.resolve() / basename, mimetype="text/javascript", max_age=0)


def main() -> None:
    run_simple("127.0.0.1", PORT, app, threaded=True)
