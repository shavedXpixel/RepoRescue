# RepoRescue

> **Flip the Switch Hackathon 2026 Submission**  
> **Track:** Best Business Workflow  
> **Tagline:** AI-assisted collaborative software debugging where developers and 4 specialized OpenCode agents triage, reproduce, patch, review, and approve fixes directly in Discord via Switch Console 0.40.1.

---

## 1. Project Overview

**RepoRescue** transforms software incident management from an error-prone, manual scramble into an automated, auditable, multi-agent workflow:
1. **Incident Intake in Discord:** An engineer or QA tester posts an issue in Discord (`#bug-triage` in the `RepoRescue Lab` server).
2. **Switch Multi-Agent Coordination:** Switch Console 0.40.1 orchestrates 4 specialized **OpenCode** (`opencode/beam-free`) agents running against the local repository (`C:\Users\Priyansu\OneDrive\Desktop\RepoRescue`).
3. **Automated Reproduction:** The reproducer agent isolates the failure using `pytest` without modifying application code.
4. **Remediation & Patch Staging:** The fixer agent applies the minimal 1-line fix, exports `patches/BUG-001.patch`, and validates that all 13 tests pass without committing to Git.
5. **Independent QA & Human Gate:** The reviewer agent audits git diffs, verifies zero regressions, issues a `PASS` verdict, and pauses for human maintainer authorization (`!approve`) before changes are committed.

---

## 2. How We Used Switch (Judges' Submission Checklist)

> *"A README that explains how you used Switch: which agents you connected, how the channel is set up, and how to run it."* — Hackathon Checklist

### A. Which Agents We Connected
Switch Console connects 4 specialized **OpenCode** (`opencode/beam-free`) agents running locally on Windows PowerShell. Each agent has strict permission boundaries and verified telemetry from our live Discord `#bug-triage` runs:

| Agent Name | Role | Switch Addressing | Scope & Permissions | Verified Live Telemetry (Discord `#bug-triage`) |
|---|---|---|---|---|
| `repo-rescue` | **Triage & Lead** | `addressing: anyone` | **Read-only.** Ingests user reports, validates fixtures, issues `[TRIAGE CARD]`, hands off to reproducer. In Mode B, finalizes incident on `!approve`. | **Initial response:** ~15s. Formulated compact triage card; delegated to `@repo-rescue-reproducer`. |
| `repo-rescue-reproducer` | **Reproduction** | `addressing: owner-agents` | **Read-only.** Runs `pytest` in `.venv`. Never modifies or commits files. | **24 tool calls, 3m 20s.** Isolated HTTP 500 (`KeyError: 'discount_percent'`), verified 12 baseline tests passed. Handed off to `@repo-rescue-fixer`. |
| `repo-rescue-fixer` | **Remediation** | `addressing: owner-agents` | **Code Fixer.** Scoped strictly to `app/service.py` and `patches/BUG-001.patch`. Never runs `git commit` or `git push`. | **22 tool calls, 3m 25s.** Replaced key lookup in `app/service.py`, exported `patches/BUG-001.patch`, confirmed 13/13 tests green. Handed off to `@repo-rescue-reviewer`. |
| `repo-rescue-reviewer` | **QA & Gatekeeper** | `addressing: owner-agents` | **Read-only Auditor.** Inspects `git status -s` and `git diff`, re-tests `.venv`, gates human approval. | **5 tool calls, 55s.** Confirmed clean 1-line diff, 13/13 tests passed, issued `Verdict: PASS`, and requested developer `!approve`. |

### B. How the Discord Channel & Switch Room Are Set Up
* **Discord Server:** `RepoRescue Lab`
* **Discord Channel:** `#bug-triage`
* **Switch Discord Gateway Bridge:** `RepoRescue Switch Bot` bridges `#bug-triage` to Switch room `bug-triage`.
* **Autonomous Handoff Architecture ("Me and my agents"):**
  * `repo-rescue` uses `addressing: anyone` so it responds to human team members reporting bugs in Discord.
  * `repo-rescue-reproducer`, `repo-rescue-fixer`, and `repo-rescue-reviewer` use `addressing: owner-agents` ("Me and my agents" in Switch Console). They only activate when explicitly `@-mentioned` by peer agents in the handoff chain. This prevents crosstalk, race conditions, and infinite conversation loops.
* **Discord Message Contract:** Each agent prompt enforces a **strict < 1,200 character total message limit** and code blocks under 15 lines. This completely avoids Discord API payload rejections (`switch_post_message` truncation) and produces readable cards.
* **Declarative Template:** Defined in [`switch/reporescue.template.yaml`](switch/reporescue.template.yaml) following Switch Console 0.40.1 list schema (`version: 1`, `params:`, `agents:` as `- name: ...`, `room:`).

---

## 3. Verified Live Telemetry & Transcript Summary

During live testing in Discord `#bug-triage`, the 4 agents autonomously completed the incident debugging cycle across 51 tool calls:

### 1. Reproducer Report (Posted by `@repo-rescue-reproducer`)
```markdown
🔬 **[REPRODUCTION REPORT] Bug Confirmed**
• **Target Test:** tests/test_checkout.py::test_reproduce_bug_001_checkout_with_rescue20_promo
• **Result:** FAILED (HTTP 500 Internal Server Error)
• **Trace Signature:** KeyError: 'discount_percent' in app/service.py:apply_discount
• **Baseline Tests:** 12 passed (normal checkout unaffected)
• **Reproducibility:** 100% deterministic

Handoff: @repo-rescue-fixer please inspect app/service.py and generate a minimal fix for rate key lookup.
```

### 2. Fix Proposal (Posted by `@repo-rescue-fixer`)
```markdown
🛠️ **[FIX PROPOSAL] Patch Generated**
• **File Modified:** app/service.py
• **Patch File:** patches/BUG-001.patch
• **Diff Summary:**
```diff
- rate = promo["discount_percent"]
+ rate = promo["rate"]
```
• **Test Verification:** 13/13 passed (0 regressions)
• **Git Status:** Working tree modified (uncommitted)

Handoff: @repo-rescue-reviewer please review the patch and audit for human approval.
```

### 3. Review Verdict & Human Gate (Posted by `@repo-rescue-reviewer`)
```markdown
⚖️ **[REVIEW VERDICT] Audit Complete**
• **Verdict:** PASS
• **Scope:** app/service.py (1 line changed, minimal diff)
• **Test Suite:** 13/13 passed in .venv
• **Regression Check:** All standard checkout & promotion tests green
• **Safety Check:** No credentials, secrets, or unrelated files modified

🧑‍💻 **HUMAN APPROVAL REQUIRED:**
Developer, please review the proposed diff above. Reply with `!approve` to authorize commit and close incident BUG-001.
```

*(Live run screenshots captured in `docs/screenshots/discord_handoff_1.png` and `docs/screenshots/discord_handoff_2.png`)*

---

## 4. The Target Checkout Service & Seeded Bug (`BUG-001`)

The repository includes a lightweight, production-grade **FastAPI Checkout Service**:
* **Endpoint:** `POST /checkout`
* **Seeded Bug:** Request with promotional code `promo_code="RESCUE20"`.
* **Root Cause:** In `app/service.py`, `ACTIVE_PROMOTIONS` defines percentage discounts with `"rate": 0.20`. Unpatched code attempted `rate = promo["discount_percent"]`, causing an unhandled `KeyError` resulting in **HTTP 500 Internal Server Error**.
* **Bug Report Fixture:** See [`fixtures/bug_report_001.json`](fixtures/bug_report_001.json).
* **Target Reproducer Test:** `tests/test_checkout.py::test_reproduce_bug_001_checkout_with_rescue20_promo`.

---

## 5. How to Run It (Step-by-Step PowerShell Guide)

### Prerequisites
* Windows 10/11
* Python 3.10+ (tested on Python 3.12)
* PowerShell 5.1+ or PowerShell 7+
* Switch Console 0.40.1 (configured with OpenCode and Discord)

### Step 1: Navigate to Workspace
```powershell
cd C:\Users\Priyansu\OneDrive\Desktop\RepoRescue
```

### Step 2: Setup Virtual Environment & Dependencies
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt
```

### Step 3: Run the Complete Test Suite
Run the 13-test suite to confirm baseline green health:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
**Expected Output:** `13 passed, 1 warning in ~0.05s`
* 5 standard checkout behavior tests
* 1 reproducer test
* 7 focused unit tests for `apply_discount` and boundary rates (0% and 100%)

### Step 4: Deterministic Bug Seeding & Reset CLI
We provide `scripts/bug_scenario.py` using Python standard library modules so judges can deterministically seed and reset `BUG-001`:

```powershell
# 1. Check current status:
.\.venv\Scripts\python.exe scripts/bug_scenario.py status

# 2. Seed the bug (activates BUG-001 in app/service.py):
.\.venv\Scripts\python.exe scripts/bug_scenario.py seed

# 3. Verify that the reproducer test fails with HTTP 500 when seeded:
.\.venv\Scripts\python.exe -m pytest -v -k "reproduce_bug_001"

# 4. Restore back to the resolved state:
.\.venv\Scripts\python.exe scripts/bug_scenario.py restore

# 5. Confirm all 13 tests pass again:
.\.venv\Scripts\python.exe -m pytest -v
```

### Step 5: Triggering the Multi-Agent Chain in Discord `#bug-triage`
1. Launch Switch Console 0.40.1 and apply [`switch/reporescue.template.yaml`](switch/reporescue.template.yaml).
2. Seed the bug via `.\.venv\Scripts\python.exe scripts/bug_scenario.py seed`.
3. In Discord `#bug-triage`, report the bug:
   > *"Customers are getting HTTP 500 errors on POST /checkout when applying promo code RESCUE20. Please investigate."*
4. Observe the autonomous handoff:
   - `@repo-rescue` triages and mentions `@repo-rescue-reproducer`.
   - `@repo-rescue-reproducer` runs pytest, captures HTTP 500, and mentions `@repo-rescue-fixer`.
   - `@repo-rescue-fixer` patches `app/service.py`, writes `patches/BUG-001.patch`, verifies 13/13 passing tests, and mentions `@repo-rescue-reviewer`.
   - `@repo-rescue-reviewer` audits git diff, confirms tests pass, issues `Verdict: PASS`, and prompts the developer for approval.
5. In Discord, reply: `@repo-rescue !approve`.
6. `@repo-rescue` validates test status and issues the final `[INCIDENT RESOLVED]` closure card.

---

## 6. Project Structure

```
RepoRescue/
├── .gitignore                          # Ignores .venv, caches, and patches/*.patch
├── README.md                           # Submission guide for judges
├── requirements.txt                    # FastAPI, pytest, uvicorn, pydantic, httpx
├── app/
│   ├── __init__.py                     # Module initializer
│   ├── main.py                         # FastAPI routes: GET /health, POST /checkout
│   ├── models.py                       # Pydantic schemas
│   └── service.py                      # Checkout & promo calculation business logic
├── docs/
│   ├── agent_collaboration_workflow.md # Multi-agent specification & state machine
│   └── screenshots/                    # Live Discord run evidence
│       ├── discord_handoff_1.png
│       └── discord_handoff_2.png
├── fixtures/
│   └── bug_report_001.json             # Seeded bug report fixture
├── patches/
│   ├── .gitkeep                        # Dedicated staging directory for fixer patches
│   └── BUG-001.patch                   # Unified diff generated by live fixer agent
├── scripts/
│   └── bug_scenario.py                 # CLI controller (status, seed, restore)
├── switch/
│   ├── reporescue.template.yaml        # Switch Console 0.40.1 declarative template
│   └── agents/
│       ├── 01_repo_rescue_triage.md    # System prompt for repo-rescue
│       ├── 02_repo_rescue_reproducer.md# System prompt for repo-rescue-reproducer
│       ├── 03_repo_rescue_fixer.md     # System prompt for repo-rescue-fixer
│       └── 04_repo_rescue_reviewer.md  # System prompt for repo-rescue-reviewer
└── tests/
    ├── __init__.py                     # Test package initializer
    ├── conftest.py                     # TestClient and sample payloads
    └── test_checkout.py                # 13 tests (5 standard, 1 reproducer, 7 unit)
```

---

## 7. Strict Hackathon Guardrails

* **No Separate Discord Bot:** Switch Console natively manages the Discord bridge (`RepoRescue Switch Bot`).
* **No Automatic Merges or Deploys:** Proposed patches are saved to `patches/` and tested; human sign-off (`!approve`) is required before any commit.
* **Documentation & Telemetry Integrity:** All tool counts, execution times, diffs, and test outputs reflect actual verified runs on the local Windows environment.
