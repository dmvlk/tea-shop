from typing import TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.address import Address
    from app.models.order_item import OrderItem
    from app.models.user import User


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_price >= 0", name="ck_orders_total_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id"))
    status: Mapped[str] = mapped_column(String(20), default="created")
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_method: Mapped[str] = mapped_column(String(20), default="on_delivery")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="orders")
    address: Mapped["Address"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )