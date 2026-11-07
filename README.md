# fly-in-visualizer

Replays the output of [Fly-in](../Fly-in) turn by turn and highlights every
rule violation in red.

## Usage

Clone it inside the Fly-in repository (Fly-in's `.gitignore`, flake8,
mypy and ruff settings already skip `fly-in-visualizer/`):

```
cd Fly-in
git clone <this repository> fly-in-visualizer
cd fly-in-visualizer
make install
make play MAP=../maps/easy/02_simple_fork.txt
```

`make play` runs Fly-in on `MAP`, saves its output to `.play-output.txt`
and replays it. To replay an output you saved yourself:

```
make run MAP=../maps/easy/02_simple_fork.txt OUT=../out.txt
```

Without `MAP`/`OUT`, `make run` replays a sample from `tests/fixtures`.
If Fly-in is somewhere else than the parent directory, pass
`FLYIN=<path to Fly-in>` to `make play`.

## Controls

| Key | Action |
|---|---|
| SPACE | play / pause |
| LEFT / RIGHT | step one turn back / forward |
| HOME / END | first / last turn |
| 1-4 | speed 0.5x / 1x / 2x / 4x |
| mouse | buttons, click or drag the bar to seek |
| Q / ESC | quit |
