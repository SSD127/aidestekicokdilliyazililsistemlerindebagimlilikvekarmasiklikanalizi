from typing import Literal

RiskLevel = Literal["low", "moderate", "high", "critical"]


def calculate_risk_level(cyclomatic_complexity: int, halstead_score: float = 0.0) -> RiskLevel:
    """
    Complexity + halstead agirlikli basit risk siniflandirmasi.
    Esikler: low <8 | moderate 8-14 | high 15-24 | critical 25+
    """
    score = cyclomatic_complexity + (halstead_score / 100)
    if score >= 25:
        return "critical"
    if score >= 15:
        return "high"
    if score >= 8:
        return "moderate"
    return "low"


def risk_label_tr(level: RiskLevel) -> str:
    return {
        "low": "Dusuk Risk",
        "moderate": "Orta Risk",
        "high": "Yuksek Risk",
        "critical": "Kritik Risk",
    }[level]
