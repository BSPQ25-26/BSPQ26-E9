
from fastapi import APIRouter, Depends, HTTPException, status, Path, File, UploadFile, Query
from sqlalchemy.orm import Session
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate, ProductState, ProductCondition
from app.repositories.product_repository import ProductRepository
from app.auth import get_current_user
from app.db.session import get_db
from app.models.product import Product
import os
import uuid

router = APIRouter()

def _upload_to_supabase(contents: bytes, filename: str, content_type: str) -> str | None:
    """Upload file bytes to Supabase Storage via REST API and return the public URL."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "product-images")

    if not supabase_url or not key:
        return None

    try:
        import httpx
        upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
        response = httpx.post(
            upload_url,
            content=contents,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            timeout=30,
        )
        if response.status_code in (200, 201):
            return f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"
        return None
    except Exception:
        return None


@router.get("/products", response_model=list[ProductOut])
def list_products(
    state: ProductState | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    condition: ProductCondition | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot be greater than max_price")

    query = db.query(Product)

    if state is not None:
        query = query.filter(Product.state == state.value)
    if category is not None:
        query = query.filter(Product.category == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if condition is not None:
        query = query.filter(Product.condition == condition.value)

    return query.order_by(Product.id.asc()).all()

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

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGES = 8

# Local fallback (used only when Supabase Storage is not configured)
DEFAULT_UPLOAD_DIR = "/app/data/uploads" if os.path.isdir("/app/data") else "uploads"
UPLOAD_DIR = os.getenv("INVENTORY_UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
UPLOAD_URL_PREFIX = os.getenv("INVENTORY_UPLOAD_URL_PREFIX", "/uploads").rstrip("/")

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

    current_images = product.images or []
    if len(current_images) >= MAX_IMAGES:
        raise HTTPException(status_code=400, detail="Image limit exceeded")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Invalid file format")

    contents = file.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File too large")

    content_type_to_ext = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    file_ext = content_type_to_ext.get(file.content_type, "jpg")
    filename = f"{uuid.uuid4()}.{file_ext}"

    # Try Supabase Storage first; fall back to local disk
    file_url = _upload_to_supabase(contents, filename, file.content_type)

    if file_url is None:
        # Local fallback
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(contents)
        file_url = f"{UPLOAD_URL_PREFIX}/{filename}"

    product.images = current_images + [file_url]
    db.commit()
    db.refresh(product)

    return {"image_url": file_url}
