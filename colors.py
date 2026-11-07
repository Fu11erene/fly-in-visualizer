"""Colors used to draw the map."""

from replay import RGB

ZONE_COLORS: dict[str, RGB] = {
    "black": (128, 128, 128),  # pure black is unreadable on dark screens
    "blue": (80, 140, 255),
    "brown": (165, 105, 60),
    "crimson": (220, 20, 60),
    "cyan": (0, 220, 220),
    "darkred": (170, 0, 0),
    "gold": (255, 215, 0),
    "gray": (150, 150, 150),
    "green": (0, 200, 80),
    "lime": (50, 255, 50),
    "magenta": (255, 0, 255),
    "maroon": (176, 48, 96),
    "orange": (255, 165, 0),
    "pink": (255, 150, 200),
    "purple": (170, 90, 230),
    "red": (255, 60, 60),
    "violet": (238, 130, 238),
    "white": (255, 255, 255),
    "yellow": (255, 230, 0),
}
"""Same values as Fly-in's ``output.Color``, keyed by lower-case name."""

UNKNOWN_ZONE: RGB = (100, 100, 100)
HIGHLIGHT: RGB = (255, 159, 26)
"""Links used during the shown turn."""
ERROR: RGB = (235, 50, 50)
OK: RGB = (60, 200, 90)
BACKGROUND: RGB = (17, 17, 17)
LINK: RGB = (85, 85, 85)
TEXT: RGB = (210, 210, 210)
DIM_TEXT: RGB = (140, 140, 140)


def zone_rgb(color: str | None) -> RGB:
    """The fill color of a zone.

    Args:
        color: The zone's color name from the map file, or None.

    Returns:
        The matching color, ignoring case; ``UNKNOWN_ZONE`` when the
        name is None or not known.
    """
    if color is None:
        return UNKNOWN_ZONE
    return ZONE_COLORS.get(color.lower(), UNKNOWN_ZONE)
