# SPDX-License-Identifier: MIT
"""Small command harnesses over public study persistence and result operations."""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .facade import Study
from .results import StudyResults


def main(argv=None):
    """Inspect, verify, collect or export retained studies; return a process status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-level", choices=("OFF", "ERROR", "WARNING", "INFO", "DEBUG"), default="WARNING")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Inspect an existing portable archive")
    inspect.add_argument("directory")
    inspect.add_argument("--verify", action="store_true", help="Checksum every retained file")
    archive = commands.add_parser("archive", help="Collect verified prepared outcomes")
    archive.add_argument("study", help="Saved StudySpec JSON")
    archive.add_argument("execution", help="Prepared execution directory")
    archive.add_argument("directory", help="New immutable archive directory")
    export = commands.add_parser("export", help="Export a metadata table without loading arrays")
    export.add_argument("directory")
    export.add_argument("output", help="New .csv or .json path")
    args = parser.parse_args(argv)
    if args.log_level == "OFF":
        logging.disable(logging.CRITICAL)
    else:
        logging.basicConfig(level=getattr(logging, args.log_level), stream=sys.stderr)
    try:
        if args.command == "archive":
            results = Study.open(args.study).archive(args.execution, args.directory)
            value = results.summary()
        else:
            results = StudyResults.open(args.directory)
            if args.command == "export":
                value = {"archive_id": results.id, "path": str(results.export(args.output))}
            else:
                if args.verify:
                    results.verify()
                value = results.summary()
    except (ValueError, OSError, KeyError, ImportError) as error:
        print(f"epsm-study: {error}", file=sys.stderr)
        return 2
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0
