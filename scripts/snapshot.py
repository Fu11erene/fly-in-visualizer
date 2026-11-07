"""Save one turn of a replay as a PNG, to check the drawing by eye.

Usage: SDL_VIDEODRIVER=dummy uv run python -m scripts.snapshot
       <map_file> <output_file> <turn> <png_file> [<hover_x> <hover_y>]
"""

import sys

import pygame

from colors import BACKGROUND
from fly_map import parse_map
from layout import MapLayout
from replay import read_output
from simulation import simulate
from view import draw_map

WIDTH, HEIGHT = 1280, 610


def main() -> None:
    """Draw the requested turn and save it."""
    map_file, output_file, turn, png_file = sys.argv[1:5]
    pygame.init()
    fly_map = parse_map(map_file)
    states = simulate(fly_map, read_output(output_file))
    state = states[min(int(turn), len(states) - 1)]
    hover = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else None
    surface = pygame.Surface((WIDTH, HEIGHT))
    surface.fill(BACKGROUND)
    layout = MapLayout(fly_map, 0, 0, WIDTH, HEIGHT)
    draw_map(surface, layout, fly_map, state, state, 0.0,
             pygame.font.Font(None, 20), hover)
    pygame.image.save(surface, png_file)


if __name__ == "__main__":
    main()
