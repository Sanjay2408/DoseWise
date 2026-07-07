# LangGraph definition for DoseWise agent
# Flow: observe → reason → plan → act → END (single deterministic pass per run)

import logging
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.observer import observe_node
from app.agent.reasoning import reason_node
from app.agent.planner import plan_node
from app.agent.action import action_node

logger = logging.getLogger(__name__)


def _logged_node(name: str, node_fn):
    """Wrap a node to log every execution."""

    def wrapped(state: AgentState) -> AgentState:
        logger.info("graph: node_execution node=%s", name)
        out = node_fn(state)
        logger.info("graph: node_complete node=%s", name)
        return out

    return wrapped


def create_agent_graph():
    """Create the LangGraph workflow for the DoseWise agent.
    Node names must not match AgentState keys (e.g. reasoning, plan, observations).
    """
    workflow = StateGraph(AgentState)

    # Add nodes with logging (names distinct from state keys)
    workflow.add_node("observe", _logged_node("observe", observe_node))
    workflow.add_node("reason", _logged_node("reason", reason_node))
    workflow.add_node("plan_step", _logged_node("plan_step", plan_node))
    workflow.add_node("act", _logged_node("act", action_node))

    # Deterministic edges: observe → reason → plan → act → END
    workflow.add_edge("observe", "reason")
    workflow.add_edge("reason", "plan_step")
    workflow.add_edge("plan_step", "act")
    workflow.add_edge("act", END)

    workflow.set_entry_point("observe")

    return workflow.compile()


agent = create_agent_graph()
