from httpx import AsyncClient
from tests.conftest import auth_header, login

async def _second_user(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "second@example.com",
            "full_name": "Second",
            "password": "secret123",
        },
    )
    token = await login(client, "second@example.com", "secret123")
    return auth_header(token)


async def _product(client, admin_user):
    admin_token = await login(client, admin_user.email, "admin123")
    admin_headers = auth_header(admin_token)
    cat = await client.post(
        "/api/categories",
        json={"name": "test", "slug": "test", "description": None},
        headers=admin_headers,
    )
    product = await client.post(
        "/api/products",
        json={
            "name": "Чай",
            "description": None,
            "price": "500.00",
            "stock_quantity": 10,
            "weight_grams": 100,
            "origin": None,
            "image_url": None,
            "category_id": cat.json()["id"],
        },
        headers=admin_headers,
    )
    return product.json()


# чужой заказ
async def test_foreign_order(client: AsyncClient, regular_user, admin_user):
    token1 = await login(client, regular_user.email, "user123")
    headers1 = auth_header(token1)

    address = await client.post(
        "/api/addresses",
        json={"city": "test", "street": "test", "building": "1", "is_default": True},
        headers=headers1,
    )
    address_id = address.json()["id"]

    product = await _product(client, admin_user)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers1,
    )
    order = await client.post(
        "/api/orders",
        json={"address_id": address_id},
        headers=headers1,
    )
    order_id = order.json()["id"]

    headers2 = await _second_user(client)
    response = await client.get(f"/api/orders/{order_id}", headers=headers2)
    assert response.status_code == 404


# чужая позиция корзины
async def test_foreign_cart_item(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)

    token1 = await login(client, regular_user.email, "user123")
    headers1 = auth_header(token1)
    add = await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers1,
    )
    item_id = add.json()["items"][0]["id"]

    headers2 = await _second_user(client)

    response = await client.patch(
        f"/api/cart/items/{item_id}",
        json={"quantity": 5},
        headers=headers2,
    )
    assert response.status_code == 404

    response = await client.delete(
        f"/api/cart/items/{item_id}",
        headers=headers2,
    )
    assert response.status_code == 404


# чужой адрес
async def test_foreign_address(client: AsyncClient, regular_user):
    token1 = await login(client, regular_user.email, "user123")
    headers1 = auth_header(token1)

    address = await client.post(
        "/api/addresses",
        json={"city": "test", "street": "test", "building": "1", "is_default": True},
        headers=headers1,
    )
    address_id = address.json()["id"]

    headers2 = await _second_user(client)

    response = await client.patch(
        f"/api/addresses/{address_id}",
        json={"city": "SPb"},
        headers=headers2,
    )
    assert response.status_code == 404