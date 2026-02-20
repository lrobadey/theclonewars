---
name: victoria3-combat-math
description: Analyze Victoria 3 warfare using exposed formulas and defines for battle generation, unit selection, casualties, morale, supply, attrition, and war support outcomes. Use when asked to explain, estimate, simulate, optimize, or debug Victoria 3 combat math, front behavior, naval-logistics effects, or capitulation pressure.
---

# Victoria 3 Combat Math

Use this skill to produce transparent, formula-first analysis of Victoria 3 warfare.

## Workflow

1. Gather scenario inputs before calculating:
- Front context: attacking/defending side, battalion counts, front length, objectives.
- Province context: state infrastructure and province combat-width multiplier.
- Unit context: manpower, morale, mobilization, offense, defense.
- Strategic context: supply status, naval disruption, casualties to date, battles lost share, turmoil.

2. Compute battle engagement width first:
- Use `ForceLimit = ceil((5 + infrastructure / 2) * province_combat_width_multiplier)`.
- Treat this as engagement cap, not total force on front.
- Note that random front-length reduction and numeric-advantage expansion affect final participating battalion count.

3. Estimate unit participation with eligibility and weighting:
- Exclude units with `manpower < 100` or `morale < 0.20`.
- Use a selection-weight framing:
  `weight ~= manpower * morale * mobilization * relevant_stat`.
- Use offense as relevant stat for attackers and defense for defenders.
- Prefer selected-commander troops and report this as a strong bias factor.

4. Model battle rounds explicitly:
- Use round loop framing: fighting-capable men -> casualties -> wounded recovery -> morale damage -> retreat/wipe check.
- Respect lethality bounds: `BATTLE_LETHALITY_MIN` to `BATTLE_LETHALITY_MAX`.
- Respect casualty floor per round: `MIN_MANPOWER_CASUALTY_PER_ROUND`.
- Explain uncertainty where per-round CE internals are partly hardcoded.

5. Integrate logistics and attrition:
- Connect convoy/supply-lane disruption to morale recovery pressure and lower effective engagement quality.
- Bound attrition with weekly min/max manpower loss defines.
- Explain that poor supply can suppress effective combat power even with high nominal battalion counts.

6. Convert battle outcomes into war outcomes:
- Track province capture and devastation effects.
- Apply weekly war exhaustion cadence (`DAYS_BETWEEN_WAR_EXHAUSTION = 7`).
- Tie casualty share, battle losses, and turmoil to war support pressure.
- Check capitulation boundary (`AUTO_CAPITULATE_WAR_SUPPORT = -100`).

7. Return outputs in this structure:
- `Assumptions`: explicit unknowns and version caveats.
- `Key Equations`: formulas and define values used.
- `Step-by-Step Result`: width -> participation -> round lethality framing -> strategic effects.
- `Sensitivity`: which 2-4 variables most change outcome.
- `Actionable Levers`: what to change (infrastructure, supply, force quality, front concentration, naval posture).

## Reference Loading

- Read `references/vic3-combat-math-deep-dive.md` when you need detailed mechanics, flowchart context, examples, or comparative modeling notes.
- Keep user-facing answers concise; only surface the parts needed for the asked question.

## Guardrails

- State which values are from exposed script/defines versus inferred behavior.
- Do not present unknown hardcoded internals as exact formulas.
- Flag patch/mod variability whenever terrain coefficients or defines may differ by version.
