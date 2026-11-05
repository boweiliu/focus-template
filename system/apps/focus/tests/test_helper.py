"""The helper: how model answers are read, cleaned and recorded. The model itself is always faked."""
import json

import pytest

from focus import helper


def test_choose_returns_reply_and_a_cleaned_proposal(fake_model) -> None:
    fake = fake_model(json.dumps({"reply": "Rent is due first.", "proposal": {"thing": " Pay the rent. ", "steps": [" Open the bank app. ", "", "Tap pay."]}}))
    answer, record = helper.choose([{"role": "you", "text": "rent, taxes, laundry"}], None)
    assert answer == {"reply": "Rent is due first.", "proposal": {"thing": "Pay the rent.", "steps": ["Open the bank app.", "Tap pay."]}}
    assert record["raw_output"].startswith('{"reply"') and record["model"] == helper.HELPER_MODEL
    assert "Person: rent, taxes, laundry" in fake.calls[0]["prompt"]
    assert fake.calls[0]["system"] == helper.CHOOSE_SYSTEM


def test_choose_tells_the_model_about_the_current_focus_and_earlier_turns(fake_model) -> None:
    fake = fake_model(json.dumps({"reply": "Which is due sooner?", "proposal": None}))
    current = {"thing": "Pay the rent.", "steps": [{"text": "Open the bank app."}, {"text": "Tap pay."}]}
    messages = [{"role": "you", "text": "rent or taxes"}, {"role": "helper", "text": "Which is due sooner?"}, {"role": "you", "text": "taxes"}]
    answer, _ = helper.choose(messages, current)
    prompt = fake.calls[0]["prompt"]
    assert "Their current focus is: Pay the rent. Steps: Open the bank app.; Tap pay." in prompt
    assert prompt.index("Person: rent or taxes") < prompt.index("Helper: Which is due sooner?") < prompt.index("Person: taxes")
    assert answer["proposal"] is None


def test_choose_accepts_json_wrapped_in_other_words(fake_model) -> None:
    fake_model('Here you go:\n{"reply": "Ok.", "proposal": null}\nDone.')
    answer, _ = helper.choose([{"role": "you", "text": "x"}], None)
    assert answer["reply"] == "Ok."


@pytest.mark.parametrize("text", ["no json here", "{not json}", "[1, 2]"])
def test_unreadable_answers_raise_a_plain_error(fake_model, text: str) -> None:
    fake_model(text)
    with pytest.raises(helper.HelperError):
        helper.choose([{"role": "you", "text": "x"}], None)


def test_an_empty_answer_raises(fake_model) -> None:
    fake_model(json.dumps({"reply": "  ", "proposal": None}))
    with pytest.raises(helper.HelperError, match="empty"):
        helper.choose([{"role": "you", "text": "x"}], None)


def test_a_proposal_without_steps_raises(fake_model) -> None:
    fake_model(json.dumps({"reply": "Try this.", "proposal": {"thing": "Pay the rent.", "steps": []}}))
    with pytest.raises(helper.HelperError, match="no steps"):
        helper.choose([{"role": "you", "text": "x"}], None)


def test_split_gives_at_most_four_steps(fake_model) -> None:
    fake = fake_model(json.dumps({"steps": ["a.", "b.", "c.", "d.", "e."]}))
    steps, record = helper.split("Pay the rent.", "Open the bank app.")
    assert steps == ["a.", "b.", "c.", "d."]
    assert "The goal: Pay the rent." in fake.calls[0]["prompt"] and "Open the bank app." in fake.calls[0]["prompt"]
    assert record["cost_usd"] == 0.01


def test_smaller_lists_every_step_and_caps_at_eight(fake_model) -> None:
    fake = fake_model(json.dumps({"steps": [f"s{i}." for i in range(12)]}))
    steps, _ = helper.smaller("Pay the rent.", ["Open the bank app.", "Tap pay."])
    assert len(steps) == 8
    assert "- Open the bank app.\n- Tap pay." in fake.calls[0]["prompt"]


def test_a_non_list_of_steps_raises(fake_model) -> None:
    fake_model(json.dumps({"steps": "do it"}))
    with pytest.raises(helper.HelperError, match="list of steps"):
        helper.split("Pay the rent.", "Tap pay.")
