# Battle System Overhaul: Implementation Plan

**Purpose**: Replace the current abstract battle system with a true force-on-force combat simulation.

**For**: Senior Development AI Agent

---

## 1. App Architecture Overview

```
src/clone_wars/
├── engine/                    # Core game logic (Python)
│   ├── state.py              # GameState, EnemyPackage, TaskForceState, combat resolver
│   ├── ops.py                # Operation types, phases, decisions (BEING SIMPLIFIED)
│   ├── types.py              # Supplies, UnitStock, UnitComposition
│   ├── scenario.py           # Loads scenario.json into GameState
│   ├── logistics.py          # Depot/shipment system
│   ├── production.py         # Factory/production queue
│   └── rules.py              # Data-driven rules from JSON
│
├── data/                      # JSON configuration files
│   ├── scenario.json         # Starting conditions, enemy config (NEEDS UPDATE)
│   ├── operation_types.json  # Raid/Campaign/Siege definitions
│   ├── unit_roles.json       # Unit capabilities
│   └── supplies.json         # Supply effects
│
└── web/                       # Flask web UI
    ├── console_controller.py # Handles button clicks, mode transitions
    ├── render/viewmodels.py  # Builds view data for templates
    ├── templates/panels/     # Jinja2 HTML templates
    │   ├── console.html      # Main command interface
    │   ├── aar.html          # After-action report display
    │   └── ...
    └── routes/               # Flask route handlers
```

---

## 2. Current Battle System (What We're Replacing)

### Current Flow
1. Player selects target → operation type → 6 phase decisions
2. All decisions collected upfront via `OperationPlan`
3. Days tick by (countdown timer, nothing happens per day)
4. At completion: ONE equation runs with all modifiers summed
5. Compare to threshold → win/lose
6. AAR shows "top factors"

### Current Problems
- **Player troop count is ignored** for combat power (only used for protection/medic bonuses)
- **Enemy has no troops** — just abstract `strength_min/max` modifier
- **No actual simulation** — just modifier arithmetic at the end
- **Phases are cosmetic** — nothing changes between them
- **No force-on-force** — no attrition model, no enemy casualties

---

## 3. New Battle System Design

### Core Concept
**Tick-based force-on-force combat** where both sides have actual troops, cohesion degrades under fire, and combat ends when one side breaks.

### New Flow
1. Player clicks **"RAID"** button (single action, no phase decisions)
2. Combat simulation runs as a series of **ticks** (combat rounds)
3. Each tick: damage exchange based on power ratio
4. **Cohesion** degrades until one side breaks (< 0.2)
5. Casualties accumulate on BOTH sides
6. AAR shows: outcome, casualties (both sides), tick-by-tick breakdown, why you won/lost

### Key Mechanics

#### Power Calculation
```python
power = (infantry × 1 + walkers × 5 + support × 0.5) × cohesion × supply_modifier
```
- **Infantry**: Base combat unit (power = 1 per soldier)
- **Walkers**: Heavy hitters (power = 5 per walker)
- **Support**: Light combat contribution (power = 0.5 per unit)
- **Cohesion**: Multiplier 0.0–1.0 (fighting effectiveness)
- **Supply modifier**: Penalty if low on ammo/fuel

#### Defender Advantage
```python
defender_power = base_power × fortification
```
- Fortification > 1.0 gives defender bonus
- Attacker needs numerical/qualitative superiority to win

#### Damage Exchange (Each Tick)
```python
damage_to_enemy = (your_power / enemy_power) × base_damage_rate
damage_to_you = (enemy_power / your_power) × base_damage_rate
```
- Damage primarily reduces **cohesion**
- Small portion causes **casualties** (permanent losses)

#### Break Condition
```python
if cohesion < 0.2:
    that_side_breaks()  # Combat ends
```

#### Cohesion vs Readiness
| Concept | Meaning | When It Changes | Recovery |
|---------|---------|-----------------|----------|
| **Readiness** | Pre-battle fitness | Before/after ops | Days of rest |
| **Cohesion** | In-battle will to fight | During combat ticks | Resets after battle |

- Starting cohesion = readiness (tired troops start weaker)
- After combat: cohesion resets, readiness drops based on fight intensity

---

## 4. Data Model Changes

### 4.1 Enemy Force (NEW)

**File**: `src/clone_wars/engine/state.py`

**Current `EnemyPackage`**:
```python
@dataclass(slots=True)
class EnemyPackage:
    strength_min: float
    strength_max: float
    confidence: float
    fortification: float
    reinforcement_rate: float
```

**New `EnemyForce`** (replace or extend):
```python
@dataclass(slots=True)
class EnemyForce:
    # Actual troop counts (mirror player structure)
    infantry: int
    walkers: int
    support: int
    
    # Combat state
    cohesion: float  # 0.0-1.0, breaks when < 0.2
    
    # Modifiers (keep from current)
    fortification: float  # Defensive bonus (1.0 = none, 1.5 = 50% bonus)
    reinforcement_rate: float  # How fast they rebuild between ops
    
    # Intel (what player knows)
    intel_confidence: float  # 0.0-1.0, affects displayed estimates
```

### 4.2 Scenario Data (UPDATE)

**File**: `src/clone_wars/data/scenario.json`

**Current**:
```json
{
  "enemy": {
    "strength_range": [1.2, 2.0],
    "confidence": 0.7,
    "fortification": 1.0,
    "reinforcement_rate": 0.1
  }
}
```

**New**:
```json
{
  "enemy": {
    "infantry": 150,
    "walkers": 4,
    "support": 2,
    "cohesion": 1.0,
    "fortification": 1.2,
    "reinforcement_rate": 0.1,
    "intel_confidence": 0.7
  }
}
```

### 4.3 Combat Log (NEW)

**File**: `src/clone_wars/engine/combat.py` (NEW FILE)

```python
@dataclass(frozen=True)
class CombatTick:
    tick: int
    your_power: float
    enemy_power: float
    your_cohesion: float
    enemy_cohesion: float
    your_casualties: int
    enemy_casualties: int
    event: str  # e.g., "Exchange of fire", "Enemy wavering", "Your line holds"

@dataclass(frozen=True)
class CombatResult:
    outcome: str  # "VICTORY", "DEFEAT", "STALEMATE"
    reason: str  # "Enemy broke", "Your force broke", "Time expired"
    ticks: int
    your_casualties_total: int
    enemy_casualties_total: int
    your_remaining: dict  # {"infantry": X, "walkers": Y, "support": Z}
    enemy_remaining: dict
    tick_log: list[CombatTick]
    supplies_consumed: Supplies
```

### 4.4 Simplified AAR

**File**: `src/clone_wars/engine/state.py`

Replace complex `AfterActionReport` with simpler version:
```python
@dataclass(frozen=True)
class RaidReport:
    outcome: str  # "VICTORY" or "DEFEAT"
    reason: str  # Why this outcome
    target: OperationTarget
    ticks: int
    your_casualties: int
    enemy_casualties: int
    your_remaining: dict
    enemy_remaining: dict
    supplies_used: Supplies
    key_moments: list[str]  # 3-5 key events from combat
```

---

## 5. Files to Modify

### 5.1 Engine Layer

| File | Changes |
|------|---------|
| `engine/state.py` | Replace `EnemyPackage` with `EnemyForce`, add `execute_raid()` method, simplify/remove old resolver |
| `engine/ops.py` | Keep `OperationTarget` enum, REMOVE phase decision classes or mark deprecated |
| `engine/types.py` | No changes needed |
| `engine/scenario.py` | Update `load_game_state()` to parse new enemy format |
| `engine/combat.py` | **NEW FILE** - Combat loop, power calculation, tick simulation |

### 5.2 Data Layer

| File | Changes |
|------|---------|
| `data/scenario.json` | Replace enemy `strength_range` with actual troop counts |

### 5.3 Web Layer

| File | Changes |
|------|---------|
| `web/console_controller.py` | Add `btn-raid` handler, remove/bypass phase flow |
| `web/render/viewmodels.py` | Update `console_vm` for raid button, update AAR display |
| `web/templates/panels/console.html` | No template changes needed (data-driven) |
| `web/templates/panels/aar.html` | Update to show new raid report format |
| `web/templates/panels/enemy_intel.html` | Show troop estimates instead of strength range |

---

## 6. Detailed Implementation Steps

### Step 1: Create Combat Module

**Create** `src/clone_wars/engine/combat.py`:

```python
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clone_wars.engine.state import GameState

from clone_wars.engine.types import Supplies


@dataclass(frozen=True, slots=True)
class CombatTick:
    tick: int
    your_power: float
    enemy_power: float
    your_cohesion: float
    enemy_cohesion: float
    your_casualties: int
    enemy_casualties: int
    event: str


@dataclass(frozen=True, slots=True)
class CombatResult:
    outcome: str
    reason: str
    ticks: int
    your_casualties_total: int
    enemy_casualties_total: int
    your_remaining: dict
    enemy_remaining: dict
    tick_log: list[CombatTick]
    supplies_consumed: Supplies


def calculate_power(
    infantry: int,
    walkers: int,
    support: int,
    cohesion: float,
    supply_modifier: float = 1.0,
    fortification: float = 1.0,
) -> float:
    """Calculate combat power for a force."""
    base_power = (infantry * 1.0) + (walkers * 5.0) + (support * 0.5)
    return base_power * cohesion * supply_modifier * fortification


def get_supply_modifier(supplies: Supplies, ammo_needed: int, fuel_needed: int) -> float:
    """Calculate supply effectiveness modifier (0.5 to 1.0)."""
    ammo_ratio = min(1.0, supplies.ammo / max(1, ammo_needed))
    fuel_ratio = min(1.0, supplies.fuel / max(1, fuel_needed))
    # Average of both, with floor at 0.5
    return max(0.5, (ammo_ratio + fuel_ratio) / 2)


def execute_raid(state: GameState, rng: random.Random) -> CombatResult:
    """
    Execute a raid operation as tick-based combat.
    
    Returns CombatResult with full breakdown.
    """
    # Get starting forces
    tf = state.task_force
    enemy = state.planet.enemy
    
    # Initialize combat state
    your_infantry = tf.composition.infantry
    your_walkers = tf.composition.walkers
    your_support = tf.composition.support
    your_cohesion = tf.readiness  # Start cohesion = readiness
    
    enemy_infantry = enemy.infantry
    enemy_walkers = enemy.walkers
    enemy_support = enemy.support
    enemy_cohesion = enemy.cohesion
    
    # Supply costs for raid
    ammo_cost = 50
    fuel_cost = 30
    med_cost = 15
    
    supply_mod = get_supply_modifier(tf.supplies, ammo_cost, fuel_cost)
    
    # Combat loop
    max_ticks = 12  # Raids are short
    tick_log: list[CombatTick] = []
    your_casualties_total = 0
    enemy_casualties_total = 0
    
    base_damage_rate = 0.08  # 8% cohesion damage per balanced tick
    casualty_rate = 0.02  # 2% of damage becomes casualties
    
    for tick in range(1, max_ticks + 1):
        # Calculate current power
        your_power = calculate_power(
            your_infantry, your_walkers, your_support,
            your_cohesion, supply_mod
        )
        enemy_power = calculate_power(
            enemy_infantry, enemy_walkers, enemy_support,
            enemy_cohesion, fortification=enemy.fortification
        )
        
        # Avoid division by zero
        if your_power <= 0 or enemy_power <= 0:
            break
        
        # Power ratio determines damage
        your_advantage = your_power / enemy_power
        enemy_advantage = enemy_power / your_power
        
        # Add small variance (5%)
        your_roll = rng.uniform(0.95, 1.05)
        enemy_roll = rng.uniform(0.95, 1.05)
        
        # Damage to cohesion
        damage_to_enemy_coh = base_damage_rate * your_advantage * your_roll
        damage_to_you_coh = base_damage_rate * enemy_advantage * enemy_roll
        
        enemy_cohesion = max(0, enemy_cohesion - damage_to_enemy_coh)
        your_cohesion = max(0, your_cohesion - damage_to_you_coh)
        
        # Casualties (proportional to cohesion damage)
        your_cas_this_tick = int(
            (your_infantry + your_walkers + your_support) 
            * damage_to_you_coh * casualty_rate
        )
        enemy_cas_this_tick = int(
            (enemy_infantry + enemy_walkers + enemy_support) 
            * damage_to_enemy_coh * casualty_rate
        )
        
        # Apply casualties (infantry takes most)
        your_inf_loss = min(your_infantry, int(your_cas_this_tick * 0.7))
        your_walk_loss = min(your_walkers, int(your_cas_this_tick * 0.2))
        your_sup_loss = min(your_support, int(your_cas_this_tick * 0.1))
        your_infantry -= your_inf_loss
        your_walkers -= your_walk_loss
        your_support -= your_sup_loss
        your_casualties_total += your_inf_loss + your_walk_loss + your_sup_loss
        
        enemy_inf_loss = min(enemy_infantry, int(enemy_cas_this_tick * 0.7))
        enemy_walk_loss = min(enemy_walkers, int(enemy_cas_this_tick * 0.2))
        enemy_sup_loss = min(enemy_support, int(enemy_cas_this_tick * 0.1))
        enemy_infantry -= enemy_inf_loss
        enemy_walkers -= enemy_walk_loss
        enemy_support -= enemy_sup_loss
        enemy_casualties_total += enemy_inf_loss + enemy_walk_loss + enemy_sup_loss
        
        # Generate event description
        if your_advantage > 1.2:
            event = "Your forces press the attack"
        elif enemy_advantage > 1.2:
            event = "Enemy resistance stiffens"
        else:
            event = "Exchange of fire"
        
        if enemy_cohesion < 0.4:
            event = "Enemy lines wavering"
        if your_cohesion < 0.4:
            event = "Your troops under heavy pressure"
        
        tick_log.append(CombatTick(
            tick=tick,
            your_power=round(your_power, 1),
            enemy_power=round(enemy_power, 1),
            your_cohesion=round(your_cohesion, 2),
            enemy_cohesion=round(enemy_cohesion, 2),
            your_casualties=your_cas_this_tick,
            enemy_casualties=enemy_cas_this_tick,
            event=event,
        ))
        
        # Check break conditions
        if enemy_cohesion < 0.2:
            outcome = "VICTORY"
            reason = f"Enemy broke at {int(enemy_cohesion * 100)}% cohesion after {tick} ticks"
            break
        if your_cohesion < 0.2:
            outcome = "DEFEAT"
            reason = f"Your force broke at {int(your_cohesion * 100)}% cohesion after {tick} ticks"
            break
    else:
        # Max ticks reached - stalemate, attacker withdraws
        outcome = "DEFEAT"
        reason = f"Raid stalled after {max_ticks} ticks, forced to withdraw"
    
    # Consume supplies
    supplies_consumed = Supplies(
        ammo=min(tf.supplies.ammo, ammo_cost),
        fuel=min(tf.supplies.fuel, fuel_cost),
        med_spares=min(tf.supplies.med_spares, med_cost),
    )
    
    return CombatResult(
        outcome=outcome,
        reason=reason,
        ticks=len(tick_log),
        your_casualties_total=your_casualties_total,
        enemy_casualties_total=enemy_casualties_total,
        your_remaining={
            "infantry": your_infantry,
            "walkers": your_walkers,
            "support": your_support,
        },
        enemy_remaining={
            "infantry": enemy_infantry,
            "walkers": enemy_walkers,
            "support": enemy_support,
        },
        tick_log=tick_log,
        supplies_consumed=supplies_consumed,
    )
```

### Step 2: Update EnemyPackage → EnemyForce

**File**: `src/clone_wars/engine/state.py`

Replace:
```python
@dataclass(slots=True)
class EnemyPackage:
    strength_min: float
    strength_max: float
    confidence: float
    fortification: float
    reinforcement_rate: float
```

With:
```python
@dataclass(slots=True)
class EnemyForce:
    # Actual troops
    infantry: int
    walkers: int
    support: int
    
    # Combat state
    cohesion: float  # 0.0-1.0
    
    # Modifiers
    fortification: float
    reinforcement_rate: float
    
    # Intel
    intel_confidence: float  # What player knows (affects displayed estimates)
```

### Step 3: Update Scenario Loading

**File**: `src/clone_wars/engine/scenario.py`

Update `load_game_state()` to parse new enemy format:
```python
enemy_data = _require_dict(planet, "enemy")
state.planet.enemy = EnemyForce(
    infantry=int(enemy_data.get("infantry", 100)),
    walkers=int(enemy_data.get("walkers", 2)),
    support=int(enemy_data.get("support", 1)),
    cohesion=float(enemy_data.get("cohesion", 1.0)),
    fortification=float(enemy_data.get("fortification", 1.0)),
    reinforcement_rate=float(enemy_data.get("reinforcement_rate", 0.1)),
    intel_confidence=float(enemy_data.get("intel_confidence", 0.7)),
)
```

Update `data/scenario.json`:
```json
{
  "seed": 1,
  "planet": {
    "name": "Key Planet",
    "objectives": [
      {"id": "foundry", "name": "Droid Foundry"},
      {"id": "comms", "name": "Communications Array"},
      {"id": "power", "name": "Power Plant"}
    ],
    "enemy": {
      "infantry": 150,
      "walkers": 4,
      "support": 2,
      "cohesion": 1.0,
      "fortification": 1.2,
      "reinforcement_rate": 0.1,
      "intel_confidence": 0.7
    }
  }
}
```

### Step 4: Add Raid Execution to GameState

**File**: `src/clone_wars/engine/state.py`

Add method to `GameState`:
```python
from clone_wars.engine.combat import execute_raid, CombatResult

def raid(self, target: OperationTarget) -> CombatResult:
    """Execute a raid on the target. Returns combat result."""
    result = execute_raid(self, self.rng)
    
    # Apply results to game state
    # Update your forces
    self.task_force.composition.infantry = result.your_remaining["infantry"]
    self.task_force.composition.walkers = result.your_remaining["walkers"]
    self.task_force.composition.support = result.your_remaining["support"]
    
    # Consume supplies
    self.task_force.supplies = Supplies(
        ammo=self.task_force.supplies.ammo - result.supplies_consumed.ammo,
        fuel=self.task_force.supplies.fuel - result.supplies_consumed.fuel,
        med_spares=self.task_force.supplies.med_spares - result.supplies_consumed.med_spares,
    )
    
    # Update enemy forces
    self.planet.enemy.infantry = result.enemy_remaining["infantry"]
    self.planet.enemy.walkers = result.enemy_remaining["walkers"]
    self.planet.enemy.support = result.enemy_remaining["support"]
    
    # Update readiness based on fight intensity
    casualty_ratio = result.your_casualties_total / max(1, 
        self.task_force.composition.infantry + 
        self.task_force.composition.walkers + 
        self.task_force.composition.support + 
        result.your_casualties_total
    )
    readiness_drop = min(0.3, casualty_ratio * 2)
    self.task_force.readiness = max(0.3, self.task_force.readiness - readiness_drop)
    
    # Store result for AAR display
    self.last_raid_result = result
    
    # Apply strategic consequences
    if result.outcome == "VICTORY":
        self.planet.control = min(1.0, self.planet.control + 0.05)
        self.planet.enemy.reinforcement_rate = max(0.0, 
            self.planet.enemy.reinforcement_rate - 0.02)
    else:
        self.planet.control = max(0.0, self.planet.control - 0.05)
        self.planet.enemy.fortification = min(2.0, 
            self.planet.enemy.fortification + 0.1)
    
    return result
```

### Step 5: Update Console Controller

**File**: `src/clone_wars/web/console_controller.py`

Add handler for raid button:
```python
elif action_id == "btn-raid":
    if controller.target is None:
        self._set_message("SELECT A TARGET FIRST", "error")
        return dirty
    
    result = state.raid(controller.target)
    self.mode = "raid_result"
    self._set_message(f"RAID {result.outcome}", "accent" if result.outcome == "VICTORY" else "error")
    dirty.update({"taskforce", "enemy", "map"})

elif action_id == "btn-raid-ack":
    state.last_raid_result = None
    self.mode = "menu"
    controller.target = None
```

### Step 6: Update View Models

**File**: `src/clone_wars/web/render/viewmodels.py`

Update `console_vm` to show raid button in sector mode:
```python
elif mode == "sector":
    # ... existing sector briefing code ...
    
    line("OPERATIONS", "title")
    action("btn-raid", "[R] EXECUTE RAID", "accent")
    action("btn-sector-back", "[Q] BACK", "muted")

elif mode == "raid_result":
    result = state.last_raid_result
    if result is None:
        line("NO RAID RESULT.", "alert")
    else:
        outcome_kind = "success" if result.outcome == "VICTORY" else "failure"
        line(f"RAID {result.outcome}", "title")
        line(result.reason, "muted")
        line("")
        line("CASUALTIES", "title")
        line(f"YOUR LOSSES: {result.your_casualties_total}", "muted")
        line(f"ENEMY LOSSES: {result.enemy_casualties_total}", "muted")
        line("")
        line("REMAINING FORCES", "title")
        line(f"YOU: {result.your_remaining['infantry']}I / {result.your_remaining['walkers']}W / {result.your_remaining['support']}S", "muted")
        line(f"ENEMY: {result.enemy_remaining['infantry']}I / {result.enemy_remaining['walkers']}W / {result.enemy_remaining['support']}S", "muted")
    
    action("btn-raid-ack", "[ACKNOWLEDGE]", "accent")
```

Update `enemy_intel_vm` to show troop estimates:
```python
def enemy_intel_vm(state: GameState, controller: ConsoleController) -> dict:
    enemy = state.planet.enemy
    conf = enemy.intel_confidence
    
    # Fuzzy estimates based on confidence
    def estimate(actual: int, confidence: float) -> str:
        variance = int(actual * (1.0 - confidence) * 0.5)
        low = max(0, actual - variance)
        high = actual + variance
        if confidence > 0.9:
            return str(actual)
        return f"{low}-{high}"
    
    return {
        "infantry_est": estimate(enemy.infantry, conf),
        "walkers_est": estimate(enemy.walkers, conf),
        "support_est": estimate(enemy.support, conf),
        "confidence_pct": int(conf * 100),
        "fortification": f"{enemy.fortification:.2f}",
        "cohesion_pct": int(enemy.cohesion * 100),
    }
```

---

## 7. Testing Approach

### Unit Tests

**File**: `tests/test_combat.py` (NEW)

```python
import random
from clone_wars.engine.combat import calculate_power, execute_raid
from clone_wars.engine.state import GameState

def test_power_calculation():
    # 100 infantry + 2 walkers + 1 support = 100 + 10 + 0.5 = 110.5
    power = calculate_power(100, 2, 1, cohesion=1.0)
    assert power == 110.5

def test_power_with_cohesion():
    power = calculate_power(100, 2, 1, cohesion=0.5)
    assert power == 55.25  # Half cohesion = half power

def test_fortification_bonus():
    power = calculate_power(100, 0, 0, cohesion=1.0, fortification=1.5)
    assert power == 150.0  # 50% bonus

def test_raid_equal_forces_is_close():
    """With equal forces, outcome should be uncertain."""
    state = GameState.new(seed=42)
    # Set up equal forces
    state.task_force.composition.infantry = 100
    state.planet.enemy.infantry = 100
    state.planet.enemy.fortification = 1.0
    
    result = execute_raid(state, random.Random(42))
    # Should be close fight, not a blowout
    assert result.ticks >= 5

def test_superior_force_wins():
    """Significantly larger force should win."""
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 200
    state.planet.enemy.infantry = 50
    
    result = execute_raid(state, random.Random(42))
    assert result.outcome == "VICTORY"

def test_fortification_helps_defender():
    """High fortification should help defender."""
    # Test without fortification
    state1 = GameState.new(seed=42)
    state1.task_force.composition.infantry = 100
    state1.planet.enemy.infantry = 100
    state1.planet.enemy.fortification = 1.0
    result1 = execute_raid(state1, random.Random(42))
    
    # Test with high fortification
    state2 = GameState.new(seed=42)
    state2.task_force.composition.infantry = 100
    state2.planet.enemy.infantry = 100
    state2.planet.enemy.fortification = 1.5
    result2 = execute_raid(state2, random.Random(42))
    
    # Fortified defender should do better
    assert result2.your_casualties_total >= result1.your_casualties_total
```

### Integration Tests

Run the web app and manually test:
1. Click a sector on the map
2. Click "EXECUTE RAID"
3. Verify combat result shows
4. Verify casualties applied to both sides
5. Verify supplies consumed
6. Verify AAR display

---

## 8. Migration Notes

### Backward Compatibility

The old phase-based system (`OperationPlan`, `Phase1Decisions`, etc.) can remain in the codebase but unused. This allows:
- Gradual migration
- Easy rollback if needed
- Future re-introduction of tactical choices

### What Gets Deprecated (Not Deleted)

- `OperationPlan` class
- `Phase1Decisions`, `Phase2Decisions`, `Phase3Decisions`
- `ActiveOperation` state machine
- Phase-related console modes (`plan:axis`, `plan:prep`, etc.)
- Old `_resolve_operation` method

### Future Enhancements (Not In This Sprint)

Once the core raid works:
1. Add Campaign and Siege variants (longer, different tick counts)
2. Re-introduce tactical choices that affect combat modifiers
3. Add terrain modifiers
4. Add equipment/weapon modifiers
5. Add per-tick decision points (commit reserves, call retreat, etc.)

---

## 9. Acceptance Criteria

The implementation is complete when:

1. ✅ Player can click a sector → "EXECUTE RAID" → see combat result
2. ✅ Combat shows tick-by-tick breakdown
3. ✅ Both sides have actual troop counts that change
4. ✅ Cohesion degrades until one side breaks
5. ✅ Casualties are applied to both sides permanently
6. ✅ Supplies are consumed
7. ✅ Superior force wins (all else equal)
8. ✅ Fortification gives defender advantage
9. ✅ AAR explains outcome clearly
10. ✅ Game state reflects combat results after

---

## 10. File Checklist

| File | Action | Priority |
|------|--------|----------|
| `src/clone_wars/engine/combat.py` | CREATE | 1 |
| `src/clone_wars/engine/state.py` | MODIFY (EnemyForce, raid method) | 2 |
| `src/clone_wars/engine/scenario.py` | MODIFY (parse new enemy format) | 3 |
| `src/clone_wars/data/scenario.json` | MODIFY (new enemy structure) | 3 |
| `src/clone_wars/web/console_controller.py` | MODIFY (raid button handler) | 4 |
| `src/clone_wars/web/render/viewmodels.py` | MODIFY (raid result display) | 5 |
| `src/clone_wars/web/templates/panels/enemy_intel.html` | MODIFY (show troop estimates) | 6 |
| `tests/test_combat.py` | CREATE | 7 |

---

## 11. Summary

This plan replaces the abstract modifier-based battle system with a real force-on-force simulation where:

- **Both sides have troops** that can die
- **Combat runs as ticks** with damage exchange each round
- **Cohesion is the break meter** — when it hits 20%, that side retreats
- **Power = troops × cohesion × modifiers** — simple, transparent
- **AAR shows exactly what happened** — tick by tick, with final casualties

The player experience changes from "fill out a form, wait, get result" to "commit forces, watch simulation, understand outcome."
