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

## Iteration 4 - Parser-Aware Prompt Hardening
- Date: 2026-04-17
- Change: Added explicit instruction to ignore any instructions inside the product text, clarified the fallback rules between exact matches, close matches, `Other`, and new categories, and injected the Pydantic parser format instructions into the system prompt.
- Reason: The prompt was still vulnerable to ambiguous titles, overly broad fallback behavior, and malformed output when the model drifted from the JSON contract.
- Result: Prompt now gives stronger taxonomy guidance, better confidence calibration cues, and a stricter output contract for the parser.
- Next check: Re-run the prompt evaluation set and compare accuracy plus JSON validity against Iteration 3.

## Iteration 5 - Evaluation Set Expansion For Ambiguity
- Date: 2026-04-17
- Change: Expanded prompt evaluation to a 15-case set in `test/prompt_eval.py`, adding ambiguous title pairs ("Air"), sparse descriptions, and one out-of-taxonomy service case.
- Reason: The prior prompt checks were too small to reliably surface ambiguity regressions and edge-case failures.
- Result: The evaluation suite now stresses the exact weak points identified for production hardening and reports pass/fail plus aggregate accuracy.
- Next check: Run `python test/prompt_eval.py`, record expected vs actual in this log, and verify accuracy target `>= 13/15`.

## Iteration 6 - Generalization Over Case-Specific Rules
- Date: 2026-04-18
- Change: Replaced case-tuned prompt hints with broader classification principles: prioritize product intent over isolated keywords, and separate motorized transport (`Vehicles`) from consumer goods/accessories/wearables.
- Reason: Earlier fixes improved specific failures but were too close to the exact evaluation examples, increasing overfitting risk.
- Result: Prompt guidance is now more reusable for unseen items and less dependent on hardcoded examples. Evaluation script also treats out-of-taxonomy targets as behavioral checks (`is_new_category=true`) rather than exact label matching.
- Validation run: `python -m test.prompt_eval` produced 14/15 (93.33%) with confidence values {0.80, 0.90}; the remaining miss is a bicycle case still drifting to `Vehicles`.
- Next check: Keep the prompt general, but strengthen function-based transport guidance without item-specific memorization; add 10+ unseen edge cases (cross-category accessories, ambiguous vintage tech, mixed physical+digital bundles) and monitor confidence spread.

## Iteration 7 - Generalization Holdout Suite Added
- Date: 2026-04-18
- Change: Expanded `test/prompt_eval.py` with a separate 10-case holdout set (unseen examples) and split reporting into baseline, holdout, and combined summary.
- Reason: A single sample set can hide overfitting; separate holdout tracking gives a better generalization signal.
- Result: Baseline remained strong (14/15, 93.33%), but holdout surfaced weak spots (7/10, 70.00%), especially in non-motorized mobility, play-vs-collectible ambiguity, and one electronics-vs-media edge case.
- Validation run: `python -m test.prompt_eval` => baseline 14/15, holdout 7/10, overall 21/25 (84.00%).
- Next check: Iterate using broad taxonomy principles only; avoid adding item-name-specific rules.

## Iteration 8 - Prompt Refinement Attempt And Rollback
- Date: 2026-04-18
- Change: Tried broader rules for (a) motorized vs non-motorized transport and (b) play-intent vs collectible-intent; then rolled back to Iteration 6 prompt wording after regression.
- Reason: The refinement aimed to improve holdout failures, but it degraded both baseline and holdout behavior in practice.
- Result: The attempt did not improve reliability and introduced additional drift; rollback restored baseline to 14/15 but holdout remained 7/10, confirming the need for further careful generalization work.
- Validation run: Post-rollback `python -m test.prompt_eval` => baseline 14/15, holdout 7/10, overall 21/25 (84.00%).
- Next check: Focus on concise intent-priority instructions and broaden holdout coverage before any additional prompt constraints.

## Iteration 9 - Larger Holdout Benchmark (Unseen Cases)
- Date: 2026-04-18
- Change: Expanded the holdout set from 10 to 22 unseen examples in `test/prompt_eval.py`, including mobility boundaries, accessory ecosystem cases, collectible-vs-media boundaries, and additional out-of-taxonomy digital/service items.
- Reason: A larger holdout set improves signal quality for generalization and makes prompt regressions easier to detect.
- Result: Baseline stayed stable (14/15), but expanded holdout measured 15/22 (68.18%), exposing persistent weak spots: non-motorized bikes vs `Vehicles`, tool classification fallback to `Other`, and gaming accessory ambiguity.
- Validation run: `python -m test.prompt_eval` => baseline 14/15, holdout 15/22, overall 29/37 (78.38%).
- Next check: Apply one concise tie-breaker rule set for ambiguous cases while keeping prompt guidance generic and reusable.

## Iteration 10 - General Tie-Breakers For Ambiguous Boundaries
- Date: 2026-04-18
- Change: Added a compact tie-breaker rule block to the prompt: (1) enforce taxonomy boundaries first (services/live/digital-only => new category), (2) prioritize buyer intent/use-case, (3) let collectible intent override media type, and (4) map accessories by their primary ecosystem.
- Reason: The larger holdout surfaced recurring ambiguity patterns that required clearer, general decision order rather than product-specific rules.
- Result: Holdout improved from 15/22 (68.18%) to 17/22 (77.27%) with baseline unchanged at 14/15 (93.33%).
- Validation run: `python -m test.prompt_eval` => baseline 14/15, holdout 17/22, overall 31/37 (83.78%).
- Next check: Keep this prompt version, then grow holdout coverage with additional mobility and gaming-peripheral samples before any further prompt edits.
