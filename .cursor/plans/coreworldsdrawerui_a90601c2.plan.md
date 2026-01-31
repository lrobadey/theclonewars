---
name: CoreWorldsDrawerUI
overview: Build a polished, animated bottom drawer for Core Worlds in the sim-v2 strategic map. The drawer displays real engine-state data (resources, facilities, garrison) and includes placeholder action modals with nice UI/animations (not wired yet).
todos:
  - id: wire-live-state
    content: Create types.ts, update client.ts, add useGameState hook, update App.tsx to use live state
    status: pending
  - id: map-from-engine
    content: Create mapFromGameState.ts to derive map nodes/connections from engine state with proper scaling and labeling
    status: pending
  - id: node-click-selection
    content: Update StrategicMap and MapNode to support click selection on major nodes only, with selected visual state
    status: pending
  - id: core-drawer
    content: Create SystemDrawer component with 3-column layout (Resources, Facilities, Garrison) and animations
    status: pending
  - id: placeholder-modals
    content: Create QueueJobModal with styled inputs and 'Not wired yet' toast behavior
    status: pending
  - id: styling-polish
    content: Add CSS for drawer, modals, progress bars, unit cards, and all animations
    status: pending
  - id: integration-verify
    content: Wire everything in App.tsx, build, and verify UI/UX
    status: pending
isProject: false
---

# Core Worlds Bottom Drawer (UI-Focused)

## Summary of confirmed requirements


| Area                  | Decision                                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Clickable nodes**   | Only the 3 major nodes (Core Worlds, Deep Space, Contested System). Intermediate nodes are decorative.                               |
| **Labels on map**     | Only major nodes labeled. Tactical waypoints (Spaceport, Mid Depot, Front) are unlabeled.                                            |
| **Drawer trigger**    | Only Core Worlds opens the drawer for now. Deep/Contested do nothing yet.                                                            |
| **Drawer close**      | X button or ESC. Clicking Core again does not toggle.                                                                                |
| **Drawer height**     | Auto-size to content up to a max (~40% viewport), then internal scroll.                                                              |
| **Resources scope**   | Core depot on-hand only (`new_system_core`).                                                                                         |
| **Units scope**       | Core garrison only (depot units at `new_system_core`): Infantry / Walkers / Support with icons.                                      |
| **Facilities detail** | Summary (factories count/capacity, barracks count/capacity) + active queue list (type/qty/ETA/stopAt).                               |
| **Actions**           | Placeholder buttons for Queue Factory Job + Queue Barracks Job. Opens animated modal, submit shows "Not wired yet" toast and closes. |
| **Focus**             | UI polish, animations, techy sci-fi vibe.                                                                                            |


---

## Implementation steps

### 1. Wire live game state into sim-v2 React client

**Files to create/update:**

- Create `[sim-v2/client/src/api/types.ts](sim-v2/client/src/api/types.ts)`
  - Copy type definitions from `src/clone_wars/frontend/src/api/types.ts` (already matches `/api/state` schema).
- Update `[sim-v2/client/src/api/client.ts](sim-v2/client/src/api/client.ts)`
  - Import `GameStateResponse` from `./types`.
  - Return typed `Promise<GameStateResponse>` from `getState()`.
- Create `[sim-v2/client/src/hooks/useGameState.ts](sim-v2/client/src/hooks/useGameState.ts)`
  - Poll `getState()` every 5s.
  - Expose `{ state, loading, error, refresh }`.
- Update `[sim-v2/client/src/App.tsx](sim-v2/client/src/App.tsx)`
  - Use `useGameState()` hook.
  - Derive header data (day, AP) from live state.
  - Pass live state to child components.

---

### 2. Derive map model from engine state

- Create `[sim-v2/client/src/data/mapFromGameState.ts](sim-v2/client/src/data/mapFromGameState.ts)`

**Logic:**

- Input: `state.systemNodes` + `state.logistics.routes`
- Output: `{ nodes: MapNodeData[], connections: ConnectionData[] }`

**Node mapping:**


| Engine ID             | UI Label         | UI Type     | Size     | Labeled? |
| --------------------- | ---------------- | ----------- | -------- | -------- |
| `new_system_core`     | CORE WORLDS      | `core`      | `large`  | Yes      |
| `deep_space`          | DEEP SPACE       | `deep`      | `medium` | Yes      |
| `contested_front`     | CONTESTED SYSTEM | `contested` | `medium` | Yes      |
| `contested_spaceport` | (none)           | `deep`      | `small`  | No       |
| `contested_mid_depot` | (none)           | `deep`      | `small`  | No       |


**Position scaling:** `x = (pos.x / 100) * 1200`, `y = (pos.y / 100) * 400` (to fit `viewBox="0 0 1200 400"`).

**Connection status:** Derive from `interdictionRisk`:

- `< 0.3` -> `active`
- `0.3 - 0.6` -> `disrupted`
- `> 0.6` -> `blocked`

---

### 3. Add click selection to major nodes

- Update `[sim-v2/client/src/components/StrategicMap.tsx](sim-v2/client/src/components/StrategicMap.tsx)`
  - Accept `selectedNodeId?: string` and `onNodeClick?: (nodeId: string) => void`.
  - Pass props to `MapNode`.
- Update `[sim-v2/client/src/components/MapNode.tsx](sim-v2/client/src/components/MapNode.tsx)`
  - Add `isClickable` prop (true for major nodes: `core`, `deep`, `contested` with labels).
  - Add `isSelected` prop.
  - If clickable: `cursor-pointer`, `role="button"`, `tabIndex={0}`, handle click/Enter/Space.
  - Selected state visual: brighter outer ring, subtle pulsing highlight, scale bump.

---

### 4. Implement Core Worlds bottom drawer

- Create `[sim-v2/client/src/components/SystemDrawer.tsx](sim-v2/client/src/components/SystemDrawer.tsx)`

**Props:**

```ts
interface SystemDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedNodeId: string | null;
  state: GameStateResponse;
}
```

**Behavior:**

- If `selectedNodeId !== "new_system_core"`, render nothing (for now).
- Framer Motion slide-up + fade animation.
- Auto-height up to `max-height: 40vh`, then scroll.
- Close button (X) top-right, ESC key listener.
- Backdrop blur + subtle neon top border.

**Sections (3-column layout matching mockup):**

#### Column 1: RESOURCES

- Fuel (icon + value + progress bar)
- Ammo (icon + value + progress bar)  
- Med+Spares (icon + value + progress bar)
- Data from: `state.logistics.depots.find(d => d.id === "new_system_core").supplies`

#### Column 2: FACILITIES & PRODUCTION

- **Factories** line: `{factories}/{maxFactories}` + `{capacity} slots/day`
- **Barracks** line: `{barracks}/{maxBarracks}` + `{capacity} slots/day`
- **Depots** line: count of logistics depots (static "1" for Core)
- Active queue list (scrollable if long):
  - Each job: type icon + quantity + ETA badge + stop_at
- Data from: `state.production`, `state.barracks`

#### Column 3: UNITS & GARRISON

- 3 unit cards with icons:
  - Infantry (silhouette icon) + count
  - Walkers (mech icon) + count
  - Support (vehicle icon) + count
- Data from: `state.logistics.depots.find(d => d.id === "new_system_core").units`

---

### 5. Implement placeholder action modals

- Create `[sim-v2/client/src/components/QueueJobModal.tsx](sim-v2/client/src/components/QueueJobModal.tsx)`

**Props:**

```ts
interface QueueJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  poolType: "factory" | "barracks";
}
```

**Factory job types:** Ammo, Fuel, Med+Spares, Walkers  
**Barracks job types:** Infantry, Support

**Modal content:**

- Animated fade-in + scale.
- Dropdown for job type (styled select with icons).
- Numeric input for quantity (styled spinner).
- "Queue" button with hover glow animation.
- On submit: show toast "Not wired yet", close modal.

**Trigger buttons in drawer:**

- "+ QUEUE FACTORY" button in Facilities section.
- "+ QUEUE BARRACKS" button in Facilities section.
- Both open the modal with appropriate `poolType`.

---

### 6. Styling and animation polish

- Update `[sim-v2/client/src/styles/index.css](sim-v2/client/src/styles/index.css)`

**Add:**

- `.system-drawer` - glassy dark background, neon border, blur backdrop.
- `.drawer-section` - section containers with headers.
- `.resource-bar` - animated progress bar with glow.
- `.unit-card` - hover effect, subtle pulse.
- `.queue-item` - job list item styling.
- `.modal-overlay` - backdrop blur.
- `.modal-content` - centered card with animations.
- `.btn-action` - techy button with glow states.
- `.toast` - notification styling.

**Animations:**

- Drawer slide-up: `translateY(100%) -> translateY(0)` with spring.
- Progress bars: animate width on mount.
- Unit cards: subtle hover scale.
- Modal: fade + scale spring.
- Buttons: glow pulse on hover.

---

### 7. Integration in App.tsx

**State management:**

```ts
const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
const [isDrawerOpen, setIsDrawerOpen] = useState(false);

const handleNodeClick = (nodeId: string) => {
  if (nodeId === "new_system_core") {
    setSelectedNodeId(nodeId);
    setIsDrawerOpen(true);
  }
  // Deep/Contested do nothing for now
};

const handleDrawerClose = () => {
  setIsDrawerOpen(false);
  setSelectedNodeId(null);
};
```

**Render:**

```tsx
<StrategicMap
  nodes={mapNodes}
  connections={mapConnections}
  selectedNodeId={selectedNodeId}
  onNodeClick={handleNodeClick}
/>
<SystemDrawer
  isOpen={isDrawerOpen}
  onClose={handleDrawerClose}
  selectedNodeId={selectedNodeId}
  state={state}
/>
```

---

### 8. Verify and polish

- Run `npm run build` in `sim-v2/client` to check TypeScript.
- Check for linter errors in edited files.
- Manual test:
  - Click Core Worlds -> drawer opens with real data.
  - Click Deep Space / Contested -> nothing happens.
  - Click X or press ESC -> drawer closes.
  - Click "+ QUEUE FACTORY" -> modal opens, submit shows toast.
  - Verify animations are smooth and techy.

