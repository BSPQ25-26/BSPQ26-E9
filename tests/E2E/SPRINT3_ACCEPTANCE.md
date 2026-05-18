# Sprint 3 Acceptance Scenarios

These scenarios cover the Sprint 3 features on the running Wallabot Docker stack:
ratings, public profile, catalog filters/search, and Wallabot.

## 1. Ratings update the seller profile

Given a buyer and a seller exist, and the buyer has enough wallet balance to complete a purchase
When the buyer purchases a seller product and submits a 5-star rating for that transaction
Then the rating is stored successfully
And the seller public profile shows an updated average rating
And the seller ratings list contains the buyer review

## 2. Public profile is accessible without authentication

Given a known user id exists
When an anonymous client requests `/users/{id}/profile`
Then the API returns `200 OK`
And the response includes username, member date, average rating, and active listing count

## 3. Catalog filters narrow the visible products

Given several catalog products exist with different categories, conditions, and prices
When a buyer requests the catalog with category, condition, min_price, and max_price filters
Then only the matching products are returned
And the filter combination excludes non-matching items

## 4. Search matches title and description

Given the catalog contains products whose titles and descriptions use realistic marketplace wording
When a buyer searches with a keyword such as `camera`
Then products whose title or description contains that keyword are returned
And unrelated products are excluded

## 5. Wallabot suggests category and pricing guidance

Given a realistic product draft such as an iPhone listing
When Wallabot receives the title and description
Then the category endpoint returns a non-empty suggested category
And, when live pricing is enabled, the price endpoint returns a valid recommended price range

## How to run against Docker

Start the stack:

```bash
docker compose up --build -d auth-service inventory-service transaction-service agentic-service frontend
```

Wait for the health checks to turn green, then run the acceptance runner:

```bash
python tests/E2E/scenario_test.py
```

If you want Wallabot price recommendation to be exercised as a live call, set:

```bash
$env:RUN_WALLABOT_PRICE="1"
python tests/E2E/scenario_test.py
```

The script seeds realistic demo users and products, then prints the seller/buyer ids and frontend routes that you can inspect in the browser.

## Frontend review after seeding

Open the frontend at:

```text
http://localhost:5173/#/products
http://localhost:5173/#/products/create
```

Use the seeded user accounts printed by the script to log in, then verify the catalog filtering/search state and the Wallabot helpers in the product creation screen.

## Notes

- The acceptance runner uses the live Docker services at ports `8001` to `8004` by default.
- If your stack uses different host ports, set `AUTH_SERVICE_URL`, `INVENTORY_SERVICE_URL`, `TRANSACTION_SERVICE_URL`, `WALLABOT_SERVICE_URL`, and `FRONTEND_URL` before running the script.
- Wallabot category suggestion is always exercised; live price recommendation is optional because it depends on the external AI provider being configured.

## Sprint 3 Acceptance Results

The Docker stack was validated successfully with the acceptance runner.
profile_and_ratings passed: a seller and buyer were created, a transaction completed, and the seller profile/ratings flow worked.
catalog passed: products were created, filtered, searched, and combined filters returned the expected results.
wallabot passed for category suggestions; live price lookup was not enabled in the default run.
Frontend routes to review: http://localhost:5173/#/products and http://localhost:5173/#/products/create.

## Acceptance Review Checklist

| Criterion | Status | Verification | Evidence |
| --- | --- | --- | --- |
| Ratings update the seller profile | Met | Verified by the acceptance runner and auth-service rating/profile tests. | `tests/E2E/scenario_test.py` creates a completed transaction, posts a 5-star rating, then checks the seller profile and ratings list; `backend/auth-service/tests/test_ratings.py` covers rating creation and avg-rating recalculation; `backend/auth-service/tests/test_profile.py` verifies the public profile payload. |
| Public profile is accessible without authentication | Met | Verified by the public profile endpoint and unit tests. | `backend/auth-service/app/api/v1/user_router.py` exposes `GET /users/{user_id}/profile` without auth, and `backend/auth-service/tests/test_profile.py` confirms no token is required and the response includes `username`, `member_since`, `avg_rating`, and `active_listing_count`. |
| Catalog filters narrow the visible products | Met | Verified by the acceptance runner and inventory-service route logic. | `tests/E2E/scenario_test.py` creates mixed catalog items and asserts category, condition, min_price, and max_price filters return only the matching product; `backend/inventory-service/app/api/v1/product_router.py` applies those filters in the query. |
| Search matches title and description | Met | Verified by the acceptance runner and inventory-service route logic. | `tests/E2E/scenario_test.py` searches `q=camera` and expects only the matching product; `backend/inventory-service/app/api/v1/product_router.py` performs case-insensitive title/description matching with `ilike`. |
| Wallabot suggests category and pricing guidance | Partially met | Category suggestion is verified; pricing guidance is implemented but not exercised in the default acceptance run. | `tests/E2E/scenario_test.py` always checks `POST /wallabot/category`; the price request is only sent when `RUN_WALLABOT_PRICE=1`. `backend/agentic-service/app/api/wallabot_router.py` and `backend/agentic-service/app/schemas/price.py` define the price endpoint and response contract. |

## Gaps And Issues

1. Wallabot live pricing is not covered in the default acceptance run. The scenario runner gates `POST /wallabot/price` behind `RUN_WALLABOT_PRICE=1`, so the backlog item is only partially verified unless the external pricing provider is configured and the runner is re-executed with that flag enabled.

For the full prioritized post-project backlog, see [tests/E2E/SPRINT3_BACKLOG.md](tests/E2E/SPRINT3_BACKLOG.md).
