# Release Notes: v2.0.0 (Production Ready)

Welcome to the **RescueNet AI v2.0.0** release! This major update transitions RescueNet from a local academic simulation into a robust, production-ready enterprise command center.

## Core Features & Upgrades

### 1. Advanced AI Capabilities
- **Hybrid RAG Integration**: Integrated Qdrant Vector DB with Cross-Encoder re-ranking, providing the agents with authoritative disaster protocols (FEMA guidelines, safety manuals).
- **Human-in-the-Loop (HITL)**: Execution now pauses gracefully before executing critical tasks like *Resource Allocation* and *Communication*, allowing operators to review and approve life-saving decisions.
- **Deterministic Simulation Engine**: Replaced static dummy data with a dynamic simulation engine that models weather progression, disaster expansion, and resource degradation over time.

### 2. Enhanced Command Center UI
- **Live Agent Graph & Timeline**: The dashboard now renders a simulated streaming timeline of the LangGraph execution, exposing supervisor reasoning and individual node outputs in real time.
- **3D Geospatial Visualization**: Upgraded mapping using PyDeck. Added interactive Heatmap layers for damage severity and Arc layers to trace real-time resource routing.
- **Observability Metrics**: Added real-time tracking for Detection Confidence, RAG retrieval scores, execution latencies, and LLM token usage directly on the dashboard.

### 3. Production Infrastructure (DevOps)
- **Docker Orchestration**: Introduced isolated, multi-stage Dockerfiles (`Dockerfile.backend`, `Dockerfile.frontend`) managed by `docker-compose.yml`, which automatically spins up Redis and Qdrant alongside the application.
- **Gunicorn Workers**: The backend now runs with Uvicorn workers managed by Gunicorn, drastically improving concurrency and load handling.
- **Resilience & Security**:
  - Implemented `slowapi` for endpoint rate limiting to prevent DDOS.
  - Added `SecureHeaders` for HTTP response hardening against XSS and clickjacking.
  - Implemented `fastapi-cache2` on read-heavy state retrieval endpoints.
  - Built-in `/health` checkpoints for container orchestration.
- **CI/CD Automation**: Integrated a full GitHub Actions pipeline (`ci.yml`) to enforce testing, linting, code coverage (`pytest-cov`), and Docker build verification on every push.

---
**Deployment:**
To run the fully orchestrated v2 stack locally:
```bash
docker-compose up --build
```
