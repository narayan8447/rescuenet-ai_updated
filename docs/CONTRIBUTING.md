# Contributing to RescueNet AI

We welcome contributions from the open-source AI community! Whether you are an AI researcher wanting to plug in a new reasoning model or a backend engineer optimizing the Redis locks, your help is appreciated.

## 1. Development Setup

1. **Fork & Clone**: Fork the repo and clone it locally.
2. **Environment**: We recommend Python 3.12+. Create a virtual environment (`python -m venv venv`).
3. **Install Dependencies**: `pip install -r requirements.txt`.
4. **Pre-commit Hooks**: (Optional) Install `flake8` and `black` to ensure code formatting matches our CI pipeline.

## 2. Pull Request Process

1. **Branching**: Create a feature branch (`git checkout -b feature/your-feature-name`).
2. **Testing**: You must write tests for any new agents or graph logic. Run the test suite:
   ```bash
   pytest tests/ -v
   ```
3. **Code Coverage**: We require 90%+ code coverage for `backend/core/` and `backend/agents/`.
4. **Documentation**: Update the relevant markdown files in `docs/` if your change modifies the architecture.
5. **Review**: Submit a PR to `main`. An automated GitHub Action will run tests and linters.

## 3. Adding a New Agent

If you want to add a new LangChain agent to the pipeline:
1. Create `backend/agents/your_agent.py` implementing `BaseAgent`.
2. Add your Agent's output schema to `backend/models/schemas.py`.
3. Register the agent in `backend/agents/stubs.py`.
4. Update the Supervisor routing logic in `backend/agents/supervisor_v2.py`.
5. Update `docs/AI_AGENTS.md`.
