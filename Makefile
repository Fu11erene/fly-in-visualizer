# Fly-in repository this visualizer is cloned into, the map to run it on,
# and where Fly-in's output is saved before it is replayed.
FLYIN ?= ..
MAP ?= $(FLYIN)/maps/easy/01_linear_path.txt
PLAY_OUT ?= .play-output.txt

.PHONY: install play debug output clean lint lint-strict test format

install:
	@uv sync

# Run Fly-in on MAP, then replay its output: make play MAP=../maps/...
play: output
	@uv run python main.py $(MAP) $(PLAY_OUT)

debug: output
	@uv run python -m pdb main.py $(MAP) $(PLAY_OUT)

output:
	@cd $(FLYIN) && uv run python main.py $(abspath $(MAP)) \
	    > $(abspath $(PLAY_OUT))

clean:
	@find . \( -name .venv -o -name .git \) -prune -o \
	    -type d \( -name ".mypy_cache" -o -name "__pycache__" \
	    -o -name ".pytest_cache" -o -name ".ruff_cache" \) \
	    -exec rm -rf {} +

lint:
	@uv run flake8 .
	@uv run mypy . \
	--warn-return-any --warn-unused-ignores \
	--ignore-missing-imports --disallow-untyped-defs \
	--check-untyped-defs

lint-strict:
	@uv run flake8 .
	@uv run mypy . --strict

test:
	@uv run pytest

format:
	@uv run ruff check . --fix
