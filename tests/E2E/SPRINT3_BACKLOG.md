# Sprint 3 Post-Project Backlog

This list captures the known bugs, edge cases, and technical debt surfaced while validating Sprint 3.

## P1 - Fix Next

1. Wallabot live pricing still depends on an external provider and is excluded from the default acceptance run. The scenario runner only exercises `POST /wallabot/price` when `RUN_WALLABOT_PRICE=1`, so the price path can regress without being noticed in the normal sprint check.
2. Wallabot category suggestions still show weak generalization on unseen edge cases. The prompt log recorded persistent misses for non-motorized mobility, play-vs-collectible ambiguity, electronics-vs-media boundaries, and gaming-accessory classification, so the classifier needs a broader holdout suite before it is considered stable.
3. The product-create screen hides Wallabot price lookup failures instead of surfacing them to the user. If the recommendation call fails, the UI clears the helper text and continues silently, which makes it impossible to tell whether no recommendation was found or the provider failed.
4. The Sprint 3 acceptance runner resolves auth user ids by shelling into the auth-service container and querying the database directly. That keeps the end-to-end flow working, but it is brittle and tightly coupled to the deployment layout.

## P2 - Schedule Soon

1. The catalog search implementation is still substring-based only. It does case-insensitive matching over title and description, treats whitespace-only queries as a no-op, and does not normalize tokens or handle typos, so search quality is limited for real marketplace data.
2. The performance harness does not benchmark the new browse flow directly. It still uses product read/write and transaction-history paths as a proxy workload, so it does not measure the actual catalog listing/filter path that Sprint 3 introduced.
3. The integration and smoke tests are heavily environment-gated. Several scenarios skip when Docker services, external providers, or optional flows are unavailable, which means the suite can report green while important paths remain unverified.

## P3 - Backlog Hygiene

1. The Sprint 3 evaluation artifacts split verification across acceptance, prompt logs, and environment-specific tests. That makes it harder to tell at a glance which behaviors are truly covered versus only demonstrated in one setup.
2. Live Wallabot pricing remains opt-in in both the acceptance runner and the frontend feature flag, so future regressions can hide behind configuration defaults unless the CI path explicitly enables it.