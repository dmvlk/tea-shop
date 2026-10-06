from httpx import AsyncClient
from tests.conftest import auth_header, login


async def _category(client, headers, slug="green"):
    response = await client.post(
        "/api/categories",
        json={"name": slug.title(), "slug": slug, "description": None},
        headers=headers,
    )
    return response.json()["id"]


async def _product(client, headers, category_id,
                   name="Лунцзин", price="1200.00",
                   stock=10, description="Зелёный чай"):
    response = await client.post(
        "/api/products",
        json={
            "name": name,
            "description": description,
            "price": price,
            "stock_quantity": stock,
            "weight_grams": 100,
            "origin": "Китай",
            "image_url": None,
            "category_id": category_id,
        },
        headers=headers,
    )
    return response.json()

# создание товара
async def test_create_product(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    product = await _product(client, headers, cat_id)
    assert product["name"] == "Лунцзин"
    assert product["stock_quantity"] == 10

# создание товара без прав
async def test_create_product_as_user(client: AsyncClient, regular_user, admin_user):
    admin_token = await login(client, admin_user.email, "admin123")
    cat_id = await _category(client, auth_header(admin_token))

    user_token = await login(client, regular_user.email, "user123")
    response = await client.post(
        "/api/products",
        json={
            "name": "test",
            "description": None,
            "price": "100.00",
            "stock_quantity": 1,
            "weight_grams": 10,
            "origin": None,
            "image_url": None,
            "category_id": cat_id,
        },
        headers=auth_header(user_token),
    )
    assert response.status_code == 403

# товар с несуществующей категорией
async def test_create_product_bad_category(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    response = await client.post(
        "/api/products",
        json={
            "name": "test",
            "description": None,
            "price": "100.00",
            "stock_quantity": 1,
            "weight_grams": 10,
            "origin": None,
            "image_url": None,
            "category_id": 99999,
        },
        headers=auth_header(token),
    )
    assert response.status_code == 400

# отрицательная цена
async def test_create_product_negative_price(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    response = await client.post(
        "/api/products",
        json={
            "name": "test",
            "description": None,
            "price": "-100.00",
            "stock_quantity": 1,
            "weight_grams": 10,
            "origin": None,
            "image_url": None,
            "category_id": cat_id,
        },
        headers=headers,
    )
    assert response.status_code == 422

# пагинация
async def test_list_products_pagination(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    for i in range(5):
        await _product(client, headers, cat_id, name=f"Товар {i}")

    response = await client.get("/api/products?page=1&size=2")
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["size"] == 2

    response = await client.get("/api/products?page=3&size=2")
    assert len(response.json()["items"]) == 1

# фильтр по категории
async def test_list_products_by_category(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat1 = await _category(client, headers, slug="cat1")
    cat2 = await _category(client, headers, slug="cat2")

    await _product(client, headers, cat1, name="test_A")
    await _product(client, headers, cat2, name="test_B")

    response = await client.get(f"/api/products?category_id={cat1}")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "test_A"

# поиск по названию
async def test_search_by_name(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    await _product(client, headers, cat_id, name="Лунцзин")
    await _product(client, headers, cat_id, name="Пуэр")

    response = await client.get("/api/products?search=лун")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Лунцзин"

# поиск по описанию
async def test_search_by_description(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    await _product(client, headers, cat_id, name="Чай",
                   description="Аромат Ханчжоу и жасмина")

    response = await client.get("/api/products?search=Ханчжоу")
    assert response.json()["total"] == 1

# фильтр по цене
async def test_filter_by_price(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    await _product(client, headers, cat_id, name="Дешёвый", price="100.00")
    await _product(client, headers, cat_id, name="Дорогой", price="2000.00")

    response = await client.get("/api/products?min_price=1000")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Дорогой"

# только в наличии
async def test_filter_in_stock(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    await _product(client, headers, cat_id, name="Есть", stock=5)
    await _product(client, headers, cat_id, name="Нет", stock=0)

    response = await client.get("/api/products?in_stock=true")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Есть"

# сортировка
async def test_ordering(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)

    await _product(client, headers, cat_id, name="test_B", price="500.00")
    await _product(client, headers, cat_id, name="test_A", price="1500.00")

    response = await client.get("/api/products?ordering=-price")
    items = response.json()["items"]
    assert items[0]["name"] == "test_A"
    assert items[1]["name"] == "test_B"

# обновление товара
async def test_update_product(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)
    product = await _product(client, headers, cat_id)

    response = await client.patch(
        f"/api/products/{product['id']}",
        json={"price": "999.00"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["price"] == "999.00"

# удаление товара
async def test_delete_product(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    cat_id = await _category(client, headers)
    product = await _product(client, headers, cat_id)

    response = await client.delete(f"/api/products/{product['id']}", headers=headers)
    assert response.status_code == 204
    assert (await client.get(f"/api/products/{product['id']}")).status_code == 404
