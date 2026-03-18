
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from app.schemas.product import ProductCreate, ProductOut
from app.repositories.product_repository import ProductRepository
from app.auth import get_current_user
from app.db.session import get_db
from app.models.product import Product

router = APIRouter()

@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        # Accept both 'name' and 'title', and require category/condition
        title = product_in.get("title") or product_in.get("name")
        if not title or not isinstance(title, str) or not title.strip():
            raise HTTPException(status_code=422, detail="title (or name) is required and must be a non-empty string")
        category = product_in.get("category") or "general"
        condition = product_in.get("condition") or "new"
        description = product_in.get("description")
        price = product_in.get("price")
        if description is None or price is None:
            raise HTTPException(status_code=422, detail="description and price are required")
        product_obj = ProductCreate(
            title=title,
            description=description,
            category=category,
            price=price,
            condition=condition
        )
        product = ProductRepository.create_product(db, product_obj, seller_id=current_user)
        return product
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=422, detail=f"{str(e)}\n{tb}")

@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
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
    product_in: dict = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not product_in:
        raise HTTPException(status_code=422, detail="No update data provided")
    product = ProductRepository.update_product(db, product, product_in)
    return product

@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(product)
    db.commit()
    return None
