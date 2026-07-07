"""
Rule-based trend detection. Primary decision maker for escalation.
Does NOT use LLM. Deterministic and safe.
"""
from datetime import datetime, timedelta
from typing import Any, List


def _parse_dt(recorded_at: Any) -> datetime | None:
    if recorded_at is None:
        return None
    if isinstance(recorded_at, datetime):
        return recorded_at
    try:
        s = str(recorded_at).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _get_vitals_by_day(vitals: List[dict], days: int = 7) -> dict:
    """Group vitals by date (YYYY-MM-DD) for the last N days."""
    today = datetime.utcnow().date()
    by_day: dict[str, List[dict]] = {}
    for v in vitals or []:
        dt = _parse_dt(v.get("recorded_at") or v.get("timestamp"))
        if dt is None:
            continue
        d = dt.date() if hasattr(dt, "date") else dt
        if (today - d).days > days:
            continue
        key = str(d)
        if key not in by_day:
            by_day[key] = []
        by_day[key].append(v)
    return by_day


def _is_bp_high(val: Any, sys_high: int = 140, dia_high: int = 90) -> bool:
    """True if value represents high BP (systolic > sys_high or diastolic > dia_high)."""
    if val is None:
        return False
    try:
        if isinstance(val, (int, float)):
            return float(val) > sys_high
        s = str(val).replace(" ", "").strip()
        if "/" in s:
            parts = s.split("/")
            if len(parts) >= 1 and parts[0].isdigit() and int(parts[0]) > sys_high:
                return True
            if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) > dia_high:
                return True
        return False
    except (ValueError, TypeError):
        return False


def _last_n_days_bp_high(vitals: List[dict], n: int = 3, sys_high: int = 140, dia_high: int = 90) -> bool:
    """True if BP is high on each of the last n days we have data for."""
    by_day = _get_vitals_by_day(vitals, days=14)
    if len(by_day) < n:
        return False
    dates = sorted(by_day.keys(), reverse=True)[:n]
    for d in dates:
        found_high = False
        for v in by_day[d]:
            val = v.get("value") or v.get("blood_pressure")
            if _is_bp_high(val, sys_high, dia_high):
                found_high = True
                break
        if not found_high:
            return False
    return True


def _sugar_spikes_after_missed_dose(
    vitals: List[dict], medications: List[dict], missed_dose_dates: List[str]
) -> bool:
    """True if sugar (glucose) spikes appear after known missed dose dates."""
    if not missed_dose_dates or not vitals:
        return False
    spike_threshold = 180  # mg/dL
    for v in vitals or []:
        kind = (v.get("type") or v.get("metric") or "").lower()
        if "sugar" not in kind and "glucose" not in kind and "blood_sugar" not in kind:
            continue
        val = v.get("value")
        try:
            num = float(val) if val is not None else None
        except (TypeError, ValueError):
            continue
        if num is None or num < spike_threshold:
            continue
        dt = _parse_dt(v.get("recorded_at") or v.get("timestamp"))
        if dt is None:
            continue
        d = str(dt.date()) if hasattr(dt, "date") else str(dt)[:10]
        if d in missed_dose_dates or any(d <= md for md in missed_dose_dates):
            return True
    return False


def _repeated_low_wellbeing(wellbeing_log: List[dict], min_count: int = 3, low_keywords: tuple = ("unwell", "not well", "bad", "poor", "low")) -> bool:
    """True if patient reported low wellbeing repeatedly."""
    if not wellbeing_log or len(wellbeing_log) < min_count:
        return False
    low_count = 0
    for w in wellbeing_log:
        feeling = (w.get("feeling") or w.get("wellbeing") or w.get("mood") or "").lower()
        if any(kw in feeling for kw in low_keywords) or (feeling and feeling in ("2", "1", "poor")):
            low_count += 1
    return low_count >= min_count


def _inventory_repeatedly_low(inventory: List[dict], threshold_count: int = 2) -> bool:
    """True if multiple meds are low stock or same med low in recent history (simplified: any low)."""
    if not inventory:
        return False
    low = [i for i in inventory if (i.get("quantity") or 0) <= (i.get("low_stock_threshold") or i.get("low_threshold") or 10)]
    return len(low) >= threshold_count or len(low) >= 1 and len(inventory) <= 2


def detect_trends(
    vitals_history: List[dict],
    medications: List[dict] | None = None,
    inventory: List[dict] | None = None,
    wellbeing_log: List[dict] | None = None,
    missed_dose_dates: List[str] | None = None,
) -> List[str]:
    """
    Rule-based trend detection. Returns list of alert strings.
    Used to decide escalation; LLM is NOT involved in this step.
    """
    alerts: List[str] = []
    vitals = vitals_history or []
    medications = medications or []
    inventory = inventory or []
    wellbeing_log = wellbeing_log or []
    missed_dose_dates = missed_dose_dates or []

    if _last_n_days_bp_high(vitals, n=3):
        alerts.append("Sustained high BP over the last 3 days")

    if _sugar_spikes_after_missed_dose(vitals, medications, missed_dose_dates):
        alerts.append("Sugar instability linked to missed medication")

    if _repeated_low_wellbeing(wellbeing_log, min_count=2):
        alerts.append("Patient reports feeling unwell repeatedly")

    if _inventory_repeatedly_low(inventory):
        alerts.append("Inventory repeatedly low for one or more medications")

    return alerts


def get_vitals_by_date(vitals: List[dict], target_date: str) -> List[dict]:
    """Return vitals entries for a single date (YYYY-MM-DD)."""
    out: List[dict] = []
    for v in vitals or []:
        dt = _parse_dt(v.get("recorded_at") or v.get("timestamp"))
        if dt is None:
            continue
        d = str(dt.date()) if hasattr(dt, "date") else str(dt)[:10]
        if d == target_date:
            out.append(v)
    return out


def detect_trends_for_day(
    vitals_for_day: List[dict],
    all_vitals: List[dict],
    patient_profile: dict,
    medications: List[dict],
    inventory: List[dict],
    wellbeing_for_day: List[dict],
) -> List[str]:
    """
    Rule-based trend detection for a single day's report.
    Uses that day's vitals and conditions from profile to tailor alerts.
    """
    conditions = (patient_profile or {}).get("conditions") or ""
    conditions_lower = conditions.lower()
    alerts: List[str] = []

    # BP: flag if hypertension in conditions and any BP high that day
    if "hypertension" in conditions_lower or "blood pressure" in conditions_lower or "bp" in conditions_lower:
        for v in vitals_for_day:
            val = v.get("value") or v.get("blood_pressure")
            if _is_bp_high(val, sys_high=140, dia_high=90):
                alerts.append("Elevated blood pressure recorded today")
                break

    # Sugar: flag if diabetes in conditions and any sugar high
    if "diabetes" in conditions_lower or "sugar" in conditions_lower or "glucose" in conditions_lower:
        for v in vitals_for_day:
            kind = (v.get("type") or v.get("metric") or "").lower()
            if "sugar" not in kind and "glucose" not in kind:
                continue
            try:
                num = float(v.get("value") or 0)
                if num > 180:
                    alerts.append("Elevated blood sugar recorded today")
                    break
            except (TypeError, ValueError):
                pass

    # General trend checks on that day's data
    day_alerts = detect_trends(
        vitals_history=vitals_for_day,
        medications=medications,
        inventory=inventory,
        wellbeing_log=wellbeing_for_day,
        missed_dose_dates=[],
    )
    for a in day_alerts:
        if a not in alerts:
            alerts.append(a)

    return alerts
