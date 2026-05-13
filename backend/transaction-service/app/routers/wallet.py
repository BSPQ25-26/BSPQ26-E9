"""
Wallet router: Top-up, balance check, and wallet history endpoints.
Ensures all wallet mutations go through the ledger for integrity.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from decimal import Decimal

from app.database import get_db
from app.models import WalletLedger
from app.schemas import (
    WalletTopUpRequest, BalanceResponse,
    WalletLedgerEntry, WalletHistoryResponse
)
from app.api.deps import get_current_user_id

#Sprint 3: Error handling audit 
from app.core.exceptions import InvalidAmountException, AtomicOperationException

#Sprint 3: Structured logging 
from app.core.logging import get_logger, log_request, log_result, log_error
logger= get_logger(__name__)

router = APIRouter(prefix="/wallet", tags=["wallet"])


# Wallet Top-Up Endpoint --> POST /wallet/topup 
# Sprint 2: balance integrity 
@router.post("/topup", response_model=BalanceResponse, status_code=status.HTTP_200_OK)
def top_up_wallet(
    payload: WalletTopUpRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Add funds to user's wallet via Top-Up transaction.
    
    BALANCE INTEGRITY GUARANTEE:
    - Gets the LAST ledger entry (current balance)
    - Calculates new balance: current + amount
    - Creates a NEW WalletLedger entry with balance_after
    - NEVER updates balance_after directly
    - This maintains complete audit trail
    
    Args:
        payload: WalletTopUpRequest with amount (must be > 0)
    
    Returns:
        BalanceResponse with updated balance
    """
    #SPRINT 3: Structured logging 
    log_request(logger, "POST /wallet/topup", user_id, amount=payload.amount)  # ← SPRINT 3 LOG

    if payload.amount <= 0:
        log_error(logger, "POST /wallet/topup", user_id, error="Invalid amount")  # ← SPRINT 3 LOG
        raise InvalidAmountException("Top-up amount must be positive")
    
    # Get current balance from LAST ledger entry
    current_balance = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id == user_id)
        .order_by(desc(WalletLedger.id))
        .first()
    )
    
    balance_before = Decimal(str(current_balance.balance_after)) if current_balance else Decimal("0.00")
    amount = Decimal(str(payload.amount))
    balance_after = balance_before + amount

    #Sprint 3: Error handling audit
    try: 
        # CREATE new entry (NEVER UPDATE balance directly)
        ledger_entry = WalletLedger(
            user_id=user_id,
            amount=amount,
            transaction_type="TOP_UP",
            description=f"Top-up of {amount}",
            balance_after=balance_after,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(ledger_entry)
        db.commit()
        db.refresh(ledger_entry)
    except Exception as e:
        db.rollback()
        raise AtomicOperationException(str(e))

    log_result(logger, "POST /wallet/topup", user_id, balance_after=float(balance_after))
    return BalanceResponse(
        user_id=user_id,
        balance=float(balance_after),
        last_update=ledger_entry.created_at
    )


# Sprint 2: Wallet Balance Endpoint --> GET /wallet/balance
# Returns current balance
@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get current wallet balance for authenticated user.
    
    BALANCE INTEGRITY GUARANTEE:
    - Fetches the LAST ledger entry ordered by creation time
    - Returns balance_after from that entry (always accurate)
    - Never calculates balance directly (impossible to be wrong)
    
    Returns:
        BalanceResponse with current balance from ledger
    """

    #SPRINT 3: Structured logging
    log_request(logger, "GET /wallet/balance", user_id) 
    latest_entry = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id == user_id)
        .order_by(desc(WalletLedger.id))
        .first()
    )

    if not latest_entry:
        #SPRINT 3: Structured logging
        log_result(logger, "GET /wallet/balance", user_id, balance=0.0) 
        # User has no balance history yet
        return BalanceResponse(
            user_id=user_id,
            balance=0.0,
            last_update=datetime.now(timezone.utc)
        )

    #SPRINT 3: Structured logging
    log_result(logger, "GET /wallet/balance", user_id, balance=float(latest_entry.balance_after))  
    return BalanceResponse(
        user_id=user_id,
        balance=float(latest_entry.balance_after),
        last_update=latest_entry.created_at
    )


# Sprint 2 : Purchase and sale transaction History --> Wallet History Endpoint

@router.get("/history", response_model=WalletHistoryResponse)
def get_wallet_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get paginated wallet ledger history for authenticated user.
    
    - Lists all movements in reverse chronological order
    - Supports pagination
    - Used for auditing wallet integrity
    """
    #SPRINT 3: Structured logging
    log_request(logger, "GET /wallet/history", user_id, page=page, per_page=per_page)
    # Get total count
    total = db.query(WalletLedger).filter(WalletLedger.user_id == user_id).count()

    # Calculate offset
    offset = (page - 1) * per_page

    # Get entries for this page
    entries = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id == user_id)
        .order_by(desc(WalletLedger.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )

    entries_schema = [
        WalletLedgerEntry.model_validate(entry) for entry in entries
    ]

    # Get current balance
    current_balance = 0.0
    if entries:
        current_balance = float(entries[0].balance_after)

    #Sprint 3: Structured logging
    log_result(logger, "GET /wallet/history", user_id, total_entries=total, page=page)
    return WalletHistoryResponse(
        user_id=user_id,
        balance=current_balance,
        entries=entries_schema,
        total=total,
        page=page,
        per_page=per_page
    )
