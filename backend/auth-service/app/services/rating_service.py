import os
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.rating_repository import RatingRepository
from app.repositories.user_repository import UserRepository
from app.core.security import create_access_token

TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8000")


def _check_transaction_eligibility(transaction_id: int, from_user_email: str):
    try:
        service_token = create_access_token({"sub": from_user_email})
        headers = {"Authorization": f"Bearer {service_token}"}
        response = httpx.get(
            f"{TRANSACTION_SERVICE_URL}/products/history",
            headers=headers,
            timeout=3.0
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No se puede verificar la transacción"
            )
        data = response.json()
        transactions = data if isinstance(data, list) else data.get("items", data.get("transactions", []))
        transaction = next((t for t in transactions if t.get("id") == transaction_id), None)
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transacción no encontrada o no tienes acceso"
            )
        if transaction.get("status") != "completed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo se puede valorar una transacción completada"
            )
        is_buyer = transaction.get("buyer_id") == from_user_email
        is_seller = transaction.get("seller_id") == from_user_email
        if not is_buyer and not is_seller:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No eres parte de esta transacción"
            )
        return transaction
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede verificar la transacción"
        )


class RatingService:

    def __init__(self):
        self.rating_repository = RatingRepository()
        self.user_repository = UserRepository()

    def create_rating(self, db: Session, from_user_email: str, to_user_id: int, transaction_id: int, stars: int, review_text: str = None):
        if stars < 1 or stars > 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Las estrellas deben estar entre 1 y 5"
            )

        from_user = self.user_repository.get_user_by_email(db, from_user_email)
        if not from_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        to_user = self.user_repository.get_user_by_id(db, to_user_id)
        if not to_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario valorado no encontrado"
            )

        if to_user.id == from_user.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No puedes valorarte a ti mismo"
            )

        transaction = _check_transaction_eligibility(transaction_id, from_user_email)
        if transaction:
            counterparty_email = (
                transaction.get("seller_id")
                if transaction.get("buyer_id") == from_user_email
                else transaction.get("buyer_id")
            )
            if to_user.email != counterparty_email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puedes valorar a la otra parte de la transacción"
                )

        existing = self.rating_repository.get_rating_by_user_and_transaction(db, from_user.id, transaction_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya has valorado esta transacción"
            )

        rating = self.rating_repository.create_rating(
            db,
            from_user_id=from_user.id,
            to_user_id=to_user_id,
            transaction_id=transaction_id,
            stars=stars,
            review_text=review_text,
        )

        self.user_repository.update_avg_rating(db, to_user_id)

        return {
            "message": "valoración creada correctamente",
            "rating_id": rating.id
        }
