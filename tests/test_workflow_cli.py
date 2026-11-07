"""Unit tests for RepoRescue CLI workflow tooling (scripts/rescue_workflow.py).

Verifies Windows Unicode safety, test isolation, and audit report integrity.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

WORKFLOW_SCRIPT = PROJECT_ROOT / "scripts" / "rescue_workflow.py"


def run_cli(*args, reports_dir: Path = None, patches_dir: Path = None, extra_env: dict = None):
    """Run rescue_workflow.py CLI with UTF-8 encoding and isolated test environment."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["REPORESCUE_TEST_MODE"] = "1"
    if reports_dir:
        env["REPORESCUE_REPORTS_DIR"] = str(reports_dir)
    if patches_dir:
        env["REPORESCUE_PATCHES_DIR"] = str(patches_dir)
    if extra_env:
        env.update(extra_env)

    cmd = [str(VENV_PYTHON), str(WORKFLOW_SCRIPT), *args]
    return subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False
    )


def test_workflow_status_command(tmp_path):
    """Verify `status` returns 0 and displays status table in an isolated environment."""
    isolated_reports = tmp_path / "reports"
    isolated_reports.mkdir()
    res = run_cli("status", reports_dir=isolated_reports)
    assert res.returncode == 0
    assert "BUG ID" in res.stdout
    assert "STAGE" in res.stdout


def test_workflow_validate_report_bug_001(tmp_path):
    """Verify `validate-report` generates a Discord-ready Triage Card for BUG-001."""
    isolated_reports = tmp_path / "reports"
    res = run_cli("validate-report", "--bug-id", "BUG-001", reports_dir=isolated_reports)
    assert res.returncode == 0
    assert "[TRIAGE CARD]" in res.stdout
    assert "BUG-001" in res.stdout
    assert "@repo-rescue-reproducer" in res.stdout
    assert len(res.stdout) < 1200


def test_workflow_validate_report_bug_002(tmp_path):
    """Verify `validate-report` generates a Discord-ready Triage Card for BUG-002."""
    isolated_reports = tmp_path / "reports"
    res = run_cli("validate-report", "--bug-id", "BUG-002", reports_dir=isolated_reports)
    assert res.returncode == 0
    assert "[TRIAGE CARD]" in res.stdout
    assert "BUG-002" in res.stdout
    assert "@repo-rescue-reproducer" in res.stdout
    assert len(res.stdout) < 1200


def test_workflow_verify_reproduction_not_reproduced_when_clean(tmp_path):
    """Verify `verify-reproduction` halts gracefully when bug is not seeded in working tree."""
    isolated_reports = tmp_path / "reports"
    res = run_cli("verify-reproduction", "--bug-id", "BUG-001", reports_dir=isolated_reports)
    assert res.returncode == 0
    assert "REPRODUCTION HALTED" in res.stdout or "REPRODUCTION REPORT" in res.stdout
    assert len(res.stdout) < 1200


def test_workflow_record_decision_approve(tmp_path):
    """Verify `record-decision` records approval and emits resolution card."""
    isolated_reports = tmp_path / "reports"
    res = run_cli("record-decision", "--bug-id", "BUG-001", "--decision", "approve", reports_dir=isolated_reports)
    assert res.returncode == 0
    assert "[INCIDENT RESOLVED]" in res.stdout
    assert "BUG-001" in res.stdout
    assert len(res.stdout) < 1200


def test_workflow_record_decision_reject(tmp_path):
    """Verify `record-decision` records rejection and emits rejection card."""
    isolated_reports = tmp_path / "reports"
    res = run_cli("record-decision", "--bug-id", "BUG-001", "--decision", "reject", reports_dir=isolated_reports)
    assert res.returncode == 0
    assert "[PATCH REJECTED" in res.stdout
    assert len(res.stdout) < 1200


def test_workflow_prepare_and_restore_demo_bug_002():
    """Verify prepare-demo and restore-clean for BUG-002."""
    # Seed BUG-002
    res_prep = run_cli("prepare-demo", "--bug-id", "BUG-002")
    assert res_prep.returncode == 0
    assert "Prepared demo: Seeded BUG-002" in res_prep.stdout

    # Restore clean
    res_rst = run_cli("restore-clean", "--bug-id", "BUG-002")
    assert res_rst.returncode == 0
    assert "Restored clean state for BUG-002" in res_rst.stdout


# -----------------------------------------------------------------------------
# Regression Tests: Windows Encoding & Test Isolation
# -----------------------------------------------------------------------------

def test_windows_encoding_safety_ascii_environment(tmp_path):
    """Regression test: verify CLI does not crash with UnicodeEncodeError under ascii encoding."""
    isolated_reports = tmp_path / "reports"
    res = run_cli(
        "validate-report", "--bug-id", "BUG-001",
        reports_dir=isolated_reports,
        extra_env={"PYTHONIOENCODING": "ascii"}
    )
    assert res.returncode == 0
    assert "UnicodeEncodeError" not in res.stderr
    assert "TRIAGE CARD" in res.stdout


def test_test_mode_tags_records(tmp_path):
    """Regression test: verify test-generated records are tagged as test artifacts."""
    isolated_reports = tmp_path / "reports"
    res = run_cli(
        "record-decision", "--bug-id", "BUG-001", "--decision", "approve",
        reports_dir=isolated_reports
    )
    assert res.returncode == 0

    status_file = isolated_reports / "BUG-001_status.json"
    assert status_file.exists()
    data = json.loads(status_file.read_text(encoding="utf-8"))
    assert data.get("test_artifact") is True
    assert data.get("decision", {}).get("actor") == "automated-test-runner"
    assert data.get("decision", {}).get("test_decision") is True


def test_persistent_audit_files_untouched(tmp_path):
    """Regression test: verify that persistent reports/ and patches/ remain untouched by tests."""
    def get_hashes(directory: Path) -> dict:
        hashes = {}
        if directory.exists():
            for p in sorted(directory.glob("*")):
                if p.is_file():
                    hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        return hashes

    reports_dir = PROJECT_ROOT / "reports"
    patches_dir = PROJECT_ROOT / "patches"

    hashes_before = {
        "reports": get_hashes(reports_dir),
        "patches": get_hashes(patches_dir)
    }

    # Run workflow actions directed strictly to tmp_path
    isolated_reports = tmp_path / "reports"
    isolated_patches = tmp_path / "patches"

    run_cli("validate-report", "--bug-id", "BUG-001", reports_dir=isolated_reports, patches_dir=isolated_patches)
    run_cli("record-decision", "--bug-id", "BUG-001", "--decision", "approve", reports_dir=isolated_reports, patches_dir=isolated_patches)
    run_cli("record-decision", "--bug-id", "BUG-001", "--decision", "reject", reports_dir=isolated_reports, patches_dir=isolated_patches)

    hashes_after = {
        "reports": get_hashes(reports_dir),
        "patches": get_hashes(patches_dir)
    }

    # Assert that no file in persistent reports/ or patches/ was modified or created
    assert hashes_before == hashes_after
