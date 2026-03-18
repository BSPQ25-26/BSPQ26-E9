from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.product import ProductCreate, ProductOut
from app.repositories.product_repository import ProductRepository
from app.auth import get_current_user
from app.db.session import get_db

router = APIRouter()

@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    product = ProductRepository.create_product(db, product_in, seller_id=current_user.id)
    return product
