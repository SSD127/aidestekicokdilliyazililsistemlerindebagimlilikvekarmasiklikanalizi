"""
risk.py — Fonksiyon Risk Seviyesi Hesaplama

Cyclomatic complexity ve Halstead Effort skorunu birleştirerek bir fonksiyon
için risk seviyesi (low/moderate/high/critical) üretir.

Literatür (saf cyclomatic complexity V(G)):
    Thomas J. McCabe, "A Complexity Measure", IEEE Transactions on Software
    Engineering, Vol. SE-2, No. 4, December 1976. Makaledeki V(G) yorumlarında
    sık atıfta bulunulan bantlar: düşük (yaklaşık 1–10), orta (11–20),
    yüksek (21–50), çok yüksek / pratikte testi zor (50 üzeri).

Bu modüldeki skor bileşiktir; McCabe bantları doğrudan yalnızca V(G) içindir.

Risk skoru formülü:
    halstead_part = min(halstead_effort / HALSTEAD_DIVISOR, HALSTEAD_MAX_CONTRIBUTION)
    score = cyclomatic_complexity + halstead_part

Halstead Effort tipik olarak küçük fonksiyonlarda 100-1000, orta fonksiyonlarda
1000-10000, çok karmaşık fonksiyonlarda 10000+ aralığına çıkar. 1000'e bölme
Effort'un katkısını CC ile aynı mertebede tutar; üst sınır (HALSTEAD_MAX_CONTRIBUTION)
CC'yi baskılamayı önler.

Risk seviyeleri (bileşik score için mühendislik eşikleri; V(G) rehberliği ve
sınırlı Halstead katkısıyla kalibre edilmiştir):
  - low      : Skor < 8    → Düşük risk, normal fonksiyon
  - moderate : Skor 8-14   → Orta risk, gözlem altında tutulmalı
  - high     : Skor 15-24  → Yüksek risk, refactor önerilir
  - critical : Skor >= 25  → Kritik, acil müdahale gerekir
"""

from typing import Literal

RiskLevel = Literal["low", "moderate", "high", "critical"]

# Halstead Effort katkısı için bölücü; Effort/HALSTEAD_DIVISOR puana eklenir
HALSTEAD_DIVISOR = 1000.0
# Halstead katkısı için üst sınır — çok büyük dosyalarda CC'yi tamamen ezmesin
HALSTEAD_MAX_CONTRIBUTION = 50.0


def calculate_risk_level(cyclomatic_complexity: int, halstead_score: float = 0.0) -> RiskLevel:
    """
    Cyclomatic complexity ve Halstead Effort skorundan risk seviyesi hesaplar.

    Skor McCabe V(G) ile özdeş değildir; McCabe (1976) bantları docstring'teki
    modül açıklamasında referans alınır; kesitler bileşik puana uygulanır.
    """
    halstead_part = min(halstead_score / HALSTEAD_DIVISOR, HALSTEAD_MAX_CONTRIBUTION)
    score = cyclomatic_complexity + halstead_part

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
