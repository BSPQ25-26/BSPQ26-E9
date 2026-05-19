# Project Overview

## What is Wallabot?

Wallabot is a full-stack **C2C (consumer-to-consumer) second-hand marketplace** inspired by
Wallapop. It allows registered users to list products, browse the catalogue, reserve items,
and complete peer-to-peer purchases through an integrated digital wallet. The platform is
augmented by an AI subsystem — the *Wallabot Agentic Service* — which provides intelligent
product category suggestion and live market-based price estimation powered by LangChain LCEL,
OpenAI GPT-4o-mini, and Tavily web search.

The project was developed across three sprints by team **BSPQ26-E9** as part of the
Software Engineering course at the University of Deusto.

---

## Sprint Deliverables

| Sprint | Main deliverables |
|--------|------------------|
| Sprint 1 | User registration & login, product CRUD, basic catalogue browsing |
| Sprint 2 | Digital wallet, product reservation with configurable timeout, atomic purchase flow, transaction history |
| Sprint 3 | AI category suggestion agent, AI price recommendation agent, LangSmith observability tracing, user ratings system, public user profiles, full-text search on catalogue |

---

## Key Features

### User Management & Authentication

- Email and password registration with **bcrypt** password hashing
- JWT-based stateless authentication (HS256) shared across all microservices via a
  single `SECRET_KEY` environment variable — no inter-service token validation call per request
- Social login via **Google OAuth 2.0** and **Facebook OAuth** using the `authlib` library
- Account linking: a social account is bound to one provider and rejects conflicting
  link attempts (you cannot link the same email to two different providers)
- Token payload: `{"sub": "<user_email>", "exp": <unix_timestamp>}`

### Product Catalogue

- Full CRUD for product listings with optional image upload
- Advanced filtering by state, category, price range, condition, and free-text keyword
  search (SQLite `LIKE` in development; full-text search enabled in PostgreSQL production)
- Images stored on the local filesystem (`data/uploads/`) in development or on
  **Supabase Storage** in production (configurable via environment variables)
- Product conditions: `New`, `Like New`, `Good`, `Fair`, `Poor`
- Product states: `Available`, `Reserved`, `Sold`

### AI-Powered Seller Assistance

- **Category suggestion** — the Wallabot agent classifies a new listing into the most
  appropriate category from a caller-provided taxonomy using GPT-4o-mini
- **Price recommendation** — the agent queries Tavily for live market prices and returns
  a structured EUR estimate (point estimate + range) adjusted for declared condition
- Both agents operate with full retry logic (up to 3 attempts with correction feedback)
  and graceful fallbacks so the seller always receives a usable response
- Optional **LangSmith** tracing for every chain invocation (validation failures,
  latency threshold alerts, full input/output traces)

### Wallet & Commerce

- Digital wallet with an **append-only ledger** pattern — balance is never stored
  directly but derived from the last entry in `wallet_ledger` for tamper-proof auditability
- **Reservation system** with a configurable timeout and a background cleanup daemon that
  automatically releases expired reservations and returns products to `Available`
- **Atomic purchase**: wallet debit (buyer) and wallet credit (seller) are executed
  simultaneously with the product state transition in a single database transaction,
  preventing partial-update inconsistencies
- Complete per-user transaction history

### Social Features

- Star ratings (1–5 stars) with optional free-text review, submitted after a completed
  transaction
- Public user profiles: shows average rating, number of active listings, and member-since
  date

### Internationalisation

- Full English and Spanish UI support via `vue-i18n` (9.14.5)
- Language selection persisted in `localStorage`
- All API error messages bilingual where applicable

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend framework | Vue 3 | 3.5.30 |
| Frontend build tool | Vite | 8.0.0 |
| State management | Pinia | 3.0.4 |
| HTTP client | Axios | 1.13.6 |
| Internationalisation | vue-i18n | 9.14.5 |
| Backend framework | FastAPI | 0.135.1 |
| Language | Python | 3.11+ |
| ORM | SQLAlchemy | 2.0.48 |
| Request validation | Pydantic v2 | latest |
| AI orchestration | LangChain LCEL | latest |
| LLM | OpenAI GPT-4o-mini | via API |
| Web search | Tavily | via API |
| Observability | LangSmith | optional |
| Structured logging | structlog | latest |
| JWT / crypto | python-jose + passlib | latest |
| Social OAuth | authlib | latest |
| Database (dev / CI) | SQLite (per service) | bundled |
| Database (production) | PostgreSQL on Supabase | latest |
| Containerisation | Docker + Docker Compose | latest |
| Production deployment | Render Blueprint | — |
| CI/CD | GitHub Actions | — |
| Documentation | Sphinx + MyST + RTD theme | — |

---

## Repository Layout

```
BSPQ26-E9/
├── backend/
│   ├── auth-service/              # JWT auth, social login, ratings, user profiles
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/            # auth_router, social_auth_router, rating_router, user_router
│   │   │   ├── core/              # security (JWT helpers, bcrypt)
│   │   │   ├── db/                # session, init_db
│   │   │   ├── models/            # User, SocialAccount, Rating
│   │   │   ├── repositories/      # user_repository, rating_repository
│   │   │   ├── schemas/           # auth, rating, user, common
│   │   │   └── services/          # auth_service, rating_service
│   │   └── tests/                 # 34 unit + integration tests (80% coverage)
│   │
│   ├── inventory-service/         # Product catalogue and image storage
│   │   ├── app/
│   │   │   ├── api/v1/            # product_router (CRUD + filtering + uploads)
│   │   │   ├── db/                # session, init_db
│   │   │   ├── models/            # Product (inventory_products table)
│   │   │   ├── repositories/      # product_repository
│   │   │   └── schemas/           # ProductCreate, ProductOut, ProductUpdate
│   │   └── tests/                 # 44 unit tests (89% coverage)
│   │
│   ├── transaction-service/       # Wallet, reservation, purchase, state machine
│   │   ├── app/
│   │   │   ├── core/              # config, logging, exceptions, security
│   │   │   ├── routers/           # products, wallet, transactions
│   │   │   ├── services/          # state_machine (Available→Reserved→Sold)
│   │   │   ├── models.py          # Product, WalletLedger, Transaction, ProductStateHistory
│   │   │   └── schemas.py         # all transaction schemas
│   │   └── tests/                 # 57 unit tests (83% coverage)
│   │
│   └── agentic-service/           # AI agents: category suggestion + price recommendation
│       ├── app/
│       │   ├── agent/             # category_agent, price_agent, tracing
│       │   ├── api/               # wallabot_router
│       │   └── schemas/           # CategoryRequest/Suggestion, PriceRequest/Recommendation
│       └── test/                  # 75 tests including live API tests (87% coverage)
│
├── frontend/                      # Vue 3 SPA
│   ├── src/
│   │   ├── views/                 # LoginView, RegisterView, ProductsView, ProductDetailView,
│   │   │                          #   CreateProductView, WalletView, ProfileView, etc.
│   │   ├── components/            # Base components (Button, Card), Layout, Feedback
│   │   ├── stores/                # auth.js (Pinia — JWT from localStorage)
│   │   ├── services/              # auth.service.js, product.service.js,
│   │   │                          #   wallet.service.js, wallabot.service.js
│   │   ├── router/                # Vue Router (hash mode, auth guards)
│   │   └── i18n/                  # en.json, es.json locale files
│   └── ...
│
├── tests/
│   ├── integration/               # Cross-service end-to-end test flows
│   ├── performance/               # Locust load tests
│   └── smoke/                     # Docker Compose health checks
│
├── docs-sphinx/                   # This documentation (Sphinx + MyST)
├── docker-compose.yml             # Local full-stack environment
├── render.yaml                    # Render Blueprint (production deployment)
└── .github/workflows/             # CI, CD, and docs pipelines
```

---

## Local Quick-Start

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Required: SECRET_KEY, OPENAI_API_KEY, TAVILY_API_KEY
# Optional: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GOOGLE_CLIENT_ID, FACEBOOK_CLIENT_ID
# Optional: LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY

# 2. Build and start all services
docker compose up --build
```

Once running, all services are available at:

| Service | URL | Interactive API docs |
|---------|-----|---------------------|
| Frontend | http://localhost:5173 | — |
| Auth Service | http://localhost:8001 | http://localhost:8001/docs |
| Inventory Service | http://localhost:8002 | http://localhost:8002/docs |
| Transaction Service | http://localhost:8003 | http://localhost:8003/docs |
| Agentic Service | http://localhost:8004 | http://localhost:8004/docs |

FastAPI generates interactive **Swagger UI** at `/docs` and **ReDoc** at `/redoc` for
each service. These are the fastest way to explore and test individual endpoints manually.

---

## Design Principles

### Microservices with No Shared Database

Each service owns its database exclusively. Cross-service reads use HTTP calls with
service-scoped JWTs (e.g. the Auth Service fetches listing counts from the Inventory
Service to populate the public profile endpoint). This ensures every service can be
deployed, scaled, and tested independently.

### Stateless JWT Authentication

JWTs are self-contained: each service validates the token locally using the shared
`SECRET_KEY` without calling the Auth Service per request. The `sub` claim carries the
user's email and serves as the canonical `user_id` across all services.

### Reliability by Design

The AI agents (Category and Price) are built so that they **never block the seller flow**.
Every agent path ends in either a successful result or a graceful fallback with a
`confidence=0.0` / `"fallback: no market data found"` signal. A complete LLM provider
outage is handled silently with a hardcoded conservative estimate.

### Immutable Audit Trails

Both the wallet ledger and the product state history use append-only rows — balances are
derived from the latest ledger entry, and every state transition is recorded with the
actor and timestamp. No financial or commerce data is ever deleted or overwritten.
