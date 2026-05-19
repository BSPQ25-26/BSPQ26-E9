# DevOps & CI/CD

## Live Production Environment

Wallabot is deployed on [Render](https://render.com) and is **publicly accessible right now**.

| Service | Production URL | API docs |
|---------|---------------|---------|
| **Frontend (app)** | https://wallabot-frontend.onrender.com | — |
| Auth Service | https://wallabot-auth.onrender.com | https://wallabot-auth.onrender.com/docs |
| Inventory Service | https://wallabot-inventory.onrender.com | https://wallabot-inventory.onrender.com/docs |
| Transaction Service | https://wallabot-transaction.onrender.com | https://wallabot-transaction.onrender.com/docs |
| Agentic Service | https://wallabot-agentic.onrender.com | https://wallabot-agentic.onrender.com/docs |

The interactive Swagger UI at `/docs` and ReDoc at `/redoc` are enabled on every backend service
in production — useful for manual testing without running anything locally.

> **Note on free-tier cold starts**: all services run on Render's free plan. After 15 minutes
> of inactivity Render spins the container down. The first request after inactivity will take
> 30–60 seconds while the container boots. Subsequent requests are fast.

---

## Sphinx Documentation (GitHub Pages)

The full project documentation (this site) is automatically published to GitHub Pages on every
push to `main`:

**https://BSPQ25-26.github.io/BSPQ26-E9/sphinx/**

A downloadable PDF version of the documentation is also generated and available at:

**https://BSPQ25-26.github.io/BSPQ26-E9/sphinx/BSPQ26-E9.pdf**

How the docs deployment works:

1. The `sphinx-docs.yml` GitHub Actions workflow triggers on every push to `main`
2. It installs Python 3.12, then all Sphinx dependencies from `docs-sphinx/requirements.txt`
3. `make html` builds the static HTML site into `docs-sphinx/_build/html/`
4. WeasyPrint + BeautifulSoup render the combined PDF (`build_pdf.py`)
5. The deployment directory is assembled:
   ```
   deploy/
   ├── .nojekyll          ← disables Jekyll processing on GitHub Pages
   ├── index.html         ← redirect to sphinx/
   └── sphinx/
       ├── index.html     ← documentation home page
       ├── ...            ← all other HTML pages and assets
       └── BSPQ26-E9.pdf  ← combined PDF export
   ```
6. `peaceiris/actions-gh-pages@v4` pushes `deploy/` to the `gh-pages` branch

**Required GitHub repository settings** (one-time setup):

1. Repository must be **public**
2. *Settings → Actions → General → Workflow permissions*: **Read and write permissions**
3. *Settings → Pages → Source*: **Deploy from a branch**, branch **gh-pages**, folder **/ (root)**

---

## Render Deployment Architecture

### Overview

All five Wallabot services are deployed as independent **Render Web Services** running Docker
containers. The deployment is defined in `render.yaml` (Render Blueprint) at the repository
root and deploys from the `main` branch.

```
GitHub (main branch)
        │
        │  push / merge → autoDeploy: yes
        ▼
  Render Build System
        │
        ├── wallabot-auth        → https://wallabot-auth.onrender.com
        ├── wallabot-inventory   → https://wallabot-inventory.onrender.com
        ├── wallabot-transaction → https://wallabot-transaction.onrender.com
        ├── wallabot-agentic     → https://wallabot-agentic.onrender.com
        └── wallabot-frontend    → https://wallabot-frontend.onrender.com
```

### Service configuration

| Render service | Source directory | Dockerfile | Port | Health check |
|---------------|-----------------|-----------|------|-------------|
| wallabot-auth | `backend/auth-service` | `./Dockerfile` | 10000 | `/health` |
| wallabot-inventory | `backend/inventory-service` | `./Dockerfile` | 10000 | `/health` |
| wallabot-transaction | `backend/transaction-service` | `./Dockerfile` | 10000 | `/health` |
| wallabot-agentic | `backend/agentic-service` | `./Dockerfile` | 10000 | `/health` |
| wallabot-frontend | `frontend` | `./Dockerfile.render` | 10000 | `/` |

Every backend service is started with:
```
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

### Persistent storage (SQLite on free tier)

The three stateful backend services have a **persistent disk** mounted at `/app/data`. SQLite
database files are created there on first startup and survive container restarts and redeploys.

| Service | Database path | Env variable |
|---------|--------------|-------------|
| wallabot-auth | `/app/data/auth.db` | `AUTH_DATABASE_URL` |
| wallabot-inventory | `/app/data/inventory.db` | `DATABASE_URL` |
| wallabot-transaction | `/app/data/transactions.db` | `DATABASE_URL` + `TRANSACTION_DATABASE_URL` |

The Agentic Service has **no database** — it is fully stateless.

### Service-to-service routing (frontend reverse proxy)

The Vue SPA is served by an **nginx container** built from `frontend/Dockerfile.render`. The
nginx configuration (`frontend/nginx.render.conf`) acts as a reverse proxy, forwarding each
URL prefix to the appropriate backend service using Render's internal private networking.

Render injects the internal hostname of each backend service at container startup via
environment variables (`AUTH_SERVICE_URL`, `INVENTORY_SERVICE_URL`, etc.), which are
referenced in the nginx config at runtime via `frontend/entrypoint.sh`.

```
Browser → https://wallabot-frontend.onrender.com
                 │
                 │ nginx reverse proxy
                 ├── /auth/*       → wallabot-auth      (internal Render URL)
                 ├── /users/*      → wallabot-auth
                 ├── /ratings/*    → wallabot-auth
                 ├── /api/v1/*     → wallabot-inventory
                 ├── /uploads/*    → wallabot-inventory
                 ├── /products/*   → wallabot-transaction
                 ├── /wallet/*     → wallabot-transaction
                 ├── /transactions/*→ wallabot-transaction
                 └── /wallabot/*   → wallabot-agentic
```

This design keeps all backend services on Render's internal network — they are only reachable
through the frontend nginx proxy and are not directly exposed to the public internet through
the app. (Their individual `*.onrender.com` URLs are still accessible for direct API testing
and Swagger UI access.)

### Environment variables

Secrets are configured in the Render dashboard (not stored in `render.yaml`). The following
must be set for a full-featured production deployment:

| Variable | Service | Description |
|----------|---------|-------------|
| `SECRET_KEY` | auth, inventory, transaction | JWT signing key — must be identical across all services |
| `OPENAI_API_KEY` | agentic | GPT-4o-mini API key |
| `TAVILY_API_KEY` | agentic | Tavily web search API key |
| `LANGCHAIN_TRACING_V2` | agentic | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | agentic | LangSmith project key |
| `SUPABASE_URL` | inventory | (Optional) Supabase project URL for PostgreSQL + Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | inventory | (Optional) Supabase service-role key |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | auth | (Optional) Google OAuth credentials |
| `FACEBOOK_CLIENT_ID` / `FACEBOOK_CLIENT_SECRET` | auth | (Optional) Facebook OAuth credentials |

The `render.yaml` marks `OPENAI_API_KEY` and `TAVILY_API_KEY` with `sync: false`, meaning
Render will prompt for these values when the Blueprint is first applied — they are never
committed to the repository.

### Auto-deploy behaviour

Each service has `autoDeploy: yes` with trigger `commit`. When a commit is pushed to `main`:

1. Render detects the push via a GitHub webhook
2. Only services whose source directory contains changed files are rebuilt (Render change
   detection is directory-scoped)
3. The affected service(s) build their Docker image, run health checks, then swap the old
   container for the new one with zero downtime (rolling update)

---

## CI/CD Pipeline (GitHub Actions)

Three workflow files live in `.github/workflows/`:

### `ci.yml` — Continuous Integration

Runs on every **push and pull request** to any branch.

| Job | What it runs | Fails if |
|-----|-------------|---------|
| `lint-python` | `ruff check` on all backend services | Any lint error |
| `lint-frontend` | `npm ci && npm run lint` in `frontend/` | Any lint error |
| `test-auth-service` | `pytest --cov=app --cov-fail-under=50` | Coverage < 50% or test failure |
| `test-inventory-service` | `pytest --cov=app --cov-fail-under=50` | Coverage < 50% or test failure |
| `test-transaction-service` | `pytest --cov=app --cov-fail-under=50` | Coverage < 50% or test failure |
| `test-agentic-service` | `pytest --cov=app --cov-fail-under=50` | Coverage < 50% or test failure |
| `docker-build` | Builds all Docker images + smoke health checks | Build failure or unhealthy container |
| `sphinx-docs` | Builds Sphinx HTML + PDF | Any Sphinx warning treated as error |

Each `test-*` job uploads three coverage artifacts to GitHub Actions:
- Terminal output (visible in job log)
- XML report (`coverage-<service>.xml`)
- HTML report (`coverage-<service>/` directory)

### `cd.yml` — Continuous Delivery

Runs **after CI passes** on `main` (triggered by `workflow_run`). It:

1. Checks that the triggering CI run concluded as `success` (guard job)
2. Builds and pushes all five Docker images to **GitHub Container Registry** (GHCR):
   ```
   ghcr.io/bspq25-26/bspq26-e9/auth-service:<sha>
   ghcr.io/bspq25-26/bspq26-e9/inventory-service:<sha>
   ghcr.io/bspq25-26/bspq26-e9/transaction-service:<sha>
   ghcr.io/bspq25-26/bspq26-e9/agentic-service:<sha>
   ghcr.io/bspq25-26/bspq26-e9/frontend:<sha>
   ```
3. Each image is tagged with both `latest` and the commit SHA
4. BuildKit layer caching (`type=registry`) is used to speed up incremental builds

The actual Render redeploy is triggered independently by Render's GitHub webhook (not by this
workflow) — Render listens for `main` branch pushes directly.

### `sphinx-docs.yml` — Documentation Deployment

Runs when **"Wallabot CI" completes on `main`** (via `workflow_run` trigger) and on manual
dispatch (`workflow_dispatch`). Using `workflow_run` instead of `push` guarantees the CI
test artifacts (coverage HTML reports) already exist when the docs build starts — avoiding
the race condition that would occur if both workflows fired on `push` at the same time.

The workflow downloads the four `coverage-*` artifacts from the triggering CI run using
`dawidd6/action-download-artifact@v6` (keyed by `run_id`), injects the HTML reports into
`docs-sphinx/source/_static/coverage/`, then runs `make html`. See the
[Sphinx Documentation section](#sphinx-documentation-github-pages) above and the
[Coverage Reports](testing.md#coverage-reports) section in Testing for full details.

---

## Docker Compose (Local Development)

The `docker-compose.yml` at the project root starts the full stack locally with SQLite databases.

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Required: SECRET_KEY, OPENAI_API_KEY, TAVILY_API_KEY

# 2. Build and start all services
docker compose up --build
```

Local service ports:

| Service | Internal port | Exposed port | URL |
|---------|--------------|-------------|-----|
| auth-service | 8000 | 8001 | http://localhost:8001 |
| inventory-service | 8000 | 8002 | http://localhost:8002 |
| transaction-service | 8000 | 8003 | http://localhost:8003 |
| agentic-service | 8000 | 8004 | http://localhost:8004 |
| frontend | 5173 | 5173 | http://localhost:5173 |

All backend containers share the `wallabot-net` Docker network. A `wallabot-data` named volume
persists the SQLite database files across `docker compose down` restarts (use
`docker compose down -v` to fully wipe all data).

### Running only the backend (frontend on host)

```bash
docker compose up --build auth-service inventory-service transaction-service agentic-service
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

---

## Environment Variables Reference

| Variable | Required | Services | Description |
|----------|---------|---------|-------------|
| `SECRET_KEY` | Yes | auth, inventory, transaction | JWT signing key shared across all services |
| `OPENAI_API_KEY` | Yes | agentic | GPT-4o-mini API key |
| `TAVILY_API_KEY` | Yes | agentic | Tavily web search API key |
| `AUTH_DATABASE_URL` | No | auth | Full database URL; falls back to SQLite |
| `DATABASE_URL` | No | inventory, transaction | Full database URL; falls back to SQLite |
| `INVENTORY_UPLOAD_DIR` | No | inventory | Image upload directory (default: `data/uploads/`) |
| `SUPABASE_URL` | No | inventory | Supabase project URL for cloud storage |
| `SUPABASE_SERVICE_ROLE_KEY` | No | inventory | Supabase service-role key |
| `GOOGLE_CLIENT_ID` | No | auth | Google OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | No | auth | Google OAuth 2.0 client secret |
| `FACEBOOK_CLIENT_ID` | No | auth | Facebook OAuth app ID |
| `FACEBOOK_CLIENT_SECRET` | No | auth | Facebook OAuth app secret |
| `LANGCHAIN_TRACING_V2` | No | agentic | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | agentic | LangSmith API key |
| `LANGSMITH_PROJECT` | No | agentic | LangSmith project name (default: `wallabot`) |
