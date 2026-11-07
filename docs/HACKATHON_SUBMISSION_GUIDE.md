# Flip the Switch Hackathon 2026: Official Submission Guide & Demo Script

> **Project:** RepoRescue
> **Track:** Best Business Workflow
> **Submission Deadline:** November 7, 2026 at 11:59 PM IST

---

## 1. Pre-Submission Checklist

- [x] **Repository Public & Accessible:** https://github.com/shavedXpixel/RepoRescue
- [x] **Clean Working Tree:** `main` branch passes all 20 tests with 0 failures (`pytest -v`).
- [x] **Screenshots Archived:** Live Discord handoff screenshots captured in `docs/screenshots/discord_handoff_1.png` and `docs/screenshots/discord_handoff_2.png`.
- [x] **Switch Template:** Tested and valid Switch Console 0.40.1 template in `switch/reporescue.template.yaml`.
- [x] **Multi-Bug Scenarios:** Two realistic scenarios documented and tested (`BUG-001` and `BUG-002`) in `fixtures/` with patch artifacts in `patches/` and audit records in `reports/`.
- [x] **Governance & Safety:** Explicit human approval gate (`!approve <BUG_ID>`) enforced before any Git commit.
- [ ] **Demo Video (2:30):** Record and upload to YouTube / Loom using the script below.

---

## 2. Copy-Paste Hackathon Submission Form Answers

### 2.1 Project Title
```text
RepoRescue — Autonomous Multi-Agent AI Software Debugging & Remediation in Discord via Switch Console
```

### 2.2 Hackathon Track
```text
Best Business Workflow
```

### 2.3 Short Description (Tagline)
```text
An autonomous AI incident response workflow where developers and 4 specialized OpenCode agents triage, reproduce, patch, independently audit, and human-approve production bug fixes directly inside Discord #bug-triage via Switch Console 0.40.1.
```

### 2.4 Detailed Project Description
```text
When software incidents happen in production, engineering teams waste critical hours context-switching between Discord alert channels, local terminal consoles, failing test logs, and Git branches. Rushed manual hotfixes often introduce regressions or slip past security reviews.

RepoRescue solves this by transforming a team's Discord `#bug-triage` channel into an autonomous, human-governed engineering war room powered by Switch Console 0.40.1 and OpenCode (opencode/beam-free).

When an engineer reports a bug in Discord, Switch coordinates 4 specialized agents operating on the local repository:
1. repo-rescue (Triage & Lead): Parses incoming symptoms, cross-references fixtures, and emits a structured Triage Card.
2. repo-rescue-reproducer (Reproduction): Read-only agent that executes targeted Pytest suites in .venv, capturing exact failure signatures (or halting gracefully if unreproducible).
3. repo-rescue-fixer (Remediation): Analyzes root causes, writes a minimal code fix, exports a unified diff to patches/<BUG_ID>.patch, and validates zero regressions across the entire test suite without auto-committing.
4. repo-rescue-reviewer (QA Gatekeeper): Independent auditor that inspects git diffs, verifies test execution, checks for secret leaks or unauthorized file modifications, issues a structured Review Verdict (PASS), and pauses the pipeline for human developer approval.

The human developer reviews the proposed patch directly in Discord and signs off with `!approve <BUG_ID>`. Only after human authorization does the lead agent mark the incident resolved.
```

### 2.5 How did you use Switch in your project?
```text
Switch Console 0.40.1 is the core orchestration backbone of RepoRescue. Rather than building a fragile standalone Discord bot, we used Switch's native Discord Gateway Bridge (RepoRescue Switch Bot) to bridge our Discord server (RepoRescue Lab) channel #bug-triage to local OpenCode (opencode/beam-free) agent runtimes.

We leveraged Switch's advanced room addressing architecture to achieve clean agent handoffs:
- `addressing: anyone` on repo-rescue allows human developers to initiate triage simply by talking in Discord.
- `addressing: owner-agents` ("Me and my agents") on the three specialist agents (reproducer, fixer, reviewer) ensures they wake up ONLY when explicitly @-mentioned by peer agents. This eliminates chat spam, race conditions, and infinite conversational loops.
- We established a strict Discord Output Contract (<1,200 characters per message, <15 lines per diff block) to guarantee that Switch's switch_post_message never encounters payload truncation.
- We defined our entire multi-agent topology declaratively in `switch/reporescue.template.yaml` following Switch Console 0.40.1 syntax.
```

### 2.6 What did you like about Switch, and what would you improve?
```text
What We Loved:
1. "Me and my agents" Addressing: This feature is game-changing for multi-agent workflows. It allows agents to collaborate autonomously via standard @-mentions without triggering accidental broadcast storms.
2. Native Chat Bridging: Eliminating the need to deploy and host custom Discord bot websockets let us focus entirely on engineering the debugging pipeline.
3. Local Execution: Switch seamlessly connected cloud LLM reasoning with local Python virtual environments and Git workspaces.

Areas for Improvement:
1. Discord Payload Handling: When an agent produces a tool call with long terminal output, Switch's Discord bridge occasionally struggles with message chunking. Built-in automatic truncation or collapsible spoiler tags for outputs >2,000 chars would make the bridge even more resilient.
2. Template Import UX: Adding a 1-click "Import Template" file picker in the Switch Console web UI would speed up multi-agent environment provisioning.
```

---

## 3. Under-3-Minute Demo Video Script (2:30 Sequence)

### [0:00 – 0:25] Introduction & The Problem
* **Visual:** Switch Console 0.40.1 UI open alongside Discord `#bug-triage` (RepoRescue Lab) and Antigravity IDE.
* **Voiceover:**
  > "Hi everyone, welcome to RepoRescue — our submission for the Flip the Switch Hackathon 2026 in the Best Business Workflow track.
  > In production incident response, engineers waste critical hours jumping between chat threads, terminals, failing test logs, and untested hotfixes.
  > RepoRescue turns our Discord `#bug-triage` channel into an autonomous, multi-agent debugging war room powered by Switch Console and OpenCode — with a strict human approval gate."

### [0:25 – 0:55] Incident Intake & Triage
* **Visual:** Type in Discord `#bug-triage`:
  `Customers are getting HTTP 500 errors on POST /checkout when applying promo code RESCUE20. Please investigate!`
* **Voiceover:**
  > "Notice how our lead agent, `@repo-rescue`, immediately triages the bug report. Because it uses Switch's `anyone` addressing policy, it listens to team messages, correlates our bug fixture, and emits a structured Triage Card.
  > It then mentions `@repo-rescue-reproducer` to hand off investigation."

### [0:55 – 1:45] Autonomous Reproduction, Fix & Review
* **Visual:** Show `@repo-rescue-reproducer` card appear, followed by `@repo-rescue-fixer` and `@repo-rescue-reviewer`.
* **Voiceover:**
  > "Because the specialist agents use Switch's 'Me and my agents' addressing, they only speak when tagged.
  > The reproducer executes `pytest` in our Python virtual environment, confirms the `KeyError: 'discount_percent'`, and tags `@repo-rescue-fixer`.
  > The fixer analyzes the root cause, applies a minimal 1-line fix, writes `patches/BUG-001.patch`, and validates that all tests pass without touching `git commit`.
  > Next, `@repo-rescue-reviewer` independently audits the diff, verifies zero secret leaks and clean test passes, issues `Verdict: PASS`, and halts the pipeline for human approval."

### [1:45 – 2:30] Human Approval Gate & Conclusion
* **Visual:** Type `@repo-rescue !approve BUG-001` in Discord. Show the `[INCIDENT RESOLVED]` card appear. Switch to terminal and run `.\.venv\Scripts\python.exe scripts/rescue_workflow.py status` and `.\.venv\Scripts\python.exe -m pytest -v` (20 passed).
* **Voiceover:**
  > "No code is committed automatically. I review the proposed diff right here in Discord and reply `!approve BUG-001`.
  > `@repo-rescue` validates the sign-off and officially closes the incident.
  > In Antigravity IDE, our CLI audit tool tracks the full history in `reports/` and our entire 20-test suite is completely green.
  > RepoRescue proves how Switch transforms chat from simple notification spam into a governed, autonomous software engineering team. Thank you!"
