
import pytest
from unittest.mock import MagicMock
from clone_wars.engine.state import GameState, LogisticsState, ProductionState, TaskForceState
from clone_wars.engine.types import LocationId, Supplies, UnitStock
from clone_wars.web.console_controller import ConsoleController
from clone_wars.web.render.viewmodels import situation_map_vm, logistics_vm

@pytest.fixture
def mock_state():
    state = MagicMock(spec=GameState)
    state.logistics = LogisticsState.new()
    state.production = MagicMock(spec=ProductionState)
    state.production.factories = 5
    state.production.capacity = 10
    state.production.jobs = []

    state.barracks = MagicMock()
    state.barracks.barracks = 3
    state.barracks.capacity = 15
    state.barracks.jobs = []
    
    state.task_force = MagicMock(spec=TaskForceState)
    state.front_supplies = Supplies(0, 0, 0)
    
    # Needs rules and objectives for vm
    state.rules = MagicMock()
    state.rules.objectives = {}
    
    # Contested planet
    state.contested_planet = MagicMock()
    # Configure Enemy Mock with int values
    enemy = MagicMock()
    enemy.intel_confidence = 0.5
    enemy.fortification = 1.0
    enemy.reinforcement_rate = 0.05
    enemy.infantry = 1000
    enemy.walkers = 50
    enemy.support = 20
    enemy.cohesion = 0.8
    state.contested_planet.enemy = enemy
    
    state.contested_planet.control = 0.5
    state.contested_planet.objectives = MagicMock()
    
    # Op / Raid
    state.operation = None
    state.raid_target = None
    
    # Config globals for logistics vm
    state.rules.globals = MagicMock()
    state.rules.globals.storage_risk_per_day = {}
    state.rules.globals.storage_loss_pct_range = {}
    
    return state

# ... (omitted)

def test_logistics_vm_structure(mock_state, controller):
    vm = logistics_vm(mock_state, controller)
    
    # Verify Depots List contains new nodes
    depot_names = [d["short"] for d in vm["depots"]]
    assert "SPACEPORT" in depot_names
    assert "MID DEPOT" in depot_names
    assert "FRONT" in depot_names
    
    # Verify Hull Constraints
    assert vm["constraints"]["hull_total"] > 0

@pytest.fixture
def controller():
    c = MagicMock(spec=ConsoleController)
    c.selected_node = None # Default
    c.target = None
    return c

def test_situation_map_default_view(mock_state, controller):
    vm = situation_map_vm(mock_state, controller)
    
    # 1. Verify System Strip
    assert len(vm["system_nodes"]) == 5
    assert vm["system_nodes"][0]["name"] == "CORE WORLDS"
    assert vm["system_nodes"][1]["name"] == "DEEP SPACE"
    assert vm["system_nodes"][2]["name"] == "CONTESTED SYSTEM"
    
    # 2. Verify Default Detail (Contested Spaceport)
    # Default selection is usually Spaceport or Core depending on impl.
    # We defaulted to CONTESTED_SPACEPORT in code.
    assert vm["detail"]["type"] == "contested"
    assert "logistics_chain" in vm["detail"]
    chain = vm["detail"]["logistics_chain"]
    assert len(chain) == 3
    assert chain[0]["name"] == "SPACEPORT"
    assert chain[1]["name"] == "MID_DEPOT"
    assert chain[2]["name"] == "FRONT"

def test_situation_map_core_selection(mock_state, controller):
    controller.selected_system_node = LocationId.NEW_SYSTEM_CORE
    vm = situation_map_vm(mock_state, controller)
    
    assert vm["detail"]["type"] == "core"
    assert vm["detail"]["title"] == "CORE INDUSTRIAL SECTOR"
    assert "factories" in vm["detail"]

def test_situation_map_deep_space_selection(mock_state, controller):
    controller.selected_system_node = LocationId.DEEP_SPACE
    vm = situation_map_vm(mock_state, controller)
    
    assert vm["detail"]["type"] == "deep_space"
    assert "ships" in vm["detail"]
    # Check if our ship from LogisticsState.new() is there
    # (LogisticsState.new puts ship at Core initially, but we show all friendly ships?)
    # The filter in vm shows: location==DEEP_SPACE or destination==DEEP_SPACE or location==CORE
    assert len(vm["detail"]["ships"]) > 0
    assert vm["detail"]["ships"][0]["name"] == "Ship 1"
