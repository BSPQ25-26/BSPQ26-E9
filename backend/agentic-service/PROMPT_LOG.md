# Prompt Iteration Log

## Iteration 1 - Baseline Task Prompt
- Date: 2026-03-21
- Change: Added explicit instruction to use category names exactly as provided and to set `is_new_category=true` only when no existing category matches.
- Reason: Reduce false "new category" proposals for products that clearly fit default categories.
- Result: Prompt structure now enforces deterministic JSON output with the fields `suggested_category`, `confidence`, and `is_new_category` for parser validation.
- Next check: Run the 7-case runner in `app/hello_chain.py` with real API credentials and verify at least one valid `is_new_category=true` case.

## Iteration 2 - Control "Other" Overuse
- Date: 2026-03-21
- Change: Added rules to use `Other` only for standard physical products and to prefer a new category for out-of-taxonomy items (food, services, live goods, niche consumables).
- Reason: Initial run classified unusual items as `Other`, which did not exercise the `is_new_category=true` path.
- Result: Prompt now explicitly separates fallback-to-`Other` from true taxonomy mismatch behavior.
- Next check: Re-run the 7-case runner and confirm at least one response uses `is_new_category=true`.

## Iteration 3 - Hard Rule For Non-Physical Offers
- Date: 2026-03-21
- Change: Escalated the instruction from preference to mandatory behavior: for services/non-physical or clearly out-of-taxonomy items, the model must return a new category and `is_new_category=true`.
- Reason: Iteration 2 still returned `Other` for service-like cases.
- Result: Prompt now includes a direct MUST constraint to enforce the branch.
- Next check: Execute the runner again and verify at least one `[NEW]` output.
