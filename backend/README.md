# Backend (FastAPI) - Baslangic Iskeleti

Bu klasor, PolyMetric projesinin backend omurgasinin ilk surumunu icerir.

## Kurulum
1. Sanal ortam olustur:
   - `python -m venv .venv`
   - `source .venv/bin/activate`
2. Bagimliliklari kur:
   - `pip install -r requirements.txt`
3. Ortam degiskenleri:
   - `.env.example` dosyasini `.env` olarak kopyala

## Calistirma
- `uvicorn app.main:app --reload`

## Endpointler
- `GET /health`
- `POST /api/projects`
- `GET /api/projects`
- `POST /api/projects/{project_id}/runs`
- `GET /api/projects/{project_id}/runs`
- `GET /api/projects/{project_id}/runs/{run_id}/summary`
- `GET /api/projects/{project_id}/runs/{run_id}/hotspots`
- `GET /api/projects/{project_id}/runs/{run_id}/dependency-graph`
- `GET /api/projects/{project_id}/runs/{run_id}/ai-insight`
- `GET /api/projects/{project_id}/trends`
- `POST /api/internal/runs/{run_id}/status` *(X-Internal-Api-Key gerekli)*
- `POST /api/internal/runs/{run_id}/ingest` *(X-Internal-Api-Key gerekli)*

## Not
Bu ilk surumda veri depolama `in-memory` tutuldu. Sonraki adimda Supabase tablolarina gecilerek kalici hale getirilecektir.

## Omurga Dokumanlari
- API sozlesmesi: `backend/docs/api_contract.md`
- Parser AST sozlesmesi: `backend/docs/parser_ast_contract.md`
- Sprint/checklist: `backend/docs/backend_execution_checklist.md`
- Parser AST schema: `backend/contracts/parser_ast.schema.json`
- Analiz cikti kontrati: `backend/contracts/analysis_result.schema.json`
- Parser AST ornegi: `backend/contracts/examples/golden_parser_ast.json`
- Supabase schema migration: `backend/supabase/migrations/0001_init_polymetric_schema.sql`
- Supabase RLS migration: `backend/supabase/migrations/0002_enable_rls.sql`
