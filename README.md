# BSPQ26-E9

Wallabot is a multi-service marketplace built around a Vue frontend, four FastAPI backend services, and a Docker-based container
 stack. The application covers authentication, product browsing and management, wallet and transaction flows, and AI-assisted category and pricing support.

## Live Links

| | URL |
|--|-----|
| **Application** | https://wallabot-frontend.onrender.com |
| **Documentation** | https://BSPQ25-26.github.io/BSPQ26-E9/sphinx/ |
| **Documentation (PDF)** | https://BSPQ25-26.github.io/BSPQ26-E9/sphinx/BSPQ26-E9.pdf |

> The app runs on Render's free tier — the first request after a period of inactivity may take up to 60 seconds while the containers cold-start.

## Application Flow

The user journey is centered on the frontend router:

1. `/` redirects to `/products`.
2. Anonymous users trying to access protected pages are redirected to `/login`.
3. `/login` and `/register` are public-only routes.
4. `/auth/callback` handles social login redirects.
5. `/products` is the main authenticated catalog.
6. `/products/:id` shows product details.
7. `/products/:id/create` and `/products/:id/edit` handle product creation and editing.

The frontend uses a hash router and syncs authentication state from local storage before each route change. If a protected route is requested without a token, the user is sent back to login with the original target preserved as a redirect parameter.

## Services

The backend is split into four services, each with its own responsibility:

| Service | Responsibility | Default local port |
| --- | --- | --- |
| `auth-service` | Registration, login, JWT sessions, and social auth callbacks | `8001` |
| `inventory-service` | Product CRUD, image uploads, and product catalog storage | `8002` |
| `transaction-service` | Wallet operations, reservations, sales, and transaction history | `8003` |
| `agentic-service` | AI-assisted category suggestions and pricing support | `8004` |

The frontend runs on `5173` and talks to those services through the URLs provided in the environment.

## Repository Structure

```text
BSPQ26-E9/
├── .github/
│   └── workflows/
├── backend/
│   ├── auth-service/
│   │   └── app/
│   ├── inventory-service/
│   │   ├── app/
│   │   └── migrations/
│   ├── transaction-service/
│   │   └── app/
│   └── agentic-service/
│       └── app/
├── frontend/
│   └── src/
│       ├── components/
│       ├── composables/
│       ├── router/
│       ├── stores/
│       └── views/
├── tests/
│   ├── integration/
│   ├── performance/
│   └── smoke/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Local Development

The default local setup uses Docker Compose with SQLite-backed services and optional Supabase configuration through the root `.env` file.

Start the full stack:

```bash
docker-compose up --build -d
```

Open the application at `http://localhost:5173`.

If you want the frontend on the host and only the backend services in Docker:

```bash
docker-compose up --build -d auth-service inventory-service transaction-service agentic-service
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Local environment files:
- Root `.env`: backend secrets and optional external database URLs. If
  `AUTH_DATABASE_URL`, `INVENTORY_DATABASE_URL`, or `TRANSACTION_DATABASE_URL`
  are not set, Docker Compose falls back to SQLite databases in the
  `wallabot-data` Docker volume.
- `frontend/.env`: only `VITE_*` frontend overrides. See
  `frontend/.env.example`.

If your Docker installation has Compose v2, `docker compose` is equivalent to
`docker-compose`; this machine currently provides `docker-compose`.

### **Render Deployment**

For Render, this repository uses a multi-service blueprint in [render.yaml](render.yaml).
It creates one Render web service per backend, plus a frontend web service that serves the Vue build and reverse-proxies API calls to the internal Render services.

The frontend stays on the same origin as the browser, so the app can keep using relative API paths while Render handles service-to-service routing privately.

Notes:
- The backend services use persistent disks mounted at `/app/data` so their SQLite fallbacks survive redeploys.
- `OPENAI_API_KEY` and `TAVILY_API_KEY` are left as Render secret prompts for the agentic service.
- The frontend image is defined in [frontend/Dockerfile.render](frontend/Dockerfile.render) and proxies `/auth`, `/api/v1`, `/uploads`, `/products`, `/wallet`, `/transactions`, and `/wallabot` to the matching backend services.
- All services deploy automatically from the `main` branch on every push.

To deploy, connect the repo to a Render Blueprint and point it at [render.yaml](render.yaml).

**Production service URLs:**

| Service | URL |
| --- | --- |
| Frontend | https://wallabot-frontend.onrender.com |
| Auth Service | https://wallabot-auth.onrender.com |
| Inventory Service | https://wallabot-inventory.onrender.com |
| Transaction Service | https://wallabot-transaction.onrender.com |
| Agentic Service | https://wallabot-agentic.onrender.com |

### **CI/CD Pipeline**

The project uses **GitHub Actions** to automate quality assurance. The pipeline:

1. Runs unit and integration tests.


2. Blocks merges if builds fail, ensuring continuous delivery of stable code.

### **Coverage Evidence (>50%)**

The course requirement asks for **unit test coverage >= 50%**.
In this repository coverage is measured with `pytest-cov` (see `.github/workflows/ci.yml`), using commands like:

`pytest --cov=app --cov-report=term-missing -q`

If you need explicit evidence that coverage is above the threshold, run the same tests locally but enforce the minimum with `--cov-fail-under=50`
(the command will fail if coverage is below 50%).

Examples (same idea as CI, using local SQLite DBs):

1. `auth-service`
```powershell
cd backend\auth-service
$env:DATABASE_URL="sqlite:///./test_auth.db"
$env:JWT_SECRET="ci-test-secret"
$env:JWT_EXPIRY_MINUTES="30"
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=50 -q
```

2. `inventory-service`
```powershell
cd backend\inventory-service
$env:DATABASE_URL="sqlite:///./test_inventory.db"
$env:SECRET_KEY="ci-test-secret"
$env:ALGORITHM="HS256"
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=50 -q
```

Note: if FastAPI complains about multipart uploads, install missing dependency in the venv:
`pip install python-multipart`

3. `transaction-service`
```powershell
cd backend\transaction-service
$env:DATABASE_URL="sqlite:///./transactions.db"
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=50 -q
```

4. `agentic-service`
```powershell
cd backend\agentic-service
$env:DATABASE_URL="sqlite:///./test_wallabot.db"
$env:TAVILY_API_KEY="ci-mock-key"
$env:OPENAI_API_KEY="ci-mock-key"
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=50 -q
```



---
Useful local endpoints:

| Endpoint | URL |
| --- | --- |
| Frontend | `http://localhost:5173` |
| Auth health | `http://localhost:8001/health` |
| Inventory health | `http://localhost:8002/health` |
| Transaction health | `http://localhost:8003/health` |
| Agentic health | `http://localhost:8004/health` |

Before restarting the stack, stop any existing containers and Vite process:

```bash
docker-compose down
pkill -f "$PWD/frontend/node_modules/.bin/vite" || true
```

## CI/CD Pipeline

GitHub Actions runs the project in layered stages:

1. Backend linting with `ruff`.
2. Frontend linting with ESLint.
3. Per-service pytest jobs for `auth-service`, `inventory-service`, `transaction-service`, and `agentic-service`.
4. A Docker-backed backend test job that runs the services against PostgreSQL.
5. A final Docker Compose smoke test that builds the full stack and checks each `/health` endpoint.

The pytest jobs now generate three coverage outputs:

* terminal coverage output for the job log
* XML coverage reports
* HTML coverage reports

Those reports are uploaded as CI artifacts for each service. The Docker-backed backend job also uploads a combined coverage artifact set.

### CI Artifacts

Coverage artifacts are published under these names:

* `coverage-auth-service`
* `coverage-inventory-service`
* `coverage-transaction-service`
* `coverage-agentic-service`
* `coverage-backend-docker`

## Coverage Verification

Coverage is measured with `pytest-cov`. To reproduce the CI check locally, run the relevant service test suite with a minimum threshold.

Example for `auth-service`:

```bash
cd backend/auth-service
export DATABASE_URL="sqlite:///./test_auth.db"
export JWT_SECRET="ci-test-secret"
export JWT_EXPIRY_MINUTES="30"
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=50 -q
```

The same pattern applies to the other backend services, adjusting the environment variables as needed.

