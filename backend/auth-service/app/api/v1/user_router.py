import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.repositories.rating_repository import RatingRepository
from app.core.security import create_access_token
from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])

user_repository = UserRepository()
rating_repository = RatingRepository()

INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8000")


def _get_active_listing_count(seller_email: str) -> int:
    try:
        service_token = create_access_token({"sub": "service@internal"})
        headers = {"Authorization": f"Bearer {service_token}"}
        response = httpx.get(f"{INVENTORY_SERVICE_URL}/api/v1/products", headers=headers, timeout=3.0)
        if response.status_code == 200:
            products = response.json()
            return sum(
                1 for p in products
                if p.get("seller_id") == seller_email and p.get("state") in ("Available", "Reserved")
            )
    except Exception:
        pass
    return 0


@router.get("/{user_id}/profile")
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return {
        "username": user.email,
        "member_since": user.created_at,
        "avg_rating": user.avg_rating,
        "active_listing_count": _get_active_listing_count(user.email)
    }


@router.get("/{user_id}/ratings")
def get_user_ratings(user_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    ratings = rating_repository.get_ratings_for_user(db, user_id, skip=skip, limit=limit)
    result = []
    for r in ratings:
        reviewer = user_repository.get_user_by_id(db, r.from_user_id)
        result.append({
            "reviewer_username": reviewer.email if reviewer else None,
            "stars": r.stars,
            "review_text": r.review_text,
            "created_at": r.created_at
        })
    return result
