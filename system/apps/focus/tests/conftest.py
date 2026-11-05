"""Shared fixtures: every test gets its own data folder and never reaches a real model."""
from pathlib import Path
from typing import Any

import pytest

from focus import helper, runner, store
from focus.claude_p import ClaudeResult, Usage


@pytest.fixture(autouse=True)
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the store at an empty temporary folder."""
    folder = tmp_path / "focus-data"
    monkeypatch.setattr(store, "DATA_DIR", folder)
    return folder


@pytest.fixture(autouse=True)
def no_real_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if a test would start the real `claude -p`."""

    def refuse(*args: Any, **kwargs: Any) -> ClaudeResult:
        raise AssertionError("a test tried to call the real model")

    monkeypatch.setattr(helper, "claude_p_completion", refuse)


class FakeModel:
    """Stands in for `claude_p_completion`: returns the queued texts in order and records each prompt."""

    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, prompt: str, *, system: str, model: str) -> ClaudeResult:
        self.calls.append({"prompt": prompt, "system": system, "model": model})
        return ClaudeResult(text=self.texts.pop(0), cost_usd=0.01, usage=Usage(input_tokens=1, output_tokens=1), raw={})


@pytest.fixture
def fake_model(monkeypatch: pytest.MonkeyPatch):
    def install(*texts: str) -> FakeModel:
        fake = FakeModel(*texts)
        monkeypatch.setattr(helper, "claude_p_completion", fake)
        return fake

    return install


@pytest.fixture
def client():
    runner.app.config["TESTING"] = True
    return runner.app.test_client()
