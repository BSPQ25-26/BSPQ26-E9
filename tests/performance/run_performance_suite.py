"""
Runs two Locust-based performance executions (one expected to succeed, one expected to fail)
and writes both HTML reports and a structured JSON summary.

The course enunciado mentions ContiPerf; this repository uses Locust while keeping the
output artifacts named/structured to match the assignment's reporting requirements.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERF_ROOT = PROJECT_ROOT / "tests" / "performance"
LOCUSTFILE = PERF_ROOT / "locustfile.py"
REPORTS_DIR = PERF_ROOT / "reports"


def run_locust(*, run_id: str, users: int, hatch_rate: int, run_time: str, html_out: Path) -> None:
    env = os.environ.copy()
    env["PERF_RUN_ID"] = run_id

    # Use the current interpreter so the user's venv works.
    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(LOCUSTFILE),
        "--headless",
        "-u",
        str(users),
        "-r",
        str(hatch_rate),
        "-t",
        str(run_time),
        "--html",
        str(html_out),
    ]

    html_out.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("mini_wallapop.perf.suite")
    logger.info("Running Locust: %s", " ".join(cmd))
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, check=True)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logger = logging.getLogger("mini_wallapop.perf.suite")
    parser = argparse.ArgumentParser(description="Run performance suite (two Locust executions).")
    parser.add_argument("--success-users", type=int, default=20)
    parser.add_argument("--success-hatch-rate", type=int, default=4)
    parser.add_argument("--success-duration", type=str, default="5m")
    parser.add_argument("--fail-users", type=int, default=50)
    parser.add_argument("--fail-hatch-rate", type=int, default=10)
    parser.add_argument("--fail-duration", type=str, default="5m")
    args = parser.parse_args()

    success_run_id = uuid.uuid4().hex[:8]
    fail_run_id = uuid.uuid4().hex[:8]

    # Keep the Locust-native HTML report filenames distinct to avoid overwrites.
    # The Locust harness also writes ContiPerf-like summaries in on_test_stop().
    success_html = REPORTS_DIR / f"locust-report-success-{success_run_id}.html"
    fail_html = REPORTS_DIR / f"locust-report-failed-{fail_run_id}.html"

    run_locust(
        run_id=success_run_id,
        users=args.success_users,
        hatch_rate=args.success_hatch_rate,
        run_time=args.success_duration,
        html_out=success_html,
    )
    run_locust(
        run_id=fail_run_id,
        users=args.fail_users,
        hatch_rate=args.fail_hatch_rate,
        run_time=args.fail_duration,
        html_out=fail_html,
    )

    logger.info("Performance suite finished.")


if __name__ == "__main__":
    main()

