# React Migration Plan & Progress Tracker

This document serves as the master checklist for migrating the *Clone Wars* UI from server-side HTMX/Jinja to a client-side React + TypeScript application.
**Strategy:** Parallel Implementation. We will build a new `api` backend alongside the existing `console` backend, and a new `frontend` project. The existing game will remain playable throughout the process.

## Phase 0: Infrastructure Setup
*Goal: Get "Hello World" running in React served by FastAPI alongside the existing app.*

- [ ] **Frontend Initialization**
    - [ ] Create `src/clone_wars/frontend` using Vite + React + TypeScript.
    - [ ] Setup TailwindCSS for styling (keeping the terminal aesthetic).
    - [ ] Configure `vite.config.ts` for proxying API requests to backend.
- [ ] **Backend Integration**
    - [ ] Create `src/clone_wars/web/api/` module.
    - [ ] Create `src/clone_wars/web/run_react.py` (new entry point) that mounts the React build as static files and includes the new API router.
    - [ ] Ensure `python3 clone-react` launches the new view, while `python3 clone` launches the old view.

## Phase 1: The API Layer (Python)
*Goal: Expose the "Engine" to the web via JSON. Logic must strictly match `console_controller.py` but return data instead of HTML.*

- [ ] **State Endpoint** (`GET /api/state`)
    - [ ] Return full GameState (Resources, Day, System Map Nodes).
    - [ ] Create Pydantic models for `GameStateResponse`.
- [ ] **Navigation API** (`POST /api/nav`)
    - [ ] Endpoints for changing view modes (Core/Deep/Tactical) if server-side tracking is needed (or move completely to client state).
- [ ] **Action Endpoints**
    - [ ] `POST /api/actions/dispatch` (Logistics)
    - [ ] `POST /api/actions/production` (Queue jobs)
    - [ ] `POST /api/actions/barracks` (Queue units)

## Phase 2: The Core UI Skeleton
*Goal: A "Terminal" container in React that can talk to the API.*

- [ ] **Layout Components**
    - [ ] `TerminalContainer`: The CRT effect wrapper.
    - [ ] `Header`: Global resource strip (Day, AP, Credits).
    - [ ] `Navigator`: The left/top navigation tabs.
    - [ ] `MessageLog`: A persistent toast/notification area for game feedback.
- [ ] **Game Context**
    - [ ] specific `useGameState` hook that polls or syncs with `GET /api/state`.

## Phase 3: Module Migration (The "Meat")
*Each module releases a major feature of the game logic.*

### 3.1: The System Map (Replacing `situation_map.html`)
- [ ] Refactor System Map into a React Component.
- [ ] Implement "Zoom" levels (Solar System vs. Planet View) using client-side state.
- [ ] **Feature Parity:**
    - [ ] Click node to select.
    - [ ] Hover for basic info.
    - [ ] "Contested Planet" detailed sub-view.

### 3.2: Logistics & Supply Chain
- [ ] Create `LogisticsPanel` component (Full screen modal or overlay).
- [ ] **Visuals:** Visual arrow lines for supply routes (SVG/Canvas).
- [ ] **Interactive:**
    - [ ] Drag-and-drop or Click-to-assign shipments.
    - [ ] Depot inspection.

### 3.3: Production & Industry
- [ ] Create `ProductionPanel`.
- [ ] **Improvement:** distinct tabs for "Factory" vs "Barracks" (no longer cramped).
- [ ] One-click queueing with visual feedback.

### 3.4: Operations (Combat)
- [ ] Create `WarRoom` component (The Tactical View).
- [ ] **Phases:**
    - [ ] Phase 1 (Shape/Contact) UI.
    - [ ] Phase 2 (Engage) UI with risk sliders.
    - [ ] Phase 3 (Exploit) UI.
- [ ] **AAR Viewer:** A dedicated nice-looking report card for battle results.

## Phase 4: Polish & Cutover
*Goal: The React version feels superior and ready to be the main version.*

- [ ] **Animations:** CSS transitions for window opening/closing.
- [ ] **Sound Effects (Optional):** Basic UI beeps/boops.
- [ ] **Tutorial/Tooltip System:** Overlay help for new players.
- [ ] **Final Verification:** Play a full 20-day campaign on the new UI.
- [ ] **Switchover:** Make `python3 clone` launch the React version by default.

## Rules for Agents
1. **NO LOGIC DUPLICATION:** Do not re-write `src/clone_wars/engine`. Import it in the API.
2. **PARALLEL ONLY:** Do not touch `console_controller.py` or existing templates. Work only in `src/clone_wars/frontend` and `src/clone_wars/web/api`.
3. **CHECKLIST:** Mark items as `[x]` in this file as you complete them.
