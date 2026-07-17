# AI Agents Architecture

RescueNet AI utilizes 12 distinct AI agents, orchestrated by a central Supervisor node. Each agent is responsible for a highly specific domain of the disaster response.

## Agent Specifications

| Agent | Purpose | Reasoning Engine | Input State | Output Constraint | External Tooling |
|:---|:---|:---|:---|:---|:---|
| **Supervisor** | Orchestrates graph execution and handles reflection | Deterministic | `GraphState` | `List[NextNodes]` | None |
| **PlanCritic** | Critic node for reflection and replanning | Groq Llama-3 8B | `GraphState` | `APPROVE` / `REJECT` | Mock Validation |
| **Event Detection** | Classifies disaster triggers | Groq Llama-3 8B | `DisasterTriggerRequest` | `DisasterEvent` | `geocode_location` |
| **Damage Assessment** | Simulates spatial damage intensity | Groq Llama-3 70B | `DisasterEvent` | `List[DamageReport]` | `query_osm_overpass` |
| **Prioritization** | Triages damage severity vs targets | Groq Llama-3 8B | `List[DamageReport]` | `List[PriorityItem]` | `fetch_vulnerability`|
| **Resource Allocation**| Pairs transport fleet to targets | Groq Llama-3 70B | `List[PriorityItem]` | `List[ResourceAssignment]`| `calculate_eta` |
| **Route Optimization** | Adjusts routing for blocked roads | Groq Llama-3 8B | `List[ResourceAssignment]` | `List[RouteInfo]` | `fetch_live_traffic` |
| **Hospital Capacity** | Routes casualties to empty beds | Groq Llama-3 8B | `List[DamageReport]` | `List[HospitalAssignment]`| `fetch_telemetry` |
| **Shelter Allocation** | Routes displaced persons | Groq Llama-3 8B | `List[DamageReport]` | `List[ShelterAssignment]` | `check_conditions`|
| **Volunteer Coord.** | Matches civic skills to target needs | Groq Llama-3 70B | `List[PriorityItem]` | `List[VolunteerAssignment]`| `waiver_status` |
| **Communication** | Generates multilingual public alerts | Groq Llama-3 70B | `List[ShelterAssignment]` | `List[Alert]` | `sms_gateway` |
| **Prediction (ReAct)**| Extrapolates disaster spread rates | Groq Llama-3 8B | `List[DamageReport]` | `List[Forecast]` | `fetch_weather` |
| **Situation Report** | Synthesizes final executive summary | Groq Llama-3 70B | `GraphState` (All) | `String (Markdown)` | `historical_data` |

## Agent Design Patterns

### 1. The ReAct Pattern (Prediction Agent)
The Prediction Agent implements a true Tool-Calling ReAct loop:
1. Receives the `GraphState`.
2. Evaluates the LLM context.
3. Decides to call the `fetch_weather_forecast` tool.
4. Pauses execution, executes the simulated Python function, and binds the result to `ToolMessage`.
5. Passes the combined history back to the LLM to generate the final `ForecastList`.

### 2. The Structured Output Pattern (All Agents)
To ensure the DAG does not crash, we strictly enforce schema boundaries:
```python
structured_llm = self.llm.with_structured_output(ResourceAssignmentList)
result = structured_llm.invoke(prompt)
```
If the LLM hallucinates an invalid schema, LangChain throws a parsing error, triggering the `tenacity` retry loop.

### 3. The Fallback Pattern (Resilience)
If the Groq API key is missing, or the LLM is experiencing an outage, every agent possesses a deterministic fallback:
```python
if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
    return self._legacy_forecast(event, damage_reports)
```
This guarantees the pipeline completes 100% of the time, regardless of API stability.
