"""
Unit tests for product state transitions.
Tests valid transitions, invalid transitions, and edge cases.
"""

import pytest
from app.services.state_machine import (
    ProductState,
    is_valid_transition,
    validate_transition
)


# ── Valid Transitions ────────────────────────

def test_available_to_reserved_is_valid():
    """Available → Reserved is a valid transition."""
    assert is_valid_transition(ProductState.AVAILABLE, ProductState.RESERVED) is True


def test_reserved_to_sold_is_valid():
    """Reserved → Sold is a valid transition."""
    assert is_valid_transition(ProductState.RESERVED, ProductState.SOLD) is True


# ── Invalid Transitions ──────────────────────

def test_available_to_sold_is_invalid():
    """Available → Sold is not allowed (must go through Reserved first)."""
    assert is_valid_transition(ProductState.AVAILABLE, ProductState.SOLD) is False


def test_reserved_to_available_is_invalid():
    """Reserved → Available is not allowed (no going back)."""
    assert is_valid_transition(ProductState.RESERVED, ProductState.AVAILABLE) is False


def test_sold_to_available_is_invalid():
    """Sold → Available is not allowed (Sold is a final state)."""
    assert is_valid_transition(ProductState.SOLD, ProductState.AVAILABLE) is False


def test_sold_to_reserved_is_invalid():
    """Sold → Reserved is not allowed (Sold is a final state)."""
    assert is_valid_transition(ProductState.SOLD, ProductState.RESERVED) is False


def test_sold_is_final_state():
    """Sold state has no valid outgoing transitions."""
    from app.services.state_machine import VALID_TRANSITIONS
    assert VALID_TRANSITIONS[ProductState.SOLD] == []


# ── validate_transition raises ValueError ────

def test_validate_transition_raises_on_invalid():
    """validate_transition raises ValueError for invalid transitions."""
    with pytest.raises(ValueError) as exc_info:
        validate_transition(ProductState.AVAILABLE, ProductState.SOLD)
    assert "Invalid transition" in str(exc_info.value)


def test_validate_transition_does_not_raise_on_valid():
    """validate_transition does not raise for valid transitions."""
    try:
        validate_transition(ProductState.AVAILABLE, ProductState.RESERVED)
        validate_transition(ProductState.RESERVED, ProductState.SOLD)
    except ValueError:
        pytest.fail("validate_transition raised ValueError on a valid transition")