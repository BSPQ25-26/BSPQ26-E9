# Agentic Service API (Wallabot)

**Base URL (local):** `http://localhost:8004`

The Agentic Service is the AI subsystem of Wallabot. It provides two intelligent endpoints
that assist sellers when creating a product listing: automatic category classification and
market-based price estimation.

All endpoints are **stateless** — each request is self-contained with no memory of prior
calls. Authentication is **not required** to call these endpoints.

---

## Health Check

### `GET /health`

```json
{ "status": "ok" }
```

---

## Category Suggestion

### `POST /wallabot/category`

Classifies a product into one of the caller-provided categories using a LangChain LCEL
chain backed by **GPT-4o-mini**.

The agent selects the most appropriate existing category. It only proposes a new category
name (setting `is_new_category: true`) when none of the provided options is a good fit.

On output validation failure the agent retries up to **3 times** with progressively
detailed correction feedback. On LLM provider failure it returns the closest available
category with `confidence: 0.0` rather than raising a 5xx error.

#### Request — `CategoryRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Product title as written by the seller |
| `description` | string | yes | Product description as written by the seller |
| `available_categories` | string[] (min 1) | yes | Non-empty list of category names the agent must choose from |

**Request example**

```json
{
  "title": "iPhone 13 Pro 128GB",
  "description": "Used for one year, minor screen scratches, battery at 87%.",
  "available_categories": ["Electronics", "Clothing & Accessories", "Home & Garden", "Other"]
}
```

#### Response 200 — `CategorySuggestion`

| Field | Type | Description |
|-------|------|-------------|
| `suggested_category` | string | Chosen category. Either an exact entry from `available_categories` or a new name |
| `confidence` | float [0.0, 1.0] | Calibrated confidence score. `0.0` indicates a provider-failure fallback |
| `is_new_category` | boolean | `true` when the agent proposed a category not in the input list |

**Response example**

```json
{
  "suggested_category": "Electronics",
  "confidence": 0.92,
  "is_new_category": false
}
```

#### Error responses

| Status | Error | Meaning |
|--------|-------|---------|
| 422 | Validation error | `available_categories` is empty, or required fields missing |
| 500 | `agent_validation_failure` | LLM produced unparseable output after 3 retries |

**500 example**

```json
{
  "detail": {
    "error": "agent_validation_failure",
    "message": "The request could not be processed due to an internal validation failure."
  }
}
```

---

## Price Recommendation

### `POST /wallabot/price`

Estimates a fair second-hand selling price in EUR for the described product.

The agent first queries **Tavily** for live market listings, then passes those results to
**GPT-4o-mini** to produce a structured price range adjusted for the declared condition.

When Tavily returns no results the endpoint still returns **HTTP 200** with
`data_source: "fallback: no market data found"` and a conservative LLM-based estimate.
On LLM provider failure a hardcoded condition-scaled fallback is returned — the seller
always receives a usable response.

#### Request — `PriceRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Product title as written by the seller |
| `description` | string | yes | Product description |
| `condition` | enum | yes | Physical condition: `New`, `Like New`, `Good`, `Fair`, or `Poor` |

**Condition influence on price**

Condition is the primary adjustment factor. `Poor` condition can reduce the estimated
price by up to **75%** compared to `New`.

| Condition | Approximate multiplier |
|-----------|----------------------|
| `New` | 1.00 (baseline) |
| `Like New` | ~0.85 |
| `Good` | ~0.70 |
| `Fair` | ~0.50 |
| `Poor` | ~0.25 |

**Request example**

```json
{
  "title": "iPhone 13 Pro 128GB",
  "description": "Used for one year, minor screen scratches, battery at 87%.",
  "condition": "Good"
}
```

#### Response 200 — `PriceRecommendation`

| Field | Type | Description |
|-------|------|-------------|
| `recommended_price` | float (> 0) | Single best-estimate selling price in EUR |
| `price_range_min` | float (> 0) | Lower bound of the estimated range in EUR |
| `price_range_max` | float (> 0) | Upper bound; always > `price_range_min` |
| `data_source` | string | Source of market data used. `"fallback: no market data found"` when Tavily had no results |

**Response example**

```json
{
  "recommended_price": 420.0,
  "price_range_min": 350.0,
  "price_range_max": 500.0,
  "data_source": "Tavily search: iPhone 13 Pro 128GB Good second-hand price EUR"
}
```

#### Error responses

| Status | Error | Meaning |
|--------|-------|---------|
| 422 | Validation error | Required fields missing or invalid |
| 500 | `agent_validation_failure` | LLM produced unparseable output after 3 retries |
| 502 | `agent_provider_failure` | Upstream LLM or Tavily provider was unreachable |

**502 example**

```json
{
  "detail": {
    "error": "agent_provider_failure",
    "message": "Wallabot could not reach the pricing provider."
  }
}
```

---

## LangSmith Tracing

When the environment variable `LANGCHAIN_TRACING_V2=true` (or `LANGSMITH_TRACING=true`)
is set, every LangChain chain invocation is automatically recorded in LangSmith under
the configured project name. This enables monitoring, debugging, and latency analysis
without any code changes.

Configure with:

| Variable | Description |
|----------|-------------|
| `LANGCHAIN_TRACING_V2` | Set to `true` to enable tracing |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | Project name in LangSmith (default: `wallabot`) |
