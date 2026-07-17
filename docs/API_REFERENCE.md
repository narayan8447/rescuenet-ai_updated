# API Reference

The backend exposes a fully documented OpenAPI specification accessible at `/docs` when the server is running. Below are the core orchestrator endpoints.

## 1. Trigger Disaster Workflow

**POST** `/api/disaster/trigger`

Initiates the LangGraph multi-agent pipeline.

**Request Body:**
```json
{
  "disaster_type": "flood",
  "location_name": "Delhi NCR",
  "lat": 28.6139,
  "lon": 77.2090
}
```

**Response:**
Returns a Server-Sent Events (SSE) stream yielding `IACP` message payloads detailing node execution, tool usage, and final markdown summaries.

## 2. Approve HITL Checkpoint

**POST** `/api/workflow/approve/{thread_id}`

Resumes a paused LangGraph execution after human validation.

**Request Body:**
```json
{
  "approved": true,
  "feedback": "Proceed with allocations."
}
```

**Response:**
```json
{
  "status": "resumed",
  "thread_id": "uuid-1234"
}
```

## 3. RAG Search

**POST** `/api/rag/search`

Queries the knowledge base directly.

**Request Body:**
```json
{
  "query": "What is the FEMA protocol for immediate flood evacuation?",
  "limit": 5
}
```

**Response:**
Returns an array of context chunks with their cross-encoder relevancy scores.
