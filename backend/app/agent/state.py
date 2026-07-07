# Agent state schema for DoseWise medication assistant

from typing import TypedDict, List, Optional, Any
from datetime import datetime


class AgentState(TypedDict, total=False):
    """State schema for the DoseWise agent. Used by LangGraph for merge semantics."""

    current_time: datetime
    medications: List[dict]
    inventory: List[dict]
    vitals: List[dict]
    observations: List[str]
    reasoning: Optional[str]
    plan: Optional[str]
    action_log: List[dict]
    alerts: List[str]
    # Intelligence layer: caregiver & trends
    patient_profile: dict  # name, age, conditions
    wellbeing_log: List[dict]  # { feeling, recorded_at }
    trend_alerts: List[str]  # rule-based trend alerts
    ai_summary: Optional[str]  # LLM-generated caregiver summary (no diagnosis)
    # Session / bookkeeping
    user_id: str
    messages: List[str]
    # Internal hand-off fields between reason → plan → act. These must be
    # declared here: LangGraph only carries keys present in the state schema.
    _problem: Optional[str]
    _urgency: Optional[str]
    _escalation_needed: bool
    _trend_severity: Optional[str]


def create_initial_state(
    current_time: Optional[datetime] = None,
    medications: Optional[List[dict]] = None,
    inventory: Optional[List[dict]] = None,
    vitals: Optional[List[dict]] = None,
) -> AgentState:
    """Build initial AgentState with required fields and empty collections."""
    from datetime import datetime as dt
    return {
        "current_time": current_time or dt.utcnow(),
        "medications": medications or [],
        "inventory": inventory or [],
        "vitals": vitals or [],
        "observations": [],
        "reasoning": None,
        "plan": None,
        "action_log": [],
        "alerts": [],
        "patient_profile": {},
        "wellbeing_log": [],
        "trend_alerts": [],
        "ai_summary": None,
    }
