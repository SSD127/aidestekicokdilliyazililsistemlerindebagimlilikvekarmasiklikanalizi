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

## Takım Rolleri (5 kişi)
- **Backend & Scrum Master : Supabase şema/ER, Auth+RLS, API endpoint’leri, GitHub pipeline, Kanban/sprint yönetimi
- **Engine Lead**: Tree-sitter ile ayrıştırma (AST/CST)
- **Logic Lead**: McCabe/Halstead algoritmaları
- **UI/UX Lead**: Panel ve görselleştirmeler (grafikler/heatmap)
- **Network Lead**: bağımlılık grafiği + döngüsel bağımlılık raporu

## Repo Durumu
Şu an repo, ilk dokümantasyon dosyalarını içermektedir. Uygulama kodu ekip planına göre kademeli olarak eklenecektir.

## Dokümanlar
- `presentationanddocumentation/`: ilgili PDF/dokümanlar
- `backend/`: FastAPI backend başlangıç iskeleti ve API uçları

## Lisans
Bu proje ders/proje kapsamındadır. Lisans seçimi ekip kararına göre eklenecektir.

