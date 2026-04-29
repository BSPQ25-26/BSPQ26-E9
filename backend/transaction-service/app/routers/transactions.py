"""
Transaction router: Product reservation and purchase endpoints.
Handles wallet-based purchases with atomic transactions and state transitions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from decimal import Decimal

from app.database import get_db
from app.models import Product, WalletLedger, Transaction, ProductStateHistory
from app.schemas import (
    ProductResponse,
    TransactionResponse,
    TransactionHistoryResponse, TransactionHistoryListResponse,
    
)
from app.services.state_machine import ProductState, is_valid_transition
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/products", tags=["transactions"])

RESERVED_HISTORY_VALUES = (
    ProductState.RESERVED.value,
    str(ProductState.RESERVED),
)


def get_latest_reservation_history(db: Session, product_id: int):
    return (
        db.query(ProductStateHistory)
        .filter(ProductStateHistory.product_id == product_id)
        .filter(ProductStateHistory.to_state.in_(RESERVED_HISTORY_VALUES))
        .order_by(desc(ProductStateHistory.id))
        .first()
    )


@router.post("/{product_id}/reserve", status_code=status.HTTP_200_OK)
def reserve_product(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Reserve a product for future purchase.
    
    - Transitions product state: Available → Reserved
    - Records state change in history
    - Returns updated product state
    - Prevents self-reservation (ownership guard)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if product.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reserve your own product"
        )

    if product.state == ProductState.RESERVED:
        latest_reservation = get_latest_reservation_history(db, product.id)

        if latest_reservation and latest_reservation.changed_by == user_id:
            return {
                "product_id": product.id,
                "state": product.state,
                "reserved_by": user_id,
                "updated_at": product.updated_at
            }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is already reserved"
        )
    
    if not is_valid_transition(product.state, ProductState.RESERVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {product.state} to {ProductState.RESERVED}"
        )
    
    old_state = product.state
    product.state = ProductState.RESERVED
    product.reserved_at = datetime.now(timezone.utc)
    product.updated_at = datetime.now(timezone.utc)
    
    history = ProductStateHistory(
        product_id=product.id,
        from_state=old_state.value if isinstance(old_state, ProductState) else old_state,
        to_state=ProductState.RESERVED.value,
        changed_by=user_id
    )
    
    db.add(history)
    db.commit()
    db.refresh(product)
    
    return {
        "product_id": product.id,
        "state": product.state,
        "reserved_by": user_id,
        "updated_at": product.updated_at
    }


@router.post("/{product_id}/cancel-reservation", status_code=status.HTTP_200_OK)
def cancel_reservation(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Cancel a reservation owned by the user or product seller."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )

    if product.state == ProductState.AVAILABLE:
        return {
            "product_id": product.id,
            "state": product.state,
            "cancelled_by": user_id,
            "updated_at": product.updated_at
        }

    if product.state != ProductState.RESERVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product is {product.state} and cannot be released"
        )

    latest_reservation = get_latest_reservation_history(db, product.id)
    reserved_by = latest_reservation.changed_by if latest_reservation else None

    if user_id not in {reserved_by, product.owner_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reservation owner or seller can cancel this reservation"
        )

    old_state = product.state
    product.state = ProductState.AVAILABLE
    product.reserved_at = None
    product.updated_at = datetime.now(timezone.utc)

    history = ProductStateHistory(
        product_id=product.id,
        from_state=old_state.value if isinstance(old_state, ProductState) else old_state,
        to_state=ProductState.AVAILABLE.value,
        changed_by=user_id
    )

    db.add(history)
    db.commit()
    db.refresh(product)

    return {
        "product_id": product.id,
        "state": product.state,
        "cancelled_by": user_id,
        "updated_at": product.updated_at
    }


@router.post("/{product_id}/buy", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def purchase_product(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Purchase a reserved or available product.
    
    ATOMIC TRANSACTION with BALANCE INTEGRITY GUARANTEE:
    
    1. VALIDATION:
       - Product exists
       - Buyer is not the seller (ownership guard)
       - Product is AVAILABLE or RESERVED
       - Buyer has sufficient wallet balance
    
    2. ATOMIC OPERATIONS (all succeed or all rollback):
       a) DEBIT buyer: Create WalletLedger entry (amount: -price)
       b) CREDIT seller: Create WalletLedger entry (amount: +price)
       c) UPDATE product: Change state from AVAILABLE/RESERVED → SOLD
       d) RECORD history: Add entry to product_state_history
       e) RECORD transaction: Add entry to trasacctions table
    
    3. BALANCE INTEGRITY:
       - Both buyer debit and seller credit create NEW ledger entries
       - NEVER update balance_after directly
       - If ANY step fails, entire transaction rolls back (try/except)
       - This ensures buyer and seller balances are always consistent
    
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if product.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot purchase your own product"
        )
    
    if product.state not in [ProductState.AVAILABLE, ProductState.RESERVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product is {product.state} and cannot be purchased"
        )
    
    buyer_ledger = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id == user_id)
        .order_by(desc(WalletLedger.id))
        .first()
    )
    
    buyer_balance = Decimal(str(buyer_ledger.balance_after)) if buyer_ledger else Decimal("0.00")
    product_price = Decimal(str(product.price))
    
    if buyer_balance < product_price:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient funds: balance {buyer_balance}, needed {product_price}"
        )
    
    try:
        buyer_new_balance = buyer_balance - product_price
        buyer_debit = WalletLedger(
            user_id=user_id,
            amount=-product_price,
            transaction_type="purchase",
            description=f"Sale of product {product_id}",
            balance_after=buyer_new_balance,
            created_at=datetime.now(timezone.utc)
        )
        db.add(buyer_debit)
        
        seller_ledger = (
            db.query(WalletLedger)
            .filter(WalletLedger.user_id == product.owner_id)
            .order_by(desc(WalletLedger.id))
            .first()
        )
        
        seller_balance = Decimal(str(seller_ledger.balance_after)) if seller_ledger else Decimal("0.00")
        seller_new_balance = seller_balance + product_price
        seller_credit = WalletLedger(
            user_id=product.owner_id,
            amount=product_price,
            description=f"Sale of product {product_id}",
            transaction_type="refund",
            balance_after=seller_new_balance,
            created_at=datetime.now(timezone.utc)
        )
        db.add(seller_credit)
        
        old_state = product.state
        product.state = ProductState.SOLD
        product.reserved_at = None
        product.updated_at = datetime.now(timezone.utc)
        
        history = ProductStateHistory(
            product_id=product.id,
            from_state=old_state,
            to_state=ProductState.SOLD,
            changed_by=user_id
        )
        db.add(history)
        
        transaction = Transaction(
            buyer_id=user_id,
            seller_id=product.owner_id,
            product_id=product.id,
            amount=product_price,
            status="completed",
            created_at=datetime.now(timezone.utc)
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(transaction)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Purchase failed: {str(e)}"
        )
    
    return TransactionResponse(
        id=transaction.id,
        buyer_id=transaction.buyer_id,
        seller_id=transaction.seller_id,
        product_id=transaction.product_id,
        amount=float(transaction.amount),
        status=transaction.status,
        created_at=transaction.created_at,
        completed_at=transaction.created_at
    )


@router.get("/history", response_model=TransactionHistoryListResponse)
def get_transaction_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    role: str = Query("all", pattern="^(buyer|seller|all)$", description="Filter by role"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get transaction history for authenticated user.
    Returns transaction history with product information.
    """
    if role == "buyer":
        filter_clause = Transaction.buyer_id == user_id
    elif role == "seller":
        filter_clause = Transaction.seller_id == user_id
    else:  
        from sqlalchemy import or_
        filter_clause = or_(
            Transaction.buyer_id == user_id,
            Transaction.seller_id == user_id
        )
    
    total = db.query(Transaction).filter(filter_clause).count()
    
    offset = (page - 1) * per_page
    
    transactions = (
        db.query(Transaction)
        .filter(filter_clause)
        .order_by(desc(Transaction.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )
    
    transaction_responses = []
    for txn in transactions:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        
        transaction_responses.append(TransactionHistoryResponse(
            id=txn.id,
            buyer_id=txn.buyer_id,
            seller_id=txn.seller_id,
            product_id=txn.product_id,
            product_title=product.title if product else "Unknown",
            amount=float(txn.amount),
            status=txn.status,
            created_at=txn.created_at,
            completed_at=txn.created_at
        ))
    
    return TransactionHistoryListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/purchases", response_model=TransactionHistoryListResponse)
def get_purchase_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get all products purchased by authenticated user."""
    total = db.query(Transaction).filter(Transaction.buyer_id == user_id).count()
    offset = (page - 1) * per_page
    
    transactions = (
        db.query(Transaction)
        .filter(Transaction.buyer_id == user_id)
        .order_by(desc(Transaction.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )
    
    transaction_responses = []
    for txn in transactions:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        transaction_responses.append(TransactionHistoryResponse(
            id=txn.id,
            buyer_id=txn.buyer_id,
            seller_id=txn.seller_id,
            product_id=txn.product_id,
            product_title=product.title if product else "Unknown",
            amount=float(txn.amount),
            status=txn.status,
            created_at=txn.created_at,
            completed_at=txn.created_at
        ))
    
    return TransactionHistoryListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/sales", response_model=TransactionHistoryListResponse)
def get_sales_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get all products sold by authenticated user."""
    total = db.query(Transaction).filter(Transaction.seller_id == user_id).count()
    offset = (page - 1) * per_page
    
    transactions = (
        db.query(Transaction)
        .filter(Transaction.seller_id == user_id)
        .order_by(desc(Transaction.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )
    
    transaction_responses = []
    for txn in transactions:
        product = db.query(Product).filter(Product.id == txn.product_id).first()
        transaction_responses.append(TransactionHistoryResponse(
            id=txn.id,
            buyer_id=txn.buyer_id,
            seller_id=txn.seller_id,
            product_id=txn.product_id,
            product_title=product.title if product else "Unknown",
            amount=float(txn.amount),
            status=txn.status,
            created_at=txn.created_at,
            completed_at=txn.created_at
        ))
    
    return TransactionHistoryListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        per_page=per_page
    )


RESERVATION_TIMEOUT_SECONDS = 900  # 15 minutes

def release_expired_reservations(db: Session, timeout_seconds: int = RESERVATION_TIMEOUT_SECONDS) -> int:
    """
    Release (timeout) expired reservations.
    
    Transitions RESERVED products back to AVAILABLE if they've been reserved 
    longer than timeout_seconds.
    
    Example:
        - Product reserved at 10:00
        - Timeout = 900 seconds (15 minutes)
        - At 10:15+, if product still RESERVED → transitions back to AVAILABLE
    """
    now = datetime.now()
    
    expired_reservations = (
        db.query(Product)
        .filter(Product.state == ProductState.RESERVED)
        .filter(Product.reserved_at.isnot(None))
        .all()
    )
    
    released_count = 0
    
    for product in expired_reservations:
        if product.reserved_at:
            age_seconds = (now - product.reserved_at).total_seconds()
            
            if age_seconds > timeout_seconds:
                old_state = product.state
                product.state = ProductState.AVAILABLE
                product.reserved_at = None
                product.updated_at = now
                
                history = ProductStateHistory(
                    product_id=product.id,
                    from_state=old_state,
                    to_state=ProductState.AVAILABLE,
                    changed_by="system"
                )
                
                db.add(history)
                released_count += 1
    
    if released_count > 0:
        db.commit()
    
    return released_count

@router.post("/release-expired", status_code=status.HTTP_200_OK)
def release_expired_reservations_endpoint(
    db: Session = Depends(get_db)
):
    """
    Manual trigger to release expired reservations.
    """
    released_count = release_expired_reservations(db)
    
    return {
        "released_count": released_count,
        "message": f"Released {released_count} expired reservations"
    }


@router.get("/{product_id}", response_model=ProductResponse)
def get_transaction_product(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Return transaction-side product state for checkout synchronization."""
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )

    return product
