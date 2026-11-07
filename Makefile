MAP ?= tests/fixtures/maps/easy/02_simple_fork.txt
OUT ?= tests/fixtures/outputs/easy/02_simple_fork.txt
# Fly-in repository this visualizer is cloned into, and where `play`
# saves Fly-in's output.
FLYIN ?= ..
PLAY_OUT ?= .play-output.txt

.PHONY: install run play debug clean lint lint-strict test format

install:
	@uv sync

run:
	@uv run python main.py $(MAP) $(OUT)

# Run Fly-in on MAP, then replay its output: make play MAP=../maps/...
play:
	@cd $(FLYIN) && uv run python main.py $(abspath $(MAP)) \
	    > $(abspath $(PLAY_OUT))
	@uv run python main.py $(MAP) $(PLAY_OUT)

debug:
	@uv run python -m pdb main.py $(MAP) $(OUT)

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
