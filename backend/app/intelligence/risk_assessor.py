"""
Severity classification for trend alerts. Rule-based only.
"""
from typing import List

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"


def assess_severity(alerts: List[str]) -> str:
    """
    Classify overall severity from list of alert strings.
    Returns one of: low, medium, high, critical.
    """
    if not alerts:
        return SEVERITY_LOW

    critical_keywords = ("critical", "out of stock", "emergency", "unresponsive")
    high_keywords = ("sustained high bp", "sugar instability", "abnormal vitals", "repeatedly", "escalat")
    medium_keywords = ("missed", "low", "unwell", "inventory")

    for a in alerts:
        lower = a.lower()
        if any(k in lower for k in critical_keywords):
            return SEVERITY_CRITICAL
    for a in alerts:
        lower = a.lower()
        if any(k in lower for k in high_keywords):
            return SEVERITY_HIGH
    for a in alerts:
        lower = a.lower()
        if any(k in lower for k in medium_keywords):
            return SEVERITY_MEDIUM

    return SEVERITY_LOW
