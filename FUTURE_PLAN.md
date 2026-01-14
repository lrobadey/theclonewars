# Clone Wars War Sim — Future Plan

This document captures the **high-level gaps** and a **forward plan** to align the current MVP implementation
with the intended experience described in `CLONE_WARS_WAR_SIM_MVP.md`.

## Current Gaps (What’s Not Working Yet)

### 1) Operations are pre-planned, not phase-prompted
- The game currently collects all phase decisions up front, then resolves after a wait.
- The MVP calls for **phase-by-phase prompts** with decision points during execution.

### 2) Operation duration ignores operation type
- The MVP requires duration to be influenced by **objective type**, **enemy strength/fortification**, and
  **operation type** (raid/campaign/siege, etc.).
- The current flow has no operation type selection and uses only a simple fortification/control adjustment.

### 3) AAR lacks explainability
- The engine logs events, but the UI only displays a single “key factor.”
- The MVP requires an AAR with top 3–5 factors, phase timeline, and recommendations.

### 4) Intel confidence never updates
- Recon should narrow the strength range / increase confidence after operations.
- Currently, confidence is only used for variance; it does not evolve post-operation.

### 5) Reinforcement rate is cosmetic
- Reinforcement is displayed but does not drive enemy growth/pressure.
- The MVP expects reinforcement reduction to materially change outcomes and escalation.

### 6) Industrial capacity doesn’t force trade-offs
- Capacity only affects ETA, not queue limits or parallelism.
- The MVP’s strategic spine requires production constraints to shape choices.

### 7) Victory condition isn’t enforced
- Objectives can be secured, but there’s no explicit win/loss handling.

## Fundamental Design Blockers

1) **Disconnected systems**: production/logistics don’t strongly influence operations beyond a single
   supply check and automatic resupply.
2) **Weak feedback loop**: AAR doesn’t tell the player “why,” undercutting the war-sim feel.
3) **Static operations**: decisions are front-loaded instead of phase-driven, which removes tension
   and mid-operation agency.

## Forward Plan (Prioritized)

### Phase 1 — Core Loop Alignment (Highest Priority)
1. **Phase-by-phase operations**
   - Prompt decisions at each phase (Contact/Shaping → Engagement → Exploit/Consolidate).
   - Resolve phase results immediately and show a short phase report.

2. **AAR rebuild**
   - Display top 3–5 causal factors with numeric attribution.
   - Add phase timeline and recommendations derived from logged factors.

3. **Operation types**
   - Add selection for raid/campaign/siege.
   - Feed into duration + supply cost models.

### Phase 2 — Strategic Spine Reinforcement
4. **Intel feedback loop**
   - Update strength range/confidence after operations based on recon and observations.

5. **Reinforcement effects**
   - Tie enemy growth/fortification scaling to reinforcement rate.
   - Reduce it meaningfully when objectives are captured.

6. **Industrial capacity constraints**
   - Enforce queue slot limits or active-job caps to force trade-offs.

### Phase 3 — Campaign Closure
7. **Win/loss handling**
   - Add explicit victory when all three objectives are secured.
   - Optional: add a “campaign failure” threshold (control collapse or supply depletion).

## Suggested Next Sprint (Practical Slice)

- Implement phase-by-phase operation prompts.
- Expand AAR to include top factors + phase timeline.
- Add operation type selection feeding duration/supply costs.

These three items collectively unblock the “three-phase real-time simulation” experience and reinforce
core systems before deeper balance tuning.
