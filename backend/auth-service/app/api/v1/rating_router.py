from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.rating import RatingCreate
from app.services.rating_service import RatingService
from app.api.deps import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/ratings", tags=["ratings"])

rating_service = RatingService()


@router.post("")
def create_rating(data: RatingCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return rating_service.create_rating(
        db,
        from_user_email=current_user,
        to_user_id=data.to_user_id,
        transaction_id=data.transaction_id,
        stars=data.stars,
        review_text=data.review_text,
    )
