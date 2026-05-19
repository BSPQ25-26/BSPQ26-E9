from pydantic import BaseModel
from pydantic import Field
from typing import Optional


class RatingCreate(BaseModel):
    to_user_id: int
    transaction_id: int
    stars: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
