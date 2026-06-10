# The Schism — MVP Scope & Intent (Agent-Ready)

This repository is intended to become a **turn-based strategic war-machine simulation** (The New System-like). The focus is **operations**, **logistics**, and a rigorous **After-Action Report (AAR)** explaining outcomes with traceable numeric attribution.

This document is the **source of truth** for MVP scope/goal so future agents can implement without revisiting design decisions.

---

## Product One-Liner

Turn-based strategic war-sim where you run a New System-like war machine. You manage **industrial throughput**, **route-based logistics**, and **3-class supplies** to execute **abstract multi-phase operations** with tactical decisions at each phase. Battles are not rendered; the payoff is a rigorous **After-Action Report** explaining outcomes.

---

## MVP Constraints (Hard Requirements)

- **UI**: a screen-based interface with minimal typing.
- **Session**: **no save/load** (single-session only).
- **Time model**: **turn-based**, where **1 turn = 1 day**.
- **Operations**: hard cap of **1 active operation at a time**.
- **Scope emphasis**: operations/battles and AAR. “Fronts” can exist as UI grouping only (no mechanics).

---

## Scenario & Win Condition (MVP)

- Single key planet with **3 simultaneous objectives**:
  - **Droid Foundry**
  - **Communications Array**
  - **Power Plant**
- **Win condition**: capture all **3 objectives**.
- Capturing objectives produces **two planet-level effects**:
  - **(A)** reduces enemy **reinforcement / regeneration** on that planet
  - **(B)** reduces enemy **fortification** on that planet

---

## Strategic Spine (Core Systems)

The game’s “feel” comes from three primary bottlenecks:

1. **Industrial capacity (A)**: global production throughput / slots
2. **Supplies in theater (E)**: three supply classes that materially affect outcomes
3. **Logistics throughput (D)**: route-based travel time + interdiction risk, represented via depots/staging

### Production structure (hybrid)

- A **global production pool** produces units/gear/supplies.
- Output is pushed via **route-based supply lines** to the key planet, through **depots/staging nodes**.
- MVP can use a **small simplified graph** (e.g., Core → Mid → Front).

**Barracks addendum (MVP clarification)**  
To keep the “global production pool” feel while clarifying throughput, industrial capacity is now modeled as **two parallel pools**:

- **Factory pool**: produces **Supplies** (Ammo/Fuel/Med+Spares) + **Walkers**.
- **Barracks pool**: produces **Infantry** + **Support**.
- Each building contributes **slots/day**; totals are **data-driven** (rules config) and can be tuned per scenario.
- Both pools use the same **deterministic fair‑share** queue policy for MVP.

---

## Supplies (MVP = 3 classes)

Track supplies per **task force** and per **depot**:

- `Ammo`
- `Fuel/Energy`
- `Medical+Spares`

Shortages must:

- increase losses
- reduce objective progress
- degrade readiness/cohesion
- increase variance (especially when intel confidence is low)

---

## Intel Model (Explicit Distributions)

The map displays enemy info as **range + confidence**, e.g.:

- “Strength 1.2–2.0, 70%”

Rules:

- Recon should **narrow the range** and/or **increase confidence**.
- Overall randomness level: **medium variance**.
- Enemy strength is instantiated as an **abstract planet-level package** (MVP), not a full mirrored force model.

Implementation bias:

- Resolver should be **deterministic given a seed** and bounded stochasticity.
- Stochasticity should be explicitly tied to **intel confidence** and **risk tolerance choice** during operations.

---

## Operations (Where Zoom Happens)

Operations are the only “zoomed-in” gameplay; everything else supports them.

### Duration (multi-turn vs same-turn)

- Operation duration is determined by a **combination rule** of:
  - objective type
  - enemy strength/fortification
  - player-chosen operation type (raid vs campaign, etc.)
- MVP can implement a simple formula + thresholds; it must still produce:
  - short operations sometimes (raids)
  - longer, multi-day operations often (campaign/siege)

### Concurrency cap

- Only **one** active operation at a time (hard cap).

---

## Battle System (Abstract, 3 Phases, Prompted Decisions)

There is **no battlefield visualization**. Each phase prompts decisions **one at a time**.

### Locked phase decisions (exact set)

**Phase 1: Contact & Shaping**

- A) Approach axis: `direct / flank / dispersed / stealth`
- C) Fire support prep: `conserve / preparatory`

**Phase 2: Main Engagement**

- E) Engagement posture: `shock / methodical / siege / feint`
- G) Risk tolerance: `low / med / high` (variance knob)

**Phase 3: Exploit / Consolidate**

- I) Exploit vs secure: `push / secure`
- J) End-state: `capture / raid / destroy / withdraw`

### Signature interactions (exactly 3 for MVP)

Only these three capability interactions are required in MVP:

1. **Transport/protection**: vehicles/walkers can carry/protect infantry, reducing infantry losses until vehicle effectiveness drops.
2. **Recon reduces variance**: better recon improves initiative/positioning and reduces randomness.
3. **Medics improve sustainment**: medics reduce casualty rate and accelerate readiness recovery.

### Unit composition logic (Approach C)

- Use **baseline power accounting** plus the 3 high-impact capability interactions above.
- No giant roster: use roles (e.g., infantry + walkers + support).

---

## Failure Consequences (Must Persist Into Future Ops)

If an operation fails:

- **Planet control decreases** (you lose ground)
- **Enemy fortification increases** (they dig in)

These consequences must make future operations **harder, longer, and/or more costly** (direct mechanical impact).

---

## After-Action Report (AAR) — MVP Requirements

Every operation resolves to an AAR that includes:

- Outcome summary:
  - objective result(s)
  - time consumed (days)
  - losses
  - remaining supplies
- Top 3–5 causal factors with **numeric contributions**, tied to:
  - industrial readiness / supply shortages
  - logistics delays / interdiction
  - intel confidence and risk choice
  - fortification and biome/terrain fit (biome can be simplified in MVP)
  - posture choices per phase
- Phase timeline: “what changed each phase”
- Recommendations derived from the same logged factors

### Non-negotiable implementation note

The battle resolver must **log named multipliers/contributors each phase** so the AAR is explainable and auditable.

Practical approach:

- Compute outcome from a set of **named factors** (multipliers or additive terms).
- Log each factor application per phase with:
  - `name`
  - `value`
  - `why` (short string)
  - `phase`
  - `delta` (what it affected: progress, casualties, readiness, etc.)

---

## Enemy Model (MVP)

Enemy is a planet-level package with:

- `strength_range` (min/max)
- `confidence` (player belief)
- `fortification`
- `reinforcement_rate`

During an operation:

- sample “true strength” from the distribution
- update the player estimate after (narrow range/increase confidence based on what was observed)

---

## Screens (Minimum Set)

1. **Situation Map**
   - key planet objectives status
   - enemy strength range + confidence
   - fortification, control, reinforcement rate

2. **Production**
   - industrial capacity, queues, ETAs

3. **Logistics / Depots**
   - depot stocks (Ammo/Fuel/Med+Spares)
   - routes to key planet with travel time + interdiction risk

4. **Task Force**
   - composition (roles/vehicles), readiness/cohesion, supply carried

5. **Operations**
   - launch operation, then phase prompts
   - after-action report viewer

---

## Out of Scope (MVP)

- Visible battlefield, sprites, pathfinding
- Save/load
- Multi-planet campaign beyond the single key planet
- Deep politics/senate
- Large unit catalog / canon naming requirements
- Full enemy force modeling

---

## Implementation Bias (Strong Preference)

Build as a **data-driven rules engine**:

- Use **JSON/YAML** for:
  - unit roles
  - supplies and shortage effects
  - objectives
  - operation types
  - terrain/biome tags (even if simple)
- Keep resolver deterministic with bounded stochasticity tied to:
  - intel confidence
  - risk tolerance
- Maintain an **event log** that powers AAR attribution.

---

## “Done” Criteria for MVP (Acceptance)

MVP is complete when a player can:

- play day-by-day
- view Situation / Production / Logistics / Task Force screens
- create shipments to move supplies through depots to the key planet
- launch exactly one operation at a time against one of the objectives
- make the 3-phase decisions (A/C → E/G → I/J)
- receive an AAR with:
  - days consumed, supplies remaining, losses, objective outcome
  - top causal factors with numeric contributions
  - phase-by-phase timeline
  - recommendations derived from logged factors
- win by capturing all 3 objectives; objectives reduce reinforcement and fortification
