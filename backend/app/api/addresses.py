from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_current_user
from app.db.session import get_db
from app.models.address import Address
from app.models.user import User
from app.schemas.address import (
    AddressCreate,
    AddressRead,
    AddressUpdate
)

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressRead])
async def list_addresses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Address)
        .where(Address.user_id == user.id)
        .order_by(Address.is_default.desc(), Address.id)
    )

    return result.scalars().all()

@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(
    data: AddressCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.is_default:
        await db.execute(
            update(Address).where(Address.user_id == user.id).values(is_default=False)
        )

    address = Address(user_id=user.id, **data.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)

    return address

@router.patch("/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: int,
    data: AddressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, address_id)
    if not address or address.user_id != user.id:
        raise HTTPException(status_code=404, detail="Адрес не найден")

    payload = data.model_dump(exclude_unset=True)

    if payload.get("is_default"):
        await db.execute(
            update(Address)
            .where(Address.user_id == user.id, Address.id != address_id)
            .values(is_default=False)
        )

    for field, value in payload.items():
        setattr(address, field, value)

    await db.commit()
    await db.refresh(address)

    return address

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = await db.get(Address, address_id)
    if not address or address.user_id != user.id:
        raise HTTPException(status_code=404, detail="Адрес не найден")

    await db.delete(address)
    await db.commit()