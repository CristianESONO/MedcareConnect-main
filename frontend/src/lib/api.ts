import { getCsrfToken } from './auth';

/**
 * API helpers — proxy to Django backend at localhost:8000
 * Vite dev server proxies /api, /sante, /cart and static assets to Django.
 */

const BASE = '';

export interface AuthSession {
  authenticated: boolean;
  is_patient: boolean;
  is_prestataire: boolean;
  is_praticien: boolean;
  is_admin: boolean;
}

export function formatApiError(error: unknown, fallback: string): string {
  if (
    error instanceof TypeError
    && /failed to fetch|networkerror|load failed/i.test(error.message)
  ) {
    return 'Le serveur Django ne répond pas. Vérifiez qu’il est démarré sur le port 8000, puis réessayez.';
  }
  return error instanceof Error ? error.message : fallback;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    credentials: 'include',
    ...options,
  });
  if (!res.ok) {
    let message = `HTTP ${res.status} — ${url}`;
    try {
      const data = (await res.json()) as { error?: string; detail?: string; message?: string };
      message = data.message || data.detail || data.error || message;
    } catch {
      // Keep the HTTP error when the response is not JSON.
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

async function postForm<T>(url: string, body: FormData): Promise<T> {
  const csrfToken = await getCsrfToken();
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': csrfToken,
    },
    body,
  });
  const data = await response.json() as {
    error?: string;
    errors?: Record<string, ({ message: string } | string)[]>;
  };
  if (!response.ok) {
    const formErrors = Object.values(data.errors || {})
      .flat()
      .map((item) => typeof item === 'string' ? item : item.message);
    throw new Error(data.error || formErrors.join(' ') || `HTTP ${response.status} — ${url}`);
  }
  return data as T;
}

// ── Search ──────────────────────────────────────────────────────────────────
export interface SearchResult {
  id: number;
  nom: string;
  type: string;
  ville?: string;
  quartier?: string;
  horaires?: string;
  verified?: boolean;
  ambulance?: boolean;
  home_collection?: boolean;
  logo?: string;
  distance_km?: number;
  note_moyenne?: number;
  price_min?: number;
  price_max?: number;
  price?: string;
  price_ipm?: string | null;
  price_assurance?: string | null;
  coverage_status_ipm?: string;
  coverage_status_assurance?: string;
  delai?: string;
  catalog_count?: number;
  insurance_names?: string[];
  insurance_match?: boolean;
  acte_id?: number;
  acte?: string;
  categorie?: string;
  profile_url?: string;
  add_url?: string;
  actes: string[];
  slug?: string;
}

export interface SearchPayload {
  redirect_url?: string;
  stats: { structures: number; piliers: number; actes: number; assurances: number };
  query: string;
  results_count: number;
  offers: SearchResult[];
  pagination: {
    number: number;
    pages: number;
    has_previous: boolean;
    previous: number | null;
    has_next: boolean;
    next: number | null;
  };
  filters: {
    service: string;
    actes: string[];
    sort: string;
    regime: string;
    assurances: string[];
    city: string;
    types: string[];
    regions: string[];
    price_min: string;
    price_max: string;
    delai: string;
    domicile: boolean;
    lat: string;
    lng: string;
    radius_km: number;
    proximity: boolean;
    active_count: number;
    min_price: string;
    max_price: string;
  };
  services: { id: string; label: string; count: number; active: boolean; ambulance: boolean }[];
  families: {
    id: number;
    title: string;
    count: number;
    open: boolean;
    subgroups: {
      title: string;
      count: number;
      acts: { id: number | null; name: string; selected: boolean; count: number }[];
    }[];
  }[];
  filter_options: {
    types: { id: number; name: string }[];
    regions: { id: number; name: string }[];
    assurances: { id: number; name: string; group: string }[];
    delais: { id: string; name: string }[];
    cities: string[];
  };
  popular_actes: { id: number; name: string; structure_count: number }[];
  presets: { id: number; name: string; [key: string]: unknown }[];
  title: string;
  subtitle: string;
  is_ambulance_service: boolean;
}

export interface SearchSuggestion {
  id?: number;
  label: string;
  type: 'famille' | 'acte' | 'centre';
  detail?: string;
  url?: string;
}

export function searchActes(params: URLSearchParams, signal?: AbortSignal) {
  const query = params.toString();
  return request<SearchPayload>(
    `/sante/api/recherche/${query ? `?${query}` : ''}`,
    { signal },
  );
}

export async function searchAutocomplete(query: string, signal?: AbortSignal) {
  return request<{ suggestions: SearchSuggestion[] }>(
    `/sante/api/autocompletion/?q=${encodeURIComponent(query)}`,
    { signal },
  );
}

export interface AnnuaireResult {
  id: number;
  name: string;
  slug: string;
  type: string;
  category: string;
  city: string;
  quartier: string;
  zone_label: string;
  logo: string;
  verified: boolean;
  pioneer: boolean;
  acte_count: number;
  insurance_count: number;
  insurance_names: string[];
  matched_insurances: string[];
  delay_label: string;
  hours: string;
  is_favorite: boolean;
  profile_url: string;
}

export interface AnnuairePayload {
  results: AnnuaireResult[];
  results_count: number;
  pagination: {
    number: number;
    pages: number;
    has_previous: boolean;
    has_next: boolean;
  };
  filters: {
    q: string;
    type_cat: string;
    zone: string;
    delai: string;
    sort: string;
    assurances: string[];
  };
  categories: { id: string; label: string }[];
  delays: { id: string; label: string }[];
  sorts: { id: string; label: string }[];
  zones: string[];
  insurances: { id: number; name: string; segment: string }[];
  geo_required: boolean;
}

export interface OrganizationPublicProfile {
  id: number;
  name: string;
  slug: string;
  type: string;
  city: string;
  quartier: string;
  address: string;
  latitude: string;
  longitude: string;
  phone: string;
  whatsapp_url: string;
  website: string;
  description: string;
  logo: string;
  verified: boolean;
  pioneer: boolean;
  show_prices: boolean;
  is_favorite: boolean;
  acte_count: number;
  acts: {
    id: number;
    name: string;
    category: string;
    price: string | null;
    price_ipm: string | null;
    price_assurance: string | null;
    status_ipm: string;
    status_assurance: string;
    delay: string;
    notes: string;
    whatsapp_url: string;
    add_url: string;
  }[];
  pillars: { name: string; count: number }[];
  hours: { day: string; display: string; closed: boolean; today: boolean }[];
  hours_summary: string;
  practical_chips: { label: string; icon: string }[];
  insurance_match: string;
  insurances: {
    name: string;
    segment: string;
    filter_key: string;
    chip_label: string;
    patient_match: boolean;
  }[];
  maps_url: string;
  waze_url: string;
}

export interface PractitionerPublicProfile {
  id: number;
  name: string;
  slug: string;
  profession: string;
  specialty: string;
  city: string;
  quartier: string;
  address: string;
  phone: string;
  description: string;
  logo: string;
  acts: { id: number; name: string; category: string; price: string; delay: string; add_url: string }[];
  affiliations: {
    structure: string;
    city: string;
    role: string;
    days: string[];
    profile_url: string;
  }[];
  tickets: {
    title: string;
    description: string;
    price: string;
    mode: string;
    zone: string;
    availability: string;
    url: string;
    search_url: string;
  }[];
}

export interface ServiceDetailData {
  name: string;
  slug: string;
  icon: string;
  acts: { name: string; category: string }[];
  categories: string[];
  providers: { name: string; slug: string; city: string; profile_url: string }[];
}

export interface FavoriteEntry {
  id: number;
  name: string;
  slug: string;
  type: string;
  city: string;
  quartier: string;
  logo: string;
  profile_url: string;
}

export const discoveryApi = {
  annuaire: (params: URLSearchParams, signal?: AbortSignal) => {
    const query = params.toString();
    return request<AnnuairePayload>(
      `/sante/api/annuaire/${query ? `?${query}` : ''}`,
      { signal },
    );
  },
  organization: (slug: string, signal?: AbortSignal) =>
    request<OrganizationPublicProfile>(`/sante/${encodeURIComponent(slug)}/`, {
      signal,
      headers: { Accept: 'application/json' },
    }),
  practitioner: (slug: string, signal?: AbortSignal) =>
    request<PractitionerPublicProfile>(
      `/sante/praticien/${encodeURIComponent(slug)}/`,
      { signal, headers: { Accept: 'application/json' } },
    ),
  service: (slug: string, signal?: AbortSignal) =>
    request<ServiceDetailData>(
      `/sante/service/${encodeURIComponent(slug)}/`,
      { signal, headers: { Accept: 'application/json' } },
    ),
  favorites: (signal?: AbortSignal) =>
    request<{ favorites: FavoriteEntry[] }>('/sante/api/favoris/', { signal }),
  toggleFavorite: (slug: string) =>
    postForm<{ ok: boolean; is_favorite: boolean }>(
      `/sante/api/favoris/${encodeURIComponent(slug)}/`,
      new FormData(),
    ),
};

// ── Cart ────────────────────────────────────────────────────────────────────
export interface CartItem {
  id: number;
  acte_id: number;
  acte_nom: string;
  structure_nom: string;
  price: number;
  quantity: number;
}

export interface PatientCartLine {
  id: number;
  prestataire_acte_id: number;
  acte: string;
  organization: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  patient_cost: string;
  coverage_rate: string | null;
  status_assurance: 'covered' | 'excluded' | 'to_confirm';
  status_ipm: 'covered' | 'excluded' | 'to_confirm';
  price_assurance: string | null;
}

export interface PatientCartGroup {
  organization_id: number;
  organization: string;
  subtotal: string;
  patient_subtotal: string;
  lines: PatientCartLine[];
}

export interface PatientCartPageData {
  groups: PatientCartGroup[];
  item_count: number;
  total_brut: string;
  total_coverage: string;
  total_patient: string;
  insurance_id: number | null;
  insurance_name: string;
  insurance_use_in_estimates: boolean;
  insurance_options: { segment: string; options: { id: number; name: string }[] }[];
}

export interface GuestCartPageData {
  groups: {
    organization_id: number;
    organization: string;
    subtotal: string;
    lines: {
      id: number;
      acte: string;
      category: string;
      quantity: number;
      unit_price: string;
      subtotal: string;
    }[];
  }[];
  item_count: number;
  total_brut: string;
  insurance_id: number | null;
  insurance_name: string;
  insurance_options: { segment: string; options: { id: number; name: string }[] }[];
  coverage: {
    insurance_name: string;
    total_brut: number;
    total_assurance: number;
    total_patient: number;
  } | null;
}

interface CartSnapshot {
  ok: boolean;
  items: {
    id: number;
    acte_pk: number;
    acte: string;
    org: string;
    price: number;
    qty: number;
  }[];
  cart_count: number;
}

export interface CartActionResponse {
  ok: boolean;
  error?: string;
  cart_count?: number;
}

async function cartAction(url: string): Promise<CartActionResponse> {
  const csrfToken = await getCsrfToken();
  return request<CartActionResponse>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      Accept: 'application/json',
      'X-CSRFToken': csrfToken,
    },
  });
}

export const cartApi = {
  session: (signal?: AbortSignal) =>
    request<AuthSession>('/cart/api/session/', { signal }),
  accountPage: (signal?: AbortSignal) =>
    request<PatientCartPageData>('/cart/api/account/', { signal }),
  accountQuotes: (signal?: AbortSignal) =>
    request<{ entries: AccountQuoteSummary[] }>('/cart/api/devis/', { signal }),
  accountQuote: (reference: string, signal?: AbortSignal) =>
    request<{ devis: AccountQuoteDetail }>(
      `/cart/api/devis/${encodeURIComponent(reference)}/`,
      { signal },
    ),
  history: (signal?: AbortSignal) =>
    request<{ entries: CartHistoryEntry[] }>('/cart/api/historique/', { signal }),
  patientPage: (signal?: AbortSignal) =>
    request<PatientCartPageData>('/cart/api/patient/', { signal }),
  guestPage: (signal?: AbortSignal) =>
    request<GuestCartPageData>('/cart/api/invite/', { signal }),
  get: async () => {
    const snapshot = await request<CartSnapshot>('/cart/api/snapshot/');
    return snapshot.items.map((item) => ({
      id: item.id,
      acte_id: item.acte_pk,
      acte_nom: item.acte,
      structure_nom: item.org,
      price: item.price,
      quantity: item.qty,
    }));
  },
  add: (paId: number) => cartAction(`/cart/ajouter/${paId}/`),
  remove: (paId: number) => cartAction(`/cart/supprimer-pa/${paId}/`),
  updateQuantity: (cartItemId: number, quantity: number) => {
    const data = new FormData();
    data.set('quantity', String(quantity));
    return postForm<CartActionResponse>(`/cart/modifier/${cartItemId}/`, data);
  },
  updateGuestQuantity: (paId: number, quantity: number) => {
    const data = new FormData();
    data.set('quantity', String(quantity));
    return postForm<CartActionResponse>(`/cart/invite/modifier/${paId}/`, data);
  },
  selectInsurance: (insuranceId: number | null) => {
    const data = new FormData();
    data.set('insurance', insuranceId ? String(insuranceId) : '');
    return postForm<CartActionResponse>('/cart/assurance/', data);
  },
  selectGuestInsurance: (insuranceId: number | null) => {
    const data = new FormData();
    data.set('insurance', insuranceId ? String(insuranceId) : '');
    return postForm<CartActionResponse>('/cart/invite/assurance/', data);
  },
  clear: () => cartAction('/cart/vider/'),
};

// ── Dashboard ───────────────────────────────────────────────────────────────
export interface DashboardStats {
  org_name: string;
  is_praticien: boolean;
  is_active: boolean;
  is_verified: boolean;
  org_city: string;
  org_quartier: string;
  org_description: string;
  org_logo: string | null;
  profile_url: string;
  edit_profile_url: string;
  period_key: '7j' | '30j' | 'total';
  period_label: string;
  views_period: number;
  profile_views_total: number;
  devis_period: number;
  devis_value: number;
  items_period: number;
  actes_count: number;
  insurances_count: number;
  completion_pct: number;
  completion_done: number;
  completion_total: number;
  completion: { label: string; complete: boolean }[];
  activity: { label: string; value: number }[];
  activity_chart: {
    labels: string[];
    series: Record<string, (number | null)[]>;
    meta: Record<string, { label: string; color: string; color_last: string }>;
    period_sub: string;
  };
  top_actes: { name: string; price: number; count: number }[];
  insurance_split: { name: string; count: number; pct: number }[];
  insurance_split_total: number;
  recent_views: {
    source: string;
    label: string;
    action: string;
    dot_class: string;
    badge_class: string;
    meta: string;
    viewer_name: string;
  }[];
  medplaque: {
    reference: string;
    nfc_scans: number;
    qr_scans: number;
    total_access: number;
    nfc_active: boolean;
    month_label: string;
  };
  accepted_insurances: string[];
  visit_source_filter: string;
  rdv_requested_count: number;
  rdv_upcoming_count: number;
  pending_devis: number;
  unread_messages: number;
}

export const dashboardApi = {
  stats: (
    period: DashboardStats['period_key'],
    visitSource = 'all',
    signal?: AbortSignal,
  ) =>
    request<DashboardStats>(
      `/api/dashboard/stats/?period=${encodeURIComponent(period)}&visit_src=${encodeURIComponent(visitSource)}`,
      { signal },
    ),
};

export type ProviderDevisStatus =
    | 'active'
    | 'all'
    | 'new'
    | 'sent'
    | 'viewed'
    | 'accepted'
    | 'relanced'
    | 'expired'
    | 'archived';

export interface ProviderDevisEntry {
    reference: string;
    parent_reference: string;
    status: string;
    status_label: string;
    is_accepted: boolean;
    created_at: string;
    valid_until: string | null;
    patient: string;
    insurance: string;
    relance_count: number;
    max_relances: number;
    relances_restantes: number;
    can_relance: boolean;
    show_relance: boolean;
    archived_reason: string;
    last_relanced_at: string | null;
    archived_at: string | null;
    creneau: string;
    subtotal: string;
    total_patient: string;
    items_count: number;
    items: {
      acte: string;
      quantity: number;
      subtotal: string;
      coverage_rate: number | null;
      patient_cost: string;
    }[];
    thread_url: string;
    show_confirm: boolean;
    pending_rdv: { reference: string } | null;
    active_rdv: { reference: string; status: string } | null;
    detail_url: string;
}

export interface ProviderDevisList {
    status_filter: ProviderDevisStatus;
    counts: Record<ProviderDevisStatus, number>;
    kpis: { active: number; new: number; accepted: number; total_value: string };
    entries: ProviderDevisEntry[];
    pagination: {
      page: number;
      pages: number;
      has_previous: boolean;
      previous: number | null;
      has_next: boolean;
      next: number | null;
    };
}

export const providerDevisApi = {
    list: (status: ProviderDevisStatus, page: number, signal?: AbortSignal) =>
      request<ProviderDevisList>(
        `/sante/api/prestataire/devis/?status=${encodeURIComponent(status)}&page=${page}`,
        { signal },
      ),
    detail: (reference: string, signal?: AbortSignal) =>
      request<{ entry: ProviderDevisEntry; devis: { reference: string; valid_until: string | null } }>(
        `/sante/api/prestataire/devis/partie/${encodeURIComponent(reference)}/`,
        { signal },
      ),
    relance: (reference: string, status: ProviderDevisStatus) => {
      const data = new FormData();
      data.set('status', status);
      return postForm<{ ok: boolean; message: string }>(
        `/sante/prestataire/devis/${encodeURIComponent(reference)}/relance/`,
        data,
      );
    },
    archive: (reference: string, status: ProviderDevisStatus) => {
      const data = new FormData();
      data.set('status', status);
      return postForm<{ ok: boolean; message: string }>(
        `/sante/prestataire/devis/${encodeURIComponent(reference)}/archiver/`,
        data,
      );
    },
    appointmentAction: (reference: string, action: 'confirm' | 'decline') => {
      const data = new FormData();
      data.set('action', action);
      data.set('next', '/sante/prestataire/devis/');
      return postForm<{ ok: boolean; message: string }>(
        `/rdv/pro/${encodeURIComponent(reference)}/action/`,
        data,
      );
    },
};

export type ProviderAppointmentStatus =
    | 'upcoming'
    | 'requested'
    | 'confirmed'
    | 'past'
    | 'all';

export interface ProviderAppointment {
    reference: string;
    status: string;
    status_label: string;
    start: string;
    local_datetime: string;
    patient: string;
    patient_note: string;
    prestataire_note: string;
    is_walk_in: boolean;
    walk_in_name: string;
    walk_in_phone: string;
    walk_in_motif: string;
    patient_phone: string;
    devis_reference: string;
    actes: { acte: string; quantity: number }[];
    total_patient: string;
    can_edit: boolean;
}

export interface ProviderAppointmentList {
    status_filter: ProviderAppointmentStatus;
    view_mode: 'list' | 'ticket';
    counts: Record<ProviderAppointmentStatus, number>;
    filter_tabs: { key: ProviderAppointmentStatus; label: string; count: number }[];
    appointments: ProviderAppointment[];
}

export const providerAppointmentsApi = {
    list: (
      status: ProviderAppointmentStatus,
      view: 'list' | 'ticket',
      signal?: AbortSignal,
    ) =>
      request<ProviderAppointmentList>(
        `/rdv/api/pro/agenda/?status=${encodeURIComponent(status)}&view=${view}`,
        { signal },
      ),
    action: (
      reference: string,
      action: 'confirm' | 'decline' | 'complete' | 'no_show' | 'cancel',
      status: ProviderAppointmentStatus,
    ) => {
      const data = new FormData();
      data.set('action', action);
      data.set('status', status);
      return postForm<{ ok: boolean; message: string }>(
        `/rdv/pro/${encodeURIComponent(reference)}/action/`,
        data,
      );
    },
    update: (reference: string, data: FormData) =>
      postForm<{ ok: boolean; message: string }>(
        `/rdv/pro/${encodeURIComponent(reference)}/modifier/`,
        data,
      ),
};

export interface ProviderCatalogAct {
  id: number;
  name: string;
  parent_name: string;
  category: string;
  reference_price: string;
  price: string;
  delai: string;
  is_available: boolean;
  coverage_status_ipm: string;
  price_ipm: string | null;
  coverage_status_assurance: string;
  price_assurance: string | null;
  preparation: {
    acte_id: number;
    name: string;
    category: string;
    pilier: string;
    reference: string;
    reference_lines: string[];
    custom: string;
    message: string;
    active: boolean;
    configured: boolean;
    reminders: { pk: number; label: string; hours: number | null; display: string }[];
  };
}

export interface ProviderCatalog {
  organization: string;
  catalogue_tarifs_delais: string;
  selected_pilier: number | null;
  total_count: number;
  pillars: {
    id: number;
    name: string;
    slug: string;
    icon: string;
    applicable: boolean;
    active_count: number;
    acte_count: number;
    subgroups: { label: string; actes: ProviderCatalogAct[] }[];
  }[];
  delai_choices: { value: string; label: string }[];
  show_domicile_block: boolean;
  domicile: {
    enabled: boolean;
    delay: string;
    delay_choices: { value: string; label: string }[];
    hours: string;
    zones: { pk: number; label: string; forfait_fcfa: number }[];
  };
  preparation: Record<number, ProviderCatalogAct['preparation']>;
  urls: {
    import: string;
    template: string;
    add: string;
    reminders: string;
    prerequisite_tpl: string;
    reminder_add_tpl: string;
    reminder_delete_tpl: string;
  };
}

export interface ProviderActFormData {
  is_edit: boolean;
  id?: number;
  acte?: number;
  price?: string;
  delai?: string;
  is_available?: boolean;
  notes?: string;
  choices: { id: number; name: string; group: string }[];
  delai_choices: { value: string; label: string }[];
}

export const providerCatalogApi = {
  get: (signal?: AbortSignal) =>
    request<ProviderCatalog>('/sante/api/prestataire/actes/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  save: (data: FormData) =>
    postForm<{ ok: boolean }>('/sante/prestataire/actes/', data),
  saveDomicile: (data: FormData) =>
    postForm<{
      ok: boolean;
      message: string;
      prises_sang_domicile: boolean;
      domicile_delai_intervention: string;
      domicile_plages_horaires: string;
      zones: { pk: number; label: string; forfait_fcfa: number; is_active: boolean }[];
    }>('/sante/prestataire/actes/', data),
  getActForm: (url: string, signal?: AbortSignal) =>
    request<ProviderActFormData>(url, { signal, headers: { Accept: 'application/json' } }),
  saveAct: (url: string, data: FormData) =>
    postForm<{ ok: boolean; id: number }>(url, data),
  toggleAct: (id: number) => {
    const data = new FormData();
    return postForm<{ ok: boolean; is_available: boolean }>(
      `/sante/prestataire/actes/${id}/disponibilite/`,
      data,
    );
  },
  deleteAct: (id: number) =>
    postForm<{ ok: boolean }>(`/sante/prestataire/actes/${id}/supprimer/`, new FormData()),
  import: (data: FormData) =>
    postForm<{
      ok: boolean;
      message: string;
      imported_count: number;
      created_count: number;
      updated_count: number;
      skipped_count: number;
      errors: string[];
    }>('/sante/prestataire/actes/import-excel/', data),
  savePrerequisites: (acteId: number, message: string, active: boolean, urlTemplate: string) => {
    const data = new FormData();
    data.set('rdv_prerequisites', message);
    data.set('rdv_prerequisites_active', active ? '1' : '0');
    return postForm<{ ok: boolean; configured: boolean; active: boolean; message: string }>(
      urlTemplate.replace('ACTE_ID', String(acteId)),
      data,
    );
  },
  addReminder: (acteId: number, hours: number, urlTemplate: string) => {
    const data = new FormData();
    data.set('hours', String(hours));
    return postForm<{ ok: boolean; reminders: ProviderCatalogAct['preparation']['reminders'] }>(
      urlTemplate.replace('ACTE_ID', String(acteId)),
      data,
    );
  },
  deleteReminder: (acteId: number, reminderId: number, urlTemplate: string) =>
    postForm<{ ok: boolean; reminders: ProviderCatalogAct['preparation']['reminders'] }>(
      urlTemplate
        .replace('ACTE_ID', String(acteId))
        .replace('SCHEDULE_PK', String(reminderId)),
      new FormData(),
    ),
};

export interface DjangoFormField {
  name: string;
  label: string;
  type: string;
  value: string | number | boolean | (string | number)[] | null;
  required: boolean;
  help_text: string;
  choices: { value: string; label: string }[];
}

export interface ProviderInsuranceData {
  organization: string;
  tarifs_delais: string;
  selected_ids: number[];
  selected_count: number;
  segment_choices: { value: string; label: string }[];
  segments: {
    segment: string;
    label: string;
    title: string;
    hint: string;
    selected_count: number;
    total_count: number;
    assurances: { id: number; name: string; description: string; selected: boolean }[];
  }[];
}

export interface ProviderOrganizationFormData {
  redirect?: string;
  is_edit: boolean;
  is_practitioner: boolean;
  organization?: string;
  logo_url?: string;
  profile_completion?: number;
  fields?: DjangoFormField[];
}

export interface ProviderHoursData {
  organization: string;
  days: { name: string; open: string; close: string; closed: boolean }[];
}

export interface ProviderPublicProfileData {
  organization: {
    name: string;
    description: string;
    address: string;
    city: string;
    phone: string;
    whatsapp_number: string;
    logo_url: string;
    website: string;
    is_practitioner: boolean;
  };
  public_url: string;
  public_path: string;
  actes_visible_count: number;
  show_prices: boolean;
  open_today: string | null;
  hours: { day: string; hours: string; closed: boolean; is_today: boolean }[];
  pillars: { id: string; name: string; actes: { name: string; price: string; delai: string; whatsapp_url: string }[] }[];
  insurances: { name: string; segment: string; chip_label: string }[];
  practical_chips: { label: string; icon: string }[];
  maps_url: string;
  whatsapp_url: string;
  show_pioneer_badge: boolean;
}

export interface ProviderTypeSetupData {
  organization: string;
  address: string;
  city: string;
  ninea: string;
  topology_type: string;
  type_libre: string;
  types: { name: string; icon: string; proposed: boolean }[];
  pillars: { id: number; name: string; slug: string; icon: string; active: boolean }[];
  type_pillars_map: Record<string, number[]>;
}

export interface ProviderSettingsData {
  organization: string;
  is_practitioner: boolean;
  user: { username: string; full_name: string; fields: DjangoFormField[] };
  notifications: { field_name: string; label: string; subtitle: string; enabled: boolean }[];
  preferences: {
    settings_dashboard_period: string;
    settings_locale: string;
    settings_currency: string;
    show_prices_on_public_profile: boolean;
  };
  team: { index: number; name: string; email: string; role: string; role_label: string; status: string }[];
  subscription: {
    plan: { name: string; short_description: string; monthly_price_fcfa: string; is_pioneer_offer: boolean } | null;
    pending_request: { plan: string; status: string } | null;
    recent_requests: { created_at: string; plan: string; status: string }[];
  };
}

export interface ProviderAnalyticsData {
  organization: string;
  stats?: {
    reference: string;
    nfc_scans: number;
    qr_scans: number;
    total_access: number;
    nfc_active: boolean;
    month_index: number;
    month_label: string;
    scan_to_visit_pct: number;
    visit_to_devis_pct: number;
    profile_url_nfc: string;
    profile_url_qr: string;
  };
  recent_visits?: Record<string, string | number | null>[];
  is_practitioner?: boolean;
  completion_pct?: number;
  completion?: { label: string; ok: boolean; url?: string }[];
  bilan?: {
    reference: string;
    section_a: { label: string; val: string; cible: number; signal: string; pct: number }[];
    section_b: { label: string; val: string; cible: number; signal: string; pct: number }[];
    section_c: { label: string; val: string; cible: number; signal: string; pct: number }[];
    pioneer: { days_remaining: number | null; end_date: string | null; progress_pct: number; label: string; available_upgrade: boolean };
    roi_ratio: number;
    recommended_slug: string;
    essentiel_plan: { name: string; slug: string; monthly_price_fcfa: string; short_description: string } | null;
    pro_plan: { name: string; slug: string; monthly_price_fcfa: string; short_description: string } | null;
  };
}

export interface ProviderReminder {
  id: number;
  label: string;
  offset_value: number;
  offset_unit: string;
  tolerance_minutes: number;
  include_prerequisites: boolean;
  is_active: boolean;
  order: number;
  sent_count: number;
  actes: string[];
}

export const providerPortalApi = {
  getInsurance: (signal?: AbortSignal) =>
    request<ProviderInsuranceData>('/sante/prestataire/assurances/', { signal, headers: { Accept: 'application/json' } }),
  saveInsurance: (data: FormData) =>
    postForm<{ ok: boolean; message: string }>('/sante/prestataire/assurances/', data),
  addInsurance: (data: FormData) =>
    postForm<{ ok: boolean; message: string }>('/sante/prestataire/assurances/', data),
  deleteInsurance: (id: number) =>
    postForm<{ ok: boolean }>(`/sante/prestataire/assurances/${id}/supprimer/`, new FormData()),
  getOrganizationForm: (url: string, signal?: AbortSignal) =>
    request<ProviderOrganizationFormData>(url, { signal, headers: { Accept: 'application/json' } }),
  saveOrganizationForm: (url: string, data: FormData) =>
    postForm<{ ok: boolean; id?: number; redirect: string }>(url, data),
  getHours: (signal?: AbortSignal) =>
    request<ProviderHoursData>('/sante/prestataire/organisme/horaires/', { signal, headers: { Accept: 'application/json' } }),
  saveHours: (data: FormData) =>
    postForm<{ ok: boolean; message: string }>('/sante/prestataire/organisme/horaires/', data),
  getPublicProfile: (signal?: AbortSignal) =>
    request<ProviderPublicProfileData>('/sante/prestataire/profil-public/', { signal, headers: { Accept: 'application/json' } }),
  getTypeSetup: (signal?: AbortSignal) =>
    request<ProviderTypeSetupData>('/sante/prestataire/type-etablissement/', { signal, headers: { Accept: 'application/json' } }),
  saveTypeSetup: (data: FormData) =>
    postForm<{ ok: boolean; message: string }>('/sante/prestataire/type-etablissement/', data),
  getSettings: (signal?: AbortSignal) =>
    request<ProviderSettingsData>('/sante/prestataire/parametres/', { signal, headers: { Accept: 'application/json' } }),
  saveSettings: (data: FormData) =>
    postForm<{ ok: boolean; message?: string; errors?: string[] }>('/sante/prestataire/parametres/', data),
  getMedPlaque: (signal?: AbortSignal) =>
    request<ProviderAnalyticsData>('/sante/prestataire/medplaque/', { signal, headers: { Accept: 'application/json' } }),
  getBilan: (signal?: AbortSignal) =>
    request<ProviderAnalyticsData>('/sante/prestataire/bilan/', { signal, headers: { Accept: 'application/json' } }),
  getReminders: (signal?: AbortSignal) =>
    request<{ organization: string; reminders: ProviderReminder[] }>('/sante/prestataire/actes/rappels/', { signal, headers: { Accept: 'application/json' } }),
  getReminderForm: (url: string, signal?: AbortSignal) =>
    request<{ is_edit: boolean; id?: number; fields: DjangoFormField[] }>(url, { signal, headers: { Accept: 'application/json' } }),
  saveReminderForm: (url: string, data: FormData) =>
    postForm<{ ok: boolean; id: number }>(url, data),
  deleteReminder: (id: number) =>
    postForm<{ ok: boolean }>(`/sante/prestataire/actes/rappels/${id}/supprimer/`, new FormData()),
};

export interface ProviderAgendaDay {
  date: string;
  weekday: string;
  is_today: boolean;
  is_open: boolean;
}

export interface ProviderAgendaAppointment {
  ref: string;
  name: string;
  phone: string;
  when: string;
  slot_iso: string;
  status: string;
  status_label: string;
  source: string;
  is_walk_in: boolean;
  motif: string;
  devis: string;
  total: string;
  note: string;
  actes: string[];
}

export interface ProviderAgendaCellAppointment {
  reference: string;
  patient_label: string;
  status: string;
  is_walk_in: boolean;
}

export interface ProviderAgendaCell {
  in_hours: boolean;
  value: string;
  label: string;
  rdv_count: number;
  is_past: boolean;
  rdvs: ProviderAgendaCellAppointment[];
}

export interface ProviderAgenda {
  organization: string;
  monday: string;
  sunday: string;
  prev_week: string;
  next_week: string;
  today: string;
  is_current_week: boolean;
  new_rdv_count: number;
  days: ProviderAgendaDay[];
  rows: { time: string; cells: ProviderAgendaCell[] }[];
  appointments: Record<string, ProviderAgendaAppointment>;
}

export const providerAgendaApi = {
  get: (date: string, signal?: AbortSignal) =>
    request<ProviderAgenda>(
      `/rdv/api/pro/agenda/grille/?date=${encodeURIComponent(date)}`,
      { signal },
    ),
  move: (reference: string, slot: string) => {
    const data = new FormData();
    data.set('slot', slot);
    return postForm<{ ok: boolean; ref: string; when: string; slot: string; label: string }>(
      `/rdv/pro/${encodeURIComponent(reference)}/deplacer/`,
      data,
    );
  },
  createWalkIn: (data: FormData) =>
    postForm<{ ok: boolean; reference: string; message: string }>(
      '/rdv/pro/sans-rendez-vous/',
      data,
    ),
};

export interface NotificationAdminSettings {
    email_enabled: boolean;
    smtp_host: string;
    smtp_port: number;
    smtp_user: string;
    smtp_password_configured: boolean;
    smtp_use_tls: boolean;
    smtp_use_ssl: boolean;
    smtp_from_email: string;
    smtp_from_name: string;
    smtp_reply_to: string;
    whatsapp_enabled: boolean;
    wa_phone_number_id: string;
    wa_business_account_id: string;
    wa_access_token_configured: boolean;
    wa_api_version: string;
    in_app_enabled: boolean;
    log_retention_days: number;
    google_reviews_url: string;
}

export interface NotificationAdminRule {
    id: number;
    event_id: number;
    channel_id: number;
    target_roles: string[];
    target_user_ids: number[];
    target_users: { id: number; label: string }[];
    extra_emails: string;
    notify_event_actor: boolean;
    is_active: boolean;
    note: string;
    template_exists: boolean;
}

export interface NotificationAdminTemplate {
    id: number;
    event_id: number;
    event_label: string;
    event_code: string;
    channel_id: number;
    channel_label: string;
    channel_code: string;
    subject: string;
    body: string;
    is_enabled: boolean;
    updated_at: string;
}

export interface NotificationAdminLog {
    id: number;
    created_at: string;
    event_label: string;
    event_code: string;
    channel_label: string;
    channel_code: string;
    recipient_name: string;
    recipient_address: string;
    status: string;
    status_label: string;
    subject: string;
    error: string;
    can_resend: boolean;
}

async function notificationAdminRequest<T>(
    path: string,
    body?: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    };
    if (body) {
      headers['Content-Type'] = 'application/json';
      headers['X-CSRFToken'] = await getCsrfToken();
    }
    const response = await fetch(path, {
      method: body ? 'POST' : 'GET',
      credentials: 'include',
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
    const data = await response.json() as { error?: string; detail?: string };
    if (!response.ok) {
      throw new Error(data.error || data.detail || `HTTP ${response.status}`);
    }
    return data as T;
}

export const notificationAdminApi = {
    getSettings: (signal?: AbortSignal) =>
      notificationAdminRequest<{ settings: NotificationAdminSettings; channels: { id: number; code: string; label: string; description: string; is_enabled: boolean }[] }>(
        '/notifications/api/admin/settings/',
        undefined,
        signal,
      ),
    saveSettings: (action: string, values: Record<string, unknown>) =>
      notificationAdminRequest<{ ok: boolean; message?: string; settings?: NotificationAdminSettings; delivery_status?: string }>(
        '/notifications/api/admin/settings/',
        { action, ...values },
      ),
    getRules: (signal?: AbortSignal) =>
      notificationAdminRequest<{
        events: { id: number; label: string; code: string; description: string; audience: string }[];
        channels: { id: number; code: string; label: string; is_enabled: boolean }[];
        rules: { event_id: number; channel_id: number; rule: NotificationAdminRule | null }[];
      }>('/notifications/api/admin/rules/', undefined, signal),
    getRule: (eventId: number, channelId: number, signal?: AbortSignal) =>
      notificationAdminRequest<{
        event: { id: number; label: string; code: string; description: string };
        channel: { id: number; label: string; code: string };
        rule: NotificationAdminRule & { users: { id: number; label: string }[] };
      }>(`/notifications/api/admin/rules/${eventId}/${channelId}/`, undefined, signal),
    saveRule: (eventId: number, channelId: number, values: Record<string, unknown>) =>
      notificationAdminRequest<{ ok: boolean; rule: NotificationAdminRule }>(
        `/notifications/api/admin/rules/${eventId}/${channelId}/`,
        values,
      ),
    getTemplates: (signal?: AbortSignal) =>
      notificationAdminRequest<{
        templates: NotificationAdminTemplate[];
        events: { id: number; label: string; code: string }[];
        channels: { id: number; label: string; code: string }[];
      }>('/notifications/api/admin/templates/', undefined, signal),
    saveTemplate: (id: number | null, values: Record<string, unknown>) =>
      notificationAdminRequest<{ ok: boolean; template: NotificationAdminTemplate }>(
        id === null ? '/notifications/api/admin/templates/' : `/notifications/api/admin/templates/${id}/`,
        values,
      ),
    getPatientWaMessages: (signal?: AbortSignal) =>
      notificationAdminRequest<{ messages: Record<string, string> }>(
        '/notifications/api/admin/patient-whatsapp/',
        undefined,
        signal,
      ),
    savePatientWaMessages: (values: Record<string, unknown>) =>
      notificationAdminRequest<{ ok: boolean; message: string }>(
        '/notifications/api/admin/patient-whatsapp/',
        values,
      ),
    getLogs: (params: URLSearchParams, signal?: AbortSignal) =>
      notificationAdminRequest<{
        logs: NotificationAdminLog[];
        filters: { q: string; status: string; channel: string };
        channels: { code: string; label: string }[];
        counts_by_status: Record<string, number>;
        pagination: { number: number; pages: number; total: number; has_previous: boolean; previous: number | null; has_next: boolean; next: number | null };
      }>(`/notifications/api/admin/logs/?${params.toString()}`, undefined, signal),
    resendLog: (logId: number) =>
      notificationAdminRequest<{ ok: boolean; new_log_id: number; status: string; error: string }>(
        '/notifications/api/admin/logs/resend/',
        { log_id: logId },
      ),
};

// ── Patient account ─────────────────────────────────────────────────────────
export interface PatientOverview {
  first_name: string;
  stats: {
    upcoming_appointments: number;
    pending_quotes: number;
    insurances: number;
    cart_items: number;
  };
  next_appointment: {
    reference: string;
    organization: string;
    start: string;
    status: string;
    conversation_url: string | null;
  } | null;
}

export interface PatientInsuranceOption {
  id: number;
  name: string;
  segment: string;
}

export interface PatientInsuranceCategoryRate {
  field: string;
  label: string;
  value: string;
  reference: string;
}

export interface PatientCompatibleStructure {
  name: string;
  location: string;
  url: string;
}

export interface PatientInsuranceData {
  has_insurance: boolean;
  insurance_id: number | null;
  insurance_name: string;
  insurance_number: string;
  insurance_coverage_pct: string;
  insurance_use_in_estimates: boolean;
  insurance_options: PatientInsuranceOption[];
  category_rates: PatientInsuranceCategoryRate[];
  compatible_structures: PatientCompatibleStructure[];
}

export interface PatientSearchHistoryEntry {
  query: string;
  results_count: number;
  searched_at: string;
  url: string;
}

export interface PatientConversationPreview {
  id: number;
  organization: string;
  initial: string;
  subject: string;
  preview: string;
  updated_at: string;
  status: string;
  status_class: 'wait' | 'ok' | 'done' | 'expired' | string;
  unread_count: number;
  url: string;
}

export interface PatientNotification {
  id: number;
  notification_type: string;
  title: string;
  content: string;
  link: string;
  is_read: boolean;
  created_at: string;
  bell_cta: string;
}

export interface PatientThreadMessage {
  kind: 'date' | 'message';
  label?: string;
  id?: number;
  content?: string;
  message_type?: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
  time_label?: string;
  sender?: string | null;
  from_patient?: boolean;
  attachment_url?: string | null;
  attachment_name?: string | null;
}

export interface PatientBookingData {
  org: string;
  org_city: string;
  part: string;
  total: string;
  actes: { acte: string; quantity: number; price: number }[];
  soonest: { value: string; label: string } | null;
  days: {
    label: string;
    short: string;
    slots: { value: string; label: string; available: boolean }[];
  }[];
}

export interface PatientThreadData {
  conversation: {
    id: number;
    organization: string;
    city: string;
    subject: string;
    initial: string;
    status: string;
    status_banner: { class: string; text: string } | null;
    closed: boolean;
    can_send_free_message: boolean;
    can_attach: boolean;
    has_live_rdv: boolean;
    can_book: boolean;
    can_reschedule: boolean;
    can_cancel: boolean;
    rdv_reference: string | null;
    show_book: boolean;
    show_reschedule: boolean;
    has_slots: boolean;
    booking_data: PatientBookingData | null;
    booking_url: string | null;
    cancel_url: string | null;
    url: string;
  };
  devis: {
    reference: string;
    organization: string;
    city: string;
    quartier: string;
    created_at: string;
    total_patient: string;
    lines: { name: string; quantity: number; price: string }[];
  } | null;
  timeline: PatientThreadMessage[];
}

export interface PatientProfile {
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  avatar_url: string | null;
  date_of_birth: string;
  address: string;
  city: string;
  quartier: string;
  last_known_latitude: string;
  last_known_longitude: string;
}

export const patientAccountApi = {
  overview: (signal?: AbortSignal) =>
    request<PatientOverview>('/users/api/patient/overview/', { signal }),
  quotes: (signal?: AbortSignal) =>
    request<{ entries: PatientQuoteEntry[] }>('/users/api/patient/devis/', { signal }),
  insurance: (signal?: AbortSignal) =>
    request<PatientInsuranceData>('/users/api/patient/assurance/', { signal }),
  insuranceDetails: (id: number, signal?: AbortSignal) =>
    request<PatientInsuranceData>(
      `/users/api/patient/assurance/?insurance=${encodeURIComponent(id)}`,
      { signal },
    ),
  saveInsurance: (data: FormData) =>
    postForm<PatientInsuranceData>('/users/api/patient/assurance/', data),
  searchHistory: (signal?: AbortSignal) =>
    request<{ entries: PatientSearchHistoryEntry[] }>(
      '/users/api/patient/recherches/',
      { signal },
    ),
  inbox: (signal?: AbortSignal) =>
    request<{ conversations: PatientConversationPreview[] }>(
      '/messaging/api/patient/inbox/',
      { signal },
    ),
  notifications: (scope: 'inbox' | 'rappels', signal?: AbortSignal) =>
    request<{ notifications: PatientNotification[] }>(
      `/messaging/api/patient/notifications/?scope=${scope}`,
      { signal },
    ),
  markAllNotificationsRead: (scope: 'inbox' | 'rappels') => {
    const data = new FormData();
    data.set('scope', scope);
    return postForm<{ ok: boolean; updated: number }>(
      '/messaging/api/patient/notifications/',
      data,
    );
  },
  conversation: (id: number, query = '', signal?: AbortSignal) =>
    request<PatientThreadData>(
      `/messaging/api/patient/conversations/${id}/${query}`,
      { signal },
    ),
  sendMessage: (id: number, data: FormData) =>
    postForm<{ ok: boolean }>(
      `/messaging/api/patient/conversations/${id}/`,
      data,
    ),
  profile: (signal?: AbortSignal) =>
    request<PatientProfile>('/users/api/patient/profile/', { signal }),
  saveProfile: (data: FormData) =>
    postForm<PatientProfile>('/users/api/patient/profile/', data),
  changePassword: (data: FormData) =>
    postForm<{ ok: boolean }>('/users/api/patient/password/', data),
};

export interface ProviderConversationPreview {
  id: number;
  patient: string;
  initial: string;
  subject: string;
  preview: string;
  updated_at: string;
  status: string;
  status_class: string;
  unread_count: number;
  url: string;
}

export interface MessagingRole {
  role: 'patient' | 'provider';
}

export interface ProviderThreadData {
  conversation: {
    id: number;
    patient: string;
    patient_initial: string;
    organization: string;
    city: string;
    subject: string;
    status: string;
    status_banner: { class: string; text: string } | null;
    closed: boolean;
    allow_reply: boolean;
    actions: {
      label: string;
      url: string;
      method: string;
      style: string;
      confirm: string;
      hidden: Record<string, string>;
    }[];
    url: string;
  };
  devis: PatientThreadData['devis'];
  timeline: PatientThreadMessage[];
}

export interface NotificationPreferenceData {
  events: { id: number; label: string; description: string; audience: string }[];
  channels: { id: number; label: string; description: string }[];
  preferences: { event_id: number; channel_id: number; enabled: boolean }[];
}

export interface GeneralUserProfile {
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  avatar_url: string | null;
}

export interface MobileDemoTicket {
  token: string;
  title: string;
  description: string;
  price: string;
  mode: string;
  zone: string;
  availability: string;
  act: string;
  public_url: string;
  provider: {
    name: string;
    profession: string;
    city: string;
    quartier: string;
    slug: string;
    logo: string | null;
  };
}

export const messagingApi = {
  role: (signal?: AbortSignal) =>
    request<MessagingRole>('/messaging/api/session/', { signal }),
  providerInbox: (signal?: AbortSignal) =>
    request<{ conversations: ProviderConversationPreview[] }>(
      '/messaging/api/provider/inbox/',
      { signal },
    ),
  providerConversation: (id: number, signal?: AbortSignal) =>
    request<ProviderThreadData>(`/messaging/api/provider/conversations/${id}/`, { signal }),
  sendProviderMessage: (id: number, data: FormData) =>
    postForm<{ ok: boolean }>(`/messaging/api/provider/conversations/${id}/`, data),
  providerNotifications: (signal?: AbortSignal) =>
    request<{ notifications: PatientNotification[] }>(
      '/messaging/api/provider/notifications/',
      { signal },
    ),
  markProviderNotificationsRead: () =>
    postForm<{ ok: boolean; updated: number }>(
      '/messaging/api/provider/notifications/',
      new FormData(),
    ),
};

export const notificationPreferencesApi = {
  get: (signal?: AbortSignal) =>
    request<NotificationPreferenceData>('/notifications/api/preferences/', { signal }),
  save: (data: FormData) =>
    postForm<{ ok: boolean }>('/notifications/api/preferences/', data),
};

export const generalProfileApi = {
  get: (signal?: AbortSignal) =>
    request<GeneralUserProfile>('/users/api/profile/', { signal }),
  save: (data: FormData) =>
    postForm<GeneralUserProfile>('/users/api/profile/', data),
};

export const providerSearchHistoryApi = {
  get: (signal?: AbortSignal) =>
    request<{ entries: PatientSearchHistoryEntry[] }>('/sante/api/historique/', { signal }),
};

export const patientMobileApi = {
  get: (signal?: AbortSignal) =>
    request<{ ticket: MobileDemoTicket | null }>('/api/patient-mobile/', { signal }),
};

export interface AdminModelSummary {
  app_label: string;
  model_name: string;
  label: string;
  can_add: boolean;
  can_change: boolean;
  can_delete: boolean;
}

export interface AdminField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  help_text: string;
  value: string | boolean;
  values: string[];
  choices: { value: string; label: string }[];
}

export interface AdminModelList {
  app_label: string;
  model_name: string;
  label: string;
  columns: { name: string; label: string }[];
  rows: { pk: string; values: Record<string, string | number | boolean> }[];
  page: number;
  pages: number;
  total: number;
  can_add: boolean;
  can_change: boolean;
  can_delete: boolean;
}

export interface AdminModelForm {
  label: string;
  fields: AdminField[];
  can_delete?: boolean;
}

export const adminApi = {
  session: (signal?: AbortSignal) =>
    request<{ ok: boolean; username: string }>('/admin/api/session/', { signal }),
  login: (data: FormData) =>
    postForm<{ ok: boolean; username: string }>('/admin/api/session/', data),
  logout: () => postForm<{ ok: boolean }>('/admin/api/logout/', new FormData()),
  models: (signal?: AbortSignal) =>
    request<{ models: AdminModelSummary[] }>('/admin/api/models/', { signal }),
  modelList: (app: string, model: string, query = '', page = 1, signal?: AbortSignal) =>
    request<AdminModelList>(
      `/admin/api/models/${encodeURIComponent(app)}/${encodeURIComponent(model)}/?q=${encodeURIComponent(query)}&page=${page}`,
      { signal },
    ),
  addForm: (app: string, model: string, signal?: AbortSignal) =>
    request<AdminModelForm>(
      `/admin/api/models/${encodeURIComponent(app)}/${encodeURIComponent(model)}/form/`,
      { signal },
    ),
  create: (app: string, model: string, data: FormData) =>
    postForm<{ ok: boolean; pk: string }>(
      `/admin/api/models/${encodeURIComponent(app)}/${encodeURIComponent(model)}/form/`,
      data,
    ),
  modelDetail: (app: string, model: string, pk: string, signal?: AbortSignal) =>
    request<AdminModelForm>(
      `/admin/api/models/${encodeURIComponent(app)}/${encodeURIComponent(model)}/${encodeURIComponent(pk)}/`,
      { signal },
    ),
  update: (app: string, model: string, pk: string, data: FormData) =>
    postForm<{ ok: boolean; pk: string }>(
      `/admin/api/models/${encodeURIComponent(app)}/${encodeURIComponent(model)}/${encodeURIComponent(pk)}/`,
      data,
    ),
  delete: (app: string, model: string, pk: string) => {
    const data = new FormData();
    data.set('action', 'delete');
    return postForm<{ ok: boolean }>(
      `/admin/api/models/${encodeURIComponent(app)}/${encodeURIComponent(model)}/${encodeURIComponent(pk)}/`,
      data,
    );
  },
};

export interface AdminDashboardSummary {
  period: string;
  period_label: string;
  kpis: {
    active_structures: number;
    new_structures: number;
    patients: number;
    quotes: number;
    quotes_total: number;
    quote_value: number;
    confirmed_appointments: number;
    upcoming_appointments: number;
    no_show_pct: number;
    acts: number;
    pioneer_slots_remaining: number;
    pioneer_target: number;
    mrr: number;
  };
  chart: {
    labels: string[];
    quotes: number[];
    patients: number[];
    structures: number[];
    value: number[];
  };
  map: {
    id: number;
    name: string;
    city: string;
    type: string;
    latitude: number;
    longitude: number;
    active: boolean;
  }[];
  pending_organizations: { id: number; name: string; city: string; type: string }[];
  recent_users: { id: number; name: string; email: string; type: string; created_at: string }[];
  services: { id: number; name: string; acts: number }[];
}

export interface AdminDashboardUser {
  id: number;
  username: string;
  name: string;
  email: string;
  type: string;
  type_label: string;
  organization: string;
  is_active: boolean;
  date_joined: string;
}

export interface AdminDashboardOrganization {
  id: number;
  name: string;
  slug: string;
  city: string;
  type: string;
  nature: string;
  user: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface AdminDashboardOrganizationDetail {
  organization: AdminDashboardOrganization & {
    address: string;
    account: string;
    subscription_plan: string;
    public_url: string;
  };
  bilan: {
    score: number;
    signal: string;
    signal_label: string;
    reco: string;
    devis_total: number;
    actes_count: number;
    insurances_count: number;
    completion_pct: number;
  };
  stats: {
    appointments: number;
    pending_appointments: number;
    quotes: number;
    conversations: number;
  };
  recent_appointments: { reference: string; patient: string; status: string; start: string }[];
  recent_quotes: { reference: string; parent_reference: string; patient: string; status: string; created_at: string }[];
  recent_conversations: { id: number; label: string; patient: string; updated_at: string }[];
}

export interface AdminPlatformReview {
  id: number;
  patient: string;
  patient_email: string;
  rating: number;
  comment: string;
  actes: string[];
  is_approved: boolean;
  created_at: string;
}

export interface AdminDashboardList<T> {
  rows: T[];
  pagination: {
    page: number;
    pages: number;
    total: number;
    has_previous: boolean;
    has_next: boolean;
  };
  filters: Record<string, unknown>;
}

export const adminDashboardApi = {
  summary: (period = '7j', signal?: AbortSignal) =>
    request<AdminDashboardSummary>(`/dashboard/api/admin/summary/?period=${encodeURIComponent(period)}`, { signal }),
  users: (filters: { type?: string; q?: string; page?: number }, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    if (filters.type) params.set('type', filters.type);
    if (filters.q) params.set('q', filters.q);
    if (filters.page) params.set('page', String(filters.page));
    return request<AdminDashboardList<AdminDashboardUser>>(`/dashboard/api/admin/utilisateurs/?${params}`, { signal });
  },
  toggleUser: (id: number) =>
    postForm<{ ok: boolean; is_active: boolean }>(`/dashboard/api/admin/utilisateurs/${id}/activer-desactiver/`, new FormData()),
  organizations: (filters: { status?: string; nature?: string; q?: string; page?: number }, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.nature) params.set('nature', filters.nature);
    if (filters.q) params.set('q', filters.q);
    if (filters.page) params.set('page', String(filters.page));
    return request<AdminDashboardList<AdminDashboardOrganization>>(`/dashboard/api/admin/organismes/?${params}`, { signal });
  },
  organization: (id: number, signal?: AbortSignal) =>
    request<AdminDashboardOrganizationDetail>(`/dashboard/api/admin/organismes/${id}/`, { signal }),
  organizationAction: (id: number, action: 'approve' | 'reject') =>
    postForm<{ ok: boolean; is_active: boolean; is_verified: boolean }>(
      `/dashboard/api/admin/organismes/${id}/${action}/`,
      new FormData(),
    ),
  reviews: (filters: { status?: string; page?: number }, signal?: AbortSignal) => {
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.page) params.set('page', String(filters.page));
    return request<{
      rows: AdminPlatformReview[];
      status: string;
      counts: { all: number; pending: number; approved: number };
      pagination: AdminDashboardList<AdminPlatformReview>['pagination'];
    }>(`/dashboard/api/admin/avis/?${params}`, { signal });
  },
  reviewAction: (id: number, action: 'approve' | 'delete') =>
    postForm<{ ok: boolean; is_approved?: boolean; deleted?: boolean }>(
      `/dashboard/api/admin/avis/${id}/${action}/`,
      new FormData(),
    ),
};

export interface PatientQuoteEntry {
  reference: string;
  organization: string;
  created_at: string;
  status: string;
  status_class: string;
  closed: boolean;
  lines: { name: string; quantity: number; subtotal: string }[];
  total_patient: string;
  action: { url: string; label: string } | null;
}

export interface AccountQuoteSummary {
  reference: string;
  created_at: string;
  valid_until: string | null;
  status: string;
  status_code: string;
  insurance: string;
  total_patient: string;
}

export interface AccountQuoteDetail extends AccountQuoteSummary {
  total_brut: string;
  total_assurance: string;
  details: {
    acte: string;
    organisme: string;
    quantity: number;
    subtotal: string;
    coverage_rate: string;
    patient_cost: string;
  }[];
  parts: {
    reference: string;
    organization: string;
    status: string;
    status_code: string;
    total_brut: string;
    whatsapp_url: string;
    phone_url: string;
  }[];
}

export interface CartHistoryEntry {
  id: number;
  name: string;
  updated_at: string;
  status: string;
  status_code: string;
  item_count: number;
  total_price: string;
}

export interface PatientAppointment {
  reference: string;
  organization: string;
  start: string;
  status: string;
  status_label: string;
  status_badge: string;
  location: { quartier: string; city: string; address: string };
  total_patient: string;
  acts: { name: string; quantity: number; subtotal: string }[];
  prerequisites: string;
  conversation_url: string | null;
  can_reschedule: boolean;
  can_cancel: boolean;
}

export const appointmentsApi = {
  patientList: (signal?: AbortSignal) =>
    request<{ upcoming: PatientAppointment[]; past: PatientAppointment[] }>(
      '/rdv/api/patient/rendez-vous/',
      { signal },
    ),
  cancelPatientAppointment: (reference: string) =>
    postForm<{ ok: boolean; message: string }>(
      `/rdv/${encodeURIComponent(reference)}/annuler/`,
      new FormData(),
    ),
  booking: (partReference: string, signal?: AbortSignal) =>
    request<{
      booking_data: PatientBookingData;
      has_slots: boolean;
      submit_url: string;
    }>(`/rdv/reserver/${encodeURIComponent(partReference)}/`, {
      signal,
      headers: { Accept: 'application/json' },
    }),
  submitBooking: (partReference: string, data: FormData) =>
    postForm<{ ok: boolean; message: string; redirect_url: string }>(
      `/rdv/reserver/${encodeURIComponent(partReference)}/`,
      data,
    ),
};

// ── Panels ──────────────────────────────────────────────────────────────────
export interface Panel {
  id: number | string;
  nom: string;
  description: string;
  actes: { id: number | string; nom: string; price: number }[];
  kind?: 'panel' | 'ticket';
  is_active?: boolean;
  token?: string;
  public_path?: string;
  search_url?: string;
  total_price?: number;
  views_count?: number;
  is_prestation_ticket?: boolean;
}

export interface ProviderPanelAct {
  id: number | string;
  nom: string;
  price: number;
  cat?: string;
  sous_cat?: string;
  actif?: boolean;
  configured?: boolean;
}

export interface ProviderPanelsData {
  organization: string;
  panels: Panel[];
  acts: ProviderPanelAct[];
  conversations: { id: number; patient: string; subject: string }[];
}

export interface ProviderTicket {
  id: number;
  title: string;
  description: string;
  price: string;
  mode: 'domicile' | 'cabinet';
  mode_label: string;
  zone: string;
  disponibilite: string;
  is_active: boolean;
  views_count: number;
  identifiant: string;
  public_path: string;
  search_url: string;
  acte: { id: number; name: string } | null;
  created_at: string;
}

export interface ProviderTicketsData {
  organization: string;
  tickets: ProviderTicket[];
  actes: { id: number; name: string; price: string }[];
  conversations: { id: number; patient: string; subject: string }[];
}

export interface PractitionerAffiliationRow {
  id: number;
  name: string;
  city: string;
  role_title: string;
  days_schedule: string[];
  status: string;
  status_label: string;
  initiated_by: string;
  agenda_url: string | null;
}

export interface PractitionerAccessData {
  organization: string;
  is_practitioner: boolean;
  affiliations: PractitionerAffiliationRow[];
  received_invitations: PractitionerAffiliationRow[];
  available_structures: { id: number; name: string; city: string; address: string }[];
  available_practitioners: { id: number; name: string; city: string; profession: string }[];
  days: string[];
}

export interface PractitionerAgendaData {
  organization: string;
  structure: string;
  affiliation_id: number;
  days: string[];
  hours: string[];
  active_slots: string[];
  active_slots_count: number;
}

export const panelsApi = {
  list: (signal?: AbortSignal) =>
    request<ProviderPanelsData>('/sante/prestataire/panels/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  create: (data: FormData) =>
    postForm<{ ok: boolean; id: number; kind: string; nom: string; desc: string; token: string; total_price: number; actes: string[]; url: string }>(
      '/sante/prestataire/panels/creer/',
      data,
    ),
  toggle: (id: number | string) =>
    postForm<{ ok: boolean; is_active: boolean }>(
      `/sante/prestataire/panels/${encodeURIComponent(String(id))}/activer/`,
      new FormData(),
    ),
  delete: (id: number | string) =>
    postForm<{ ok: boolean }>(
      `/sante/prestataire/panels/${encodeURIComponent(String(id))}/supprimer/`,
      new FormData(),
    ),
  send: (data: FormData) =>
    postForm<{ ok: boolean; sent: number; message: string }>(
      '/sante/prestataire/panels/envoyer/',
      data,
    ),
};

export interface BundlePreset {
  id: number;
  name: string;
  teaser: string;
  icon: string;
  description: string;
  acte_ids: number[];
  acte_labels: string[];
}

export interface BundleAct {
  id: number;
  name: string;
}

export interface BundleLine {
  acte_id: number;
  acte_name: string;
  prestataire_acte_id: number;
  organisme_id: number;
  organisme_name: string;
  organisme_slug: string;
  price: string;
}

export interface BundlePlan {
  key: string;
  kind: string;
  title: string;
  subtitle: string;
  center_count: number;
  total_price: string;
  avg_distance_km: number | null;
  lines: BundleLine[];
  missing_actes: string[];
}

export interface BundlePlannerData {
  presets: BundlePreset[];
  initial_actes: BundleAct[];
  is_patient: boolean;
  is_authenticated: boolean;
  urls: {
    plan: string;
    actes: string;
    save: string;
    alternatives: string;
    add_bundle: string;
  };
}

export const bundlePlannerApi = {
  initial: (signal?: AbortSignal) =>
    request<BundlePlannerData>('/sante/parcours/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  searchActs: (url: string, query: string, signal?: AbortSignal) =>
    request<{ results: (BundleAct & { service: string })[] }>(
      `${url}?q=${encodeURIComponent(query)}`,
      { signal },
    ),
  saveSelection: async (url: string, acteIds: number[]) => {
    const csrfToken = await getCsrfToken();
    return request<{ ok: boolean; count: number }>(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ acte_ids: acteIds }),
    });
  },
  compare: async (
    url: string,
    payload: { acte_ids: number[]; save_selection: true; lat?: number; lng?: number },
  ) => {
    const csrfToken = await getCsrfToken();
    return request<{ plans: BundlePlan[]; warnings: string[]; acte_count: number; error?: string }>(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(payload),
      },
    );
  },
  alternatives: (url: string, lat?: number, lng?: number, signal?: AbortSignal) => {
    const query = lat !== undefined && lng !== undefined
      ? `?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`
      : '';
    return request<{ alternatives: BundleLine[] }>(`${url}${query}`, { signal });
  },
  addToCart: async (url: string, ids: number[]) => {
    const csrfToken = await getCsrfToken();
    return request<{ ok: boolean; error?: string; message?: string; cart_url?: string }>(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ prestataire_acte_ids: ids }),
    });
  },
};

export interface CatalogAssistantData {
  has_organization: boolean;
  organization: {
    name: string;
    city: string;
    phone: string;
    email: string;
    nature: string;
    type: string;
    pillar_ids: number[];
  } | null;
  pillars: { id: number; name: string }[];
  organization_types: string[];
  reference_acts: { id: number; n: string; c: string }[];
}

export interface ReconciliationRow {
  raw: string;
  nraw: string;
  st: 'ok' | 'confirm' | 'none';
  via: string;
  sc: number;
  best: number;
  best_nom: string;
  price: number | null;
  delai: string;
}

export interface ReconciliationPayload {
  ok: boolean;
  filename: string;
  display_name?: string;
  rows: ReconciliationRow[];
  stats: { ok: number; cf: number; no: number; total: number };
}

export const catalogAssistantApi = {
  initial: (signal?: AbortSignal) =>
    request<CatalogAssistantData>('/sante/assistant-collecte/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  submitOrganization: async (payload: {
    q1_nature: string;
    q1_type_libre: string;
    q2_piliers: number[];
    q4_nom: string;
    q4_telephone: string;
    q4_email: string;
    q4_city: string;
  }) => {
    const csrfToken = await getCsrfToken();
    return request<{
      ok: boolean;
      errors?: Record<string, string>;
      message?: string;
      import_url: string;
    }>('/sante/api/chatbot/submit/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(payload),
    });
  },
  reconcile: (file: File) => {
    const form = new FormData();
    form.set('file', file);
    return postForm<ReconciliationPayload>('/sante/api/chatbot/reconcile/', form);
  },
  loadPreset: (preset: string, signal?: AbortSignal) =>
    request<ReconciliationPayload>(
      `/sante/api/chatbot/load-preset/?preset=${encodeURIComponent(preset)}`,
      { signal, headers: { Accept: 'application/json' } },
    ),
  apply: async (items: {
    acte_id: number;
    raw: string;
    price: number | null;
    delai: string;
  }[]) => {
    const csrfToken = await getCsrfToken();
    return request<{
      ok: boolean;
      error?: string;
      message: string;
      created_count: number;
      updated_count: number;
      skipped_count: number;
      skipped_labels: string[];
    }>('/sante/api/chatbot/apply-reconciliation/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ items }),
    });
  },
};

export interface PublicTicketData {
  kind: 'ticket' | 'panel';
  token: string;
  title: string;
  description: string;
  price: string;
  provider: { name: string; slug: string; city: string };
  login_url: string;
  signup_url: string;
  cart_url: string;
  contact_url: string;
  mode?: string;
  zone?: string;
  availability?: string;
  act?: string;
  acts?: { name: string; price: string }[];
  preview_only?: boolean;
}

export const publicTicketApi = {
  get: (token: string, query = '', signal?: AbortSignal) =>
    request<PublicTicketData>(`/t/${encodeURIComponent(token)}/${query}`, {
      signal,
      headers: { Accept: 'application/json' },
    }),
  action: async (token: string, action: 'add_cart' | 'request_devis') => {
    const csrfToken = await getCsrfToken();
    const body = new FormData();
    body.set('action', action);
    const response = await fetch(`/t/${encodeURIComponent(token)}/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
      },
      body,
    });
    const result = await response.json() as {
      status?: string;
      ok?: boolean;
      error?: string;
      login_url?: string;
      redirect_url?: string;
      cart_url?: string;
      message?: string;
    };
    if (!response.ok && response.status !== 401) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    return result;
  },
};

export interface PlatformReviewData {
  has_review: boolean;
  google_url: string;
  groups: { service: string; acts: { id: number; name: string }[] }[];
  selected_acte_ids: number[];
}

export const accountSecurityApi = {
  changePassword: (form: FormData) =>
    postForm<{ ok: boolean; message: string }>('/users/mot-de-passe/', form),
  requestPasswordReset: (form: FormData) =>
    postForm<{ ok: boolean; message: string }>('/api/auth/password-reset/', form),
  checkResetToken: (uid: string, token: string, signal?: AbortSignal) =>
    request<{ valid: boolean }>(
      `/api/auth/password-reset/confirm/${encodeURIComponent(uid)}/${encodeURIComponent(token)}/`,
      { signal, headers: { Accept: 'application/json' } },
    ),
  resetPassword: (uid: string, token: string, form: FormData) =>
    postForm<{ ok: boolean; redirect_url: string }>(
      `/api/auth/password-reset/confirm/${encodeURIComponent(uid)}/${encodeURIComponent(token)}/`,
      form,
    ),
};

export const platformReviewApi = {
  get: (signal?: AbortSignal) =>
    request<PlatformReviewData>('/sante/avis/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  submit: (form: FormData) =>
    postForm<{ ok: boolean; message: string; redirect_url: string }>('/sante/avis/', form),
  googleUrl: (signal?: AbortSignal) =>
    request<{ google_reviews_url: string }>('/sante/avis/google/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
};

export const practitionerPortalApi = {
  getTickets: (signal?: AbortSignal) =>
    request<ProviderTicketsData>('/sante/prestataire/tickets/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  createTicket: (data: FormData) =>
    postForm<{ ok: boolean; id: number; title: string; public_path: string; message: string }>(
      '/sante/prestataire/tickets/creer/',
      data,
    ),
  toggleTicket: (id: number) =>
    postForm<{ status: string; is_active: boolean }>(
      `/sante/prestataire/tickets/${id}/activer/`,
      new FormData(),
    ),
  deleteTicket: (id: number) =>
    postForm<{ ok: boolean; message: string }>(
      `/sante/prestataire/tickets/${id}/supprimer/`,
      new FormData(),
    ),
  sendTicket: (data: FormData) =>
    postForm<{ ok: boolean; sent: number; message: string }>(
      '/sante/prestataire/tickets/envoyer/',
      data,
    ),
  getAccess: (signal?: AbortSignal) =>
    request<PractitionerAccessData>('/sante/prestataire/acces/', {
      signal,
      headers: { Accept: 'application/json' },
    }),
  createAffiliation: (data: FormData) =>
    postForm<{ ok: boolean; id: number; message: string }>(
      '/sante/prestataire/acces/affiliation/creer/',
      data,
    ),
  invitePractitioner: (data: FormData) =>
    postForm<{ ok: boolean; id: number; message: string }>(
      '/sante/prestataire/acces/affiliation/inviter/',
      data,
    ),
  acceptAffiliation: (id: number) =>
    postForm<{ ok: boolean; message: string }>(
      `/sante/prestataire/acces/affiliation/${id}/accepter/`,
      new FormData(),
    ),
  approveAffiliation: (id: number) =>
    postForm<{ ok: boolean; message: string }>(
      `/sante/prestataire/acces/affiliation/${id}/valider/`,
      new FormData(),
    ),
  deleteAffiliation: (id: number) =>
    postForm<{ ok: boolean; message: string }>(
      `/sante/prestataire/acces/affiliation/${id}/supprimer/`,
      new FormData(),
    ),
  getPractitionerAgenda: (affiliationId: number, signal?: AbortSignal) =>
    request<PractitionerAgendaData>(
      `/sante/prestataire/acces/agenda/${affiliationId}/`,
      { signal, headers: { Accept: 'application/json' } },
    ),
  savePractitionerAgenda: (affiliationId: number, data: FormData) =>
    postForm<{ ok: boolean; message: string }>(
      `/sante/prestataire/acces/agenda/${affiliationId}/`,
      data,
    ),
};
