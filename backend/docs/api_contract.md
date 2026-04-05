# PolyMetric Backend API Sozlesmesi (v1)

Bu sozlesme frontend ve analiz motoru ekiplerinin backend ile uyumlu gelistirme yapmasi icin v1 omurgasini tanimlar.

## Kimlik Dogrulama

- Tum `/api/*` endpointleri Supabase Auth JWT bekler.
- Backend, kullanici kimligini `auth.uid()` uzerinden cozer.
- Kullanici yalnizca kendi `project` ve ona bagli verilere erisebilir.

## Run Durum Modeli

- `pending`: run olusturuldu, kuyruge alindi.
- `running`: analiz su an calisiyor.
- `completed`: analiz basariyla bitti.
- `failed`: analiz hata ile sonlandi.

## Endpointler

### Projeler

- `POST /api/projects`
  - Request:
    - `name` (string)
    - `github_repo_url` (url)
    - `default_branch` (string, optional, default `main`)
  - Response: `project`

- `GET /api/projects`
  - Response: kullanicinin tum projeleri

### Run Yonetimi

- `POST /api/projects/{project_id}/runs`
  - Request:
    - `github_ref` (string, optional)
  - Davranis:
    - Yeni kayit `status=pending` ile olusur.
  - Response: `run`

- `GET /api/projects/{project_id}/runs`
  - Response: proje run gecmisi (en yeni once)

- `GET /api/projects/{project_id}/runs/{run_id}/summary`
  - Response:
    - run status + ozet metrikler (dosya sayisi, fonksiyon sayisi, mccabe avg/max, halstead toplam)

### Analiz Ciktilari

- `GET /api/projects/{project_id}/runs/{run_id}/hotspots`
  - Response:
    - en riskli ilk 5 fonksiyon (`rank`, `risk_score`, `reason`)

- `GET /api/projects/{project_id}/runs/{run_id}/dependency-graph`
  - Query:
    - `level=file|module` (opsiyonel, default `file`)
  - Response:
    - `nodes[]`, `edges[]`

- `GET /api/projects/{project_id}/trends?metric=mccabe_avg`
  - Metric secenekleri:
    - `mccabe_avg`, `mccabe_max`, `halstead_total`, `risk_total`
  - Response:
    - ayni proje icin run bazli trend noktasi listesi

### Analiz Motoru Yazma Uclari (internal)

- `POST /api/internal/runs/{run_id}/ingest`
  - Amac: analiz motorunun toplu cikti yazmasi.
  - Auth: sadece backend service role.
  - Body: `analysis_result.schema.json` formati.

- `POST /api/internal/runs/{run_id}/status`
  - Amac: `running/completed/failed` gecisleri.
  - Auth: sadece backend service role.

## Hata Sozlesmesi

- 400: gecerli olmayan payload
- 401: auth yok/gecersiz
- 403: yetki yok
- 404: kaynak bulunamadi veya kullaniciya ait degil
- 409: ayni commit icin duplicate run

## NFR Notlari

- 50+ dosya hedefi icin tum ingest yazmalari batch olmalidir.
- Ayni `project_id + commit_hash` icin completed run varsa yeniden analiz opsiyonel olarak atlanir (cache stratejisi).
