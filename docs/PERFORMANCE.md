# Performance & Observability

Enterprise AI platforms must maintain low latency while executing highly complex, parallelized LLM chains.

## 1. Parallel Execution

The shift from sequential execution to a LangGraph DAG drastically reduced total pipeline latency.
- Tasks like `HospitalCapacity`, `ShelterAllocation`, `VolunteerCoordination`, and `RouteOptimization` execute simultaneously.
- **Latency Gain**: Reduces execution time of this block from ~15 seconds (sequential) to ~4 seconds (parallel).

## 2. Caching Strategy

- **FastAPI Cache**: Integrated `fastapi-cache2` using a `RedisBackend`.
- Read-heavy endpoints (like fetching available resources for the UI) are cached for 30 seconds.
- This prevents the UI from hammering the simulation database on every re-render.

## 3. Observability (OpenTelemetry)

RescueNet AI utilizes `opentelemetry-instrumentation-fastapi`.
- **Tracing**: Every HTTP request is wrapped in an OTel span.
- **Datadog / Jaeger Integration**: These traces can be effortlessly exported to enterprise APMs to track bottleneck nodes in the LangGraph pipeline.

## 4. Structured Metrics

The `backend.core.logging.StructuredLogger` emits metric events:
```json
{"level": "METRIC", "metric_name": "agent_start", "value": 1.0, "tags": {"agent": "rescue_prioritization"}}
```
These logs are parsed by the Streamlit frontend to construct the real-time execution timeline and the agent token/latency counters.
