# PolyMetric Backend Omurga Checklist

Bu liste haftalik demo ve sprint takibi icin "backend hazirlik" durumunu netlestirir.

## Sprint 1 - Kilit Kararlar (blokaj acici)

- [x] Supabase veri modeli ve iliskiler tanimlandi.
- [x] RLS tasarimi project ownership ekseninde yazildi.
- [x] Run state modeli `pending/running/completed/failed` kilitlendi.
- [x] Analiz cikti JSON kontrati netlestirildi.
- [x] Frontend API sozlesmesi ilk surum cikarildi.

## Sprint 2 - Uygulama Omurgasi

- [ ] Supabase migration dosyalari ortama uygulandi.
- [ ] FastAPI auth katmani Supabase JWT ile degistirildi.
- [ ] In-memory store kaldirilarak Postgres repository katmani eklendi.
- [ ] `/api/internal/runs/{run_id}/ingest` endpointi eklendi.
- [ ] Run status gecisleri (pending -> running -> completed/failed) implement edildi.

## Sprint 3 - Performans ve NFR

- [ ] Batch insert stratejisi (files/functions/dependencies/hotspots) uygulandi.
- [ ] Trend sorgulari `project_run_trends_v` uzerinden optimize edildi.
- [ ] Ayni commit icin cache/skip stratejisi eklendi.
- [ ] Dependency graph icin module-level aggregate endpointi eklendi.

## Definition of Done (Backend Hazir)

- [ ] Kullanici yalnizca kendi proje ve run verisini gorebiliyor (RLS test edildi).
- [ ] Frontend tum zorunlu ekranlari API ile besleyebiliyor.
- [ ] Analiz motoru tek ingest payload ile run verisi yazabiliyor.
- [ ] 50 dosyali test reposunda p95 hedefi olculdu ve raporlandi.
