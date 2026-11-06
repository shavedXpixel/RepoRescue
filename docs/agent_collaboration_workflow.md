# Switch Agent Collaboration Workflow: RepoRescue

## 1. Overview & System Context

RepoRescue demonstrates an AI-assisted collaborative software debugging and remediation workflow designed for the **Flip the Switch Hackathon 2026** (Track: *Best Business Workflow*).

The infrastructure utilizes:
* **Development Environment:** Antigravity IDE
* **Agent Orchestrator:** Switch Console 0.40.1 (running locally)
* **Agent Provider:** OpenCode (`opencode/beam-free`)
* **Chat Integration:** Discord Server (`RepoRescue Lab`), Channel (`#bug-triage`)
* **Switch Discord Bridge:** `RepoRescue Switch Bot` bridging `#bug-triage` to Switch room `bug-triage`
* **Agent Fleet:** 4 specialized OpenCode agents sharing the local working directory (`C:\Users\Priyansu\OneDrive\Desktop\RepoRescue`):
  1. `repo-rescue` (Triage & Lead Agent)
  2. `repo-rescue-reproducer` (Reproduction Agent)
  3. `repo-rescue-fixer` (Remediation Agent)
  4. `repo-rescue-reviewer` (QA & Gatekeeper Agent)

```
  +-----------------------------------------------------------------------+
  |                        Discord: #bug-triage                           |
  |                       (RepoRescue Lab Server)                         |
  +-----------------------------------+-----------------------------------+
                                      | Bug Report Posted by Developer
                                      v
  +-----------------------------------------------------------------------+
  |                         Switch Console 0.40.1                         |
  |                     (Discord Bridge: RepoRescue Switch Bot)           |
  +-----------------------------------+-----------------------------------+
                                      |
       +------------------------------+------------------------------+
       |                                                             |
       v                                                             v
[1. repo-rescue]                                       [2. repo-rescue-reproducer]
(Triage & Lead, anyone)                                (Reproduction, owner-agents)
* Parses Discord message                               * Runs pytest in .venv
* Correlates fixtures/bug_report_001.json              * Verifies HTTP 500 / KeyError
* Emits Triage Card (<1,200 chars)                     * Emits Report (<1,200 chars)
* Hands off: @repo-rescue-reproducer                   * Hands off: @repo-rescue-fixer
       |                                                             |
       +------------------------------+------------------------------+
                                      |
       +------------------------------+------------------------------+
       |                                                             |
       v                                                             v
[3. repo-rescue-fixer]                                 [4. repo-rescue-reviewer]
(Remediation, owner-agents)                            (Auditor & Gatekeeper, owner-agents)
* Fixes rate lookup in app/service.py                  * Inspects git status -s and git diff
* Exports patches/BUG-001.patch                        * Verifies 13/13 tests pass
* Verifies 13/13 tests pass                            * Emits Review Verdict (PASS)
* Hands off: @repo-rescue-reviewer                     * Pauses for human !approve
       |                                                             |
       +------------------------------+------------------------------+
                                      |
                                      v
                        +---------------------------+
                        |  5. Human Approval Gate   |
                        | (!approve in #bug-triage) |
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
* **Agent:** `repo-rescue` (`addressing: anyone`)
* **Trigger:** An engineer or QA member reports an issue in Discord `#bug-triage`.
* **Switch Coordination:** Switch captures the Discord message via native Discord bridge and routes the event to `repo-rescue`.
* **Agent Responsibilities:**
  1. Parses raw Discord chat messages into structured problem reports.
  2. Identifies affected service (`checkout-service`), endpoints (`POST /checkout`), and parameters (`promo_code="RESCUE20"`).
  3. Validates against the standardized bug report fixture (`fixtures/bug_report_001.json`).
  4. Categorizes severity (`High`) and creates incident tracking ID (`BUG-001`).
  5. Emits a compact Triage Card under 1,200 characters and mentions `@repo-rescue-reproducer`.

### Stage 2: Reproduction (Automated Verification)
* **Agent:** `repo-rescue-reproducer` (`addressing: owner-agents`)
* **Trigger:** Mentioned by `@repo-rescue` in `#bug-triage`.
* **Agent Responsibilities:**
  1. Inspects the test suite (`tests/test_checkout.py`).
  2. Executes reproduction in the project's virtual environment:
     ```powershell
     .\.venv\Scripts\python.exe -m pytest -v -k "reproduce_bug_001"
     .\.venv\Scripts\python.exe -m pytest -v -k "not reproduce_bug_001"
     ```
  3. Confirms that baseline checkout tests pass while the reproducer test triggers the reported failure (`KeyError: 'discount_percent'` / HTTP 500 vs HTTP 200).
  4. Records the exact trace and failure signature **without altering any application code**.
  5. Emits a compact Reproduction Report under 1,200 characters and mentions `@repo-rescue-fixer`.

### Stage 3: Remediation & Patch Staging
* **Agent:** `repo-rescue-fixer` (`addressing: owner-agents`)
* **Trigger:** Mentioned by `@repo-rescue-reproducer`.
* **Agent Responsibilities:**
  1. Analyzes the failure trace back to `app/service.py` in `apply_discount()`.
  2. Resolves the dictionary key mismatch between `ACTIVE_PROMOTIONS` (`rate: 0.20`) and lookup `promo["rate"]`.
  3. Formulates a minimal 1-line patch in `app/service.py`.
  4. Exports the diff to `patches/BUG-001.patch`:
     ```powershell
     git diff app/service.py > patches/BUG-001.patch
     ```
  5. Re-runs the full 13-test suite (`.\.venv\Scripts\python.exe -m pytest -v`) to confirm 13/13 passing tests.
  6. **Guardrail:** The patch is staged locally; **no automatic commit or push is executed**.
  7. Emits a compact Fix Card under 1,200 characters with diff preview and mentions `@repo-rescue-reviewer`.

### Stage 4: Independent QA & Audit
* **Agent:** `repo-rescue-reviewer` (`addressing: owner-agents`)
* **Trigger:** Mentioned by `@repo-rescue-fixer`.
* **Agent Responsibilities:**
  1. Inspects working tree changes via `git status -s` and `git diff app/service.py`.
  2. Validates that **only** `app/service.py` was modified and that no secrets, credentials, or unrelated files were touched.
  3. Runs the complete 13-test suite (`.\.venv\Scripts\python.exe -m pytest -v`) to verify zero regressions.
  4. Emits a structured Review Verdict (`PASS`).
  5. Pauses the workflow and explicitly prompts the human engineer in `#bug-triage` for sign-off:
     > *"Developer, please review the proposed diff above. Reply with `!approve` to authorize commit and close incident BUG-001."*

### Stage 5: Human Approval Gate
* **Mechanism:**
  1. The human developer reviews the patch preview and regression audit posted in Discord `#bug-triage`.
  2. Approval requires explicit human sign-off (`!approve`).
  3. Once approved, the patch can be committed and merged. Automatic merges or unreviewed commits are strictly prohibited.

---

## 3. Deterministic Scenario Seeding CLI (`scripts/bug_scenario.py`)

To allow judges and developers to test the full lifecycle deterministically without manual file editing, `scripts/bug_scenario.py` provides three standard commands:
* `status`: Inspects `app/service.py` and reports whether state is `SEEDED (BUG-001 active)` or `RESOLVED (BUG-001 fixed)`.
* `seed`: Inverts `rate = promo["rate"]` to `rate = promo["discount_percent"]`, making the bug active and causing `test_reproduce_bug_001_checkout_with_rescue20_promo` to fail with HTTP 500.
* `restore`: Replaces `rate = promo["discount_percent"]` with `rate = promo["rate"]`, restoring the codebase to all 13 passing tests.

---

## 4. Current Status & Verified Telemetry

* **Repository Scaffolding & Fix:** Complete. FastAPI service, seeded reproducer test, bug report fixture, 13-test suite, and scenario CLI are fully implemented and verified.
* **Switch Console 0.40.1 Template:** Declaratively defined in `switch/reporescue.template.yaml` and synchronized with `switch/agents/*.md`.
* **Live Discord Verification (Milestones 2 & 3 Complete):** Fully executed and verified in Discord `#bug-triage` on the `RepoRescue Lab` server:
  - `repo-rescue` received human bug report and delegated to `repo-rescue-reproducer`.
  - `repo-rescue-reproducer` autonomously ran pytest in `.venv` (24 tool calls, 3m 20s), isolated HTTP 500, and handed off to `repo-rescue-fixer`.
  - `repo-rescue-fixer` patched `app/service.py`, generated `patches/BUG-001.patch`, confirmed 13/13 tests green (22 tool calls, 3m 25s), and handed off to `repo-rescue-reviewer`.
  - `repo-rescue-reviewer` audited git diff, verified zero regressions (5 tool calls, 55s), issued `Verdict: PASS`, and gated human maintainer sign-off (`!approve`).
  - Human maintainer sign-off received; incident triage successfully resolved. Live screenshots archived in `docs/screenshots/`.
