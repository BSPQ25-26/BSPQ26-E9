import os
from collections.abc import Iterable

import httpx
import pytest

#for running:
# docker compose up --build -d auth-service inventory-service transaction-service //(until the rest is done or working)
# $env:RUN_DOCKER_SMOKE="1"; python.exe -m pytest tests/smoke/test_docker_smoke.py -v


RUN_SMOKE = os.getenv("RUN_DOCKER_SMOKE") == "1"
SMOKE_TIMEOUT_SECONDS = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "10"))

# Current working baseline: auth + transaction are required.
DEFAULT_REQUIRED_SERVICES = "auth-service,transaction-service,inventory-service"
DEFAULT_OPTIONAL_SERVICES = "agentic-service"

SERVICE_URLS = {
    "auth-service": "http://localhost:8001",
    "inventory-service": "http://localhost:8002",
    "transaction-service": "http://localhost:8003",
    "agentic-service": "http://localhost:8004",
}

HEALTH_PATHS = {
    "auth-service": "/health",
    "inventory-service": "/health",
    "transaction-service": "/health",
    "agentic-service": "/health",
}

API_SMOKE_PATHS = {
    "auth-service": "/auth/test",
    "inventory-service": "/openapi.json",
    "transaction-service": "/openapi.json",
    "agentic-service": "/openapi.json",
}

pytestmark = pytest.mark.skipif(
    not RUN_SMOKE,
    reason="Set RUN_DOCKER_SMOKE=1 to run Docker smoke tests.",
)



def _parse_service_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]



def _services_from_env(var_name: str, default_value: str) -> list[str]:
    services = _parse_service_list(os.getenv(var_name, default_value))
    unknown = [name for name in services if name not in SERVICE_URLS]
    if unknown:
        raise ValueError(f"Unknown service names in {var_name}: {unknown}")
    return services



def _service_url(service_name: str) -> str:
    override = os.getenv(f"SMOKE_URL_{service_name.upper().replace('-', '_')}")
    return override or SERVICE_URLS[service_name]



def _check_endpoint(client: httpx.Client, url: str, service_name: str, endpoint_label: str) -> httpx.Response:
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        pytest.fail(f"{service_name} {endpoint_label} request failed: {exc}")
    return response



def _assert_service_available(client: httpx.Client, service_name: str) -> None:
    base_url = _service_url(service_name)

    health_url = f"{base_url}{HEALTH_PATHS[service_name]}"
    health_response = _check_endpoint(client, health_url, service_name, "health")
    assert health_response.status_code == 200, (
        f"{service_name} health check failed [{health_response.status_code}]: {health_response.text}"
    )

    api_url = f"{base_url}{API_SMOKE_PATHS[service_name]}"
    api_response = _check_endpoint(client, api_url, service_name, "API smoke")
    assert api_response.status_code == 200, (
        f"{service_name} API smoke check failed [{api_response.status_code}]: {api_response.text}"
    )



def _run_services_smoke(client: httpx.Client, services: Iterable[str]) -> None:
    for service_name in services:
        _assert_service_available(client, service_name)



def test_required_services_are_healthy_and_reachable() -> None:
    required_services = _services_from_env("SMOKE_REQUIRED_SERVICES", DEFAULT_REQUIRED_SERVICES)

    with httpx.Client(timeout=SMOKE_TIMEOUT_SECONDS) as client:
        _run_services_smoke(client, required_services)



def test_optional_services_are_reachable_when_enabled() -> None:
    optional_services = _services_from_env("SMOKE_OPTIONAL_SERVICES", DEFAULT_OPTIONAL_SERVICES)

    with httpx.Client(timeout=SMOKE_TIMEOUT_SECONDS) as client:
        for service_name in optional_services:
            base_url = _service_url(service_name)
            health_url = f"{base_url}{HEALTH_PATHS[service_name]}"

            try:
                health_response = client.get(health_url)
            except httpx.HTTPError:
                pytest.skip(f"Optional service {service_name} is unavailable at {base_url}")

            if health_response.status_code != 200:
                pytest.skip(
                    f"Optional service {service_name} health is {health_response.status_code} at {base_url}"
                )

            _assert_service_available(client, service_name)
