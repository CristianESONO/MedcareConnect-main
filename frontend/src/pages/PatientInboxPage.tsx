import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle, Search } from 'lucide-react';
import { patientAccountApi, type PatientConversationPreview } from '../lib/api';

function formatConversationDate(value: string) {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const sameDay = (left: Date, right: Date) => left.toDateString() === right.toDateString();

  if (sameDay(date, today)) {
    return new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' }).format(date);
  }
  if (sameDay(date, yesterday)) return 'Hier';
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short' }).format(date);
}

function conversationBadgeClass(status: PatientConversationPreview['status_class']) {
  switch (status) {
    case 'wait':
      return 'bg-amber-100 text-amber-800';
    case 'done':
      return 'bg-blue-50 text-blue-700';
    case 'expired':
      return 'bg-gray-100 text-gray-600';
    default:
      return 'bg-emerald-50 text-emerald-800';
  }
}

export function PatientInboxPage() {
  const [conversations, setConversations] = useState<PatientConversationPreview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    patientAccountApi.inbox(controller.signal)
      .then((data) => setConversations(data.conversations))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger vos messages.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6 flex items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
          <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
            <MessageCircle size={24} aria-hidden="true" />
            Messagerie
          </h1>
        </div>
        <Link to="/sante/recherche/" className="hidden rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#0a5c8a] hover:bg-sky-50 sm:inline-flex">
          <Search size={16} className="mr-2" aria-hidden="true" />
          Prestations
        </Link>
      </header>

      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement des conversations…
        </p>
      )}
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          {error}
          {error.includes('Authentification') && (
            <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">
              Se connecter
            </Link>
          )}
        </p>
      )}

      {!loading && !error && (conversations.length ? (
        <div className="divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {conversations.map((conversation) => (
            <a
              key={conversation.id}
              href={conversation.url}
              className="flex items-center gap-3 p-4 transition hover:bg-sky-50 sm:gap-4 sm:px-5"
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sm font-bold text-[#0a5c8a]">
                {conversation.initial}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-gray-900">{conversation.organization}</span>
                  <time className="shrink-0 text-[11px] text-gray-400">{formatConversationDate(conversation.updated_at)}</time>
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-gray-400">{conversation.subject}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide ${conversationBadgeClass(conversation.status_class)}`}>
                    {conversation.status}
                  </span>
                </span>
                {conversation.preview && (
                  <span className="mt-1 block truncate text-xs text-gray-500">{conversation.preview}</span>
                )}
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
          <h2 className="mt-3 font-semibold text-gray-700">Aucun message pour l’instant</h2>
          <p className="mt-1 text-sm text-gray-500">Ajoutez des actes au panier puis demandez un rendez-vous.</p>
          <Link to="/sante/recherche/" className="mt-4 inline-block rounded-lg bg-[#0a5c8a] px-5 py-2.5 text-sm font-bold text-white">
            Parcourir les prestations
          </Link>
        </div>
      ))}
    </section>
  );
}
