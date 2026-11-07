"""Tests for replay.py."""

from pathlib import Path

import pytest

from replay import (
    Move,
    OutputFileError,
    TurnRecord,
    colored_segments,
    read_output,
)

YELLOW_JUNCTION = "D1-\033[38;2;255;230;0mjunction\033[0m"


def read(tmp_path: Path, content: bytes) -> list[TurnRecord]:
    """Write ``content`` to an output file and read it."""
    path = tmp_path / "out.txt"
    path.write_bytes(content)
    return read_output(str(path))


def moves(records: list[TurnRecord]) -> list[list[Move]]:
    """The moves of every turn."""
    return [record.moves for record in records]


def test_one_line_per_turn(tmp_path: Path) -> None:
    """O1: each line is a turn, each word a move."""
    assert moves(read(tmp_path, b"D1-a D2-b\nD1-e\n")) == [
        [Move(1, "a"), Move(2, "b")],
        [Move(1, "e")],
    ]


def test_colors_are_stripped(tmp_path: Path) -> None:
    """O2: color codes are removed from moves but kept in ``raw``."""
    [record] = read(tmp_path, YELLOW_JUNCTION.encode() + b"\n")
    assert record.moves == [Move(1, "junction")]
    assert record.raw == YELLOW_JUNCTION


def test_blank_line_is_a_turn(tmp_path: Path) -> None:
    """O3: a blank line in the middle is a turn where nobody moves."""
    assert moves(read(tmp_path, b"D1-a\n\nD1-e\n")) == [
        [Move(1, "a")],
        [],
        [Move(1, "e")],
    ]


def test_connection_name(tmp_path: Path) -> None:
    """O4: a move onto a connection keeps the whole ``a-b`` name."""
    assert moves(read(tmp_path, b"D1-s-r\n")) == [[Move(1, "s-r")]]


@pytest.mark.parametrize(
    "word",
    [
        pytest.param("x1-a", id="O5a"),
        pytest.param("D-a", id="O5b"),
        pytest.param("D1a", id="O5c"),
        pytest.param("D1-", id="O5d"),
        pytest.param("D0x-a", id="O5e"),
    ],
)
def test_malformed_move(tmp_path: Path, word: str) -> None:
    """O5: a word that is not ``D<ID>-<name>`` reports its line."""
    with pytest.raises(OutputFileError, match=r"^line 2:"):
        read(tmp_path, f"D1-a\n{word}\n".encode())


def test_crlf(tmp_path: Path) -> None:
    """O6: CRLF line endings read the same as LF."""
    assert moves(read(tmp_path, b"D1-a\r\nD1-e\r\n")) == [
        [Move(1, "a")],
        [Move(1, "e")],
    ]


def test_no_final_newline(tmp_path: Path) -> None:
    """O7: the last line may lack its newline."""
    assert len(read(tmp_path, b"D1-a\nD1-e")) == 2


def test_trailing_blank_lines(tmp_path: Path) -> None:
    """O8: blank lines at the end are not turns."""
    assert len(read(tmp_path, b"D1-a\nD1-e\n\n\n")) == 2


def test_colored_segments() -> None:
    """O9: a line splits into runs of text with their colors."""
    raw = "D1-\033[38;2;80;140;255mpath_a\033[0m D2-x"
    assert colored_segments(raw) == [
        ("D1-", None),
        ("path_a", (80, 140, 255)),
        (" D2-x", None),
    ]


def test_empty_file(tmp_path: Path) -> None:
    """O10: an empty file has no turns."""
    assert read(tmp_path, b"") == []


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("\033[38;2;300;0;0m", id="O11a"),
        pytest.param("\033[38;2;;;m", id="O11b"),
    ],
)
def test_invalid_color_is_plain(code: str) -> None:
    """O11: a color that cannot be drawn is shown as plain text."""
    assert colored_segments(f"D1-{code}a\033[0m") == [
        ("D1-", None),
        ("a", None),
    ]
