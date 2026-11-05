"""The saved state: steps, toggling, splitting, and what happens to the old focus."""
import json
from pathlib import Path

from focus import store


def test_empty_state_has_no_current_focus_and_no_history() -> None:
    assert store.load_state() == {"current": None, "history": []}


def test_saving_a_focus_makes_it_current_with_unfinished_steps() -> None:
    state = store.save_focus("Send the invoice.", ["Open the sheet.", "  ", "Type the total."], None)
    current = state["current"]
    assert current["thing"] == "Send the invoice."
    assert [s["text"] for s in current["steps"]] == ["Open the sheet.", "Type the total."]
    assert not any(s["done"] for s in current["steps"])
    assert store.load_state()["current"]["id"] == current["id"]


def test_toggling_crosses_a_step_out_and_back() -> None:
    step = store.save_focus("Send the invoice.", ["Open the sheet."], None)["current"]["steps"][0]
    assert store.toggle_step(step["id"])["current"]["steps"][0]["done"] is True
    assert store.toggle_step(step["id"])["current"]["steps"][0]["done"] is False


def test_toggling_an_unknown_step_or_a_step_with_children_changes_nothing() -> None:
    assert store.toggle_step("nope") is None
    state = store.save_focus("Send the invoice.", ["Open the sheet."], None)
    parent = state["current"]["steps"][0]
    store.set_children(parent["id"], ["Find the file.", "Double-click it."])
    assert store.toggle_step(parent["id"]) is None


def test_saving_the_same_thing_again_keeps_progress_on_unchanged_steps() -> None:
    state = store.save_focus("Send the invoice.", ["Open the sheet.", "Type the total."], None)
    first = state["current"]["steps"][0]
    store.toggle_step(first["id"])
    state = store.save_focus("Send the invoice.", ["Open the sheet.", "Check the total.", "Press send."], "abc123")
    steps = state["current"]["steps"]
    assert [s["text"] for s in steps] == ["Open the sheet.", "Check the total.", "Press send."]
    assert steps[0]["done"] is True and steps[0]["id"] == first["id"]
    assert steps[1]["done"] is False
    assert state["current"]["conversation_id"] == "abc123"
    assert state["history"] == []


def test_a_different_focus_moves_the_old_one_to_history_as_replaced() -> None:
    store.save_focus("Send the invoice.", ["Open the sheet."], None)
    state = store.save_focus("Book the dentist.", ["Find the number."], None)
    assert state["current"]["thing"] == "Book the dentist."
    [old] = state["history"]
    assert old["thing"] == "Send the invoice."
    assert old["outcome"] == "replaced"
    assert "ended_at" in old


def test_a_finished_focus_is_recorded_as_done_and_history_is_newest_first() -> None:
    state = store.save_focus("One.", ["a."], None)
    store.toggle_step(state["current"]["steps"][0]["id"])
    store.save_focus("Two.", ["b."], None)
    state = store.save_focus("Three.", ["c."], None)
    assert [h["thing"] for h in state["history"]] == ["Two.", "One."]
    assert state["history"][1]["outcome"] == "done"
    assert state["history"][0]["outcome"] == "replaced"


def test_a_focus_counts_as_done_only_when_every_leaf_step_is_done() -> None:
    state = store.save_focus("Send the invoice.", ["Open the sheet.", "Type the total."], None)
    first, second = state["current"]["steps"]
    store.set_children(second["id"], ["Find the number.", "Type it."])
    store.toggle_step(first["id"])
    current = store.load_state()["current"]
    assert not store.all_done(current["steps"])
    for child in current["steps"][1]["children"]:
        store.toggle_step(child["id"])
    assert store.all_done(store.load_state()["current"]["steps"])


def test_splitting_a_step_replaces_it_with_unfinished_children() -> None:
    state = store.save_focus("Send the invoice.", ["Open the sheet."], None)
    step = state["current"]["steps"][0]
    store.toggle_step(step["id"])
    state = store.set_children(step["id"], ["Find the file.", "", "Open it."])
    updated = state["current"]["steps"][0]
    assert [c["text"] for c in updated["children"]] == ["Find the file.", "Open it."]
    assert updated["done"] is False


def test_find_step_looks_inside_children() -> None:
    state = store.save_focus("Send the invoice.", ["Open the sheet."], None)
    parent = state["current"]["steps"][0]
    state = store.set_children(parent["id"], ["Find the file."])
    child = state["current"]["steps"][0]["children"][0]
    assert store.find_step(state["current"]["steps"], child["id"])["text"] == "Find the file."
    assert store.find_step(state["current"]["steps"], "missing") is None


def test_state_survives_a_restart_and_a_damaged_shape_reads_as_empty(data_dir: Path) -> None:
    store.save_focus("Send the invoice.", ["Open the sheet."], None)
    assert (data_dir / "state.json").is_file()
    assert store.load_state()["current"]["thing"] == "Send the invoice."
    (data_dir / "state.json").write_text(json.dumps(["not", "a", "dict"]))
    assert store.load_state() == {"current": None, "history": []}


def test_conversations_round_trip_and_reject_path_tricks(data_dir: Path) -> None:
    conversation = {"id": "abc123", "messages": [], "calls": []}
    store.save_conversation(conversation)
    assert store.load_conversation("abc123") == conversation
    assert store.load_conversation("missing") is None
    assert store.load_conversation("../state") is None
    assert store.load_conversation("") is None


def test_calls_are_appended_one_json_object_per_line(data_dir: Path) -> None:
    store.log_call({"kind": "split", "raw_output": "x"})
    store.log_call({"kind": "smaller", "raw_output": "y"})
    lines = (data_dir / "calls.jsonl").read_text().splitlines()
    assert [json.loads(line)["kind"] for line in lines] == ["split", "smaller"]
