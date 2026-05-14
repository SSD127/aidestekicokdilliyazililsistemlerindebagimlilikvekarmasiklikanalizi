# PolyMetric Projesi Veritabanı Analiz Özeti

Proje dosyaları incelendiğinde, veritabanı ve veri katmanı ile ilgili oldukça kapsamlı ve profesyonel bir altyapı oluşturulduğu görülmektedir. Yapılan işlemler aşağıda özetlenmiştir:

### 1. Veritabanı Tercihi: Supabase (PostgreSQL)
Projede asıl veritabanı sağlayıcısı olarak **Supabase** tercih edilmiştir. Supabase üzerinden PostgreSQL kullanılmakta olup, hem veri saklama hem de kimlik doğrulama (Auth) süreçlerinin entegre edilmesi hedeflenmiştir.

### 2. Şema ve Tablo Tasarımı (SQL Migrations)
`backend/supabase/migrations/` klasörü altında veritabanı tablolarının, güvenlik kurallarının ve görünümlerin (views) oluşturulduğu SQL dosyaları bulunmaktadır:
*   **Temel Tablolar (`0001_init_polymetric_schema.sql`):** 
    *   `projects`: Kullanıcıların eklediği projeleri tutar.
    *   `analysis_runs`: Projelerin her bir analiz edilme oturumunu (run) kaydeder (trend analizi yapabilmek için).
    *   `files`: Analiz edilen kaynak kod dosyalarını ve dosya bazlı metriklerini (karmaşıklık, satır sayısı vb.) tutar.
    *   `function_metrics`: Dosyaların içindeki fonksiyonların detaylı metriklerini (McCabe karmaşıklığı, Halstead skoru, risk skoru) barındırır.
    *   `dependencies`: Dosyalar arası bağlantıları (import/include bağımlılıklarını) grafik çıkarabilmek için kaydeder.
    *   `hotspots`: En riskli fonksiyonları sıralayarak kaydeder.
    *   `run_metadata`: Kullanılan parser versiyonları gibi meta bilgileri tutar.
    *   *Ayrıca performans için gerekli indekslemeler (index) ve trend raporları çekebilmek için `project_run_trends_v` adında bir PostgreSQL Görünümü (View) oluşturulmuştur.*
*   **Güvenlik Kuralları (`0002_enable_rls.sql`):** Supabase'in Row-Level Security (RLS) özelliği aktif edilerek kullanıcı izolasyonu sağlanmıştır. Sistemde her kullanıcının sadece kendi projelerini ve analiz verilerini görebilmesi güvence altına alınmıştır.
*   **Yapay Zeka Önbelleği (`0003_add_ai_insights.sql`):** Yapay zeka servislerine (OpenAI/Gemini) aynı analiz için tekrar tekrar istek atıp maliyet ve zaman kaybetmemek adına, dönen AI yorumlarının önbelleğe alınacağı (cache) `ai_insights` adında bir tablo eklenmiştir.

### 3. Esnek Depolama Mimarisi (Storage Katmanı)
`backend/app/storage.py` dosyası incelendiğinde, sistemin ortam değişkenlerine göre dinamik çalıştığı görülmektedir.
*   Eğer `.env` dosyasında `SUPABASE_URL` ve `SUPABASE_SERVICE_ROLE_KEY` tanımlanmışsa sistem otomatik olarak gerçek veritabanı olan Supabase'e bağlanmaktadır.
*   Eğer bu anahtarlar girilmemişse, sistem geliştirme (development) ve test aşamalarını kilitlememek için **`InMemoryStore`** (bellek içi depo) üzerinden çalışmaktadır. Bu sayede veriler geçici olarak bilgisayarın belleğinde (RAM) tutularak hata vermeden sistemin ayağa kalkması sağlanmaktadır.

**Sonuç:** Projede modern bir veritabanı yaklaşımı izlenerek, veri ilişkileri düzgün bir şekilde normalize edilmiş (proje -> run -> dosya -> fonksiyon), RLS ile veri güvenliği düşünülmüş ve geliştirme esnasında esneklik sağlamak için bellek içi (in-memory) yedek senaryosu başarıyla entegre edilmiştir.
