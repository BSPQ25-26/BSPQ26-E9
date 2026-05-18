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
