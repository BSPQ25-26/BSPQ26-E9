# BSPQ26-E9
Repository for team BSPQ26-E9

# Wallabot: AI-Powered Microservices Marketplace

Wallabot is a multi-tier, distributed **RESTful microservice architecture** designed to provide a seamless buying and selling experience. The platform integrates advanced AI capabilities via "Wallabot," an intelligent agent that assists users with automated category suggestions and competitive price recommendations.

---

## Features

### **User Management & Authentication**

* **Secure Access**: Traditional registration and login using email and password with hashed storage for security.


* **Social Integration**: OAuth2 authentication flow supporting Google and Facebook accounts.


* **Identity**: Stateless authentication handled via JWT tokens with set expirations.


* **Trust System**: A post-transaction rating (1-5 stars) and review system to build community trust.



### **Inventory & Transaction Engine**

* **Product Lifecycle**: Full CRUD operations for sellers, including image uploads (JPEG/PNG) and quality specifications.


* **State Management**: Atomic transitions between `Available`, `Reserved`, and `Sold` states to ensure data integrity.


* **Virtual Wallet**: Integrated wallet system for adding funds and making secure, balance-validated purchases.



### **Wallabot (AI Agent)**

* 
**Smart Categorization**: Automatically suggests product categories in structured JSON format.


* **Price Recommendations**: Provides competitive pricing data using **Tavily** real-time web search grounded by **OpenAI GPT-4o-mini** structured output.


* **Observability**: Uses **LangSmith** to trace every AI chain invocation, monitor latency, and alert on validation failures or slow responses.



### **User Experience**

* **Reactive Frontend**: Built with **TO BE DEFINED** for an intuitive and responsive product listing interface.


* 
**Advanced Filtering**: Capability to filter the product catalog by state, category, price range, and item quality.



---

## Stack

| Component | Technology |
| --- | --- |

 |
|  **Backend** | FastAPI (Python) 

 |
| **Frontend** | TO BE DEFINED

 |
| **Database** | TO BE DEFINED 

 |
| **AI Monitoring** | LangSmith 

 |
| **External AI API** | OpenAI (GPT-4o-mini) + Tavily Search

 |
| **Containerization** | Docker & Docker Compose 

 |
| **CI/CD** | GitHub Actions 

 

---

## Development & Deployment

## Current Project Structure

```text
BSPQ26-E9/
├── .env
├── .github/
├── .gitignore
├── LICENSE
├── README.md
├── docker-compose.yml
├── backend/
│   ├── agentic-service/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── auth-service/
│   ├── inventory-service/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── transaction-service/
│       ├── Dockerfile
│       └── requirements.txt
├── data/
│   └── test-wallabot.db
├── frontend/
│   └── Dockerfile
└── tests/
	└── integration/
```

### **Containerization**

Each microservice is containerized using optimized **Dockerfiles**. You can spin up the entire local environment, including the database and services, using **Docker Compose**.

### **Local Deployment**

The local stack uses fixed ports. Do not run the Docker frontend and a separate
`npm run dev` frontend at the same time, because both use port `5173`.

Port map:
- Frontend: `http://localhost:5173`
- Auth service: `http://localhost:8001/health`
- Inventory service: `http://localhost:8002/health`
- Transaction service: `http://localhost:8003/health`
- Wallabot agentic service: `http://localhost:8004/health`

Before a clean restart, stop old project containers and any local Vite process:

```bash
docker-compose down
pkill -f "$PWD/frontend/node_modules/.bin/vite" || true
```

Run the full app with Docker:

```bash
docker-compose up --build
```

Then open `http://localhost:5173`. The app root (`/`) redirects to `/products`;
if you are not authenticated, it redirects to `/login`.

For backend-in-Docker plus frontend-on-host development, start only the backend
services:

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

To deploy, connect the repo to a Render Blueprint and point it at [render.yaml](render.yaml).

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

## Wallabot — LangSmith Monitoring

All Wallabot LCEL chains (category suggestion and price recommendation) are
auto-instrumented by LangSmith when tracing is enabled. No code changes are
needed beyond setting the environment variables.

### Enable tracing

In `backend/agentic-service/.env` (or the root `.env`):

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your key from smith.langchain.com>
LANGCHAIN_PROJECT=wallabot
```

The service logs `Wallabot LangSmith tracing ENABLED project='wallabot'` at
startup when tracing is active.

### Accessing the dashboard

1. Open [smith.langchain.com](https://smith.langchain.com) and sign in.
2. Select the project named `wallabot` (or whatever `LANGCHAIN_PROJECT` is set to).
3. The **Traces** tab shows every chain invocation with inputs, outputs, and
   per-step latency.

### Run names and tags

| Run name | What it represents |
|----------|-------------------|
| `wallabot_category_suggest` | One category classification request (full chain) |
| `wallabot_price_recommendation` | One price recommendation request (full chain) |
| `wallabot_category_agent_validation_failure` | Parser/schema error logged during a category retry |
| `wallabot_price_agent_validation_failure` | Parser/schema error logged during a price retry |
| `wallabot_category_agent_latency_exceeded` | Category call exceeded 15 s threshold |
| `wallabot_price_agent_latency_exceeded` | Price call exceeded 30 s threshold |

All Wallabot runs are tagged `wallabot` plus the component tag (`category_agent`
or `price_agent`), making it easy to filter by agent in the dashboard.

### Setting up alert rules

In LangSmith → **Automations** → **Add Rule**:

1. **Validation-failure alert**
   - Filter: Run name contains `validation_failure`
   - Condition: count > 0 in a 5-minute window
   - Action: email / Slack webhook

2. **Latency alert**
   - Filter: Run name contains `latency_exceeded`
   - Condition: count > 0 in any window
   - Action: email / Slack webhook

### Interpreting and responding to alerts

| Alert | Likely cause | Response |
|-------|-------------|----------|
| `validation_failure` fires repeatedly | Prompt drift — LLM output stopped conforming to the JSON schema | Open the failing run in LangSmith, inspect `llm_output` in the error field, update the prompt in `prompts.py` |
| `latency_exceeded` for price agent | Tavily rate-limit or slow OpenAI response | Check Tavily dashboard for quota; consider caching frequent queries |
| `latency_exceeded` for category agent | OpenAI latency spike | Monitor OpenAI status page; the fallback path returns immediately if the provider is down |

---

## Product Backlog Highlights

The project is prioritized to ensure core functionality is delivered first:

* **High Priority (1-2)**: Email/Password Authentication, Basic Product Listings, and Containerization.


* **Medium Priority (3-5)**: Wallet Management, Image Uploads, and CI/CD Pipeline Setup.


* **AI & Social (6-9)**: Social Logins, AI Category/Price suggestions, and User Ratings.



---
