import numpy as np

class ComplexityAnalyzer:
    def __init__(self, function_payload):
        """
        Salih'in v1.1.0 Parser sözleşmesinden gelen veriyi alır.
        """
        self.veri = function_payload if isinstance(function_payload, dict) else {}

    def hesapla_mccabe(self):
        """
        M = Branch + Loop + 1
        """
        return self.veri.get("branch_count", 0) + self.veri.get("loop_count", 0) + 1

    def hesapla_halstead(self):
        """
        Salih'in yeni eklediği Halstead alanlarını kullanır.
        """
        # Salih'in v1.1.0 ile gönderdiği gerçek anahtarlar:
        n1 = self.veri.get("unique_operators", 0)
        N1 = self.veri.get("total_operators", 0)
        n2 = self.veri.get("unique_operands", 0)
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
        IEEE 2024 ICC: Salih'in yeni return_count ve executable_lines verilerini işler.
        """
        f = 1  # Fonksiyonun kendisi
        i = len(self.veri.get("parameters", []))
        
        # Salih'in v1.1.0 ile eklediği yeni ICC alanları:
        o = self.veri.get("return_count", 1)
        S_x = self.veri.get("executable_lines", 0)
        
        if loc_total <= 0:
            return 0.0
            
        icc_skoru = (f + S_x + i + o) / float(loc_total)
        return float(round(icc_skoru, 3))

    def hesapla_risk_skoru(self, mccabe, halstead_efor):
        """
        Karmaşıklık ve Efor limitlerine göre 100 üzerinden risk puanı.
        """
        risk = 0.0
        # McCabe limitleri (Literatür: 10 ve 20)
        if mccabe > 20: risk += 50.0
        elif mccabe > 10: risk += 25.0
            
        # Halstead Efor limitleri (Literatür: 5000 ve 10000)
        if halstead_efor > 10000: risk += 50.0
        elif halstead_efor > 5000: risk += 25.0
            
        return min(risk, 100.0)

    def analiz_raporu_uret(self, dosya_loc_degeri=100):
        """
        Tüm metrikleri birleştirip nihai JSON raporunu oluşturur.
        """
        mccabe_sonuc = self.hesapla_mccabe()
        halstead_sonuc = self.hesapla_halstead()
        icc_sonuc = self.hesapla_icc(dosya_loc_degeri)
        risk_sonuc = self.hesapla_risk_skoru(mccabe_sonuc, halstead_sonuc["Efor"])

        return {
            "function_name": self.veri.get("name", "unknown"),
            "cyclomatic_complexity": int(mccabe_sonuc),
            "halstead_score": float(halstead_sonuc["Efor"]),
            "icc_density": float(icc_sonuc),
            "risk_score": float(risk_sonuc)
        }