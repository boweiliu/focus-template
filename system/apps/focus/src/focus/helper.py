"""The helper: Claude picks the one most important thing and writes tiny first steps."""
import json
import re
import time
from typing import Any

from focus.claude_p import claude_p_completion

HELPER_MODEL = "claude-sonnet-5-5"

STYLE = """Write for someone who procrastinates and gets overwhelmed. Plain, short words. \
No praise, no exclamation marks, no markdown, no emoji."""

STEP_RULES = """Each step is one concrete physical action that starts with a verb, ends with a period, \
is under 12 words, and takes under 10 minutes. The first step takes under 2 minutes and needs no \
decision, for example "Open the budget sheet." Never write vague steps like "Think about" or "Plan"."""

CHOOSE_SYSTEM = f"""You help a person pick the single most important thing to work on right now, \
then break it into tiny first steps so starting is easy.

{STYLE}

How to choose: the most important thing is usually what someone is waiting on, what has the \
nearest real deadline, or what blocks other things. If they keep avoiding something that matters, \
that is often the one.

Ask at most one short question per reply, and at most two questions in the whole conversation. \
If you can already tell what matters most, propose right away without asking. If they disagree or \
add something, revise the proposal.

The thing: one sentence that starts with a verb, ends with a period, under 12 words.
The steps: 3 to 5. {STEP_RULES}

Answer with only a JSON object, nothing else:
{{"reply": "one or two plain sentences", "proposal": null or {{"thing": "...", "steps": ["...", "..."]}}}}
When you propose, the reply says in one sentence why this thing comes first."""

SPLIT_SYSTEM = f"""You break one step that feels too big into smaller steps.

{STYLE}

Write 2 to 4 smaller steps that together do the big step. Each takes under 5 minutes, starts with \
a verb, ends with a period, and is under 12 words. The first takes under 1 minute and needs no \
decision.

Answer with only a JSON object, nothing else: {{"steps": ["...", "..."]}}"""

SMALLER_SYSTEM = f"""You rewrite a list of first steps so each one is smaller and easier to start.

{STYLE}

Keep the same goal. Write 4 to 8 steps. {STEP_RULES} Make them smaller than the ones given: each \
under 5 minutes.

Answer with only a JSON object, nothing else: {{"steps": ["...", "..."]}}"""


class HelperError(RuntimeError):
    pass


def _parse_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise HelperError("The helper's answer had no JSON in it.")
    try:
        value = json.loads(match.group(0))
    except ValueError as exc:
        raise HelperError("The helper's answer was not readable.") from exc
    if not isinstance(value, dict):
        raise HelperError("The helper's answer was not readable.")
    return value


def _clean_steps(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise HelperError("The helper did not give a list of steps.")
    steps = [str(s).strip() for s in value if str(s).strip()]
    if not steps:
        raise HelperError("The helper gave no steps.")
    return steps[:8]


def _call(prompt: str, system: str) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.time()
    result = claude_p_completion(prompt, system=system, model=HELPER_MODEL)
    record = {
        "at": round(started, 3),
        "seconds": round(time.time() - started, 2),
        "model": HELPER_MODEL,
        "prompt": prompt,
        "raw_output": result.text,
        "cost_usd": result.cost_usd,
    }
    return _parse_json(result.text), record


def today() -> str:
    return time.strftime("%A, %B %-d, %Y")


def choose(messages: list[dict[str, str]], current: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Next helper turn. Returns ({reply, proposal}, raw call record)."""
    lines = [f"Today is {today()}."]
    if current:
        steps = "; ".join(s["text"] for s in current["steps"])
        lines.append(f"Their current focus is: {current['thing']} Steps: {steps}")
    lines.append("Conversation so far:")
    for message in messages:
        who = "Person" if message["role"] == "you" else "Helper"
        lines.append(f"{who}: {message['text']}")
    lines.append("Write the helper's next reply as JSON.")
    value, record = _call("\n\n".join(lines), CHOOSE_SYSTEM)
    reply = str(value.get("reply") or "").strip()
    proposal = value.get("proposal")
    if isinstance(proposal, dict) and str(proposal.get("thing") or "").strip():
        proposal = {"thing": str(proposal["thing"]).strip(), "steps": _clean_steps(proposal.get("steps"))}
    else:
        proposal = None
    if not reply and not proposal:
        raise HelperError("The helper gave an empty answer.")
    return {"reply": reply, "proposal": proposal}, record


def split(thing: str, step: str) -> tuple[list[str], dict[str, Any]]:
    prompt = f"The goal: {thing}\n\nThe step that feels too big: {step}"
    value, record = _call(prompt, SPLIT_SYSTEM)
    return _clean_steps(value.get("steps"))[:4], record


def smaller(thing: str, steps: list[str]) -> tuple[list[str], dict[str, Any]]:
    listed = "\n".join(f"- {s}" for s in steps)
    prompt = f"The goal: {thing}\n\nThe current steps:\n{listed}"
    value, record = _call(prompt, SMALLER_SYSTEM)
    return _clean_steps(value.get("steps")), record
