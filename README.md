# RepoRescue

> **Flip the Switch Hackathon 2026 Submission**  
> **Track:** Best Business Workflow  
> **Tagline:** Autonomous AI-assisted multi-agent software debugging and remediation where developers and 4 specialized OpenCode agents triage, reproduce, patch, independently audit, and human-approve production bug fixes directly inside Discord via Switch Console 0.40.1.

---

## 1. Project Overview

**RepoRescue** transforms software incident management from an error-prone, manual scramble into an automated, auditable, multi-agent workflow. When a production bug is reported in Discord (`#bug-triage` in the `RepoRescue Lab` server), Switch Console 0.40.1 orchestrates a four-agent team powered by **OpenCode** (`opencode/beam-free`) operating on the local repository (`C:\Users\Priyansu\OneDrive\Desktop\RepoRescue`).

The agents autonomously triage the incident, execute targeted reproduction tests in a local Python virtual environment, generate a minimal patch, audit the diff against regressions and secret leaks, and pause for explicit human maintainer sign-off (`!approve <BUG_ID>`) before any Git commit.

---

## 2. Problem Statement

When production software breaks, engineering teams face significant operational friction:
* **Context-Switching Bottlenecks:** Engineers waste critical time jumping between Discord alerts, terminal windows, complex test suites, and Git branches.
* **Flaky & Hallucinated Fixes:** Generic conversational AI bots often propose fixes that look plausible but fail real test suites or introduce unintended regressions.
* **Unsafe Hotfixes:** Rushed emergency patches pushed directly to production bypass code review and quality gates, leading to secondary outages.
* **Chat Notification Spam:** Without strict multi-agent coordination policies, automated bots trigger broadcast storms and conversational deadlocks in incident channels.

---

## 3. Proposed Solution

RepoRescue solves these challenges through a disciplined, human-governed multi-agent pipeline:
1. **Chat-Native Intake:** Team members report bugs in their existing Discord workflow.
2. **Specialized Division of Labor:** Four distinct OpenCode agents handle Triage, Reproduction, Remediation, and Review respectively.
3. **Real Virtual Environment Verification:** No fix is proposed without executing real Pytest suites inside `.venv`.
4. **Structured Audit Trail:** All test traces, diffs, and verdicts are saved to `patches/<BUG_ID>.patch` and `reports/<BUG_ID>_status.json`.
5. **Mandatory Human-in-the-Loop Gate:** The reviewer agent issues a formal `PASS` verdict and halts the pipeline until a human developer inspects the diff and replies `!approve`.

---

## 4. Technology Stack

* **Operating System & Shell:** Windows 11 / PowerShell 5.1+ / PowerShell 7+
* **Development Environment:** Google Antigravity IDE
* **Target Application:** Python 3.12, FastAPI, Pydantic v2, Uvicorn, HTTPX / Starlette TestClient
* **Test Suite:** Pytest 9.2 (20 automated unit, endpoint, and workflow CLI tests)
* **Agent Orchestrator:** Switch Console 0.40.1 (Local Daemon + Discord Gateway Bridge)
* **Agent Provider:** OpenCode (`opencode/beam-free`)
* **Chat & Incident Room:** Discord Server (`RepoRescue Lab`), Channel (`#bug-triage`)
* **Version Control & Artifact Staging:** Git, GitHub (`shavedXpixel/RepoRescue`), unified `.patch` staging

---

## 5. System Architecture & Diagram

```
+-------------------------------------------------------------------------------------------------+
|                                     DISCORD: #bug-triage                                        |
|                                   (RepoRescue Lab Server)                                       |
+-----------------------------------------------+-------------------------------------------------+
                                                |
               Developer posts bug report       |       Developer replies: !approve <BUG_ID>
                                                v                                 ^
+---------------------------------------------------------------------------------+---------------+
|                                    SWITCH CONSOLE 0.40.1                                        |
|                          (Discord Gateway Bridge: RepoRescue Switch Bot)                        |
|                               Shared Room: bug-triage                                           |
+-----------------------------------------------+-------------------------------------------------+
                                                |
        +---------------------------------------+---------------------------------------+
        |                                                                               |
        v                                                                               v
[1. repo-rescue]                                                  [2. repo-rescue-reproducer]
(Triage & Lead, addressing: anyone)                               (Reproduction, addressing: owner-agents)
* Parses incoming bug report                                      * Runs pytest in local .venv
* Correlates fixtures/<BUG_ID>.json                               * Confirms failure signature (or halts)
* Posts Triage Card (<1,200 chars)                                * Posts Reproduction Report (<1,200 chars)
* Hands off: @repo-rescue-reproducer                              * Hands off: @repo-rescue-fixer
        |                                                                               |
        +---------------------------------------+---------------------------------------+
                                                |
        +---------------------------------------+---------------------------------------+
        |                                                                               |
        v                                                                               v
[3. repo-rescue-fixer]                                            [4. repo-rescue-reviewer]
(Remediation, addressing: owner-agents)                           (QA Gatekeeper, addressing: owner-agents)
* Implements minimal code fix in app/service.py                   * Independently inspects git status & diff
* Exports patches/<BUG_ID>.patch                                  * Runs full 20-test pytest suite in .venv
* Validates tests pass in .venv                                   * Validates zero secret leaks or extra edits
* Posts Fix Proposal Card (<1,200 chars)                          * Posts Review Verdict Card (PASS)
* Hands off: @repo-rescue-reviewer                                * Pauses pipeline for human !approve
        |                                                                               |
        +---------------------------------------+---------------------------------------+
                                                |
                                                v
                                 +------------------------------+
                                 |    HUMAN APPROVAL GATE       |
                                 |  Developer replies !approve  |
                                 +--------------+---------------+
                                                |
                                                v
                                  [Incident Marked RESOLVED]
                                  [Maintainer Commits to Main]
```

---

## 6. The Four Switch Agents & Responsibilities

| Agent Name | Role | Switch Addressing | File Permissions | Verified Responsibilities & Live Telemetry |
|---|---|---|---|---|
| **`repo-rescue`** | **Triage & Lead Orchestrator** | `addressing: anyone` | Read-only | Listens to all Discord messages in `#bug-triage`. Ingests bug reports, validates fixtures, issues `[TRIAGE CARD]`, delegates to reproducer. On `!approve`, marks incident `RESOLVED`. |
| **`repo-rescue-reproducer`** | **Investigation & Reproduction** | `addressing: owner-agents` | Read-only | Triggered ONLY by `@-mention`. Runs `pytest` in `.venv`. Never alters code. **Verified live telemetry:** 24 tool calls, 3m 20s. Isolated HTTP 500 `KeyError: 'discount_percent'`. |
| **`repo-rescue-fixer`** | **Root-Cause Remediation** | `addressing: owner-agents` | Write-scoped to `app/service.py` & `patches/` | Triggered ONLY by `@-mention`. Fixes bug, exports unified diff to `patches/<BUG_ID>.patch`, verifies full test suite passes. Never runs `git commit`. **Verified live telemetry:** 22 tool calls, 3m 25s. |
| **`repo-rescue-reviewer`** | **Independent QA Gatekeeper** | `addressing: owner-agents` | Read-only | Triggered ONLY by `@-mention`. Independently audits `git status`, diff, and runs `pytest` in `.venv`. Verifies zero secret leaks. Issues `Verdict: PASS` and gates on human `!approve`. **Verified live telemetry:** 5 tool calls, 55s. |

---

## 7. Why Switch Is Central to RepoRescue

Switch Console 0.40.1 is the indispensable foundation of RepoRescue:
1. **Native Chat Bridging Without Custom Bot Servers:** Switch natively bridges Discord `#bug-triage` into local agent rooms via `RepoRescue Switch Bot`, eliminating the need to maintain external bot servers, webhooks, or websocket daemons.
2. **"Me and my agents" (`owner-agents`) Addressing Architecture:** Switch's addressing policy allows `repo-rescue` to listen to anyone while keeping the three specialist agents quiet until explicitly `@-mentioned`. This allows autonomous multi-agent handoffs while preventing broadcast loops and chat noise.
3. **Bridging Cloud LLMs to Local Sandboxes:** Switch connects OpenCode (`opencode/beam-free`) cloud models directly to our local Windows virtual environment, allowing agents to execute real `pytest` commands, inspect Git diffs, and write patch files.
4. **Discord Reliability Contract:** By enforcing `<1,200 characters` per message and `<15 lines` per code block, RepoRescue avoids Discord's 2,000-character payload rejection limit and produces clean, human-readable status cards.

---

## 8. Installation Instructions for Windows (PowerShell)

### Prerequisites
* Windows 10/11
* Python 3.10+ (tested on Python 3.12)
* PowerShell 5.1+ or PowerShell 7+
* Git installed and on PATH

### Step-by-Step Setup
```powershell
# 1. Clone repository
git clone https://github.com/shavedXpixel/RepoRescue.git
cd RepoRescue

# 2. Create Python virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install pinned dependencies
pip install -r requirements.txt
```

---

## 9. Running the FastAPI Backend

Start the local checkout development server:
```powershell
uvicorn app.main:app --reload --port 8000
```

Verify service endpoints in a separate PowerShell terminal:
```powershell
# Health check
Invoke-RestMethod -Uri http://localhost:8000/health

# Available promotions
Invoke-RestMethod -Uri http://localhost:8000/promotions
```

Interactive Swagger documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 10. Running the Test Suite

Run the full automated test suite (all 20 tests):
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

**Test Coverage Summary (20 Passed, 0 Failed in ~1.8s):**
* **13 Checkout Service Tests (`tests/test_checkout.py`):**
  * `test_health_endpoint`: Verifies `/health` returns 200 OK.
  * `test_checkout_standard_order_success`: Verifies standard checkout without promo codes.
  * `test_checkout_with_valid_fixed_discount_promo`: Verifies `SAVE10` fixed promo discount and post-discount tax math ($11.20 tax on $140.00).
  * `test_checkout_with_invalid_promo_code_returns_400`: Verifies 400 Bad Request on unknown promo codes.
  * `test_checkout_validation_empty_items_returns_422`: Verifies Pydantic 422 Unprocessable Entity on empty carts.
  * `test_reproduce_bug_001_checkout_with_rescue20_promo`: Dedicated reproducer test for percentage discount `RESCUE20`.
  * `test_apply_discount_*`: 7 focused unit tests verifying exact 20% discount math, whitespace insensitivity, boundary rates (`rate = 0.0` and `rate = 1.0`), and zero subtotal.
* **7 Workflow CLI & Audit Tests (`tests/test_workflow_cli.py`):**
  * `test_workflow_status_command`: Verifies status table formatting.
  * `test_workflow_validate_report_bug_001`: Verifies Triage Card generation for `BUG-001`.
  * `test_workflow_validate_report_bug_002`: Verifies Triage Card generation for `BUG-002`.
  * `test_workflow_verify_reproduction_not_reproduced_when_clean`: Verifies graceful halting when bugs are not active.
  * `test_workflow_record_decision_approve`: Verifies human approval card and status transition.
  * `test_workflow_record_decision_reject`: Verifies human rejection card and status transition.
  * `test_workflow_prepare_and_restore_demo_bug_002`: Verifies deterministic demo seeding and clean restoration for `BUG-002`.

---

## 11. Running the Multi-Agent Demonstration (`BUG-001` & `BUG-002`)

### Option A: Live Discord Multi-Agent Flow (`#bug-triage`)
1. In Switch Console 0.40.1, verify the 4 agents (`repo-rescue`, `repo-rescue-reproducer`, `repo-rescue-fixer`, `repo-rescue-reviewer`) are online and joined to `#bug-triage`.
2. Seed the desired demo bug:
   ```powershell
   # Seed BUG-001 (Percentage discount key lookup error):
   .\.venv\Scripts\python.exe scripts/bug_scenario.py seed BUG-001

   # OR Seed BUG-002 (Pre-discount sales tax math error):
   .\.venv\Scripts\python.exe scripts/bug_scenario.py seed BUG-002
   ```
3. In Discord `#bug-triage`, post the incident report:
   > *"Customers are getting HTTP 500 errors on POST /checkout when applying promo code RESCUE20. Please investigate."*
   *(or for `BUG-002`: "Customer reported overcharged sales tax when using promo code SAVE10. Please investigate.")*
4. Watch the autonomous handoff sequence:
   * `@repo-rescue` triages and mentions `@repo-rescue-reproducer`.
   * `@repo-rescue-reproducer` runs `pytest`, captures failure trace, and mentions `@repo-rescue-fixer`.
   * `@repo-rescue-fixer` applies minimal fix, writes `patches/<BUG_ID>.patch`, verifies tests, and mentions `@repo-rescue-reviewer`.
   * `@repo-rescue-reviewer` audits diff, verifies tests, issues `Verdict: PASS`, and prompts developer.
5. In Discord, reply:
   `@repo-rescue !approve BUG-001`
6. `@repo-rescue` validates test status and issues the final `[INCIDENT RESOLVED]` closure card.
7. Restore working tree:
   ```powershell
   .\.venv\Scripts\python.exe scripts/bug_scenario.py restore --all
   ```

### Option B: Deterministic Local CLI Pipeline (`scripts/rescue_workflow.py`)
Both developers and AI agents can execute the exact same pipeline locally:
```powershell
# 1. Triage bug report:
.\.venv\Scripts\python.exe scripts/rescue_workflow.py validate-report --bug-id BUG-001

# 2. Verify reproduction:
.\.venv\Scripts\python.exe scripts/rescue_workflow.py verify-reproduction --bug-id BUG-001

# 3. Stage patch and verify tests:
.\.venv\Scripts\python.exe scripts/rescue_workflow.py stage-patch --bug-id BUG-001

# 4. Independent QA audit:
.\.venv\Scripts\python.exe scripts/rescue_workflow.py audit-patch --bug-id BUG-001

# 5. Record human approval decision:
.\.venv\Scripts\python.exe scripts/rescue_workflow.py record-decision --bug-id BUG-001 --decision approve

# 6. View full audit table:
.\.venv\Scripts\python.exe scripts/rescue_workflow.py status
```

---

## 12. Example Bug Reports & Verified Evidence

### Bug Scenarios Catalog
* **`BUG-001` ([`fixtures/bug_report_001.json`](fixtures/bug_report_001.json)):**
  * **Symptom:** HTTP 500 on checkout with `promo_code="RESCUE20"`.
  * **Root Cause:** In `app/service.py`, `apply_discount()` accesses `promo["discount_percent"]` instead of `promo["rate"]`.
  * **Fix:** `rate = promo["rate"]` (Unified diff: [`patches/BUG-001.patch`](patches/BUG-001.patch)).
  * **Verification Status:** **Verified Live in Switch Console & Discord `#bug-triage`** (51 total tool calls, live screenshots in `docs/screenshots/`).
* **`BUG-002` ([`fixtures/bug_report_002.json`](fixtures/bug_report_002.json)):**
  * **Symptom:** Overcharged sales tax ($12.00 instead of $11.20) when using fixed discount promo `SAVE10`.
  * **Root Cause:** In `app/service.py`, `taxable_amount = subtotal` instead of `max(0.0, subtotal - discount)`.
  * **Fix:** `taxable_amount = max(0.0, subtotal - discount)` (Unified diff: [`patches/BUG-002.patch`](patches/BUG-002.patch)).
  * **Verification Status:** **Tested & Verified Locally via Pytest & CLI** (Full audit artifact: [`reports/BUG-002_status.json`](reports/BUG-002_status.json)).

### Live Discord Run Evidence
Screenshots from the live multi-agent execution in Discord `#bug-triage` are archived in:
* [`docs/screenshots/discord_handoff_1.png`](docs/screenshots/discord_handoff_1.png) — Reproducer report confirming `KeyError` failure and Fixer proposal card.
* [`docs/screenshots/discord_handoff_2.png`](docs/screenshots/discord_handoff_2.png) — Reviewer audit verdict (`PASS`) and human approval prompt.
* [`docs/screenshots/switch.png`](docs/screenshots/switch.png) — Switch Console 0.40.1 room overview showing the 4 connected OpenCode agents.

---

## 13. Security, Git Hygiene & Human Approval Safeguards

RepoRescue enforces enterprise-grade safety guardrails at every step:
1. **Read-Only Permission Isolation:**
   * `repo-rescue`, `repo-rescue-reproducer`, and `repo-rescue-reviewer` operate in strictly read-only mode.
   * Only `repo-rescue-fixer` has write permission, and its scope is strictly restricted to `app/service.py` and `patches/`.
2. **Uncommitted Patch Staging:**
   * Proposed diffs are exported to `patches/<BUG_ID>.patch`. Agents are strictly prohibited from executing `git commit` or `git push`.
3. **Secret Leak Prevention:**
   * The reviewer agent audits `git status --porcelain` to ensure `.env`, `.pem`, `.key`, or credentials are never staged or touched.
4. **Mandatory Human-in-the-Loop Sign-Off:**
   * An incident cannot be marked `RESOLVED` without explicit human authorization (`!approve <BUG_ID>`).
   * The human maintainer retains full control over final `git commit` and deployment decisions.
