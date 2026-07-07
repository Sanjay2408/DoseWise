# Reason node: decide problem, urgency, and whether escalation is needed
# Integrates trend-aware intelligence: rule-based trends + optional LLM summary for caregivers

import logging
from app.agent.state import AgentState
from app.intelligence.trend_analyzer import detect_trends
from app.intelligence.risk_assessor import assess_severity
from app.intelligence.llm_explainer import generate_caregiver_summary

logger = logging.getLogger(__name__)

URGENCY_LOW = "low"
URGENCY_MEDIUM = "medium"
URGENCY_HIGH = "high"
URGENCY_CRITICAL = "critical"


def _parse_missed_dose_dates(observations: list) -> list[str]:
    """Extract missed dose names from observations; return empty (dates not stored in obs)."""
    for o in observations:
        if o.startswith("missed_doses:") and "none" not in o:
            rest = o.replace("missed_doses:", "").strip()
            if rest:
                return [rest.split(",")[0].strip()]  # placeholder: one "date" for linkage
    return []


def reason(state: AgentState) -> AgentState:
    """
    Decide: problem, urgency, escalation.
    Runs trend analyzer (rule-based), risk assessor, and optional LLM explainer for caregivers.
    """
    logger.info("reasoning: executing reason node")
    observations = state.get("observations") or []
    vitals = state.get("vitals") or []
    medications = state.get("medications") or []
    inventory = state.get("inventory") or []
    wellbeing_log = state.get("wellbeing_log") or []
    missed_dates = _parse_missed_dose_dates(observations)

    # --- Trend-aware intelligence (rule-based) ---
    trend_alerts = detect_trends(
        vitals_history=vitals,
        medications=medications,
        inventory=inventory,
        wellbeing_log=wellbeing_log,
        missed_dose_dates=missed_dates,
    )
    trend_severity = assess_severity(trend_alerts)
    ai_summary = ""
    if trend_alerts:
        patient_data = {
            "patient_profile": state.get("patient_profile") or {},
            "medications": medications,
        }
        ai_summary = generate_caregiver_summary(patient_data, trend_alerts)

    # --- Combine with observation-based logic ---
    reasoning_parts: list[str] = []
    problem: str = "none"
    urgency: str = URGENCY_LOW
    escalation_needed: bool = False

    has_due = any("due_medicines:" in o and "none" not in o for o in observations)
    has_missed = any("missed_doses:" in o and "none" not in o for o in observations)
    has_low_inv = any("low_inventory:" in o and "none" not in o for o in observations)
    has_abnormal = any("abnormal_vitals:" in o and "none" not in o for o in observations)
    has_trend_alerts = len(trend_alerts) > 0

    if trend_severity == URGENCY_CRITICAL or (has_trend_alerts and trend_severity == URGENCY_HIGH):
        problem = "trend_alerts"
        urgency = trend_severity
        escalation_needed = True
        reasoning_parts.append("Trend alerts detected; escalation recommended.")
    if has_abnormal and problem == "none":
        problem = "abnormal_vitals"
        urgency = URGENCY_HIGH
        escalation_needed = True
        reasoning_parts.append("Abnormal vitals detected; escalation recommended.")
    if has_missed:
        if problem == "none":
            problem = "missed_doses"
        urgency = URGENCY_MEDIUM if urgency == URGENCY_LOW else urgency
        reasoning_parts.append("Missed doses identified.")
    if has_due and problem == "none":
        problem = "due_medicines"
        reasoning_parts.append("Medicines are due; remind user.")
    if has_low_inv:
        if problem == "none":
            problem = "low_inventory"
        urgency = URGENCY_MEDIUM if urgency == URGENCY_LOW else urgency
        reasoning_parts.append("Low inventory; consider reorder.")
    if has_trend_alerts and problem == "none":
        problem = "trend_alerts"
        urgency = trend_severity if trend_severity != URGENCY_LOW else URGENCY_MEDIUM
        reasoning_parts.append("Trend patterns detected.")

    if problem == "none":
        reasoning_parts.append("No actionable problem detected.")

    reasoning_text = " ".join(reasoning_parts)
    reasoning_text += f" problem={problem} urgency={urgency} escalation_needed={escalation_needed}"

    logger.info(
        "reasoning: problem=%s urgency=%s escalation_needed=%s trend_alerts=%s",
        problem, urgency, escalation_needed, len(trend_alerts),
    )
    return {
        **state,
        "reasoning": reasoning_text,
        "_problem": problem,
        "_urgency": urgency,
        "_escalation_needed": escalation_needed,
        "trend_alerts": trend_alerts,
        "ai_summary": ai_summary or state.get("ai_summary"),
        "_trend_severity": trend_severity,
    }


def reason_node(state: AgentState) -> AgentState:
    """Node entry point for LangGraph."""
    return reason(state)
