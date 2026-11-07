"""Reading the output that Fly-in prints, saved to a file."""

import re
from dataclasses import dataclass

type RGB = tuple[int, int, int]

_ANSI_RE = re.compile(r"\033\[([0-9;]*)m")
_MOVE_RE = re.compile(r"^D(\d+)-(.+)$")


@dataclass(frozen=True)
class Move:
    """One word of an output line, ``D<drone>-<name>``.

    Attributes:
        drone: The drone's ID.
        name: A zone name, or a connection name ``a-b`` when the drone
            is flying towards a restricted zone.
    """

    drone: int
    name: str


@dataclass(frozen=True)
class TurnRecord:
    """One line of the output, i.e. one turn.

    Attributes:
        raw: The line as written, color codes included, without the
            newline.
        moves: The drones that moved during the turn, in line order.
    """

    raw: str
    moves: list[Move]


class OutputFileError(Exception):
    """Error in an output file, reported with its line number."""

    def __init__(self, line_no: int, message: str) -> None:
        """Build the message as ``line <line_no>: <message>``.

        Args:
            line_no: 1-based line number.
            message: What is wrong.
        """
        super().__init__(f"line {line_no}: {message}")


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes.

    Args:
        text: Text that may contain ``\\033[...m`` codes.

    Returns:
        The text without them.
    """
    return _ANSI_RE.sub("", text)


def parse_line(line_no: int, line: str) -> TurnRecord:
    """Split one output line into moves.

    Args:
        line_no: Line number, for errors.
        line: The line, without its newline; color codes allowed.

    Returns:
        The turn.

    Raises:
        OutputFileError: If a word is not ``D<ID>-<name>``.
    """
    moves: list[Move] = []
    for word in strip_ansi(line).split():
        match = _MOVE_RE.match(word)
        if match is None:
            raise OutputFileError(line_no, f"invalid move '{word}'")
        moves.append(Move(int(match[1]), match[2]))
    return TurnRecord(line, moves)


def read_output(path: str) -> list[TurnRecord]:
    """Read an output file.

    Blank lines at the end of the file are not turns.

    Args:
        path: Path to the output file.

    Returns:
        One record per turn; element ``i`` is turn ``i + 1``.

    Raises:
        OSError: If the file cannot be read.
        OutputFileError: If a line is malformed.
    """
    with open(path, encoding="utf-8") as output_file:
        lines = output_file.read().splitlines()
    while lines and not strip_ansi(lines[-1]).strip():
        lines.pop()
    return [
        parse_line(line_no, line)
        for line_no, line in enumerate(lines, start=1)
    ]


def colored_segments(raw: str) -> list[tuple[str, RGB | None]]:
    """Split a line into runs of text and the color each is shown in.

    Only 24-bit foreground colors (``38;2;r;g;b``) with values from 0 to
    255 are understood; any other code turns the color off.

    Args:
        raw: An output line with its color codes.

    Returns:
        ``(text, color)`` pairs in order; ``color`` is None for plain
        text. Empty runs are left out.
    """
    segments: list[tuple[str, RGB | None]] = []
    color: RGB | None = None
    pos = 0
    for match in _ANSI_RE.finditer(raw):
        if match.start() > pos:
            segments.append((raw[pos:match.start()], color))
        color = _rgb(match[1])
        pos = match.end()
    if pos < len(raw):
        segments.append((raw[pos:], color))
    return segments


def _rgb(params: str) -> RGB | None:
    """The color set by an SGR code's parameters, or None.

    Args:
        params: The text between ``\\033[`` and ``m``.

    Returns:
        The color for a valid ``38;2;r;g;b``; None for anything else.
    """
    parts = params.split(";")
    if len(parts) != 5 or parts[:2] != ["38", "2"]:
        return None
    if not all(part.isdigit() and int(part) <= 255 for part in parts[2:]):
        return None
    return (int(parts[2]), int(parts[3]), int(parts[4]))
