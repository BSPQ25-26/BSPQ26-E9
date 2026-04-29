"""
Define how the data entering and leaving your API is validated. 
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.services.state_machine import ProductState


# Product Schemas 
#Validate the data for creating a new product and for returning product information.
class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    title:       str   = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category:    Optional[str] = Field(None, max_length=100)
    price:       float = Field(..., gt=0)

#What the API will return when a product is retrieved.
class ProductResponse(BaseModel):
    """Schema for returning a product."""
    id:          int
    title:       str
    description: Optional[str]
    category:    Optional[str]
    price:       float
    state:       str
    owner_id:    str
    created_at:  datetime
    updated_at:  datetime

    class Config:
        from_attributes = True


# State Transition Schemas 

#The body of PATCH /products/{id}/state
class StateTransitionRequest(BaseModel):
    """Schema for requesting a state change."""
    target_state: ProductState = Field(..., description="The state to transition to")

#Confirmation wheen a state change is successfully done 
class StateTransitionResponse(BaseModel):
    """Schema for returning the result of a state change."""
    product_id:  int
    from_state:  str
    to_state:    str
    changed_at:  datetime

    class Config:
        from_attributes = True


# State History Schemas 

#Entrie in the state history of a product
class StateHistoryResponse(BaseModel):
    """Schema for returning a single history entry."""
    id:         int
    product_id: int
    from_state: Optional[str]
    to_state:   str
    changed_at: datetime
    changed_by: Optional[str]

    class Config:
        from_attributes = True


# ── Sprint 2: Wallet Schemas ───────────────────────────────────────────────
# BALANCE INTEGRITY GUARANTEE:
# - Each entry in wallet_ledger represents ONE atomic operation (top-up, purchase, sale, etc)
# - balance_after field stores the cumulative balance AFTER that operation
# - Current balance = balance_after from the LAST entry (by created_at)
# - History endpoint returns complete audit trail of all balance changes
class WalletTopUpRequest(BaseModel):
    """Request schema for top-up endpoint."""
    amount: float = Field(..., gt=0, description="Amount to add to wallet")

class BalanceResponse(BaseModel):
    """Current wallet balance for a user."""
    user_id:     str
    balance:     float
    last_update: datetime

class WalletLedgerEntry(BaseModel):
    """Single entry in wallet ledger - represents ONE atomic operation."""
    id:                int
    user_id:           str
    amount:            float                   # Signed: +credit, -debit
    transaction_type:  str                     # deposit, purchase, refund, etc
    description:       Optional[str] = None    # Human-readable description
    balance_after:     float                   # Balance AFTER this operation (immutable)
    created_at:        datetime
    class Config:
        from_attributes = True



class WalletHistoryResponse(BaseModel):
    """Wallet history with pagination - complete audit trail."""
    user_id:  str
    balance:  float
    entries:  list[WalletLedgerEntry]
    total:    int
    page:     int
    per_page: int


# ── Sprint 2: Transaction Schemas ──────────────────────────────────────────
# Transactions are IMMUTABLE (read-only) and always reference ledger entries
class TransactionRequest(BaseModel):
    """Request schema for purchase endpoint."""
    product_id: int = Field(..., description="Product ID to purchase")


class TransactionResponse(BaseModel):
    """Response schema for completed transaction."""
    id:            int
    buyer_id:      str
    seller_id:     str
    product_id:    int
    amount:        float
    status:        str
    created_at:    datetime
    completed_at:  Optional[datetime]

    class Config:
        from_attributes = True

#String 2: New schema for trasaction history response with product details included
class TransactionHistoryResponse(BaseModel):
    """Transaction history entry of a completed transaction."""
    id:             int
    buyer_id:       str
    seller_id:      str
    product_id:     int
    product_title:  str
    amount:         float
    status:         str
    created_at:     datetime
    completed_at:   Optional[datetime]

    class Config:
        from_attributes = True

#String 2:  list of transactions for history endpoints
class TransactionHistoryListResponse(BaseModel):
    """List of history transactions."""
    transactions: list[TransactionHistoryResponse]
    total:        int
    page:         int
    per_page:     int