# RepoRescue

> **Flip the Switch Hackathon 2026**  
> AI-assisted software debugging and remediation workflow with Switch, OpenCode, and Discord.

---

## 1. Project Overview

RepoRescue is an automated AI-assisted incident response and debugging workflow:
1. **Report:** An incident/bug is reported in Discord (`#bug-triage` in the `RepoRescue Lab` server).
2. **Coordinate:** Switch coordinates AI agents powered by OpenCode (`repo-rescue`).
3. **Reproduce:** An automated reproducer test isolates the bug and verifies failure.
4. **Fix & Review:** A minimal code patch is generated, audited, and tested for regressions.
5. **Human Approval:** A human maintainer reviews the diff and approves before changes are applied.

---

## 2. Milestone 1: Reproducible Demo Repository

This repository contains a lightweight, fully functional **FastAPI Checkout Service** with a deliberately seeded, reproducible bug (`BUG-001`).

### The Seeded Bug (`BUG-001`)
* **Endpoint:** `POST /checkout`
* **Trigger:** Checkout request with valid promotional code `promo_code="RESCUE20"`.
* **Root Cause:** In `app/service.py`, `ACTIVE_PROMOTIONS` defines percentage discounts using the key `'rate'` (0.20), but `apply_discount()` attempts to look up `'discount_percent'`.
* **Result:** Unhandled `KeyError: 'discount_percent'` triggers an **HTTP 500 Internal Server Error**.
* **Reproducer Test:** `tests/test_checkout.py::test_reproduce_bug_001_checkout_with_rescue20_promo` (deliberately expected to fail).
* **Bug Report Fixture:** See `fixtures/bug_report_001.json`.

> ⚠️ **Note:** Per hackathon rules, this bug is intentionally preserved during Milestone 1 scaffolding and will be addressed via the agent workflow in Milestone 2.

---

## 3. Windows PowerShell Setup Guide

### Prerequisites
* Windows 10/11
* Python 3.10+ (tested on Python 3.12)
* PowerShell 5.1+ or PowerShell 7+

### Step 1: Clone / Navigate to Workspace
```powershell
cd c:\Users\Priyansu\OneDrive\Desktop\RepoRescue
```

### Step 2: Create & Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate in PowerShell (run 'Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass' if script execution is restricted)
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 4. Running the Checkout Service

Start the local development server:
```powershell
uvicorn app.main:app --reload --port 8000
```

Verify service health in a separate PowerShell terminal:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "checkout-service",
  "version": "1.0.0"
}
```

Interactive API documentation (Swagger UI) is accessible at:
* [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5. Running the Test Suite

### Run All Tests (Shows Passing Tests and the Seeded Failure)
```powershell
pytest -v
```
**Expected Outcome:** `5 passed, 1 failed`
* `test_health_endpoint` -> **PASSED**
* `test_checkout_standard_order_success` -> **PASSED**
* `test_checkout_with_valid_fixed_discount_promo` -> **PASSED**
* `test_checkout_with_invalid_promo_code_returns_400` -> **PASSED**
* `test_checkout_validation_empty_items_returns_422` -> **PASSED**
* `test_reproduce_bug_001_checkout_with_rescue20_promo` -> **FAILED** (HTTP 500 reproduced)

### Run Only Standard Normal Tests
```powershell
pytest -v -k "not reproduce_bug"
```
**Expected Outcome:** `5 passed, 1 deselected`

### Run Only the Bug Reproducer Test
```powershell
pytest -v -k "reproduce_bug"
```
**Expected Outcome:** `1 failed` with `AssertionError: Seeded bug BUG-001 reproduced: Expected HTTP 200, but received HTTP 500`.

---

## 6. Project Structure

```
RepoRescue/
├── .gitignore                      # Git ignore rules for Python, venv, secrets
├── README.md                       # Setup and execution documentation
├── requirements.txt                # Pinned dependencies (FastAPI, pytest, uvicorn, etc.)
├── app/
│   ├── __init__.py                 # Package initializer
│   ├── main.py                     # FastAPI application entry point & routing
│   ├── models.py                   # Pydantic schemas (Items, Addresses, Requests)
│   └── service.py                  # Checkout business logic (contains seeded bug BUG-001)
├── fixtures/
│   └── bug_report_001.json         # Standardized bug report fixture for BUG-001
├── docs/
│   └── agent_collaboration_workflow.md # Multi-agent workflow specification (Triage -> Fix -> Approval)
└── tests/
    ├── __init__.py                 # Test package initializer
    ├── conftest.py                 # Pytest fixtures and TestClient configuration
    └── test_checkout.py            # 5 passing standard tests + 1 seeded reproducer test
```

---

## 7. Switch Agent Collaboration Workflow

For a detailed specification of how the Switch agents collaborate across the triage, reproduction, fix proposal, review, and human approval stages, see:
* [`docs/agent_collaboration_workflow.md`](docs/agent_collaboration_workflow.md)

### Key Guardrails
* **No Separate Discord Bot:** Switch natively handles Discord server and channel connectivity.
* **No Unverified Coordination Claims:** The agent collaboration specification is documented; live agent-to-agent verification is scheduled for Milestone 2.
* **No Automatic Merges or Deploys:** Every proposed patch requires explicit human sign-off via Discord or Switch Console.
