# Yapay Zeka Destekli Çok Dilli Yazılım Sistemlerinde Mimari Bağımlılık ve Karmaşıklık Analiz Sistemi

Bu repo, “Mini SonarQube” benzeri bir **statik analiz** sistemi geliştirir: Tree-sitter ile çok dilli kaynak kodu ayrıştırır, **McCabe** ve **Halstead** metriklerini üretir, dosyalar arası **bağımlılık grafiğini** çıkarır ve sonuçları **Supabase (PostgreSQL + Auth)** üzerinde saklar.

## Amaç
- Çok dilli projelerde (örn. Python/Java/C++/JavaScript) **derlemeden/çalıştırmadan** metrik ve bağımlılık analizi yapmak
- Analiz sonuçlarını versiyonlayarak **trend** (zaman içi artış/azalış) göstermek
- Karmaşıklığı en yüksek fonksiyonları **hotspot** olarak işaretlemek

## Temel Özellikler (FR)
- **FR-1 Proje Yükleme**: Yerel klasör veya tekil kod dosyaları analize alınır
- **FR-2 Otomatik Dil Tanımlama**: Uzantıya göre dil tespiti
- **FR-3 Metrik Hesaplama**: McCabe + Halstead
- **FR-4 Bağımlılık Haritalama**: import/include ilişkilerinden yönlü grafik
- **FR-5 Trend Analizi**: farklı analiz “run” sonuçlarını kıyaslama
- **FR-6 Supabase Entegrasyonu**: sonuçların ve oturumların güvenli saklanması

## Kalite Hedefleri (NFR)
- **NFR-1 Performans**: 50 dosyalık proje < 5 saniye analiz + DB yazma
- **NFR-2 Modülerlik**: yeni dil eklemek ana motoru bozmadan mümkün olmalı
- **NFR-3 Veri Güvenliği**: Supabase Auth + RLS ile kullanıcı izolasyonu
- **NFR-4 Kullanılabilirlik**: büyük grafikleri kümeleme ile okunur tutma

## Mimari Özet
- **Universal Parser**: Tree-sitter → CST/AST üretimi (çok dillilik)
- **Statik Analiz**: runtime yok; sadece ayrıştırma ve hesaplama
- **Merkezi Veri**: Supabase üzerinde kullanıcı/proje/run/metrik/graph kayıtları
- **Run modeli**: her analiz çalıştırması bir “run” olarak saklanır (trend için)

## Repo Durumu
Uygulama kodu mevcuttur: **FastAPI** backend ([`backend/app/main.py`](backend/app/main.py)), GitHub zip indirme ve dosya seçimi ([`backend/app/services/github_pipeline.py`](backend/app/services/github_pipeline.py)), analiz orkestratörü ([`backend/app/core/orchestrator.py`](backend/app/core/orchestrator.py)), Tree-sitter tabanlı parser ([`backend/app/core/parser.py`](backend/app/core/parser.py)), **Streamlit** arayüz kökü ([`app.py`](app.py), [`frontend/`](frontend/)).

### Desteklenen uzantılar (indirme / ayrıştırma)
Backend `SUPPORTED_EXTENSIONS` ile uyumlu: `.py`, `.java`, `.js`, `.ts`, `.c`, `.h`, `.cpp`, `.cc`, `.cxx`, `.hpp`, `.cs`.

**Metrik ve risk üretimi** (McCabe, Halstead, hotspot) şu an **Python** kaynakları için tam akışta kullanılır. Diğer diller Tree-sitter ile ayrıştırılabilir; tam ürün doğrulaması ağırlıklı olarak Python üzerindedir.

## Kurulum ve çalıştırma

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API varsayılan olarak `http://127.0.0.1:8000` üzerinde ayağa kalkar. Sağlık kontrolü: `GET /health`.

### Frontend (Streamlit)
Depo kökünden:
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Birim testleri
```bash
cd backend
pytest
```
`pytest.ini` içinde `pythonpath = .` tanımlıdır; komutların `backend` dizininde çalıştırılması gerekir.

## Takım Rolleri (5 kişi)
- **Backend & Scrum Master : Supabase şema/ER, Auth+RLS, API endpoint’leri, GitHub pipeline, Kanban/sprint yönetimi
- **Engine Lead**: Tree-sitter ile ayrıştırma (AST/CST)
- **Logic Lead**: McCabe/Halstead algoritmaları
- **UI/UX Lead**: Panel ve görselleştirmeler (grafikler/heatmap)
- **Network Lead**: bağımlılık grafiği + döngüsel bağımlılık raporu

## Dokümanlar
- `presentationanddocumentation/`: ilgili PDF/dokümanlar
- `backend/`: FastAPI uygulaması ve analiz motoru
- `backend_mock/`: mock API ve ekip notları

## Lisans
Bu proje ders/proje kapsamındadır. Lisans seçimi ekip kararına göre eklenecektir.
