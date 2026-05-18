from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.models.rating import Rating


class UserRepository:

    def create_user(self, db: Session, email: str, password_hash: str):
        user = User(
            email=email,
            password_hash=password_hash
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_user_by_email(self, db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()

    def update_avg_rating(self, db: Session, user_id: int):
        avg = db.query(func.avg(Rating.stars)).filter(Rating.to_user_id == user_id).scalar()
        user = self.get_user_by_id(db, user_id)
        if user:
            user.avg_rating = float(avg) if avg is not None else None
            db.commit()
            db.refresh(user)
        return user