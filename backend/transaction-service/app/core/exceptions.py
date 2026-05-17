"""
SPRINT 3: Error Handling Audit
Typed HTTP exceptions for the transaction service.
Centralizes all error responses for consistency and auditability.
"""
from fastapi import HTTPException, status


class ProductNotFoundException(HTTPException):
    def __init__(self, product_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )

class ProductForbiddenException(HTTPException):
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class InvalidStateTransitionException(HTTPException):
    def __init__(self, current: str, target: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: '{current}' → '{target}'"
        )

class InsufficientFundsException(HTTPException):
    def __init__(self, balance: float, required: float):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient funds: balance {balance:.2f}, required {required:.2f}"
        )

class InvalidAmountException(HTTPException):
    def __init__(self, detail: str = "Amount must be positive"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )

class AtomicOperationException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Atomic operation failed: {detail}"
        )


class ReservationConflictException(HTTPException):
    """Another buyer already holds an active reservation."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already reserved",
        )


class PurchaseReservedByOtherException(HTTPException):
    """Buyer is not the reservation holder."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This product is reserved by another user",
        )


class ReservationReleaseInvalidStateException(HTTPException):
    """Product cannot be released from reservation in its current state."""

    def __init__(self, state: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product is {state} and cannot be released",
        )