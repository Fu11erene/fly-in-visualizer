"""Tests for the entry point; the window itself is not opened."""

import sys
from pathlib import Path

import pytest

import app
from main import main

FIXTURES = Path(__file__).parent / "fixtures"
FORK_MAP = str(FIXTURES / "maps" / "easy" / "02_simple_fork.txt")
FORK_OUT = str(FIXTURES / "outputs" / "easy" / "02_simple_fork.txt")


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[object, ...]]:
    """Replace ``app.run`` with a recorder of its arguments."""
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(app, "run", lambda *args: calls.append(args))
    return calls


def test_opens_replay(
    monkeypatch: pytest.MonkeyPatch, runs: list[tuple[object, ...]]
) -> None:
    """A1: a map and its output open the window with every turn."""
    monkeypatch.setattr(sys, "argv", ["viz", FORK_MAP, FORK_OUT])
    assert main() == 0
    [(_, records, states, _)] = runs
    assert isinstance(records, list) and isinstance(states, list)
    assert len(records) == 4
    assert len(states) == 5


def test_missing_map(
    monkeypatch: pytest.MonkeyPatch,
    runs: list[tuple[object, ...]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A2: a missing file is reported and the window is not opened."""
    monkeypatch.setattr(sys, "argv", ["viz", "nope.txt", FORK_OUT])
    assert main() == 1
    assert capsys.readouterr().err.startswith("Error: ")
    assert runs == []


def test_malformed_output(
    monkeypatch: pytest.MonkeyPatch,
    runs: list[tuple[object, ...]],
    tmp_path: Path,
) -> None:
    """A3: an output file that cannot be read is reported."""
    bad = tmp_path / "out.txt"
    bad.write_text("D1-junction\nhello\n")
    monkeypatch.setattr(sys, "argv", ["viz", FORK_MAP, str(bad)])
    assert main() == 1
    assert runs == []
