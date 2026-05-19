# DevOps & CI/CD

## Docker Compose (Local Development)

The `docker-compose.yml` at the project root starts the full stack locally.

```bash
cp .env.example .env   # fill in secrets
docker compose up --build
```

Services and ports:

| Service | Internal port | Exposed port |
|---------|--------------|-------------|
| auth-service | 8000 | 8001 |
| inventory-service | 8000 | 8002 |
| transaction-service | 8000 | 8003 |
| agentic-service | 8000 | 8004 |
| frontend | 5173 | 5173 |

All backend containers share the `wallabot-net` Docker network and the `wallabot-data`
named volume that persists SQLite database files.

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (shared by all services) |
| `OPENAI_API_KEY` | Required by agentic-service for GPT-4o-mini |
| `TAVILY_API_KEY` | Required by agentic-service for web search |
| `SUPABASE_URL` | (Optional) Supabase project URL for PostgreSQL + Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | (Optional) Supabase service-role key |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | (Optional) Google OAuth |
| `FACEBOOK_CLIENT_ID` / `FACEBOOK_CLIENT_SECRET` | (Optional) Facebook OAuth |
| `LANGCHAIN_TRACING_V2` | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | LangSmith API key |

## CI Pipeline (GitHub Actions)

The CI pipeline (`.github/workflows/ci.yml`) runs on every push and pull request.

**Jobs:**

1. **lint-python** — runs `ruff check` on all backend services
2. **lint-frontend** — runs `npm ci && npm run lint` in `frontend/`
3. **test-auth-service** — pytest with coverage, fails if < 50%
4. **test-inventory-service** — pytest with coverage, fails if < 50%
5. **test-transaction-service** — pytest with coverage, fails if < 50%
6. **test-agentic-service** — pytest with coverage, fails if < 50%
7. **docker-build** — builds all images and runs the smoke test against the live stack
8. **sphinx-docs** — builds and deploys this documentation to GitHub Pages

## CD Pipeline (Render)

Production deployments are managed via `render.yaml` (Render Blueprint).

Each service is deployed as an independent Render Web Service. On merge to `main` Render
automatically rebuilds and redeploys changed services.

| Service | Render service name | Persistent disk |
|---------|--------------------|--------------------|
| auth-service | `wallabot-auth` | `/app/data` |
| inventory-service | `wallabot-inventory` | `/app/data` |
| transaction-service | `wallabot-transaction` | `/app/data` |
| agentic-service | `wallabot-agentic` | — |
| frontend | `wallabot-frontend` | — |

## GitHub Pages (Sphinx Documentation)

This documentation site is automatically built and deployed on every push to `main` by
the `.github/workflows/sphinx-docs.yml` workflow.

**Required repository settings:**

1. Repository must be **public**
2. *Settings → Actions → General → Workflow permissions*: set to **Read and write permissions**
3. *Settings → Pages → Source*: set to **Deploy from a branch**, branch **gh-pages**, folder **/ (root)**

After the first successful workflow run, the documentation is available at:

```
https://BSPQ25-26.github.io/BSPQ26-E9/sphinx/
```

## Sphinx Documentation Workflow

The workflow (`.github/workflows/sphinx-docs.yml`) performs these steps on every push to `main`:

1. Checkout repository
2. Install Python 3.12 + dependencies from `docs-sphinx/requirements.txt`
3. Run `make html` in `docs-sphinx/`
4. Build a PDF with WeasyPrint
5. Assemble the `deploy/` directory:
   - `deploy/index.html` — redirect to `sphinx/`
   - `deploy/sphinx/` — full HTML site
   - `deploy/sphinx/BSPQ26-E9.pdf` — PDF export
6. Push `deploy/` to the `gh-pages` branch via `peaceiris/actions-gh-pages`
