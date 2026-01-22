# System Map UI Overhaul: "The Command OS" Integration Plan

## 1. Vision
Transform the interface from a "dashboard of disjointed panels" into a **Map-Centric Operating System**. The user's engagement with the world is driven entirely by the **System Map**. Selecting a location changes the entire context of the screen, immersing the commander in that specific theater ("Industrial", "Transit", or "Combat").

## 2. Layout Architecture

The screen is divided into three permanent zones:

### Zone 1: Global Command Header (Top)
The "Heads-Up Display" for the entire war effort.
*   **Left (Status)**: "Republic Command Network", Turn Counter, Global Stockpiles (Ammo/Fuel/Med), Global Unit Counts.
*   **Right (Actions)**: 
    *   **Action Points (AP)**: Clearly displayed currency.
    *   **[END TURN] Button**: Prominent action to advance the day.
    *   *(Note: No generic "Production" or "Logistics" buttons here; those move to context-specific views).*

### Zone 2: Theater Navigator (Below Header)
A horizontal track that persists across all views.
*   **Visuals**: The existing "Metro Map" style.
*   **Function**: Acts as the primary navigation tab bar.
*   **Nodes**: `[ CORE WORLDS ] -- [ DEEP SPACE ] -- [ CONTESTED SYSTEM ]`
*   **Active State**: The currently selected node is highlighted/glowing, indicating the active "View Mode."

### Zone 3: The Command Viewport (Main Content)
The large central area filling the rest of the screen. Its content is **completely swappable** based on the Zone 2 selection.

---

## 3. The Viewport Modes

### Mode A: Industrial Command (Selected: "Core Worlds")
*   **Purpose**: Production management and rear-echelon logistics.
*   **Layout**:
    *   **Left Column**: **Factory Status**. Slots utilized, current jobs, queue visualization.
    *   **Right Column**: **Core Stockpiles**. Detailed breakdown of reserves available for shipment.
    *   **Action HUD (Bottom)**: Integrated "Queue Production" controls. Buttons to `[PRODUCE AMMO]`, `[RECRUIT INFANTRY]`, etc., appear here.

### Mode B: Transit Monitor (Selected: "Deep Space")
*   **Purpose**: Visibility of the supply lines.
*   **Layout**:
    *   **Main View**: A "Radar" or List view of all active `CargoShip` entities.
    *   **Data Columns**: Ship Name, Location, Destination, Payload Manifest, ETA.
    *   **Empty State**: "SECTOR CLEAR. NO SHIPS IN TRANSIT."

### Mode C: Tactical Theater (Selected: "Contested System")
*   **Purpose**: The "Fight" and the local logistics chain.
*   **Sub-Navigation (Planetary Map)**:
    *   Visual representation of the surface chain: `[SPACEPORT] -> [MID DEPOT] -> [THE FRONT]`.
    *   Clicking these nodes updates the details *within* this view (no page reload, just update the data panel below).
*   **Sub-Views**:
    *   **Spaceport Focus**: Shows stockpile at port, interdiction risk, and ability to "Unload/Manage" ships if docked.
    *   **Front Focus (The Combat Hub)**:
        *   **Left**: Task Force Status (Readiness, Cohesion, Local Supplies).
        *   **Right**: Enemy Intel (Estimates, Fortification, Alertness).
        *   **Center/Bottom**: Active Objectives (`Foundry`, `Comms`, `Power`) and Action Buttons (`[RAID]`, `[SIEGE]`, `[CAMPAIGN]`).
    *   **Mid Depot Focus**: Stockpiles and throughput status.

---

## 4. Technical Implementation Strategy

### A. Frontend (Templates)
1.  **Rewrite `dashboard.html`**:
    *   Remove the rigid CSS grid (`#grid`, `#col-mid`, `#col-right`).
    *   Implement the 3-Zone vertical stack structure.
    *   Define a generic `#viewport` container for HTMX swapping.
2.  **New Template Components**:
    *   `viewport_core.html`: Production UI.
    *   `viewport_space.html`: Ship list.
    *   `viewport_tactical.html`: The complex surface view with its own sub-swapping logic for Spaceport/Front.
3.  **Refined Header**: Move AP and Next Day logic to `header.html` and align to the right.

### B. Backend (Controller & ViewModels)
1.  **Refactor `ConsoleController`**:
    *   Fix the "click eating" bug: Differentiate between *Navigation* (switching Viewport modes) and *Interaction* (clicking a button within a mode).
    *   **State Tracking**: Add `self.view_mode` (Core/Deep/System) separate from `self.selected_node`.
2.  **Update `viewmodels.py`**:
    *   Create aggregate ViewModels for the page loads (`core_view_vm`, `tactical_view_vm`) that combine data previously split across `production_vm`, `logistics_vm`, etc.
    *   **Unified HUD Logic**: Ensure prompts and action results are passed into the Viewport's local feedback area, not a disconnected console log.

### C. Styling (CSS)
1.  **Viewport Container**: Ensure it fills available vertical height (`flex: 1`).
2.  **Context-Aware Theming**: subtle color shifts (e.g., Industrial = Amber accents, Space = Blue/Cyan accents, Combat = Red accents) to reinforce the "Mode" feel.

---

## 5. Execution Steps

1.  **Step 1: The Frame.** Update `base.html` / `dashboard.html` and `terminal.css` to establish the Header + Strip + Viewport layout.
2.  **Step 2: The Controller.** Update `ConsoleController` to handle the top-level navigation (switching modes) and fix the input handling bug.
3.  **Step 3: The Modes.** Implement the three Viewport templates (`Core`, `Deep`, `Tactical`) and their corresponding Logical ViewModels one by one.
    *   *3a. Core (Production)*
    *   *3b. Deep Space (Transit)*
    *   *3c. Tactical (Combat + Logistics)*
4.  **Step 4: The Header.** Finalize the Global Header (AP/Turn placement).
5.  **Step 5: Polish.** Verify smooth transitions and "active state" highlighting.
