"""
LLM layer (Groq or Gemini): used ONLY to summarize trends for caregivers.
Does NOT diagnose, prescribe, or override rules. Called only when alerts exist.

Provider selection: GROQ_API_KEY is used if set, otherwise GEMINI_API_KEY,
otherwise a safe rule-based fallback summary.
"""
import logging
import os
from typing import Any, List

import httpx

logger = logging.getLogger(__name__)

# Optional: only used when GEMINI_API_KEY is set
_gemini_model = None

# Hard cap on how long a single LLM call may take; a slow or unreachable API
# must never hang a request (summaries fall back to the rule-based text).
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "20"))

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _groq_generate(prompt: str, max_tokens: int) -> str | None:
    """Call Groq's OpenAI-compatible chat API. Returns None on any failure."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        resp = httpx.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return text.strip() if text else None
    except Exception as e:
        logger.warning("Groq generate failed: %s", e)
        return None


def _get_model():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        return _gemini_model
    except Exception as e:
        logger.warning("Gemini not available: %s", e)
        return None


def generate_caregiver_summary(
    patient_data: dict,
    alerts: List[str],
    historical_context: dict = None,
    max_tokens: int = 1500,
) -> str:
    """
    Generate a detailed plain-language summary for the caregiver.
    Called only when alerts exist. Does not give medical advice or diagnosis.
    Now includes historical context for comprehensive analysis.
    """
    if not alerts:
        return "No alerts at this time. Patient data is within expected ranges."

    prompt = _build_prompt(patient_data, alerts, historical_context)

    # Groq first (if configured), then Gemini, then rule-based fallback
    groq_text = _groq_generate(prompt, max_tokens)
    if groq_text:
        return groq_text

    model = _get_model()
    if model is None:
        return _fallback_summary(alerts, patient_data, historical_context)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.3,
            },
            request_options={"timeout": LLM_TIMEOUT_SECONDS},
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logger.warning("Gemini generate_caregiver_summary failed: %s", e)

    return _fallback_summary(alerts, patient_data, historical_context)


def _build_prompt(patient_data: dict, alerts: List[str], historical_context: dict = None) -> str:
    # Keep patient data minimal for privacy; no raw vitals in prompt if sensitive
    profile = patient_data.get("patient_profile") or {}
    name = profile.get("name") or "Patient"
    age = profile.get("age") or "Not specified"
    conditions = profile.get("conditions") or "Not specified"
    med_list = patient_data.get("medications") or []
    med_names = [m.get("name") or m.get("id") for m in med_list if m][:10]
    
    # Build historical context section
    historical_section = ""
    if historical_context:
        adherence = historical_context.get("adherence", {})
        vital_trends = historical_context.get("vital_trends", {})
        wellbeing = historical_context.get("wellbeing", {})
        comparative = historical_context.get("comparative", {})
        
        historical_section = f"""
Historical Context (Past 7 days):
- Medication Adherence: {adherence.get('overall_rate', 'N/A')}% (taken {adherence.get('total_taken', 0)} of {adherence.get('total_expected', 0)} expected doses)
- Vital Trends: {_format_vital_trends(vital_trends)}
- Wellbeing: {wellbeing.get('most_common_feeling', 'Not recorded')} (most common feeling)
- Comparative Analysis: {_format_comparative(comparative)}
"""

    return f"""You are creating a detailed intelligence report for a caregiver monitoring an elderly patient. 
Do NOT give medical advice, diagnosis, or prescribe. Focus on observations and practical suggestions.

Structure your response in the following sections:
1. **OVERVIEW** (2-3 sentences): Brief summary of the patient's current status
2. **KEY TRENDS** (3-4 bullet points): Important patterns from historical data
3. **AREAS OF CONCERN** (2-3 bullet points): Issues that need attention
4. **RECOMMENDATIONS** (3-4 bullet points): Practical next steps for the caregiver

Current Alerts (rule-based, already decided by the system):
{chr(10).join('- ' + a for a in alerts)}

Patient Profile:
- Name: {name}
- Age: {age}
- Conditions: {conditions}
- Medications: {', '.join(str(m) for m in med_names) if med_names else 'None listed'}
{historical_section}

Write a comprehensive but clear report. Use simple language that a non-medical caregiver can understand. 
Focus on actionable insights and patterns that help the caregiver provide better care."""


def _format_vital_trends(vital_trends: dict) -> str:
    """Format vital trends for prompt."""
    if not vital_trends or not vital_trends.get("metrics"):
        return "No recent data"
    
    metrics = vital_trends.get("metrics", {})
    parts = []
    
    for metric, data in metrics.items():
        trend = data.get("trend", "stable")
        avg = data.get("average", "N/A")
        parts.append(f"{metric.replace('_', ' ').title()}: {avg} ({trend})")
    
    return ", ".join(parts) if parts else "No data"


def _format_comparative(comparative: dict) -> str:
    """Format comparative analysis for prompt."""
    if not comparative or not comparative.get("comparisons"):
        return "No comparison data"
    
    comparisons = comparative.get("comparisons", {})
    parts = []
    
    for metric, data in comparisons.items():
        direction = data.get("direction", "stable")
        change_pct = data.get("change_percent", 0)
        parts.append(f"{metric.replace('_', ' ').title()}: {direction} by {abs(change_pct):.1f}%")
    
    return ", ".join(parts) if parts else "No changes"


def _fallback_summary(alerts: List[str], patient_data: dict, historical_context: dict = None) -> str:
    """When Gemini is unavailable, return a safe rule-based summary with historical context."""
    lines = [
        "📊 **PATIENT INTELLIGENCE REPORT**",
        "",
        "**CURRENT ALERTS:**",
    ]
    for a in alerts:
        lines.append(f"• {a}")
    
    lines.append("")
    
    if historical_context:
        adherence = historical_context.get("adherence", {})
        vital_trends = historical_context.get("vital_trends", {})
        
        lines.append("**HISTORICAL TRENDS (7 days):**")
        lines.append(f"• Medication Adherence: {adherence.get('overall_rate', 'N/A')}%")
        
        if vital_trends.get("metrics"):
            for metric, data in vital_trends["metrics"].items():
                trend = data.get("trend", "stable")
                avg = data.get("average", "N/A")
                lines.append(f"• {metric.replace('_', ' ').title()}: Average {avg}, trend {trend}")
        
        lines.append("")
    
    lines.extend([
        "**RECOMMENDATIONS:**",
        "• Monitor the patient closely for the noted alerts",
        "• Ensure medications are taken as prescribed",
        "• Track vital signs regularly",
        "• Consider a routine checkup if patterns persist",
        "",
        "Note: This is automated analysis, not medical advice. Consult healthcare professionals for medical decisions.",
    ])
    return "\n".join(lines)

