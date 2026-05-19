from pydantic import BaseModel
from typing import Optional


class RatingCreate(BaseModel):
    to_user_id: int
    transaction_id: int
    stars: int
    review_text: Optional[str] = None
