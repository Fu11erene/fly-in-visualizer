# fly-in-visualizer

Replays the output of [Fly-in](../Fly-in) turn by turn and highlights every
rule violation in red.

## Usage

```
cd ../Fly-in && uv run python main.py maps/easy/02_simple_fork.txt > out.txt
cd ../fly-in-visualizer
uv run python main.py ../Fly-in/maps/easy/02_simple_fork.txt ../Fly-in/out.txt
# or: make run MAP=<map file> OUT=<output file>
```

## Controls

| Key | Action |
|---|---|
| SPACE | play / pause |
| LEFT / RIGHT | step one turn back / forward |
| HOME / END | first / last turn |
| 1-4 | speed 0.5x / 1x / 2x / 4x |
| mouse | buttons, click or drag the bar to seek |
| Q / ESC | quit |
