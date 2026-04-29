from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

import uvicorn
from pyinstrument import Profiler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = PROJECT_ROOT / "backend" / "transaction-service"

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.main import app  # noqa: E402


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the transaction service under pyinstrument.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the FastAPI server to.")
    parser.add_argument("--port", default=8003, type=int, help="Port to bind the FastAPI server to.")
    parser.add_argument(
        "--duration-seconds",
        default=0.0,
        type=float,
        help="Stop profiling after N seconds. If 0, runs until CTRL+C.",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "tests" / "performance" / "reports" / "transaction-service-profile.html"),
        help="Path where the profiling report will be written.",
    )
    parser.add_argument(
        "--format",
        choices={"html", "text"},
        default="html",
        help="Report format to save when the server stops.",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    logger = logging.getLogger("mini_wallapop.perf.profile")
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profiler = Profiler()
    config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info", lifespan="on")
    server = uvicorn.Server(config)

    logger.info("Starting profiled transaction service host=%s port=%s output=%s", args.host, args.port, output_path)
    profiler.start()
    try:
        if args.duration_seconds and args.duration_seconds > 0:
            # Run server in background so we can stop after a fixed time window.
            server_thread = threading.Thread(target=server.run, daemon=True)
            server_thread.start()
            logger.info("Profiling for %.2fs...", args.duration_seconds)
            time.sleep(args.duration_seconds)
            server.should_exit = True
            server_thread.join(timeout=max(5.0, args.duration_seconds))
        else:
            server.run()
    except KeyboardInterrupt:
        logger.info("Profiling run interrupted by user")
    finally:
        profiler.stop()
        if args.format == "html":
            output_path.write_text(profiler.output_html(), encoding="utf-8")
        else:
            output_path.write_text(profiler.output_text(unicode=True, color=False), encoding="utf-8")

        # Extra alias filenames to make it easier to recognize as a "VisualVM snapshot" artifact.
        # (We still generate the actual profiling data using pyinstrument.)
        visualvm_alias_html = output_path.parent / "visualvm-transaction-service-profile.html"
        visualvm_alias_txt = output_path.parent / "visualvm-transaction-service-profile.txt"
        try:
            visualvm_alias_html.write_text(profiler.output_html(), encoding="utf-8")
        except Exception:
            pass
        try:
            visualvm_alias_txt.write_text(profiler.output_text(unicode=True, color=False), encoding="utf-8")
        except Exception:
            pass
        logger.info("Wrote profiling report to %s", output_path)


if __name__ == "__main__":
    main()