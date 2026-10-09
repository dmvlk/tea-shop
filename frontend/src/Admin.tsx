import { useState } from 'react';
import { api, type ApiCategory, type ApiProduct } from './api';

type Props = { products: ApiProduct[]; categories: ApiCategory[]; reload: () => Promise<void>; money: (n: number) => string };
const empty = { name: '', description: '', price: '', stock_quantity: '0', weight_grams: '50', origin: '', category_id: '' };

export default function Admin({ products, categories, reload, money }: Props) {
  const [form, setForm] = useState(empty);
  const [editId, setEditId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof empty, v: string) => setForm(f => ({ ...f, [k]: v }));

  const edit = (p: ApiProduct) => {
    setEditId(p.id);
    setForm({ name: p.name, description: p.description || '', price: String(p.price), stock_quantity: String(p.stock_quantity), weight_grams: String(p.weight_grams), origin: p.origin || '', category_id: String(p.category_id) });
  };
  const reset = () => { setEditId(null); setForm(empty); setError(''); };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError('');
    const body = { name: form.name, description: form.description || null, price: Number(form.price), stock_quantity: Number(form.stock_quantity), weight_grams: Number(form.weight_grams), origin: form.origin || null, category_id: Number(form.category_id) };
    try {
      if (editId) await api.updateProduct(editId, body); else await api.createProduct(body);
      await reload(); reset();
    } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось сохранить'); } finally { setBusy(false); }
  };
  const remove = async (p: ApiProduct) => {
    if (!confirm(`Удалить «${p.name}»?`)) return;
    try { await api.deleteProduct(p.id); await reload(); } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось удалить'); }
  };

  return <main className="content-page">
    <div className="eyebrow">АДМИНИСТРИРОВАНИЕ</div><h1>Управление товарами</h1>
    <p className="page-subtitle">Данные напрямую из базы tea_shop_db.</p>
    <div className="cart-layout">
      <section className="cart-items">
        <div className="section-heading"><h3>Товары</h3><span>{products.length} шт.</span></div>
        {products.map(p => <article className="admin-row" key={p.id}>
          <div><strong>{p.name}</strong><small>{categories.find(c => c.id === p.category_id)?.name || `Категория #${p.category_id}`} · {p.weight_grams} г · остаток {p.stock_quantity}</small></div>
          <b>{money(Number(p.price))}</b>
          <div className="admin-actions"><button className="outline" onClick={() => edit(p)}>Изменить</button><button className="outline danger" onClick={() => remove(p)}>Удалить</button></div>
        </article>)}
      </section>
      <aside className="summary-card">
        <h3>{editId ? `Товар #${editId}` : 'Новый товар'}</h3>
        <form className="admin-form" onSubmit={submit}>
          <label>Название<input value={form.name} onChange={e => set('name', e.target.value)} required /></label>
          <label>Описание<input value={form.description} onChange={e => set('description', e.target.value)} /></label>
          <label>Цена, ₽<input type="number" min="0" step="0.01" value={form.price} onChange={e => set('price', e.target.value)} required /></label>
          <label>Вес упаковки, г<input type="number" min="1" value={form.weight_grams} onChange={e => set('weight_grams', e.target.value)} required /></label>
          <label>Остаток<input type="number" min="0" value={form.stock_quantity} onChange={e => set('stock_quantity', e.target.value)} required /></label>
          <label>Происхождение<input value={form.origin} onChange={e => set('origin', e.target.value)} /></label>
          <label>Категория{categories.length
            ? <select value={form.category_id} onChange={e => set('category_id', e.target.value)} required><option value="">Выберите…</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
            : <input type="number" value={form.category_id} onChange={e => set('category_id', e.target.value)} placeholder="ID категории" required />}</label>
          <button className="primary full" disabled={busy}>{busy ? 'Сохраняем…' : editId ? 'Сохранить' : 'Добавить'}</button>
          {editId && <button type="button" className="outline full" onClick={reset}>Отмена</button>}
          {error && <p className="api-error">{error}</p>}
        </form>
      </aside>
    </div>
  </main>;
}
