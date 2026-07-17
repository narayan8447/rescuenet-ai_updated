from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RescueNetError(Exception):
    """Base exception for all RescueNet errors."""
    pass

class AgentExecutionError(RescueNetError):
    """Raised when an agent fails to execute its logic."""
    pass

class StateValidationError(RescueNetError):
    """Raised when the GraphState is invalid or missing required data."""
    pass

class DependencyResolutionError(RescueNetError):
    """Raised when the AgentRegistry cannot resolve a dependency."""
    pass

def with_retry():
    """
    Retry framework decorator. 
    Applies exponential backoff for transient failures in agent execution.
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AgentExecutionError),
        reraise=True
    )
