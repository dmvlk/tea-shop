const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const TOKEN_KEY = 'tea_access_token';
const REFRESH_KEY = 'tea_refresh_token';

export type ApiCategory = { id: number; name: string; slug: string; description?: string | null };
export type ApiProduct = {
  id: number; name: string; description: string | null; price: number | string;
  stock_quantity: number; weight_grams: number; origin: string | null;
  image_url: string | null; category_id: number; created_at: string;
};
export type ProductInput = Omit<ApiProduct, 'id' | 'created_at' | 'image_url'> & { image_url?: string | null };
export type ApiUser = { id: number; email: string; full_name: string; role: string; created_at: string };
export type Tokens = { access_token: string; refresh_token: string; token_type: string };
// ВНИМАНИЕ: форма заказа предположительная — поправьте под реальные схемы бэка.
export type ApiOrderItem = { product_id: number; quantity: number; price?: number | string; product_name?: string };
export type ApiOrder = { id: number; status?: string; total_amount?: number | string; total?: number | string; created_at?: string; items?: ApiOrderItem[] };

export const tokenStore = {
  set: (t: Tokens) => { localStorage.setItem(TOKEN_KEY, t.access_token); localStorage.setItem(REFRESH_KEY, t.refresh_token); },
  clear: () => { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_KEY); },
  has: () => !!localStorage.getItem(TOKEN_KEY),
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    let message = `Ошибка API (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === 'string') message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d: { msg: string }) => d.msg).join('; ');
    } catch { /* не JSON */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const json = (body: unknown) => ({ body: JSON.stringify(body) });

export const api = {
  products: () => request<{ items: ApiProduct[]; total: number }>('/api/products?size=100'),
  categories: () => request<ApiCategory[] | { items: ApiCategory[] }>('/api/categories')
    .then(r => (Array.isArray(r) ? r : r.items)),
  createProduct: (p: ProductInput) => request<ApiProduct>('/api/products', { method: 'POST', ...json(p) }),
  updateProduct: (id: number, p: Partial<ProductInput>) => request<ApiProduct>(`/api/products/${id}`, { method: 'PUT', ...json(p) }),
  deleteProduct: (id: number) => request<void>(`/api/products/${id}`, { method: 'DELETE' }),
  login: (email: string, password: string) => request<Tokens>('/api/auth/login', { method: 'POST', ...json({ email, password }) }),
  register: (email: string, full_name: string, password: string) => request<ApiUser>('/api/auth/register', { method: 'POST', ...json({ email, full_name, password }) }),
  me: () => request<ApiUser>('/api/auth/me'),
  orders: () => request<ApiOrder[] | { items: ApiOrder[] }>('/api/orders').then(r => (Array.isArray(r) ? r : r.items)),
  createOrder: (items: { product_id: number; quantity: number }[], shipping_address: string) =>
    request<ApiOrder>('/api/orders', { method: 'POST', ...json({ items, shipping_address }) }),
};
