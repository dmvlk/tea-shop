from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.address import Address
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderItemRead,
    OrderRead,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])

ALLOWED_STATUSES = {"created", "paid", "shipped", "delivered", "cancelled"}


def _to_read(order: Order) -> OrderRead:
    items = [
        OrderItemRead(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            price_at_purchase=item.price_at_purchase,
        )
        for item in order.items
    ]
    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        address_id=order.address_id,
        status=order.status,
        total_price=order.total_price,
        payment_method=order.payment_method,
        created_at=order.created_at,
        items=items,
    )

@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, data.address_id)
    if not address or address.user_id != user.id:
        raise HTTPException(status_code=404, detail="Адрес не найден")

    cart_stmt = (
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == user.id)
    )
    cart_items = (await db.execute(cart_stmt)).scalars().all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    total_price = Decimal("0.00")

    for item in cart_items:
        product = await db.get(
            Product, item.product_id, with_for_update=True
        )
        if not product or product.stock_quantity < item.quantity:
            available = product.stock_quantity if product else 0
            name = product.name if product else "товар"
            raise HTTPException(
                status_code=409,
                detail=f"«{name}»: на складе только {available} шт.",
            )
        total_price += product.price * item.quantity

    order = Order(
        user_id=user.id,
        address_id=address.id,
        status="created",
        total_price=total_price,
        payment_method=data.payment_method,
    )
    db.add(order)
    await db.flush()

    for item in cart_items:
        product = await db.get(Product, item.product_id)
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_purchase=product.price,
            )
        )
        product.stock_quantity -= item.quantity
        await db.delete(item)

    await db.commit()

    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order.id)
    )
    order = (await db.execute(stmt)).scalar_one()

    return _to_read(order)


@router.get("", response_model=list[OrderRead])
async def list_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = (await db.execute(stmt)).scalars().all()

    return [_to_read(o) for o in orders]

@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = (await db.execute(stmt)).scalar_one_or_none()

    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    return _to_read(order)

@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_status(
    order_id: int,
    data: OrderStatusUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if data.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус. Разрешены: {', '.join(sorted(ALLOWED_STATUSES))}",
        )

    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order.status = data.status
    await db.commit()
    await db.refresh(order)

    return _to_read(order)
