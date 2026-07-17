# Simulation Engine

RescueNet AI is not just a static reasoning engine; it contains a deterministic time-series simulation engine to mock the physical reality of a disaster zone.

## Engine Mechanics (backend/simulation/engine.py)

The `SimulationEngine` runs in the background of the FastAPI server.

### 1. Tick System
The simulation progresses in "ticks" (e.g., 1 real second = 1 simulation hour). 
At each tick, the engine iterates over all active disaster events and applies deterministic mutations to the global state.

### 2. Weather & Spread Mechanics
- Depending on the `disaster_type`, the engine alters severity. For example, a `flood` might increase in severity if the mocked weather forecasts predict heavy rainfall.
- `Building Collapse` incidents might spawn secondary `Fire` incidents.

### 3. Resource Fatigue
- Deployed volunteers and vehicles accrue "fatigue" over time.
- If a resource exceeds its operational threshold without returning to a base, its efficiency drops, forcing the `ResourceAllocationAgent` to dynamically dispatch replacements in future LangGraph loops.

### 4. Integration with Agents
The Simulation Engine writes its mutated state directly to the `Live State` dictionary in `GraphState`. When the LangGraph Supervisor runs its next cycle, the agents read this new, degraded reality and adjust their plans accordingly.
