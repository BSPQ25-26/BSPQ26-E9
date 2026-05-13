"""
Product router handling product creation, state transitions, and state history retrieval.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Product, ProductStateHistory
from app.schemas import (
    ProductCreate, ProductResponse,
    StateTransitionRequest, StateTransitionResponse,
    StateHistoryResponse
)
from app.services.state_machine import validate_transition, ProductState
from app.api.deps import get_current_user_id
# Sprint 3: Error handling audit 
from app.core.exceptions import (
    ProductNotFoundException,
    ProductForbiddenException,
    InvalidStateTransitionException
)

#Sprint 3: Structured logging
from app.core.logging import get_logger, log_request, log_result, log_error  

logger = get_logger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Product creation with initial state: Available (Only authenticated users can create products)
@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    #Sprint 3: Structured logging - Creates a new product with initial state available 
    log_request(logger, "POST /products", user_id, title=payload.title, price=payload.price)

    product = Product(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        price=payload.price,
        state=ProductState.AVAILABLE,
        owner_id=user_id
    )
    db.add(product)
    db.flush()  # get product.id before commit

    # Record initial state in history
    history = ProductStateHistory(
        product_id=product.id,
        from_state=None,
        to_state=ProductState.AVAILABLE,
        changed_by=user_id
    )
    db.add(history)
    db.commit()
    db.refresh(product)

    log_result(logger, "POST /products", user_id, product_id=product.id)
    return product

#Changes the state of a product following valid transitions only (Available → Reserved → Sold).
@router.patch("/{product_id}/state", response_model=StateTransitionResponse)
def change_product_state(
    product_id: int,
    payload: StateTransitionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    #Sprint 3: Structured logging - Changes the state of a product following valid transitions only (Available → Reserved → Sold)
    log_request(logger, f"PATCH /products/{product_id}/state", user_id, target_state=str(payload.target_state))
    # Lock the row to prevent race conditions (Tarea 2: atomic transitions)
    product = db.query(Product).filter(
        Product.id == product_id
    ).with_for_update().first()

    
    if product is None:
        #Sprint 3: Sructured logging
        log_error(logger, f"PATCH /products/{product_id}/state", user_id, error="Product not found")
        #Sprint 3: Error handlig audit - replace generic HTTPException with specific exceptions
        raise ProductNotFoundException(product_id)

    if product.owner_id != user_id:
        #Sprint 3: Structured logging
        log_error(logger, f"PATCH /products/{product_id}/state", user_id, error="Forbidden: Not the owner")
        #Sprint 3: Error handling audit - replace generic HTTPException with specific exceptions
        raise ProductForbiddenException("You are not the owner of this product")

    # Validate transition via state machine
    try:
        validate_transition(
            current=ProductState(product.state),
            target=payload.target_state
        )
    except ValueError:
        #Sprint 3: Structured logging
        log_error(logger, f"PATCH /products/{product_id}/state", user_id, error=f"Invalid transition {product.state} → {payload.target_state}")
        #Sprint 3: Error handling audit - replace generic HTTPException with specific exceptions
        raise InvalidStateTransitionException(product.state, payload.target_state) 

    from_state = product.state
    product.state = payload.target_state
    product.updated_at = datetime.now(timezone.utc)

    # Record change in history (Tarea 4: state history logging)
    history = ProductStateHistory(
        product_id=product.id,
        from_state=from_state,
        to_state=payload.target_state,
        changed_by=user_id
    )
    db.add(history)
    db.commit()
    db.refresh(product)

    #Sprint 3: Structured logging
    log_result(logger, f"PATCH /products/{product_id}/state", user_id, from_state=from_state, to_state=str(product.state))
    return StateTransitionResponse(
        product_id=product.id,
        from_state=from_state,
        to_state=product.state,
        changed_at=history.changed_at
    )

#Returns the full state transition history of a product. (Only authenticated users can view the history)
@router.get("/{product_id}/history", response_model=list[StateHistoryResponse])
def get_state_history(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    #Sprint 3: Structured logging - Returns the full state transition history of a product
    log_request(logger, f"GET /products/{product_id}/history", user_id)

    """Returns the full state transition history of a product."""
    product = db.query(Product).filter(Product.id == product_id).first()

    #Sprint 3: Error handling audit - replace generic HTTPException with specific exceptions
    if product is None:
        raise ProductNotFoundException(product_id)

    #Sprint 3: Structured logging
    log_result(logger, f"GET /products/{product_id}/history", user_id, entries=len(product.state_history))  # ← SPRINT 3 LOG
    return product.state_history