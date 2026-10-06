from httpx import AsyncClient
from tests.conftest import auth_header, login

#создание категории
async def test_create_category_as_admin(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    response = await client.post(
        "/api/categories",
        json={"name": "Зелёный", "slug": "green", "description": "Зелёные"},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    assert response.json()["slug"] == "green"

# создание категории без прав
async def test_create_category_as_user(client: AsyncClient, regular_user):
    token = await login(client, regular_user.email, "user123")
    response = await client.post(
        "/api/categories",
        json={"name": "test", "slug": "test", "description": None},
        headers=auth_header(token),
    )
    assert response.status_code == 403

# создание категории без токена
async def test_create_category_without_token(client: AsyncClient):
    response = await client.post(
        "/api/categories",
        json={"name": "test", "slug": "test", "description": None},
    )
    assert response.status_code == 401

# создание дупликата
async def test_create_duplicate_slug(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)

    await client.post(
        "/api/categories",
        json={"name": "test_A", "slug": "test", "description": None},
        headers=headers,
    )
    response = await client.post(
        "/api/categories",
        json={"name": "test_B", "slug": "test", "description": None},
        headers=headers,
    )
    assert response.status_code == 409

# просмотр категорий
async def test_list_categories_public(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    await client.post(
        "/api/categories",
        json={"name": "test", "slug": "test", "description": None},
        headers=auth_header(token),
    )

    response = await client.get("/api/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# несуществуюшая категория
async def test_get_category_404(client: AsyncClient):
    response = await client.get("/api/categories/99999")
    assert response.status_code == 404

# обновление категории
async def test_update_category(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)

    created = await client.post(
        "/api/categories",
        json={"name": "Old", "slug": "old", "description": None},
        headers=headers,
    )
    cat_id = created.json()["id"]

    response = await client.patch(
        f"/api/categories/{cat_id}",
        json={"name": "New"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New"

# удаление категории
async def test_delete_category(client: AsyncClient, admin_user):
    token = await login(client, admin_user.email, "admin123")
    headers = auth_header(token)
    
    created = await client.post(
        "/api/categories",
        json={"name": "Del", "slug": "del", "description": None},
        headers=headers,
    )
    cat_id = created.json()["id"]

    response = await client.delete(f"/api/categories/{cat_id}", headers=headers)
    assert response.status_code == 204

    assert (await client.get(f"/api/categories/{cat_id}")).status_code == 404
