from httpx import AsyncClient
from tests.conftest import auth_header, login


async def _product(client, admin_user, stock=10):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)

    cat = await client.post(
        "/api/categories",
        json={"name": "test", "slug": "test", "description": None},
        headers=headers,
    )

    product = await client.post(
        "/api/products",
        json={
            "name": "Чай",
            "description": None,
            "price": "500.00",
            "stock_quantity": stock,
            "weight_grams": 100,
            "origin": None,
            "image_url": None,
            "category_id": cat.json()["id"],
        },
        headers=headers,
    )
    return product.json()

# пустая корзина
async def test_cart_empty(client: AsyncClient, regular_user):
    token = await login(client, regular_user.email, "user123")
    response = await client.get("/api/cart", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["total_price"] == "0.00"

# корзина без токена
async def test_cart_without_token(client: AsyncClient):
    response = await client.get("/api/cart")
    assert response.status_code == 401

# добавление товара
async def test_add_item(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")

    response = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total_items"] == 2
    assert data["total_price"] == "1000.00"

# добавление 2 товаров
async def test_add_same_item(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    response = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers=headers,
    )
    assert response.json()["total_items"] == 3

# больше, чем на складе
async def test_add_item_over_stock(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user, stock=3)
    token = await login(client, regular_user.email, "user123")
    
    response = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 5},
        headers=auth_header(token),
    )
    assert response.status_code == 409

# несуществующий товар
async def test_add_unknown_product(client: AsyncClient, regular_user):
    token = await login(client, regular_user.email, "user123")
    response = await client.post(
        "/api/cart/items",
        json={"product_id": 99999, "quantity": 1},
        headers=auth_header(token),
    )
    assert response.status_code == 404

# изменение количества
async def test_update_item(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    add = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    item_id = add.json()["items"][0]["id"]

    response = await client.patch(
        f"/api/cart/items/{item_id}",
        json={"quantity": 5},
        headers=headers,
    )
    assert response.json()["total_items"] == 5

# количество больше остатка
async def test_update_item_over_stock(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user, stock=3)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    add = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    item_id = add.json()["items"][0]["id"]

    response = await client.patch(
        f"/api/cart/items/{item_id}",
        json={"quantity": 99},
        headers=headers,
    )
    assert response.status_code == 409

# удаление товара
async def test_delete_item(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    add = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    item_id = add.json()["items"][0]["id"]

    response = await client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert response.json()["items"] == []