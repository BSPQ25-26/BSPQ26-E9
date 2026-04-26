from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str, default: float) -> float:
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class PerfSettings:
    auth_base_url: str = os.getenv("PERF_AUTH_BASE_URL", "http://localhost:8001")
    inventory_base_url: str = os.getenv("PERF_INVENTORY_BASE_URL", "http://localhost:8002")
    transaction_base_url: str = os.getenv("PERF_TRANSACTION_BASE_URL", "http://localhost:8003")
    wallabot_base_url: str = os.getenv("PERF_WALLABOT_BASE_URL", "http://localhost:8004")
    run_id: str = field(default_factory=lambda: os.getenv("PERF_RUN_ID", uuid.uuid4().hex[:8]))
    seller_password: str = os.getenv("PERF_SELLER_PASSWORD", "PerfSeller!123")
    buyer_password: str = os.getenv("PERF_BUYER_PASSWORD", "PerfBuyer!123")
    top_up_amount: float = _as_float(os.getenv("PERF_TOPUP_AMOUNT", "500"), 500.0)
    product_price: float = _as_float(os.getenv("PERF_PRODUCT_PRICE", "49.90"), 49.9)
    upload_images: bool = _as_bool(os.getenv("PERF_UPLOAD_IMAGES", "true"))
    enable_inventory_flow: bool = _as_bool(os.getenv("PERF_ENABLE_INVENTORY_FLOW", "false"))
    enable_wallabot: bool = _as_bool(os.getenv("PERF_ENABLE_WALLABOT", "false"))


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def load_settings() -> PerfSettings:
    return PerfSettings()


def build_absolute_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def build_identity(role: str, run_id: str, index: str, password: str | None = None) -> tuple[str, str]:
    email = f"perf-{run_id}-{role}-{index}@example.com"
    resolved_password = password or f"{role.title()}!{run_id}"
    return email, resolved_password


def build_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}