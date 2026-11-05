"""The `claude -p` wrapper: result parsing and failure reporting, run against a stub program, never the real binary."""
import json
import stat
from pathlib import Path

import pytest

from focus import claude_p


def stub(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "claude-stub"
    script.write_text("#!/bin/sh\n" + body + "\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return [str(script)]


SUCCESS = {"subtype": "success", "is_error": False, "result": "hello", "total_cost_usd": 0.02, "usage": {"input_tokens": 5, "output_tokens": 7}}


def test_a_successful_run_gives_text_cost_and_usage(tmp_path: Path) -> None:
    argv = stub(tmp_path, f"cat <<'EOF'\n{json.dumps(SUCCESS)}\nEOF")
    result = claude_p._run_blocking(argv, env={}, cwd=str(tmp_path))
    assert result.text == "hello" and result.cost_usd == 0.02
    assert (result.usage.input_tokens, result.usage.output_tokens) == (5, 7)
    assert result.raw["subtype"] == "success"


def test_a_failed_exit_raises_with_the_error_text(tmp_path: Path) -> None:
    argv = stub(tmp_path, "echo 'not logged in' >&2; exit 3")
    with pytest.raises(claude_p.ClaudeCLIError, match="exited 3: not logged in"):
        claude_p._run_blocking(argv, env={}, cwd=str(tmp_path))


def test_output_that_is_not_json_raises(tmp_path: Path) -> None:
    argv = stub(tmp_path, "echo 'plain words'")
    with pytest.raises(claude_p.ClaudeCLIError, match="not valid JSON"):
        claude_p._run_blocking(argv, env={}, cwd=str(tmp_path))


@pytest.mark.parametrize(
    "payload",
    [
        {"subtype": "error_max_turns", "is_error": True, "errors": ["too long"]},
        {"subtype": "success", "total_cost_usd": 0.1},
        {"subtype": "success", "result": "x"},
        ["not", "an", "object"],
    ],
)
def test_error_and_incomplete_results_are_rejected_rather_than_read_as_empty(payload: object) -> None:
    with pytest.raises(claude_p.ClaudeCLIError):
        claude_p._parse_result(payload)


def test_a_completion_turns_all_tools_off() -> None:
    argv = claude_p._completion_argv("hi", system="be brief", model="claude-sonnet-5-5")
    assert "-p" in argv and "--tools" in argv and argv[argv.index("--tools") + 1] == ""
    assert "claude-sonnet-5-5" in argv
