from typing import Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ProductState(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    SOLD = "Sold"


class ProductCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    condition: str = Field(default="new", min_length=1)

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
            normalized["condition"] = "new"
        return normalized


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, gt=0)
    condition: str | None = Field(default=None, min_length=1)

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

    model_config = ConfigDict(from_attributes=True)
