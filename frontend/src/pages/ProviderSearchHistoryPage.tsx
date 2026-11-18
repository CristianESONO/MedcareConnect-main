import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { providerSearchHistoryApi, type PatientSearchHistoryEntry } from '../lib/api';

function dateLabel(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function ProviderSearchHistoryPage() {
  const [entries, setEntries] = useState<PatientSearchHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    providerSearchHistoryApi.get(controller.signal)
      .then((data) => setEntries(data.entries))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger l’historique.');
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
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Historique des recherches</h1>
        <p className="mt-2 text-sm text-gray-500">Retrouvez les dernières recherches effectuées avec ce compte.</p>
      </header>
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement de l’historique…</p>}
      {error && <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {!loading && !error && (entries.length ? (
        <div className="divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {entries.map((entry, index) => (
            <a key={`${entry.searched_at}-${index}`} href={entry.url} className="flex items-center gap-3 p-4 transition hover:bg-sky-50 sm:p-5">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-sky-50 text-[#0a5c8a]"><Search size={18} aria-hidden="true" /></span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-gray-900">{entry.query}</span>
                <span className="mt-1 block text-xs text-gray-500">{entry.results_count} résultat{entry.results_count !== 1 ? 's' : ''} · {dateLabel(entry.searched_at)}</span>
              </span>
              <span className="text-xl text-gray-400" aria-hidden="true">›</span>
            </a>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-7 text-center">
          <Search size={28} className="mx-auto text-gray-400" aria-hidden="true" />
          <h2 className="mt-3 font-semibold text-gray-700">Aucune recherche enregistrée</h2>
          <p className="mt-1 text-sm text-gray-500">Vos recherches apparaîtront ici.</p>
          <Link to="/sante/recherche/" className="mt-4 inline-block rounded-lg bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white">Rechercher des soins</Link>
        </div>
      ))}
    </section>
  );
}
