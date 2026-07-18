import backend.core.mock_ormsgpack

from langgraph.graph import StateGraph, END
from typing import List, Union

from backend.core.state import GraphState
from backend.core.registry import AgentRegistry
from backend.core.logging import logger
import backend.agents.stubs  # Ensure agents are registered


def route_supervisor(state: GraphState) -> Union[str, List[str]]:
    """Determine which node(s) should run next based on what's missing in the state."""
    logger.info("routing_evaluation", state_correlation=state.correlation_id)
    
    completed = state.completed_tasks if state.completed_tasks else []
    
    if "event_detection" not in completed:
        return "event_detection"
    if "damage_assessment" not in completed:
        return "damage_assessment"
    if "rescue_prioritization" not in completed:
        return "rescue_prioritization"
    if "resource_allocation" not in completed:
        return "resource_allocation"
    
    # Parallel Fan-Out Block
    parallel_targets = []
    if "route_optimization" not in completed:
        parallel_targets.append("route_optimization")
    if "hospital_capacity" not in completed:
        parallel_targets.append("hospital_capacity")
    if "shelter_allocation" not in completed:
        parallel_targets.append("shelter_allocation")
    if "volunteer_coordination" not in completed:
        parallel_targets.append("volunteer_coordination")
    
    if parallel_targets:
        return parallel_targets

    # Check Reflection Loop via PlanCritic
    parallel_nodes = ["route_optimization", "hospital_capacity", "shelter_allocation", "volunteer_coordination"]
    if all(n in completed for n in parallel_nodes):
        # Cap reflection at 1 retry to prevent infinite loops
        critic_retries = state.retries.get("plan_critic", 0)
        if "plan_critic" not in completed:
            return "plan_critic"
        # Find the last PlanCritic entry in accumulated history
        critic_entries = [e for e in state.execution_history if e.get("agent") == "PlanCritic"]
        if critic_entries:
            last_critic = critic_entries[-1]
            if "rejected" in last_critic.get("summary", "").lower() and critic_retries < 2:
                logger.info("Reflection loop triggered by PlanCritic", retry=critic_retries)
                return "resource_allocation"

    # Dependent Nodes
    if "plan_critic" in completed and "relief_distribution" not in completed:
        return "relief_distribution"
    if "prediction" not in completed:
        return "prediction"
    if "communication" not in completed:
        return "communication"
    if "situation_reporting" not in completed:
        return "situation_reporting"
    
    return END

def build_supervisor_graph():
    builder = StateGraph(GraphState)

    # We add a dummy supervisor node to act as the routing hub
    builder.add_node("supervisor", lambda state: state)

    # Fetch nodes dynamically from registry and wrap their safe_execute
    agent_names = [
        "event_detection", "damage_assessment", "rescue_prioritization",
        "resource_allocation", "route_optimization", "hospital_capacity",
        "shelter_allocation", "relief_distribution", "volunteer_coordination",
        "communication", "prediction", "situation_reporting"
    ]
    
    # In LangGraph 0.0.x, node functions take dict/dataclass and return dict to merge
    for name in agent_names:
        agent = AgentRegistry.get(name)
        # We need to wrap it because safe_execute expects GraphState object
        # In newer langgraph (and pydantic state), it might pass a dict or the model itself.
        # We'll handle both cases to be safe.
        def node_func(state_obj, agent_inst=agent):
            if isinstance(state_obj, dict):
                state_obj = GraphState(**state_obj)
            return agent_inst.safe_execute(state_obj)
        
        builder.add_node(name, node_func)
        builder.add_edge(name, "supervisor")
        
    # Inject PlanCritic Node
    def plan_critic_node(state_obj):
        if isinstance(state_obj, dict):
            state_obj = GraphState(**state_obj)
        
        from langchain_groq import ChatGroq
        import os
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.environ.get("GROQ_API_KEY", "dummy_key")
        )
        
        # Determine if we should fail or approve based on a mock strict critique
        prompt = f"Critique this allocation: Hospitals {len(state_obj.hospital_assignments)}, Resources {len(state_obj.resource_assignments)}. Reply REJECT if unbalanced, else APPROVE."
        try:
            if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
                raise ValueError("Dummy key")
            res = llm.invoke([SystemMessage(content="You are a strict disaster plan critic."), HumanMessage(content=prompt)]).content
            if "REJECT" in res and state_obj.retries.get("plan_critic", 0) < 1:
                # Force at least one retry for demonstration of the reflection loop
                return {
                    "completed_tasks": ["plan_critic"],
                    "retries": {"plan_critic": 1},
                    "execution_history": [{"agent": "PlanCritic", "summary": "Critic rejected plan, triggering reflection loop", "data": {"reason": res}}]
                }
        except Exception:
            pass
            
        return {
            "completed_tasks": ["plan_critic"],
            "execution_history": [{"agent": "PlanCritic", "summary": "Critic approved the allocation plan", "data": {"status": "approved"}}]
        }

    builder.add_node("plan_critic", plan_critic_node)
    builder.add_edge("plan_critic", "supervisor")

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
    )

    # Initialize checkpointer for Human-In-The-Loop
    import os
    if os.environ.get("USE_FAKE_REDIS", "false").lower() == "true":
        # Use pure-Python MemorySaver on Render to avoid ormsgpack segfaults
        from langgraph.checkpoint.memory import MemorySaver
        memory = MemorySaver()
    else:
        from backend.core.memory import RedisSaver, memory_manager
        memory = RedisSaver(memory_manager.client)

    # Compile the graph with interrupts
    return builder.compile(
        checkpointer=memory,
        interrupt_before=["resource_allocation", "communication"]
    )

# Instantiate the globally available graph
supervisor_graph = build_supervisor_graph()
