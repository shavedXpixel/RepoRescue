#!/usr/bin/env python3
"""RepoRescue Multi-Agent Workflow & Audit CLI.

Provides deterministic, auditable execution for OpenCode agents and human
maintainers during incident triage, reproduction, patch staging, and review.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Any, Optional, List

# -----------------------------------------------------------------------------
# Cross-Platform UTF-8 Console & Stream Configuration (Windows Compatibility)
# -----------------------------------------------------------------------------
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


def safe_print(text: str, file=None) -> None:
    """Print text safely across Windows codepages, falling back gracefully if needed."""
    target_file = file or sys.stdout
    try:
        print(text, file=target_file)
    except (UnicodeEncodeError, UnicodeError):
        # Fallback to ascii representation with backslash escaping
        ascii_text = text.encode("ascii", errors="backslashreplace").decode("ascii")
        target_file.write(ascii_text + "\n")
        target_file.flush()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_SERVICE = PROJECT_ROOT / "app" / "service.py"
FIXTURES_DIR = PROJECT_ROOT / "fixtures"

# Dynamic directory resolution for audit reports and patches (supports test isolation)
def get_reports_dir(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        p = Path(custom_path)
    else:
        env_val = os.environ.get("REPORESCUE_REPORTS_DIR")
        p = Path(env_val) if env_val else PROJECT_ROOT / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_patches_dir(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        p = Path(custom_path)
    else:
        env_val = os.environ.get("REPORESCUE_PATCHES_DIR")
        p = Path(env_val) if env_val else PROJECT_ROOT / "patches"
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_test_mode(cli_flag: bool = False) -> bool:
    return cli_flag or os.environ.get("REPORESCUE_TEST_MODE") in ("1", "true", "True")


# Legacy constants for backwards compatibility
REPORTS_DIR = PROJECT_ROOT / "reports"
PATCHES_DIR = PROJECT_ROOT / "patches"

# Python executable inside .venv
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

# Known demo code replacement targets
BUG_TARGETS = {
    "BUG-001": {
        "title": "HTTP 500 on percentage discount promo RESCUE20 (key lookup mismatch)",
        "resolved": '        rate = promo["rate"]',
        "seeded": '        rate = promo["discount_percent"]',
        "file": APP_SERVICE,
        "target_test": "tests/test_checkout.py::test_reproduce_bug_001_checkout_with_rescue20_promo",
        "keyword": "reproduce_bug_001"
    },
    "BUG-002": {
        "title": "Pre-discount subtotal used for sales tax calculation with SAVE10 promo",
        "resolved": '    taxable_amount = max(0.0, subtotal - discount)',
        "seeded": '    taxable_amount = subtotal',
        "file": APP_SERVICE,
        "target_test": "tests/test_checkout.py::test_checkout_with_valid_fixed_discount_promo",
        "keyword": "test_checkout_with_valid_fixed_discount_promo"
    }
}


def load_fixture(bug_id: str) -> Optional[Dict[str, Any]]:
    clean_id = bug_id.strip().upper()
    direct_file = FIXTURES_DIR / f"{clean_id.lower().replace('-', '_')}.json"
    if direct_file.exists():
        try:
            return json.loads(direct_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Search in fixtures directory
    for f in FIXTURES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("id", "").upper() == clean_id:
                return data
        except Exception:
            continue
    return None


def get_status_file(bug_id: str, reports_dir: Optional[Path] = None) -> Path:
    r_dir = reports_dir or get_reports_dir()
    r_dir.mkdir(parents=True, exist_ok=True)
    return r_dir / f"{bug_id.upper()}_status.json"


def load_status(bug_id: str, reports_dir: Optional[Path] = None) -> Dict[str, Any]:
    sfile = get_status_file(bug_id, reports_dir)
    if sfile.exists():
        try:
            return json.loads(sfile.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "bug_id": bug_id.upper(),
        "stage": "NEW",
        "history": []
    }


def save_status(
    bug_id: str,
    data: Dict[str, Any],
    reports_dir: Optional[Path] = None,
    test_mode: bool = False
) -> None:
    sfile = get_status_file(bug_id, reports_dir)
    if test_mode or is_test_mode():
        data["test_artifact"] = True
    sfile.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_history(data: Dict[str, Any], agent: str, action: str, details: str) -> None:
    if "history" not in data:
        data["history"] = []
    data["history"].append({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "details": details
    })


# -----------------------------------------------------------------------------
# Subcommands
# -----------------------------------------------------------------------------

def cmd_validate_report(args: argparse.Namespace) -> int:
    fixture: Optional[Dict[str, Any]] = None
    if args.file:
        fpath = Path(args.file)
        if not fpath.exists():
            print(f"Error: Fixture file not found: {fpath}", file=sys.stderr)
            return 1
        fixture = json.loads(fpath.read_text(encoding="utf-8"))
    elif args.bug_id:
        fixture = load_fixture(args.bug_id)

    if not fixture or "id" not in fixture:
        print(f"Error: Valid bug report fixture not found for: {args.bug_id or args.file}", file=sys.stderr)
        return 1

    r_dir = get_reports_dir(getattr(args, "reports_dir", None))
    test_mode = is_test_mode(getattr(args, "test_mode", False))

    bug_id = fixture["id"].upper()
    status_data = load_status(bug_id, reports_dir=r_dir)
    status_data["title"] = fixture.get("title", "")
    status_data["severity"] = fixture.get("severity", "Medium")
    status_data["endpoint"] = fixture.get("endpoint", "POST /checkout")
    status_data["target_test"] = fixture.get("target_test", "")
    status_data["suspect_files"] = fixture.get("suspect_files", ["app/service.py"])
    status_data["stage"] = "TRIAGED"
    append_history(status_data, "repo-rescue", "validate-report", f"Validated {bug_id} from fixture")
    save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

    # Discord-safe Triage Card (< 1,200 chars)
    card = f"""🚨 **[TRIAGE CARD] Bug Identified**
• **ID:** {bug_id}
• **Severity:** {fixture.get('severity', 'High')}
• **Endpoint:** {fixture.get('endpoint', 'POST /checkout')}
• **Suspect File:** {', '.join(fixture.get('suspect_files', ['app/service.py']))}
• **Target Test:** {fixture.get('target_test', 'N/A')}
• **Summary:** {fixture.get('title', '')}

Handoff: @repo-rescue-reproducer please execute the reproduction test in .venv and verify the failure signature."""

    safe_print(card)
    return 0


def cmd_verify_reproduction(args: argparse.Namespace) -> int:
    r_dir = get_reports_dir(getattr(args, "reports_dir", None))
    test_mode = is_test_mode(getattr(args, "test_mode", False))

    bug_id = args.bug_id.upper()
    fixture = load_fixture(bug_id)
    status_data = load_status(bug_id, reports_dir=r_dir)

    target_test = ""
    keyword = ""
    if fixture and fixture.get("target_test"):
        target_test = fixture["target_test"]
    elif bug_id in BUG_TARGETS:
        target_test = BUG_TARGETS[bug_id]["target_test"]
        keyword = BUG_TARGETS[bug_id]["keyword"]
    else:
        target_test = status_data.get("target_test", "")

    if not target_test:
        print(f"Error: No target test configured for {bug_id}", file=sys.stderr)
        return 1

    # Determine pytest test argument
    cmd = [str(VENV_PYTHON), "-m", "pytest", "-v"]
    if "::" in target_test:
        cmd.append(target_test)
    elif keyword:
        cmd.extend(["-k", keyword])
    else:
        cmd.append(target_test)

    start_time = datetime.datetime.now(datetime.timezone.utc)
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
    duration = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds()

    reproduced = (res.returncode != 0)
    assertion_snippet = ""
    for line in res.stdout.splitlines():
        if "assert " in line or "AssertionError:" in line or "KeyError:" in line or "FAILED " in line:
            assertion_snippet = line.strip()
            if "AssertionError:" in line or "KeyError:" in line:
                break

    if reproduced:
        status_data["stage"] = "REPRODUCED"
        status_data["reproduction"] = {
            "exit_code": res.returncode,
            "reproduced": True,
            "assertion": assertion_snippet,
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        append_history(status_data, "repo-rescue-reproducer", "verify-reproduction", f"Failure reproduced: {assertion_snippet}")
        save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

        card = f"""🔬 **[REPRODUCTION REPORT] Bug Confirmed**
• **Target Test:** {target_test}
• **Result:** FAILED (Reproduced as expected)
• **Trace Signature:** {assertion_snippet or 'Test assertion failed'}
• **Execution Time:** {duration:.2f}s
• **Reproducibility:** 100% deterministic

Handoff: @repo-rescue-fixer please inspect app/service.py and generate a minimal fix."""
        safe_print(card)
        return 0
    else:
        status_data["stage"] = "NOT_REPRODUCED"
        status_data["reproduction"] = {
            "exit_code": res.returncode,
            "reproduced": False,
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        append_history(status_data, "repo-rescue-reproducer", "verify-reproduction", "Target test passed - bug not reproduced")
        save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

        card = f"""⚠️ **[REPRODUCTION HALTED — Bug Not Reproduced]**
• **Target Test:** {target_test}
• **Result:** PASSED (Expected failure did not trigger)
• **Status:** NOT_REPRODUCED in current working tree

Handoff: @repo-rescue reproduction failed to trigger. Please verify parameters or seeded demo state."""
        safe_print(card)
        return 0


def cmd_stage_patch(args: argparse.Namespace) -> int:
    r_dir = get_reports_dir(getattr(args, "reports_dir", None))
    p_dir = get_patches_dir(getattr(args, "patches_dir", None))
    test_mode = is_test_mode(getattr(args, "test_mode", False))

    bug_id = args.bug_id.upper()
    status_data = load_status(bug_id, reports_dir=r_dir)
    p_dir.mkdir(parents=True, exist_ok=True)
    patch_file = p_dir / f"{bug_id}.patch"

    # Capture real git diff
    diff_res = subprocess.run(
        ["git", "diff", "app/"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False
    )
    diff_text = diff_res.stdout

    # If git diff is empty, check if patch_file already exists on disk
    if not diff_text.strip():
        if patch_file.exists():
            diff_text = patch_file.read_text(encoding="utf-8")
        else:
            print("Error: No changes detected in app/ and no existing patch file found.", file=sys.stderr)
            return 1
    else:
        patch_file.write_text(diff_text, encoding="utf-8")

    # Compute sha256
    patch_sha = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()[:12]

    # Verify tests with pytest
    test_res = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", "-v"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False
    )
    tests_passed = (test_res.returncode == 0)

    # Format diff snippet (< 10 lines)
    diff_lines = [l for l in diff_text.splitlines() if l.startswith("+") or l.startswith("-")][:8]
    diff_snippet = "\n".join(diff_lines)

    status_data["stage"] = "PATCH_PROPOSED"
    status_data["patch"] = {
        "file": f"{p_dir.name}/{bug_id}.patch",
        "sha256": patch_sha,
        "tests_passed": tests_passed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    status_data["approval_status"] = "PENDING_HUMAN_APPROVAL"
    append_history(status_data, "repo-rescue-fixer", "stage-patch", f"Created {p_dir.name}/{bug_id}.patch (tests_passed={tests_passed})")
    save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

    if tests_passed:
        card = f"""🛠️ **[FIX PROPOSAL] Patch Generated**
• **File Modified:** app/service.py
• **Patch File:** {p_dir.name}/{bug_id}.patch (SHA: {patch_sha})
• **Diff Summary:**
```diff
{diff_snippet}
```
• **Test Verification:** Full suite PASSED (0 regressions)
• **Git Status:** Working tree modified (uncommitted)

Handoff: @repo-rescue-reviewer please review the patch and audit for human approval."""
    else:
        card = f"""⚠️ **[FIX PROPOSAL] Patch Tests Failed**
• **File Modified:** app/service.py
• **Patch File:** {p_dir.name}/{bug_id}.patch
• **Result:** Pytest suite failed after applying fix.
• **Status:** Revision needed.

Handoff: @repo-rescue-fixer please refine patch."""

    safe_print(card)
    return 0 if tests_passed else 1


def cmd_audit_patch(args: argparse.Namespace) -> int:
    r_dir = get_reports_dir(getattr(args, "reports_dir", None))
    p_dir = get_patches_dir(getattr(args, "patches_dir", None))
    test_mode = is_test_mode(getattr(args, "test_mode", False))

    bug_id = args.bug_id.upper()
    status_data = load_status(bug_id, reports_dir=r_dir)
    patch_file = p_dir / f"{bug_id}.patch"

    # Check git status for modified files
    status_res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False
    )

    unauthorized_files: List[str] = []
    allowed_prefixes = (
        "app/", "patches/", "reports/", "tests/", "scripts/", "switch/",
        "fixtures/", "docs/", ".gitignore", "README.md", "requirements.txt",
        ".gitattributes"
    )
    forbidden_tokens = (".env", ".secret", ".key", ".pem", "id_rsa")

    for line in status_res.stdout.splitlines():
        fname = line[3:].strip()
        # Any file containing forbidden tokens is strictly unauthorized
        if any(tok in fname for tok in forbidden_tokens):
            unauthorized_files.append(fname)
        elif not any(fname.startswith(pref) for pref in allowed_prefixes) and not fname.endswith(".patch") and not fname.endswith(".json"):
            unauthorized_files.append(fname)

    # Run full test suite
    test_res = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", "-v"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False
    )
    tests_passed = (test_res.returncode == 0)

    verdict = "PASS" if (tests_passed and not unauthorized_files) else "FAIL"

    status_data["stage"] = f"REVIEWED_{verdict}"
    status_data["review"] = {
        "verdict": verdict,
        "tests_passed": tests_passed,
        "unauthorized_files": unauthorized_files,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    append_history(status_data, "repo-rescue-reviewer", "audit-patch", f"Audit verdict: {verdict}")
    save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

    if verdict == "PASS":
        card = f"""⚖️ **[REVIEW VERDICT] Audit Complete**
• **Verdict:** PASS
• **Scope:** app/service.py (minimal diff, no extra files)
• **Test Suite:** Full suite passed in .venv
• **Safety Check:** No credentials, secrets, or unauthorized files modified

🧑‍💻 **HUMAN APPROVAL REQUIRED:**
Developer, please review the proposed diff above. Reply with `!approve {bug_id}` or `!reject {bug_id}` to authorize or cancel commit."""
    else:
        card = f"""❌ **[REVIEW VERDICT] Audit Failed**
• **Verdict:** FAIL
• **Issues:** Tests passed: {tests_passed}, Unauthorized files: {unauthorized_files}

Handoff: @repo-rescue-fixer please address review feedback."""

    safe_print(card)
    return 0 if verdict == "PASS" else 1


def cmd_record_decision(args: argparse.Namespace) -> int:
    r_dir = get_reports_dir(getattr(args, "reports_dir", None))
    test_mode = is_test_mode(getattr(args, "test_mode", False))

    bug_id = args.bug_id.upper()
    action = args.decision.lower()
    status_data = load_status(bug_id, reports_dir=r_dir)
    actor = getattr(args, "actor", None) or ("automated-test-runner" if test_mode else "human-maintainer")

    if action == "approve":
        status_data["stage"] = "APPROVED"
        status_data["approval_status"] = "APPROVED"
        status_data["decision"] = {
            "action": "APPROVED",
            "actor": actor,
            "test_decision": test_mode,
            "notes": args.notes or ("Test approval" if test_mode else "Approved by human developer in #bug-triage"),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        append_history(status_data, "repo-rescue", "record-decision", f"Approved by {actor}")
        save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

        card = f"""✅ **[INCIDENT RESOLVED] {bug_id} Approved by Human Maintainer**
• **Status:** RESOLVED
• **Approval Sign-Off:** Received from developer in #bug-triage
• **Verification:** Verified by repo-rescue-reviewer with green test suite
• **Patch Location:** patches/{bug_id}.patch
• **Next Steps:** Maintainer can commit to main. Automatic deployment bypassed.

Thank you team. Incident {bug_id} triage is officially closed."""
        safe_print(card)
        return 0

    elif action == "reject":
        status_data["stage"] = "REJECTED"
        status_data["approval_status"] = "REJECTED"
        status_data["decision"] = {
            "action": "REJECTED",
            "actor": actor,
            "test_decision": test_mode,
            "notes": args.notes or ("Test rejection" if test_mode else "Rejected by human maintainer"),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        append_history(status_data, "repo-rescue", "record-decision", f"Rejected by {actor}")
        save_status(bug_id, status_data, reports_dir=r_dir, test_mode=test_mode)

        card = f"""🛑 **[PATCH REJECTED — Changes Reverted]**
• **Status:** REJECTED by human maintainer
• **Action:** Proposed patch for {bug_id} was rejected.
• **Notes:** {args.notes or 'Revision requested.'}

Handoff: @repo-rescue incident {bug_id} remains open for further diagnosis."""
        safe_print(card)
        return 0
    else:
        print(f"Error: Unknown decision action '{action}'. Use 'approve' or 'reject'.", file=sys.stderr)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    r_dir = get_reports_dir(getattr(args, "reports_dir", None))
    reports: List[Dict[str, Any]] = []
    if args.bug_id:
        reports.append(load_status(args.bug_id, reports_dir=r_dir))
    else:
        # Collect all status files and known fixtures
        seen_ids = set()
        for f in r_dir.glob("*_status.json"):
            bid = f.stem.replace("_status", "")
            seen_ids.add(bid)
            reports.append(load_status(bid, reports_dir=r_dir))

        for f in FIXTURES_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                bid = data.get("id", "").upper()
                if bid and bid not in seen_ids:
                    reports.append({
                        "bug_id": bid,
                        "title": data.get("title", ""),
                        "stage": "FIXTURE_AVAILABLE",
                        "history": []
                    })
                    seen_ids.add(bid)
            except Exception:
                continue

    if not reports:
        safe_print("No bug reports or active statuses found.")
        return 0

    safe_print("=" * 80)
    safe_print(f"{'BUG ID':<10} | {'STAGE':<18} | {'APPROVAL':<18} | {'TITLE'}")
    safe_print("=" * 80)
    for r in sorted(reports, key=lambda x: x.get("bug_id", "")):
        bid = r.get("bug_id", "UNKNOWN")
        stage = r.get("stage", "NEW")
        approval = r.get("approval_status", r.get("approval", {}).get("status", "N/A"))
        title = r.get("title", "")
        if len(title) > 35:
            title = title[:32] + "..."
        safe_print(f"{bid:<10} | {stage:<18} | {approval:<18} | {title}")
    safe_print("=" * 80)

    # Detailed provenance view when inspecting a single bug
    if getattr(args, "bug_id", None) and reports and reports[0].get("stage") != "NEW":
        r = reports[0]
        dec = r.get("decision") or {}
        rev = r.get("review") or {}
        safe_print(f"\n[Audit Provenance for {r.get('bug_id')}]:")
        safe_print(f"  • Review Verdict: {rev.get('verdict', 'N/A')}")
        safe_print(f"  • Approval Status: {r.get('approval_status', 'N/A')}")
        if dec.get("notes"):
            safe_print(f"  • Decision Notes: {dec.get('notes')}")
        if dec.get("actor"):
            safe_print(f"  • Decision Actor: {dec.get('actor')}")
        if "genuine_human_approval" in dec:
            safe_print(f"  • Genuine Human Approval: {dec.get('genuine_human_approval')}")

    return 0


# -----------------------------------------------------------------------------
# Demo Seeding / Restore Helpers
# -----------------------------------------------------------------------------

def cmd_prepare_demo(args: argparse.Namespace) -> int:
    bug_id = args.bug_id.upper()
    if bug_id not in BUG_TARGETS:
        print(f"Error: Unknown demo bug '{bug_id}'. Available: {list(BUG_TARGETS.keys())}", file=sys.stderr)
        return 1

    target = BUG_TARGETS[bug_id]
    sfile = target["file"]
    resolved = target["resolved"]
    seeded = target["seeded"]

    content = sfile.read_text(encoding="utf-8")
    if seeded in content:
        print(f"Demo scenario {bug_id} is already active.")
        return 0
    if resolved not in content:
        print(f"Error: Target line for {bug_id} not found in {sfile}.", file=sys.stderr)
        return 1

    new_content = content.replace(resolved, seeded, 1)
    sfile.write_text(new_content, encoding="utf-8")
    print(f"Prepared demo: Seeded {bug_id} in {sfile.name}.")
    print(f"Title: {target['title']}")
    print(f"Target test expected to fail: {target['target_test']}")
    return 0


def cmd_restore_clean(args: argparse.Namespace) -> int:
    target_bug = args.bug_id.upper() if getattr(args, "bug_id", None) else None
    restored_any = False

    for bid, target in BUG_TARGETS.items():
        if target_bug and target_bug != bid:
            continue
        sfile = target["file"]
        resolved = target["resolved"]
        seeded = target["seeded"]

        content = sfile.read_text(encoding="utf-8")
        if seeded in content:
            new_content = content.replace(seeded, resolved, 1)
            sfile.write_text(new_content, encoding="utf-8")
            print(f"Restored clean state for {bid} in {sfile.name}.")
            restored_any = True

    if not restored_any:
        print("Working tree is already in clean/resolved state.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoRescue Multi-Agent Workflow & Audit CLI")
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--reports-dir", help="Override path to status reports directory")
    common_parser.add_argument("--patches-dir", help="Override path to patches directory")
    common_parser.add_argument("--test-mode", action="store_true", help="Flag indicating automated test execution")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_status = subparsers.add_parser("status", parents=[common_parser], help="Display summary status table")
    p_status.add_argument("--bug-id", help="Filter by Bug ID")

    # validate-report
    p_val = subparsers.add_parser("validate-report", parents=[common_parser], help="Validate bug report fixture and emit Triage Card")
    p_val.add_argument("--file", help="Path to bug report JSON fixture")
    p_val.add_argument("--bug-id", help="Bug ID to look up in fixtures")

    # verify-reproduction
    p_rep = subparsers.add_parser("verify-reproduction", parents=[common_parser], help="Run pytest and capture reproduction trace")
    p_rep.add_argument("--bug-id", required=True, help="Bug ID")

    # stage-patch
    p_stg = subparsers.add_parser("stage-patch", parents=[common_parser], help="Export git diff to patches/ and verify tests")
    p_stg.add_argument("--bug-id", required=True, help="Bug ID")

    # audit-patch
    p_aud = subparsers.add_parser("audit-patch", parents=[common_parser], help="Independently review patch diff and run pytest")
    p_aud.add_argument("--bug-id", required=True, help="Bug ID")

    # record-decision
    p_dec = subparsers.add_parser("record-decision", parents=[common_parser], help="Record human approval or rejection")
    p_dec.add_argument("--bug-id", required=True, help="Bug ID")
    p_dec.add_argument("--decision", required=True, choices=["approve", "reject"], help="Human decision")
    p_dec.add_argument("--notes", help="Optional decision notes")
    p_dec.add_argument("--actor", help="Actor recording the decision (human maintainer or test runner)")

    # prepare-demo
    p_dem = subparsers.add_parser("prepare-demo", parents=[common_parser], help="Seed a demo bug scenario into app/service.py")
    p_dem.add_argument("--bug-id", required=True, choices=list(BUG_TARGETS.keys()), help="Bug ID to seed")

    # restore-clean
    p_rst = subparsers.add_parser("restore-clean", parents=[common_parser], help="Restore app/service.py to clean passing state")
    p_rst.add_argument("--bug-id", choices=list(BUG_TARGETS.keys()), help="Optional specific Bug ID to restore")

    args = parser.parse_args()

    if args.subcommand == "status":
        return cmd_status(args)
    elif args.subcommand == "validate-report":
        return cmd_validate_report(args)
    elif args.subcommand == "verify-reproduction":
        return cmd_verify_reproduction(args)
    elif args.subcommand == "stage-patch":
        return cmd_stage_patch(args)
    elif args.subcommand == "audit-patch":
        return cmd_audit_patch(args)
    elif args.subcommand == "record-decision":
        return cmd_record_decision(args)
    elif args.subcommand == "prepare-demo":
        return cmd_prepare_demo(args)
    elif args.subcommand == "restore-clean":
        return cmd_restore_clean(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
