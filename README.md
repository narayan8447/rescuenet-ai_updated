# RescueNet AI — Disaster Response Multi-Agent System

An academic project implementing the **RescueNet AI** architecture: an autonomous
multi-agent AI command center that coordinates disaster response across rescue
teams, hospitals, shelters, relief supplies, and volunteers — instead of every
agency working independently.

Built **entirely in Python**:
- **Backend**: FastAPI, hosting 12 independent agent modules coordinated by an
  Orchestrator Agent.
- **Frontend**: Streamlit dashboard (also pure Python — no HTML/JS needed).
- **Storage**: SQLite for incident history (long-term memory), in-memory state
  for live resource availability (mirrors the brief's Redis role).

This is a **working simulation**, not a production system — there are no real
satellite feeds or trained ML models plugged in. Every agent is built so that
its rule-based/simulated logic can be swapped for a real model (YOLO, LSTM,
XGBoost, etc.) without changing the pipeline shape. See "Extending with real
AI models" below.

---

## 1. Project Structure

```
rescuenet-ai/
├── backend/
│   ├── main.py                      # FastAPI app + routes
│   ├── database.py                  # SQLite (history) + in-memory live state
│   ├── utils.py                      # haversine distance, geo jitter, seeded RNG
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py               # Pydantic schemas (shared data contracts)
│   ├── data/
│   │   └── simulated_data.py        # Hospitals, shelters, resources, volunteers, POIs
│   └── agents/
│       ├── graph_state.py           # LangGraph State Definition
│       ├── stubs.py                 # LangGraph Node Wrappers
│       ├── supervisor_v2.py         # LangGraph Supervisor Agent
│       ├── event_detection.py       # Agent 1
│       ├── damage_assessment.py     # Agent 2
│       ├── rescue_prioritization.py # Agent 3
│       ├── resource_allocation.py   # Agent 4
│       ├── route_optimization.py    # Agent 5
│       ├── hospital_capacity.py     # Agent 6
│       ├── shelter_allocation.py    # Agent 7
│       ├── relief_distribution.py   # Agent 8
│       ├── volunteer_coordination.py# Agent 9
│       ├── communication.py         # Agent 10
│       ├── situation_reporting.py   # Agent 11
│       ├── prediction.py            # Agent 12
│       └── orchestrator.py          # Legacy sequential orchestrator
├── frontend/
│   ├── app.py                       # Streamlit command dashboard
│   └── requirements.txt
├── requirements.txt                  # Combined (backend + frontend)
└── README.md
```

## 2. How to Run (VS Code)

1. Open the `rescuenet-ai` folder in VS Code.
2. Open a terminal and create a virtual environment (recommended):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Start the backend** (Terminal 1, from the project root):
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   - API docs available at http://127.0.0.1:8000/docs (Swagger UI — great for
     testing/demoing each endpoint independently, e.g. for a viva/demo).
5. **Start the frontend** (Terminal 2, from the project root):
   ```bash
   streamlit run frontend/app.py
   ```
   - Dashboard opens automatically at http://localhost:8501

6. In the dashboard sidebar: pick a disaster type and location, then click
   **"Trigger Disaster Response Pipeline"**. Watch all 12 agents run and
   populate the dashboard.

> Both processes must be running at the same time — FastAPI is the "brain",
> Streamlit is the "face".

## 3. How the Pipeline Works

Matches the workflow diagram in the project brief:

```
Event Detection → Damage Assessment → Rescue Prioritization →
Resource Allocation → Route Optimization → Hospital Capacity →
Shelter Allocation → Relief Distribution → Volunteer Coordination →
Communication → Prediction → Situation Reporting
```

Each agent is a plain Python function that takes the previous agents'
structured output (Pydantic models) and returns new structured output. The
**Orchestrator Agent** (`backend/agents/orchestrator.py`) calls them all in
order, mutates the shared live state (hospital beds fill up, resources get
dispatched and become unavailable, shelter capacity drops), and records a
full trace for transparency — this trace is what the "Agent-by-Agent Trace"
section in the dashboard shows.

## 4. Data & Memory Architecture

| Brief's concept        | This project's implementation                          |
|-------------------------|---------------------------------------------------------|
| Short-term memory        | In-memory `STATE` dict in `backend/database.py`         |
| Long-term memory / SOPs  | SQLite `rescuenet.db` (created automatically) storing every past incident + its full situation report |
| PostgreSQL (citizens, hospitals, shelters, resources) | `backend/data/simulated_data.py` |
| Redis (live resource availability) | In-memory mutation of the same `STATE` dict during a pipeline run |
| Vector DB / RAG over SOPs | Not implemented in this version — see "Extending" below |

## 5. Extending With Real AI Models

Every agent function is intentionally isolated so a real model can be dropped
in without touching the orchestrator or the frontend:

- **Event Detection** → replace the validation logic with an NLP classifier
  over emergency-call transcripts (Whisper) + social media text.
- **Damage Assessment** → replace the simulated severity numbers with a
  YOLO/SAM/SegFormer inference step over real satellite/drone imagery.
- **Resource Allocation / Route Optimization** → swap the greedy
  nearest-match for an OR-Tools optimization model or real A*/Dijkstra over
  an OpenStreetMap road graph.
- **Prediction Agent** → replace the linear extrapolation with a trained
  LSTM/XGBoost model on historical disaster + weather data.
- **RAG over SOPs** → add a vector DB (e.g. Qdrant, as named in the brief),
  embed NDRF/WHO/government SOP documents, and have the Communication /
  Situation Reporting agents query it before generating text.

Because every agent returns a typed Pydantic object, none of these swaps
require changing any other file — only the internals of that one agent
module.

## 6. Notes for Submission

- This is a **simulation and prototype**, useful for demonstrating multi-agent
  orchestration, not a real-world-ready emergency system.
- All location data defaults to Delhi NCR coordinates (matching the flood
  example in the original brief) but any lat/lon can be entered.
- Re-running the same disaster type + location produces the same "random"
  damage numbers (seeded RNG) so results are reproducible for a demo/viva.
