"""
Product router handling product creation, state transitions, and state history retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/products", tags=["products"])

# Product creation with initial state: Available (Only authenticated users can create products)
@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
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
    return product

#Changes the state of a product following valid transitions only (Available → Reserved → Sold).
@router.patch("/{product_id}/state", response_model=StateTransitionResponse)
def change_product_state(
    product_id: int,
    payload: StateTransitionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):

    # Lock the row to prevent race conditions (Tarea 2: atomic transitions)
    product = db.query(Product).filter(
        Product.id == product_id
    ).with_for_update().first()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )

    if product.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this product"
        )

    # Validate transition via state machine
    try:
        validate_transition(
            current=ProductState(product.state),
            target=payload.target_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

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
    """Returns the full state transition history of a product."""
    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )

    return product.state_history