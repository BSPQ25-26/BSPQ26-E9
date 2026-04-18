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
- 5 passed
- 1 skipped (the live test is skipped by default)

## 5) Run live endpoint test (real LLM call)

If RUN_LIVE_TESTS is set to true in your .env, run:

```bat
pytest test\test_category_endpoint.py -m live -q
```

If you want to force it from CMD for the current terminal session only:

```bat
set RUN_LIVE_TESTS=true
pytest test\test_category_endpoint.py -m live -q
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
