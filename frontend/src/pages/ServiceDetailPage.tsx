import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { discoveryApi, type ServiceDetailData } from '../lib/api';

export function ServiceDetailPage() {
  const { slug = '' } = useParams();
  const [data, setData] = useState<ServiceDetailData | null>(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setLoading(true);
    setError('');
    discoveryApi.service(slug, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger ce catalogue.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [slug]);

  const acts = useMemo(() => (data?.acts || []).filter((act) => (
    (!category || act.category === category)
    && (!query || act.name.toLocaleLowerCase('fr').includes(query.toLocaleLowerCase('fr')))
  )), [category, data, query]);

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <p className="mb-4 text-sm"><Link to="/sante/recherche/" className="font-semibold text-[#0a5c8a] hover:underline">← Retour à la recherche</Link></p>
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement du catalogue…</p>}
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {data && (
        <>
          <header className="mb-6 rounded-2xl bg-gradient-to-br from-[#0a4a72] to-[#054a38] p-6 text-white">
            <p className="text-3xl" aria-hidden="true">{data.icon}</p>
            <h1 className="mt-2 font-syne text-2xl font-extrabold sm:text-3xl">{data.name}</h1>
            <p className="mt-2 text-sm text-white/85">Catalogue des actes et établissements proposant ce service.</p>
          </header>
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(260px,1fr)]">
            <section className="rounded-2xl border border-gray-200 bg-white p-4 sm:p-5">
              <div className="grid gap-3 sm:grid-cols-[1fr_220px]">
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher un acte…" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
                <select value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm">
                  <option value="">Toutes catégories</option>
                  {data.categories.map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </div>
              <div className="mt-4 divide-y divide-gray-100">
                {acts.map((act, index) => <div key={`${act.name}-${index}`} className="flex items-center justify-between gap-3 py-3"><span className="text-sm font-medium text-gray-900">{act.name}</span><span className="shrink-0 rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-600">{act.category}</span></div>)}
                {!acts.length && <p className="py-8 text-center text-sm text-gray-500">Aucun acte ne correspond à la recherche.</p>}
              </div>
            </section>
            <aside className="rounded-2xl border border-gray-200 bg-white p-5">
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Établissements</h2>
              <div className="mt-3 space-y-3">
                {data.providers.map((provider) => <Link key={provider.slug} to={provider.profile_url} className="block rounded-xl border border-gray-100 p-3 hover:border-sky-200 hover:bg-sky-50"><p className="text-sm font-semibold text-gray-900">{provider.name}</p><p className="mt-1 text-xs text-gray-500">{provider.city}</p></Link>)}
                {!data.providers.length && <p className="text-sm text-gray-500">Aucun prestataire référencé pour ce service.</p>}
              </div>
              <Link to={`/sante/recherche/?q=${encodeURIComponent(data.name)}`} className="mt-4 inline-flex rounded-lg bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white">Chercher une prestation</Link>
            </aside>
          </div>
        </>
      )}
    </section>
  );
}
