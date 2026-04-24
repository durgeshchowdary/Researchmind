# ResearchMind

ResearchMind is an AI Retrieval Platform for building, testing, evaluating, and deploying grounded document search and RAG pipelines. It ingests PDFs, Markdown, text files, and web pages; extracts and chunks content; stores metadata in SQLite; persists BM25 and FAISS indexes; supports keyword, semantic, hybrid, and reranked retrieval; evaluates retrieval quality; and exposes workspace-scoped APIs for retrieval and answer generation.

## Stack

- Frontend: Next.js 15 App Router, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic, PyMuPDF
- Auth: SQLite users, password hashing, JWT bearer tokens
- Storage: SQLite, persisted BM25 files, FAISS
- Retrieval: BM25, sentence-transformers embeddings, weighted hybrid fusion
- RAG: grounded prompt builder with OpenAI-compatible optional LLM fallback
- Platform: workspaces, roles, benchmark builder, retrieval playground, index management, connectors, API keys, observability

## Architecture

- The frontend is a Next.js App Router application that talks to the backend through a typed API client using `NEXT_PUBLIC_API_BASE_URL`.
- The backend is a FastAPI service responsible for ingestion, extraction, chunking, BM25 indexing, FAISS indexing, hybrid retrieval, and grounded answer generation.
- SQLite stores document and chunk metadata, while persisted files under `backend/data` hold uploads and search indexes.
- Authenticated users own their uploaded documents. Listing, upload, search, and ask routes require a bearer token and only return the current user's corpus.
- Runtime failures degrade safely:
  - embedding or FAISS failure falls back to keyword-only retrieval with explicit warnings,
  - LLM failure falls back to extractive grounded answers,
  - frontend request failures surface safe UI messages instead of blank screens.

## What Improved In This Iteration

- Backend runtime hardening with startup checks, health endpoint, automatic runtime directory creation, and global error handling.
- Idempotent document flow with checksum deduplication, richer document statuses, safer ingestion failures, and indexing status visibility.
- Better retrieval quality with query-frequency-aware BM25, title weighting, snippets, matched term highlighting, normalized hybrid fusion, warnings, and ranking explanations.
- Better RAG quality with chunk deduplication, document diversity, stable chunk ordering, insufficient-evidence handling, improved fallback extractive answers, richer citations, and a new clickable citation-to-evidence flow.
- Frontend API/type cleanup with a centralized client, typed responses, upload progress, dashboard summaries, document status badges, search filters, evidence modal navigation, and visible "why this ranked" / "why this answer" explanations.
- Deployment-ready environment examples for local and hosted setup.
- Minimal real pytest coverage for preprocessing, chunking, BM25 ranking, and hybrid fusion.

## Standout Demo Features

- Click any answer citation to open a dedicated evidence panel with document title, chunk id, page number, highlighted snippet, and full supporting text.
- Inspect a "Why This Answer?" summary that reveals whether the response came from the LLM path, extractive fallback, or insufficient-evidence guardrail.
- Expand each search result to see the ranking explanation, including keyword overlap, title boost usage, semantic similarity, and hybrid score contribution.
- Walk through the full product story in under two minutes: upload, search, ask, click citation, inspect evidence.

## Monorepo Structure

```text
researchmind/
  backend/
    app/
    data/
    scripts/
    tests/
    requirements.txt
  frontend/
    app/
    components/
    lib/
    types/
```

## Platform Capabilities

- Workspaces: each user can belong to multiple workspaces as owner, editor, or viewer. Documents, chunks, tasks, evaluation sets, API keys, and platform metrics are scoped by workspace.
- Benchmark builder: create evaluation sets, add expected terms/citations, run benchmarks, and inspect aggregate and per-question metrics.
- Retrieval playground: compare BM25, semantic, hybrid, and hybrid-reranked pipelines side by side with latency and ranking explanations.
- Index management: inspect document indexing status, reindex documents, delete documents, rebuild a workspace index, and review indexing logs.
- Connectors: Web URL import is available now. GitHub, Notion, and Google Drive connector slots are scaffolded for future OAuth/import flows.
- API platform mode: create workspace-scoped API keys and call `/api/retrieve`, `/api/rerank`, `/api/answer`, and `/api/evaluate`.
- Observability: inspect search/ask/indexing latency, queue mode, Redis availability, indexing failures, document totals, chunk totals, and evaluation run counts.

## Local Development

### Backend

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

macOS/Linux:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

API runs on `http://localhost:8000`.

Run the optional Celery worker when Redis is available:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.worker.celery_app.celery_app worker --loglevel=info --pool=solo
```

Run Redis locally with Docker:

```powershell
docker run --name researchmind-redis -p 6379:6379 redis:7
```

If Redis or Celery is unavailable, uploads still work. ResearchMind automatically falls back to FastAPI background tasks, or synchronous processing when async indexing is disabled.

Auth endpoints:

```text
POST /auth/signup
POST /auth/login
GET  /auth/me
```

The local demo account is seeded automatically on backend startup:

```text
demo@researchmind.ai / researchmind-demo
```

> **Note for VS Code users:** If you receive a warning about "terminal environment injection", enable the `python.terminal.useEnvFile` setting in your VS Code preferences to ensure your `.env` variables are correctly loaded into the integrated terminal.

Optional seed ingestion:

```powershell
cd backend
python scripts\seed_documents.py
```

### Frontend

Windows PowerShell:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

macOS/Linux:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend runs on `http://localhost:3000`.

Main platform pages:

```text
/workspace-settings
/evaluation/builder
/playground
/index-management
/connectors
/observability
/api-platform
```

Evaluation benchmark:

```powershell
curl http://localhost:8000/evaluation/run -H "Authorization: Bearer <token>"
```

The frontend evaluation lab is available at `http://localhost:3000/evaluation`.

Demo script:

```text
1. Log in with demo@researchmind.ai / researchmind-demo.
2. Open Workspace Settings and confirm the Demo Workspace.
3. Upload a document or import a webpage from Connectors.
4. Use Search, Ask, Compare, and Citations.
5. Open Playground to compare retrieval pipelines.
6. Open Evaluation Builder, create a benchmark, add questions, and run it.
7. Open Index Management and Observability to inspect platform state.
8. Create an API key in API Platform and call /api/retrieve with X-API-Key.
```

### Tests

```powershell
cd backend
pytest -p no:cacheprovider
```

## Environment Variables

### Backend

- `APP_NAME`, `APP_ENV`, `APP_HOST`, `APP_PORT`: FastAPI app metadata and bind settings.
- `JWT_SECRET`: long random secret used to sign access tokens. Replace the development value before deployment.
- `JWT_EXPIRES_MINUTES`: access token lifetime in minutes.
- `FRONTEND_ORIGIN`: primary frontend origin.
- `CORS_ORIGINS`: comma-separated allowed origins for local or deployed frontends.
- `CORS_ORIGIN_REGEX`: optional regex for preview/deployment origins.
- `DATABASE_PATH`: SQLite file location.
- `UPLOADS_DIR`: persisted raw upload directory.
- `INDEX_DIR`: BM25 and FAISS storage directory.
- `TEMP_DIR`: runtime temp directory created automatically on boot.
- `SEED_DIR`: sample data directory.
- `CHUNK_SIZE`, `CHUNK_OVERLAP`: chunking controls.
- `TOP_K_DEFAULT`: default retrieval depth.
- `EMBEDDING_MODEL`: sentence-transformers model name.
- `SEMANTIC_MIN_SCORE`: minimum semantic score threshold.
- `SEMANTIC_RESULT_LIMIT_MULTIPLIER`: semantic over-fetch factor before filtering.
- `HYBRID_BM25_WEIGHT`, `HYBRID_SEMANTIC_WEIGHT`: fusion weights.
- `TITLE_MATCH_WEIGHT`: title overlap boost.
- `ASK_MIN_GROUNDED_SCORE`, `ASK_MIN_SUPPORTED_TERMS`: insufficient-evidence thresholds.
- `LLM_TIMEOUT_SECONDS`: external LLM timeout.
- `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`: optional OpenAI-compatible provider settings.
- `ASYNC_INDEXING_ENABLED`: enables queued indexing. If false, indexing runs synchronously.
- `REDIS_URL`: Redis broker URL for Celery, defaulting to `redis://localhost:6379/0`.
- `RERANKING_ENABLED`: enables the post-hybrid reranking layer.
- `RERANKER_MODEL`: optional sentence-transformers CrossEncoder model. Deterministic reranking is used if unavailable.
- `EVALUATION_DATASET_PATH`: JSON benchmark dataset path.

### Frontend

- `NEXT_PUBLIC_API_BASE_URL`: public backend origin for browser requests. For Vercel, set this to your deployed Railway/Render backend URL.

## Production Deployment

### Backend on Railway or Render

- Deploy the `backend` directory as the service root.
- Install command: `pip install -r requirements.txt`
- Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set persistent disk storage if you want SQLite, uploaded files, and indexes to survive restarts.
- Set `CORS_ORIGINS` to include your Vercel frontend origin.
- Set `CORS_ORIGIN_REGEX=^https://.*\.vercel\.app$` if you want Vercel preview deployments to work without updating CORS on every preview URL.
- Set `FRONTEND_ORIGIN` to the same deployed frontend URL for clearer health reporting and CORS defaults.
- Set `JWT_SECRET` to a strong deployment secret and rotate it if it is ever exposed.
- Ensure the first embedding-model download can complete during build or first boot.
- Recommended envs for hosted use:
  - `APP_ENV=production`
  - `DATABASE_PATH=./data/researchmind.db`
  - `UPLOADS_DIR=./data/uploads`
  - `INDEX_DIR=./data/indexes`
  - `TEMP_DIR=./data/tmp`
  - `CORS_ORIGINS=https://your-frontend.vercel.app`
  - `CORS_ORIGIN_REGEX=^https://.*\.vercel\.app$`

### Frontend on Vercel

- Deploy the `frontend` directory.
- Framework preset: Next.js
- Build command: `npm run build`
- Set `NEXT_PUBLIC_API_BASE_URL` to the public backend URL.
- If frontend and backend are same-origin behind a reverse proxy, the client can also operate with a relative base URL by setting that variable accordingly in deployment.
- When the backend is unavailable, the frontend now surfaces deployment-safe error messages instead of failing silently.

## Final Integration Notes

- `/ask` was verified live against the running FastAPI backend on `http://127.0.0.1:8000`.
- Citation payloads now map cleanly
