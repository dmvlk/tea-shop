from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    price: Decimal = Field(gt=0)
    stock_quantity: int = Field(ge=0)
    weight_grams: int = Field(gt=0)
    origin: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    category_id: int

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    weight_grams: int | None = Field(default=None, gt=0)
    origin: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    category_id: int | None = None

class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
