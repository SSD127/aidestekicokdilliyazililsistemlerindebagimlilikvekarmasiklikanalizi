import numpy as np
import json

class ComplexityAnalyzer:
    def __init__(self, function_payload):
        """
        Salih'in Parser AST Schema'sındaki 'FunctionEntry' objesini içeri alır.
        """
        self.veri = function_payload

    def hesapla_mccabe(self):
        """
        Şemadaki branch ve loop verilerini kullanarak anında hesaplama yapar (O(1) Performans).
        Formül: Karar Yolları + Döngüler + 1
        """
        branch_sayisi = self.veri.get("branch_count", 0)
        loop_sayisi = self.veri.get("loop_count", 0)
        
        return branch_sayisi + loop_sayisi + 1

    def hesapla_halstead(self):
        """
        Halstead Metrikleri. (Salih'ten talep edilen güncel veriler eklendiğinde tam uyumlu çalışacak)
        """
        n1 = self.veri.get("unique_operators", 0)
        n2 = self.veri.get("unique_operands", 0)
        N1 = self.veri.get("total_operators", 0)
        N2 = self.veri.get("total_operands", 0)

        n = n1 + n2
        N = N1 + N2

        if n == 0 or n2 == 0:
            return {"Hacim": 0.0, "Zorluk": 0.0, "Efor": 0.0}

        hacim = N * np.log2(n)
        zorluk = (n1 / 2.0) * (N2 / float(n2))
        efor = zorluk * hacim

        return {
            "Hacim": float(round(hacim, 2)),
            "Zorluk": float(round(zorluk, 2)),
            "Efor": float(round(efor, 2))
        }

    def hesapla_icc(self, loc_total):
        """
        IEEE 2024 Makalesi: Geliştirilmiş Siklomatik Karmaşıklık (Karmaşıklık Yoğunluğu)
        """
        f = 1 # Bu fonksiyon bazlı bir analiz olduğu için fonksiyon sayısı 1
        i = len(self.veri.get("parameters", [])) # Girdi sayısı (Parametre listesinin uzunluğu)
        o = self.veri.get("return_count", 1)     # Çıktı sayısı
        S_x = self.veri.get("executable_lines", 0) # Çalışan satır sayısı
        
        if loc_total <= 0:
            return 0.0
            
        icc_skoru = (f + S_x + i + o) / float(loc_total)
        return float(round(icc_skoru, 3))

    def hesapla_risk_skoru(self, mccabe, halstead_efor):
        """
        Literatüre dayalı risk ağırlıklandırması (Maksimum 100).
        """
        risk = 0.0
        if mccabe > 20: risk += 50.0
        elif mccabe > 10: risk += 25.0
            
        if halstead_efor > 10000: risk += 50.0
        elif halstead_efor > 5000: risk += 25.0
            
        return min(risk, 100.0)

    def analiz_raporu_uret(self, dosya_loc_degeri=100):
        """
        Çağrı'nın veritabanına ('functions' dizisine) gidecek nihai JSON formatını üretir.
        """
        mccabe_sonuc = self.hesapla_mccabe()
        halstead_sonuc = self.hesapla_halstead()
        icc_sonuc = self.hesapla_icc(dosya_loc_degeri)
        risk_sonuc = self.hesapla_risk_skoru(mccabe_sonuc, halstead_sonuc["Efor"])

        return {
            "function_name": self.veri.get("name", "unknown_function"),
            "cyclomatic_complexity": int(mccabe_sonuc),
            "halstead_score": float(halstead_sonuc["Efor"]),
            "icc_density": float(icc_sonuc),
            "risk_score": float(risk_sonuc)
        }


# ==========================================
# GITHUB İÇİN TEST (MOCK) ÇALIŞTIRMASI
# ==========================================
ornek_function_entry = {
    # Şemadan gelen kesin veriler
    "name": "create_run",
    "branch_count": 8,
    "loop_count": 4,
    "parameters": [{"name": "project_id"}, {"name": "config"}], # 2 Parametre
    
    # Salih'ten istediğimiz yeni veriler (Mock)
    "unique_operators": 14,
    "unique_operands": 10,
    "total_operators": 55,
    "total_operands": 40,
    "return_count": 2,
    "executable_lines": 28
}

motor = ComplexityAnalyzer(ornek_function_entry)
# Dosya genelinde 120 satır kod olduğunu varsayarak rapor üretiyoruz:
sonuc = motor.analiz_raporu_uret(dosya_loc_degeri=120)

print(json.dumps(sonuc, indent=2, ensure_ascii=False))