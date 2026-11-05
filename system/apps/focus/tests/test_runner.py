"""The web routes, exercised through Flask's test client with the model faked."""
import json
from pathlib import Path

from focus import store


def post(client, url: str, body: dict | None = None):
    return client.post(url, json=body or {})


def test_pages_and_health_answer(client) -> None:
    assert client.get("/health").get_json() == {"status": "ok"}
    index = client.get("/")
    assert index.status_code == 200 and b"Focus" in index.data
    setup = client.get("/setup")
    assert setup.status_code == 200
    assert client.get("/style.css").status_code == 200


def test_shell_modules_are_served_only_by_allow_list(client) -> None:
    assert client.get("/_static/secrets.js").status_code == 404
    assert client.get("/_static/..%2Fstate.json").status_code == 404


def test_state_starts_empty_with_no_mirror(client) -> None:
    assert client.get("/api/state").get_json() == {"current": None, "history": [], "mirror": None}


def test_saving_a_focus_needs_a_thing_and_a_step(client) -> None:
    assert post(client, "/api/focus", {"thing": "", "steps": ["a."]}).status_code == 400
    assert post(client, "/api/focus", {"thing": "Pay the rent.", "steps": ["  "]}).status_code == 400
    assert post(client, "/api/focus", {"thing": "Pay the rent.", "steps": ["Open the app."]}).status_code == 200
    state = client.get("/api/state").get_json()
    assert state["current"]["thing"] == "Pay the rent."


def test_toggle_route_crosses_a_step_out_and_reports_a_missing_step(client) -> None:
    state = post(client, "/api/focus", {"thing": "Pay the rent.", "steps": ["Open the app."]}).get_json()
    step_id = state["current"]["steps"][0]["id"]
    assert post(client, f"/api/steps/{step_id}/toggle").get_json()["current"]["steps"][0]["done"] is True
    missing = post(client, "/api/steps/nope/toggle")
    assert missing.status_code == 404 and "Reload" in missing.get_json()["detail"]


def test_split_route_adds_children_and_logs_the_raw_call(client, fake_model, data_dir: Path) -> None:
    fake_model(json.dumps({"steps": ["Find the app.", "Tap it."]}))
    state = post(client, "/api/focus", {"thing": "Pay the rent.", "steps": ["Open the app."]}).get_json()
    step_id = state["current"]["steps"][0]["id"]
    updated = post(client, f"/api/steps/{step_id}/split").get_json()
    assert [c["text"] for c in updated["current"]["steps"][0]["children"]] == ["Find the app.", "Tap it."]
    [line] = (data_dir / "calls.jsonl").read_text().splitlines()
    logged = json.loads(line)
    assert logged["kind"] == "split" and logged["step_id"] == step_id and "Find the app." in logged["raw_output"]


def test_split_route_reports_a_helper_failure_and_changes_nothing(client, fake_model) -> None:
    fake_model("not json at all")
    state = post(client, "/api/focus", {"thing": "Pay the rent.", "steps": ["Open the app."]}).get_json()
    step_id = state["current"]["steps"][0]["id"]
    response = post(client, f"/api/steps/{step_id}/split")
    assert response.status_code == 502 and "could not break it down" in response.get_json()["detail"]
    assert client.get("/api/state").get_json()["current"]["steps"][0]["children"] == []


def test_split_with_no_current_focus_is_a_404(client) -> None:
    assert post(client, "/api/steps/anything/split").status_code == 404


def test_chat_starts_a_saved_conversation_and_returns_the_proposal(client, fake_model) -> None:
    fake_model(json.dumps({"reply": "Rent first.", "proposal": {"thing": "Pay the rent.", "steps": ["Open the app."]}}))
    answer = post(client, "/api/helper/chat", {"text": "rent, taxes"}).get_json()
    assert answer["reply"] == "Rent first." and answer["proposal"]["thing"] == "Pay the rent."
    saved = client.get(f"/api/conversations/{answer['conversation_id']}").get_json()
    assert [m["role"] for m in saved["messages"]] == ["you", "helper"]
    assert "Rent first." in saved["calls"][0]["raw_output"]


def test_chat_continues_an_existing_conversation(client, fake_model) -> None:
    fake = fake_model(json.dumps({"reply": "Which is due sooner?", "proposal": None}), json.dumps({"reply": "Taxes.", "proposal": None}))
    first = post(client, "/api/helper/chat", {"text": "rent or taxes"}).get_json()
    second = post(client, "/api/helper/chat", {"text": "taxes", "conversation_id": first["conversation_id"]}).get_json()
    assert second["conversation_id"] == first["conversation_id"]
    assert "Helper: Which is due sooner?" in fake.calls[1]["prompt"]
    saved = client.get(f"/api/conversations/{first['conversation_id']}").get_json()
    assert len(saved["messages"]) == 4


def test_chat_needs_text_and_keeps_the_conversation_clean_when_the_helper_fails(client, fake_model) -> None:
    assert post(client, "/api/helper/chat", {"text": "  "}).status_code == 400
    fake_model(json.dumps({"reply": "Fine.", "proposal": None}), "garbled")
    first = post(client, "/api/helper/chat", {"text": "hello"}).get_json()
    failed = post(client, "/api/helper/chat", {"text": "again", "conversation_id": first["conversation_id"]})
    assert failed.status_code == 502
    saved = client.get(f"/api/conversations/{first['conversation_id']}").get_json()
    assert [m["text"] for m in saved["messages"]] == ["hello", "Fine."]


def test_smaller_returns_steps_and_notes_it_in_the_conversation(client, fake_model) -> None:
    fake_model(json.dumps({"reply": "Rent first.", "proposal": None}), json.dumps({"steps": ["a.", "b.", "c."]}))
    first = post(client, "/api/helper/chat", {"text": "rent"}).get_json()
    answer = post(client, "/api/helper/smaller", {"thing": "Pay the rent.", "steps": ["Open the app."], "conversation_id": first["conversation_id"]})
    assert answer.get_json() == {"steps": ["a.", "b.", "c."]}
    saved = client.get(f"/api/conversations/{first['conversation_id']}").get_json()
    assert saved["messages"][-1]["proposal"] == {"thing": "Pay the rent.", "steps": ["a.", "b.", "c."]}
    assert saved["calls"][-1]["kind"] == "smaller"


def test_smaller_without_a_conversation_goes_to_the_call_log(client, fake_model, data_dir: Path) -> None:
    fake_model(json.dumps({"steps": ["a."]}))
    assert post(client, "/api/helper/smaller", {"thing": "Pay the rent.", "steps": ["Open the app."]}).status_code == 200
    assert json.loads((data_dir / "calls.jsonl").read_text().splitlines()[0])["kind"] == "smaller"
    assert post(client, "/api/helper/smaller", {"thing": "", "steps": []}).status_code == 400


def test_unknown_conversation_is_a_404(client) -> None:
    assert client.get("/api/conversations/nope").status_code == 404
    assert client.get("/api/conversations/..").status_code == 404


def test_a_view_only_copy_refuses_changes_and_says_where_the_real_one_is(client, data_dir: Path) -> None:
    store.save_focus("Pay the rent.", ["Open the app."], None)
    (data_dir / "mirror.json").write_text(json.dumps({"source": "main-machine", "source_url": "https://example.test/", "pulled_at": 1.5}))
    state = client.get("/api/state").get_json()
    assert state["mirror"] == {"source": "main-machine", "url": "https://example.test/", "pulled_at": 1.5}
    for url in ("/api/focus", "/api/helper/chat", "/api/steps/x/toggle"):
        refused = post(client, url, {"thing": "x", "steps": ["y."], "text": "z"})
        assert refused.status_code == 409 and "main-machine" in refused.get_json()["detail"]
    assert store.load_state()["current"]["thing"] == "Pay the rent."


def test_a_broken_mirror_file_is_ignored(client, data_dir: Path) -> None:
    data_dir.mkdir(parents=True)
    (data_dir / "mirror.json").write_text("{broken")
    assert post(client, "/api/focus", {"thing": "Pay the rent.", "steps": ["a."]}).status_code == 200
