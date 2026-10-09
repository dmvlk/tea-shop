# Only Tea — frontend

React + TypeScript + Vite. Макетный интерфейс для учебного магазина.

## Запуск

```bash
npm install
cp .env.example .env.local
npm run dev
```

В режиме разработки запросы `/api/*` проксируются Vite на `http://localhost:8000`, поэтому CORS-настройки бэкенда менять не нужно. Если API работает на другом адресе, поменяйте `target` в `vite.config.ts`.

## Интеграция

Все данные берутся из API (БД `tea_shop_db`), демо-данных на фронте нет.

- `GET /api/products`, `GET /api/categories` — каталог и категории;
- `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me` — вход, роль берётся из `role` (`admin` / `user`);
- `GET/POST /api/orders` — история и оформление заказа (форма запроса предположительная, см. `src/api.ts`);
- `POST/PUT/DELETE /api/products` — раздел `/admin` (только для `role === 'admin'`).
- Корзина хранится в localStorage (id товара + количество).
- Изображения не используются: если `image_url` пуст, показывается заглушка.
