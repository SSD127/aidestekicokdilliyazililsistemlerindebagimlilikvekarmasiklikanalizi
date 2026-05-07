# Backend API Specification

PolyMetric backend'inin frontend ile iletişim kurduğu HTTP arayüzünün resmi tanımı.

> **Güncel kaynak:** `backend/app/schemas.py` Pydantic modelleri ve
> `backend/contracts/examples/golden_analysis_result.json` örnek payload'ı bu
> dökümanın altında yatan tek doğruluk kaynağıdır. Çelişki durumunda kod kazanır.

---

## Endpoint: Analyze Repository (Senkron Sarmalayıcı)

Frontend tek istekle GitHub URL gönderir, backend senkron olarak repo'yu indirir,
parse eder, metrik hesaplar ve `AnalysisResult` JSON'unu döndürür.

### Request

**Endpoint:** `POST /api/analyze`

**Headers:**
```
Content-Type: application/json
X-User-Id: <opsiyonel; verilmezse "local-dev-user" kullanılır>
```

**Body (`AnalyzeRequest`):**
```json
{
  "github_url": "https://github.com/username/repository",
  "branch": "main",
  "include_tests": true
}
```

| Alan            | Tip      | Zorunlu | Açıklama                                                  |
|-----------------|----------|---------|-----------------------------------------------------------|
| `github_url`    | string   | evet    | Geçerli `https://github.com/owner/repo` formatında URL    |
| `branch`        | string   | hayır   | Varsayılan `"main"`. 404 alınırsa `master` denenir         |
| `include_tests` | boolean  | hayır   | Varsayılan `true`. Şu an kabul edilir, filtreleme yok      |

### Response

**Status Code:** `200 OK`

**Body:** `AnalysisResult` JSON. Örnek için bkz.
[`backend/contracts/examples/golden_analysis_result.json`](../backend/contracts/examples/golden_analysis_result.json).

```json
{
  "run_id": "8e35bc35-9480-47af-8635-965f9b3bdb0d",
  "project_id": "6f6dd412-2e2d-4c71-99f0-7a48695fbc91",
  "commit_hash": "a1b2c3d4e5f6",
  "branch_name": "main",
  "analyzed_at": "2026-04-30T10:00:00Z",
  "parser_version": "polymetric-tree-sitter:v0.1.0",
  "grammar_version": "tree-sitter-python:bundled",
  "files":        [ /* FileMetric[] */       ],
  "functions":    [ /* FunctionMetric[] */   ],
  "dependencies": [ /* DependencyEntry[] */  ],
  "hotspots":     [ /* HotspotEntry[]; max 5 */ ]
}
```

`/api/analyze` ek olarak `timing`, `skipped_files`, `partial` gibi non-strict
alanları da gönderir (frontend bunları gösterebilir veya yok sayabilir).

---

## Veri Yapıları

Tüm tipler `backend/app/schemas.py` içinde Pydantic modeli olarak tanımlıdır;
422 hata gelirse alan eksik veya tip hatalı demektir.

### `FileMetric` (`files[]`)

```json
{
  "path": "app/main.py",
  "language": "python",
  "loc": 120,
  "complexity_score": 11,
  "dependency_count": 4,
  "maintainability_index": null
}
```

- `complexity_score`: dosyadaki tüm fonksiyonların McCabe CC toplamı.
- `loc`: yorum/boş satırlar hariç kod satırı sayısı.
- `maintainability_index`: opsiyonel; şu an üretilmiyor (`null`).

### `FunctionMetric` (`functions[]`)

```json
{
  "file_path": "app/main.py",
  "function_name": "create_run",
  "cyclomatic_complexity": 13,
  "halstead_score": 1840.5,
  "loc": 36,
  "start_line": 40,
  "end_line": 75,
  "risk_score": 10
}
```

- `cyclomatic_complexity`: `1 + branch_count + loop_count`.
- `halstead_score`: gerçek Halstead **Effort** (`E = D × V`).
- `risk_score`: `risk.calculate_risk_level` çıkışından map edilen sayı
  (`low=1`, `moderate=5`, `high=10`, `critical=18`).
- `loc`: fonksiyonun çalıştırılabilir satırları (`executable_lines`).

### `DependencyEntry` (`dependencies[]`)

```json
{
  "source_path": "app/main.py",
  "target_path": "app/storage.py",
  "dependency_type": "import",
  "source_symbol": null,
  "target_symbol": null
}
```

- `dependency_type`: `"import" | "call" | "inheritance" | "composition"`.
- Sadece repo içindeki dosyalara işaret eden bağımlılıklar dahil edilir.

### `HotspotEntry` (`hotspots[]`, en fazla 5 eleman)

```json
{
  "file_path": "app/main.py",
  "function_name": "create_run",
  "risk_score": 10,
  "reason": "Cyclomatic complexity: 13",
  "rank": 1
}
```

---

## Hata Cevapları

| Kod | Anlam                                                                                  |
|-----|----------------------------------------------------------------------------------------|
| 400 | `github_url` geçersiz GitHub repo formatı                                              |
| 413 | Repo çok büyük (`MAX_TOTAL_FILES * 10` aşıldı) — `RepoTooLargeError`                   |
| 422 | `AnalysisResult` Pydantic doğrulamasından geçemedi                                     |
| 502 | GitHub'dan zip indirilemedi (`requests.RequestException`)                              |
| 500 | Beklenmedik analiz hatası                                                              |

Hata gövdesi formatı FastAPI standardındadır:
```json
{ "detail": "..." }
```

---

## Asenkron Akış (Geriye Dönük Uyumluluk)

`POST /api/analyze` haricinde aynı backend, run-id polling akışını da sunar:

- `POST /api/projects` → proje oluştur
- `POST /api/projects/{project_id}/runs` → analiz başlat (arka plan)
- `GET  /api/projects/{project_id}/runs/{run_id}/summary` → durum sorgula
- `GET  /api/projects/{project_id}/runs/{run_id}/hotspots`
- `GET  /api/projects/{project_id}/runs/{run_id}/dependency-graph`
- `GET  /api/projects/{project_id}/trends?metric=...`
- `GET  /api/projects/{project_id}/runs/{run_id}/ai-insight`

Detaylar için `backend/docs/api_contract.md`'ye bakınız.

---

## Şu An Üretilmeyen Metrikler

Aşağıdaki alanlar mevcut sürümde üretilmiyor; sonraki sprintlerde eklenecek
araç entegrasyonlarını gerektiriyor:

- `test_coverage`, `documentation_coverage` → coverage.py / pydocstyle
- `code_quality_score`, `code_smells` → pylint / ruff
- `security_hotspots`, `vulnerable_dependencies` → bandit / pip-audit
- `disk_space`, `time_complexity (O-notation)`, `space_complexity` → tasarım dışı

Frontend bu alanların yokluğunu kabul eder ve karşılık gelen kartları gizler.

---

## Test

`backend/contracts/examples/golden_analysis_result.json` örnek payload'ı şema ile
birebir uyumludur. Manuel test:

```bash
uvicorn app.main:app --reload  # backend/ altında
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url":"https://github.com/psf/requests","branch":"main"}'
```
