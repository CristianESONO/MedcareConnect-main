import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, MessageCircle, Paperclip, Send } from 'lucide-react';
import {
  messagingApi,
  type PatientNotification,
  type ProviderConversationPreview,
  type ProviderThreadData,
} from '../lib/api';
import { getCsrfToken } from '../lib/auth';
import { PatientInboxPage } from './PatientInboxPage';
import { PatientConversationPage } from './PatientConversationPage';
import { PatientNotificationsPage } from './PatientNotificationsPage';

function MessagingRoleGate({
  patient,
  provider,
}: {
  patient: ReactNode;
  provider: ReactNode;
}) {
  const [role, setRole] = useState<'patient' | 'provider' | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    messagingApi.role(controller.signal)
      .then((data) => setRole(data.role))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de vérifier votre compte.');
        }
      });
    return () => controller.abort();
  }, []);

  if (error) {
    return (
      <p className="mx-auto mt-8 max-w-5xl rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
        {error}
        {error.includes('Authentification') && (
          <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">
            Se connecter
          </Link>
        )}
      </p>
    );
  }
  if (!role) {
    return <p className="mx-auto max-w-5xl px-4 py-8 text-sm text-gray-600" role="status">Chargement…</p>;
  }
  return role === 'patient' ? patient : provider;
}

export function MessagingInboxRoute() {
  return (
    <MessagingRoleGate
      patient={<PatientInboxPage />}
      provider={<ProviderInboxPage />}
    />
  );
}

export function MessagingConversationRoute() {
  const { conversationId = '' } = useParams();
  return (
    <MessagingRoleGate
      patient={<PatientConversationPage />}
      provider={<ProviderConversationPage key={conversationId} conversationId={Number(conversationId)} />}
    />
  );
}

export function MessagingNotificationsRoute() {
  return (
    <MessagingRoleGate
      patient={<PatientNotificationsPage />}
      provider={<ProviderNotificationsPage />}
    />
  );
}

function conversationDate(value: string) {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' }).format(date);
  }
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short' }).format(date);
}

function statusStyle(status: string) {
  if (status === 'wait') return 'bg-amber-100 text-amber-800';
  if (status === 'done') return 'bg-blue-50 text-blue-700';
  if (status === 'expired') return 'bg-gray-100 text-gray-600';
  return 'bg-emerald-50 text-emerald-800';
}

function ProviderInboxPage() {
  const [conversations, setConversations] = useState<ProviderConversationPreview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    messagingApi.providerInbox(controller.signal)
      .then((data) => setConversations(data.conversations))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les messages.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace prestataire</p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          <MessageCircle size={24} aria-hidden="true" /> Messages
        </h1>
        <p className="mt-2 text-sm text-gray-500">Fils de discussion par patient et par dossier (devis ou rendez-vous).</p>
      </header>

      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement des conversations…</p>}
      {error && <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {!loading && !error && (conversations.length ? (
        <div className="divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {conversations.map((conversation) => (
            <a key={conversation.id} href={conversation.url} className="flex items-center gap-3 p-4 transition hover:bg-sky-50 sm:gap-4 sm:px-5">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sm font-bold text-[#0a5c8a]">
                {conversation.initial}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-gray-900">{conversation.patient}</span>
                  <time className="shrink-0 text-[11px] text-gray-400">{conversationDate(conversation.updated_at)}</time>
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-gray-400">{conversation.subject}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide ${statusStyle(conversation.status_class)}`}>
                    {conversation.status}
                  </span>
                </span>
                {conversation.preview && <span className="mt-1 block truncate text-xs text-gray-500">{conversation.preview}</span>}
              </span>
              {conversation.unread_count > 0 && (
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white" aria-label={`${conversation.unread_count} messages non lus`}>
                  {conversation.unread_count}
                </span>
              )}
            </a>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <MessageCircle size={34} className="mx-auto text-gray-300" aria-hidden="true" />
          <h2 className="mt-3 font-semibold text-gray-700">Aucun fil pour l’instant</h2>
          <p className="mt-1 text-sm text-gray-500">Les demandes de devis et de rendez-vous apparaîtront ici.</p>
        </div>
      ))}
    </section>
  );
}

function ProviderConversationPage({ conversationId }: { conversationId: number }) {
  const [data, setData] = useState<ProviderThreadData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadConversation = useCallback(async () => {
    const response = await messagingApi.providerConversation(conversationId);
    setData(response);
  }, [conversationId]);

  useEffect(() => {
    let active = true;
    messagingApi.providerConversation(conversationId)
      .then((response) => {
        if (active) setData(response);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Impossible de charger cette conversation.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [conversationId]);

  const sendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    setError('');
    setSaving(true);
    try {
      await messagingApi.sendProviderMessage(conversationId, new FormData(form));
      form.reset();
      await loadConversation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’envoyer le message.');
    } finally {
      setSaving(false);
    }
  };

  const runAction = async (
    action: ProviderThreadData['conversation']['actions'][number],
  ) => {
    if (action.confirm && !window.confirm(action.confirm)) return;
    setError('');
    setSaving(true);
    try {
      const csrfToken = await getCsrfToken();
      const body = new FormData();
      Object.entries(action.hidden).forEach(([key, value]) => body.set(key, value));
      const response = await fetch(action.url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' },
        body,
      });
      if (!response.ok) throw new Error(`Impossible d’effectuer l’action (${response.status}).`);
      await loadConversation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’effectuer cette action.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="mx-auto max-w-5xl px-4 py-8 text-sm text-gray-600" role="status">Chargement de la conversation…</p>;
  if (error && !data) return <p className="mx-auto mt-8 max-w-5xl rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>;
  if (!data) return null;

  const conversation = data.conversation;
  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-6 sm:py-8">
      <Link to="/messaging/" className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-[#0a5c8a] hover:underline">
        <ArrowLeft size={16} aria-hidden="true" /> Retour aux messages
      </Link>
      <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <header className="flex items-center gap-3 border-b border-gray-100 p-4 sm:px-6">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-sky-50 font-bold text-[#0a5c8a]">{conversation.patient_initial}</span>
          <div className="min-w-0">
            <h1 className="truncate font-syne text-lg font-bold text-[#123a63]">{conversation.patient}</h1>
            <p className="truncate text-xs text-gray-500">{conversation.subject}{conversation.city ? ` · ${conversation.city}` : ''}</p>
          </div>
          <span className="ml-auto rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">{conversation.status}</span>
        </header>

        <div className="max-h-[65vh] min-h-64 space-y-3 overflow-y-auto bg-gray-50/70 p-4 sm:p-6">
          {conversation.status_banner && (
            <p className="mx-auto max-w-lg rounded-full bg-sky-50 px-4 py-2 text-center text-xs font-semibold text-sky-800">
              {conversation.status_banner.text}
            </p>
          )}
          {data.devis && (
            <section className="mx-auto w-full max-w-xl rounded-xl border border-sky-100 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-sky-700">Devis {data.devis.reference}</p>
              <ul className="mt-3 space-y-2">
                {data.devis.lines.map((line, index) => (
                  <li key={`${line.name}-${index}`} className="flex justify-between gap-3 text-sm text-gray-700">
                    <span>{line.name}{line.quantity > 1 ? ` × ${line.quantity}` : ''}</span>
                    <span className="shrink-0 font-semibold">{line.price} FCFA</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 border-t border-gray-100 pt-3 text-right text-sm font-bold text-[#123a63]">Total patient : {data.devis.total_patient} FCFA</p>
            </section>
          )}
          {data.timeline.map((item, index) => item.kind === 'date' ? (
            <p key={`date-${index}`} className="py-1 text-center text-xs font-semibold text-gray-400">{item.label}</p>
          ) : (
            <div key={item.id ?? index} className={`flex ${item.from_patient ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm sm:max-w-[75%] ${item.from_patient ? 'rounded-tl-sm bg-white text-gray-800' : 'rounded-tr-sm bg-[#0a5c8a] text-white'}`}>
                {item.sender && <p className={`mb-1 text-[10px] font-bold ${item.from_patient ? 'text-sky-700' : 'text-white/75'}`}>{item.sender}</p>}
                <p className="whitespace-pre-wrap break-words text-sm">{item.content}</p>
                {item.attachment_url && (
                  <a href={item.attachment_url} target="_blank" rel="noreferrer" className={`mt-2 inline-flex items-center gap-1 text-xs underline ${item.from_patient ? 'text-sky-700' : 'text-white'}`}>
                    <Paperclip size={13} aria-hidden="true" /> {item.attachment_name || 'Pièce jointe'}
                  </a>
                )}
                <p className={`mt-1 text-right text-[10px] ${item.from_patient ? 'text-gray-400' : 'text-white/70'}`}>{item.time_label}</p>
              </div>
            </div>
          ))}
        </div>

        {error && <p className="border-t border-red-100 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">{error}</p>}
        {conversation.actions.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t border-gray-100 p-4 sm:px-6">
            {conversation.actions.map((action) => (
              <button
                key={`${action.url}-${action.label}`}
                type="button"
                disabled={saving}
                onClick={() => { void runAction(action); }}
                className={`rounded-lg px-4 py-2 text-sm font-bold disabled:opacity-60 ${action.style === 'danger' ? 'bg-red-50 text-red-700 hover:bg-red-100' : 'bg-emerald-600 text-white hover:bg-emerald-700'}`}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
        {conversation.allow_reply && (
          <form onSubmit={sendMessage} className="flex items-center gap-2 border-t border-gray-100 p-3 sm:p-4">
            <label className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full text-gray-500 hover:bg-gray-100" aria-label="Joindre un fichier">
              <Paperclip size={18} aria-hidden="true" />
              <input name="attachment" type="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,image/*,application/pdf" className="sr-only" />
            </label>
            <input name="content" maxLength={500} autoComplete="off" placeholder="Message…" className="min-w-0 flex-1 rounded-full border border-gray-200 px-4 py-2.5 text-sm outline-none focus:border-sky-500" />
            <button type="submit" disabled={saving} aria-label="Envoyer le message" className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#0a5c8a] text-white hover:bg-[#084b70] disabled:opacity-60">
              <Send size={17} aria-hidden="true" />
            </button>
          </form>
        )}
      </article>
    </section>
  );
}

function ProviderNotificationsPage() {
  const [notifications, setNotifications] = useState<PatientNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadNotifications = useCallback(async () => {
    const data = await messagingApi.providerNotifications();
    setNotifications(data.notifications);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    messagingApi.providerNotifications(controller.signal)
      .then((data) => setNotifications(data.notifications))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les notifications.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const markAllRead = async () => {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      await messagingApi.markProviderNotificationsRead();
      await loadNotifications();
      setNotice('Toutes les notifications sont marquées comme lues.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de mettre à jour les notifications.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace prestataire</p>
          <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Notifications</h1>
        </div>
        <button type="button" onClick={() => { void markAllRead(); }} disabled={saving || !notifications.some((item) => !item.is_read)} className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50">
          Tout marquer comme lu
        </button>
      </header>
      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement…</p>}
      {!loading && !error && (notifications.length ? (
        <div className="divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {notifications.map((item) => (
            <a key={item.id} href={`/messaging/notifications/${item.id}/lu/`} className={`block p-4 transition hover:bg-sky-50 sm:px-5 ${item.is_read ? '' : 'bg-sky-50/50'}`}>
              <div className="flex items-start gap-3">
                <span className={`mt-1 size-2 shrink-0 rounded-full ${item.is_read ? 'bg-gray-300' : 'bg-sky-600'}`} aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-gray-900">{item.title}</span>
                    <time className="text-xs text-gray-400">{conversationDate(item.created_at)}</time>
                  </span>
                  {item.content && <span className="mt-1 block whitespace-pre-line text-sm text-gray-600">{item.content}</span>}
                  {item.bell_cta && <span className="mt-2 block text-xs font-bold text-[#0a5c8a]">{item.bell_cta} →</span>}
                </span>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">Aucune notification pour le moment.</div>
      ))}
      <Link to="/notifications/preferences/" className="mt-5 inline-block text-sm font-semibold text-[#0a5c8a] hover:underline">Gérer mes préférences de notifications →</Link>
    </section>
  );
}
