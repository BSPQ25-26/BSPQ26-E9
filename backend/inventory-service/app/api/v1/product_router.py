
from fastapi import APIRouter, Depends, HTTPException, status, Path, File, UploadFile
from sqlalchemy.orm import Session
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.repositories.product_repository import ProductRepository
from app.auth import get_current_user
from app.db.session import get_db
from app.models.product import Product
import os
import uuid

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

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGES = 8

UPLOAD_DIR = "uploads"

@router.post("/products/{product_id}/images")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != current_user:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Validate image count
    current_images = product.images or []
    if len(current_images) >= MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Image limit exceeded")

    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Invalid file format")

    # Validate file size
    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File too large")

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Generate URL (simple version)
    file_url = f"/uploads/{filename}"

    # Save in DB
    product.images = current_images + [file_url]
    db.commit()
    db.refresh(product)

    return {"image_url": file_url}

