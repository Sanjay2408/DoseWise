# Intelligence layer: trend detection (rule-based) + LLM explainer (Gemini)
from app.intelligence.trend_analyzer import detect_trends, get_vitals_by_date, detect_trends_for_day
from app.intelligence.risk_assessor import assess_severity
from app.intelligence.llm_explainer import generate_caregiver_summary

__all__ = ["detect_trends", "get_vitals_by_date", "detect_trends_for_day", "assess_severity", "generate_caregiver_summary"]
