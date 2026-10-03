from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    address_id: int
    payment_method: str = Field(default="on_delivery", max_length=20)

class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    price_at_purchase: Decimal

class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    address_id: int
    status: str
    total_price: Decimal
    payment_method: str
    created_at: datetime
    items: list[OrderItemRead]

class OrderStatusUpdate(BaseModel):
    status: str = Field(max_length=20)
