
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.repositories.product_repository import ProductRepository
from app.auth import get_current_user
from app.db.session import get_db
from app.models.product import Product

router = APIRouter()

@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return ProductRepository.create_product(db, product_in, seller_id=current_user)

@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    return product

@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int = Path(...),
    product_in: ProductUpdate = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    updates = product_in.model_dump(exclude_unset=True) if product_in else {}
    if not updates:
        raise HTTPException(status_code=422, detail="No update data provided")

    product = ProductRepository.update_product(db, product, updates)
    return product

@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    ProductRepository.delete_product(db, product)
    return None
