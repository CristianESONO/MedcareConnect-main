/**
 * API helpers — proxy to Django backend at localhost:8000
 * Vite dev server proxies /api, /healthcare, /cart to Django.
 */

const BASE = '';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    credentials: 'include',
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`);
  return res.json() as Promise<T>;
}

// ── Search ──────────────────────────────────────────────────────────────────
export interface SearchResult {
  id: number;
  nom: string;
  type: string;
  ville?: string;
  distance_km?: number;
  note_moyenne?: number;
  price_min?: number;
  price_max?: number;
  actes: string[];
  slug?: string;
}

export async function searchActes(params: Record<string, string | number | boolean>) {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== '' && v !== undefined && v !== null)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return request<{ results: SearchResult[]; total: number }>(`/api/search/?${qs}`);
}

// ── Cart ────────────────────────────────────────────────────────────────────
export interface CartItem {
  id: number;
  acte_nom: string;
  structure_nom: string;
  price: number;
}

export interface Cart {
  items: CartItem[];
  total: number;
}

export const cartApi = {
  get:    ()                        => request<Cart>('/cart/api/'),
  add:    (acteId: number, structId: number) =>
    request<Cart>('/cart/api/add/', { method: 'POST', body: JSON.stringify({ acte_id: acteId, structure_id: structId }) }),
  remove: (itemId: number)          =>
    request<Cart>('/cart/api/remove/', { method: 'POST', body: JSON.stringify({ item_id: itemId }) }),
  clear:  ()                        => request<Cart>('/cart/api/clear/', { method: 'POST' }),
};

// ── Dashboard ───────────────────────────────────────────────────────────────
export interface DashboardStats {
  total_patients: number;
  revenue_month: number;
  actes_month: number;
  completion_rate: number;
  activity: { label: string; value: number }[];
}

export const dashboardApi = {
  stats: () => request<DashboardStats>('/api/dashboard/stats/'),
};

// ── Panels ──────────────────────────────────────────────────────────────────
export interface Panel {
  id: number;
  nom: string;
  description: string;
  actes: { id: number; nom: string; price: number }[];
}

export const panelsApi = {
  list:   ()           => request<Panel[]>('/healthcare/api/panels/'),
  create: (data: Omit<Panel, 'id'>) =>
    request<Panel>('/healthcare/api/panels/', { method: 'POST', body: JSON.stringify(data) }),
  delete: (id: number) =>
    request<void>(`/healthcare/api/panels/${id}/`, { method: 'DELETE' }),
};
