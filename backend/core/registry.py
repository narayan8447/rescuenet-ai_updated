from typing import Dict, Type
from backend.core.base_agent import BaseAgent
from backend.core.errors import DependencyResolutionError

class AgentRegistry:
    """
    Registry for managing agent lifecycle and dependency injection.
    """
    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, name: str, agent_instance: BaseAgent):
        """Register a new agent instance."""
        cls._agents[name] = agent_instance

    @classmethod
    def get(cls, name: str) -> BaseAgent:
        """Retrieve an agent instance by name."""
        agent = cls._agents.get(name)
        if not agent:
            raise DependencyResolutionError(f"Agent '{name}' not found in registry.")
        return agent
        
    @classmethod
    def list_agents(cls) -> list[str]:
        """List all registered agent names."""
        return list(cls._agents.keys())

    @classmethod
    def clear(cls):
        """Clear the registry (useful for testing)."""
        cls._agents.clear()
