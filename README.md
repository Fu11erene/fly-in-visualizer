# fly-in-visualizer

English | [日本語](README.ja.md)

Replays the output of Fly-in turn by turn, like a video player, and
highlights every rule violation in red. Use it to show that an output is
correct: if nothing is red, every rule held on every turn.

## Requirements

- Python 3.14 and [uv](https://github.com/astral-sh/uv)
- The Fly-in repository (this visualizer runs Fly-in to get its output)

## Usage

Clone it inside the Fly-in repository. Fly-in's `.gitignore`, flake8,
mypy and ruff settings already skip `fly-in-visualizer/`.

```
cd Fly-in
git clone https://github.com/Fu11erene/fly-in-visualizer.git
cd fly-in-visualizer
make install
make play MAP=../maps/easy/02_simple_fork.txt
```

`make play` runs Fly-in on `MAP`, saves its output to `.play-output.txt`
and replays it. If Fly-in stops with an error (missing map, no route to
end, ...), its message is shown and the window does not open.

| Variable | Default | Meaning |
|---|---|---|
| `MAP` | `../maps/easy/01_linear_path.txt` | Map to run Fly-in on |
| `FLYIN` | `..` | Path to the Fly-in repository |
| `PLAY_OUT` | `.play-output.txt` | Where Fly-in's output is saved |

## Controls

| Key | Action |
|---|---|
| SPACE | play / pause (from the last turn, restarts) |
| LEFT / RIGHT | step one turn back / forward |
| HOME / END | first / last turn |
| 1-4 | speed 0.5x / 1x / 2x / 4x (1x = one turn per second) |
| mouse | buttons; click or drag the bar to jump to a turn |
| Q / ESC | quit |

## What the screen shows

**Map (top)**

- Zones are circles in their map color, placed by their coordinates.
  Blocked zones are crossed out.
- Each zone shows `drones / max_drones` at the end of the turn. Start and
  end hold `nb_drones`.
- Each connection shows `drones / max_link_capacity` used during the
  turn, both directions combined.
- Connections used during the turn are drawn thick and orange.
- Drones are numbered white dots that move along the connections between
  turns. A drone entering a restricted zone stops halfway along the
  connection for one turn, then lands.
- When more than 6 drones wait on the same spot, they are drawn as one
  dot labelled `xN`.
- On dense maps, zone names are hidden and only counts in use are shown.
  Hover a zone to see its name, count and type.

**Panel (bottom)**

- The seek bar, with the current turn and a red mark on every turn that
  has a violation.
- The playback and speed buttons.
- The output line of the current turn, in the colors Fly-in printed.
- The violations of the current turn, or `No violations` when the whole
  replay is clean.
- A reminder of the keys.

## Violations

Counting follows Fly-in's reservation table: a zone counts the drones in
it at the end of a turn, waiting ones included; a link counts the drones
that use it during the turn. Entering a restricted zone uses the link on
the entry turn only; landing and waiting use no link.

| Rule broken | Drawn in red |
|---|---|
| More drones in a zone than `max_drones` | the zone |
| More drones on a link than `max_link_capacity` | the link |
| A move between zones that are not connected | the drone |
| Entering a blocked zone | the zone and the drone |
| Entering a restricted zone in one turn | the zone and the drone |
| A drone on a connection that does not land the next turn | the drone |
| A drone on a connection that does not lead to a restricted zone | the link and the drone |
| A zone or connection name that does not exist | the drone |
| A drone ID outside `1..nb_drones` | (message only) |
| The same drone twice on one line | the drone |
| A drone that moves again after reaching end | the drone |
| A drone not at end on the last turn | the drone |

The replay goes on after a violation: the drone is drawn where the output
says, or where it was if the output names nothing that exists.

## Development

```
make test      # pytest
make lint      # flake8 + mypy
make format    # ruff check --fix
make debug     # make play under pdb
```

`tests/fixtures/` holds every Fly-in map with the output Fly-in gave for
it; the tests check that all of them replay without a violation. To check
the drawing without a window:

```
SDL_VIDEODRIVER=dummy uv run python -m scripts.snapshot \
    <map_file> <output_file> <turn> <png_file>
```

| File | Role |
|---|---|
| `fly_map.py` | Reads the map file |
| `replay.py` | Reads Fly-in's output and its colors |
| `simulation.py` | Rebuilds each turn: positions, counts, violations |
| `player.py` | Playback clock: play, step, seek, speed |
| `layout.py`, `colors.py` | Screen positions and colors |
| `view.py` | Draws the map |
| `panel.py` | Draws the panel and handles its buttons |
| `app.py`, `main.py` | Window, main loop, command line |
