# Project Overview

## What is Wallabot?

Wallabot is a full-stack **C2C (consumer-to-consumer) second-hand marketplace** inspired by
Wallapop. It allows users to list products, browse listings, reserve items, and complete
purchases through a digital wallet. The platform is augmented by an AI subsystem — the
*Wallabot Agentic Service* — which provides intelligent product classification and price
recommendations powered by LangChain and OpenAI GPT-4o-mini.

## Key Features

- **User authentication** — email/password registration and login with JWT, plus OAuth via
  Google and Facebook.
- **Product catalogue** — create, browse, filter, and search listings with image uploads.
- **Smart AI assistance** — automatic category suggestion and market-based price estimation
  when creating a listing.
- **Wallet & transactions** — deposit funds, reserve products, and complete peer-to-peer
  purchases atomically.
- **User ratings** — buyers and sellers can rate each other after a completed transaction.
- **Internationalisation** — the frontend supports English and Spanish (`vue-i18n`).

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Vite, Pinia, Vue Router, Axios, vue-i18n |
| Backend (all services) | Python 3.11+, FastAPI 0.135, SQLAlchemy 2, Pydantic v2 |
| AI / Agentic subsystem | LangChain LCEL, OpenAI GPT-4o-mini, Tavily Web Search |
| Observability | LangSmith tracing (optional), structlog structured logging |
| Database (local) | SQLite per service |
| Database (production) | PostgreSQL on Supabase, 3 service-scoped roles |
| Container | Docker, Docker Compose |
| Deployment | Render Blueprint |
| CI/CD | GitHub Actions |

## Repository Layout

```
BSPQ26-E9/
├── backend/
│   ├── auth-service/          # JWT auth, social login, ratings
│   ├── inventory-service/     # Product catalogue and image storage
│   ├── transaction-service/   # Wallet, reservation, purchase
│   └── agentic-service/       # AI category & price agents
├── frontend/                  # Vue 3 SPA
├── tests/
│   ├── integration/           # Cross-service end-to-end tests
│   ├── performance/           # Locust load tests
│   └── smoke/                 # Docker Compose health checks
├── docs-sphinx/               # This documentation
├── docker-compose.yml
├── render.yaml
└── .github/workflows/
```

## Local Quick-Start

```bash
# 1. Copy environment template
cp .env.example .env
# 2. Start all services (requires Docker)
docker compose up --build
```

Once running the services are available at:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Auth Service | http://localhost:8001 |
| Inventory Service | http://localhost:8002 |
| Transaction Service | http://localhost:8003 |
| Agentic Service | http://localhost:8004 |
