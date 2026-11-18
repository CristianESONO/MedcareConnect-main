import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, FlaskConical, Search } from 'lucide-react';
import { SearchCardMobile } from '../components/search/SearchCardMobile';
import {
  cartApi,
  patientMobileApi,
  searchActes,
  type MobileDemoTicket,
  type SearchResult,
} from '../lib/api';
import { useGeoLocation } from '../hooks/useGeoLocation';

type MobileTab = 'proximite' | 'tarifs' | 'assurances' | 'ticket';

const QUICK_CATEGORIES = [
  { label: 'Urgences', icon: 'ti-emergency-bed', query: 'urgence' },
  { label: 'Consultations', icon: 'ti-stethoscope', query: 'consultation' },
  { label: 'Laboratoires', icon: 'ti-microscope', query: 'laboratoire' },
  { label: 'Pharmacies', icon: 'ti-pill', query: 'pharmacie' },
  { label: 'Imagerie', icon: 'ti-scan', query: 'imagerie' },
];

export function PatientMobilePage() {
  const geo = useGeoLocation();
  const [activeTab, setActiveTab] = useState<MobileTab>('proximite');
  const [query, setQuery] = useState(
    () => new URLSearchParams(window.location.search).get('q') || '',
  );
  const [results, setResults] = useState<SearchResult[]>([]);
  const [ticket, setTicket] = useState<MobileDemoTicket | null>(null);
  const [loadedSearchKey, setLoadedSearchKey] = useState<string | null>(null);
  const [ticketLoading, setTicketLoading] = useState(true);
  const [searchError, setSearchError] = useState<{ key: string; message: string } | null>(null);
  const [cartError, setCartError] = useState('');
  const [ticketError, setTicketError] = useState('');
  const [notice, setNotice] = useState('');
  const [cartBusy, setCartBusy] = useState(false);

  const searchParams = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    if (query.trim()) params.set('q', query.trim());
    else params.delete('q');
    if (geo.lat !== null && geo.lon !== null) {
      params.set('lat', String(geo.lat));
      params.set('lng', String(geo.lon));
      params.set('proximity', '1');
    }
    return params;
  }, [geo.lat, geo.lon, query]);
  const searchKey = searchParams.toString();
  const loading = loadedSearchKey !== searchKey;
  const error = searchError?.key === searchKey ? searchError.message : '';

  useEffect(() => {
    const controller = new AbortController();
    searchActes(new URLSearchParams(searchKey), controller.signal)
      .then((data) => setResults(data.offers))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setSearchError({
            key: searchKey,
            message: reason instanceof Error ? reason.message : 'Impossible de charger les structures.',
          });
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadedSearchKey(searchKey);
      });
    return () => controller.abort();
  }, [searchKey]);

  useEffect(() => {
    const controller = new AbortController();
    patientMobileApi.get(controller.signal)
      .then((data) => setTicket(data.ticket))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setTicketError(reason instanceof Error ? reason.message : 'Impossible de charger le ticket.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setTicketLoading(false);
      });
    return () => controller.abort();
  }, []);

  const visibleResults = useMemo(() => {
    const sorted = [...results];
    if (activeTab === 'tarifs') {
      sorted.sort((left, right) => (left.price_min ?? Number.MAX_VALUE) - (right.price_min ?? Number.MAX_VALUE));
    } else if (activeTab === 'assurances') {
      sorted.sort((left, right) => Number(Boolean(right.insurance_match)) - Number(Boolean(left.insurance_match)));
    } else if (activeTab === 'proximite' && geo.lat !== null) {
      sorted.sort((left, right) => (left.distance_km ?? Number.MAX_VALUE) - (right.distance_km ?? Number.MAX_VALUE));
    }
    return sorted;
  }, [activeTab, geo.lat, results]);

  const addToCart = async (result: SearchResult) => {
    setCartBusy(true);
    setCartError('');
    setNotice('');
    try {
      await cartApi.add(result.id);
      setNotice(`Une prestation de ${result.nom} a été ajoutée au panier.`);
    } catch (reason) {
      setCartError(reason instanceof Error ? reason.message : 'Impossible d’ajouter cette prestation au panier.');
    } finally {
      setCartBusy(false);
    }
  };

  return (
    <div className="sipn-prestations struct-list-m mx-auto min-h-screen w-full max-w-md bg-gray-50 pb-20 dark:bg-gray-900">
      <header className="rounded-b-3xl bg-gradient-to-br from-[#123a63] via-[#123a63] to-[#1a4f87] p-5 text-white shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-xl bg-white/10 font-syne text-base font-bold text-[#4fa3c7]">M</div>
            <span className="font-syne text-base font-extrabold tracking-tight">MedCare Mobile</span>
          </div>
          <button type="button" onClick={geo.request} className="flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-bold transition hover:bg-white/25">
            <i className={`ti ti-location ${geo.loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            {geo.lat !== null ? 'Localisé' : 'Me localiser'}
          </button>
        </div>

        <h1 className="font-syne text-2xl font-black leading-tight text-white">
          {activeTab === 'ticket' ? 'Votre prestation' : 'Trouvez un soin à proximité'}
        </h1>
        <p className="mt-1 text-xs text-white/70">Dakar & Régions · Prix transparents · Tiers-payant</p>

        <div className="no-scrollbar flex gap-2 overflow-x-auto pt-4">
          {QUICK_CATEGORIES.map((category) => (
            <button
              key={category.label}
              type="button"
              onClick={() => {
                setQuery(category.query);
                setActiveTab('proximite');
              }}
              className="flex shrink-0 items-center gap-1.5 rounded-full bg-white/10 px-3.5 py-1.5 text-xs font-bold text-white/85 transition hover:bg-white/20"
            >
              <i className={`ti ${category.icon}`} aria-hidden="true" />
              <span>{category.label}</span>
            </button>
          ))}
        </div>
      </header>
      {geo.error && <p className="mx-4 mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800" role="status">{geo.error}</p>}

      <div className="px-4 pt-4">
        <label className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-gray-500 shadow-sm">
          <Search size={17} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Soin, examen ou structure"
            className="min-w-0 flex-1 border-0 bg-transparent text-sm text-gray-800 outline-none placeholder:text-gray-400"
          />
        </label>
      </div>

      <nav className="px-4 pt-4" aria-label="Trier les structures">
        <div className="grid grid-cols-4 rounded-xl bg-gray-200/70 p-1 text-[10px] font-bold dark:bg-gray-800">
          {([
            ['proximite', 'Proximité'],
            ['tarifs', 'Tarifs'],
            ['assurances', 'Mutuelles'],
            ['ticket', 'Ticket'],
          ] as const).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              aria-pressed={activeTab === tab}
              className={`rounded-lg py-2 transition ${activeTab === tab ? 'bg-white text-[#123a63] shadow-sm dark:bg-gray-700 dark:text-[#4fa3c7]' : 'text-gray-500 dark:text-gray-400'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      <main className="flex flex-col gap-3 p-4">
        {activeTab === 'ticket' ? (
          ticketLoading ? (
            <p className="rounded-xl bg-white p-4 text-sm text-gray-600" role="status">Chargement du ticket…</p>
          ) : ticketError ? (
            <p className="rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{ticketError}</p>
          ) : ticket ? (
            <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
              <header className="bg-gradient-to-br from-[#0a4a72] to-[#054a38] p-4 text-white">
                <p className="text-[10px] font-bold uppercase tracking-widest text-white/70">Ticket partagé</p>
                <h2 className="mt-1 font-syne text-lg font-extrabold">{ticket.title}</h2>
                <p className="mt-2 text-xs text-white/80">{ticket.provider.name}{ticket.provider.city ? ` · ${ticket.provider.city}` : ''}</p>
              </header>
              <div className="space-y-3 p-4">
                {ticket.description && <p className="text-sm leading-5 text-gray-600">{ticket.description}</p>}
                <dl className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-gray-50 p-2"><dt className="text-gray-500">Modalité</dt><dd className="mt-1 font-semibold text-gray-800">{ticket.mode}</dd></div>
                  <div className="rounded-lg bg-gray-50 p-2"><dt className="text-gray-500">Tarif estimatif</dt><dd className="mt-1 font-semibold text-gray-800">{Number(ticket.price).toLocaleString('fr-FR')} FCFA</dd></div>
                  <div className="rounded-lg bg-gray-50 p-2"><dt className="text-gray-500">Zone</dt><dd className="mt-1 font-semibold text-gray-800">{ticket.zone || ticket.provider.quartier || ticket.provider.city}</dd></div>
                  <div className="rounded-lg bg-gray-50 p-2"><dt className="text-gray-500">Disponibilité</dt><dd className="mt-1 font-semibold text-gray-800">{ticket.availability}</dd></div>
                </dl>
                {ticket.act && <p className="text-xs text-gray-500">Acte associé : <span className="font-semibold text-gray-700">{ticket.act}</span></p>}
                <a href={ticket.public_url} className="block rounded-xl bg-[#0a5c8a] px-4 py-3 text-center text-sm font-bold text-white hover:bg-[#084b70]">
                  Ouvrir la fiche et contacter
                </a>
              </div>
            </article>
          ) : (
            <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-6 text-center">
              <CalendarDays size={28} className="mx-auto text-gray-400" aria-hidden="true" />
              <h2 className="mt-3 font-semibold text-gray-800">Aucun ticket actif</h2>
              <p className="mt-1 text-sm text-gray-500">Un ticket partagé par un praticien apparaîtra ici.</p>
            </div>
          )
        ) : (
          <>
            <div className="flex items-center justify-between px-1 text-xs font-bold uppercase tracking-wider text-gray-400">
              <span>{geo.lat !== null ? 'Structures à proximité' : 'Structures disponibles'}</span>
              <span>{visibleResults.length} résultat{visibleResults.length !== 1 ? 's' : ''}</span>
            </div>
            {notice && <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
            {(error || cartError) && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error || cartError}</p>}
            {cartBusy && <p className="text-xs text-gray-500" role="status">Mise à jour du panier…</p>}
            {loading ? (
              <p className="rounded-xl bg-white p-4 text-sm text-gray-600" role="status">Recherche des prestations…</p>
            ) : visibleResults.length ? (
              visibleResults.map((result, index) => (
                <SearchCardMobile
                  key={result.id}
                  result={result}
                  index={index}
                  onSelect={(selected) => {
                    if (selected.profile_url) window.location.assign(selected.profile_url);
                  }}
                  onAddCart={(selected) => { void addToCart(selected); }}
                />
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-6 text-center">
                <FlaskConical size={26} className="mx-auto text-gray-400" aria-hidden="true" />
                <p className="mt-2 text-sm text-gray-600">Aucune structure trouvée pour cette recherche.</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
