"""
risk.py — Fonksiyon Risk Seviyesi Hesaplama

Bu dosya cyclomatic complexity ve Halstead skorunu birleştirerek
bir fonksiyon için risk seviyesi (low/moderate/high/critical) üretir.

Risk seviyeleri:
  - low      : Skor < 8    → Düşük risk, normal fonksiyon
  - moderate : Skor 8-14   → Orta risk, gözlem altında tutulmalı
  - high     : Skor 15-24  → Yüksek risk, refactor önerilir
  - critical : Skor >= 25  → Kritik, acil müdahale gerekir

Gerçek metrik motoru (McCabe/Halstead) entegre edildiğinde
eşik değerleri bu dosyadan kalibre edilecektir.
"""

from typing import Literal

# Risk seviyesi için tip tanımı
RiskLevel = Literal["low", "moderate", "high", "critical"]


def calculate_risk_level(cyclomatic_complexity: int, halstead_score: float = 0.0) -> RiskLevel:
    """
    Cyclomatic complexity ve Halstead skorundan ağırlıklı risk seviyesi hesaplar.

    Args:
        cyclomatic_complexity: McCabe karmaşıklık değeri (>=0)
        halstead_score: Halstead effort skoru (opsiyonel, varsayılan 0)

    Returns:
        RiskLevel: "low" | "moderate" | "high" | "critical"
    """
    # Halstead skoru 100'de 1 ağırlıkla toplam skora eklenir
    score = cyclomatic_complexity + (halstead_score / 100)

    if score >= 25:
        return "critical"
    if score >= 15:
        return "high"
    if score >= 8:
        return "moderate"
    return "low"


def risk_label_tr(level: RiskLevel) -> str:
    # Risk seviyesini Türkçe etiket olarak döndürür; frontend gösterimi için
    return {
        "low": "Dusuk Risk",
        "moderate": "Orta Risk",
        "high": "Yuksek Risk",
        "critical": "Kritik Risk",
    }[level]
