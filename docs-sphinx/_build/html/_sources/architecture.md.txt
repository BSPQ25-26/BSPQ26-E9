# System Architecture

## Microservices Overview

Wallabot follows a **microservices architecture**: each domain is encapsulated in an
independently deployable FastAPI service. The Vue 3 frontend acts as the sole entry point
for end users and proxies all API calls to the appropriate backend service.

```
┌─────────────────────────────────────────────────────────────┐
│                     Vue 3 Frontend (5173)                   │
│           (Vite proxy / Nginx reverse proxy in prod)        │
└──────┬──────────┬──────────┬──────────┬───────────┬─────────┘
       │ /auth    │ /api/v1  │ /products│ /wallet   │ /wallabot
       ▼          ▼          ▼          ▼           ▼
  ┌─────────┐ ┌──────────┐ ┌──────────────────────┐ ┌─────────────┐
  │  Auth   │ │Inventory │ │  Transaction Service │ │  Agentic    │
  │ Service │ │ Service  │ │       (8003)         │ │  Service    │
  │  (8001) │ │  (8002)  │ └──────────────────────┘ │   (8004)   │
  └─────────┘ └──────────┘                           └─────────────┘
```

## Service Responsibilities

### Auth Service (port 8001)

Owns user identity. All other services trust Auth Service-issued JWTs for authentication.

- User registration and login (`/auth/register`, `/auth/login`)
- Social OAuth flow with Google and Facebook (`/auth/social/...`)
- Public user profiles and ratings (`/users/{id}/profile`, `/users/{id}/ratings`)
- JWT access-token issuance with `python-jose` + `bcrypt` password hashing

### Inventory Service (port 8002)

Owns the product catalogue. Products here represent the *listing* view.

- Full CRUD for product listings (`/api/v1/products`)
- Image upload to local filesystem or Supabase Storage
- Filtering by state, category, price range, condition, and full-text keyword search

### Transaction Service (port 8003)

Owns the commerce domain. Products in this service mirror listing state but track commerce
events separately.

- Wallet operations: top-up and balance query (`/wallet`)
- Product reservation with configurable timeout (`/products/{id}/reserve`)
- Purchase completion with atomic wallet debit (`/products/{id}/purchase`)
- Transaction history (`/transactions`)
- Background reservation-expiry daemon

### Agentic Service (port 8004)

The AI subsystem. All endpoints are **stateless** — no session memory between requests.

- Category suggestion via LangChain LCEL + GPT-4o-mini (`/wallabot/category`)
- Price recommendation via Tavily web search + GPT-4o-mini (`/wallabot/price`)
- Optional LangSmith tracing for monitoring and debugging

## Authentication Flow

```
Client                  Auth Service           Other Services
  │                          │                       │
  │── POST /auth/login ──────►│                       │
  │◄── {access_token: ...} ──│                       │
  │                          │                       │
  │── GET /api/v1/products ──────────────────────────►│
  │   (Authorization: Bearer <token>)                 │
  │◄── [...products] ─────────────────────────────────│
```

JWT tokens are verified locally by each service using the shared `SECRET_KEY` environment
variable; no service-to-service auth call is required on every request.

## Product State Machine

Products in the Transaction Service follow a strict state machine:

```
Available ──► Reserved ──► Sold
     ▲            │
     └────────────┘  (timeout / explicit release)
```

| Transition | Trigger | Notes |
|-----------|---------|-------|
| Available → Reserved | `POST /products/{id}/reserve` | Holds for `RESERVATION_TIMEOUT_SECONDS` |
| Reserved → Available | Background cleanup or `DELETE /products/{id}/reserve` | Auto-releases on timeout |
| Reserved → Sold | `POST /products/{id}/purchase` | Atomically debits buyer's wallet |

## Database Strategy

| Environment | Database | Notes |
|------------|---------|-------|
| Local / CI | SQLite (per service) | Auto-created on startup |
| Production | PostgreSQL on Supabase | Three service-scoped DB roles |

Services share **no database**. Cross-service data needs (e.g. listing counts on a profile)
are satisfied by internal HTTP calls with a service-scoped JWT.
