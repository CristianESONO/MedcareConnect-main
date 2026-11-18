import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  bundlePlannerApi,
  type BundleAct,
  type BundleLine,
  type BundlePlan,
  type BundlePlannerData,
} from '../lib/api';

function amount(value: string | number) {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? `${new Intl.NumberFormat('fr-FR').format(Math.round(parsed))} FCFA`
    : 'Tarif indisponible';
}

function alternativeUrl(template: string, acteId: number) {
  return template.replace('__ACTE__', String(acteId));
}

export function BundlePlannerPage() {
  const [data, setData] = useState<BundlePlannerData | null>(null);
  const [selectedActs, setSelectedActs] = useState<BundleAct[]>([]);
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<(BundleAct & { service: string })[]>([]);
  const [plans, setPlans] = useState<BundlePlan[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [alternatives, setAlternatives] = useState<Record<number, BundleLine[]>>({});
  const [selectedOffers, setSelectedOffers] = useState<Record<string, number>>({});
  const [latitude, setLatitude] = useState<number>();
  const [longitude, setLongitude] = useState<number>();
  const [geoMessage, setGeoMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    bundlePlannerApi.initial(controller.signal)
      .then((payload) => {
        setData(payload);
        setSelectedActs(payload.initial_actes);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger le parcours.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!data || query.trim().length < 2) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      bundlePlannerApi.searchActs(data.urls.actes, query.trim(), controller.signal)
        .then((response) => setSuggestions(response.results))
        .catch((reason: unknown) => {
          if (!controller.signal.aborted) {
            setError(reason instanceof Error ? reason.message : 'La recherche d’examens a échoué.');
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearching(false);
        });
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [data, query]);

  const persistSelection = async (acts: BundleAct[]) => {
    if (!data) return;
    try {
      await bundlePlannerApi.saveSelection(data.urls.save, acts.map((act) => act.id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer votre sélection.');
    }
  };

  const updateSelection = (acts: BundleAct[]) => {
    setSelectedActs(acts);
    setPlans([]);
    setWarnings([]);
    void persistSelection(acts);
  };

  const addAct = (act: BundleAct) => {
    if (selectedActs.some((selected) => selected.id === act.id)) return;
    updateSelection([...selectedActs, act]);
    setQuery('');
    setSuggestions([]);
    setError('');
  };

  const applyPreset = (preset: BundlePlannerData['presets'][number]) => {
    const acts = preset.acte_ids.map((id, index) => ({
      id,
      name: preset.acte_labels[index] || `Examen #${id}`,
    }));
    updateSelection(acts);
    setError('');
  };

  const compare = async () => {
    if (!data || selectedActs.length === 0 || comparing) return;
    setComparing(true);
    setError('');
    try {
      const response = await bundlePlannerApi.compare(data.urls.plan, {
        acte_ids: selectedActs.map((act) => act.id),
        save_selection: true,
        ...(latitude !== undefined && longitude !== undefined
          ? { lat: latitude, lng: longitude }
          : {}),
      });
      setPlans(response.plans);
      setWarnings(response.warnings);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de comparer les centres.');
      setPlans([]);
    } finally {
      setComparing(false);
    }
  };

  const loadAlternatives = async (acteId: number) => {
    if (!data || alternatives[acteId]) return;
    try {
      const response = await bundlePlannerApi.alternatives(
        alternativeUrl(data.urls.alternatives, acteId),
        latitude,
        longitude,
      );
      setAlternatives((current) => ({ ...current, [acteId]: response.alternatives }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de charger les autres centres.');
    }
  };

  const planLines = (plan: BundlePlan) => plan.lines.map((line) => {
    const key = `${plan.key}:${line.acte_id}`;
    const options = alternatives[line.acte_id] || [line];
    const selectedId = selectedOffers[key] || line.prestataire_acte_id;
    return options.find((option) => option.prestataire_acte_id === selectedId) || line;
  });

  const planTotals = Object.fromEntries(plans.map((plan) => {
    const lines = planLines(plan);
    return [plan.key, {
      total: lines.reduce((sum, line) => sum + Number(line.price || 0), 0),
      centers: new Set(lines.map((line) => line.organisme_id)).size,
    }];
  }));

  const useLocation = () => {
    if (!navigator.geolocation) {
      setGeoMessage('La géolocalisation n’est pas disponible sur cet appareil.');
      return;
    }
    setGeoMessage('Localisation en cours…');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude);
        setLongitude(position.coords.longitude);
        setGeoMessage('Position enregistrée.');
        setAlternatives({});
      },
      () => setGeoMessage('Impossible d’obtenir votre position.'),
      { enableHighAccuracy: false, timeout: 10000 },
    );
  };

  const addPlanToCart = async (plan: BundlePlan) => {
    if (!data) return;
    const offerIds = planLines(plan).map((line) => line.prestataire_acte_id);
    try {
      const response = await bundlePlannerApi.addToCart(data.urls.add_bundle, offerIds);
      window.location.assign(response.cart_url || '/cart/');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ajouter ce lot au panier.');
    }
  };

  if (loading) {
    return <p className="mx-auto max-w-6xl px-4 py-10 text-sm text-gray-600" role="status">Chargement du parcours…</p>;
  }

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="rounded-2xl bg-gradient-to-br from-sky-700 to-cyan-700 p-6 text-white shadow-lg sm:p-8">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-100">Parcours patient</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold sm:text-3xl">Composer un lot d’examens</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/85">
          Comparez les combinaisons de centres selon le prix, la proximité ou la possibilité de tout réaliser au même endroit.
        </p>
      </header>

      {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}

      {data?.presets.length ? (
        <section className="mt-7">
          <h2 className="font-syne text-lg font-bold text-[#123a63]">Lots prédéfinis</h2>
          <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
            {data.presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset)}
                className="min-w-52 rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm hover:border-sky-300"
              >
                <span className="text-2xl" aria-hidden="true">{preset.icon}</span>
                <span className="mt-2 block text-sm font-bold text-gray-900">{preset.name}</span>
                <span className="mt-1 block text-xs text-gray-500">{preset.teaser || preset.description}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="font-syne text-lg font-bold text-[#123a63]">Vos examens</h2>
        <div className="relative mt-3">
          <label htmlFor="bundle-act-search" className="sr-only">Rechercher un examen</label>
          <input
            id="bundle-act-search"
            type="search"
            autoComplete="off"
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              setQuery(nextQuery);
              if (nextQuery.trim().length < 2) setSuggestions([]);
            }}
            placeholder="Ex. NFS, IRM, échographie, glycémie…"
            className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          />
          {query.trim().length >= 2 && (
            <div className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-gray-200 bg-white py-1 shadow-lg">
              {searching && <p className="px-4 py-3 text-sm text-gray-500">Recherche…</p>}
              {!searching && suggestions.map((act) => (
                <button
                  key={act.id}
                  type="button"
                  onClick={() => addAct(act)}
                  disabled={selectedActs.some((selected) => selected.id === act.id)}
                  className="flex w-full flex-col px-4 py-2 text-left text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  <span className="font-semibold text-gray-900">{act.name}</span>
                  <span className="text-xs text-gray-500">{act.service}</span>
                </button>
              ))}
              {!searching && suggestions.length === 0 && <p className="px-4 py-3 text-sm text-gray-500">Aucun examen trouvé.</p>}
            </div>
          )}
        </div>
        <div className="mt-4 flex min-h-10 flex-wrap gap-2">
          {selectedActs.map((act) => (
            <span key={act.id} className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-900">
              {act.name}
              <button
                type="button"
                aria-label={`Retirer ${act.name}`}
                onClick={() => updateSelection(selectedActs.filter((selected) => selected.id !== act.id))}
                className="text-sky-700 hover:text-red-700"
              >×</button>
            </span>
          ))}
          {selectedActs.length === 0 && <p className="text-sm text-amber-700">Ajoutez au moins un examen pour comparer les centres.</p>}
        </div>
      </section>

      <section className="mt-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="font-syne text-lg font-bold text-[#123a63]">Votre position <span className="text-sm font-normal text-gray-400">(facultatif)</span></h2>
        <p className="mt-1 text-sm text-gray-500">Utilisée pour classer les options par proximité.</p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button type="button" onClick={useLocation} className="rounded-lg bg-sky-700 px-4 py-2 text-sm font-bold text-white hover:bg-sky-800">
            Utiliser ma position
          </button>
          {geoMessage && <span className="text-xs text-gray-500" role="status">{geoMessage}</span>}
        </div>
      </section>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={compare}
          disabled={!selectedActs.length || comparing}
          className="rounded-xl bg-[#123a63] px-6 py-3 text-sm font-bold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
        >
          {comparing ? 'Comparaison en cours…' : 'Comparer les combinaisons'}
        </button>
        <Link to="/sante/recherche/" className="text-sm font-semibold text-sky-800 hover:underline">Retour à la recherche</Link>
      </div>

      {warnings.map((warning) => <p key={warning} className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{warning}</p>)}
      {!comparing && plans.length === 0 && selectedActs.length > 0 && (
        <p className="mt-6 text-sm text-gray-500">Comparez les options pour afficher les centres et leurs tarifs.</p>
      )}
      <div className="mt-6 space-y-5">
        {plans.map((plan) => {
          const currentLines = planLines(plan);
          const totals = planTotals[plan.key] as { total: number; centers: number } | undefined;
          return (
            <article key={plan.key} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-bold text-sky-800">
                    {plan.kind === 'single_center' ? 'Un seul centre' : plan.kind === 'multi_price' ? 'Prix minimum' : plan.kind === 'multi_proximity' ? 'Proximité' : 'Équilibre'}
                  </span>
                  <h2 className="mt-2 font-syne text-lg font-bold text-[#123a63]">{plan.title}</h2>
                  <p className="mt-1 text-sm text-gray-500">{plan.subtitle}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Total estimé</p>
                  <p className="text-xl font-extrabold text-[#123a63]">{amount(totals?.total ?? plan.total_price)}</p>
                  <p className="text-xs text-gray-500">{totals?.centers ?? plan.center_count} centre(s)</p>
                  {plan.avg_distance_km !== null && <p className="text-xs text-gray-400">{plan.avg_distance_km} km en moyenne</p>}
                </div>
              </div>
              {plan.missing_actes.length > 0 && <p className="mt-3 text-xs text-amber-800">Offre manquante pour : {plan.missing_actes.join(', ')}</p>}
              <div className="mt-4 divide-y divide-gray-100">
                {plan.lines.map((line, index) => {
                  const key = `${plan.key}:${line.acte_id}`;
                  const choices = alternatives[line.acte_id] || [line];
                  const selectedId = selectedOffers[key] || line.prestataire_acte_id;
                  return (
                    <div key={`${line.acte_id}-${index}`} className="grid gap-2 py-3 sm:grid-cols-[minmax(120px,1fr)_minmax(240px,2fr)_auto] sm:items-center">
                      <span className="text-sm font-semibold text-gray-800">{line.acte_name}</span>
                      <select
                        aria-label={`Centre pour ${line.acte_name}`}
                        value={selectedId}
                        onFocus={() => { void loadAlternatives(line.acte_id); }}
                        onChange={(event) => setSelectedOffers((current) => ({
                          ...current,
                          [key]: Number(event.target.value),
                        }))}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs"
                      >
                        {choices.map((option) => (
                          <option key={option.prestataire_acte_id} value={option.prestataire_acte_id}>
                            {option.organisme_name} — {amount(option.price)}
                          </option>
                        ))}
                      </select>
                      <Link to={`/sante/${currentLines[index]?.organisme_slug || line.organisme_slug}/`} className="text-xs font-semibold text-sky-800 hover:underline">Voir la fiche</Link>
                    </div>
                  );
                })}
              </div>
              <button
                type="button"
                onClick={() => { void addPlanToCart(plan); }}
                disabled={!data?.is_patient && data?.is_authenticated}
                className="mt-4 rounded-lg bg-cyan-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-cyan-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Ajouter ce lot au panier
              </button>
              {!data?.is_patient && data?.is_authenticated && (
                <p className="mt-2 text-xs text-gray-500">L’ajout au panier est réservé aux comptes patient.</p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
