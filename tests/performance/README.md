# Performance Testing And Profiling

This folder contains the Python replacements for the Java course tools:

- `logging` instead of `print()` for diagnostics.
- `pyinstrument` instead of VisualVM.
- `Locust` instead of ContiPerf.

## Install

```powershell
.\.venv\Scripts\python.exe -m pip install -r tests/performance/requirements.txt
```

## Run Locust

The Locust plan exercises the real backend flows that already exist:

- Auth register/login.
- Wallet top-up and balance/history reads.
- Product creation, update, image upload, and product read on the inventory service.
- Reserve and buy on the transaction service.
- Transaction history reads.

The backend does not currently expose a public catalog listing/filter endpoint, so the browsing coverage here uses the available product read/write paths and transaction history as the closest current read-heavy workload.

```powershell
$env:PERF_AUTH_BASE_URL = "http://localhost:8001"
$env:PERF_INVENTORY_BASE_URL = "http://localhost:8002"
$env:PERF_TRANSACTION_BASE_URL = "http://localhost:8003"
$env:PERF_WALLABOT_BASE_URL = "http://localhost:8004"
$env:PERF_ENABLE_INVENTORY_FLOW = "false"

.\.venv\Scripts\python.exe -m locust -f tests/performance/locustfile.py --headless -u 20 -r 4 -t 5m --html tests/performance/reports/locust-report.html
```

Set `PERF_ENABLE_INVENTORY_FLOW=true` only when your `inventory_products` RLS policy allows service-role CRUD.

Suggested starting points:

- Light check: `-u 5 -r 1 -t 2m`
- Sprint 2 baseline: `-u 20 -r 4 -t 5m`
- Higher stress: `-u 50 -r 10 -t 10m`

Key metrics to watch in the Locust report:

- Average response time.
- P95 latency.
- Requests per second.
- Failure rate.

## Run Profiling

Start the transaction service under `pyinstrument` in one terminal, then run Locust in another terminal against the same service.

```powershell
.\.venv\Scripts\python.exe tests/performance/profile_transaction_service.py --host 127.0.0.1 --port 8003 --output tests/performance/reports/transaction-service-profile.html
```

When you stop the server, the script writes the profiling snapshot to the path above. The report shows where the backend spent most of its time while the load test was running.

## Interpreting The Results

- If P95 grows much faster than the average, the service is queuing under load.
- If throughput is flat while latency rises, the bottleneck is usually DB-bound or lock-bound.
- If failures increase after wallet top-ups or purchase attempts, check balance validation, transaction rollbacks, and row locking in the transaction service.
- If the profiler points to repeated ORM query work, look for N+1 reads in the history endpoints and product lookup paths.

## Sprint 2 Performance Runs

- `locust-report-docker-clean.html`: Successful performance run  
  - Config: 20 users, spawn rate 4/s, duration 5m.  
  - P95 latency and failure rate within our targets.

- `locust-report-docker-more-users.html`: Failing performance run  
  - Config: 50 users, higher spawn rate.  
  - P95 latency grows too high and/or failures increase, showing the system limit.