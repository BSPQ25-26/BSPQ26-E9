
from typing import Any, Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ProductState(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    SOLD = "Sold"

class ProductCondition(str, Enum):
    NEW = "New"
    LIKE_NEW = "Like New"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"

class ProductCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    condition: ProductCondition = Field(default=ProductCondition.NEW)
    transaction_product_id: Optional[int] = Field(default=None)

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if normalized.get("title") is None and normalized.get("name") is not None:
            normalized["title"] = normalized["name"]
        if normalized.get("condition") is None:
            normalized["condition"] = ProductCondition.NEW
        return normalized

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = Field(default=None, min_length=1)
    price: Optional[float] = Field(default=None, gt=0)
    condition: Optional[ProductCondition] = Field(default=None)
    transaction_product_id: Optional[int] = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if normalized.get("title") is None and normalized.get("name") is not None:
            normalized["title"] = normalized.pop("name")
        else:
            normalized.pop("name", None)
        normalized.pop("stock", None)
        return normalized


class ProductOut(BaseModel):
    id: int
    title: str
    description: str
    category: str
    price: float
    condition: str
    state: ProductState
    seller_id: str
    created_at: datetime
    images: List[str] = []
    transaction_product_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
