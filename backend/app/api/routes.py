"""
FastAPI glue layer: load state, call agent/setup/dose/vitals, save state, return state.
No business logic or reasoning here.

Every endpoint requires authentication and operates only on the signed-in
user's own state (stored per-user in SQLite via app.storage.db).
"""

import asyncio
import logging
import re
from datetime import datetime
import shutil
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from app.agent.graph import agent
from app.agent.state import AgentState, create_initial_state
from app.api.schemas import (
    AgentRunRequest,
    DoseConfirmationRequest,
    InventoryUpdateRequest,
    MedicationSetupRequest,
    VitalsSubmissionRequest,
)
from app.auth import get_current_user
from app.intelligence import (
    detect_trends,
    get_vitals_by_date,
    detect_trends_for_day,
    assess_severity,
    generate_caregiver_summary,
)
from app.intelligence.historical_analyzer import (
    calculate_adherence_rate,
    analyze_vital_trends,
    analyze_wellbeing_patterns,
    generate_comparative_summary,
)
from app.medication.inventory import InventoryManager
from app.medication.registry import MedicationRegistry
from app.medication.schedule import ScheduleManager
from app.config import DATA_DIR
from app.storage import db

logger = logging.getLogger(__name__)

_STORAGE_DIR = DATA_DIR

# The agent is synchronous (LangGraph + optional LLM call). Run it off the
# event loop with a hard timeout so one slow run can never freeze the server.
AGENT_TIMEOUT_SECONDS = 90


async def _run_agent(state: AgentState) -> AgentState:
    return await asyncio.wait_for(
        asyncio.to_thread(agent.invoke, state), timeout=AGENT_TIMEOUT_SECONDS
    )


def load_state(user_id: str) -> AgentState:
    """Load the user's AgentState from SQLite. Return empty initial state if missing."""
    data = db.load_user_state(user_id)
    state = create_initial_state()
    if data:
        state.update(data)

    if "current_time" in state and isinstance(state["current_time"], str):
        try:
            state["current_time"] = datetime.fromisoformat(
                state["current_time"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            state["current_time"] = datetime.utcnow()
    state["user_id"] = user_id
    if "messages" not in state:
        state["messages"] = []
    if "patient_profile" not in state:
        state["patient_profile"] = {}
    if "wellbeing_log" not in state:
        state["wellbeing_log"] = []
    if "trend_alerts" not in state:
        state["trend_alerts"] = []
    if "ai_summary" not in state:
        state["ai_summary"] = None
    return state


def save_state(user_id: str, state: AgentState) -> None:
    """Persist the user's AgentState to SQLite."""
    out: dict[str, Any] = dict(state)
    if "current_time" in out and isinstance(out["current_time"], datetime):
        out["current_time"] = out["current_time"].isoformat()
    db.save_user_state(user_id, out)


router = APIRouter(prefix="/api", tags=["api"])


def _parse_client_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _enrich_medications_with_next_dose(medications: list, current_time: datetime) -> list:
    """Add next_dose_at to each medication based on timings and current_time."""
    from datetime import date, time as dt_time, timedelta
    result = []

    today = current_time.date() if hasattr(current_time, "date") else date.today()
    now_minutes = current_time.hour * 60 + current_time.minute if hasattr(current_time, "hour") else 0

    for m in medications:
        m = dict(m)
        timings = m.get("timings") or ["08:00"]
        next_dose_at = None

        sorted_timings = sorted(timings)

        for t in sorted_timings:
            parts = t.strip().split(":")
            try:
                h = int(parts[0]) if len(parts) >= 1 and parts[0].strip().isdigit() else 8
                minu = int(parts[1]) if len(parts) >= 2 and parts[1].strip().isdigit() else 0
            except (ValueError, IndexError):
                h, minu = 8, 0

            t_minutes = h * 60 + minu

            if t_minutes > now_minutes:
                if current_time.tzinfo:
                    next_dose_at = current_time.replace(hour=h, minute=minu, second=0, microsecond=0)
                else:
                    next_dose_at = datetime.combine(today, dt_time(h, minu, 0))
                break

        if next_dose_at is None and sorted_timings:
            first = sorted_timings[0]
            parts = first.strip().split(":")
            try:
                h = int(parts[0]) if len(parts) >= 1 and parts[0].strip().isdigit() else 8
                minu = int(parts[1]) if len(parts) >= 2 and parts[1].strip().isdigit() else 0
            except (ValueError, IndexError):
                h, minu = 8, 0

            if current_time.tzinfo:
                next_dose_at = current_time.replace(hour=h, minute=minu, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_dose_at = datetime.combine(today, dt_time(h, minu, 0)) + timedelta(days=1)

        m["next_dose_at"] = next_dose_at.isoformat() if next_dose_at else None
        result.append(m)
    return result


def _state_response(state: AgentState) -> dict:
    resp: dict[str, Any] = dict(state)
    if "current_time" in resp and isinstance(resp["current_time"], datetime):
        resp["current_time"] = resp["current_time"].isoformat()
    return resp


@router.get("/state")
async def get_state(
    current_time: str | None = Query(None, description="Device current time (ISO)"),
    user: dict = Depends(get_current_user),
) -> dict:
    """GET /state: load and return the user's AgentState. Optional current_time from device updates state."""
    state = load_state(user["id"])
    client_time = _parse_client_time(current_time)
    if client_time is not None:
        state["current_time"] = client_time
        save_state(user["id"], state)
    resp = _state_response(state)
    if client_time is not None and state.get("medications"):
        resp["medications"] = _enrich_medications_with_next_dose(
            state.get("medications", []), client_time
        )
    elif "current_time" in state and state.get("medications"):
        ct = state["current_time"] if isinstance(state["current_time"], datetime) else _parse_client_time(resp.get("current_time"))
        if ct:
            resp["medications"] = _enrich_medications_with_next_dose(state.get("medications", []), ct)
    return resp


@router.post("/agent/run")
async def run_agent(
    body: AgentRunRequest | None = Body(None),
    user: dict = Depends(get_current_user),
) -> dict:
    """POST /agent/run: load state, optionally set current_time from device, invoke agent, save, return state."""
    state = load_state(user["id"])
    client_time = body.current_time if body and body.current_time else None
    if client_time is not None:
        state["current_time"] = client_time
        save_state(user["id"], state)
    try:
        result = await _run_agent(state)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="The assistant is taking too long. Please try again.")
    except Exception as e:
        logger.exception("agent run failed")
        raise HTTPException(status_code=500, detail=f"Agent run failed: {e}") from e
    save_state(user["id"], result)
    return _state_response(result)


@router.delete("/medications/{name}")
async def delete_medication(name: str, user: dict = Depends(get_current_user)) -> dict:
    """DELETE /medications/{name}: remove a medication from the system."""
    state = load_state(user["id"])

    medications = state.get("medications") or []
    state["medications"] = [m for m in medications if (m.get("name") or "") != name]

    inventory = state.get("inventory") or []
    state["inventory"] = [i for i in inventory if (i.get("med_name") or "") != name]

    save_state(user["id"], state)
    return {"status": "success", "message": f"Medication {name} deleted"}


@router.post("/setup/medications")
async def setup_medications(
    payload: MedicationSetupRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """POST /setup/medications: full setup or edit/add. If profile exists, merge new medications only."""
    state = load_state(user["id"])
    existing_meds = {m.get("name") or m.get("id"): m for m in (state.get("medications") or []) if m.get("name") or m.get("id")}
    is_edit_mode = bool(state.get("patient_profile") and (state.get("patient_profile") or {}).get("name"))

    registry = MedicationRegistry()
    schedule_mgr = ScheduleManager()
    inv_mgr = InventoryManager()

    # Rehydrate existing into registry/schedule/inventory when editing
    if is_edit_mode:
        for name, m in existing_meds.items():
            timings = m.get("timings") or ["08:00"]
            try:
                registry.add_medication(
                    name=name,
                    dosage=m.get("dosage") or "",
                    timings=timings,
                    before_after_food=m.get("before_after_food") or "anytime",
                )
            except ValueError:
                pass
            schedule_mgr.add_medication_schedule(name, timings)
        for inv_item in (state.get("inventory") or []):
            mn = inv_item.get("med_name") or inv_item.get("name") or inv_item.get("id")
            if not mn:
                continue
            try:
                inv_mgr.add_medication(
                    mn,
                    initial_quantity=inv_item.get("quantity", 0),
                    low_stock_threshold=inv_item.get("low_stock_threshold", 10),
                )
            except ValueError:
                pass

    for med in payload.medications:
        if not (med.name or "").strip():
            continue
        timings = med.times if getattr(med, "times", None) else ["08:00"]
        if not timings:
            timings = ["08:00"]
        take_with_food = (getattr(med, "take_with_food", None) or "anytime").lower()
        if take_with_food not in ("before", "after", "anytime"):
            take_with_food = "anytime"
        try:
            registry.add_medication(
                name=med.name.strip(),
                dosage=med.dosage or "",
                timings=timings,
                before_after_food=take_with_food,
            )
        except ValueError:
            if is_edit_mode:
                try:
                    registry.update_medication(med.name.strip(), dosage=med.dosage, timings=timings, before_after_food=take_with_food)
                except ValueError:
                    pass
            else:
                continue
        schedule_mgr.add_medication_schedule(med.name.strip(), timings)

        # Ensure inventory exists for this medication
        existing_inventory = [item for item in state.get("inventory", []) if item.get("med_name") == med.name.strip()]

        if not existing_inventory:
            try:
                qty = med.quantity if med.quantity is not None else 30
                inv_mgr.add_medication(med.name.strip(), initial_quantity=qty)
            except ValueError:
                pass
        elif med.quantity is not None:
            try:
                inv_mgr.set_quantity(med.name.strip(), med.quantity)
            except ValueError:
                pass

    # Preserve fields the registry doesn't track (e.g. uploaded images, last taken)
    new_meds = registry.get_all()
    for m in new_meds:
        prev = existing_meds.get(m.get("name"))
        if prev:
            for keep in ("image_file", "last_taken_at"):
                if prev.get(keep) and not m.get(keep):
                    m[keep] = prev[keep]
    state["medications"] = new_meds
    state["inventory"] = inv_mgr.get_inventory_status()
    state["patient_profile"] = {
        "name": payload.name or (state.get("patient_profile") or {}).get("name") or "",
        "age": payload.age or (state.get("patient_profile") or {}).get("age") or "",
        "conditions": payload.conditions or (state.get("patient_profile") or {}).get("conditions") or "",
    }
    if "messages" not in state:
        state["messages"] = []

    save_state(user["id"], state)
    return _state_response(state)


@router.post("/dose/confirm")
async def dose_confirm(
    body: DoseConfirmationRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """POST /dose/confirm: mark dose taken, decrement inventory, persist, run agent, return state."""
    state = load_state(user["id"])
    medication_name = body.medication_name
    if not medication_name and body.medication_id:
        for m in state.get("medications") or []:
            mid = str(m.get("id") or m.get("name", ""))
            if mid == str(body.medication_id):
                medication_name = m.get("name") or m.get("id")
                break
        if not medication_name:
            medication_name = str(body.medication_id)
    if not medication_name:
        raise HTTPException(status_code=400, detail="medication_name or medication_id required")

    taken_at = body.timestamp or datetime.utcnow()
    scheduled_time = body.scheduled_time
    if not scheduled_time:
        scheduled_time = taken_at.strftime("%H:%M")

    schedule_mgr = ScheduleManager()
    for m in state.get("medications") or []:
        name = m.get("name") or m.get("id")
        timings = m.get("timings") or ["08:00"]
        if name == medication_name or str(m.get("id")) == str(body.medication_id):
            schedule_mgr.add_medication_schedule(medication_name, timings, start_date=taken_at)
            break
    schedule_mgr.mark_dose_taken(medication_name, scheduled_time, taken_at=taken_at)

    # Check if dose was taken late and send email alert
    try:
        from app.notifications.email_service import get_email_service
        from datetime import time as dt_time

        scheduled_parts = scheduled_time.split(":")
        scheduled_hour = int(scheduled_parts[0]) if len(scheduled_parts) >= 1 else 0
        scheduled_minute = int(scheduled_parts[1]) if len(scheduled_parts) >= 2 else 0

        today = taken_at.date() if hasattr(taken_at, "date") else datetime.now().date()
        scheduled_dt = datetime.combine(today, dt_time(scheduled_hour, scheduled_minute))

        if hasattr(taken_at, "tzinfo") and taken_at.tzinfo:
            scheduled_dt = scheduled_dt.replace(tzinfo=taken_at.tzinfo)

        delay = (taken_at - scheduled_dt).total_seconds() / 3600

        if delay > 2:
            email_service = get_email_service()
            email_service.send_missed_dose_alert(
                medication_name=medication_name,
                scheduled_time=scheduled_time
            )
    except Exception as e:
        logger.warning("Failed to send missed dose email: %s", e)

    for m in state.get("medications") or []:
        if (m.get("name") or m.get("id")) == medication_name:
            m["last_taken_at"] = taken_at.isoformat()
            break

    inv_mgr = InventoryManager()
    for item in state.get("inventory") or []:
        mn = item.get("med_name") or item.get("name") or item.get("id")
        if not mn:
            continue
        try:
            inv_mgr.add_medication(
                mn,
                initial_quantity=item.get("quantity", 0),
                low_stock_threshold=item.get("low_stock_threshold", 10),
            )
        except ValueError:
            pass
    try:
        inv_mgr.decrement(medication_name, 1)
        state["inventory"] = inv_mgr.get_inventory_status()
    except (ValueError, KeyError):
        pass

    save_state(user["id"], state)
    try:
        result = await _run_agent(state)
        save_state(user["id"], result)
        state = result
    except Exception as e:
        logger.warning("post-dose agent run skipped: %s", e)

    return _state_response(state)


@router.post("/vitals/submit")
async def vitals_submit(
    body: VitalsSubmissionRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """POST /vitals/submit: append vitals and optional wellbeing to AgentState, persist, return state."""
    state = load_state(user["id"])
    vitals = state.get("vitals") or []
    try:
        entry = dict(body.model_dump(exclude_none=True))
    except AttributeError:
        entry = dict(body.dict(exclude_none=True))
    if "recorded_at" not in entry:
        entry["recorded_at"] = datetime.utcnow().isoformat()
    elif isinstance(entry.get("recorded_at"), datetime):
        entry["recorded_at"] = entry["recorded_at"].isoformat()
    vitals.append(entry)
    state["vitals"] = vitals

    # Check for abnormal vitals and send email alert
    try:
        from app.notifications.email_service import get_email_service
        email_service = get_email_service()

        bp = entry.get("blood_pressure")
        hr = entry.get("heart_rate")
        temp = entry.get("temperature")

        if bp:
            try:
                systolic, diastolic = map(int, str(bp).split("/"))
                if systolic < 90 or systolic > 160:
                    email_service.send_abnormal_vitals_alert(
                        vital_type="Blood Pressure (Systolic)",
                        value=f"{systolic} mmHg",
                        normal_range="90-160 mmHg"
                    )
                if diastolic < 60 or diastolic > 100:
                    email_service.send_abnormal_vitals_alert(
                        vital_type="Blood Pressure (Diastolic)",
                        value=f"{diastolic} mmHg",
                        normal_range="60-100 mmHg"
                    )
            except (ValueError, AttributeError):
                pass

        if hr:
            try:
                heart_rate = float(hr)
                if heart_rate < 50 or heart_rate > 120:
                    email_service.send_abnormal_vitals_alert(
                        vital_type="Heart Rate",
                        value=f"{heart_rate} bpm",
                        normal_range="50-120 bpm"
                    )
            except (ValueError, TypeError):
                pass

        if temp:
            try:
                temperature = float(temp)
                if temperature < 36.0 or temperature > 38.0:
                    email_service.send_abnormal_vitals_alert(
                        vital_type="Temperature",
                        value=f"{temperature}°C",
                        normal_range="36.0-38.0°C"
                    )
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.warning("Failed to send abnormal vitals email: %s", e)

    # Wellbeing (how patient feels) for trend analyzer
    feeling = entry.get("feeling") or entry.get("wellbeing") or entry.get("mood")
    if feeling is not None:
        wellbeing_log = state.get("wellbeing_log") or []
        wellbeing_log.append({"feeling": str(feeling), "recorded_at": entry.get("recorded_at")})
        state["wellbeing_log"] = wellbeing_log
    save_state(user["id"], state)
    return _state_response(state)


def _get_wellbeing_by_date(wellbeing_log: list, target_date: str) -> list:
    out = []
    for w in wellbeing_log or []:
        rec = w.get("recorded_at") or w.get("timestamp")
        if not rec:
            continue
        try:
            dt = rec if isinstance(rec, datetime) else _parse_client_time(str(rec))
            if dt is None:
                continue
            d = str(dt.date()) if hasattr(dt, "date") else str(rec)[:10]
            if d == target_date:
                out.append(w)
        except Exception:
            pass
    return out


@router.get("/caregiver/daily-reports")
async def get_daily_reports(user: dict = Depends(get_current_user)) -> dict:
    """GET /caregiver/daily-reports: list of dates with vitals and per-day intelligence report for caregiver."""
    state = load_state(user["id"])
    vitals = state.get("vitals") or []
    wellbeing_log = state.get("wellbeing_log") or []
    profile = state.get("patient_profile") or {}
    medications = state.get("medications") or []
    inventory = state.get("inventory") or []

    dates_set: set[str] = set()
    for v in vitals:
        rec = v.get("recorded_at") or v.get("timestamp")
        if not rec:
            continue
        try:
            dt = rec if isinstance(rec, datetime) else _parse_client_time(str(rec))
            if dt is None:
                continue
            d = str(dt.date()) if hasattr(dt, "date") else str(rec)[:10]
            dates_set.add(d)
        except Exception:
            pass
    dates = sorted(dates_set, reverse=True)

    reports: dict[str, dict] = {}
    for d in dates:
        vitals_day = get_vitals_by_date(vitals, d)
        wellbeing_day = _get_wellbeing_by_date(wellbeing_log, d)
        trend_alerts = detect_trends_for_day(
            vitals_for_day=vitals_day,
            all_vitals=vitals,
            patient_profile=profile,
            medications=medications,
            inventory=inventory,
            wellbeing_for_day=wellbeing_day,
        )

        historical_context = {
            "adherence": calculate_adherence_rate(medications, vitals, days=7),
            "vital_trends": analyze_vital_trends(vitals, days=7),
            "wellbeing": analyze_wellbeing_patterns(wellbeing_log, days=7),
            "comparative": generate_comparative_summary(vitals, vitals, current_days=7, historical_days=14),
        }

        patient_data = {"patient_profile": profile, "medications": medications}

        if trend_alerts:
            ai_summary = generate_caregiver_summary(patient_data, trend_alerts, historical_context)
        else:
            if historical_context["vital_trends"].get("count", 0) > 0:
                adherence_data = historical_context['adherence']
                vital_trends = historical_context['vital_trends']
                wellbeing_data = historical_context['wellbeing']
                comparative = historical_context['comparative']

                summary_parts = [
                    f"# 📊 Daily Intelligence Report - {d}",
                    "",
                    "## ✅ Overall Status",
                    "No critical alerts detected. Patient vitals are within acceptable ranges.",
                    "",
                    "## 💊 Medication Adherence (Past 7 Days)",
                    f"**Overall Rate:** {adherence_data.get('overall_rate', 0):.1f}%",
                ]

                by_med = adherence_data.get('by_medication', {})
                if by_med:
                    summary_parts.append("")
                    summary_parts.append("**By Medication:**")
                    for med_name, status in by_med.items():
                        icon = "✓" if "taken" in status.lower() else "⚠️"
                        summary_parts.append(f"- {icon} **{med_name}**: {status}")

                summary_parts.extend(["", "## 🩺 Vital Signs Analysis (Past 7 Days)"])
                summary_parts.append(f"**Total Recordings:** {vital_trends.get('count', 0)}")

                metrics = vital_trends.get('metrics', {})
                if metrics:
                    summary_parts.append("")
                    for metric, data in metrics.items():
                        metric_name = metric.replace('_', ' ').title()
                        avg = data.get('average', 'N/A')
                        trend = data.get('trend', 'stable')
                        min_val = data.get('min', 'N/A')
                        max_val = data.get('max', 'N/A')

                        trend_icon = "📈" if trend == "increasing" else "📉" if trend == "decreasing" else "➡️"
                        summary_parts.append(f"**{metric_name}:**")
                        summary_parts.append(f"  - Average: {avg} {trend_icon} ({trend})")
                        summary_parts.append(f"  - Range: {min_val} - {max_val}")

                if wellbeing_data.get('entries', 0) > 0:
                    summary_parts.extend(["", "## 😊 Wellbeing & Mood"])
                    summary_parts.append(f"**Entries:** {wellbeing_data.get('entries', 0)}")
                    summary_parts.append(f"**Most Common Feeling:** {wellbeing_data.get('most_common_feeling', 'Not recorded').title()}")

                    feelings = wellbeing_data.get('feeling_distribution', {})
                    if feelings:
                        summary_parts.append("")
                        summary_parts.append("**Mood Distribution:**")
                        for feeling, count in sorted(feelings.items(), key=lambda x: x[1], reverse=True):
                            summary_parts.append(f"- {feeling.title()}: {count} time(s)")

                comparisons = comparative.get('comparisons', {})
                if comparisons:
                    summary_parts.extend(["", "## 📊 Week-over-Week Changes"])
                    for metric, comp_data in comparisons.items():
                        direction = comp_data.get('direction', 'stable')
                        change_pct = comp_data.get('change_percent', 0)

                        if direction != 'stable':
                            metric_name = metric.replace('_', ' ').title()
                            sign = "+" if change_pct > 0 else ""
                            summary_parts.append(f"- **{metric_name}**: {direction} by {sign}{change_pct:.1f}%")

                summary_parts.extend([
                    "",
                    "## 💡 Recommendations",
                    "- ✅ Continue current medication schedule",
                    "- 📋 Monitor vital signs daily",
                ])

                if adherence_data.get('overall_rate', 100) < 80:
                    summary_parts.append("- ⚠️ **Action Required:** Medication adherence is below 80%. Please ensure all doses are taken on time")

                for metric, data in metrics.items():
                    if data.get('trend') == 'increasing' and 'pressure' in metric:
                        summary_parts.append("- 👀 Blood pressure showing upward trend - continue monitoring closely")
                    elif data.get('trend') == 'increasing' and 'heart' in metric:
                        summary_parts.append("- 💓 Heart rate trending up - ensure patient is resting adequately")

                summary_parts.extend([
                    "- 📞 Schedule routine checkup if any concerning patterns persist",
                    "",
                    "_This is an automated analysis. Consult healthcare professionals for medical decisions._"
                ])

                ai_summary = "\n".join(summary_parts)
            else:
                ai_summary = "No alerts for this day. Vitals recorded as entered."

        reports[d] = {
            "vitals": vitals_day,
            "wellbeing": wellbeing_day,
            "trend_alerts": trend_alerts,
            "ai_summary": ai_summary,
            "historical_context": historical_context,
        }

    return {
        "dates": dates,
        "reports": reports,
        "patient_profile": profile,
    }


@router.get("/alerts")
async def get_alerts(user: dict = Depends(get_current_user)) -> dict:
    """GET /alerts: alerts + trend_alerts + ai_summary for caregiver dashboard."""
    state = load_state(user["id"])
    alerts = list(state.get("alerts") or [])
    trend_alerts = list(state.get("trend_alerts") or [])
    combined = alerts + [f"[Trend] {a}" for a in trend_alerts] if trend_alerts else alerts
    return {
        "alerts": combined,
        "trend_alerts": trend_alerts,
        "ai_summary": state.get("ai_summary") or "",
        "severity": state.get("_trend_severity") or "low",
    }


@router.get("/vitals/trends")
async def get_vitals_trends(user: dict = Depends(get_current_user)) -> dict:
    """GET /vitals/trends: vitals history and per-metric series for caregiver charts.

    Vitals records store readings as top-level fields (heart_rate,
    blood_pressure "120/80", temperature), so each record can contribute to
    several series.
    """
    state = load_state(user["id"])
    vitals = state.get("vitals") or []
    by_type: dict[str, list] = {}

    def _add(metric: str, value: Any, recorded_at: Any) -> None:
        by_type.setdefault(metric, []).append({"value": value, "recorded_at": recorded_at})

    for v in vitals[-50:]:  # last 50 entries
        rec = v.get("recorded_at") or v.get("timestamp")
        hr = v.get("heart_rate")
        if hr is not None:
            _add("heart_rate", hr, rec)
        bp = v.get("blood_pressure")
        if bp:
            _add("blood_pressure", str(bp), rec)
            # Also expose systolic as a numeric series for charting
            m = re.match(r"\s*(\d+)", str(bp))
            if m:
                _add("blood_pressure_systolic", int(m.group(1)), rec)
        temp = v.get("temperature")
        if temp is not None:
            _add("temperature", temp, rec)
        # Legacy {type, value} records, if any exist
        t = (v.get("type") or v.get("metric") or "").lower()
        if t and v.get("value") is not None:
            if "sugar" in t or "glucose" in t:
                _add("blood_sugar", v.get("value"), rec)
            elif "heart" in t or t == "hr":
                _add("heart_rate", v.get("value"), rec)

    return {
        "vitals": vitals[-30:],
        "by_type": by_type,
        "patient_profile": state.get("patient_profile") or {},
        "medications": state.get("medications") or [],
    }


# --- Frontend compatibility (existing frontend calls these) ---
@router.get("/medications")
async def get_medications(user: dict = Depends(get_current_user)) -> dict:
    """Return medications from state (frontend getMedications)."""
    state = load_state(user["id"])
    return {"medications": state.get("medications") or []}


@router.post("/setup")
async def setup_legacy(
    payload: MedicationSetupRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Legacy POST /setup: same as /setup/medications."""
    return await setup_medications(payload, user)


@router.post("/medications/{medication_id}/confirm")
async def dose_confirm_by_id(
    medication_id: str,
    body: DoseConfirmationRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Legacy POST /medications/:id/confirm: same as /dose/confirm with medication_id."""
    try:
        kwargs = body.model_dump()
    except AttributeError:
        kwargs = body.dict()
    kwargs["medication_id"] = medication_id
    if kwargs.get("timestamp") is None:
        kwargs["timestamp"] = datetime.utcnow()
    return await dose_confirm(DoseConfirmationRequest(**kwargs), user)


@router.post("/vitals")
async def vitals_legacy(
    body: VitalsSubmissionRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Legacy POST /vitals: same as /vitals/submit."""
    return await vitals_submit(body, user)


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")


@router.post("/medications/{medication_id}/image")
async def upload_medication_image(
    medication_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict:
    """POST /medications/{medication_id}/image: Upload an image for a medication (stored per user)."""
    images_dir = _STORAGE_DIR / "images" / user["id"]
    images_dir.mkdir(parents=True, exist_ok=True)

    safe_med = _SAFE_FILENAME.sub("_", medication_id)[:60]
    safe_name = _SAFE_FILENAME.sub("_", file.filename or "image")[:80]
    filename = f"{safe_med}_{safe_name}"
    file_path = images_dir / filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # image_file is stored as "<user_id>/<filename>" and served from /images
        rel_path = f"{user['id']}/{filename}"
        state = load_state(user["id"])
        updated = False
        for m in state.get("medications") or []:
            mid = m.get("id") or m.get("name")
            if str(mid) == medication_id or m.get("name") == medication_id:
                m["image_file"] = rel_path
                updated = True
                break

        if updated:
            save_state(user["id"], state)

    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {e}") from e

    return {"filename": rel_path, "status": "uploaded"}


# --- Pharmacy Search ---
class PharmacySearchRequest(BaseModel):
    medication_name: str
    quantity: int = 30
    location: Optional[str] = None


@router.post("/pharmacy/search")
async def search_pharmacy(
    body: PharmacySearchRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Search for pharmacies carrying a specific medication."""
    from app.reorder.pharmacy_search import PharmacySearchService
    service = PharmacySearchService()
    results = service.search_pharmacies(
        medication_name=body.medication_name,
        quantity=body.quantity,
        user_location=body.location
    )
    return {"results": results}


# --- Inventory Update ---
@router.post("/inventory/update")
async def update_inventory(
    body: InventoryUpdateRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Update medication inventory quantity."""
    state = load_state(user["id"])
    inventory = state.get("inventory") or []

    found = False
    for item in inventory:
        med_name = item.get("med_name") or item.get("name") or item.get("id")
        if med_name == body.medication_name:
            item["quantity"] = body.quantity
            item["last_updated"] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        inventory.append({
            "med_name": body.medication_name,
            "quantity": body.quantity,
            "low_stock_threshold": 10,
            "last_updated": datetime.utcnow().isoformat()
        })

    state["inventory"] = inventory
    save_state(user["id"], state)

    return {
        "message": f"Inventory updated for {body.medication_name}",
        "medication_name": body.medication_name,
        "new_quantity": body.quantity,
        "inventory": inventory
    }
