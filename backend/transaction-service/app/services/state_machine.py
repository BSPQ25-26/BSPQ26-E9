"""
Module for defining valid states and which transitions are allowed between them. 
This is a simple state machine for product states in a transaction system.

TRANSITION LOGIC: 
* Available --> Reserved --> Sold 
* Available cannot go directly to Sold, and Reserved cannot go back to Available.
"""
from enum import Enum

#Posible states for a product in the transaction system
class ProductState(str, Enum):
    AVAILABLE = "available"
    RESERVED  = "reserved"
    SOLD      = "sold"

# Transactions: From an state, which states can we transition to
VALID_TRANSITIONS: dict[ProductState, list[ProductState]] = {
    ProductState.AVAILABLE: [ProductState.RESERVED],
    ProductState.RESERVED:  [ProductState.SOLD],
    ProductState.SOLD:      [],  # final state, no transitions allowed
}

def is_valid_transition(current: ProductState, target: ProductState) -> bool:
    """Returns True if the transition from current to target is valid."""
    return target in VALID_TRANSITIONS[current]

def validate_transition(current: ProductState, target: ProductState) -> None:
    """Raises an exception if the transition is not allowed."""
    if not is_valid_transition(current, target):
        raise ValueError(
            f"Invalid transition: '{current}' → '{target}'. "
            f"From '{current}' you can only go to: {VALID_TRANSITIONS[current]}"
        )