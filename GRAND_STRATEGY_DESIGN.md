# The Clone Wars: Grand Strategy Design & MVP Plan

**Vision:** A systems-driven simulated war campaign rooted in the *Star Wars* archetypes.
**Platform:** Textual UI / Terminal-first (Rich/Textual).
**Genre:** Grand Strategy / Simulation / Narrative Generator.

---

## 1. High Concept & Scope
A 4-year bounded campaign simulating a solar-system-wide conflict between two asymmetric powers. The player manages the high-level machinery of war (Logistics, Politics, Strategy) through a constrained daily loop, while an AI "Storyteller" interprets the system logs to generate emergent narrative.

### The Conflict
*   **The New System (Technocracy):**
    *   **Ideology:** Efficiency, Logic, Automation.
    *   **Governance:** *Council of Experts* (Values math/results, dislikes waste).
    *   **Forces:** 100% Droid armies. Fearless, consistent, mass-produced.
*   **The Human Collective (Biopunk/Socialist):**
    *   **Ideology:** Human-centric, collective spirit.
    *   **Governance:** *The Senate* (Values lives/populism, highly volatile).
    *   **Forces:** Clone troopers, Human officers. High variance (heroism/panic), morale-driven.

---

## 2. The Core Loop: Scarcity of Attention
The simulation runs day-by-day. The player cannot micro-manage everything.
**Constraint:** You have **3 Command Actions** per day.

### The Daily Flow
1.  **Morning Briefing:** Review logs/news.
2.  **Action Phase (Spend 3 AP):**
    *   *Logistics:* "Order Convoy", "Expand Port", "Build Factory".
    *   *Politics:* "Lobby Senator", "Cover-up Scandal", "Request Funding".
    *   *Military:* "Launch Operation", "Deploy Fleet", "Order Bombardment".
3.  **Night Processing:**
    *   Convoys move (physical travel).
    *   Battles resolve (tick-based).
    *   Politics update (support calculated).
    *   **Storyteller Phase:** The AI summarizes the day's events into narrative.

---

## 3. Core Systems Architecture

### A. The Logistics "Spine" (Physicality)
War is moving matter through space.
*   **Topology (MVP):** `[Core World A] <==> [Deep Space] <==> [Contested Planet] <==> [Core World B]`
*   **The Pipeline:**
    1.  **Production:** Factories on Core World generate stock (Ammo, Fuel, Units).
    2.  **Lift:** Items move to the **Spaceport** stockpile.
    3.  **Transit:** Items are loaded onto **Convoys** (requires Hull capacity).
    4.  **Travel:** Convoy physically traverses the graph (takes days).
    5.  **Arrival:** Items unload into **Frontline Depot**.
*   **Constraints:**
    *   **Port Capacity:** Only $N$ convoys can launch/dock per day.
    *   **Hull Pool:** Finite ships. Losing a convoy hurts future throughput.

### B. The Military Layer (Two Theaters)
#### Theater 1: Deep Space (The Blockade)
*   **Mechanic:** Interdiction & Attrition.
*   **Interaction:** Player deploys **Fleets** to Deep Space nodes.
*   **Combat:**
    *   Blockading fleets attack passing convoys.
    *   Convoys have **Hull Integrity** and **Cargo Integrity**.
    *   *Result:* Convoys may survive but arrive with 50% cargo destroyed.

#### Theater 2: Planetary Ground War (The Operation)
*   **Scope:** Operations are multi-day pushes to secure Objectives.
*   **Structure:** 3 Distinct Phases.
    *   **Phase 1: Setup & Contact:**
        *   *Choices:* **Artillery** (Spend Ammo -> Reduce Fortification) OR **Scout** (Risk Detection -> Reveal Enemy Strength).
    *   **Phase 2: The Engagement:**
        *   *Asymmetry:* Clones check Morale (Heroism/Panic). Droids check Stability (Consistent grind).
        *   *Storyteller:* Narrates specific tactical vignettes (e.g., "501st pinned by snipers").
    *   **Phase 3: Resolution:**
        *   *Winning:* **Chase** (High kills, high fatigue) OR **Secure** (Safe, high control gain).
        *   *Losing:* **Retreat** (Save units, lose ground) OR **Second Wind** (Risk total wipeout for rally).

### C. The Political Layer (Consequences)
*   **Entities:** Named Politicians with traits (Hawk, Dove, Corrupt).
*   **Global Metric:** **War Support** (0-100%).
*   **Resource:** **Political Capital** (Earned by victories/completed objectives).
*   **Dynamics:**
    *   High Casualties -> Low Support (Collective).
    *   Wasted Resources/Stalled Front -> Low Support (New System).
    *   Low Support -> Budget cuts, forced peace (Game Over).

---

## 4. MVP Implementation Roadmap (Phased)

We will build the system in 4 vertical slices to ensure playability at each step.

### Phase 1: The Backbone (The Loop & Map)
*Goal: A functioning solar system where you can move supplies.*
1.  **Map State:** Implement Multi-planet graph + Deep Space nodes.
2.  **Action System:** Implement the `ActionPoints` (3/day) logic.
3.  **Logistics V1:**
    *   Port Capacity logic.
    *   Convoy Travel (Physical movement over days).
    *   Production-to-Front flow.
4.  **UI:** Textual Dashboard showing Map, Stockpiles, and AP count.

### Phase 2: The Front (Ground Combat)
*Goal: Give the supplies a purpose (consumption/fighting).*
1.  **Operation Logic:** Deepen `ActiveOperation` to use the new 3-Phase designs.
2.  **Unit Traits:** Implement Clone Morale vs Droid Stability.
3.  **UI:** Dedicated `BattleScreen` for the 3-phase interactive flow.
4.  **Integration:** Operations consume supplies delivered in Phase 1.

### Phase 3: The Void (Space Combat)
*Goal: Add friction to the supply line.*
1.  **Fleet Objects:** Fleets can be stationed in Deep Space.
2.  **Interdiction Logic:** When Convoy enters Node X, if Enemy Fleet present -> Trigger Combat.
3.  **Space Calc:** Simple resolver for Hull/Cargo damage.

### Phase 4: The Senate (Politics & Narrative)
*Goal: The overarching "Why" and "Story".*
1.  **Politician System:** Generate initial senators/councilors.
2.  **Event Engine:** Triggers (High Casualties -> Senator Speech).
3.  **Budget/Support:** Connect Support levels to available AP or Production slots.

---

## 5. Technical Architecture
*   **Language:** Python 3.11+.
*   **UI Framework:** Textual (Terminal UI).
*   **Data:** JSON-driven rules (Unit stats, Politician traits) for easy balancing.
*   **State:** Single `GameState` object, pickle-able for save/load (future proofing).
