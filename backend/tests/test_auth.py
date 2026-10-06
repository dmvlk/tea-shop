from httpx import AsyncClient
from tests.conftest import auth_header, login

# успешная регистрация
async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "full_name": "New User",
            "password": "secret123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["role"] == "user"
    assert "password" not in data
    assert "hashed_password" not in data

# регистрация на уже зарегистрированный емейл
async def test_register_duplicate_email(client: AsyncClient, regular_user):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": regular_user.email,
            "full_name": "Dup",
            "password": "secret123",
        },
    )
    assert response.status_code == 409

# некорректный емейл
async def test_register_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "full_name": "X", "password": "secret123"},
    )
    assert response.status_code == 422

# некорректный пароль
async def test_register_short_password(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "a@a.com", "full_name": "test", "password": "123"},
    )
    assert response.status_code == 422

# успешный вход
async def test_login_success(client: AsyncClient, regular_user):
    response = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "user123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

# попытка входа с неверным паролем
async def test_login_wrong_password(client: AsyncClient, regular_user):
    response = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "wrong"},
    )
    assert response.status_code == 401

# вход с незарегистрированного емейла
async def test_login_unknown_email(client: AsyncClient):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
    )
    assert response.status_code == 401

# попытка получить данные без токена
async def test_me_without_token(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401

# попытка полусить данные с токеном
async def test_me_with_token(client: AsyncClient, regular_user):
    token = await login(client, regular_user.email, "user123")
    response = await client.get("/api/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["email"] == regular_user.email

# обновление токена
async def test_refresh(client: AsyncClient, regular_user):
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "user123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

# использования access токена как refresh
async def test_refresh_with_access_token_fails(client: AsyncClient, regular_user):
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "user123"},
    )
    access_token = login_resp.json()["access_token"]

    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
