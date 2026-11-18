import { getCsrfToken } from './auth';

const API = '/dashboard/api/admin/activite';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...init?.headers,
    },
  });
  const data = await response.json() as { error?: string; [key: string]: unknown };
  if (!response.ok) throw new Error(data.error || `Erreur HTTP ${response.status}`);
  return data as T;
}

function queryString(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && String(value) !== '') query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : '';
}

async function mutate<T>(path: string, method: 'POST' | 'PUT' | 'PATCH' | 'DELETE', body?: unknown) {
  const csrfToken = await getCsrfToken();
  return request<T>(path, {
    method,
    headers: { 'X-CSRFToken': csrfToken },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export interface AdminActivityUser {
  id: number;
  username: string;
  name: string;
  email: string;
}

export interface AdminActivityQuote {
  reference: string;
  patient: AdminActivityUser;
  insurance: { id: number; name: string } | null;
  status: string;
  status_label: string;
  total_brut: number;
  total_assurance: number;
  total_patient: number;
  details: Record<string, unknown>[];
  notes: string;
  created_at: string;
  valid_until: string | null;
  relance_count: number;
  max_relances: number;
  can_relance: boolean;
  is_archived: boolean;
  archived_at: string | null;
  organizations?: string[];
  parts_count?: number;
  parts?: {
    id: number;
    reference: string;
    organization: { id: number; name: string };
    status: string;
    status_label: string;
    total_brut: number;
    relance_count: number;
    can_relance: boolean;
    is_archived: boolean;
    conversation: { id: number; label: string } | null;
    appointment: { reference: string } | null;
  }[];
}

export interface AdminActivityAppointment {
  reference: string;
  patient: AdminActivityUser | null;
  patient_label: string;
  patient_phone: string;
  organization: { id: number; name: string };
  devis_reference: string | null;
  devis_part_reference: string | null;
  start: string;
  end: string | null;
  source: string;
  source_label: string;
  status: string;
  status_label: string;
  total_brut: number;
  total_patient: number;
  created_at: string;
  confirmed_at?: string | null;
  patient_note?: string;
  prestataire_note?: string;
  cancel_reason?: string;
  actes_snapshot?: Record<string, unknown>[];
  prerequisites?: string;
  conversation?: { id: number; label: string } | null;
}

export interface AdminActivityConversation {
  id: number;
  label: string;
  subject: string;
  patient: AdminActivityUser;
  prestataire: AdminActivityUser;
  organization: { id: number; name: string } | null;
  kind: string;
  kind_label: string;
  status: string;
  status_label: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  devis_part_reference: string | null;
  devis_reference: string | null;
  appointment_reference: string | null;
  last_message: { content: string; timestamp: string } | null;
}

export interface AdminActivityPage<T> {
  rows: T[];
  pagination: {
    page: number;
    pages: number;
    total: number;
    has_previous: boolean;
    has_next: boolean;
  };
  counts: Record<string, number>;
  filters: Record<string, string>;
}

export interface AdminReminderSchedule {
  id: number;
  label: string;
  offset_value: number;
  offset_unit: 'minutes' | 'hours' | 'days';
  offset_unit_label: string;
  offset_display: string;
  tolerance_minutes: number;
  include_prerequisites: boolean;
  is_active: boolean;
  order: number;
  actes: { id: number; name: string }[];
  sent_count: number;
}

export interface AdminReminderScheduleInput {
  label: string;
  offset_value: number;
  offset_unit: 'minutes' | 'hours' | 'days';
  tolerance_minutes: number;
  include_prerequisites: boolean;
  is_active: boolean;
  order: number;
  actes: number[];
}

export const adminActivityApi = {
  overview: (signal?: AbortSignal) =>
    request<{
      kpis: Record<string, number>;
      recent_quotes: AdminActivityQuote[];
      recent_appointments: AdminActivityAppointment[];
      recent_conversations: AdminActivityConversation[];
    }>('/overview/', { signal }),
  quotes: (params: { status?: string; q?: string; page?: number }, signal?: AbortSignal) =>
    request<AdminActivityPage<AdminActivityQuote> & {
      kpis: Record<string, number>;
    }>(`/devis/${queryString(params)}`, { signal }),
  quote: (reference: string, signal?: AbortSignal) =>
    request<{ quote: AdminActivityQuote }>(`/devis/${encodeURIComponent(reference)}/`, { signal }),
  quoteAction: (reference: string, action: 'relance' | 'archive') =>
    mutate<{ message: string; quote: AdminActivityQuote }>(
      `/devis/${encodeURIComponent(reference)}/${action}/`, 'POST',
    ),
  appointments: (params: { status?: string; q?: string; org?: string; page?: number }, signal?: AbortSignal) =>
    request<AdminActivityPage<AdminActivityAppointment> & {
      kpis: Record<string, number>;
    }>(`/rdv/${queryString(params)}`, { signal }),
  appointment: (reference: string, signal?: AbortSignal) =>
    request<{ appointment: AdminActivityAppointment }>(
      `/rdv/${encodeURIComponent(reference)}/`, { signal },
    ),
  reminderSchedules: (signal?: AbortSignal) =>
    request<{ rows: AdminReminderSchedule[]; act_options: { id: number; name: string }[] }>(
      '/rappels/', { signal },
    ),
  reminderSchedule: (id: number, signal?: AbortSignal) =>
    request<{ schedule: AdminReminderSchedule }>(`/rappels/${id}/`, { signal }),
  createReminderSchedule: (data: AdminReminderScheduleInput) =>
    mutate<{ schedule: AdminReminderSchedule }>('/rappels/', 'POST', data),
  updateReminderSchedule: (id: number, data: AdminReminderScheduleInput) =>
    mutate<{ schedule: AdminReminderSchedule }>(`/rappels/${id}/`, 'PUT', data),
  deleteReminderSchedule: (id: number) =>
    mutate<{ message: string }>(`/rappels/${id}/`, 'DELETE'),
  conversations: (params: { kind?: string; status?: string; q?: string; page?: number }, signal?: AbortSignal) =>
    request<AdminActivityPage<AdminActivityConversation> & {
      kpis: Record<string, number>;
    }>(`/messages/${queryString(params)}`, { signal }),
  conversation: (id: number, signal?: AbortSignal) =>
    request<{
      conversation: AdminActivityConversation;
      messages: {
        id: number;
        sender: AdminActivityUser;
        sender_id: number;
        content: string;
        timestamp: string;
        message_type: string;
        message_type_label: string;
      }[];
    }>(`/messages/${id}/`, { signal }),
};
