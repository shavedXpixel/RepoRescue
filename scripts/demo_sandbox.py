#!/usr/bin/env python3
"""Isolated Demo Sandbox Helper for RepoRescue.

Allows judges and presenters to cleanly prepare and restore live bug scenarios
(BUG-001 or BUG-002) in app/service.py with a single command.
"""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.rescue_workflow import BUG_TARGETS, cmd_prepare_demo, cmd_restore_clean


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoRescue Demo Sandbox Helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-demos
    subparsers.add_parser("list-demos", help="List available demo bug scenarios")

    # prepare-demo
    p_prep = subparsers.add_parser("prepare-demo", help="Prepare/seed demo bug in app/service.py")
    p_prep.add_argument("--bug-id", required=True, choices=list(BUG_TARGETS.keys()), help="Bug ID to prepare")

    # restore-clean
    p_rst = subparsers.add_parser("restore-clean", help="Restore app/service.py to clean resolved state")
    p_rst.add_argument("--bug-id", choices=list(BUG_TARGETS.keys()), help="Optional bug ID to restore")

    args = parser.parse_args()

    if args.command == "list-demos":
        print("Available RepoRescue Demo Scenarios:")
        for bid, info in BUG_TARGETS.items():
            print(f"  • {bid}: {info['title']}")
            print(f"    Target test: {info['target_test']}")
        return 0
    elif args.command == "prepare-demo":
        return cmd_prepare_demo(args)
    elif args.command == "restore-clean":
        return cmd_restore_clean(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
