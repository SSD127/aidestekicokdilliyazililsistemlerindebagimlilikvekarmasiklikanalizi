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