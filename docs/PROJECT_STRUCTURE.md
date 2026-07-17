# Project Structure

A deep dive into the RescueNet AI directory tree.

```text
rescuenet-ai/
├── backend/
│   ├── main.py                      # Application entrypoint. Configures Uvicorn, CORS, Rate Limiting, and Caching.
│   ├── database.py                  # Manages SQLite history and in-memory dicts for live state.
│   ├── core/
│   │   ├── base_agent.py            # Abstract class dictating the execute() contract for all agents.
│   │   ├── logging.py               # Enterprise JSON structured logger.
│   │   ├── memory.py                # Redis lock manager and LangGraph checkpointer.
│   │   ├── registry.py              # Dependency Injection container for agents.
│   │   └── state.py                 # Pydantic schema for the global GraphState.
│   ├── rag/
│   │   ├── api.py                   # FastAPI routes for RAG search.
│   │   └── rag_engine.py            # SentenceTransformers, Qdrant Client, and Cross-Encoder re-ranker.
│   ├── simulation/
│   │   └── engine.py                # Deterministic background task that degrades disaster state over time.
│   ├── models/
│   │   └── schemas.py               # The single source of truth for all Pydantic IACP models.
│   └── agents/
│       ├── supervisor_v2.py         # The core LangGraph state machine and routing logic.
│       ├── stubs.py                 # LangChain node wrappers that parse state for legacy agents.
│       └── *.py                     # The specialized domain agents (Hospital, Route, Resource, etc).
├── frontend/
│   ├── app.py                       # The single-page Streamlit application.
│   └── requirements.txt
├── tests/                           # Pytest suite covering Supervisor, RAG, Memory, and Core logic.
├── docs/                            # (You are here)
├── Dockerfile.backend               # Multi-stage build for FastAPI.
├── Dockerfile.frontend              # Multi-stage build for Streamlit.
├── docker-compose.yml               # Orchestrates Backend, Frontend, Redis, and Qdrant.
└── ingest_rag.py                    # Script to seed the Qdrant database with chunks.
```
