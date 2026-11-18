import { getCsrfToken } from './auth';

const BASE = '/dashboard/api/reports';

export interface AdminReportPlan {
  id: number;
  name: string;
  slug: string;
  short_description: string;
  long_description: string;
  monthly_price_fcfa: number;
  is_default: boolean;
  is_public: boolean;
  is_pioneer_offer: boolean;
  trial_months: number | null;
  order: number;
  orgs_count: number;
  included_feature_ids: number[];
}

export interface AdminReportFeature {
  id: number;
  code: string;
  label: string;
  description: string;
}

export interface AdminReportOrganization {
  id: number;
  name: string;
  slug: string;
  city: string;
  type: string;
  is_active: boolean;
  plan_id: number | null;
  plan_name: string;
  plan_slug: string;
  monthly_price_fcfa: number;
  subscription_started_at: string | null;
  subscription_renewal_at: string | null;
  subscription_auto_renew: boolean;
  expires_soon: boolean;
  profile_views_count: number;
}

export interface SubscriptionsReport {
  plan_filter: string;
  in_30_days: string;
  kpis: { active_organizations: number; expiring_soon: number; pending_upgrades: number; mrr: number };
  plans: AdminReportPlan[];
  features: AdminReportFeature[];
  organizations: AdminReportOrganization[];
}

export interface FinancesReport {
  today: string;
  kpis: { mrr: number; arr: number; service_fees: number; estimated_conversion: string };
  plan_rows: { plan: AdminReportPlan; subtotal: number }[];
  months: string[];
  scenarios: { pessimiste: number[]; median: number[]; optimiste: number[] };
}

export interface PioneersReport {
  target: number;
  signed: number;
  active: number;
  pending: number;
  onboarding: number;
  remaining: number;
  progress_pct: number;
  rows: {
    reference: string;
    organization: AdminReportOrganization;
    score: number;
    signal: string;
    signal_label: string;
    acts: number;
  }[];
}

export interface BilansReport {
  rows: {
    organization: AdminReportOrganization;
    score: number;
    signal: string;
    signal_label: string;
    recommendation: string;
    devis_total: number;
    actes_count: number;
    insurances_count: number;
    completion_pct: number;
  }[];
  counts: { green: number; amber: number; red: number };
  total: number;
}

export interface ComplianceReport {
  checklist: { key: string; label: string; detail: string; suggested: boolean; ok: boolean }[];
  completed: number;
  total: number;
  updated_at: string | null;
  logs: {
    id: number;
    action_time: string;
    actor: string;
    action_flag: number;
    content_type: string;
    object_repr: string;
  }[];
}

async function request<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET') headers['X-CSRFToken'] = await getCsrfToken();
  const response = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  let data: { ok?: boolean; error?: string; details?: Record<string, { message: string }[]> } & T;
  try {
    data = await response.json() as typeof data;
  } catch {
    throw new Error(`Réponse invalide du serveur (HTTP ${response.status}).`);
  }
  if (!response.ok || data.ok === false) {
    const fieldErrors = Object.values(data.details || {}).flat().map((item) => item.message);
    throw new Error(data.error || fieldErrors.join(' ') || `Erreur HTTP ${response.status}.`);
  }
  return data;
}

export const adminReportApi = {
  subscriptions: (filter = 'all', signal?: AbortSignal) =>
    request<SubscriptionsReport>(`/subscriptions/?plan=${encodeURIComponent(filter)}`, 'GET', undefined, signal),
  finances: (signal?: AbortSignal) => request<FinancesReport>('/finances/', 'GET', undefined, signal),
  pioneers: (signal?: AbortSignal) => request<PioneersReport>('/pioneers/', 'GET', undefined, signal),
  bilans: (signal?: AbortSignal) => request<BilansReport>('/bilans/', 'GET', undefined, signal),
  compliance: (signal?: AbortSignal) => request<ComplianceReport>('/compliance/', 'GET', undefined, signal),
  assignPlan: (organizationId: number, planSlug: string) =>
    request(`/subscriptions/organizations/${organizationId}/assign/`, 'POST', { plan_slug: planSlug }),
  toggleFeature: (planId: number, featureId: number) =>
    request<{ included: boolean }>(`/subscriptions/plans/${planId}/features/${featureId}/toggle/`, 'POST', {}),
  savePlan: (payload: Record<string, unknown>, planId?: number) =>
    request<{ plan: AdminReportPlan }>(
      planId ? `/subscriptions/plans/${planId}/` : '/subscriptions/plans/',
      planId ? 'PATCH' : 'POST',
      payload,
    ),
  deletePlan: (planId: number) => request(`/subscriptions/plans/${planId}/`, 'DELETE'),
  saveCompliance: (checks: Record<string, boolean>) =>
    request('/compliance/', 'PUT', { checks }),
};
