import pytest
from pydantic import ValidationError

from app.schemas import WalletTopUpRequest
from app.services.state_machine import ProductState, is_valid_transition, validate_transition
# cd backend\transaction-service
# python -m pytest test\test_state_transitions.py -q

@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ProductState.AVAILABLE, ProductState.RESERVED),
        (ProductState.RESERVED, ProductState.SOLD),
    ],
)
def test_valid_state_transitions(current, target):
    assert is_valid_transition(current, target) is True

    validate_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ProductState.AVAILABLE, ProductState.SOLD),
        (ProductState.RESERVED, ProductState.AVAILABLE),
        (ProductState.SOLD, ProductState.AVAILABLE),
        (ProductState.SOLD, ProductState.RESERVED),
    ],
)
def test_invalid_state_transitions_raise(current, target):
    assert is_valid_transition(current, target) is False

    with pytest.raises(ValueError, match="Invalid transition"):
        validate_transition(current, target)


@pytest.mark.parametrize("amount", [0, -1, -25.5])
def test_wallet_topup_request_rejects_non_positive_amount(amount):
    with pytest.raises(ValidationError) as exc_info:
        WalletTopUpRequest(amount=amount)

    assert "amount" in str(exc_info.value)


def test_wallet_topup_request_accepts_positive_amount():
    request = WalletTopUpRequest(amount=12.5)

    assert request.amount == 12.5