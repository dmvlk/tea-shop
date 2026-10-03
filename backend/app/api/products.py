from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_current_admin
from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    PaginatedProducts,
)

router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=PaginatedProducts)
async def list_products(
    category_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool | None = Query(default=None),
    ordering: str = Query(default="name"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Product)
    count_stmt = select(func.count()).select_from(Product)

    filters = []

    if category_id is not None:
        filters.append(Product.category_id == category_id)

    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )

    if min_price is not None:
        filters.append(Product.price >= min_price)

    if max_price is not None:
        filters.append(Product.price <= max_price)

    if in_stock is True:
        filters.append(Product.stock_quantity > 0)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    allowed_ordering = {
        "name": Product.name,
        "-name": Product.name.desc(),
        "price": Product.price,
        "-price": Product.price.desc(),
        "created_at": Product.created_at,
        "-created_at": Product.created_at.desc(),
        "weight": Product.weight_grams,
        "-weight": Product.weight_grams.desc(),
    }

    order_by = allowed_ordering.get(ordering, Product.name)
    stmt = stmt.order_by(order_by)

    offset = (page - 1) * size
    stmt = stmt.offset(offset).limit(size)

    total = (await db.execute(count_stmt)).scalar_one()
    items = (await db.execute(stmt)).scalars().all()
    
    return PaginatedProducts(
        items=list(items),
        total=total,
        page=page,
        size=size,
    )

@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    category = await db.get(Category, data.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Категория не найдена")

    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    payload = data.model_dump(exclude_unset=True)

    if "category_id" in payload:
        category = await db.get(Category, payload["category_id"])
        if not category:
            raise HTTPException(status_code=400, detail="Категория не найдена")
    for field, value in payload.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    await db.delete(product)
    await db.commit()
