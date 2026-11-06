#!/usr/bin/env python3
"""Deterministic Bug Seeding & Reset CLI for RepoRescue BUG-001.

Used during live Switch multi-agent testing in Discord.
"""

import argparse
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVICE_FILE = PROJECT_ROOT / "app" / "service.py"

RESOLVED_TARGET = '        rate = promo["rate"]'
SEEDED_TARGET = '        rate = promo["discount_percent"]'


def get_current_status(content: str) -> str:
    if 'promo["discount_percent"]' in content:
        return "SEEDED (BUG-001 active)"
    elif 'promo["rate"]' in content:
        return "RESOLVED (BUG-001 fixed)"
    else:
        return "UNKNOWN"


def cmd_status() -> int:
    if not SERVICE_FILE.exists():
        print(f"Error: {SERVICE_FILE} not found.", file=sys.stderr)
        return 1

    content = SERVICE_FILE.read_text(encoding="utf-8")
    status_str = get_current_status(content)
    print(f"Current State: {status_str}")

    print("Git status (-s):")
    try:
        res = subprocess.run(
            ["git", "status", "-s"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout:
            print(res.stdout.rstrip())
        else:
            print("(clean)")
    except Exception as e:
        print(f"Failed to run git status: {e}", file=sys.stderr)

    return 0


def cmd_seed() -> int:
    if not SERVICE_FILE.exists():
        print(f"Error: {SERVICE_FILE} not found.", file=sys.stderr)
        return 1

    with open(SERVICE_FILE, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    if SEEDED_TARGET in content:
        print("BUG-001 is already seeded in app/service.py.")
        print("Confirmation: BUG-001 is now active for live reproduction.")
        return 0

    if RESOLVED_TARGET not in content:
        print(
            f"Error: Target line '{RESOLVED_TARGET.strip()}' not found in {SERVICE_FILE}.",
            file=sys.stderr,
        )
        return 1

    new_content = content.replace(RESOLVED_TARGET, SEEDED_TARGET, 1)
    with open(SERVICE_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    print(f"Updated {SERVICE_FILE}: replaced promo['rate'] with promo['discount_percent'].")
    print("Confirmation: BUG-001 is now active for live reproduction.")
    return 0


def cmd_restore() -> int:
    if not SERVICE_FILE.exists():
        print(f"Error: {SERVICE_FILE} not found.", file=sys.stderr)
        return 1

    with open(SERVICE_FILE, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    if RESOLVED_TARGET in content:
        print("BUG-001 is already restored in app/service.py.")
        print("Confirmation: BUG-001 is restored to the fixed state.")
        return 0

    if SEEDED_TARGET not in content:
        print(
            f"Error: Target line '{SEEDED_TARGET.strip()}' not found in {SERVICE_FILE}.",
            file=sys.stderr,
        )
        return 1

    new_content = content.replace(SEEDED_TARGET, RESOLVED_TARGET, 1)
    with open(SERVICE_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    print(f"Updated {SERVICE_FILE}: restored promo['rate'].")
    print("Confirmation: BUG-001 is restored to the fixed state.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RepoRescue BUG-001 Scenario Controller"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Check current bug status in app/service.py")
    subparsers.add_parser("seed", help="Seed BUG-001 (replaces rate with discount_percent)")
    subparsers.add_parser("restore", help="Restore BUG-001 to fixed state (rate)")

    args = parser.parse_args()

    if args.command == "status":
        return cmd_status()
    elif args.command == "seed":
        return cmd_seed()
    elif args.command == "restore":
        return cmd_restore()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
