# Deployment Guide

RescueNet AI is containerized for seamless deployment across standard cloud providers.

## 1. Docker Compose (Local & Sandbox)

The easiest way to run the entire stack is via the provided `docker-compose.yml`.

```bash
docker-compose up --build -d
```
This spins up:
- `backend`: FastAPI server on port 8000.
- `frontend`: Streamlit dashboard on port 8501.
- `redis`: In-memory datastore on port 6379.
- `qdrant`: Vector database on port 6333.

## 2. Production Deployment (AWS / Azure)

For true high-availability production, split the services:

### 2.1 Managed Services
- **Database**: Use AWS ElastiCache (Redis) for the memory layer.
- **Vector DB**: Use Qdrant Cloud or AWS OpenSearch.

### 2.2 Backend Cluster (ECS / EKS)
Deploy the `Dockerfile.backend` image to ECS or Kubernetes.
- Ensure the load balancer supports long-lived connections for Server-Sent Events (SSE).
- Ensure `UVICORN_WORKERS` is set to utilize multi-core CPU instances.

### 2.3 Frontend Cluster
Deploy the `Dockerfile.frontend` image.
- Streamlit does not require horizontal scaling as heavily as the backend, but sticky sessions on the load balancer are highly recommended.

## 3. Environment Variables

| Variable | Description | Required |
|:---|:---|:---:|
| `GROQ_API_KEY` | Your Llama-3 inference key. | Yes |
| `API_BASE` | URL of the backend (e.g. `http://backend:8000`). | Yes |
| `REDIS_URL` | Redis connection string. | Yes |
| `QDRANT_URL` | Qdrant connection string. | Yes |
| `USE_FAKE_REDIS` | Set to `true` to bypass Redis and use local RAM (dev only). | No |
