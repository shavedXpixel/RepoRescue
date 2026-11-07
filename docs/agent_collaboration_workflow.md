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
  1. `repo-rescue` (Triage & Lead Orchestrator)
  2. `repo-rescue-reproducer` (Investigation & Reproduction Agent)
  3. `repo-rescue-fixer` (Remediation & Patch Staging Agent)
  4. `repo-rescue-reviewer` (Independent QA & Gatekeeper Agent)

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
* Ingests bug report for any <BUG_ID>                  * Runs pytest in .venv via CLI
* Correlates fixtures/<BUG_ID>.json                    * Read/test-only access to workspace
* Posts Triage Card (<1,200 chars)                     * Verifies failure trace (or halts)
* Hands off: @repo-rescue-reproducer                   * Hands off: @repo-rescue-fixer
       |                                                             |
       +------------------------------+------------------------------+
                                      |
       +------------------------------+------------------------------+
       |                                                             |
       v                                                             v
[3. repo-rescue-fixer]                                 [4. repo-rescue-reviewer]
(Remediation, owner-agents)                            (Auditor & Gatekeeper, owner-agents)
* Modifies code ONLY in demo workspace                 * Strictly read-only auditor
* Fixes targeted code in app/service.py                * Inspects git status -s and git diff
* Exports patches/<BUG_ID>.patch                       * Audits EXACT supplied <BUG_ID>
* Verifies full test suite passes                      * Emits Review Verdict (PASS)
* Hands off: @repo-rescue-reviewer                     * Pauses for human !approve <BUG_ID>
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

## 2. Agent Roles, Communication & Collaboration Lifecycle

The workflow consists of five disciplined stages. Each stage has strict inputs, boundaries, workspace isolation rules, and validation criteria:

### Dispatch & Communication Protocol (Switch Discord Bridge)
* In Switch Discord bridged channels, all agent-to-agent dispatches MUST use `switch_post_message` in the connected room with explicit `@agent-name` mentions.
* Agents must NOT invoke `switch_send_targeted_message` without an active direct session (which returns HTTP 400: Not connected to a room).
* If any tool call or dispatch fails, agents must report the error honestly to the room rather than failing silently or fabricating handoffs.

### Strict Workspace Isolation Rules
1. **Protected Main Repository:** The primary repository worktree (`C:\Users\Priyansu\OneDrive\Desktop\RepoRescue`) is protected. During a demo, agents must never modify the main repo worktree.
2. **Explicit Workspace Passing:** The target workspace path is explicitly passed from triage through reviewer.
3. **Reproducer Access:** Read/test-only access in the supplied workspace. Never alters source code.
4. **Fixer Access:** Authorized to modify code files ONLY within the explicitly supplied demo workspace. Never treats the demo workspace as read-only.
5. **Reviewer Access:** Strictly read-only auditor. Never modifies, commits, or pushes files.

---

### Stage 1: Triage (Ingestion & Normalization)
* **Agent:** `repo-rescue` (`addressing: anyone`)
* **Trigger:** An engineer or QA member reports an issue in Discord `#bug-triage`.
* **Switch Coordination:** Switch captures the Discord message via native Discord bridge and routes the event to `repo-rescue`.
* **Agent Responsibilities:**
  1. Parses raw Discord chat messages into structured problem reports for ANY valid Bug ID (`BUG-001`, `BUG-002`, or future IDs).
  2. Identifies affected service (`checkout-service`), endpoints (`POST /checkout`), and parameters.
  3. Validates against standardized bug report fixtures (`fixtures/*.json`) or runs `scripts/rescue_workflow.py validate-report --bug-id <BUG_ID>`.
  4. Identifies the target workspace (default or isolated demo workspace).
  5. Categorizes severity (`High`/`Medium`) and records incident tracking ID.
  6. Emits a compact Triage Card under 1,200 characters and mentions `@repo-rescue-reproducer`.

### Stage 2: Reproduction (Automated Verification)
* **Agent:** `repo-rescue-reproducer` (`addressing: owner-agents`)
* **Trigger:** Mentioned by `@repo-rescue` in `#bug-triage`.
* **Agent Responsibilities:**
  1. Operates with strictly **read/test-only** access to the supplied workspace.
  2. Executes reproduction in the project's virtual environment:
     ```powershell
     .\.venv\Scripts\python.exe scripts/rescue_workflow.py verify-reproduction --bug-id <BUG_ID>
     ```
  3. Confirms that baseline checkout tests pass while the reproducer test triggers the reported failure.
  4. Records the exact trace and failure signature **without altering any application code**.
  5. If the bug fails to reproduce, halts gracefully and notifies `@repo-rescue`.
  6. If confirmed, emits a compact Reproduction Report under 1,200 characters and mentions `@repo-rescue-fixer` with `<BUG_ID>` and `<WORKSPACE_PATH>`.

### Stage 3: Remediation & Patch Staging
* **Agent:** `repo-rescue-fixer` (`addressing: owner-agents`)
* **Trigger:** Mentioned by `@repo-rescue-reproducer`.
* **Agent Responsibilities:**
  1. Accepts ANY supplied bug ID. Never refuses a bug as out of scope.
  2. Modifies code files **ONLY inside the explicitly supplied demo workspace**. Never treats the demo workspace as read-only, and never touches the main repository worktree.
  3. Analyzes failure trace back to `app/service.py` and implements a minimal 1-2 line code fix.
  4. Stages the patch and validates test suites:
     ```powershell
     .\.venv\Scripts\python.exe scripts/rescue_workflow.py stage-patch --bug-id <BUG_ID>
     ```
  5. Re-runs the full test suite (`.\.venv\Scripts\python.exe -m pytest -v`) to confirm 0 regressions.
  6. **Guardrail:** The patch is staged in `patches/<BUG_ID>.patch`; **no automatic commit or push is executed**.
  7. Emits a compact Fix Card under 1,200 characters with diff preview and mentions `@repo-rescue-reviewer` with `<BUG_ID>` and `<WORKSPACE_PATH>`.

### Stage 4: Independent QA & Audit
* **Agent:** `repo-rescue-reviewer` (`addressing: owner-agents`)
* **Trigger:** Mentioned by `@repo-rescue-fixer`.
* **Agent Responsibilities:**
  1. Audits the **EXACT supplied bug ID** (e.g. `BUG-002`, `BUG-003`). Never defaults to `BUG-001`!
  2. Operates as a strictly **read-only** auditor. Never modifies, commits, or pushes files.
  3. Inspects working tree changes via `git status -s` and `git diff` within the supplied workspace.
  4. Validates that **only** `app/service.py` was modified and that no secrets, credentials, or unauthorized files were touched.
  5. Runs independent verification:
     ```powershell
     .\.venv\Scripts\python.exe scripts/rescue_workflow.py audit-patch --bug-id <SUPPLIED_BUG_ID>
     ```
  6. Confirms that all tests pass in `.venv`.
  7. Emits a structured Review Verdict (`PASS`).
  8. Pauses the workflow and explicitly prompts the human engineer in `#bug-triage` for sign-off:
     > *"Developer, please review the proposed diff above. Reply with `!approve <SUPPLIED_BUG_ID>` to authorize commit or `!reject <SUPPLIED_BUG_ID>` to request revision."*

### Stage 5: Human Approval Gate
* **Mechanism:**
  1. The human developer reviews the patch preview and regression audit posted in Discord `#bug-triage`.
  2. Approval requires explicit, genuine human sign-off (`!approve <BUG_ID>`).
  3. Automated agents and test runners **must never simulate or auto-grant approval**.
  4. Once genuinely approved, the patch can be committed and merged by the human maintainer. Automatic merges or unreviewed commits are strictly prohibited.

---

## 3. Reusable Multi-Bug Scenarios & Tooling

To allow judges and developers to test the full lifecycle deterministically without manual file editing, RepoRescue provides standard tooling:

* **`scripts/bug_scenario.py`:**
  * `list`: Lists registered scenarios (`BUG-001`, `BUG-002`) and their current status.
  * `status [BUG-ID]`: Checks whether code contains seeded or resolved patterns.
  * `seed [BUG-ID]`: Seeds target bug in `app/service.py`.
  * `restore [BUG-ID|--all]`: Restores `app/service.py` to clean passing state.
* **`scripts/rescue_workflow.py`:**
  * Standardized CLI for all workflow stages: `validate-report`, `verify-reproduction`, `stage-patch`, `audit-patch`, `record-decision`, and `status`.

---

## 4. Current Status & Verified Telemetry

* **Repository Scaffolding & Clean Baseline:** Complete. FastAPI service, automated test suite, multi-bug scenarios (`BUG-001`, `BUG-002`), and CLI tooling are fully tested and passing.
* **Switch Console 0.40.1 Template:** Declaratively defined in `switch/reporescue.template.yaml` and synchronized with `switch/agents/*.md`.
* **Live Discord Verification (BUG-001 Telemetry):** Fully executed across the 4 OpenCode agents in Discord `#bug-triage` on the `RepoRescue Lab` server across 51 tool calls:
  - `repo-rescue` received human bug report and delegated to `repo-rescue-reproducer`.
  - `repo-rescue-reproducer` autonomously ran pytest in `.venv` (24 tool calls, 3m 20s), isolated HTTP 500, and handed off to `repo-rescue-fixer`.
  - `repo-rescue-fixer` patched `app/service.py`, generated `patches/BUG-001.patch`, confirmed tests green (22 tool calls, 3m 25s), and handed off to `repo-rescue-reviewer`.
  - `repo-rescue-reviewer` audited git diff, verified zero regressions (5 tool calls, 55s), issued `Verdict: PASS`, and gated human maintainer sign-off (`!approve`).
  - Pre-approval review complete (`Verdict: PASS`); awaiting human maintainer sign-off (`!approve BUG-001`). Live screenshots archived in `docs/screenshots/`.
* **CLI & Local Verification (BUG-002 Rehearsal):** Fully rehearsed locally using `rescue_workflow.py` (triage -> reproduction confirmed `assert 12.0 == 11.20` -> minimal diff staged to `patches/BUG-002.patch` -> audit verdict `PASS`; simulated rehearsal approval for workflow testing, awaiting human maintainer production approval).
