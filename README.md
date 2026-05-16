# BSPQ26-E9

Wallabot is a multi-service marketplace built around a Vue frontend, four FastAPI backend services, and a Docker-based container
 stack. The application covers authentication, product browsing and management, wallet and transaction flows, and AI-assisted category and pricing support.

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

