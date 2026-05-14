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

# Risk seviyesi için tip tanımı
RiskLevel = Literal["low", "moderate", "high", "critical"]

# Halstead Effort katkısı için bölücü; Effort/HALSTEAD_DIVISOR puana eklenir
HALSTEAD_DIVISOR = 1000.0

# Halstead katkısı için üst sınır — çok büyük dosyalarda CC'yi tamamen ezmesin
HALSTEAD_MAX_CONTRIBUTION = 50.0

def calculate_risk_level(cyclomatic_complexity: int, halstead_score: float = 0.0) -> RiskLevel:
    """
    Halil'in Metric Engine risk değerlendirme sistemi ile Salih'in UI görsel oranlarını
    birleştiren nihai risk hesaplama fonksiyonu.

    Cyclomatic complexity ve Halstead Effort skorundan risk seviyesi hesaplar.

    Skor McCabe V(G) ile özdeş değildir; McCabe (1976) bantları docstring'teki
    modül açıklamasında referans alınır; kesitler bileşik puana uygulanır.
    """
    risk_puani = 0.0

    # 1. Halil'in McCabe Risk Kontrolü (Literatür: 10 ve 20 Sınırları)
    if cyclomatic_complexity > 20: 
        risk_puani += 50.0
    elif cyclomatic_complexity > 10: 
        risk_puani += 25.0
    else:
        # cc 10'un altındaysa sadece cc kadar puan ekle
        risk_puani += cyclomatic_complexity

    # 2. Salih'in Frontend Oranlaması (Halstead için 1000'e bölüp 50 ile sınırlama)
    halstead_part = min(halstead_score / HALSTEAD_DIVISOR, HALSTEAD_MAX_CONTRIBUTION)
    risk_puani += halstead_part

    # 3. Sonuçların Risk Sınıflarına Bölünmesi
    if risk_puani >= 25:
        return "critical"
    elif risk_puani >= 15:
        return "high"
    elif risk_puani >= 8:
        return "moderate"
    else:
        return "low"