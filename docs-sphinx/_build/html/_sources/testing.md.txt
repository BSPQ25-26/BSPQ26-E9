# Testing & Quality

## Overview

Wallabot enforces a **50% minimum code coverage** threshold across all backend services.
The CI pipeline fails if any service falls below this threshold. All four services exceed
this threshold significantly — the current measured coverage, obtained by running the full
test suite locally, is summarised below.

---

## Coverage Summary

| Service | Tests | Lines covered | Coverage |
|---------|------:|:-------------:|---------:|
| auth-service | 34 | 331 / 415 | **80%** |
| inventory-service | 44 | 267 / 301 | **89%** |
| transaction-service | 57 | 511 / 619 | **83%** |
| agentic-service | 75 | 277 / 318 | **87%** |
| **Total** | **210** | **1 386 / 1 653** | **84%** |

> Coverage is measured with `pytest-cov` against each service's `app/` package.
> The 50% minimum threshold is enforced by `--cov-fail-under=50` in every test run.

---

## Per-Service Breakdown

### Auth Service — 80%

Run:

```bash
cd backend/auth-service
pytest --cov=app --cov-report=term-missing -q
```

| Module | Stmts | Miss | Cover |
|--------|------:|-----:|------:|
| `api/deps.py` | 10 | 0 | **100%** |
| `api/v1/auth_router.py` | 20 | 1 | **95%** |
| `api/v1/rating_router.py` | 11 | 0 | **100%** |
| `api/v1/social_auth_router.py` | 92 | 38 | 59% |
| `api/v1/user_router.py` | 37 | 3 | **92%** |
| `core/security.py` | 26 | 0 | **100%** |
| `models/rating.py` | 16 | 0 | **100%** |
| `models/social_account.py` | 14 | 0 | **100%** |
| `models/user.py` | 11 | 0 | **100%** |
| `repositories/rating_repository.py` | 13 | 0 | **100%** |
| `repositories/user_repository.py` | 23 | 0 | **100%** |
| `services/auth_service.py` | 25 | 2 | **92%** |
| `services/rating_service.py` | 47 | 22 | 53% |
| `db/init_db.py` | 27 | 10 | 63% |

**Test files:**

| File | What it covers |
|------|---------------|
| `test_register.py` | User registration, duplicate email rejection, password hashing |
| `test_login.py` | JWT issuance, wrong password, unknown user |
| `test_auth_middleware.py` | Bearer token validation, expired token rejection |
| `test_social_auth.py` | OAuth callback handling, account linking flow |
| `test_ratings.py` | Star rating creation, invalid star rejection (422), self-rating guard |
| `test_profile.py` | Public user profile endpoint, average rating calculation |
| `test_auth_integration_flow.py` | Full register → login → protected-route end-to-end flow |

The lowest coverage is in `social_auth_router.py` (59%) because the OAuth redirect flows
require a live OAuth provider to test fully, and `rating_service.py` (53%) which has
several guard branches around completed-transaction requirements.

---

### Inventory Service — 89%

Run:

```bash
cd backend/inventory-service
pytest --cov=app --cov-report=term-missing -q
```

| Module | Stmts | Miss | Cover |
|--------|------:|-----:|------:|
| `api/v1/product_router.py` | 112 | 13 | **88%** |
| `auth.py` | 19 | 3 | **84%** |
| `db/init_db.py` | 15 | 3 | 80% |
| `db/session.py` | 14 | 4 | 71% |
| `main.py` | 31 | 8 | 74% |
| `models/product.py` | 27 | 0 | **100%** |
| `repositories/product_repository.py` | 26 | 1 | **96%** |
| `schemas/product.py` | 55 | 2 | **96%** |

**Test files:**

| File | What it covers |
|------|---------------|
| `test_products.py` | Full CRUD (create, read, update, delete), filtering by category/condition/price range, keyword search, image upload, auth enforcement |
| `test_schema_validators.py` | Pydantic schema validation for `ProductCreate`, `ProductUpdate`, `ProductOut` edge cases |

The inventory service achieves the highest overall coverage (89%) because its core business
logic — the product repository and schemas — is almost entirely covered. The uncovered lines
in `main.py` and `db/session.py` are production startup paths (Supabase Storage
initialisation, PostgreSQL connection) that require external services.

---

### Transaction Service — 83%

Run:

```bash
cd backend/transaction-service
pytest --cov=app --cov-report=term-missing -q
```

| Module | Stmts | Miss | Cover |
|--------|------:|-----:|------:|
| `api/deps.py` | 10 | 1 | **90%** |
| `core/config.py` | 16 | 1 | **94%** |
| `core/exceptions.py` | 28 | 3 | **89%** |
| `core/logging.py` | 30 | 1 | **97%** |
| `core/security.py` | 11 | 8 | 27% |
| `database.py` | 15 | 7 | 53% |
| `main.py` | 57 | 5 | **91%** |
| `models.py` | 62 | 3 | **95%** |
| `routers/products.py` | 61 | 31 | 49% |
| `routers/transactions.py` | 228 | 42 | **82%** |
| `routers/wallet.py` | 59 | 6 | **90%** |
| `schemas.py` | 31 | 0 | **100%** |
| `services/state_machine.py` | 11 | 0 | **100%** |

**Test files:**

| File | What it covers |
|------|---------------|
| `test_state_transitions.py` | All product state machine transitions (Available → Reserved → Sold), invalid transition rejection, background expiry, atomic purchase (wallet debit + product state in one transaction) |

The `services/state_machine.py` module — the critical correctness invariant — achieves
**100% coverage**. The low score on `routers/products.py` (49%) reflects admin/internal
endpoints not exercised by the public test suite. `core/security.py` is low because it
contains production JWT validation helpers invoked only under live PostgreSQL configuration.

---

### Agentic Service — 87%

Run:

```bash
cd backend/agentic-service
pytest --cov=app --cov-report=term-missing -q
```

| Module | Stmts | Miss | Cover |
|--------|------:|-----:|------:|
| `agent/category_agent.py` | 72 | 2 | **97%** |
| `agent/price_agent.py` | 94 | 11 | **88%** |
| `agent/tracing.py` | 45 | 0 | **100%** |
| `api/wallabot_router.py` | 31 | 6 | **81%** |
| `main.py` | 20 | 6 | 70% |
| `schemas/category.py` | 15 | 0 | **100%** |
| `schemas/price.py` | 18 | 0 | **100%** |

**Test files:**

| File | What it covers |
|------|---------------|
| `test_category_agent.py` | Unit tests using mock chains: happy path, retry-on-parse-failure, retry-exhaustion, provider-down fallback, retry payload feedback content |
| `test_category_endpoint.py` | HTTP endpoint tests via FastAPI `TestClient`: request validation, 200 responses, 422 on empty categories |
| `test_category_schema.py` | `CategoryRequest` and `CategorySuggestion` Pydantic schema validation |
| `test_price_agent.py` | Unit tests: happy path, Tavily available/unavailable branches, condition multiplier fallback |
| `test_price_live.py` | Live integration tests — makes real calls to OpenAI and Tavily; validates response structure, price range invariants, and condition ordering |
| `test_tracing.py` | LangSmith tracing module: `is_tracing_enabled()`, `get_project_name()`, disabled tracing no-ops, latency threshold constants |

The `agent/tracing.py` module achieves **100% coverage** and `category_agent.py` reaches
**97%** — only two lines (the final `raise RuntimeError` guard in the error path) are not
exercised. The live tests in `test_price_live.py` make real API calls and account for the
~105 second test suite execution time.

---

## Test Layers

### Unit Tests (per service)

Each backend service has its own `tests/` (or `test/`) directory with pytest-based unit
tests. Tests use in-memory SQLite databases so there are no external runtime dependencies.
The agentic service tests additionally include a live test suite (`test_price_live.py`) that
calls the real OpenAI and Tavily APIs to verify end-to-end agent behaviour.

### Integration Tests

Located in `tests/integration/`, these exercise cross-service flows using a live
Docker Compose stack.

Key flows covered:

- Full registration → login → product creation → purchase flow
- Product state machine transitions: Available → Reserved → Sold
- Wallet deposit → reservation → purchase atomicity
- Social OAuth callback handling

Run integration tests:

```bash
docker compose up -d
pytest tests/integration/ -v
```

### Performance / Load Tests

Located in `tests/performance/`, these use [Locust](https://locust.io/) to simulate
concurrent user traffic and measure response latency under load.

```bash
locust -f tests/performance/locustfile.py --host http://localhost:8001
```

The Locust web UI is available at `http://localhost:8089`. Use it to configure the number
of users and spawn rate interactively.

### Smoke Tests

Located in `tests/smoke/`, these verify that all services in the Docker Compose stack
respond to their `/health` endpoint after startup. Run automatically in CI after the
Docker image build job completes.

---

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

---

## Coverage Reports

HTML coverage reports are generated as CI artifacts for each service. The CI pipeline
runs:

```bash
pytest --cov=app --cov-report=xml --cov-report=html --cov-fail-under=50
```

Reports are uploaded as GitHub Actions artifacts named `coverage-{service-name}` and
are available for download from the Actions run summary page.

---

## Linting

| Language | Tool | Config file |
|----------|------|-------------|
| Python | `ruff` | `pyproject.toml` in each service |
| JavaScript | `ESLint` | `frontend/.eslintrc.*` |

```bash
# Python (all services)
ruff check backend/

# JavaScript
cd frontend && npm run lint
```

`ruff` is configured to enforce PEP 8 style, import ordering, and a set of
pyflakes and pycodestyle rules. The CI pipeline fails the `lint-python` job on any
`ruff` error.
