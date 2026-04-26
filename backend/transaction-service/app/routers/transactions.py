"""
Transaction router: Product reservation and purchase endpoints.
Handles wallet-based purchases with atomic transactions and state transitions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timezone
from decimal import Decimal

from app.database import get_db
from app.models import Product, WalletLedger, Transaction, ProductStateHistory
from app.schemas import (
    TransactionRequest, TransactionResponse,
    TransactionHistoryResponse, TransactionHistoryListResponse,
    StateTransitionResponse
)
from app.services.state_machine import ProductState, validate_transition, is_valid_transition
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/products", tags=["transactions"])


# Sprint 2: Product Reservation Endpoint

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
    # Get product and validate existence
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    # Sprint 2: Ownership Guard: A user cannot reserve their own product
    if product.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reserve your own product"
        )
    
    # Validate state transition (Available → Reserved)
    if not is_valid_transition(product.state, ProductState.RESERVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {product.state} to {ProductState.RESERVED}"
        )
    
    # Update product state
    old_state = product.state
    product.state = ProductState.RESERVED
    product.reserved_at = datetime.now(timezone.utc)  # TIMEOUT RELEASE: Record when reserved
    product.updated_at = datetime.now(timezone.utc)
    
    # Record state change in history
    history = ProductStateHistory(
        product_id=product.id,
        from_state=old_state,
        to_state=ProductState.RESERVED,
        changed_by=user_id
    )
    
    db.add(history)
    db.commit()
    db.refresh(product)
    
    #return confirmation
    return {
        "product_id": product.id,
        "state": product.state,
        "reserved_by": user_id,
        "updated_at": product.updated_at
    }


#Sprint 2: Purchase Endpoint

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
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    # Ownership Guard: cannot buy own product
    if product.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot purchase your own product"
        )
    
    # State validation: product must be Available or Reserved
    if product.state not in [ProductState.AVAILABLE, ProductState.RESERVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product is {product.state} and cannot be purchased"
        )
    
    # Fund Validation: check buyer's wallet balance
    buyer_ledger = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id == user_id)
        .order_by(desc(WalletLedger.id))
        .first()
    )
    
    buyer_balance = Decimal(str(buyer_ledger.balance_after)) if buyer_ledger else Decimal("0.00")
    product_price = Decimal(str(product.price))
    
    #Fund validation: check if buyer has enough money
    if buyer_balance < product_price:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient funds: balance {buyer_balance}, needed {product_price}"
        )
    
    # String 2: Atomic purchase flow
    #Atomic: If any of the steps fails all changes are rolled back to maintain balance integrity
    try:
        # 1) DEBIT buyer's wallet
        # BALANCE INTEGRITY: Create NEW entry, never UPDATE
        buyer_new_balance = buyer_balance - product_price
        buyer_debit = WalletLedger(
            user_id=user_id,
            amount=-product_price,  # Negative = money OUT
            transaction_type="PURCHASE",
            description=f"Sale of product {product_id}",
            balance_after=buyer_new_balance,  # Final balance after debit
            created_at=datetime.now(timezone.utc)
        )
        db.add(buyer_debit)
        
        # 2) CREDIT seller's wallet
        # BALANCE INTEGRITY: Create NEW entry, never UPDATE
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
            amount=product_price,  # Positive = money IN
            description=f"Sale of product {product_id}",
            transaction_type="SALE",
            balance_after=seller_new_balance,  # Final balance after credit
            created_at=datetime.now(timezone.utc)
        )
        db.add(seller_credit)
        
        # 3) Update product state to Sold
        old_state = product.state
        product.state = ProductState.SOLD
        product.reserved_at = None  # TIMEOUT RELEASE: Clear reservation timestamp after purchase
        product.updated_at = datetime.now(timezone.utc)
        
        # 4) Record state transition in history
        history = ProductStateHistory(
            product_id=product.id,
            from_state=old_state,
            to_state=ProductState.SOLD,
            changed_by=user_id
        )
        db.add(history)
        
        # 5) Create transaction (Transaction Record)
        transaction = Transaction(
            buyer_id=user_id,
            seller_id=product.owner_id,
            product_id=product.id,
            amount=product_price,
            created_at=datetime.now(timezone.utc)
        )
        db.add(transaction)
        
        db.commit() #Save 
        db.refresh(transaction)

    #In case of error rollback     
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
        status="completed",
        created_at=transaction.created_at,
        completed_at=transaction.created_at
    )


# String 2: Transaction History Endpoint --> GET /products/history
#Obtain all the trasnaction of a user as a buyer or a seller 
@router.get("/history", response_model=TransactionHistoryListResponse)
def get_transaction_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    role: str = Query("all", regex="^(buyer|seller|all)$", description="Filter by role"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get transaction history for authenticated user.
    Returns transaction history with product information.
    """
    # Build filter based on role
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
    
    # Count total
    total = db.query(Transaction).filter(filter_clause).count()
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get transactions
    transactions = (
        db.query(Transaction)
        .filter(filter_clause)
        .order_by(desc(Transaction.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )
    
    # Build response with product info
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
            status="completed",
            created_at=txn.created_at,
            completed_at=txn.created_at
        ))
    
    #Return paginated response
    return TransactionHistoryListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        per_page=per_page
    )


#String 2: Endpoint to obtain only the purchases of a user 
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
            status="completed",
            created_at=txn.created_at,
            completed_at=txn.created_at
        ))
    
    return TransactionHistoryListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        per_page=per_page
    )


#String 2: Endpoint to obtain only the sales of a user
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
            status="completed",
            created_at=txn.created_at,
            completed_at=txn.created_at
        ))
    
    return TransactionHistoryListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        per_page=per_page
    )


# Sprint 2: TIMEOUT RELEASE

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
    now = datetime.now()  # Use naive datetime (same as DB)
    
    # Find all RESERVED products where reserved_at is older than timeout
    expired_reservations = (
        db.query(Product)
        .filter(Product.state == ProductState.RESERVED)
        .filter(Product.reserved_at.isnot(None))
        .all()
    )
    
    released_count = 0
    
    for product in expired_reservations:
        # Calculate age of reservation
        if product.reserved_at:
            age_seconds = (now - product.reserved_at).total_seconds()
            
            # If older than timeout, release it
            if age_seconds > timeout_seconds:
                old_state = product.state
                product.state = ProductState.AVAILABLE
                product.reserved_at = None  # Clear reservation timestamp
                product.updated_at = now
                
                # Record state change in history
                history = ProductStateHistory(
                    product_id=product.id,
                    from_state=old_state,
                    to_state=ProductState.AVAILABLE,
                    changed_by="system"  # Changed by background task
                )
                
                db.add(history)
                released_count += 1
    
    if released_count > 0:
        db.commit()
    
    return released_count

#String 2: Endpoitn to realese expired reservation 
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
