from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, gt=0)

class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)

class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    product_name: str
    price: Decimal
    subtotal: Decimal

class CartRead(BaseModel):
    items: list[CartItemRead]
    total_items: int
    total_price: Decimal