# AGENTS.md - Execution Contract for The Clone Wars

This is the single canonical agent-instructions file for this repository. Do not maintain a second instruction file.

## 1) Mission and Quality Bar

Agents must deliver intentional, production-grade changes. A task is not complete if features are only partially wired, untested, or explained away with placeholders.

Hard rule:
- Do not ship half-implemented behavior.
- Do not claim completion without explicit verification evidence.

## 2) Source of Truth and Spec Traceability

`CLONE_WARS_WAR_SIM_MVP.md` is the source of truth for gameplay constraints and MVP behavior.

For every gameplay-affecting change, the final report must include:
- The exact MVP section(s) used as requirements.
- A short mapping from requirement to implementation.

Silent design drift from the MVP spec is prohibited.

## 3) Repository Architecture and Ownership Boundaries

Primary implementation paths:
- `sim-v2/` (primary server + web UI surface)
- `src/war_sim/` (shared simulation engine/domain)

Supporting legacy paths:
- `src/clone_wars/` (legacy engine/web/TUI/frontend)

Web-first hard rule:
- New feature development must target the web experience first.
- TUI/legacy-only feature work is not allowed unless explicitly requested for parity or bugfix reasons.

Cross-layer synchronization rule:
- Engine/domain/state changes are incomplete until corresponding API and web UI layers are updated.
- Required sync path for v2 work:
  - `src/war_sim/...`
  - `sim-v2/server/api/{schemas.py,mappers.py,router.py}` (as needed)
  - `sim-v2/client/src/{api,hooks,features,components}` (as needed)
- For touched legacy flows, apply the same rule across:
  - `src/clone_wars/engine/...`
  - `src/clone_wars/web/api/...` and render/viewmodel layers
  - `src/clone_wars/frontend/src/...`

## 4) Todo Discipline (Mandatory)

Use the todo/checklist system for any multi-step, investigative, or feature-level task.

Rules:
1. Break work into concrete steps.
2. Keep exactly one step in progress at a time.
3. Mark steps complete immediately after finishing.
4. Do not skip planning for cross-layer work.

You may skip todos only for single-line edits or purely informational replies.

## 5) Edit Consent Policy

Ask for user approval before major changes.

Major change means any of:
- Cross-layer implementation (engine + API + UI)
- Schema/interface contract changes
- More than 3 files edited

For non-major, tightly scoped fixes, direct execution is allowed.

## 6) Fully Wired Feature Gate (Definition of Done)

For feature or behavior changes, all items below are mandatory unless marked `N/A` with a task-specific reason:

1. Engine/domain logic is implemented and coherent.
2. API schema/mapper/router surfaces are updated where needed.
3. UI state/types/components/actions are wired to expose the behavior.
4. Rules/data/config are updated when behavior depends on tunable values.
5. Tests are added or updated (targeted + at least one relevant integration path).
6. No dead code, dangling feature flags, stub branches, or orphan controls remain.
7. Verification commands were executed and results reported.

If any required item is missing, completion is blocked.

## 7) Placeholder and Scaffolding Policy

Disallowed by default:
- Placeholder handlers
- Stubbed returns presented as complete behavior
- Dummy UI/data paths without full wiring
- `TODO`/`FIXME` used to defer required behavior for a completed task

Allowed only when explicitly requested by the user in the same task:
- Scaffold-only output
- Intentional placeholders with clear scope limits

## 8) Testing Policy (Strict Cross-Layer)

Behavior changes require robust verification.

Required minimum:
1. Run targeted tests for touched logic.
2. Run at least one relevant integration path test.
3. For frontend changes, run client build/typecheck and related API contract checks.
4. If no test harness exists in the touched area, add minimal practical tests in the same task.

Examples of expected coverage:
- Engine/domain: relevant tests under `tests/war_sim/` and/or targeted `tests/` modules.
- API/server: `sim-v2/server/tests/test_api_contract.py` plus affected server tests.
- Frontend: `npm run build` in the touched client (`sim-v2/client` or `src/clone_wars/frontend`) plus matching backend/API contract checks.

## 9) Verification Evidence Format (Mandatory)

Final reports must include exact commands and outcomes.

Required format:
- ``<command>`` -> `PASS`/`FAIL`
- If not run: ``<command>`` -> `SKIPPED` with explicit reason

High-level statements like "tests look good" are insufficient.

## 10) Repo Command Playbook

Use repo-root commands unless noted.

Core run flow:
- `python sim-v2/run_server.py`

Python tests:
- `pytest sim-v2/server/tests`
- `pytest tests/war_sim`
- `pytest tests` (broader regression when appropriate)

Frontend verification:
- `cd sim-v2/client && npm install && npm run build`
- `cd src/clone_wars/frontend && npm install && npm run build` (only when that client is touched)

Use targeted subsets first, then broaden when risk warrants it.

## 11) Prohibited Completion States

Do not mark tasks done when any of the following are true:
- Feature is only partially wired across layers.
- Behavior changed but verification is missing.
- MVP constraints were altered without explicit acknowledgment and approval.
- Implementation contains intentional gaps not requested by the user.

## 12) Required Final Response Structure

For implementation tasks, final responses must include:

1. `Spec traceability`
- MVP section references used
- Requirement-to-change mapping

2. `Files changed`
- Exact paths and concise purpose

3. `Verification`
- Commands run with pass/fail outcomes
- Explicit skipped checks with reasons

4. `Remaining risks`
- Known limitations or follow-up risks, if any
