"""Entry point: replay a Fly-in output file on its map."""

import argparse
import sys

import app
from fly_map import MapFileError, parse_map
from replay import OutputFileError, read_output
from simulation import simulate


def main() -> int:
    """Read the files named on the command line and open the replay.

    Returns:
        The exit status: 0 once the window is closed, 1 if a file
        cannot be read.
    """
    arg_parser = argparse.ArgumentParser(
        description="Replay Fly-in output and highlight rule violations."
    )
    arg_parser.add_argument("map_file", help="the map Fly-in was run on")
    arg_parser.add_argument("output_file", help="Fly-in's saved output")
    args = arg_parser.parse_args()

    try:
        fly_map = parse_map(args.map_file)
        records = read_output(args.output_file)
    except (
        OSError, UnicodeDecodeError, MapFileError, OutputFileError
    ) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    states = simulate(fly_map, records)
    app.run(
        fly_map, records, states, f"Fly-in Visualizer - {args.output_file}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
