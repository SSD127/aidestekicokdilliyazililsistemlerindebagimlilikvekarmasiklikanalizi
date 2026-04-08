# Çok Dilli Yazılım Sistemlerinde AI Destekli Karmaşıklık ve Bağımlılık Analizi

## 🏗️ Proje Yapısı

```
project-root/
│
├── dependency-analyzer/          # 📦 Bağımlılık Analizi Modülü (Aktif)
│   ├── analyzer.py               #    AST tabanlı import ayrıştırıcı
│   ├── graph.py                  #    NetworkX grafik modeli + döngü tespiti
│   ├── visualizer.py             #    Matplotlib görselleştirme + terminal raporu
│   ├── dependency_map.png        #    Örnek çıktı görseli
│   └── test_project/             #    Test senaryosu (kasıtlı döngüsel bağımlılık)
│       ├── a.py
│       ├── b.py
│       └── c.py
│
├── complexity-analyzer/          # 📦 Karmaşıklık Analizi Modülü (Henüz eklenmedi)
│   └── ...
│
└── README.md
```


##  Kurulum

### Gereksinimler

- Python **3.8** veya üzeri

### Adımlar

```bash
# 1. Depoyu klonlayın
git clone <repo-url>
cd <proje-klasörü>

# 2. Gerekli kütüphaneleri yükleyin
pip install networkx matplotlib
```

> 📌 `ast`, `os`, `sys` ve `tkinter` Python standart kütüphanesindedir, ek kurulum gerektirmez.

---

## Bağımlılık Analizi

Bir Python projesindeki `import` / `from ... import` ilişkilerini tarayarak **yönlü grafik (directed graph)** modeline dönüştürür ve **döngüsel bağımlılıkları (circular dependencies)** otomatik tespit eder.

### Nasıl Çalışır?

```
Klasör Seçimi ──▶ .py Dosyalarını Tara ──▶ AST ile Import Çıkar ──▶ Grafik Kur ──▶ Döngü Tespit Et ──▶ Görselleştir
```

| Adım | Dosya | Açıklama |
|---|---|---|
| 1 | `analyzer.py` | Python AST modülü ile kaynak kodu parse eder, `import X` ve `from X import Y` ifadelerini çıkarır |
| 2 | `graph.py` | NetworkX `DiGraph` yapısı ile düğüm (dosya) ve kenar (bağımlılık) ilişkilerini modeller, `simple_cycles()` ile döngü tespit eder |
| 3 | `visualizer.py` | Terminal raporu yazar + Matplotlib ile koyu temalı, renk kodlu bağımlılık haritası çizer |

### Çalıştırma

```bash
cd dependency-analyzer

# Tam analiz: terminal raporu + görsel harita
python visualizer.py

# Sadece terminal çıktısı (grafiksiz)
python graph.py

# Sadece import listesi (test_project üzerinde)
python analyzer.py
```

### Renk Kodlaması

| Renk | Anlam |
|:---:|---|
| 🟢 Yeşil | Temiz proje dosyası |
| ⬜ Gri | Dış kütüphane (os, sys vb.) |
| 🔴 Kırmızı | Döngüsel bağımlılığa dahil dosya/bağlantı |

### Örnek Çıktı

<p align="center">
  <img src="dependency-analyzer/dependency_map.png" alt="Bağımlılık Haritası" width="650">
</p>

**Terminal çıktısı:**

```
══════════════════════════════════════════════════
  📋  BAĞIMLILIK LİSTESİ (Dosya → Import)
══════════════════════════════════════════════════

  📄 a.py
      └──▶ b
  📄 b.py
      └──▶ c
  📄 c.py
      └──▶ a

  🔍  DÖNGÜSEL BAĞIMLILIK ANALİZİ
──────────────────────────────────────────────────
  ⚠️  1 döngü tespit edildi!

  [1] a ──▶ b ──▶ c ──▶ a
```

### Mevcut Durum ve Sonraki Adımlar

- [x] Python AST ile import ayrıştırma
- [x] NetworkX yönlü grafik modeli
- [x] Döngüsel bağımlılık tespiti (Tarjan/DFS)
- [x] Matplotlib ile renkli görselleştirme
- [x] Terminal rapor çıktısı
- [x] GUI dosya seçici (tkinter)
- [ ] Java desteği (`import` statement parse)
- [ ] JavaScript/TypeScript desteği (`import`/`require` parse)
- [ ] HTML interaktif grafik çıktısı (D3.js)
- [ ] CLI argüman desteği (`--path`, `--output`, `--format`)


## 🛠️ Kullanılan Teknolojiler

| Teknoloji | Kullanım Amacı |
|---|---|
| [Python AST](https://docs.python.org/3/library/ast.html) | Kaynak kodu soyut sözdizimi ağacına dönüştürme |
| [NetworkX](https://networkx.org/) | Yönlü grafik oluşturma ve döngü analizi |
| [Matplotlib](https://matplotlib.org/) | Grafik görselleştirme |
| [Tkinter](https://docs.python.org/3/library/tkinter.html) | GUI klasör seçim diyaloğu |

---

