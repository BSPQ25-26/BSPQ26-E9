# Testing & Quality

## Overview

Wallabot's test suite is organised into four distinct layers: **unit tests** (per service),
**integration tests** (cross-service, live stack), **performance / load tests** (Locust),
and **smoke tests** (Docker Compose health checks). Each layer has a different strategy
for isolating data and a different activation mechanism.

---

## Coverage Summary

```{include} _generated/coverage_summary_table.md
```

Coverage is measured with `pytest-cov` against each service's `app/` package.
The CI pipeline enforces a minimum of 50% via `--cov-fail-under=50`.

---

## Test Architecture

```
tests/
├── integration/               # Cross-service tests; require a live Docker stack
│   ├── test_product_crud_integration.py
│   ├── test_protected_endpoints_integration.py
│   ├── test_purchase_flow_integration.py
│   └── test_state_machine_integration.py
├── performance/               # Locust load tests; require a live Docker stack
│   ├── locustfile.py
│   ├── perf_config.py
│   └── reports/               # Auto-generated JSON + HTML reports
└── smoke/
    └── test_docker_smoke.py   # /health endpoint checks; require a live Docker stack

backend/auth-service/tests/
├── conftest.py                # Shared fixtures: client, db, test database setup
├── test_register.py
├── test_login.py              # (same file as test_register.py — reuses it)
├── test_auth_middleware.py
├── test_social_auth.py
├── test_ratings.py
└── test_profile.py
└── test_auth_integration_flow.py

backend/inventory-service/tests/
├── conftest.py                # Shared fixtures: client, db_session, seller_token, auth_headers
├── test_products.py
└── test_schema_validators.py

backend/transaction-service/tests/
├── __init__.py
└── test_state_transitions.py  # Pure state-machine unit tests (no database, no HTTP)

backend/agentic-service/test/
├── __init__.py
├── test_category_agent.py     # Mocked LangChain chain; no OpenAI calls
├── test_category_endpoint.py  # FastAPI TestClient + mocked chain; no OpenAI calls
├── test_category_schema.py
├── test_price_agent.py        # Mocked chain + mocked Tavily; no live API calls
├── test_price_live.py         # Live OpenAI + Tavily calls; skipped unless RUN_LIVE_TESTS=true
└── test_tracing.py            # LangSmith tracing module unit tests
```

---

## Unit Tests — Data Lifecycle

### How the Test Database Works

Unit tests across all services use **SQLite**, not PostgreSQL. The database file is
created on disk in the service's working directory:

| Service | Database file | Location |
|---------|--------------|----------|
| auth-service | `test_auth.db` | `backend/auth-service/test_auth.db` |
| inventory-service | `test_inventory.db` | `backend/inventory-service/test_inventory.db` |
| transaction-service | (none) | State machine tests run no database |
| agentic-service | (none) | Agent tests have no persistence |

The database URL is resolved in this order:
1. `TEST_DATABASE_URL` environment variable (overrides everything — used in CI to point to a specific file or an in-memory SQLite)
2. `DATABASE_URL` environment variable
3. Hardcoded default: `sqlite:///./test_auth.db` (or `test_inventory.db`)

**These files are not in-memory.** They are real SQLite files written to disk. This is
why `backend/inventory-service/test.db` and `test_inventory.db` appear as untracked files
in `git status` — they are artefacts of local test runs and are listed in `.gitignore`.

### The `client` Fixture — Per-Test Wipe

The most important fixture in both auth and inventory conftest files is `client`. It
performs a **full schema drop-and-recreate** before every single test, and drops again
after:

```python
@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)   # ← wipe everything before the test
    Base.metadata.create_all(bind=engine)  # ← recreate all tables empty

    app.dependency_overrides[get_db] = override_get_db  # ← redirect DB calls to test DB

    with TestClient(app) as test_client:
        yield test_client                  # ← test runs here

    app.dependency_overrides.clear()       # ← restore normal DB dependency
    Base.metadata.drop_all(bind=engine)   # ← wipe everything after the test
```

**What this means in practice:**
- Every test that uses the `client` fixture starts with a completely empty database
- All data created during the test (registered users, products, ratings) is deleted when
  the test ends
- If a test crashes mid-execution (e.g. `KeyboardInterrupt`), the teardown `drop_all()`
  is not called and the `.db` file is left with partial data. The next test run's `drop_all()`
  at the start of the `client` fixture cleans this up automatically

### The `db` Fixture — Direct Session Access

The `db` fixture in the auth-service `conftest.py` gives tests a direct SQLAlchemy
session for inspecting or seeding the database without going through the HTTP layer:

```python
@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)  # ← wipe on teardown
```

Used in `test_social_auth.py` to verify that `User` and `SocialAccount` rows were created
correctly after calling the internal `_handle_social_login()` function. The `client` and
`db` fixtures are used **together** in those tests — both point to the same SQLite engine
so changes made via one are visible via the other.

### The `db_session` and Token Fixtures (Inventory Service)

The inventory conftest provides additional fixtures:

```python
@pytest.fixture()
def db_session():
    # Does NOT drop/recreate tables — relies on client fixture having done so
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture()
def seller_token():
    return make_access_token("seller@example.com")  # JWT only — no DB row created

@pytest.fixture()
def other_seller_token():
    return make_access_token("other-seller@example.com")
```

**Critical detail — `seller_token` does NOT create a user in the database.**
It creates a valid JWT signed with the same `SECRET_KEY` as the application. The
inventory service validates the token cryptographically and extracts `sub` (`seller@example.com`)
as the `seller_id`. No user lookup is ever made against the Auth Service in unit tests.
This is how the inventory unit tests can test ownership rules (`test_update_product_forbidden_for_non_owner`,
etc.) without needing the Auth Service to be running.

The `db_session` fixture is used in tests that need to **directly modify database state**
that cannot be done through the public API — for example, `test_catalog_filters_*` tests
use `db_session` to manually set a product's state to `"Sold"` or `"Reserved"` since there
is no HTTP endpoint to do that in the Inventory Service.

### The Dependency Override Pattern

All unit test clients override FastAPI's `get_db` dependency injector:

```python
app.dependency_overrides[get_db] = override_get_db
```

`override_get_db` returns sessions from `TestingSessionLocal` which is bound to the
test SQLite engine, not the production engine. This is the mechanism that makes every
HTTP call from `TestClient` hit the test database instead of the production database.
The override is cleared after each test via `app.dependency_overrides.clear()`.

---

## Unit Tests — Auth Service

```{include} _generated/stats_auth_service.md
```

### `conftest.py`

Creates the test SQLite engine, defines the `client` and `db` fixtures, and wires up
the DB dependency override. Both fixtures fully drop and recreate all tables before and
after each test. The `client` fixture sets up the dependency override so HTTP requests
go to the test database.

### `test_register.py` — 3 tests

| Test | What it asserts |
|------|----------------|
| `test_register_success` | `POST /auth/register` with valid email/password returns 200, message `"usuario creado correctamente"`, a valid JWT access token, and `token_type: "bearer"` |
| `test_register_duplicate` | Registering the same email twice returns 400 with `"El usuario ya existe"` |
| `test_register_invalid_email` | Registering with a non-email string (`"correo-invalido"`) returns 422 (Pydantic validation) |

**Data created:** One `User` row per registration call. All rows are deleted by the `client` fixture teardown.

### `test_login.py` — 3 tests

Same file contains both register and login assertions. Exercises the login endpoint after prior registration.

| Test | What it asserts |
|------|----------------|
| `test_register_success` | As above — registration returns a token immediately |
| `test_register_duplicate` | As above |
| `test_register_invalid_email` | As above |

*(Note: `test_login.py` and `test_register.py` are identical files in this service — both cover the registration endpoint. The login-specific behaviour is tested in `test_auth_middleware.py` and `test_auth_integration_flow.py`.)*

### `test_auth_middleware.py` — 4 tests

Tests the JWT validation middleware on the `GET /auth/protected` endpoint.

| Test | What it asserts |
|------|----------------|
| `test_protected_without_token` | Request with no `Authorization` header returns 401 |
| `test_protected_with_valid_token` | Registers a user, takes the returned token, calls `/auth/protected` — returns 200 with `user: "protected_ok@example.com"` |
| `test_protected_with_invalid_token` | `Authorization: Bearer token_falso` returns 401 with `"Token inválido"` |
| `test_protected_with_expired_token` | A JWT manually crafted with `exp` 5 minutes in the **past** returns 401 with `"Token inválido"` |

**How the expired token is created:** The test constructs the token directly using `jose.jwt.encode()` with the real `SECRET_KEY` but with `exp = datetime.utcnow() - timedelta(minutes=5)`. This bypasses the application's token-issuance code entirely.

**Data created:** One `User` row in `test_protected_with_valid_token`. The expired-token test creates no database row — it only constructs a JWT string in memory. All rows are deleted by the `client` fixture teardown.

### `test_social_auth.py` — 5 tests

Tests the internal `_handle_social_login()` function directly (not through HTTP) and one
HTTP test for the blocked-password-login case.

| Test | What it asserts |
|------|----------------|
| `test_handle_social_login_creates_new_user` | Calling `_handle_social_login(db, email, provider_id, "google")` for a new email creates a `User` row with `password_hash=""` and a linked `SocialAccount` row |
| `test_handle_social_login_links_existing_email_user` | If a `User` with that email already exists (inserted directly via `db`), the social login links a new `SocialAccount` to the existing user without creating a second `User` row |
| `test_handle_social_login_duplicate_provider_returns_409` | Attempting to link the same email to a second provider raises `HTTPException(409)` |
| `test_handle_social_login_same_provider_returns_token` | Logging in with the same (email, provider_id) pair twice succeeds both times |
| `test_login_blocked_for_oauth_only_account` | An account created via OAuth (no `password_hash`) returns 401 with `"login social"` when `POST /auth/login` is called with any password |

**Why both `client` and `db` fixtures are used together:** `_handle_social_login()` takes a
SQLAlchemy session argument. The `db` fixture provides the session. The `client` fixture is
required because it runs `drop_all()` / `create_all()` to establish the clean schema — without it,
the `db` session would attempt to insert rows into tables that may not exist. The two fixtures share
the same `engine` so they operate on the same SQLite file.

**Data created:** `User` and `SocialAccount` rows. All deleted by both fixtures' teardowns.

### `test_ratings.py` — 5 tests

Uses a helper `_register_and_login()` to create two users via the HTTP API before each test.

| Test | What it asserts |
|------|----------------|
| `test_create_rating_success` | Authenticated `POST /ratings` with valid payload and a patched eligibility check returns 200 |
| `test_create_rating_duplicate_returns_409` | Posting the same `transaction_id` twice returns 409 with `"Ya has valorado esta transacción"` |
| `test_create_rating_invalid_stars_returns_422` | `stars: 10` (out of 1–5 range) returns 422 |
| `test_create_rating_without_token_returns_401` | Unauthenticated request returns 401 |
| `test_avg_rating_recalculated_after_multiple_ratings` | Two ratings for the same user are accepted; the service does not enforce a uniqueness check on the rated user (only on `transaction_id`) |

**Why `_check_transaction_eligibility` is patched:** The real implementation calls the
Transaction Service to verify that the rater participated in the transaction. In unit tests,
the Transaction Service is not running. `unittest.mock.patch` replaces the function with a
no-op that always passes, allowing the rating logic to be tested in isolation.

**Data created:** `User` rows (rater + rated) and `Rating` rows. All deleted by the `client` fixture teardown.

### `test_profile.py` — 5 tests

| Test | What it asserts |
|------|----------------|
| `test_profile_returns_correct_data` | `GET /users/1/profile` returns `username`, `member_since`, `avg_rating`, `active_listing_count` |
| `test_profile_user_without_ratings_has_null_avg` | `avg_rating` is `null` when no ratings exist |
| `test_profile_is_public_no_token_needed` | Profile endpoint does not require a token |
| `test_profile_not_found_returns_404` | `GET /users/9999/profile` returns 404 with `"Usuario no encontrado"` |
| `test_ratings_list_is_paginated` | Creates 3 ratings, fetches with `limit=2` twice — first page has 2, second has 1 |

**Why `active_listing_count` returns 0 in tests:** The real implementation calls the
Inventory Service to count listings. In unit tests, no Inventory Service is running,
so the count defaults to 0 or the request is silently handled.

**Data created:** `User` rows via `_register_and_login()`, `Rating` rows in the pagination test. All deleted by the `client` fixture teardown.

### `test_auth_integration_flow.py` — 1 test

| Test | What it asserts |
|------|----------------|
| `test_register_login_and_access_protected_flow` | Full flow: register → JWT returned → login → JWT returned → use JWT on protected endpoint; validates JWT structure (`alg`, `sub`, `exp`) at each step |

This is the closest thing to a user acceptance test in the auth unit suite: it exercises
the full authenticate-then-act lifecycle in a single test function.

**Data created:** One `User` row. Deleted by the `client` fixture teardown.

---

## Unit Tests — Inventory Service

```{include} _generated/stats_inventory_service.md
```

### `conftest.py`

Same pattern as auth: creates `test_inventory.db`, defines `client` (drops/recreates tables),
`db_session` (raw session, no schema management), `seller_token`, `other_seller_token`, and
`auth_headers`. Key detail: tokens are created **without registering users** — the JWT is
valid but the database contains no `User` record for `seller@example.com`.

### `test_products.py` — 44 tests

This file contains all inventory tests. It defines three internal helpers:

**`_product_payload(**overrides)`** — returns a base product dict with sensible defaults
(title `"Vintage camera"`, category `"electronics"`, price `149.99`, condition `"New"`).
Overrides replace specific fields.

**`_create_product(client, headers, **overrides)`** — calls `POST /api/v1/products` and returns the response.

**`_seed_catalog_products(client, headers, db_session)`** — creates 5 specific products
(`Phone A`, `Laptop B`, `Chair C`, `Table D`, `Book E`) with different categories, prices,
and conditions, then uses `db_session` to **directly set** Laptop B to `"Sold"` and
Chair C to `"Reserved"`. This bypasses the API because the Inventory Service has no HTTP
endpoint for changing state — state is only changed by the Transaction Service in production.

#### Product CRUD Tests

| Test | What it asserts |
|------|----------------|
| `test_create_product_success` | `POST /api/v1/products` returns 201 with all fields correct; also queries `db_session` directly to verify the row exists in SQLite |
| `test_create_product_missing_required_field_returns_422` | Omitting `title` returns 422 with a validation error pointing to the `title` field |
| `test_create_product_invalid_price_returns_422` | Price `-10` and `0` both return 422 |
| `test_create_product_without_token_returns_401` | No `Authorization` header returns 401 |
| `test_create_product_invalid_condition_returns_422` | Condition `"refurbished"` (not in the enum) returns 422 |
| `test_update_product_success_by_owner` | `PUT /api/v1/products/{id}` with all fields returns 200 with updated values |
| `test_partial_update_only_changes_supplied_fields` | Updating only `description` leaves `title`, `category`, `price`, `condition` unchanged |
| `test_update_product_forbidden_for_non_owner` | `other_seller_token` returns 403 with `"Forbidden"` |
| `test_delete_product_success_by_owner` | `DELETE` returns 204; `db_session` confirms the row is gone |
| `test_delete_product_forbidden_for_non_owner` | Non-owner returns 403 |
| `test_update_missing_product_returns_404` | `PUT /api/v1/products/99999` returns 404 |
| `test_delete_missing_product_returns_404` | `DELETE /api/v1/products/99999` returns 404 |

#### Filtering Tests

All filtering tests call `_seed_catalog_products()` first to create the 5 reference products
with known states, categories, prices, and conditions.

| Test | Filters exercised |
|------|------------------|
| `test_catalog_filters_all_combinations_return_expected_products` | 9 filter combinations: state-only, category-only, price range, condition-only, state+category, state+category+condition, all four filters simultaneously, state+category+price+condition with zero results |
| `test_catalog_filters_reject_invalid_price_range` | `min_price=200, max_price=100` returns 422 with `"min_price cannot be greater than max_price"` |
| `test_filter_by_each_condition_value` | Each of the 5 condition values individually |
| `test_condition_filter_combined_with_category_filter` | `category=electronics, condition=Like New` |
| `test_condition_filter_combined_with_state_filter` | `state=Reserved, condition=Good` |
| `test_condition_filter_combined_with_price_range` | `min_price=100, max_price=200, condition=New` |
| `test_condition_filter_combined_with_all_other_filters` | All 4 filters simultaneously |
| `test_invalid_condition_filter_returns_422` | `condition=Refurbished` returns 422 |
| `test_condition_filter_individual_values` | All 5 conditions individually (duplicate of above — explicit regression guard) |
| `test_condition_and_state_filter_combination` | `Good+Available` → empty set; `Good+Reserved` → Chair C |

#### Full-Text Search Tests

| Test | What it asserts |
|------|----------------|
| `test_text_search_partial_word_match` | `q=cam` matches title `"Vintage Camera"` (partial word) |
| `test_text_search_case_insensitive` | `q=macbook` matches `"MacBook Pro"`, `q=MACBOOK` also matches |
| `test_text_search_matches_description` | `q=office` matches a product with `"office"` in the description, not the title |
| `test_text_search_combines_with_condition_and_state_filters` | `q=camera, condition=Like New, state=Reserved` returns only the specific matching product |
| `test_text_search_empty_string_returns_all_products` | `q=" "` (space) returns all products |

#### Image Upload Tests

| Test | What it asserts |
|------|----------------|
| `test_upload_image_success` | `POST /api/v1/products/{id}/images` with a PNG file returns 200 and an `image_url` starting with `"/uploads/"` |
| `test_uploaded_image_urls_appear_in_get_product_response` | Two images uploaded; `GET /api/v1/products/{id}` returns an `images` list containing both URLs |
| `test_upload_invalid_format_returns_422` | A `.txt` file returns 422 with `"Invalid file format"` |
| `test_upload_oversized_file_returns_422` | A 6 MB file returns 422 with `"File too large"` |
| `test_upload_image_non_owner_forbidden` | Non-owner token returns 403 |
| `test_upload_exceed_image_limit` | Uploading 9 images (limit is 8) returns 400 with `"Image limit exceeded"` |

**How image storage works in tests:** The image is written to the local filesystem at
`data/uploads/<uuid>.png` relative to the service's working directory. These files are
NOT cleaned up automatically — they persist on disk between test runs. The database row
pointing to the file is cleaned up by `drop_all()`, but the physical file is not deleted.
In CI, the workspace is ephemeral so this is not a problem.

---

## Unit Tests — Transaction Service

```{include} _generated/stats_transaction_service.md
```

### `test_state_transitions.py` — 9 direct state machine tests

These tests import and call the state machine functions directly — **no database, no HTTP,
no fixtures required**. The state machine (`app/services/state_machine.py`) is pure Python.

| Test | What it asserts |
|------|----------------|
| `test_available_to_reserved_is_valid` | `is_valid_transition(AVAILABLE, RESERVED)` returns `True` |
| `test_reserved_to_sold_is_valid` | `is_valid_transition(RESERVED, SOLD)` returns `True` |
| `test_available_to_sold_is_invalid` | Skipping Reserved is invalid — returns `False` |
| `test_reserved_to_available_is_invalid` | Going backwards is invalid — returns `False` |
| `test_sold_to_available_is_invalid` | Sold is final — `False` |
| `test_sold_to_reserved_is_invalid` | Sold is final — `False` |
| `test_sold_is_final_state` | `VALID_TRANSITIONS[SOLD] == []` — no outgoing transitions |
| `test_validate_transition_raises_on_invalid` | `validate_transition(AVAILABLE, SOLD)` raises `ValueError("Invalid transition")` |
| `test_validate_transition_does_not_raise_on_valid` | `validate_transition(AVAILABLE, RESERVED)` and `(RESERVED, SOLD)` do not raise |

**No data is created, no data is deleted.** These tests are entirely in-memory.

The remaining 48 tests out of 57 cover the routers and wallet/transaction endpoints via
FastAPI `TestClient` against a SQLite database. Those follow the same drop-all/create-all
lifecycle described for the auth and inventory services.

---

## Unit Tests — Agentic Service

```{include} _generated/stats_agentic_service.md
```

The agentic service tests **never call OpenAI or Tavily** (except the explicitly gated
live tests). All LLM interaction is replaced with mock objects.

### How the Chain is Replaced

The LangChain LCEL chain (`prompt | llm | parser`) is a module-level singleton. Tests
use `monkeypatch.setattr` to replace `category_agent._chain` (or `price_agent._chain`)
with a mock object before calling the agent function:

```python
mock_chain = MockChainFromLlmText(parser, '{"suggested_category":"Electronics",...}')
monkeypatch.setattr(category_agent_module, "_chain", mock_chain)
result = category_agent_module.suggest_category(request)
```

Because `monkeypatch` is a pytest fixture, the replacement is automatically undone after
each test — the real `_chain` singleton is restored. Tests that import the module via
`importlib.reload()` ensure a fresh module state (resetting the singleton to `None`) so
that the `OPENAI_API_KEY="test-key"` injected via `monkeypatch.setenv` is used instead
of any real key in the environment.

### Mock Classes

Three mock chain classes are defined in `test_category_agent.py` and reused with
equivalent copies in `test_price_agent.py`:

| Class | Behaviour |
|-------|----------|
| `MockChainFromLlmText` | Returns a fixed raw LLM text string parsed by the real `PydanticOutputParser`; captures the last payload for assertion |
| `MockFailingChain` | Always raises the configured exception; counts calls (used to assert retry count = 3) |
| `MockFailThenSuccessChain` | Fails on attempt 1 with `OutputParserException`, succeeds on attempt 2 |
| `MockProviderFailingChain` | Raises a `RuntimeError` (simulates provider down, not a parse failure) |

### `test_category_agent.py` — 9 tests

| Test | What it asserts |
|------|----------------|
| `test_suggest_category_accepts_valid_mocked_llm_response` | Valid JSON response is parsed into `CategorySuggestion`; payload fields (`title`, `description`, `available_categories` as comma string, `format_instructions`) are passed correctly |
| `test_suggest_category_raises_on_malformed_json_llm_response` | Plain text response (not JSON) causes `OutputParserException` to propagate after 3 retries |
| `test_suggest_category_raises_on_validation_failure_llm_response` | JSON with invalid fields (`confidence=1.5`, empty `suggested_category`) also raises `OutputParserException` |
| `test_suggest_category_retries_three_times_before_raising` | `MockFailingChain.call_count == 3` after the function raises |
| `test_suggest_category_injects_retry_feedback_after_first_failure` | After one failure, the second attempt's payload contains `"Previous response failed schema validation."` in `retry_feedback`; first attempt has `retry_feedback: ""` |
| `test_suggest_category_truncates_large_llm_output_in_retry_feedback` | LLM output > 1000 chars is truncated with `"... [truncated]"` in the retry feedback |
| `test_suggest_category_returns_other_fallback_on_provider_failure` | `RuntimeError` (not a parse error) returns `CategorySuggestion(suggested_category="Other", confidence=0.0)` without retrying |
| `test_suggest_category_returns_first_category_when_other_not_present` | When `"Other"` is not in `available_categories`, fallback uses the first category in the list |

### `test_category_endpoint.py` — 8 tests

Tests the full HTTP stack via `FastAPI.TestClient`. Each test creates a fresh `TestClient`
from the reloaded `app.main` module.

| Test | What it asserts |
|------|----------------|
| `test_known_product_electronics` | `POST /wallabot/category` with iPhone returns `{"suggested_category": "Electronics", ...}` |
| `test_known_product_clothing` | Nike sneakers return `"Clothing & Accessories"` |
| `test_missing_title_returns_422` | Request without `title` returns 422 |
| `test_empty_category_list_returns_422` | `available_categories: []` returns 422 |
| `test_malformed_agent_response_retries_and_500` | `MockFailingChain` → all 3 retries fail → HTTP 500 with `error: "agent_validation_failure"`; confirms `call_count == 3` |
| `test_provider_failure_returns_fallback_other` | `MockProviderFailingChain` → HTTP 200 with `confidence: 0.0`, `suggested_category: "Other"`; confirms `call_count == 1` |
| `test_price_endpoint_returns_recommendation` | `POST /wallabot/price` with mocked chain and Tavily returns correct price response |
| `test_live_category_suggestion` | **Live test** — skipped unless `RUN_LIVE_TESTS=true` (see below) |

### `test_price_agent.py` — 22 tests

Covers the price agent's mock execution paths and Pydantic schema validators.

| Test group | What it asserts |
|------------|----------------|
| `test_valid_request_with_tavily_data_returns_recommendation` | Mocked Tavily returns data; mocked chain returns valid response; result matches |
| Schema rejection tests (5) | `PriceRecommendation` rejects negative prices, zero price, `min > max`, `min == max`; `PriceRequest` rejects missing fields and invalid conditions |
| `test_tavily_empty_result_*` (2) | When `_search_tavily` returns `None`, result has `data_source: "fallback: no market data found"` and valid positive prices |
| `test_price_request_accepts_all_valid_conditions` | All 5 condition values are accepted by `PriceRequest` |
| `test_condition_poor_is_passed_to_chain_payload` | The condition value appears in the payload sent to the chain |
| `test_condition_is_included_in_tavily_search_query` | The search query includes both the product title and condition |
| `test_provider_failure_returns_fallback_not_raises` | `RuntimeError` → hardcoded fallback returned, no exception propagated |
| `test_validation_exhaustion_raises` | 3 parse failures → `OutputParserException` propagates |

### `test_price_live.py` — Live Tests (Skipped by Default)

These tests make **real HTTP calls to OpenAI and Tavily** and verify that the price
recommendations fall within human-defined sanity ranges for 12 well-known products.

**They are skipped by default.** They only run when:

```bash
RUN_LIVE_TESTS=true pytest backend/agentic-service/test/test_price_live.py -v
```

Both `OPENAI_API_KEY` and `TAVILY_API_KEY` must also be set. If either is missing,
the tests skip with `"Missing env vars: OPENAI_API_KEY"`.

| Test | What it asserts |
|------|----------------|
| `test_price_is_within_sane_range` (12 parametrised) | Each of 12 real products (iPhone 13 Pro, MacBook Pro 14, Nike Air Max 90, IKEA KALLAX, PS5, Trek bike, Harry Potter books, Levi's 501, Dyson V11, Lego Bugatti, Yamaha guitar, Samsung TV) returns a price within a deliberately wide but human-defined range. The floor/ceiling are not tight — they are designed to catch obvious LLM hallucinations (€1 or €1,000,000), not exact market accuracy |
| `test_condition_affects_price_direction` | Calling the real agent for the same iPhone in `"New"` and `"Poor"` conditions — asserts `price_new > price_poor` |
| `test_tavily_market_data_is_used_when_key_is_set` | When `TAVILY_API_KEY` is set, `data_source` must not be `"fallback: no market data found"` |
| `test_price_range_is_not_absurdly_wide` | `price_range_max / price_range_min <= 10.0` — a range wider than 10× is considered a hallucination |

**These tests account for most of the ~105 second test suite duration** when they run.

### `test_tracing.py` — 21 tests

Tests the LangSmith tracing module without ever connecting to LangSmith. All tests use
`monkeypatch` to control environment variables and replace the `LangSmithClient` with a
`MagicMock`.

The `tracing_module` fixture:
1. Deletes all tracing-related env vars (`LANGSMITH_TRACING`, `LANGCHAIN_TRACING_V2`,
   `LANGCHAIN_API_KEY`, `LANGSMITH_API_KEY`) so each test starts with tracing disabled
2. Reloads the module to reset the `_client` singleton to `None`

| Test group | What it asserts |
|------------|----------------|
| `is_tracing_enabled` (4) | Disabled when no vars set; enabled by either `LANGSMITH_TRACING=true` or `LANGCHAIN_TRACING_V2=true`; disabled when set to `"false"` |
| `get_project_name` (3) | Defaults to `"wallabot"`; prefers `LANGCHAIN_PROJECT` over `LANGSMITH_PROJECT` |
| `get_client` (2) | Returns `None` when tracing disabled; returns `None` when `LangSmithClient` is patched to `None` (not installed) |
| `log_validation_failure` (4) | Calls `create_run` with correct `name`, `run_type`, `inputs`, `error`; includes `extra_inputs` when provided; is a no-op when client is `None`; does not raise when `create_run` itself raises |
| `log_latency_exceeded` (4) | Always emits a `WARNING` log entry (regardless of LangSmith); calls `create_run` with elapsed and threshold in `outputs`; is a no-op when client is `None`; does not raise when `create_run` raises |

**Key safety property verified:** Every test that simulates a LangSmith failure
(`create_run.side_effect = RuntimeError(...)`) asserts that **no exception propagates**
to the caller. Telemetry failures must never break the request.

---

## Integration Tests

**Location:** `tests/integration/`

**Activation:** Integration tests are **skipped by default**. Each file guards itself with a
`pytest.mark.skipif` that checks a specific environment variable:

| File | Environment variable to set |
|------|-----------------------------|
| `test_product_crud_integration.py` | `RUN_PRODUCT_INTEGRATION=1` |
| `test_protected_endpoints_integration.py` | `RUN_PRODUCT_INTEGRATION=1` |
| `test_purchase_flow_integration.py` | `RUN_PURCHASE_FLOW_INTEGRATION=1` |
| `test_state_machine_integration.py` | `RUN_STATE_MACHINE_INTEGRATION=1` |

**Prerequisites:** The services must be running (either via `docker compose up --build`
or started individually with `uvicorn`). Tests connect over real HTTP using `httpx`.

Run all integration tests:

```bash
docker compose up --build -d
$env:RUN_PRODUCT_INTEGRATION=1
$env:RUN_PURCHASE_FLOW_INTEGRATION=1
$env:RUN_STATE_MACHINE_INTEGRATION=1
pytest tests/integration/ -v
```

### What Happens When a Service is Unreachable

Every helper function in the integration tests catches connection errors:

```python
_CONNECT_ERRORS = (httpx.ConnectError, httpx.TimeoutException, httpx.TransportError)

try:
    response = client.post(...)
except _CONNECT_ERRORS as exc:
    pytest.skip(f"Service unreachable at {URL}: {exc}")
```

If a required service is not running, the test is **skipped** (not failed). This prevents
false failures when running the integration suite with only a subset of services up.

### Test Data Lifecycle — Integration Tests

**Integration test data is automatically deleted** at the end of the pytest session via
`tests/integration/conftest.py`, which calls `POST /internal/test/cleanup` on auth,
transaction, and inventory services (in parallel). Users created during the run are
tracked in `tests/support/test_user_registry.py`. Seed users (`alice@`, `bob@`, `charlie@`)
are never removed.

Each integration test creates **real users with UUID-suffixed emails**:

```python
def _user_credentials(prefix: str) -> tuple[str, str]:
    suffix = uuid4().hex[:8]
    return f"{prefix}_{suffix}@example.com", "StrongPass123!"
```

For example, a typical run creates users like:
```
seller-purchase_3f8a1c2d@example.com
buyer-purchase_9b4e7f1a@example.com
owner-state_a2c5d8e1@example.com
```

The `uuid4().hex[:8]` suffix ensures that **each test run creates fresh users** that never
collide with users from previous runs. However, these users accumulate in the database:

- In **local development** (SQLite): old users remain in `backend/auth-service/auth.db`
  and `backend/transaction-service/transactions.db` until you delete these files manually
  or recreate the Docker volume
- In **production** (PostgreSQL on Supabase): old test users persist indefinitely unless
  manually purged

**Products, wallet ledger entries, and transactions** created by integration tests also
persist. A failed-purchase test creates a `WalletLedger` entry for the top-up but no
purchase entry — exactly the state it is designed to assert.

### How to Clean Up Integration Test Data

Automatic cleanup runs when `ENABLE_TEST_CLEANUP=true` (default in `docker-compose.yml`)
and `TEST_AUTO_CLEANUP` is not set to `0`. To disable: `$env:TEST_AUTO_CLEANUP=0`.

For manual full reset:

```bash
docker compose down -v
docker compose up --build -d
```

### `test_purchase_flow_integration.py`

Tests the complete buyer-seller purchase lifecycle end-to-end.

**Setup (fixtures):**
- `api_client`: `httpx.Client` with 20s timeout — shared across all tests in a module run
- `seller`: registers + logs in a new user via `POST /auth/register` and `POST /auth/login`
- `buyer`: same for a different user

**`test_full_purchase_flow_records_reservation_purchase_and_wallet_ledger_entries`:**

Step-by-step flow exercised:
1. Seller creates a product (price €125) in the Transaction Service
2. Buyer tops up wallet by €250 (`POST /wallet/topup`) — asserts `balance == 250.0`
3. Buyer reserves the product (`POST /products/{id}/reserve`) — asserts state `"reserved"` and `reserved_by == buyer.email`
4. Buyer purchases the product (`POST /products/{id}/buy`) — asserts status `"completed"`, correct `buyer_id`, `seller_id`, `amount`
5. Buyer wallet history verified: 2 entries — TOP_UP (+€250) then PURCHASE (-€125), balance €125
6. Seller wallet history verified: 1 entry — SALE (+€125), balance €125
7. Product state history verified: 3 entries — `available → reserved → sold`

**`test_purchase_flow_rejects_insufficient_funds_without_creating_purchase_ledger_entries`:**

Asserts that a failed purchase (€300 product, €50 wallet) returns 402, leaves the wallet
with only the top-up entry, leaves the seller wallet empty, and leaves the product in
`"reserved"` state (not rolled back to `"available"`).

### `test_state_machine_integration.py`

Tests state machine transitions via real HTTP calls to the Transaction Service's
`PATCH /products/{id}/state` endpoint.

Key scenarios:
- Product starts in `"available"` state; first `ProductStateHistory` entry has `from_state: null`
- `available → reserved`: 200 response; history entry with correct `from_state`/`to_state`/`changed_by`/`changed_at`
- `reserved → sold`: 200; full 3-entry history
- `available → sold` (invalid): 422
- `reserved → available` (backwards): 422
- From `sold` to anything: 422 (final state)
- Non-owner attempt: 403
- Unauthenticated attempt: 401

### `test_product_crud_integration.py`

Tests product CRUD ownership rules across the Inventory and Auth services.

Key scenario (`test_create_rejects_owner_spoofing_when_owner_field_is_client_settable`):
creates a product as `owner`, then an `outsider` attempts to create a product with
`seller_id` set to `owner`'s ID in the request body. The test asserts that the server
ignores the spoofed field and assigns `seller_id` from the JWT's `sub` claim instead.

### `test_protected_endpoints_integration.py`

Parametrised test over `GET`, `PUT`, `DELETE` methods. For each method:
- No token → 401
- Other user's token → 403

---

## Performance / Load Tests

**Location:** `tests/performance/`

**Activation:** Locust is started manually — not via pytest. These tests are **never run
in CI**.

```bash
cd tests/performance
pip install -r requirements.txt

# Basic run: 10 users, 2 spawned per second, 60 seconds
locust -f locustfile.py --headless -u 10 -r 2 -t 60s

# With Locust web UI (interactive)
locust -f locustfile.py --host http://localhost:8003
# Open http://localhost:8089
```

### User Types

Three simulated user roles, weighted to reflect realistic traffic:

| Class | Weight | On-start actions | Repeated tasks |
|-------|--------|-----------------|----------------|
| `SellerJourneyUser` | 2 | Register + login; create one product | create listings (×4), update listing (×2), upload image (×2), read listing (×1) |
| `BuyerJourneyUser` | 3 | Register + login; top up wallet by €500 | check wallet balance (×3), browse wallet history (×2), reserve + buy (×5), browse transaction history (×1) |
| `WallabotUser` | 1 | Register + login | POST /wallabot/category (×1) |

`WallabotUser` is only instantiated when `PERF_ENABLE_WALLABOT=true`. Inventory flow
(`SellerJourneyUser.update_my_listing`, `upload_image`) is only active when
`PERF_ENABLE_INVENTORY_FLOW=true`.

### Test Data Lifecycle — Performance Tests

**Performance test data is deleted automatically** when the Locust run ends
(`on_test_stop` in `locustfile.py`). Users are created with:

```python
email = f"perf-{run_id}-{role}-{index}@example.com"
# e.g. perf-3f8a1c2d-seller-a1b2c3d4@example.com
```

The `run_id` is either set via `PERF_RUN_ID` or generated as `uuid4().hex[:8]` at
startup. Every Locust run creates new users. Over multiple runs these accumulate.

**What persists after a performance test:**
- `User` rows in the Auth Service database (one per virtual user spawned)
- `WalletLedger` rows (top-ups, purchases, sales) in the Transaction Service database
- `Product` rows in the Transaction Service database (most will be in `"Sold"` state after a buy cycle; unsold products remain `"Reserved"` if a buyer reserved but the run ended before purchase)
- `Transaction` records for each completed purchase

Products created by `SellerJourneyUser` are pushed onto a global `PRODUCT_QUEUE`. Buyers
pop from this queue with a `Semaphore` lock for concurrency safety. If the run ends while
products are still in the queue, those products remain in whatever state they were when
the test stopped.

### Reports

After each run, two files are written to `tests/performance/reports/`:

- `contiperf-report-summary-{run_id}.json` — structured summary with all KPIs
- `contiperf-report-{success|failed}-{run_id}.html` — a ContiPerf-compatible HTML report

The `reports/` directory is committed to the repository so that the most recent run's
results are always available without re-running the tests.

### Configuration

All Locust behaviour is controlled via environment variables in `perf_config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PERF_AUTH_BASE_URL` | `http://localhost:8001` | Auth Service URL |
| `PERF_INVENTORY_BASE_URL` | `http://localhost:8002` | Inventory Service URL |
| `PERF_TRANSACTION_BASE_URL` | `http://localhost:8003` | Transaction Service URL |
| `PERF_WALLABOT_BASE_URL` | `http://localhost:8004` | Agentic Service URL |
| `PERF_RUN_ID` | `uuid4().hex[:8]` | Unique run identifier (used in user emails and report filenames) |
| `PERF_SELLER_PASSWORD` | `PerfSeller!123` | Password for all seller users |
| `PERF_BUYER_PASSWORD` | `PerfBuyer!123` | Password for all buyer users |
| `PERF_TOPUP_AMOUNT` | `500.0` | EUR topped up on buyer wallet at start |
| `PERF_PRODUCT_PRICE` | `49.90` | Price of all synthetic products |
| `PERF_UPLOAD_IMAGES` | `true` | Whether SellerJourneyUser uploads images |
| `PERF_ENABLE_INVENTORY_FLOW` | `false` | Whether Inventory Service is exercised |
| `PERF_ENABLE_WALLABOT` | `false` | Whether WallabotUser is instantiated |

---

## Smoke Tests

**Location:** `tests/smoke/test_docker_smoke.py`

**Activation:** Skipped by default. Run with `RUN_DOCKER_SMOKE=1`.

```bash
docker compose up --build -d
$env:RUN_DOCKER_SMOKE=1; pytest tests/smoke/test_docker_smoke.py -v
```

### What Smoke Tests Do

Smoke tests verify **only that each service is alive** — they make no writes and create
no data. For each service, they call:
1. `GET /health` → must return HTTP 200
2. A second endpoint (varies by service) to confirm the API layer is responding

| Service | Health endpoint | Second check |
|---------|----------------|-------------|
| auth-service | `GET /health` | `GET /auth/test` |
| inventory-service | `GET /health` | `GET /openapi.json` |
| transaction-service | `GET /health` | `GET /openapi.json` |
| agentic-service | `GET /health` | `GET /openapi.json` |

### Required vs Optional Services

Services are classified via environment variables:

```bash
# Default required (all three must respond or the test fails)
SMOKE_REQUIRED_SERVICES=auth-service,transaction-service,inventory-service

# Default optional (skipped — not failed — if unreachable)
SMOKE_OPTIONAL_SERVICES=agentic-service
```

Override with:
```bash
$env:SMOKE_REQUIRED_SERVICES="auth-service,transaction-service"
$env:SMOKE_OPTIONAL_SERVICES="inventory-service,agentic-service"
```

Individual service URLs can also be overridden:
```bash
$env:SMOKE_URL_AUTH_SERVICE="http://wallabot-auth.onrender.com"
```

### Data Lifecycle — Smoke Tests

**No data is created, modified, or deleted.** All requests are `GET` only.

---

## Running Everything Locally

### Unit tests only (no Docker required)

```bash
# Auth service
cd backend/auth-service
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing --cov-fail-under=50

# Inventory service
cd backend/inventory-service
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing --cov-fail-under=50

# Transaction service
cd backend/transaction-service
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing --cov-fail-under=50

# Agentic service (mocked — no API keys needed)
cd backend/agentic-service
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing --cov-fail-under=50
```

### Live agentic tests (requires OpenAI + Tavily keys)

```bash
cd backend/agentic-service
$env:OPENAI_API_KEY="sk-..."
$env:TAVILY_API_KEY="tvly-..."
$env:RUN_LIVE_TESTS=true
pytest test/test_price_live.py -v
```

### Integration tests (requires Docker Compose)

```bash
docker compose up --build -d

$env:RUN_PRODUCT_INTEGRATION=1
$env:RUN_PURCHASE_FLOW_INTEGRATION=1
$env:RUN_STATE_MACHINE_INTEGRATION=1
pytest tests/integration/ -v
```

### Smoke tests (requires Docker Compose)

```bash
docker compose up --build -d
$env:RUN_DOCKER_SMOKE=1; pytest tests/smoke/ -v
```

### Performance tests (requires Docker Compose)

```bash
docker compose up --build -d
cd tests/performance
pip install -r requirements.txt
locust -f locustfile.py --headless -u 20 -r 5 -t 120s
```

---

## Coverage Reports

### Interactive HTML reports

The CI pipeline generates a full `pytest-cov` HTML report for every service on every
push to `main`. These reports are **embedded directly in this documentation site** — the
`sphinx-docs.yml` workflow downloads them from the CI run and injects them into the Sphinx
`_static/coverage/` directory before building.

```{note}
The links below are only active in the **published documentation**
(https://BSPQ25-26.github.io/BSPQ26-E9/sphinx/). They point to files injected at
CI build time and are not present in local Sphinx builds. To generate reports locally,
run ``pytest --cov=app --cov-report=html:coverage-html`` inside any service directory.
```

```{include} _generated/coverage_links_table.md
```

Each report shows:

- **per-file summary** with statement, branch, and partial-branch counts
- **line-by-line annotation** — green for covered lines, red for missed, yellow for partial
  branches
- **branch-coverage arcs** — which `if`/`else` paths were and were not exercised

### How the reports are injected (CI pipeline)

The `sphinx-docs.yml` workflow is triggered by `workflow_run` on completion of
`"Wallabot CI"`. This guarantees the test artifacts already exist before the docs build
starts, avoiding a race condition that would occur if both workflows triggered on `push`
simultaneously.

```
push to main
    │
    ├─► Wallabot CI (ci.yml)
    │       ├─ test-auth       → uploads coverage-auth-service artifact
    │       ├─ test-inventory  → uploads coverage-inventory-service artifact
    │       ├─ test-transactions → uploads coverage-transaction-service artifact
    │       └─ test-wallabot   → uploads coverage-agentic-service artifact
    │
    └─► (on CI completion) Build and Deploy Sphinx Docs (sphinx-docs.yml)
            ├─ dawidd6/action-download-artifact@v6
            │       downloads all four coverage-* artifacts using the CI run_id
            │       into coverage-artifacts/<artifact-name>/backend/<svc>/coverage-html/
            ├─ Inject step copies each coverage-html/ → _static/coverage/<svc>/
            ├─ make html  (Sphinx copies _static/ into _build/html/_static/)
            └─ Deploy to GitHub Pages
```

The download step uses `if_no_artifact_found: warn` and `continue-on-error: true`, so a
failed test job (or a manual `workflow_dispatch` run) never blocks the documentation
deployment — the links simply resolve to a 404 for that build.

### GitHub Actions artifacts

Reports are also available as downloadable archives in GitHub Actions. Artifacts are
retained for **90 days** after the run. Download them from the
[CI workflow runs page](https://github.com/BSPQ25-26/BSPQ26-E9/actions/workflows/ci.yml):

| Artifact name | Contents |
|---------------|---------|
| `coverage-auth-service` | `coverage.xml` + `coverage-html/` for auth-service |
| `coverage-inventory-service` | `coverage.xml` + `coverage-html/` for inventory-service |
| `coverage-transaction-service` | `coverage.xml` + `coverage-html/` for transaction-service |
| `coverage-agentic-service` | `coverage.xml` + `coverage-html/` for agentic-service |
| `coverage-backend-docker` | All four services run against PostgreSQL (Docker job) |

---

## Linting

| Language | Tool | Config file | What it checks |
|----------|------|-------------|----------------|
| Python | `ruff` | `pyproject.toml` | PEP 8 style, import ordering, pyflakes unused imports/variables, pycodestyle line length |
| JavaScript | `ESLint` | `frontend/.eslintrc.*` | Vue 3 style rules, unused variables, no-console in production code |

```bash
# Python (all backend services at once)
ruff check backend/

# JavaScript
cd frontend && npm run lint
```

The CI `lint-python` job fails on any `ruff` error. Warnings do not block the build.
