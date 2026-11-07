#!/usr/bin/env python3
"""Deterministic Bug Seeding & Reset CLI for RepoRescue.

Supports BUG-001 (percentage rate key lookup) and BUG-002 (pre-discount sales tax math)
during live Switch multi-agent testing in Discord.
"""

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Dict, Any

# Windows UTF-8 stdout/stderr stream reconfigure
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVICE_FILE = PROJECT_ROOT / "app" / "service.py"

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "BUG-001": {
        "title": "HTTP 500 on percentage promo RESCUE20 (discount_percent vs rate)",
        "resolved": '        rate = promo["rate"]',
        "seeded": '        rate = promo["discount_percent"]',
        "file": SERVICE_FILE,
        "target_test": "tests/test_checkout.py::test_reproduce_bug_001_checkout_with_rescue20_promo"
    },
    "BUG-002": {
        "title": "Pre-discount subtotal used for sales tax calculation with SAVE10 promo",
        "resolved": '    taxable_amount = max(0.0, subtotal - discount)',
        "seeded": '    taxable_amount = subtotal',
        "file": SERVICE_FILE,
        "target_test": "tests/test_checkout.py::test_checkout_with_valid_fixed_discount_promo"
    }
}


def check_status(bug_id: str, content: str) -> str:
    scenario = SCENARIOS.get(bug_id)
    if not scenario:
        return "UNKNOWN"
    if scenario["seeded"] in content:
        return f"SEEDED ({bug_id} active)"
    elif scenario["resolved"] in content:
        return f"RESOLVED ({bug_id} fixed)"
    return "UNKNOWN"


def cmd_list() -> int:
    if not SERVICE_FILE.exists():
        print(f"Error: {SERVICE_FILE} not found.", file=sys.stderr)
        return 1

    content = SERVICE_FILE.read_text(encoding="utf-8")
    print("=" * 80)
    print(f"{'BUG ID':<10} | {'STATUS':<25} | {'TARGET TEST'}")
    print("=" * 80)
    for bid, sc in SCENARIOS.items():
        st = check_status(bid, content)
        print(f"{bid:<10} | {st:<25} | {sc['target_test']}")
    print("=" * 80)
    return 0


def cmd_status(bug_id: str = None) -> int:
    if not SERVICE_FILE.exists():
        print(f"Error: {SERVICE_FILE} not found.", file=sys.stderr)
        return 1

    content = SERVICE_FILE.read_text(encoding="utf-8")
    if bug_id:
        bid = bug_id.upper()
        if bid not in SCENARIOS:
            print(f"Unknown bug ID: {bid}. Available: {list(SCENARIOS.keys())}", file=sys.stderr)
            return 1
        st = check_status(bid, content)
        print(f"Current State: {st}")
    else:
        for bid in SCENARIOS:
            st = check_status(bid, content)
            print(f"{bid}: {st}")

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


def cmd_seed(bug_id: str = "BUG-001") -> int:
    bid = bug_id.upper() if bug_id else "BUG-001"
    if bid not in SCENARIOS:
        print(f"Unknown bug ID '{bid}'. Available: {list(SCENARIOS.keys())}", file=sys.stderr)
        return 1

    scenario = SCENARIOS[bid]
    resolved = scenario["resolved"]
    seeded = scenario["seeded"]

    with open(SERVICE_FILE, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    if seeded in content:
        print(f"{bid} is already seeded in {SERVICE_FILE.name}.")
        print(f"Confirmation: {bid} is now active for live reproduction.")
        return 0

    if resolved not in content:
        print(f"Error: Target line for {bid} not found in {SERVICE_FILE.name}.", file=sys.stderr)
        return 1

    new_content = content.replace(resolved, seeded, 1)
    with open(SERVICE_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)

    print(f"Updated {SERVICE_FILE.name}: seeded {bid}.")
    print(f"Confirmation: {bid} is now active for live reproduction.")
    return 0


def cmd_restore(bug_id: str = "BUG-001", restore_all: bool = False) -> int:
    with open(SERVICE_FILE, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    targets = list(SCENARIOS.keys()) if restore_all or not bug_id else [bug_id.upper()]

    restored_any = False
    for bid in targets:
        if bid not in SCENARIOS:
            continue
        scenario = SCENARIOS[bid]
        resolved = scenario["resolved"]
        seeded = scenario["seeded"]

        if seeded in content:
            content = content.replace(seeded, resolved, 1)
            print(f"Restored clean state for {bid} in {SERVICE_FILE.name}.")
            restored_any = True

    with open(SERVICE_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(content)

    if not restored_any:
        print("Working tree is already in clean/resolved state.")
    else:
        print("Confirmation: Scenarios restored to fixed state.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoRescue Multi-Bug Scenario Controller")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all registered bug scenarios and their status")

    # status
    p_status = subparsers.add_parser("status", help="Check current bug status in app/service.py")
    p_status.add_argument("bug_id", nargs="?", default=None, help="Optional bug ID (e.g. BUG-001, BUG-002)")

    # seed
    p_seed = subparsers.add_parser("seed", help="Seed a bug into app/service.py (defaults to BUG-001)")
    p_seed.add_argument("bug_id", nargs="?", default="BUG-001", help="Bug ID to seed")

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore bug in app/service.py (defaults to BUG-001)")
    p_restore.add_argument("bug_id", nargs="?", default="BUG-001", help="Bug ID to restore")
    p_restore.add_argument("--all", action="store_true", help="Restore all scenarios to resolved state")

    args = parser.parse_args()

    if args.command == "list":
        return cmd_list()
    elif args.command == "status":
        return cmd_status(args.bug_id)
    elif args.command == "seed":
        return cmd_seed(args.bug_id)
    elif args.command == "restore":
        return cmd_restore(args.bug_id, getattr(args, "all", False))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
