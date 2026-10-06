from httpx import AsyncClient
from tests.conftest import auth_header, login


async def _product(client, admin_user, stock=10):
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
            "stock_quantity": stock,
            "weight_grams": 100,
            "origin": None,
            "image_url": None,
            "category_id": cat.json()["id"],
        },
        headers=admin_headers,
    )
    return product.json()


async def _address(client, headers):
    response = await client.post(
        "/api/addresses",
        json={
            "city": "Москва",
            "street": "Первая",
            "building": "10",
            "apartment": "5",
            "is_default": True,
        },
        headers=headers,
    )
    return response.json()["id"]

# создание заказа
async def test_create_order(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    address_id = await _address(client, headers)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers=headers,
    )

    response = await client.post(
        "/api/orders",
        json={"address_id": address_id},
        headers=headers,
    )
    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "created"
    assert order["total_price"] == "1000.00"
    assert len(order["items"]) == 1

    cart = await client.get("/api/cart", headers=headers)
    assert cart.json()["items"] == []

    p = await client.get(f"/api/products/{product['id']}")
    assert p.json()["stock_quantity"] == 8

# заказ с пустой корзиной
async def test_create_order_empty_cart(client: AsyncClient, regular_user):
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    address_id = await _address(client, headers)
    response = await client.post(
        "/api/orders",
        json={"address_id": address_id},
        headers=headers,
    )
    assert response.status_code == 400

# заказ на адрес другого пользователя
async def test_create_order_foreign_address(client: AsyncClient, regular_user, admin_user):
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)

    admin_token = await login(client, admin_user.email, "admin123")
    admin_address_id = await _address(client, auth_header(admin_token))

    response = await client.post(
        "/api/orders",
        json={"address_id": admin_address_id},
        headers=headers,
    )
    assert response.status_code == 404

# попытка заказа при нехватке на складе
async def test_create_order_no_stock(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user, stock=1)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)
    address_id = await _address(client, headers)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )

    admin_token = await login(client, admin_user.email, "admin123")
    await client.patch(
        f"/api/products/{product['id']}",
        json={"stock_quantity": 0},
        headers=auth_header(admin_token),
    )

    response = await client.post(
        "/api/orders",
        json={"address_id": address_id},
        headers=headers,
    )
    assert response.status_code == 409

# список заказов
async def test_list_orders(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)
    address_id = await _address(client, headers)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    await client.post("/api/orders", json={"address_id": address_id}, headers=headers)

    response = await client.get("/api/orders", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

# смена статуса
async def test_update_status(client: AsyncClient, regular_user, admin_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)
    address_id = await _address(client, headers)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    order_resp = await client.post(
        "/api/orders", json={"address_id": address_id}, headers=headers
    )
    order_id = order_resp.json()["id"]

    admin_token = await login(client, admin_user.email, "admin123")
    response = await client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "paid"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paid"

# недопустимый статус
async def test_update_status_bad_value(client: AsyncClient, admin_user, regular_user):
    product = await _product(client, admin_user)
    token = await login(client, regular_user.email, "user123")
    headers = auth_header(token)
    address_id = await _address(client, headers)

    await client.post(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    order_resp = await client.post(
        "/api/orders", json={"address_id": address_id}, headers=headers
    )
    order_id = order_resp.json()["id"]

    admin_token = await login(client, admin_user.email, "admin123")
    response = await client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "nonsense"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 400
