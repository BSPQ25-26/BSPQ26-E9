from sqlalchemy.orm import Session
from app.models.rating import Rating


class RatingRepository:

    def create_rating(self, db: Session, from_user_id: int, to_user_id: int, transaction_id: int, stars: int, review_text: str = None):
        rating = Rating(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            transaction_id=transaction_id,
            stars=stars,
            review_text=review_text,
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)
        return rating

    def get_rating_by_user_and_transaction(self, db: Session, from_user_id: int, transaction_id: int):
        return db.query(Rating).filter(
            Rating.from_user_id == from_user_id,
            Rating.transaction_id == transaction_id
        ).first()

    def get_ratings_for_user(self, db: Session, to_user_id: int, skip: int = 0, limit: int = 20):
        return db.query(Rating).filter(
            Rating.to_user_id == to_user_id
        ).offset(skip).limit(limit).all()
