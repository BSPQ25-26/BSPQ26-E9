# System Architecture

## Design Philosophy

Wallabot follows a **microservices architecture** where each business domain is encapsulated
in an independently deployable FastAPI service. Services share no databases and communicate
only via HTTP REST. The Vue 3 frontend is the sole public entry point and routes every
API call through a Vite proxy in development (or Nginx in production) to the appropriate
service.

Key design decisions:
- **No shared database** — each service owns its schema; cross-service data access goes
  over HTTP with service-scoped JWTs
- **Stateless JWT validation** — every service validates tokens locally, eliminating a
  central auth round-trip per request
- **Append-only ledger** — wallet balance and product state history are immutable,
  audit-safe records
- **Graceful AI degradation** — agents always return a usable response even when the LLM
  provider is unreachable

---

## High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Vue 3 Frontend (:5173)                        │
│  Vite dev proxy (development)  /  nginx.render.conf (production)     │
└───────┬──────────────┬──────────────┬──────────────┬────────────────┘
        │ /auth/*      │ /api/v1/*    │ /products/*  │ /wallabot/*
        │ /users/*     │ /uploads/*   │ /wallet/*    │
        ▼              ▼              ▼              ▼
  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌──────────────┐
  │   Auth   │  │ Inventory │  │ Transaction  │  │   Agentic    │
  │ Service  │  │  Service  │  │   Service    │  │   Service    │
  │  :8001   │  │   :8002   │  │    :8003     │  │    :8004     │
  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  └──────┬───────┘
       │              │               │                  │
    SQLite/        SQLite/         SQLite/          OpenAI API
    PostgreSQL     PostgreSQL      PostgreSQL       Tavily API
                                                   LangSmith (opt.)
```

The Agentic Service has **no database** — every request is stateless and fully
self-contained.

---

## Service Responsibilities

### Auth Service (:8001)

The single source of truth for user identity. Every other service validates JWTs issued
here by sharing the same `SECRET_KEY` — no cross-service call is needed per request.

**Responsibilities:**
- User registration with bcrypt password hashing (`passlib[bcrypt]`)
- Email/password login and JWT issuance (`python-jose`, HS256 algorithm)
- Social OAuth flow for Google and Facebook (via `authlib`); handles redirect,
  code exchange, and account linking
- Account merging: links a social account to an existing email account when the email
  matches; rejects conflicting provider links
- Star ratings (1–5) between users with optional review text
- Public user profile endpoint: aggregates listing count from Inventory Service via
  an internal service token

**Key models:** `User`, `SocialAccount`, `Rating`

**API prefix:** `/auth/*`, `/users/*`, `/ratings/*`

---

### Inventory Service (:8002)

Owns the product catalogue: the *listing* representation of a product, independent
of its commerce state.

**Responsibilities:**
- Full CRUD on product listings
- Image upload and serving (local filesystem `data/uploads/` or Supabase Storage)
- Advanced filtering: state, category, price range, condition, full-text keyword search
- Hosts static files at `/uploads/`

**Key model:** `Product` (table: `inventory_products`)

The Inventory product is **distinct** from the Transaction product. They are separate
data copies in separate databases:
- **Inventory** tracks listing metadata (title, description, price, image, category)
- **Transaction** tracks commerce state (reservation owner, purchase record, state history)

**API prefix:** `/api/v1/products/*`, `/uploads/*`

---

### Transaction Service (:8003)

Owns the commerce domain: wallets, reservations, and purchases.

**Responsibilities:**
- Digital wallet with an immutable ledger-based balance (never stores balance as a column)
- Product reservation with configurable timeout and a background daemon that releases
  expired reservations automatically
- Atomic purchase: wallet debit, wallet credit, and product state transition executed in
  a single database transaction
- Per-user transaction history
- Product state machine enforcement

**Key models:**
- `Product` (table: `transaction_products`) — mirrors inventory data at reservation time
- `WalletLedger` — append-only balance rows (delta, type, balance_after)
- `Transaction` — purchase records
- `ProductStateHistory` — every state transition with actor and timestamp

**API prefix:** `/products/*`, `/wallet/*`, `/transactions/*`

---

### Agentic Service (:8004)

The AI subsystem. Every endpoint is stateless — no memory between requests, no database.

**Responsibilities:**
- Category suggestion using LangChain LCEL + GPT-4o-mini
- Price recommendation using Tavily web search + GPT-4o-mini
- Retry logic and graceful degradation on any provider failure
- Optional LangSmith tracing for every chain invocation

See [Wallabot AI Agent](wallabot_agent.md) for full technical details.

**API prefix:** `/wallabot/*`, `/health`

---

## Authentication Flow

JWT tokens are self-contained: each service validates the token locally using the shared
`SECRET_KEY` without calling the Auth Service. The subject (`sub`) claim contains the
user's email address and is used as the `user_id` throughout all services.

```
Client               Auth Service             Other Services
  │                       │                         │
  │─ POST /auth/login ────►│                         │
  │◄─ {access_token} ─────│                         │
  │                       │                         │
  │─ GET /api/v1/products ──────────────────────────►│
  │  Authorization: Bearer <token>                   │
  │  (token validated locally — no Auth Service call)│
  │◄─ [...products] ────────────────────────────────│
```

**Service-to-service calls** (e.g. Auth Service fetching listing counts from Inventory)
use a service token with `sub: service@internal` generated at startup and never exposed
to external clients.

**Social OAuth flow:**

```
Browser              Auth Service           OAuth Provider
  │                       │                     │
  │─ GET /auth/social/login/google ────────────►│
  │◄─ 302 redirect to Google ──────────────────│
  │                       │                     │
  │─ GET /auth/social/callback/google ─────────►│
  │  ?code=... &state=...                       │
  │                       │─ exchange code ─────►│
  │                       │◄─ user profile ──────│
  │                       │  (create or link account)
  │◄─ {access_token} ─────│
```

---

## Product State Machine

Products in the **Transaction Service** follow a strict state machine enforced in
`app/services/state_machine.py`. The `Available → Reserved → Sold` path is the only
valid forward path.

```
  ┌───────────┐   reserve   ┌──────────┐   purchase   ┌──────┐
  │ Available │────────────►│ Reserved │─────────────►│ Sold │
  └───────────┘             └──────────┘              └──────┘
       ▲                         │
       └─────────────────────────┘
         timeout expires / explicit release
```

| Transition | HTTP endpoint | Guard conditions |
|-----------|---------------|------------------|
| Available → Reserved | `POST /products/{id}/reserve` | Caller must not be the seller; product must be `Available` |
| Reserved → Available | Background daemon or `DELETE /products/{id}/reserve` | Caller must be the reservation owner or reservation has expired |
| Reserved → Sold | `POST /products/{id}/purchase` | Caller must be the reservation owner and have sufficient wallet funds |
| Sold → * | — | Final state; no further transitions permitted |

Every transition writes a row to `ProductStateHistory` with `actor` (user email) and
`timestamp`, providing a full immutable audit trail.

---

## Wallet Ledger Architecture

The wallet uses an **append-only ledger** pattern for balance integrity. The current
balance is never stored directly in a column — it is always derived from the `balance_after`
column of the most recent row for that user.

```
WalletLedger table (append-only — rows are never updated or deleted):

┌────┬──────────────────┬────────┬──────┬────────────────┐
│ id │ user_id          │  delta │ type │ balance_after  │
├────┼──────────────────┼────────┼──────┼────────────────┤
│  1 │ alice@example.com│ +100.0 │ dep  │ 100.00         │
│  2 │ alice@example.com│  +50.0 │ dep  │ 150.00         │
│  3 │ alice@example.com│ -420.0 │ pur  │ (refused)      │
│  4 │ alice@example.com│ -420.0 │ pur  │ -270.00        │
└────┴──────────────────┴────────┴──────┴────────────────┘

Current balance = balance_after WHERE id = MAX(id) AND user_id = 'alice@example.com'
```

| Entry type | Description |
|------------|-------------|
| `dep` | Top-up (wallet deposit) |
| `pur` | Purchase debit (buyer) |
| `sal` | Sale credit (seller, on successful purchase) |

Every wallet mutation (top-up, purchase debit, sale credit) creates a **new row**.
`UPDATE` statements on `wallet_ledger` are never issued. This guarantees a complete,
immutable financial audit trail.

---

## Atomic Purchase Flow

The purchase operation is the most complex transaction in the system. It must atomically:

1. Read the buyer's current balance
2. Verify the buyer has sufficient funds
3. Debit the buyer's wallet (new ledger row)
4. Credit the seller's wallet (new ledger row)
5. Transition the product from `Reserved` to `Sold` in the Transaction Service
6. Record the transition in `ProductStateHistory`

All six steps execute inside a single SQLAlchemy `Session` with a database-level
transaction. If any step fails, the entire transaction is rolled back — no partial
state is possible.

```
POST /products/{id}/purchase
  │
  ├─ Validate: caller is reservation owner
  ├─ BEGIN TRANSACTION
  │   ├─ Read latest WalletLedger row for buyer → current_balance
  │   ├─ Verify current_balance >= product.price
  │   ├─ INSERT WalletLedger (buyer, -price, "pur", current_balance - price)
  │   ├─ INSERT WalletLedger (seller, +price, "sal", seller_balance + price)
  │   ├─ UPDATE transaction_products SET state = "Sold"
  │   ├─ INSERT ProductStateHistory (actor=buyer, from=Reserved, to=Sold)
  │   └─ INSERT Transaction record
  └─ COMMIT → HTTP 200
     ROLLBACK on any error → HTTP 4xx/5xx
```

---

## Database Strategy

| Environment | Engine | Notes |
|------------|--------|-------|
| Local development | SQLite (per service, file-based) | Auto-created by SQLAlchemy `create_all()` on startup |
| CI pipeline | SQLite (in-memory or temp file) | Isolated per test run; no external dependencies |
| Production | PostgreSQL on Supabase | Three independent DB roles: `auth_service_user`, `inventory_service_user`, `transaction_service_user` |

Services use **no shared database**. Cross-service data access is done via HTTP with
service-scoped JWTs. The Agentic Service has no database at all.

---

## Frontend Architecture

The Vue 3 SPA uses **hash-based routing** (`createWebHashHistory`) so the frontend can
be served from any static host without server-side routing configuration.

```
main.js
  └── createApp(App)
        ├── use(pinia)
        │     └── auth.js store — JWT in localStorage, reactive auth state
        ├── use(router)
        │     ├── Hash-mode routes: /login, /register, /products, /products/:id, ...
        │     ├── Navigation guard: requiresAuth → redirect /login if no token
        │     └── /auth/callback → exchanges OAuth code, stores JWT, redirect /products
        ├── use(i18n)        — en / es locale files
        └── mount('#app')
```

**HTTP service modules** (`src/services/`):

| Module | Routes called |
|--------|--------------|
| `auth.service.js` | `/auth/register`, `/auth/login`, `/auth/social/*` |
| `product.service.js` | `/api/v1/products*`, `/uploads/*` |
| `wallet.service.js` | `/wallet/*`, `/products/*/reserve`, `/products/*/purchase` |
| `wallabot.service.js` | `/wallabot/category`, `/wallabot/price` |

In **production**, `nginx.render.conf` replaces the Vite proxy and forwards each URL
prefix to the corresponding Render service's internal URL.

---

## Deployment Architecture (Production)

All services are deployed on **Render** via the `render.yaml` Blueprint:

```
render.yaml
  ├── wallabot-frontend (Static Site — Nginx)
  │     nginx.render.conf → proxy_pass to each Render service
  │
  ├── wallabot-auth (Web Service — Docker)
  │     persistent disk at /app/data (SQLite in free tier, PostgreSQL for production)
  │
  ├── wallabot-inventory (Web Service — Docker)
  │     persistent disk at /app/data
  │
  ├── wallabot-transaction (Web Service — Docker)
  │     persistent disk at /app/data
  │
  └── wallabot-agentic (Web Service — Docker)
        no persistent disk (stateless)
```

On every push to `main`, Render automatically rebuilds and redeploys only the services
whose source directories have changed.

---

## CI/CD Pipeline

The GitHub Actions CI pipeline (`ci.yml`) runs on every push and pull request:

| Job | What it does |
|-----|-------------|
| `lint-python` | `ruff check` on all backend services |
| `lint-frontend` | `npm ci && npm run lint` in `frontend/` |
| `test-auth-service` | `pytest --cov=app --cov-fail-under=50` |
| `test-inventory-service` | `pytest --cov=app --cov-fail-under=50` |
| `test-transaction-service` | `pytest --cov=app --cov-fail-under=50` |
| `test-agentic-service` | `pytest --cov=app --cov-fail-under=50` |
| `docker-build` | Builds all images; runs smoke health checks |
| `sphinx-docs` | Builds HTML + PDF; deploys to GitHub Pages (`gh-pages` branch) |
