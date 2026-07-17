# Security & Compliance

RescueNet AI is designed to handle sensitive civic data, simulated PII (Personally Identifiable Information), and critical infrastructure controls.

## 1. Network Security

- **CORS Policy**: The FastAPI backend strictly limits Cross-Origin Resource Sharing. By default, it only accepts requests from the exact origin of the Streamlit dashboard (`http://localhost:8501`), blocking external spoofing attempts.
- **Secure Headers**: The `secure` library is integrated into the ASGI pipeline to automatically attach OWASP-recommended headers (HSTS, X-Frame-Options, X-XSS-Protection).

## 2. API Security

- **Rate Limiting**: `slowapi` is implemented on all endpoints. The `/api/disaster/trigger` endpoint is strictly limited to 2 requests per minute per IP to prevent LLM abuse and cost overruns.
- **API Keys**: All LLM inference requires a `GROQ_API_KEY`. This key is never passed to the frontend; it is securely bound to the backend environment variables.

## 3. Distributed Locking

In a multi-agent environment, "security" also means "state integrity."
- **Redis Memory Manager**: Implements distributed locks. Without this, malicious or buggy parallel agents could simultaneously claim the same physical resource (e.g., dispatching one ambulance to two locations). The lock ensures ACID-like compliance on the global `Live State`.

## 4. Human-in-the-Loop (HITL)

RescueNet AI prevents autonomous LLM hallucination from executing physical actions.
- The LangGraph DAG is hard-coded to pause at `interrupt_before=["resource_allocation", "communication"]`.
- The graph cannot proceed until an authenticated human operator manually calls `/api/workflow/approve`.
