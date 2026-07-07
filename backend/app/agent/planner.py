# Plan node: convert reasoning into structured actions REMIND, ESCALATE, REORDER

import logging
from app.agent.state import AgentState

logger = logging.getLogger(__name__)

ACTION_REMIND = "REMIND"
ACTION_ESCALATE = "ESCALATE"
ACTION_REORDER = "REORDER"

# Plan format: one entry per line, "TYPE:target_or_reason"
PLAN_SEP = "\n"


def plan(state: AgentState) -> AgentState:
    """
    Convert reasoning into structured actions:
    - REMIND
    - ESCALATE
    - REORDER
    """
    logger.info("planner: executing plan node")
    reasoning = state.get("reasoning") or ""
    observations = state.get("observations") or []
    problem = state.get("_problem") or "none"
    escalation_needed = state.get("_escalation_needed", False)
    medications = state.get("medications") or []
    inventory = state.get("inventory") or []

    actions: list[str] = []

    # REMIND: for due / missed medicines (from observations)
    due_line = next((o for o in observations if o.startswith("due_medicines:")), "")
    missed_line = next((o for o in observations if o.startswith("missed_doses:")), "")
    due_names = _parse_list(due_line, "due_medicines:")
    missed_names = _parse_list(missed_line, "missed_doses:")
    for name in due_names:
        if name and name != "none":
            actions.append(f"{ACTION_REMIND}:{name}")
    for name in missed_names:
        if name and name != "none":
            actions.append(f"{ACTION_REMIND}:{name}")

    # ESCALATE: when reasoning says escalation needed (e.g. abnormal vitals)
    if escalation_needed:
        actions.append(f"{ACTION_ESCALATE}:{problem}")

    # REORDER: for low inventory
    low_line = next((o for o in observations if o.startswith("low_inventory:")), "")
    low_ids = _parse_list(low_line, "low_inventory:")
    for item_id in low_ids:
        if item_id and item_id != "none":
            actions.append(f"{ACTION_REORDER}:{item_id}")

    plan_text = PLAN_SEP.join(actions) if actions else ""
    logger.info("planner: plan=%s", plan_text.replace(PLAN_SEP, " | "))
    return {**state, "plan": plan_text}


def _parse_list(line: str, prefix: str) -> list[str]:
    """Extract comma-separated list from observation line."""
    if not line.startswith(prefix):
        return []
    rest = line[len(prefix):].strip()
    if not rest or rest == "none":
        return []
    return [x.strip() for x in rest.split(",") if x.strip()]


def plan_node(state: AgentState) -> AgentState:
    """Node entry point for LangGraph."""
    return plan(state)
