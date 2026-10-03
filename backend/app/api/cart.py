from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.deps import get_current_user
from app.db.session import get_db
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import (
    CartItemCreate,
    CartItemRead,
    CartItemUpdate,
    CartRead
)

router = APIRouter(prefix="/api/cart", tags=["cart"])


async def _build_cart(db: AsyncSession, user_id: int) -> CartRead:
    stmt = (
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    read_items = [
        CartItemRead(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            product_name=item.product.name,
            price=item.product.price,
            subtotal=item.product.price * item.quantity,
        )
        for item in items
    ]

    total_items = sum(i.quantity for i in read_items)
    total_price = sum((i.subtotal for i in read_items), Decimal("0.00"))

    return CartRead(items=read_items, total_items=total_items, total_price=total_price)

@router.get("", response_model=CartRead)
async def get_cart(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _build_cart(db, user.id)

@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_item(
    data: CartItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    stmt = select(CartItem).where(
        CartItem.user_id == user.id,
        CartItem.product_id == data.product_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    new_quantity = (existing.quantity if existing else 0) + data.quantity
    if new_quantity > product.stock_quantity:
        raise HTTPException(
            status_code=409,
            detail=f"На складе только {product.stock_quantity} шт.",
        )

    if existing:
        existing.quantity = new_quantity
    else:
        db.add(CartItem(user_id=user.id, product_id=data.product_id, quantity=data.quantity))

    await db.commit()
    return await _build_cart(db, user.id)

@router.patch("/items/{item_id}", response_model=CartRead)
async def update_item(
    item_id: int,
    data: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    product = await db.get(Product, item.product_id)
    if data.quantity > product.stock_quantity:
        raise HTTPException(
            status_code=409,
            detail=f"На складе только {product.stock_quantity} шт.",
        )

    item.quantity = data.quantity
    await db.commit()
    return await _build_cart(db, user.id)

@router.delete("/items/{item_id}", response_model=CartRead)
async def delete_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    await db.delete(item)
    await db.commit()

    return await _build_cart(db, user.id)
