import pytest
from backend.simulation.engine import SimulationEngine

def test_deterministic_simulation():
    # Run simulation 1
    engine1 = SimulationEngine(seed=42)
    engine1.step(5)
    state1 = engine1.get_state()
    
    # Run simulation 2 with same seed
    engine2 = SimulationEngine(seed=42)
    engine2.step(5)
    state2 = engine2.get_state()
    
    # Assert deterministic equality
    assert state1["weather"] == state2["weather"]
    assert state1["disaster_spread_radius_km"] == state2["disaster_spread_radius_km"]
    assert state1["traffic_congestion_index"] == state2["traffic_congestion_index"]

def test_hospital_capacity_degrades():
    engine = SimulationEngine(seed=100)
    # Fast forward many ticks to trigger spread and casualties
    engine.step(20)
    state = engine.get_state()
    
    # Ensure hospital beds went down
    total_beds = sum(h["general_beds"] for h in state["hospitals"])
    # Original total is 40 + 25 + 55 + 30 = 150
    assert total_beds < 150

def test_flood_spread_causes_damage():
    engine = SimulationEngine(seed=123)
    # High precipitation ensures flood logic triggers in engine
    # Force precipitation
    engine.state["weather"]["precipitation_mm"] = 50.0 
    engine.step(10)
    state = engine.get_state()
    
    # Check that at least some POIs have flooded status and damage
    flooded = [poi for poi in state["points_of_interest"] if poi["flooded"]]
    damaged = [poi for poi in state["points_of_interest"] if poi["damage_level"] != "none"]
    
    assert len(flooded) > 0
    assert len(damaged) > 0
