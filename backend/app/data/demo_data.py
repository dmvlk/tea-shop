# Демо-данные (категории, товары + тестовые админ и пользователь)
 
import asyncio
import json
from decimal import Decimal
from pathlib import Path
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.product import Product
from app.models.user import User                      # TODO: проверьте путь/имя модели
from app.core.security import hash_password           # TODO: проверьте путь/имя функции хеширования
 
 
DATA_FILE = Path(__file__).parent / "demo_data.json"
 
DEMO_USERS = [
    {"email": "admin@teashop.local", "full_name": "Администратор", "password": "Admin12345", "role": "admin"},
    {"email": "user@teashop.local", "full_name": "Анна Петрова", "password": "User12345", "role": "user"},
]
 
 
def load_data() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)
 
async def seed():
    data = load_data()
 
    async with AsyncSessionLocal() as db:
        for item in DEMO_USERS:
            existing = await db.execute(select(User).where(User.email == item["email"]))
            if existing.scalar_one_or_none():
                print(f"= пользователь уже есть: {item['email']}")
                continue
            db.add(User(
                email=item["email"],
                full_name=item["full_name"],
                hashed_password=hash_password(item["password"]),  # TODO: имя поля (hashed_password / password_hash)
                role=item["role"],                                # TODO: если role — Enum, используйте UserRole.admin / .user
            ))
            print(f"+ пользователь: {item['email']} ({item['role']})")
 
        slug_to_category: dict[str, Category] = {}
        for item in data["categories"]:
            existing = await db.execute(
                select(Category).where(Category.slug == item["slug"])
            )
            category = existing.scalar_one_or_none()
 
            if category is None:
                category = Category(**item)
                db.add(category)
                await db.flush()
                print(f"+ категория: {category.name}")
            slug_to_category[item["slug"]] = category
 
 
        for item in data["products"]:
            existing = await db.execute(
                select(Product).where(Product.name == item["name"])
            )
            if existing.scalar_one_or_none():
                print(f"= товар уже есть: {item['name']}")
                continue
 
            category = slug_to_category[item["category_slug"]]
            product = Product(
                name=item["name"],
                description=item["description"],
                price=Decimal(item["price"]),
                stock_quantity=item["stock_quantity"],
                weight_grams=item["weight_grams"],
                origin=item["origin"],
                image_url=None,
                category_id=category.id,
            )
            db.add(product)
            print(f"+ товар: {product.name} ({product.price} ₽)")
 
        await db.commit()
 
if __name__ == "__main__":
    asyncio.run(seed())
