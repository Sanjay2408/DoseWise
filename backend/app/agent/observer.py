# Observe node: populate observations from current state
# Uses current_time from device (set by API) for due/missed logic

import logging
from datetime import datetime, date, time as dt_time, timedelta
from typing import Any

from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def _next_dose_at(timings: list, current_time: Any) -> datetime | None:
    """Next scheduled dose datetime from timings and current time."""
    if not timings or current_time is None:
        return None
    try:
        if hasattr(current_time, "date"):
            today = current_time.date()
        else:
            today = date.today()
        now_min = current_time.hour * 60 + current_time.minute if hasattr(current_time, "hour") else 0
        tz = getattr(current_time, "tzinfo", None)
        for t in sorted(timings):
            parts = str(t).strip().split(":")
            h = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 8
            m = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0
            t_min = h * 60 + m
            if t_min > now_min:
                dt = datetime.combine(today, dt_time(h, m, 0))
                if tz:
                    dt = dt.replace(tzinfo=tz)
                return dt
        first = sorted(timings)[0]
        parts = str(first).strip().split(":")
        h = int(parts[0]) if len(parts) >= 1 else 8
        m = int(parts[1]) if len(parts) >= 2 else 0
        dt = datetime.combine(today, dt_time(h, m, 0)) + timedelta(days=1)
        if tz:
            dt = dt.replace(tzinfo=tz)
        return dt
    except Exception:
        return None


def observe(state: AgentState) -> AgentState:
    """
    Populate observations from state:
    - due medicines
    - missed doses
    - low inventory
    - abnormal vitals
    """
    logger.info("observer: executing observe node")
    observations: list[str] = []
    current_time = state.get("current_time")
    medications = state.get("medications") or []
    inventory = state.get("inventory") or []
    vitals = state.get("vitals") or []

    # Enrich medications with next_dose_at from timings and current_time
    meds_with_next = []
    for m in medications:
        m = dict(m)
        timings = m.get("timings") or ["08:00"]
        m["next_dose_at"] = _next_dose_at(timings, current_time)
        meds_with_next.append(m)
    medications = meds_with_next

    # Due medicines: medications that are due at or before current_time
    due_medicines = _due_medicines(medications, current_time)
    if due_medicines:
        observations.append(f"due_medicines:{','.join(due_medicines)}")
    else:
        observations.append("due_medicines:none")

    # Missed doses: inferred from schedule vs current time (placeholder logic)
    missed = _missed_doses(medications, current_time)
    if missed:
        observations.append(f"missed_doses:{','.join(missed)}")
    else:
        observations.append("missed_doses:none")

    # Low inventory
    low = _low_inventory(inventory)
    if low:
        observations.append(f"low_inventory:{','.join(low)}")
    else:
        observations.append("low_inventory:none")

    # Abnormal vitals
    abnormal = _abnormal_vitals(vitals)
    if abnormal:
        observations.append(f"abnormal_vitals:{','.join(abnormal)}")
    else:
        observations.append("abnormal_vitals:none")

    logger.info("observer: observations=%s", observations)
    return {**state, "observations": observations, "medications": medications}


def _due_medicines(medications: list[dict], current_time: Any) -> list[str]:
    """Names of medications with a scheduled dose at or before current_time (dose time has arrived)."""
    names: list[str] = []
    if current_time is None:
        return names
    try:
        today = current_time.date() if hasattr(current_time, "date") else date.today()
        now_dt = current_time if isinstance(current_time, datetime) else datetime.combine(today, dt_time(current_time.hour, current_time.minute, 0))
        tz = getattr(current_time, "tzinfo", None)
        for m in medications:
            name = m.get("name") or m.get("id") or "unknown"
            timings = m.get("timings") or ["08:00"]
            for t in timings:
                parts = str(t).strip().split(":")
                h = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 8
                minu = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0
                scheduled = datetime.combine(today, dt_time(h, minu, 0))
                if tz:
                    scheduled = scheduled.replace(tzinfo=tz)
                if scheduled <= now_dt:
                    names.append(str(name))
                    break
    except Exception:
        pass
    return names


def _missed_doses(medications: list[dict], current_time: Any) -> list[str]:
    """Names of medications with missed doses (placeholder: past due window)."""
    missed: list[str] = []
    for m in medications:
        name = m.get("name") or m.get("id") or "unknown"
        last_taken = m.get("last_taken_at") or m.get("last_taken")
        if last_taken is None:
            continue
        # Placeholder: if we have due_medicines and no recent take, could be missed
        next_at = m.get("next_dose_at") or m.get("next_dose")
        if next_at and current_time:
            try:
                from datetime import datetime
                if isinstance(next_at, datetime):
                    n = next_at
                else:
                    n = datetime.fromisoformat(str(next_at).replace("Z", "+00:00"))
                if isinstance(current_time, datetime) and n < current_time:
                    missed.append(str(name))
            except Exception:
                pass
    return missed


def _low_inventory(inventory: list[dict]) -> list[str]:
    """Names of inventory items at or below their low-stock threshold.

    Real inventory records use med_name / quantity / low_stock_threshold
    (see InventoryManager.get_inventory_status).
    """
    low: list[str] = []
    for item in inventory:
        try:
            quantity = float(item.get("quantity") or item.get("remaining") or 0)
            threshold = float(
                item.get("low_stock_threshold")
                or item.get("low_threshold")
                or item.get("threshold")
                or 10
            )
        except (TypeError, ValueError):
            continue
        if quantity <= threshold:
            ident = (
                item.get("med_name")
                or item.get("name")
                or item.get("medication_id")
                or item.get("id")
                or "unknown"
            )
            low.append(str(ident))
    return low


def _abnormal_vitals(vitals: list[dict]) -> list[str]:
    """Labels for vitals outside normal range.

    Real vitals records store readings as top-level fields on each entry:
    heart_rate (int), blood_pressure ("120/80"), temperature (float °C).
    Only the most recent entries matter for escalation; check the last 5.
    """
    abnormal: list[str] = []
    for v in vitals[-5:]:
        hr = v.get("heart_rate")
        if hr is not None:
            try:
                num = float(hr)
                if num < 50 or num > 120:
                    abnormal.append(f"heart_rate={num:g}")
            except (TypeError, ValueError):
                pass

        bp = v.get("blood_pressure")
        if bp:
            try:
                parts = str(bp).replace(" ", "").split("/")
                systolic = float(parts[0])
                diastolic = float(parts[1]) if len(parts) > 1 else None
                if systolic < 90 or systolic > 160:
                    abnormal.append(f"blood_pressure_systolic={systolic:g}")
                if diastolic is not None and (diastolic < 60 or diastolic > 100):
                    abnormal.append(f"blood_pressure_diastolic={diastolic:g}")
            except (TypeError, ValueError, IndexError):
                pass

        temp = v.get("temperature")
        if temp is not None:
            try:
                num = float(temp)
                if num < 36.0 or num > 38.5:
                    abnormal.append(f"temperature={num:g}")
            except (TypeError, ValueError):
                pass
    return abnormal


# LangGraph node: same signature, name used in graph
def observe_node(state: AgentState) -> AgentState:
    """Node entry point for LangGraph."""
    return observe(state)
