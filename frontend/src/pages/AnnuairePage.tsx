import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Building2, MapPin, Search, ShieldCheck, Star } from 'lucide-react';
import { FavoriteButton } from '../components/FavoriteButton';
import { discoveryApi, formatApiError, type AnnuairePayload, type AnnuaireResult } from '../lib/api';

function ResultCard({ result }: { result: AnnuaireResult }) {
  const [showAllInsurances, setShowAllInsurances] = useState(false);
  const insuranceNames = result.insurance_names || [];
  const matchedInsurances = result.matched_insurances || [];
  const visibleInsuranceNames = showAllInsurances ? insuranceNames : insuranceNames.slice(0, 3);

  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-sky-200 hover:shadow-md sm:p-5">
      <div className="flex items-start gap-4">
        {result.logo ? (
          <img src={result.logo} alt="" className="size-14 shrink-0 rounded-xl border border-gray-100 object-cover" />
        ) : (
          <span className="flex size-14 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
            <Building2 size={24} aria-hidden="true" />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-bold text-[#123a63]">{result.name}</h2>
            {result.verified && <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800"><ShieldCheck size={12} /> Vérifié</span>}
            {result.pioneer && <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800"><Star size={12} /> Pionnier</span>}
          </div>
          <p className="mt-1 text-xs text-gray-500">{result.type || 'Établissement de santé'}</p>
          <p className="mt-2 flex items-center gap-1 text-xs text-gray-600">
            <MapPin size={13} aria-hidden="true" /> {result.zone_label}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-gray-600">
            <span className="rounded-full bg-gray-100 px-2.5 py-1">{result.acte_count} acte{result.acte_count === 1 ? '' : 's'}</span>
            <span className="rounded-full bg-gray-100 px-2.5 py-1">{result.delay_label}</span>
            <span className="rounded-full bg-gray-100 px-2.5 py-1">{result.hours}</span>
          </div>
          <div className="mt-4 border-t border-gray-100 pt-3">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-gray-700">
              <ShieldCheck size={14} className="text-emerald-700" aria-hidden="true" />
              Assurances acceptées
              <span className="font-normal text-gray-500">({insuranceNames.length})</span>
            </p>
            {insuranceNames.length ? (
              <div className="flex flex-wrap items-center gap-1.5">
                {visibleInsuranceNames.map((name) => {
                  const isMatched = matchedInsurances.includes(name);
                  return (
                    <span
                      key={name}
                      title={name}
                      className={`inline-flex max-w-full items-center rounded-full px-2.5 py-1 text-[11px] leading-4 ring-1 ${
                        isMatched
                          ? 'bg-sky-50 text-sky-900 ring-sky-200'
                          : 'bg-emerald-50 text-emerald-900 ring-emerald-100'
                      }`}
                    >
                      <span className="truncate">{name}</span>
                    </span>
                  );
                })}
                {insuranceNames.length > 3 && (
                  <button
                    type="button"
                    aria-expanded={showAllInsurances}
                    onClick={() => setShowAllInsurances((shown) => !shown)}
                    className="rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-200"
                  >
                    {showAllInsurances ? 'Réduire' : `+${insuranceNames.length - 3} autres`}
                  </button>
                )}
              </div>
            ) : (
              <p className="text-xs text-gray-500">Aucune assurance renseignée</p>
            )}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Link to={result.profile_url} className="rounded-lg bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white hover:bg-[#084b70]">
              Voir la fiche
            </Link>
            <FavoriteButton slug={result.slug} initialFavorite={result.is_favorite} />
          </div>
        </div>
      </div>
    </article>
  );
}

export function AnnuairePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [data, setData] = useState<AnnuairePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [category, setCategory] = useState(searchParams.get('type_cat') || 'all');
  const [zone, setZone] = useState(searchParams.get('zone') || '');
  const [delay, setDelay] = useState(searchParams.get('delai') || '');
  const [sort, setSort] = useState(searchParams.get('sort') || 'alpha');
  const [insurances, setInsurances] = useState(searchParams.getAll('assurance'));
  const [insuranceSearch, setInsuranceSearch] = useState('');
  const [showAllInsuranceFilters, setShowAllInsuranceFilters] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    setQuery(searchParams.get('q') || '');
    setCategory(searchParams.get('type_cat') || 'all');
    setZone(searchParams.get('zone') || '');
    setDelay(searchParams.get('delai') || '');
    setSort(searchParams.get('sort') || 'alpha');
    setInsurances(searchParams.getAll('assurance'));
    const controller = new AbortController();
    setError('');
    setLoading(true);
    discoveryApi.annuaire(new URLSearchParams(searchParams), controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(formatApiError(reason, 'Impossible de charger l’annuaire.'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [searchParams, retryCount]);

  const submitFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams();
    if (query.trim()) params.set('q', query.trim());
    if (category !== 'all') params.set('type_cat', category);
    if (zone) params.set('zone', zone);
    if (delay) params.set('delai', delay);
    if (sort !== 'alpha') params.set('sort', sort);
    insurances.forEach((id) => params.append('assurance', id));
    navigate(`/sante/annuaire/${params.size ? `?${params}` : ''}`);
  };

  const toggleInsurance = (id: string) => {
    setInsurances((current) => current.includes(id)
      ? current.filter((value) => value !== id)
      : [...current, id]);
  };

  const goToPage = (page: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(page));
    navigate(`/sante/annuaire/?${params}`);
  };

  const filteredInsuranceOptions = (data?.insurances || []).filter((insurance) =>
    insurance.name.toLocaleLowerCase('fr').includes(insuranceSearch.trim().toLocaleLowerCase('fr')),
  );
  const visibleInsuranceOptions = showAllInsuranceFilters || insuranceSearch.trim()
    ? filteredInsuranceOptions
    : filteredInsuranceOptions.slice(0, 8);

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Découverte des soins</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Annuaire des établissements</h1>
        <p className="mt-2 text-sm text-gray-600">Recherchez par nom, type, quartier, assurance ou disponibilité.</p>
      </header>

      <form onSubmit={submitFilters} className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <label className="relative block">
          <span className="sr-only">Rechercher un établissement</span>
          <Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" aria-hidden="true" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nom, type, quartier…" className="w-full rounded-xl border border-gray-200 py-2.5 pl-10 pr-3 text-sm focus:border-sky-500 focus:outline-none" />
        </label>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs font-semibold text-gray-600">
            Type
            <select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-normal text-gray-800">
              {(data?.categories || [{ id: 'all', label: 'Tous les types' }]).map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Zone / quartier
            <select value={zone} onChange={(event) => setZone(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-normal text-gray-800">
              <option value="">Toutes les zones</option>
              {(data?.zones || []).map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Disponibilité
            <select value={delay} onChange={(event) => setDelay(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-normal text-gray-800">
              <option value="">Tous les délais</option>
              {(data?.delays || []).map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Trier par
            <select value={sort} onChange={(event) => setSort(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-normal text-gray-800">
              {(data?.sorts || [{ id: 'alpha', label: 'A → Z' }]).map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </label>
        </div>

        {data?.insurances.length ? (
          <fieldset className="mt-4">
            <legend className="text-xs font-semibold text-gray-700">Filtrer par assurance ({data.insurances.length})</legend>
            <label className="mt-2 block max-w-sm">
              <span className="sr-only">Rechercher une assurance</span>
              <input
                type="search"
                value={insuranceSearch}
                onChange={(event) => setInsuranceSearch(event.target.value)}
                placeholder="Rechercher une assurance…"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-xs focus:border-sky-500 focus:outline-none"
              />
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              {visibleInsuranceOptions.map((insurance) => {
                const selected = insurances.includes(String(insurance.id));
                return (
                <label key={insurance.id} className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${selected ? 'border-sky-300 bg-sky-50 text-sky-900 shadow-sm ring-1 ring-sky-100' : 'border-gray-200 bg-white text-gray-600 hover:border-sky-200 hover:bg-sky-50/50'}`}>
                  <input type="checkbox" checked={selected} onChange={() => toggleInsurance(String(insurance.id))} className="sr-only" />
                  {selected && <ShieldCheck size={13} aria-hidden="true" />}
                  <span>{insurance.name}</span>
                </label>
                );
              })}
            </div>
            {!filteredInsuranceOptions.length && (
              <p className="mt-2 text-xs text-gray-500">Aucune assurance ne correspond à cette recherche.</p>
            )}
            {!insuranceSearch.trim() && filteredInsuranceOptions.length > 8 && (
              <button
                type="button"
                aria-expanded={showAllInsuranceFilters}
                onClick={() => setShowAllInsuranceFilters((shown) => !shown)}
                className="mt-2 text-xs font-semibold text-[#0a5c8a] hover:underline"
              >
                {showAllInsuranceFilters ? 'Afficher moins' : `Afficher les ${filteredInsuranceOptions.length - 8} autres assurances`}
              </button>
            )}
          </fieldset>
        ) : null}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="submit" className="rounded-lg bg-[#0a5c8a] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#084b70]">Appliquer les filtres</button>
          <Link to="/sante/annuaire/" className="text-sm font-semibold text-gray-500 hover:text-gray-800">Réinitialiser</Link>
          <Link to="/sante/favoris/" className="ml-auto text-sm font-semibold text-[#0a5c8a] hover:underline">Mes favoris</Link>
        </div>
      </form>

      {error && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setRetryCount((count) => count + 1)}
            className="rounded-lg bg-red-700 px-3 py-2 font-semibold text-white hover:bg-red-800"
          >
            Réessayer
          </button>
        </div>
      )}
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Recherche des établissements…</p>}
      {!loading && data && (
        <>
          <p className="mb-3 text-sm text-gray-600">{data.results_count} établissement{data.results_count === 1 ? '' : 's'} trouvé{data.results_count === 1 ? '' : 's'}</p>
          {data.geo_required && <p className="mb-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-900">Autorisez la localisation ou choisissez une zone pour trier par proximité.</p>}
          {data.results.length ? (
            <div className="space-y-3">{data.results.map((result) => <ResultCard key={result.id} result={result} />)}</div>
          ) : (
            <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-600">Aucun établissement ne correspond à ces filtres.</div>
          )}
          {data.pagination.pages > 1 && (
            <nav className="mt-6 flex items-center justify-center gap-3" aria-label="Pagination">
              <button type="button" disabled={!data.pagination.has_previous} onClick={() => goToPage(data.pagination.number - 1)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40">Précédent</button>
              <span className="text-sm text-gray-600">Page {data.pagination.number} / {data.pagination.pages}</span>
              <button type="button" disabled={!data.pagination.has_next} onClick={() => goToPage(data.pagination.number + 1)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40">Suivant</button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
