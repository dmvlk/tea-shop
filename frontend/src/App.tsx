import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { Search, ShoppingBag, ChevronDown, X, Minus, Plus, ArrowLeft, Check, Leaf, Menu } from 'lucide-react';
import { api, tokenStore, type ApiCategory, type ApiOrder, type ApiProduct, type ApiUser } from './api';
import Admin from './Admin';

type CartLine = { id: number; qty: number };
const CART_KEY = 'tea_cart';
const money = (n: number) => new Intl.NumberFormat('ru-RU').format(n) + ' ₽';
const errText = (e: unknown, fb: string) => (e instanceof Error ? e.message : fb);

function loadCart(): CartLine[] {
  try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); } catch { return []; }
}

function Img({ p }: { p: ApiProduct }) {
  return p.image_url ? <img src={p.image_url} alt={p.name} /> : <div className="img-ph"><Leaf size={28} /></div>;
}

export default function App() {
  const [products, setProducts] = useState<ApiProduct[]>([]);
  const [categories, setCategories] = useState<ApiCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState('');
  const [user, setUser] = useState<ApiUser | null>(null);
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [ordersError, setOrdersError] = useState('');
  const [cart, setCart] = useState<CartLine[]>(loadCart);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('popular');
  const [category, setCategory] = useState(0);
  const [modal, setModal] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const navigate = useNavigate();

  const loadProducts = useCallback(async () => {
    try {
      const r = await api.products();
      setProducts(r.items); setApiError('');
    } catch (e) { setApiError(errText(e, 'Не удалось загрузить каталог') + '. Проверьте, запущен ли бэкенд.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    loadProducts();
    api.categories().then(setCategories).catch(() => setCategories([]));
    if (tokenStore.has()) api.me().then(setUser).catch(() => tokenStore.clear());
  }, [loadProducts]);

  useEffect(() => { localStorage.setItem(CART_KEY, JSON.stringify(cart)); }, [cart]);

  const loadOrders = useCallback(() => {
    api.orders().then(o => { setOrders(o); setOrdersError(''); })
      .catch(e => { setOrders([]); setOrdersError(errText(e, 'Не удалось загрузить заказы')); });
  }, []);
  useEffect(() => { if (user) loadOrders(); else setOrders([]); }, [user, loadOrders]);

  const byId = useMemo(() => new Map(products.map(p => [p.id, p])), [products]);
  // строки корзины, товары которых уже исчезли из БД, отбрасываем
  const lines = cart.filter(l => byId.has(l.id) || loading);
  const cartCount = lines.reduce((s, l) => s + l.qty, 0);
  const cartTotal = lines.reduce((s, l) => s + Number(byId.get(l.id)?.price ?? 0) * l.qty, 0);

  const changeQty = (id: number, d: number) => setCart(old => {
    const max = byId.get(id)?.stock_quantity ?? Infinity;
    const next = old.some(l => l.id === id) ? old : [...old, { id, qty: 0 }];
    return next.map(l => (l.id === id ? { ...l, qty: Math.min(max, Math.max(0, l.qty + d)) } : l)).filter(l => l.qty > 0);
  });
  const addToCart = (id: number) => changeQty(id, 1);

  const logout = () => { tokenStore.clear(); setUser(null); navigate('/'); };
  const isAdmin = user?.role === 'admin';

  const catalog = <Catalog {...{ search, setSearch, sort, setSort, category, setCategory, categories, products, loading, apiError, addToCart }} />;

  return <>
    <header className="topbar">
      <Link to="/" className="brand"><span className="brand-mark">◉</span><span>Tea shop</span></Link>
      <button className="mobile-menu" onClick={() => setMobileMenu(!mobileMenu)}><Menu size={18} /></button>
      <nav className={mobileMenu ? 'nav open' : 'nav'}>
        <Link to="/" onClick={() => setMobileMenu(false)}>Каталог</Link>
        {isAdmin && <Link to="/admin" onClick={() => setMobileMenu(false)} style={{ marginLeft: 18 }}>Админка</Link>}
      </nav>
      <div className="header-actions">
        <button className="pill cart-pill" onClick={() => navigate('/cart')}><ShoppingBag size={14} /> Корзина · {cartCount}</button>
        {user
          ? <button className="pill user-pill" onClick={() => navigate('/profile')}>{user.full_name || user.email}</button>
          : <button className="pill login-pill" onClick={() => setModal(true)}>Войти / Зарегистрироваться</button>}
      </div>
    </header>

    <Routes>
      <Route path="/" element={catalog} />
      <Route path="/product/:id" element={<Product products={products} loading={loading} addToCart={addToCart} categories={categories} />} />
      <Route path="/cart" element={<Cart lines={lines} byId={byId} changeQty={changeQty} total={cartTotal} />} />
      <Route path="/checkout" element={<Checkout lines={lines} byId={byId} total={cartTotal} user={user} onLogin={() => setModal(true)}
        onDone={() => { setCart([]); loadOrders(); loadProducts(); }} />} />
      <Route path="/profile" element={<Profile user={user} orders={orders} ordersError={ordersError} byId={byId} onLogin={() => setModal(true)} onLogout={logout} />} />
      <Route path="/admin" element={isAdmin
        ? <Admin products={products} categories={categories} reload={loadProducts} money={money} />
        : <Navigate to="/" replace />} />
      <Route path="*" element={catalog} />
    </Routes>

    {modal && <AuthModal onClose={() => setModal(false)} onAuth={u => { setUser(u); setModal(false); navigate(u.role === 'admin' ? '/admin' : '/profile'); }} />}
    <footer className="footer"><span>Tea shop</span><span>Хороший чай — повод замедлиться.</span><span>© 2026</span></footer>
  </>;
}

function AuthModal({ onClose, onAuth }: { onClose: () => void; onAuth: (u: ApiUser) => void }) {
  const [register, setRegister] = useState(false);
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setError(''); setBusy(true);
    const d = new FormData(e.currentTarget);
    const email = String(d.get('email') || ''), password = String(d.get('password') || '');
    try {
      if (register) await api.register(email, String(d.get('full_name') || ''), password);
      tokenStore.set(await api.login(email, password));
      onAuth(await api.me());
    } catch (err) { setError(errText(err, 'Не удалось выполнить запрос')); } finally { setBusy(false); }
  };

  return <div className="overlay" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
    <section className="auth-modal">
      <button className="close-modal" onClick={onClose} aria-label="Закрыть"><X size={18} /></button>
      <h2>{register ? 'Создать аккаунт' : 'Войти в Tea shop'}</h2>
      <div className="auth-tabs">
        <button className={!register ? 'active' : ''} onClick={() => setRegister(false)}>Войти</button>
        <button className={register ? 'active' : ''} onClick={() => setRegister(true)}>Регистрация</button>
      </div>
      <form onSubmit={submit}>
        <label>Электронная почта<input name="email" type="email" required /></label>
        {register && <label>Имя<input name="full_name" required /></label>}
        <label>Пароль<div className="password-wrap">
          <input name="password" type={show ? 'text' : 'password'} minLength={6} required />
          <button type="button" onClick={() => setShow(!show)}>{show ? 'Скрыть' : 'Показать'}</button></div></label>
        <button className="primary full" type="submit" disabled={busy}>{busy ? 'Подождите…' : register ? 'Зарегистрироваться' : 'Войти'}</button>
        {error && <p className="api-error">{error}</p>}
      </form>
    </section>
  </div>;
}

type CatalogProps = {
  search: string; setSearch: (s: string) => void; sort: string; setSort: (s: string) => void;
  category: number; setCategory: (n: number) => void; categories: ApiCategory[];
  products: ApiProduct[]; loading: boolean; apiError: string; addToCart: (id: number) => void;
};
function Catalog({ search, setSearch, sort, setSort, category, setCategory, categories, products, loading, apiError, addToCart }: CatalogProps) {
  const items = useMemo(() => {
    const q = search.toLowerCase();
    const a = products.filter(p => (!category || p.category_id === category)
      && `${p.name} ${p.origin ?? ''} ${p.description ?? ''}`.toLowerCase().includes(q));
    if (sort === 'price-up') a.sort((x, y) => Number(x.price) - Number(y.price));
    if (sort === 'price-down') a.sort((x, y) => Number(y.price) - Number(x.price));
    if (sort === 'name') a.sort((x, y) => x.name.localeCompare(y.name, 'ru'));
    return a;
  }, [search, sort, category, products]);

  return <main className="catalog-page">
    {apiError && <p className="api-notice">{apiError}</p>}
    {loading && <p className="api-notice">Загружаем каталог с сервера…</p>}
    <div className="search-row">
      <div className="search-box"><Search size={16} />
        <input placeholder="Найти чай по названию, origin или описанию" value={search} onChange={e => setSearch(e.target.value)} />
        {search && <button onClick={() => setSearch('')}><X size={14} /></button>}</div>
      {categories.length > 0 && <div className="select-wrap">
        <select value={category} onChange={e => setCategory(Number(e.target.value))} aria-label="Категория">
          <option value={0}>Все категории</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select><ChevronDown size={14} /></div>}
      <div className="select-wrap">
        <select value={sort} onChange={e => setSort(e.target.value)} aria-label="Сортировка">
          <option value="popular">По умолчанию</option><option value="price-up">Сначала дешевле</option>
          <option value="price-down">Сначала дороже</option><option value="name">По названию</option></select><ChevronDown size={14} /></div>
    </div>
    <section className="intro"><div className="eyebrow">ЧАЙНАЯ КОЛЛЕКЦИЯ</div><h1>Чай</h1><p>Товары из базы данных магазина.</p></section>
    <div className="product-grid">{items.map(p => <ProductCard key={p.id} p={p} cat={categories.find(c => c.id === p.category_id)?.name} addToCart={addToCart} />)}</div>
    {!loading && !items.length && !apiError && <div className="empty-state"><Leaf size={30} /><h3>Ничего не найдено</h3>
      <button className="outline" onClick={() => { setSearch(''); setCategory(0); }}>Сбросить фильтры</button></div>}
  </main>;
}

function ProductCard({ p, cat, addToCart }: { p: ApiProduct; cat?: string; addToCart: (id: number) => void }) {
  const out = p.stock_quantity <= 0;
  return <article className="product-card">
    <Link className="product-image-wrap" to={'/product/' + p.id}><Img p={p} />{out && <span className="image-badge">Нет в наличии</span>}</Link>
    <div className="product-info">
      {cat && <span className="product-kind">{cat}</span>}
      <Link to={'/product/' + p.id} className="product-name">{p.name}</Link>
      <p>{p.origin || ''}</p>
      <div className="product-bottom"><span>{p.weight_grams} г</span>
        <button className="price-button" disabled={out} onClick={() => addToCart(p.id)} aria-label={'Добавить ' + p.name}>{money(Number(p.price))}</button></div>
    </div>
  </article>;
}

function Product({ products, loading, addToCart, categories }: { products: ApiProduct[]; loading: boolean; addToCart: (id: number) => void; categories: ApiCategory[] }) {
  const { id } = useParams();
  const [added, setAdded] = useState(false);
  const p = products.find(x => x.id === Number(id));
  if (!p) return <main className="detail-page"><Link to="/" className="back-link"><ArrowLeft size={15} /> В каталог</Link>
    <p className="api-notice">{loading ? 'Загрузка…' : 'Товар не найден'}</p></main>;
  const cat = categories.find(c => c.id === p.category_id)?.name;
  const specs: [string, string][] = [['Происхождение', p.origin || '—'], ['Вес упаковки', p.weight_grams + ' г'], ['В наличии', p.stock_quantity + ' шт.']];
  if (cat) specs.unshift(['Категория', cat]);
  return <main className="detail-page"><Link to="/" className="back-link"><ArrowLeft size={15} /> В каталог</Link>
    <div className="detail-grid">
      <div className="detail-image"><Img p={p} /></div>
      <section className="detail-info">
        {cat && <div className="eyebrow">{cat.toUpperCase()}</div>}
        <h1>{p.name}</h1>
        <p className="detail-description">{p.description || 'Описание отсутствует.'}</p>
        <div className="spec-list">{specs.map(([a, b]) => <div key={a}><span>{a}</span><strong>{b}</strong></div>)}</div>
        <div className="buy-row"><div><strong className="detail-price">{money(Number(p.price))}</strong>
          <small>{p.stock_quantity > 0 ? 'В наличии' : 'Нет в наличии'}</small></div>
          <button className="primary buy-button" disabled={p.stock_quantity <= 0}
            onClick={() => { addToCart(p.id); setAdded(true); setTimeout(() => setAdded(false), 1800); }}>
            {added ? <><Check size={16} /> Добавлено</> : 'Купить'}</button></div>
      </section>
    </div></main>;
}

type CartProps = { lines: CartLine[]; byId: Map<number, ApiProduct> };
function Cart({ lines, byId, changeQty, total }: CartProps & { changeQty: (id: number, d: number) => void; total: number }) {
  const nav = useNavigate();
  const count = lines.reduce((s, x) => s + x.qty, 0);
  return <main className="content-page"><div className="eyebrow">ВАШ ВЫБОР</div><h1>Корзина</h1>
    {!lines.length
      ? <div className="empty-state"><ShoppingBag size={32} /><h3>Корзина пока пуста</h3><Link to="/" className="primary inline-button">Перейти в каталог</Link></div>
      : <div className="cart-layout">
        <section className="cart-items"><div className="section-heading"><h3>Ваши чаи</h3><span>{count} шт.</span></div>
          {lines.map(l => { const p = byId.get(l.id); if (!p) return null; return <article className="cart-item" key={l.id}>
            <Link to={'/product/' + p.id}><Img p={p} /></Link>
            <div className="cart-item-info"><Link to={'/product/' + p.id} className="product-name">{p.name}</Link><p>{p.weight_grams} г · {money(Number(p.price))} за упаковку</p></div>
            <div className="quantity"><button onClick={() => changeQty(l.id, -1)} aria-label="Меньше"><Minus size={13} /></button><span>{l.qty}</span>
              <button onClick={() => changeQty(l.id, 1)} aria-label="Больше" disabled={l.qty >= p.stock_quantity}><Plus size={13} /></button></div>
            <strong className="line-total">{money(Number(p.price) * l.qty)}</strong></article>; })}
        </section>
        <aside className="summary-card"><h3>Итого</h3>
          <div className="summary-line"><span>Товары · {count} шт.</span><strong>{money(total)}</strong></div>
          <div className="summary-divider" /><div className="summary-total"><span>К оплате</span><strong>{money(total)}</strong></div>
          <button className="primary full" onClick={() => nav('/checkout')}>Перейти к оформлению</button></aside>
      </div>}
  </main>;
}

function Checkout({ lines, byId, total, user, onLogin, onDone }: CartProps & { total: number; user: ApiUser | null; onLogin: () => void; onDone: () => void }) {
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (done) return <main className="content-page"><div className="success-card"><span className="success-icon"><Check size={28} /></span>
    <h1>Спасибо за заказ!</h1><Link to="/profile" className="primary inline-button">Посмотреть заказ</Link></div></main>;
  if (!user) return <main className="content-page"><h1>Оформление заказа</h1>
    <div className="empty-state"><h3>Войдите, чтобы оформить заказ</h3><button className="primary inline-button" onClick={onLogin}>Войти</button></div></main>;

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true); setError('');
    const d = new FormData(e.currentTarget);
    const address = `${d.get('city')}, ${d.get('street')}, д. ${d.get('house')}${d.get('flat') ? ', кв. ' + d.get('flat') : ''}, ${d.get('zip')}`;
    try {
      await api.createOrder(lines.map(l => ({ product_id: l.id, quantity: l.qty })), address);
      setDone(true); onDone();
    } catch (err) { setError(errText(err, 'Не удалось оформить заказ')); } finally { setBusy(false); }
  };

  return <main className="content-page"><div className="eyebrow">ПОСЛЕДНИЙ ШАГ</div><h1>Оформление заказа</h1>
    <form className="checkout-layout" onSubmit={submit}>
      <div className="checkout-forms"><section className="form-card"><h3>Адрес доставки</h3><div className="form-grid">
        <label>Город<input name="city" required /></label><label>Улица<input name="street" required /></label>
        <label>Дом<input name="house" required /></label><label>Квартира<input name="flat" /></label>
        <label className="span-2">Индекс<input name="zip" required /></label></div></section></div>
      <aside className="summary-card checkout-summary"><h3>Ваш заказ</h3>
        {lines.map(l => { const p = byId.get(l.id); if (!p) return null; return <div className="checkout-product" key={l.id}>
          <Img p={p} /><div><strong>{p.name}</strong><small>{p.weight_grams} г · {l.qty} шт.</small></div><b>{money(Number(p.price) * l.qty)}</b></div>; })}
        <div className="summary-divider" /><div className="summary-total"><span>К оплате</span><strong>{money(total)}</strong></div>
        <button className="primary full" type="submit" disabled={!lines.length || busy}>{busy ? 'Отправляем…' : 'Подтвердить заказ'}</button>
        {error && <p className="api-error">{error}</p>}</aside>
    </form></main>;
}

function Profile({ user, orders, ordersError, byId, onLogin, onLogout }: { user: ApiUser | null; orders: ApiOrder[]; ordersError: string; byId: Map<number, ApiProduct>; onLogin: () => void; onLogout: () => void }) {
  if (!user) return <main className="content-page"><h1>Профиль</h1><div className="empty-state"><h3>Вы не вошли в аккаунт</h3>
    <button className="primary inline-button" onClick={onLogin}>Войти</button></div></main>;
  return <main className="content-page"><div className="eyebrow">ЛИЧНЫЙ КАБИНЕТ</div><h1>Профиль</h1>
    <div className="profile-layout">
      <section className="profile-card">
        <div className="profile-person"><span className="avatar">{(user.full_name || user.email).slice(0, 1).toUpperCase()}</span>
          <div><strong>{user.full_name || user.email}</strong><small>{user.role === 'admin' ? 'Администратор' : 'Покупатель'}</small></div></div>
        <div className="summary-divider" /><h3>Основные данные</h3>
        <div className="profile-field"><small>Имя</small><strong>{user.full_name}</strong></div>
        <div className="profile-field"><small>Электронная почта</small><strong>{user.email}</strong></div>
        <button className="outline full" onClick={onLogout}>Выйти</button>
      </section>
      <section className="orders-section"><h3>История заказов</h3>
        {ordersError && <p className="api-notice">{ordersError}</p>}
        {!ordersError && !orders.length && <p className="muted">Заказов пока нет.</p>}
        {orders.map(o => <article className="order-card" key={o.id}>
          <div className="order-top"><div><strong>Заказ № {o.id}</strong><small>{o.created_at ? new Date(o.created_at).toLocaleDateString('ru-RU') : ''}</small></div>
            {o.status && <span className="status"><i /> {o.status}</span>}</div>
          <div className="order-bottom"><span>{(o.items || []).map(i => `${i.product_name || byId.get(i.product_id)?.name || 'Товар #' + i.product_id} × ${i.quantity}`).join(' · ')}</span>
            {(o.total_amount ?? o.total) !== undefined && <strong>{money(Number(o.total_amount ?? o.total))}</strong>}</div>
        </article>)}
      </section>
    </div></main>;
}
