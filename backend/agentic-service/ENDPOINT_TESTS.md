# Endpoint Test Procedure (Windows CMD)

This guide explains how to run endpoint-level tests for the agentic service from Windows CMD.

Assumption:
- Your .env is already configured (OPENAI_API_KEY, RUN_LIVE_TESTS when needed).

## 1) Open CMD and go to repository root

Copy and run:

```bat
cd /d C:\{path}\BSPQ26-E9
```

## 2) Activate virtual environment

Copy and run:

```bat
call .venv\Scripts\activate.bat
```

You should see the environment name at the beginning of the command line.

## 3) Go to the agentic-service folder

Copy and run:

```bat
cd backend\agentic-service
```

## 4) Run endpoint tests (default, non-live)

This runs endpoint tests that do not require a real LLM call.

Copy and run:

```bat
pytest test\test_category_endpoint.py -q
```

Expected result:
- 6 passed
- 1 skipped (the live test is skipped by default)

## 5) Run with live marker (real LLM call + same-file endpoint tests)

If RUN_LIVE_TESTS is set to true in your .env, run:

```bat
pytest test\test_category_endpoint.py -m live -q
```

Current behavior in this project:
- With RUN_LIVE_TESTS=true, this command runs all tests in `test_category_endpoint.py` (live + non-live).
- With RUN_LIVE_TESTS=false, this command selects only the live-marked test and it is skipped.

If you want to force it from CMD for the current terminal session only:

```bat
set RUN_LIVE_TESTS=true
pytest test\test_category_endpoint.py -m live -q
```

If you want to run only the real live test function:

```bat
set RUN_LIVE_TESTS=true
pytest test\test_category_endpoint.py -k test_live_category_suggestion -q
```

## 6) Run all endpoint-relevant tests together

Copy and run:

```bat
pytest test\test_category_schema.py test\test_category_agent.py test\test_category_endpoint.py -q
```

## 7) Optional: run prompt evaluation (not an endpoint test)

`prompt_eval.py` is used to evaluate prompt quality across multiple fixed product cases.
It prints PASS/FAIL per case and final accuracy. It is useful for prompt tuning,
but it is separate from endpoint-level pytest tests.

Copy and run:

```bat
python -m test.prompt_eval
```

Alternative (also supported):

```bat
python test\prompt_eval.py
```

## 8) Optional: verbose output for debugging

Copy and run:

```bat
pytest test\test_category_endpoint.py -vv
```

## 9) Common quick checks

If pytest is not found:

```bat
python -m pytest test\test_category_endpoint.py -q
```

If imports fail, make sure you are inside backend\agentic-service before running pytest.
