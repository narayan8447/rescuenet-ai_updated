# Inter-Agent Communication Protocol (IACP)

RescueNet AI implements a standardized JSON envelope for agent-to-agent and agent-to-dashboard communication.

## Protocol Structure

```json
{
  "protocol_version": "1.0",
  "message_id": "uuid-1234",
  "correlation_id": "uuid-5678",
  "sender": "damage_assessment",
  "receiver": "rescue_prioritization",
  "message_type": "DATA_TRANSFER",
  "timestamp": "2024-03-15T12:00:00Z",
  "priority": "HIGH",
  "payload": {
    "reports": [
      { "location": "Sector A", "severity": 85 }
    ]
  },
  "metadata": {
    "model_used": "llama-3.1-8b-instant",
    "token_usage": 150,
    "latency_ms": 350
  }
}
```

## Streamlit SSE Formatting

When the backend streams logs to the frontend timeline, it wraps the LangGraph state transitions inside IACP structures.

1. **Agent Start**: Notifies the UI that an agent has begun reasoning.
2. **Agent Complete**: Contains the `metadata` metrics (tokens, latency) which Streamlit updates in its sidebar metric widgets.
3. **Routing Evaluation**: Broadcast by the Supervisor indicating which parallel nodes are scheduled next.
