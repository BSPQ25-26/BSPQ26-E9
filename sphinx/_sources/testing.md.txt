# Testing & Quality

## Overview

Wallabot enforces a **50% minimum code coverage** threshold across all backend services.
The CI pipeline fails if any service falls below this threshold.

## Test Layers

### Unit Tests (per service)

Each service has its own `tests/` directory with pytest-based unit tests. Tests use SQLite
databases (created in memory or as temp files) to avoid any external dependencies.

| Service | Test directory | Coverage threshold |
|---------|---------------|-------------------|
| auth-service | `backend/auth-service/tests/` | 50% |
| inventory-service | `backend/inventory-service/tests/` | 50% |
| transaction-service | `backend/transaction-service/tests/` | 50% |
| agentic-service | `backend/agentic-service/tests/` | 50% |

Run a single service's tests:

```bash
cd backend/auth-service
pytest --cov=app --cov-report=term-missing --cov-fail-under=50
```

### Integration Tests

Located in `tests/integration/`, these tests exercise cross-service flows using a live
Docker Compose stack.

Key flows covered:

- Full registration → login → product creation → purchase flow
- Product state machine transitions
- Wallet deposit → reservation → purchase atomicity
- Social auth callback handling

Run integration tests:

```bash
docker compose up -d
pytest tests/integration/ -v
```

### Performance / Load Tests

Located in `tests/performance/`, these use [Locust](https://locust.io/) to simulate
concurrent user traffic.

```bash
locust -f tests/performance/locustfile.py --host http://localhost:8001
```

The Locust web UI is available at `http://localhost:8089`.

### Smoke Tests

Located in `tests/smoke/`, these verify that all services in the Docker Compose stack
respond to their `/health` endpoint after startup. Run automatically in CI after the
Docker build job.

## Running All Tests Locally

```bash
# Start dependencies
docker compose up -d

# Backend unit tests (all services)
for svc in auth-service inventory-service transaction-service agentic-service; do
  echo "=== $svc ==="
  cd backend/$svc
  pip install -r requirements.txt
  pytest --cov=app --cov-fail-under=50
  cd ../..
done

# Frontend unit tests
cd frontend
npm ci
npm run test
```

## Coverage Reports

HTML coverage reports are generated as CI artifacts for each service. The CI pipeline
runs `pytest --cov=app --cov-report=xml --cov-report=html`, and the reports are uploaded
as GitHub Actions artifacts named `coverage-{service-name}`.

## Linting

| Language | Tool | Config |
|----------|------|--------|
| Python | `ruff` | `pyproject.toml` |
| JavaScript | `ESLint` | `frontend/.eslintrc.*` |

```bash
# Python
ruff check backend/

# JavaScript
cd frontend && npm run lint
```
