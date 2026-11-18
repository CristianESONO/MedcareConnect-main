import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, MessageCircle } from 'lucide-react';
import { patientAccountApi, type PatientQuoteEntry } from '../lib/api';

const ACCOUNT_LINKS = [
  { label: 'Tableau de bord', href: '/users/compte/panel/accueil/' },
  { label: 'Mes rendez-vous', href: '/users/compte/panel/rdv/' },
  { label: 'Assurance', href: '/users/compte/panel/assurance/' },
  { label: 'Mes informations', href: '/users/compte/panel/profil/' },
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function quoteBadgeClass(statusClass: string) {
  switch (statusClass) {
    case 'pac-badge--ok':
      return 'bg-emerald-50 text-emerald-800';
    case 'pac-badge--done':
      return 'bg-blue-50 text-blue-800';
    case 'pac-badge--expired':
      return 'bg-gray-100 text-gray-600';
    default:
      return 'bg-amber-50 text-amber-800';
  }
}

function QuoteCard({ quote }: { quote: PatientQuoteEntry }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-gray-100 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="font-bold text-[#123a63]">{quote.organization}</h2>
          <p className="mt-1 text-xs text-gray-500">
            Réf. {quote.reference} · {formatDate(quote.created_at)}
          </p>
        </div>
        <span className={`w-fit shrink-0 rounded-full px-3 py-1 text-xs font-bold ${quoteBadgeClass(quote.status_class)}`}>
          {quote.status}
        </span>
      </div>

      <div className="p-5">
        <div className="divide-y divide-gray-100">
          {quote.lines.map((line, index) => (
            <div key={`${line.name}-${index}`} className="flex justify-between gap-3 py-2 text-sm first:pt-0 last:pb-0">
              <span className="text-gray-700">
                {line.name}{line.quantity > 1 ? ` × ${line.quantity}` : ''}
              </span>
              <span className="shrink-0 font-semibold text-gray-600">
                {Number(line.subtotal).toLocaleString('fr-FR')} F
              </span>
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-syne text-lg font-extrabold text-[#123a63]">
            {Number(quote.total_patient).toLocaleString('fr-FR')} FCFA
          </p>
          {quote.action ? (
            <a
              href={quote.action.url}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#084b70]"
            >
              <MessageCircle size={16} aria-hidden="true" />
              {quote.action.label}
            </a>
          ) : quote.closed ? (
            <span className="text-xs text-gray-400">Devis clos</span>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function PatientQuotesPage() {
  const [quotes, setQuotes] = useState<PatientQuoteEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    patientAccountApi.quotes(controller.signal)
      .then((data) => setQuotes(data.entries))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger vos devis.');
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
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          Mes devis
        </h1>
      </header>

      <nav className="mb-6 flex gap-2 overflow-x-auto pb-1" aria-label="Navigation du compte patient">
        {ACCOUNT_LINKS.map((item) => (
          <a key={item.href} href={item.href} className="shrink-0 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-600 hover:border-sky-300 hover:text-[#0a5c8a]">
            {item.label}
          </a>
        ))}
        <span className="shrink-0 rounded-full bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white" aria-current="page">
          Mes devis
        </span>
      </nav>

      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement des devis…
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

      {!loading && !error && (quotes.length ? (
        <div className="space-y-3">
          {quotes.map((quote, index) => (
            <QuoteCard key={`${quote.reference}-${index}`} quote={quote} />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-7 text-center">
          <FileText size={28} className="mx-auto text-gray-400" aria-hidden="true" />
          <h2 className="mt-3 font-semibold text-gray-700">Aucun devis généré</h2>
          <p className="mt-1 text-sm text-gray-500">Ajoutez des actes au panier, puis demandez votre estimation.</p>
          <Link to="/sante/recherche/" className="mt-4 inline-block rounded-lg bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white">
            Parcourir les prestations
          </Link>
        </div>
      ))}
    </section>
  );
}
