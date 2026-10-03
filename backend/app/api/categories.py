from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_current_admin
from app.db.session import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate
)

router = APIRouter(prefix="/api/categories", tags=["categories"])

@router.get("", response_model=list[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()

@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category

@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    existing = await db.execute(select(Category).where(Category.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Категория с таким slug уже есть")

    category = Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    await db.delete(category)
    await db.commit()