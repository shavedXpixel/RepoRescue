# Switch Agent Collaboration Workflow: RepoRescue

## 1. Overview & System Context

RepoRescue demonstrates an AI-assisted software debugging and remediation workflow designed for the **Flip the Switch Hackathon 2026**.

The infrastructure utilizes:
* **Development Environment:** Antigravity IDE
* **Agent Orchestrator:** Switch Console (running locally)
* **Agent Provider:** OpenCode
* **Chat Integration:** Discord Server (`RepoRescue Lab`), Channel (`#bug-triage`)
* **Switch Agent:** `repo-rescue`

```
  +--------------------------------------------------------------+
  |                   Discord: #bug-triage                       |
  |                (RepoRescue Lab Server)                       |
  +------------------------------+-------------------------------+
                                 | Bug Report Posted
                                 v
  +--------------------------------------------------------------+
  |                        Switch Console                        |
  |             (Agent Orchestrator & OpenCode Provider)         |
  +------------------------------+-------------------------------+
                                 |
         +-----------------------+-----------------------+
         |                       |                       |
         v                       v                       v
  [1. Triage Agent]   [2. Reproduction Agent]  [3. Fix Proposal Agent]
         |                       |                       |
         +-----------------------+-----------------------+
                                 |
                                 v
                      [4. Review Agent]
                                 |
                                 v
                   +---------------------------+
                   |  5. Human Approval Gate   |
                   | (Discord / Switch Prompt) |
                   +-------------+-------------+
                                 |
                    [Approved] --+-- [Rejected]
                                 |
                                 v
                        [Apply & Commit]
```

---

## 2. Agent Roles & Collaboration Lifecycle

The workflow consists of five disciplined stages. Each stage has strict inputs, boundaries, and validation criteria:

### Stage 1: Triage (Ingestion & Normalization)
* **Source:** A team member or QA engineer reports an issue in Discord `#bug-triage`.
* **Switch Coordination:** Switch captures the Discord message (via native Switch-Discord integration; no custom bot required) and routes the event to the `repo-rescue` agent.
* **Agent Responsibility:**
  1. Parses raw Discord chat messages into structured problem reports.
  2. Identifies affected service (`checkout-service`), endpoints (`POST /checkout`), and parameters (`promo_code="RESCUE20"`).
  3. Validates against or produces a standardized bug report fixture (see `fixtures/bug_report_001.json`).
  4. Categorizes severity and creates an incident tracking ID (`BUG-001`).

### Stage 2: Reproduction (Automated Verification)
* **Agent Responsibility:**
  1. Inspects the test suite (`tests/test_checkout.py`).
  2. Formulates or verifies an automated reproducer test: `test_reproduce_bug_001_checkout_with_rescue20_promo`.
  3. Executes the test suite in the virtual environment.
  4. Confirms that normal tests pass while the reproducer test triggers the reported failure (HTTP 500 / `KeyError: 'discount_percent'`).
  5. Records the trace and failure signature without altering application code.

### Stage 3: Fix Proposal (Root Cause & Minimal Diff)
* **Agent Responsibility:**
  1. Analyzes the failure trace back to `app/service.py` in `apply_discount()`.
  2. Identifies the dictionary schema mismatch between `ACTIVE_PROMOTIONS` (`rate: 0.20`) and the lookup `promo['discount_percent']`.
  3. Drafts a minimal, clean patch that resolves the issue safely (e.g., aligning the rate calculation).
  4. Formulates a localized git diff without modifying unrelated lines.
  5. **Constraint:** The fix is staged in memory / patch preview; **no automatic commit or push is executed**.

### Stage 4: Review & Audit (Regression Testing)
* **Agent Responsibility:**
  1. Applies the proposed patch in a test sandbox.
  2. Re-runs the entire test suite (`pytest -v`).
  3. Verifies that `test_reproduce_bug_001_checkout_with_rescue20_promo` transitions from **FAILED** to **PASSED**.
  4. Confirms zero regressions across standard checkout and promotion tests.
  5. Prepares an audit report summarizing root cause, proposed fix, and test verification evidence.

### Stage 5: Human Approval (Strict Quality Gate)
* **Mechanism:**
  1. Switch transmits the review report and proposed diff back to Discord `#bug-triage` and the Switch Console.
  2. A human maintainer or judge reviews the diff, the reproducer output, and regression test results.
  3. Approval requires explicit human sign-off (`!approve` or console confirmation).
  4. Once approved, the change is committed. Automatic merges or deployments are strictly prohibited.

---

## 3. Transparency & Current Status

* **Milestone 1 Deliverable:** The reproducible demo repository, FastAPI checkout service, seeded bug (`BUG-001`), automated reproducer test, bug report fixture, and PowerShell test commands are fully implemented and verified locally.
* **Agent Coordination Status:** The workflow above represents the design specification for Switch agent orchestration. Real agent-to-agent coordination via Switch and OpenCode will be executed and verified in Milestone 2.
