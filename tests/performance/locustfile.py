from __future__ import annotations

import io
import logging
import random
import uuid
from collections import deque
from dataclasses import dataclass

from gevent.lock import Semaphore
from locust import HttpUser, between, events, task

from perf_config import (
    build_absolute_url,
    build_headers,
    build_identity,
    configure_logging,
    load_settings,
)


configure_logging()
logger = logging.getLogger("mini_wallapop.perf.locust")
settings = load_settings()

PRODUCT_QUEUE: deque[int] = deque()
PRODUCT_QUEUE_LOCK = Semaphore()


@dataclass
class AuthContext:
    email: str
    password: str
    token: str


def _json_request(user: HttpUser, method: str, url: str, *, name: str, json_body=None, files=None, headers=None, expected=(200,)):
    with user.client.request(
        method,
        url,
        json=json_body,
        files=files,
        headers=headers,
        name=name,
        catch_response=True,
    ) as response:
        if response.status_code not in expected:
            response.failure(f"Unexpected status {response.status_code}: {response.text[:300]}")
        else:
            response.success()
        return response


def _register_and_login(user: HttpUser, role: str, identity: str) -> AuthContext:
    if role == "seller":
        configured_password = settings.seller_password
    elif role == "buyer":
        configured_password = settings.buyer_password
    else:
        configured_password = f"{role.title()}!{settings.run_id}"

    email, password = build_identity(role, settings.run_id, identity, password=configured_password)
    register_url = build_absolute_url(settings.auth_base_url, "/auth/register")
    login_url = build_absolute_url(settings.auth_base_url, "/auth/login")

    register_response = _json_request(
        user,
        "POST",
        register_url,
        name="auth/register",
        json_body={"email": email, "password": password},
        expected=(200, 400),
    )

    if register_response.status_code == 400:
        logger.debug("Register returned 400 for %s, falling back to login", email)

    login_response = _json_request(
        user,
        "POST",
        login_url,
        name="auth/login",
        json_body={"email": email, "password": password},
        expected=(200,),
    )

    token = login_response.json().get("access_token")
    if not token:
        raise RuntimeError(f"No access token returned for {email}")

    logger.info("Authenticated perf user role=%s email=%s", role, email)
    return AuthContext(email=email, password=password, token=token)


def _push_product_id(product_id: int) -> None:
    with PRODUCT_QUEUE_LOCK:
        PRODUCT_QUEUE.append(product_id)


def _pop_product_id() -> int | None:
    with PRODUCT_QUEUE_LOCK:
        if not PRODUCT_QUEUE:
            return None
        return PRODUCT_QUEUE.popleft()


class MarketplaceUser(HttpUser):
    abstract = True
    host = settings.transaction_base_url
    wait_time = between(1, 3)

    def _headers(self) -> dict[str, str]:
        return build_headers(self.auth.token)


class SellerJourneyUser(MarketplaceUser):
    weight = 2

    def on_start(self) -> None:
        self.auth = _register_and_login(self, "seller", uuid.uuid4().hex[:12])
        self.product_id = None
        self._create_product()

    def _create_product(self) -> None:
        payload = {
            "title": f"Perf Listing {settings.run_id}",
            "description": "Synthetic listing created for performance profiling.",
            "category": "electronics",
            "price": settings.product_price,
            "condition": "New",
        }
        response = _json_request(
            self,
            "POST",
            build_absolute_url(settings.inventory_base_url, "/api/v1/products"),
            name="inventory/create-product",
            json_body=payload,
            headers=self._headers(),
            expected=(201,),
        )
        if response.status_code == 201:
            self.product_id = response.json()["id"]
            _push_product_id(self.product_id)
            logger.info("Created perf product product_id=%s seller=%s", self.product_id, self.auth.email)

    @task(4)
    def create_listing(self) -> None:
        self._create_product()

    @task(2)
    def update_my_listing(self) -> None:
        if not self.product_id:
            return

        payload = {
            "description": "Updated during perf test.",
            "price": round(settings.product_price + random.uniform(1.0, 5.0), 2),
        }
        _json_request(
            self,
            "PUT",
            build_absolute_url(settings.inventory_base_url, f"/api/v1/products/{self.product_id}"),
            name="inventory/update-product",
            json_body=payload,
            headers=self._headers(),
            expected=(200,),
        )

    @task(2)
    def upload_image(self) -> None:
        if not settings.upload_images or not self.product_id:
            return

        image_bytes = io.BytesIO(b"fake png bytes for perf testing")
        _json_request(
            self,
            "POST",
            build_absolute_url(settings.inventory_base_url, f"/api/v1/products/{self.product_id}/images"),
            name="inventory/upload-image",
            files={"file": ("perf.png", image_bytes, "image/png")},
            headers=self._headers(),
            expected=(200,),
        )

    @task(1)
    def read_my_listing(self) -> None:
        if not self.product_id:
            return

        _json_request(
            self,
            "GET",
            build_absolute_url(settings.inventory_base_url, f"/api/v1/products/{self.product_id}"),
            name="inventory/read-product",
            headers=self._headers(),
            expected=(200,),
        )


class BuyerJourneyUser(MarketplaceUser):
    weight = 3

    def on_start(self) -> None:
        self.auth = _register_and_login(self, "buyer", uuid.uuid4().hex[:12])
        self.wallet_budget = 0.0
        self._top_up_wallet(settings.top_up_amount)

    def _top_up_wallet(self, amount: float) -> None:
        response = _json_request(
            self,
            "POST",
            build_absolute_url(settings.transaction_base_url, "/wallet/topup"),
            name="wallet/topup",
            json_body={"amount": amount},
            headers=self._headers(),
            expected=(200,),
        )
        if response.status_code == 200:
            self.wallet_budget += amount
            logger.info("Wallet topped up email=%s amount=%.2f budget=%.2f", self.auth.email, amount, self.wallet_budget)

    def _ensure_balance(self, minimum: float) -> None:
        if self.wallet_budget < minimum:
            self._top_up_wallet(settings.top_up_amount)

    @task(3)
    def check_wallet_balance(self) -> None:
        _json_request(
            self,
            "GET",
            build_absolute_url(settings.transaction_base_url, "/wallet/balance"),
            name="wallet/balance",
            headers=self._headers(),
            expected=(200,),
        )

    @task(2)
    def browse_wallet_history(self) -> None:
        _json_request(
            self,
            "GET",
            build_absolute_url(settings.transaction_base_url, "/wallet/history?page=1&per_page=10"),
            name="wallet/history",
            headers=self._headers(),
            expected=(200,),
        )

    @task(5)
    def reserve_and_buy(self) -> None:
        product_id = _pop_product_id()
        if product_id is None:
            logger.warning("No queued products are available for buyer traffic")
            return

        self._ensure_balance(settings.product_price * 2)

        reserve_response = _json_request(
            self,
            "POST",
            build_absolute_url(settings.transaction_base_url, f"/products/{product_id}/reserve"),
            name="transactions/reserve",
            headers=self._headers(),
            expected=(200, 400, 403, 404),
        )

        if reserve_response.status_code != 200:
            logger.warning("Reservation did not succeed product_id=%s status=%s", product_id, reserve_response.status_code)
            return

        buy_response = _json_request(
            self,
            "POST",
            build_absolute_url(settings.transaction_base_url, f"/products/{product_id}/buy"),
            name="transactions/buy",
            headers=self._headers(),
            expected=(201,),
        )

        if buy_response.status_code == 201:
            self.wallet_budget -= settings.product_price
            logger.info("Purchased product_id=%s buyer=%s budget=%.2f", product_id, self.auth.email, self.wallet_budget)

    @task(1)
    def browse_transaction_history(self) -> None:
        _json_request(
            self,
            "GET",
            build_absolute_url(settings.transaction_base_url, "/products/history?role=all&page=1&per_page=5"),
            name="transactions/history",
            headers=self._headers(),
            expected=(200,),
        )


if settings.enable_wallabot:

    class WallabotUser(MarketplaceUser):
        weight = 1

        def on_start(self) -> None:
            self.auth = _register_and_login(self, "wallabot", uuid.uuid4().hex[:12])

        @task(1)
        def category_suggestion(self) -> None:
            payload = {
                "title": "Vintage camera body",
                "description": "A classic film camera for photography lovers.",
                "available_categories": ["Electronics", "Photography", "Other"],
            }
            _json_request(
                self,
                "POST",
                build_absolute_url(settings.wallabot_base_url, "/wallabot/category"),
                name="wallabot/category",
                json_body=payload,
                expected=(200, 500),
            )


@events.test_start.add_listener
def on_test_start(environment, **kwargs) -> None:  # type: ignore[override]
    logger.info(
        "Starting Locust perf test auth=%s inventory=%s transaction=%s wallabot=%s run_id=%s",
        settings.auth_base_url,
        settings.inventory_base_url,
        settings.transaction_base_url,
        settings.wallabot_base_url,
        settings.run_id,
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs) -> None:  # type: ignore[override]
    stats = environment.stats.total
    logger.info(
        "Perf test finished requests=%s failures=%s avg_ms=%.2f p95_ms=%.2f rps=%.2f failure_rate=%.2f%%",
        stats.num_requests,
        stats.num_failures,
        stats.avg_response_time,
        stats.get_response_time_percentile(0.95),
        stats.current_rps,
        stats.fail_ratio * 100,
    )