from sqlalchemy.orm import Session
from app.models.user import User


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