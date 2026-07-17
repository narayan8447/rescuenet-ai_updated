# Troubleshooting

Common issues and their resolutions when running RescueNet AI.

### 1. Agents return generic fallback data instead of LLM output
**Cause**: The `GROQ_API_KEY` is missing or invalid. The system has automatically triggered its resilience fallback pattern.
**Fix**: Ensure your `.env` file contains a valid `GROQ_API_KEY`.

### 2. Streamlit Dashboard is blank or says "Connection Refused"
**Cause**: The frontend cannot reach the backend API.
**Fix**: 
- If running locally (without Docker), ensure the FastAPI server is running (`uvicorn backend.main:app`).
- If using Docker, ensure `API_BASE=http://backend:8000` is set in the frontend's environment.

### 3. Redis Connection Errors
**Cause**: The backend is attempting to connect to Redis, but it is not running.
**Fix**: 
- Run `docker-compose up -d redis`.
- Or, for local development without Redis, set `USE_FAKE_REDIS=true` in your `.env` to fall back to the thread-safe in-memory singleton.

### 4. RAG Queries return empty results
**Cause**: The Qdrant database is empty.
**Fix**: Run the ingestion script: `python ingest_rag.py`. This will parse the local knowledge base and populate the vector DB.

### 5. `ModuleNotFoundError` during tests
**Cause**: Your `PYTHONPATH` is not set to the project root.
**Fix**: Run tests with `PYTHONPATH="." pytest tests/`.
