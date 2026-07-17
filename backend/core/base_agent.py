from abc import ABC, abstractmethod
from typing import Dict, Any
from backend.core.state import GraphState
from backend.core.errors import AgentExecutionError, with_retry

class BaseAgent(ABC):
    """Abstract base class for all V2 agents in the RescueNet AI system."""
    
    name: str = "BaseAgent"
    
    @abstractmethod
    def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Core logic of the agent. Must return a dictionary representing
        state updates to be merged into the LangGraph state.
        """
        pass
        
    @with_retry()
    def safe_execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Wraps the execute method with standardized retry logic and error handling.
        """
        try:
            result = self.execute(state)
            
            # Ensure we track completion to prevent infinite loops in the supervisor
            # LangGraph will use operator.add to append this to the existing list
            result["completed_tasks"] = [self.name]
            
            return result
        except Exception as e:
            raise AgentExecutionError(f"{self.name} failed during execution: {str(e)}") from e
