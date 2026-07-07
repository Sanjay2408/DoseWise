"""
Historical data analyzer for patient trends and patterns.
Provides detailed analytics for caregiver intelligence reports.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def calculate_adherence_rate(
    medications: List[Dict[str, Any]],
    vitals: List[Dict[str, Any]],
    days: int = 7
) -> Dict[str, Any]:
    """
    Calculate medication adherence rate over the specified period.
    Returns overall adherence percentage and per-medication breakdown.
    """
    if not medications:
        return {"overall_rate": 100.0, "by_medication": {}, "total_expected": 0, "total_taken": 0}
    
    # Count medications with last_taken_at in the period
    now = datetime.now()
    # Use 36h window to allow for next-morning review of last night's dose
    cutoff = now - timedelta(hours=36)
    
    # Limitation: We currently only track last_taken_at, so we can only accurately calculate
    # adherence for the immediate past. Calculating for >1 day incorrectly penalizes
    # because we don't store a full history log.
    # We fix the window to 1 day for calculation purposes until dose history is implemented.
    calculation_days = 1 
    
    total_expected = len(medications) * calculation_days
    total_taken = 0
    by_medication = {}
    
    for med in medications:
        med_name = med.get("name", "Unknown")
        last_taken = med.get("last_taken_at")
        
        # Simplified adherence: if taken recently, count as adhering
        if last_taken:
            try:
                if isinstance(last_taken, str):
                    taken_dt = datetime.fromisoformat(last_taken.replace('Z', '+00:00'))
                else:
                    taken_dt = last_taken
                
                if taken_dt >= cutoff:
                    total_taken += 1
                    by_medication[med_name] = "Recent dose taken"
                else:
                    by_medication[med_name] = "No recent dose"
            except Exception:
                by_medication[med_name] = "Unknown"
        else:
            by_medication[med_name] = "Never taken"
    
    overall_rate = (total_taken / total_expected * 100) if total_expected > 0 else 100.0
    
    return {
        "overall_rate": round(overall_rate, 1),
        "by_medication": by_medication,
        "total_expected": total_expected,
        "total_taken": total_taken,
        "period_days": days
    }


def analyze_vital_trends(vitals: List[Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    """
    Analyze vital sign trends over the specified period.
    Returns trend direction, average values, and ranges.
    """
    if not vitals:
        return {"trend": "no_data", "metrics": {}}
    
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    
    # Filter vitals within the period
    recent_vitals = []
    for v in vitals:
        recorded = v.get("recorded_at") or v.get("timestamp")
        if recorded:
            try:
                if isinstance(recorded, str):
                    rec_dt = datetime.fromisoformat(recorded.replace('Z', '+00:00'))
                else:
                    rec_dt = recorded
                
                if rec_dt >= cutoff:
                    recent_vitals.append(v)
            except Exception:
                pass
    
    if not recent_vitals:
        return {"trend": "no_recent_data", "metrics": {}, "count": 0}
    
    # Analyze blood pressure
    bp_values = []
    hr_values = []
    temp_values = []
    
    for v in recent_vitals:
        if v.get("blood_pressure"):
            try:
                systolic = int(v["blood_pressure"].split("/")[0])
                bp_values.append(systolic)
            except Exception:
                pass
        
        if v.get("heart_rate"):
            try:
                hr_values.append(float(v["heart_rate"]))
            except Exception:
                pass
        
        if v.get("temperature"):
            try:
                temp_values.append(float(v["temperature"]))
            except Exception:
                pass
    
    metrics = {}
    
    if bp_values:
        metrics["blood_pressure"] = {
            "average": round(sum(bp_values) / len(bp_values), 1),
            "min": min(bp_values),
            "max": max(bp_values),
            "trend": _calculate_trend(bp_values)
        }
    
    if hr_values:
        metrics["heart_rate"] = {
            "average": round(sum(hr_values) / len(hr_values), 1),
            "min": min(hr_values),
            "max": max(hr_values),
            "trend": _calculate_trend(hr_values)
        }
    
    if temp_values:
        metrics["temperature"] = {
            "average": round(sum(temp_values) / len(temp_values), 1),
            "min": min(temp_values),
            "max": max(temp_values),
            "trend": _calculate_trend(temp_values)
        }
    
    return {
        "trend": "analyzed",
        "metrics": metrics,
        "count": len(recent_vitals),
        "period_days": days
    }


def _calculate_trend(values: List[float]) -> str:
    """Calculate if values are increasing, decreasing, or stable."""
    if len(values) < 2:
        return "stable"
    
    # Simple linear trend: compare first half to second half
    mid = len(values) // 2
    first_half_avg = sum(values[:mid]) / mid if mid > 0 else 0
    second_half_avg = sum(values[mid:]) / (len(values) - mid) if len(values) > mid else 0
    
    diff_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
    
    if diff_pct > 5:
        return "increasing"
    elif diff_pct < -5:
        return "decreasing"
    else:
        return "stable"


def analyze_wellbeing_patterns(wellbeing_log: List[Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    """
    Analyze wellbeing/mood patterns over time.
    """
    if not wellbeing_log:
        return {"pattern": "no_data", "entries": 0}
    
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    
    recent_entries = []
    for entry in wellbeing_log:
        recorded = entry.get("recorded_at")
        if recorded:
            try:
                if isinstance(recorded, str):
                    rec_dt = datetime.fromisoformat(recorded.replace('Z', '+00:00'))
                else:
                    rec_dt = recorded
                
                if rec_dt >= cutoff:
                    recent_entries.append(entry)
            except Exception:
                pass
    
    if not recent_entries:
        return {"pattern": "no_recent_data", "entries": 0}
    
    # Count feelings
    feelings = {}
    for entry in recent_entries:
        feeling = entry.get("feeling", "").lower()
        if feeling:
            feelings[feeling] = feelings.get(feeling, 0) + 1
    
    most_common = max(feelings.items(), key=lambda x: x[1])[0] if feelings else "unknown"
    
    return {
        "pattern": "analyzed",
        "entries": len(recent_entries),
        "most_common_feeling": most_common,
        "feeling_distribution": feelings,
        "period_days": days
    }


def generate_comparative_summary(
    current_vitals: List[Dict[str, Any]],
    historical_vitals: List[Dict[str, Any]],
    current_days: int = 7,
    historical_days: int = 14
) -> Dict[str, Any]:
    """
    Compare current period vitals to historical period.
    Returns week-over-week or period-over-period changes.
    """
    current_analysis = analyze_vital_trends(current_vitals, current_days)
    historical_analysis = analyze_vital_trends(historical_vitals, historical_days)
    
    comparisons = {}
    
    for metric in ["blood_pressure", "heart_rate", "temperature"]:
        if metric in current_analysis.get("metrics", {}) and metric in historical_analysis.get("metrics", {}):
            current_avg = current_analysis["metrics"][metric]["average"]
            historical_avg = historical_analysis["metrics"][metric]["average"]
            
            change = current_avg - historical_avg
            change_pct = (change / historical_avg * 100) if historical_avg > 0 else 0
            
            comparisons[metric] = {
                "current_average": current_avg,
                "historical_average": historical_avg,
                "change": round(change, 1),
                "change_percent": round(change_pct, 1),
                "direction": "increased" if change > 0 else "decreased" if change < 0 else "stable"
            }
    
    return {
        "comparisons": comparisons,
        "current_period_days": current_days,
        "historical_period_days": historical_days
    }
