import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { SearchCart } from '../components/search/SearchCart';
import { SearchCard } from '../components/search/SearchCard';
import { SearchStructureCard } from '../components/search/SearchStructureCard';
import { type CartItem, type SearchPayload, type SearchResult, type SearchSuggestion, searchActes, searchAutocomplete } from '../lib/api';
import { useGeoLocation } from '../hooks/useGeoLocation';
import { useAppStore } from '../store/appStore';

interface SearchPageProps {
  cartItems: CartItem[];
  onAddToCart: (result: SearchResult) => void | Promise<void>;
  onRemoveFromCart: (id: number) => void | Promise<void>;
  onClearCart: () => void | Promise<void>;
  onRequestDevis: () => void;
}

const SEARCH_STYLES = [
  '/static/healthcare/css/sipn_patient.css?v=44',
  '/static/healthcare/css/sipn_cards.css?v=1',
  '/static/healthcare/css/sipn_structure_results.css?v=2',
  '/static/healthcare/css/sipn_mobile_pilier.css?v=46',
  '/static/healthcare/css/demo_patient_search.css?v=20261117',
];

const SORT_OPTIONS = [
  ['price_asc', 'Prix croissant'],
  ['price_desc', 'Prix décroissant'],
  ['price_ipm_asc', 'Prix IPM croissant'],
  ['price_ipm_desc', 'Prix IPM décroissant'],
  ['price_assurance_asc', 'Prix Assurance croissant'],
  ['price_assurance_desc', 'Prix Assurance décroissant'],
  ['delai_rdv_asc', 'RDV disponible le plus vite'],
  ['delai_asc', 'Délai de réponse le plus court'],
  ['name_org', 'Par zone / quartier'],
  ['distance', 'Proximité'],
];

const MOBILE_SORT_OPTIONS = [
  ['price_asc', 'Prix croissant'],
  ['price_desc', 'Prix décroissant'],
  ['popular', 'Couverture assurance'],
  ['delai_asc', 'Délai le plus court'],
  ['name_org', 'Zone / Quartier'],
];

const SEARCH_RETURN_STORAGE_KEY = 'mc_patient_search_return';
type FilterPanel = 'sort' | 'assurance' | 'zone' | 'budget' | 'delai';

function normalizeSearchText(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
}

function highlightSuggestion(label: string, query: string) {
  const index = normalizeSearchText(label).indexOf(normalizeSearchText(query));
  if (index < 0 || !query) return label;
  return (
    <>
      {label.slice(0, index)}
      <span className="ac-highlight">{label.slice(index, index + query.length)}</span>
      {label.slice(index + query.length)}
    </>
  );
}

function updateMultiValue(params: URLSearchParams, key: string, value: string) {
  const values = params.getAll(key);
  params.delete(key);
  for (const current of values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value]) {
    params.append(key, current);
  }
}

export function SearchPage({
  cartItems,
  onAddToCart,
  onRemoveFromCart,
  onClearCart,
  onRequestDevis,
}: SearchPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { cartOpen, toggleCart } = useAppStore();
  const geo = useGeoLocation();
  const proximityRequestedRef = useRef(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const suppressedSuggestionQueryRef = useRef('');
  const searchKey = searchParams.toString();
  const [data, setData] = useState<SearchPayload | null>(null);
  const [loadedSearchKey, setLoadedSearchKey] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<{ key: string; message: string } | null>(null);
  const [query, setQuery] = useState(() => {
    const activeQuery = searchParams.get('q');
    if (activeQuery) return activeQuery;
    if (searchParams.has('acte') || searchParams.has('lot') || searchParams.has('service')) return '';
    const savedSearch = new URLSearchParams(sessionStorage.getItem(SEARCH_RETURN_STORAGE_KEY) || '');
    return savedSearch.get('q') || '';
  });
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);
  const [pendingSuggestion, setPendingSuggestion] = useState<SearchSuggestion | null>(null);
  const [autocompleteError, setAutocompleteError] = useState('');
  const [searchSubmitting, setSearchSubmitting] = useState(false);
  const [actSearch, setActSearch] = useState('');
  const [actesOpen, setActesOpen] = useState(false);
  const [openFilterPanel, setOpenFilterPanel] = useState<FilterPanel | null>(null);
  const [filterPanelLeft, setFilterPanelLeft] = useState(0);
  const [pendingAssurances, setPendingAssurances] = useState<string[]>(searchParams.getAll('assurance'));
  const [pendingCity, setPendingCity] = useState(searchParams.get('city') || '');
  const [pendingDelai, setPendingDelai] = useState(searchParams.get('delai') || '');
  const [budgetDraft, setBudgetDraft] = useState(searchParams.get('price_max') || '');
  const [isMobileViewport, setIsMobileViewport] = useState(false);

  useEffect(() => {
    const returnParams = new URLSearchParams(searchKey);
    const draftQuery = query.trim();
    if (
      draftQuery
      && !returnParams.has('q')
      && !returnParams.has('acte')
      && !returnParams.has('lot')
      && !returnParams.has('service')
    ) {
      returnParams.set('q', draftQuery);
    }
    sessionStorage.setItem(SEARCH_RETURN_STORAGE_KEY, returnParams.toString());
  }, [query, searchKey]);

  useEffect(() => {
    const body = document.body;
    const hadPrestations = body.classList.contains('sipn-prestations');
    body.classList.add('sipn-prestations');
    const links = SEARCH_STYLES.map((href) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.dataset.reactSearchStyle = 'true';
      document.head.appendChild(link);
      return link;
    });

    return () => {
      for (const link of links) link.remove();
      if (!hadPrestations) body.classList.remove('sipn-prestations');
    };
  }, []);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1023px)');
    const updateViewport = () => setIsMobileViewport(media.matches);
    updateViewport();
    media.addEventListener('change', updateViewport);
    return () => media.removeEventListener('change', updateViewport);
  }, []);

  useEffect(() => {
    const body = document.body;
    const params = new URLSearchParams(searchKey);
    const hasActs = params.has('acte') || params.has('lot') || params.has('q');
    body.classList.toggle('sipn-has-actes', hasActs);
    body.classList.toggle('sipn-mobile-view-results', isMobileViewport && hasActs);
    body.classList.toggle('sipn-mobile-view-prestations', isMobileViewport && !hasActs);
    return () => {
      body.classList.remove(
        'sipn-has-actes',
        'sipn-mobile-view-results',
        'sipn-mobile-view-prestations',
      );
    };
  }, [isMobileViewport, searchKey]);

  useEffect(() => {
    const controller = new AbortController();
    searchActes(new URLSearchParams(searchKey), controller.signal)
      .then((response) => {
        if (response.redirect_url) {
          navigate(response.redirect_url, { replace: true });
          return;
        }
        setSearchError(null);
        setData(response);
        setQuery(response.query);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setSearchError({
          key: searchKey,
          message: reason instanceof Error ? reason.message : 'La recherche est momentanément indisponible.',
        });
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadedSearchKey(searchKey);
      });
    return () => controller.abort();
  }, [searchKey, navigate]);

  useEffect(() => {
    const term = query.trim();
    if (term && term === suppressedSuggestionQueryRef.current) {
      suppressedSuggestionQueryRef.current = '';
      setSuggestions([]);
      setSuggestionsOpen(false);
      return;
    }
    if (term.length < 2) {
      setSuggestions([]);
      setSuggestionsOpen(false);
      setActiveSuggestionIndex(-1);
      setAutocompleteError('');
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      searchAutocomplete(term, controller.signal)
        .then((response) => {
          setSuggestions(response.suggestions);
          setSuggestionsOpen(response.suggestions.length > 0);
          setActiveSuggestionIndex(-1);
          setAutocompleteError('');
        })
        .catch((reason: unknown) => {
          if (controller.signal.aborted) return;
          setSuggestions([]);
          setSuggestionsOpen(false);
          setAutocompleteError(
            reason instanceof Error ? reason.message : 'Les suggestions sont momentanément indisponibles.',
          );
        });
    }, 220);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query]);

  const changeParams = (
    change: (params: URLSearchParams) => void,
    replace = true,
  ) => {
    const params = new URLSearchParams(searchParams);
    change(params);
    params.delete('page');
    setSearchError(null);
    setSearchParams(params, { replace });
  };

  const selectAct = (id: number) => {
    setQuery('');
    setPendingSuggestion(null);
    setSuggestionsOpen(false);
    changeParams((params) => {
      params.delete('q');
      params.delete('service');
      params.delete('lot');
      const selected = params.getAll('acte');
      if (!selected.includes(String(id))) params.append('acte', String(id));
    }, false);
  };

  const selectSuggestion = (suggestion: SearchSuggestion) => {
    setSuggestionsOpen(false);
    setActiveSuggestionIndex(-1);
    setPendingSuggestion(suggestion);
    setQuery(suggestion.label);
    suppressedSuggestionQueryRef.current = suggestion.label;
    searchInputRef.current?.focus();
  };

  const submitSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const term = query.trim();
    if (!term) return;

    setSearchSubmitting(true);
    setAutocompleteError('');
    setSuggestionsOpen(false);
    try {
      if (pendingSuggestion?.label === term) {
        if (pendingSuggestion.type === 'acte' && pendingSuggestion.id) {
          selectAct(pendingSuggestion.id);
          return;
        }
        if (pendingSuggestion.type === 'famille' && pendingSuggestion.url) {
          const serviceId = new URLSearchParams(pendingSuggestion.url.split('?')[1] || '').get('service');
          if (serviceId) {
            setQuery('');
            setPendingSuggestion(null);
            selectService(serviceId);
            return;
          }
        }
      }

      const response = await searchAutocomplete(term);
      const acts = response.suggestions.filter((suggestion) => suggestion.type === 'acte' && suggestion.id);
      const normalizedTerm = normalizeSearchText(term);
      const match = acts.find((suggestion) => normalizeSearchText(suggestion.label) === normalizedTerm) || acts[0];
      if (match?.id) {
        selectAct(match.id);
        return;
      }
    } catch (reason) {
      setAutocompleteError(
        reason instanceof Error ? reason.message : 'Les suggestions sont momentanément indisponibles.',
      );
    } finally {
      setSearchSubmitting(false);
    }

    changeParams((params) => {
      params.delete('q');
      if (!params.getAll('acte').length) params.set('q', term);
      if (geo.lat !== null && geo.lon !== null) {
        params.set('lat', String(geo.lat));
        params.set('lng', String(geo.lon));
        params.set('proximity', '1');
      }
    }, false);
  };

  const loading = loadedSearchKey !== searchKey;
  const currentData = loading ? null : data;
  const error = searchError?.key === searchKey ? searchError.message : '';
  const filters = currentData?.filters;
  const options = currentData?.filter_options;
  const activeActs = filters?.actes || [];
  const knownActeNames = new Map<string, string>();
  for (const family of data?.families || []) {
    for (const subgroup of family.subgroups) {
      for (const act of subgroup.acts) {
        if (act.id !== null) knownActeNames.set(String(act.id), act.name);
      }
    }
  }
  for (const offer of data?.offers || []) {
    if (offer.acte_id && offer.acte) knownActeNames.set(String(offer.acte_id), offer.acte);
  }
  const selectedActTokens = searchParams.getAll('acte').map((id) => ({
    id,
    name: knownActeNames.get(id) || `Acte #${id}`,
  }));
  const cartOfferIds = new Set(cartItems.map((item) => item.id));
  const cartActeIds = new Set(cartItems.map((item) => item.acte_id));
  const structureOffers = (() => {
    const groups = new Map<string, SearchResult[]>();
    for (const offer of currentData?.offers || []) {
      const key = offer.slug || `${offer.nom}-${offer.ville || ''}`;
      const group = groups.get(key) || [];
      group.push(offer);
      groups.set(key, group);
    }
    return Array.from(groups.values());
  })();
  const filteredFamilies = (currentData?.families || []).map((family) => ({
    ...family,
    subgroups: family.subgroups.map((subgroup) => ({
      ...subgroup,
      acts: subgroup.acts.filter((act) =>
        act.name.toLocaleLowerCase().includes(actSearch.toLocaleLowerCase())
      ),
    })).filter((subgroup) => subgroup.acts.length > 0),
  })).filter((family) => family.subgroups.length > 0);

  const setSingle = (key: string, value: string) => {
    changeParams((params) => {
      params.delete(key);
      if (value) params.set(key, value);
    });
  };

  const activateProximity = () => {
    if (filters?.proximity) {
      setSingle('proximity', '');
    } else if (filters?.lat && filters.lng) {
      setSingle('proximity', '1');
    } else {
      proximityRequestedRef.current = true;
      geo.request();
    }
  };

  useEffect(() => {
    if (!proximityRequestedRef.current || geo.lat === null || geo.lon === null) return;
    proximityRequestedRef.current = false;
    const params = new URLSearchParams(searchParams);
    params.set('lat', String(geo.lat));
    params.set('lng', String(geo.lon));
    params.set('proximity', '1');
    setSearchParams(params, { replace: true });
  }, [geo.lat, geo.lon, searchParams, setSearchParams]);

  const setMultiple = (key: string, values: string[]) => {
    changeParams((params) => {
      params.delete(key);
      values.forEach((value) => params.append(key, value));
    });
  };

  const selectService = (serviceId: string) => {
    setPendingSuggestion(null);
    changeParams((params) => {
      params.delete('service');
      params.delete('acte');
      params.delete('lot');
      params.delete('q');
      if (serviceId) params.set('service', serviceId);
    });
  };

  const returnToSearch = () => {
    setQuery('');
    changeParams((params) => {
      params.delete('acte');
      params.delete('lot');
      params.delete('q');
      params.delete('service');
    }, false);
  };

  const toggleAct = (id: number) => {
    changeParams((params) => {
      updateMultiValue(params, 'acte', String(id));
      params.delete('lot');
    });
  };

  const clearFilters = () => {
    const filterKeys = [
      'service', 'acte', 'lot', 'level', 'assurance', 'city', 'type', 'region',
      'price_min', 'price_max', 'delai', 'domicile', 'lat', 'lng', 'proximity',
      'radius_km', 'regime', 'sort',
    ];
    changeParams((params) => filterKeys.forEach((key) => params.delete(key)));
  };

  const goToPage = (page: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(page));
    setSearchParams(params);
  };

  const handleSearchKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      if (suggestionsOpen && activeSuggestionIndex >= 0) {
        selectSuggestion(suggestions[activeSuggestionIndex]);
      }
      return;
    }
    if (!suggestionsOpen || !suggestions.length) {
      if (event.key === 'Escape') setSuggestionsOpen(false);
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveSuggestionIndex((index) => (index + 1) % suggestions.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSuggestionIndex((index) => (index <= 0 ? suggestions.length - 1 : index - 1));
    } else if (event.key === 'Escape') {
      setSuggestionsOpen(false);
    }
  };

  const selectedAssurances = filters?.assurances || [];
  const assuranceGroups = (options?.assurances || []).reduce<
    Record<string, SearchPayload['filter_options']['assurances']>
  >((groups, assurance) => {
    if (!groups[assurance.group]) groups[assurance.group] = [];
    groups[assurance.group].push(assurance);
    return groups;
  }, {});
  const parsePriceBound = (value: string | undefined, fallback: number) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  };
  const globalPriceMin = parsePriceBound(filters?.min_price, 2000);
  const globalPriceMax = Math.max(globalPriceMin + 1000, parsePriceBound(filters?.max_price, 500000));
  const mobileSortLabel = MOBILE_SORT_OPTIONS.find(([value]) => value === filters?.sort)?.[1] || 'Prix croissant';

  useEffect(() => {
    setPendingAssurances(filters?.assurances || []);
    setPendingCity(filters?.city || '');
    setPendingDelai(filters?.delai || '');
    setBudgetDraft(filters?.price_max || '');
  }, [filters?.assurances, filters?.city, filters?.delai, filters?.price_max]);

  useEffect(() => {
    if (!openFilterPanel) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpenFilterPanel(null);
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [openFilterPanel]);

  const toggleFilterPanel = (panel: FilterPanel, trigger?: HTMLButtonElement) => {
    if (openFilterPanel === panel) {
      setOpenFilterPanel(null);
      return;
    }
    if (!isMobileViewport && trigger) {
      const row = trigger.closest<HTMLElement>('.dem-filter-row');
      if (row) {
        const rowBounds = row.getBoundingClientRect();
        const triggerBounds = trigger.getBoundingClientRect();
        const panelWidth = Math.min(380, rowBounds.width);
        const requestedLeft = triggerBounds.left - rowBounds.left;
        setFilterPanelLeft(Math.min(Math.max(0, requestedLeft), rowBounds.width - panelWidth));
      }
    }
    if (cartOpen) toggleCart();
    setPendingAssurances(selectedAssurances);
    setPendingCity(filters?.city || '');
    setPendingDelai(filters?.delai || '');
    setBudgetDraft(filters?.price_max || '');
    setOpenFilterPanel(panel);
  };

  const applyFilterPanel = () => {
    if (openFilterPanel === 'assurance') setMultiple('assurance', pendingAssurances);
    if (openFilterPanel === 'zone') setSingle('city', pendingCity);
    if (openFilterPanel === 'delai') setSingle('delai', pendingDelai);
    if (openFilterPanel === 'budget') {
      changeParams((params) => {
        params.delete('price_min');
        params.delete('price_max');
        if (budgetDraft && Number(budgetDraft) < globalPriceMax) params.set('price_max', budgetDraft);
      });
    }
    setOpenFilterPanel(null);
  };

  const clearFilterPanel = (panel: FilterPanel) => {
    if (panel === 'assurance') {
      setPendingAssurances([]);
      setMultiple('assurance', []);
    } else if (panel === 'zone') {
      setPendingCity('');
      setSingle('city', '');
    } else if (panel === 'delai') {
      setPendingDelai('');
      setSingle('delai', '');
    } else if (panel === 'budget') {
      setBudgetDraft('');
      changeParams((params) => {
        params.delete('price_min');
        params.delete('price_max');
      });
    }
    setOpenFilterPanel(null);
  };

  const applyBudgetRange = (value: string) => {
    const amount = Number(value);
    const nextBudget = Number.isFinite(amount) && amount < globalPriceMax
      ? String(Math.round(amount))
      : '';
    setBudgetDraft(nextBudget);
    changeParams((params) => {
      params.delete('price_min');
      params.delete('price_max');
      if (nextBudget) params.set('price_max', nextBudget);
    });
    setOpenFilterPanel(null);
  };

  const filterPanelTitle = (panel: FilterPanel) => ({
    sort: 'Trier les résultats',
    assurance: 'Filtrer par assurance',
    zone: 'Filtrer par zone / quartier',
    budget: 'Budget maximum',
    delai: 'Délai souhaité',
  })[panel];

  const renderFilterPanel = (panel: FilterPanel, mobile: boolean) => {
    if (panel === 'sort') {
      return (
        <div>
          {(mobile ? MOBILE_SORT_OPTIONS : SORT_OPTIONS).map(([value, label]) => (
            <button
              type="button"
              key={value}
              className={mobile ? 'sipn-m-sheet-opt' : 'sipn-filter-sort-option'}
              aria-pressed={filters?.sort === value}
              onClick={() => {
                setSingle('sort', value);
                setOpenFilterPanel(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      );
    }

    if (panel === 'assurance') {
      return (
        <div>
          {!mobile && <p className="sipn-filter-panel-title">Filtrer par assurance</p>}
          <div className="sipn-filter-panel-scroll">
            {Object.entries(assuranceGroups).length ? Object.entries(assuranceGroups).map(([group, assurances]) => (
              <div key={group}>
                <p className={mobile ? 'sipn-m-ins-grp' : 'sipn-filter-panel-group'}>{group}</p>
                {mobile ? assurances.map((assurance) => (
                  <label className="sipn-m-ins-opt" key={assurance.id}>
                    <input
                      type="checkbox"
                      value={assurance.id}
                      checked={pendingAssurances.includes(String(assurance.id))}
                      onChange={() => setPendingAssurances((current) =>
                        current.includes(String(assurance.id))
                          ? current.filter((value) => value !== String(assurance.id))
                          : [...current, String(assurance.id)]
                      )}
                    />
                    <span>{assurance.name}</span>
                  </label>
                )) : (
                  <div className="dem-filter-pills">
                    {assurances.map((assurance) => {
                      const checked = pendingAssurances.includes(String(assurance.id));
                      return (
                        <label className={`dem-filter-pill${checked ? ' on' : ''}`} key={assurance.id}>
                          <input
                            type="checkbox"
                            className="sr-only"
                            value={assurance.id}
                            checked={checked}
                            onChange={() => setPendingAssurances((current) =>
                              checked
                                ? current.filter((value) => value !== String(assurance.id))
                                : [...current, String(assurance.id)]
                            )}
                          />
                          <span>{assurance.name}</span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            )) : <p className="sipn-filter-panel-empty">Aucune assurance disponible.</p>}
          </div>
          {!mobile && (
            <div className="sipn-filter-panel-actions">
              <button type="button" className="sipn-filter-panel-clear" onClick={() => clearFilterPanel('assurance')}>Effacer</button>
              <button type="button" className="sipn-filter-panel-apply" onClick={applyFilterPanel}>Appliquer</button>
            </div>
          )}
        </div>
      );
    }

    if (panel === 'zone') {
      return (
        <div>
          {!mobile && <p className="sipn-filter-panel-title">Filtrer par zone / quartier</p>}
          {mobile ? (
            <div className="sipn-m-sheet-radios">
              {['', ...(options?.cities || [])].map((zone) => (
                <label className="sipn-m-ins-opt" key={zone || 'all-zones'}>
                  <input
                    type="radio"
                    name="sipn-m-zone"
                    value={zone}
                    checked={pendingCity === zone}
                    onChange={() => setPendingCity(zone)}
                  />
                  <span>{zone || 'Toutes les zones'}</span>
                </label>
              ))}
            </div>
          ) : (
            <>
              <div className="dem-filter-pills">
                {(options?.cities || []).map((zone) => (
                  <button
                    type="button"
                    key={zone}
                    className={`dem-filter-pill${pendingCity === zone ? ' on' : ''}`}
                    onClick={() => {
                      setSingle('city', zone === filters?.city ? '' : zone);
                      setOpenFilterPanel(null);
                    }}
                  >
                    {zone}
                  </button>
                ))}
              </div>
              <button type="button" className="dem-filter-clear-link" onClick={() => clearFilterPanel('zone')}>Effacer</button>
            </>
          )}
        </div>
      );
    }

    if (panel === 'budget') {
      const displayedBudget = budgetDraft
        ? `${Number(budgetDraft).toLocaleString('fr-FR')} FCFA`
        : 'Illimité';
      return (
        <div className={mobile ? 'sipn-m-budget-wrap' : ''}>
          {!mobile && <p className="sipn-filter-panel-title">Budget maximum</p>}
          <p className={mobile ? 'sipn-m-budget-display' : 'dem-budget-dd-lbl'}>{displayedBudget}</p>
          <input
            type="range"
            className={mobile ? 'sipn-m-budget-range' : 'dem-dd-budget-range'}
            min={globalPriceMin}
            max={globalPriceMax}
            step="1000"
            value={budgetDraft || globalPriceMax}
            aria-label="Budget maximum"
            onChange={(event) => setBudgetDraft(
              Number(event.target.value) >= globalPriceMax ? '' : event.target.value
            )}
            onPointerUp={(event) => {
              if (!mobile) applyBudgetRange(event.currentTarget.value);
            }}
            onKeyUp={(event) => {
              if (!mobile && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
                applyBudgetRange(event.currentTarget.value);
              }
            }}
          />
          <div className={mobile ? 'sipn-m-budget-hints' : 'dem-dd-budget-hints'}>
            <span>{globalPriceMin.toLocaleString('fr-FR')} F</span>
            <span>{globalPriceMax.toLocaleString('fr-FR')} F</span>
          </div>
          <button
            type="button"
            className="dem-filter-clear-link"
            onClick={() => {
              if (mobile) setBudgetDraft('');
              else clearFilterPanel('budget');
            }}
          >
            Effacer
          </button>
        </div>
      );
    }

    return (
      <div>
        {!mobile && <p className="sipn-filter-panel-title">Délai souhaité</p>}
        {mobile ? (
          <div className="sipn-m-sheet-radios">
            {[{ id: '', name: 'Tous les délais' }, ...(options?.delais || [])].map((delay) => (
              <label className="sipn-m-ins-opt" key={delay.id || 'all-delays'}>
                <input
                  type="radio"
                  name="sipn-m-delai"
                  value={delay.id}
                  checked={pendingDelai === delay.id}
                  onChange={() => setPendingDelai(delay.id)}
                />
                <span>{delay.name}</span>
              </label>
            ))}
          </div>
        ) : (
          <>
            <div className="dem-filter-pills">
              {(options?.delais || []).map((delay) => (
                <button
                  type="button"
                  key={delay.id}
                  className={`dem-filter-pill${pendingDelai === delay.id ? ' on' : ''}`}
                  onClick={() => {
                    setSingle('delai', delay.id === filters?.delai ? '' : delay.id);
                    setOpenFilterPanel(null);
                  }}
                >
                  {delay.name}
                </button>
              ))}
            </div>
            <button type="button" className="dem-filter-clear-link" onClick={() => clearFilterPanel('delai')}>Effacer</button>
          </>
        )}
      </div>
    );
  };

  return (
    <div id="search-form" className="search-page--dem min-h-screen bg-[#eef3f7]">
      <div className="dem-page-fill">
        <section className="sipn-hero" aria-label="Introduction">
          <div className="sipn-hero-inner">
            <div>
              <div className="sipn-hero-lbl">Plateforme paraclinique numérique · Sénégal</div>
              <h1 className="sipn-hero-title">
                Choisissez vos actes.<br />
                <em>Trouvez où les faire. Devis en 1 clic.</em>
              </h1>
              <p className="sipn-hero-sub">
                Sélectionnez un acte — les structures et tarifs s’affichent. Ajoutez au panier, obtenez votre devis. Zéro commission sur les actes.
              </p>
            </div>
            <div className="sipn-hero-stats" aria-label="Chiffres clés">
              {[
                ['Structures', currentData?.stats.structures ?? '—'],
                ['Piliers', currentData?.stats.piliers ?? '—'],
                ['Actes', currentData ? `${currentData.stats.actes}+` : '—'],
                ['Assurances', currentData?.stats.assurances ?? '—'],
                ['Commission', '0%'],
              ].map(([label, value]) => (
                <div className="sipn-hs" key={label}>
                  <div className={`sipn-hs-n${label === 'Commission' ? ' sipn-hs-n--green' : ''}`}>{value}</div>
                  <div className="sipn-hs-l">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>

      <section className="sipn-search-section search-section" aria-label="Recherche et filtres">
        <div className="sipn-search-inner search-inner">
          {!!currentData?.services.length && (
            <div className="sipn-piliers-block sipn-piliers-block--desktop">
              <p className="sipn-piliers-lbl">Recherchez un acte médical</p>
              <nav className="sipn-piliers-in-search piliers dem-piliers" aria-label="Familles de soins">
                {currentData.services.map((service) => (
                  <button
                    type="button"
                    key={`${service.id}-${service.label}`}
                    onClick={() => selectService(service.id)}
                    aria-pressed={service.active}
                    className={`pbtn dem-pbtn${service.active ? ' active' : ''}`}
                  >
                    <i className={`dem-pbtn-ic ti ${service.ambulance ? 'ti-ambulance' : 'ti-category'}`} />
                    <span className="min-w-0 truncate">{service.label}</span>
                    <span className="dem-pbtn-count">{service.count}</span>
                  </button>
                ))}
              </nav>
            </div>
          )}

          <p className="sipn-piliers-lbl sipn-piliers-lbl--mobile">Recherchez un acte médical</p>

          <form onSubmit={submitSearch} className="sipn-main-search">
            <div className="search-input-zone sipn-search-input-zone" id="search-input-zone" data-dem-mode="acte">
              <div id="search-input-inner" className="sipn-search-input-wrap" data-dem-slot="acte">
                <div id="ac-box" className="sipn-ac-box">
                  <span className="sipn-search-emoji" aria-hidden="true"><i className="ti ti-flask" /></span>
                  {selectedActTokens.length > 0 && (
                    <div id="search-tags-list" className="search-selected-actes" aria-label="Actes sélectionnés">
                      {selectedActTokens.map((act) => (
                        <span className="token-tag" key={act.id}>
                          <span>{act.name}</span>
                          <button
                            type="button"
                            className="token-remove"
                            aria-label={`Retirer ${act.name}`}
                            onClick={() => changeParams((params) => {
                              const remaining = params.getAll('acte').filter((id) => id !== act.id);
                              params.delete('acte');
                              remaining.forEach((id) => params.append('acte', id));
                              if (!remaining.length) params.delete('lot');
                            })}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  <input
                    ref={searchInputRef}
                    type="text"
                    name="q"
                    id="search-q"
                    value={query}
                    onChange={(event) => {
                      setActiveSuggestionIndex(-1);
                      setPendingSuggestion(null);
                      setQuery(event.target.value);
                    }}
                    onKeyDown={handleSearchKeyDown}
                    autoComplete="off"
                    inputMode="search"
                    placeholder={selectedActTokens.length ? '' : 'NFS, Glycémie, IRM, Scanner…'}
                    className="sipn-search-input"
                    aria-label="Rechercher un acte médical"
                    aria-expanded={suggestionsOpen}
                    aria-controls="ac-list"
                    aria-activedescendant={activeSuggestionIndex >= 0 ? `ac-suggestion-${activeSuggestionIndex}` : undefined}
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => {
                        setQuery('');
                        setPendingSuggestion(null);
                        changeParams((params) => params.delete('q'));
                      }}
                      className="sipn-search-clear"
                      title="Effacer"
                      aria-label="Effacer la recherche"
                    >
                      <i className="ti ti-x" />
                    </button>
                  )}
                  <div
                    id="ac-list"
                    role="listbox"
                    style={{ display: suggestionsOpen && suggestions.length ? 'block' : 'none' }}
                  >
                    {(['famille', 'acte', 'centre'] as const).map((type) => {
                      const group = suggestions
                        .map((suggestion, index) => ({ suggestion, index }))
                        .filter(({ suggestion }) => suggestion.type === type);
                      if (!group.length) return null;
                      const title = type === 'famille'
                        ? 'Familles de soins'
                        : type === 'acte'
                          ? 'Examens & actes'
                          : 'Centres de santé';
                      const icon = type === 'famille'
                        ? 'ti-building-hospital'
                        : type === 'acte'
                          ? 'ti-flask'
                          : 'ti-map-pin';
                      return (
                        <div key={type}>
                          <div className="ac-group">{title}</div>
                          {group.map(({ suggestion, index }) => (
                            <button
                              type="button"
                              role="option"
                              aria-selected={activeSuggestionIndex === index}
                              id={`ac-suggestion-${index}`}
                              className={`ac-item${activeSuggestionIndex === index ? ' ac-active' : ''}`}
                              key={`${suggestion.type}-${suggestion.id || suggestion.label}`}
                              onMouseDown={(event) => event.preventDefault()}
                              onClick={() => selectSuggestion(suggestion)}
                            >
                              <span className={`ac-icon t-${type}`} aria-hidden="true">
                                <i className={`ti ${icon}`} />
                              </span>
                              <span className="min-w-0 flex-1 truncate">
                                {highlightSuggestion(suggestion.label, query)}
                              </span>
                              {suggestion.detail && <span className="ac-detail">{suggestion.detail}</span>}
                            </button>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
            <button type="submit" className="sipn-search-go" aria-label="Rechercher" disabled={searchSubmitting}>
              <span className="sipn-search-go-label">{searchSubmitting ? 'Recherche…' : 'Rechercher'}</span>
              <svg className="sipn-search-go-ic sm:hidden" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
            </button>
          </form>
          {autocompleteError && <p className="mt-2 text-xs text-amber-700" role="status">{autocompleteError}</p>}

          {!!currentData?.services.length && (
            <div className="sipn-mobile-pilier-zone sipn-pilier-mobile-ui" aria-label="Familles de soins">
              <div className="sipn-pgrid" role="group" aria-label="Choisir une famille de soins">
                {currentData.services.map((service) => (
                  <button
                    type="button"
                    key={`mobile-${service.id}-${service.label}`}
                    onClick={() => selectService(service.id)}
                    aria-pressed={service.active}
                    className={`pgrid-btn${service.active ? ' active' : ''}`}
                  >
                    <i className={`pgrid-icon ti ${service.ambulance ? 'ti-ambulance' : 'ti-category'}`} />
                    <span className="pgrid-lbl">{service.label}</span>
                    <span className="pgrid-sub">{service.count} actes</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="dem-filter-row sipn-filter-row" id="sipn-desktop-filter-row" aria-label="Trier et filtrer les résultats">
            <span className="dem-filter-lbl">Trier :</span>
            <button
              type="button"
              className="dem-sort-select"
              style={{ display: isMobileViewport ? 'none' : 'inline-flex' }}
              id="id-sort-dem"
              aria-label="Trier les résultats"
              aria-haspopup="listbox"
              aria-expanded={openFilterPanel === 'sort'}
              onClick={(event) => toggleFilterPanel('sort', event.currentTarget)}
            >
              {SORT_OPTIONS.find(([value]) => value === filters?.sort)?.[1] || 'Prix croissant'}
              <span aria-hidden="true">▼</span>
            </button>
            <button
              type="button"
              className="sipn-filter-chip"
              style={{ display: isMobileViewport ? 'inline-flex' : 'none' }}
              onClick={(event) => toggleFilterPanel('sort', event.currentTarget)}
              aria-expanded={openFilterPanel === 'sort'}
            >
              {mobileSortLabel}<span className="sipn-filter-arr" aria-hidden="true">▼</span>
            </button>

            <span className="dem-filter-lbl dem-filter-lbl--sep order-last lg:order-none">Régime :</span>
            <div className="inline-flex order-last rounded-lg bg-gray-100 p-0.5 text-xs font-semibold mr-1 lg:order-none" id="tritarif-regime-chips" role="radiogroup" aria-label="Régime de couverture">
              {[
                ['comptant', 'Comptant'],
                ['ipm', 'IPM'],
                ['assurance', 'Assurance privée'],
              ].map(([value, label]) => {
                const active = (filters?.regime || 'comptant') === value;
                return (
                  <button
                    type="button"
                    key={value}
                    onClick={() => setSingle('regime', value)}
                    className={`tritarif-chip-btn rounded-md px-2.5 py-1 transition-all ${
                      active
                        ? 'bg-white text-gray-900 shadow-xs font-bold ring-1 ring-gray-200'
                        : 'text-gray-600 hover:text-gray-900 font-medium'
                    }`}
                    aria-pressed={active}
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            <span className="dem-filter-lbl dem-filter-lbl--sep">Filtrer :</span>
            <button
              type="button"
              id="sipn-desktop-geo-chip"
              onClick={activateProximity}
              className={`filter-chip sipn-filter-chip${filters?.proximity ? ' active' : ''}`}
              title="Définir votre position pour trier à proximité"
            >
              <i className="ti ti-map-pin" /> {filters?.proximity ? 'Position active' : geo.loading ? 'Localisation…' : 'Près de moi'}
            </button>
            <button
              type="button"
              id="fc-assurance"
              onClick={(event) => toggleFilterPanel('assurance', event.currentTarget)}
              className={`filter-chip sipn-filter-chip${selectedAssurances.length ? ' active' : ''}`}
              aria-expanded={openFilterPanel === 'assurance'}
            >
              <i className="ti ti-shield-check" />
              {selectedAssurances.length ? `${selectedAssurances.length} assurance${selectedAssurances.length > 1 ? 's' : ''}` : 'Assurance'}
              <span className="dem-filter-arr" aria-hidden="true">▼</span>
            </button>
            <button
              type="button"
              id="fc-zone"
              onClick={(event) => toggleFilterPanel('zone', event.currentTarget)}
              className={`filter-chip sipn-filter-chip${filters?.city ? ' active' : ''}`}
              aria-expanded={openFilterPanel === 'zone'}
            >
              <i className="ti ti-map-pin" /> {filters?.city || 'Zone'}
              <span className="dem-filter-arr" aria-hidden="true">▼</span>
            </button>
            <button
              type="button"
              id="fc-budget"
              onClick={(event) => toggleFilterPanel('budget', event.currentTarget)}
              className={`filter-chip sipn-filter-chip${filters?.price_max ? ' active' : ''}`}
              aria-expanded={openFilterPanel === 'budget'}
            >
              <i className="ti ti-coin" /> {filters?.price_max ? `${Number(filters.price_max).toLocaleString('fr-FR')} F` : 'Budget'}
              <span className="dem-filter-arr" aria-hidden="true">▼</span>
            </button>
            <button
              type="button"
              id="fc-delai"
              onClick={(event) => toggleFilterPanel('delai', event.currentTarget)}
              className={`filter-chip sipn-filter-chip${filters?.delai ? ' active' : ''}`}
              aria-expanded={openFilterPanel === 'delai'}
            >
              <i className="ti ti-clock" /> {options?.delais.find((delay) => delay.id === filters?.delai)?.name || 'Délai'}
              <span className="dem-filter-arr" aria-hidden="true">▼</span>
            </button>
            {(filters?.active_count || searchParams.has('q')) ? (
              <button type="button" id="fc-reset" onClick={clearFilters} className="filter-chip sipn-filter-chip filter-chip--reset dem-filter-reset">
                × Réinitialiser
              </button>
            ) : null}

            <div
              id="sipn-filter-dropdown"
              className={`sipn-filter-dropdown${openFilterPanel ? '' : ' hidden'}`}
              hidden={!openFilterPanel}
              style={{ left: `${filterPanelLeft}px` }}
              aria-live="polite"
            >
              {openFilterPanel && renderFilterPanel(openFilterPanel, false)}
            </div>
          </div>
          {geo.error && <p className="mt-2 text-xs text-red-600" role="alert">{geo.error}</p>}

        </div>
      </section>

      {openFilterPanel && (
        <>
          <div
            className="sipn-m-sheet-overlay open"
            aria-hidden="true"
            onClick={() => setOpenFilterPanel(null)}
          />
          <section className="sipn-m-sheet open" role="dialog" aria-modal="true" aria-labelledby="sipn-m-sheet-title">
            <div className="sipn-m-sheet-handle" aria-hidden="true" />
            <div className="sipn-m-sheet-head">
              <div className="sipn-m-sheet-title" id="sipn-m-sheet-title">{filterPanelTitle(openFilterPanel)}</div>
            </div>
            <div className="sipn-m-sheet-body">{renderFilterPanel(openFilterPanel, true)}</div>
            {openFilterPanel !== 'sort' && (
              <div className="sipn-m-sheet-footer">
                <button type="button" className="sipn-m-sheet-apply" onClick={applyFilterPanel}>Appliquer</button>
              </div>
            )}
          </section>
        </>
      )}

      <div className="sipn-layout-wrap">
        <div className="grid items-start gap-5 lg:grid-cols-[265px_minmax(0,1fr)_380px]">
          <aside id="sidebar-desktop" className={`${actesOpen ? 'block' : 'hidden'} min-w-0 lg:block`}>
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <header className="border-b border-slate-100 bg-slate-50/80 px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="flex items-center gap-2 text-sm font-extrabold text-slate-800">
                      <i className="ti ti-list-search text-base text-[#287d9d]" />
                      Parcourir les actes
                    </h2>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">
                      Choisissez un ou plusieurs actes à comparer.
                    </p>
                  </div>
                  {activeActs.length > 0 && (
                    <span className="shrink-0 rounded-full bg-[#e7f4f8] px-2 py-1 text-[11px] font-bold text-[#287d9d]">
                      {activeActs.length} sélectionné{activeActs.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                {activeActs.length > 0 && (
                  <button
                    type="button"
                    onClick={() => changeParams((params) => {
                      params.delete('acte');
                      params.delete('lot');
                    })}
                    className="mt-2 text-xs font-semibold text-slate-500 transition hover:text-red-600"
                  >
                    <i className="ti ti-x mr-1" />Effacer la sélection
                  </button>
                )}
              </header>

              <div className="border-b border-slate-100 p-3">
                <label className="relative block">
                  <span className="sr-only">Rechercher un acte</span>
                  <i className="ti ti-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400" />
                  <input
                    value={actSearch}
                    onChange={(event) => setActSearch(event.target.value)}
                    placeholder="Rechercher un acte…"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-xs text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-[#4fa3c7] focus:bg-white focus:ring-2 focus:ring-[#4fa3c7]/15"
                  />
                </label>
              </div>

              <div className="max-h-[min(55vh,520px)] overflow-y-auto overscroll-contain p-2">
                {filteredFamilies.map((family) => {
                  const hasSelectedAct = family.subgroups.some((subgroup) =>
                    subgroup.acts.some((act) => act.id !== null && activeActs.includes(String(act.id)))
                  );
                  const serviceIsSelected = filters?.service === String(family.id);

                  return (
                    <details
                      className="group border-b border-slate-100 last:border-b-0"
                      key={family.id}
                      open={Boolean(actSearch.trim() || hasSelectedAct || serviceIsSelected)}
                    >
                      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg px-2.5 py-2.5 text-left text-xs font-bold text-slate-700 transition hover:bg-slate-50 hover:text-[#176b83] [&::-webkit-details-marker]:hidden">
                        <i className="ti ti-chevron-right text-xs text-slate-400 transition-transform group-open:rotate-90" />
                        <span className="min-w-0 flex-1">{family.title}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold tabular-nums text-slate-500 group-open:bg-[#e7f4f8] group-open:text-[#287d9d]">
                          {family.count}
                        </span>
                      </summary>
                      <div className="pb-2 pl-2">
                        {family.subgroups.map((subgroup) => {
                          const subgroupHasSelection = subgroup.acts.some(
                            (act) => act.id !== null && activeActs.includes(String(act.id))
                          );

                          return (
                            <details
                              className="group/sub border-t border-slate-50 first:border-t-0"
                              key={subgroup.title}
                              open={Boolean(actSearch.trim() || subgroupHasSelection)}
                            >
                              <summary className="flex cursor-pointer list-none items-center gap-2 rounded-md px-2.5 py-2 text-left text-[10px] font-semibold text-slate-500 transition hover:bg-slate-50 hover:text-slate-800 [&::-webkit-details-marker]:hidden">
                                <span className="min-w-0 flex-1">{subgroup.title || 'Autres actes'}</span>
                                <span className="shrink-0 tabular-nums text-[10px] text-slate-400">{subgroup.count}</span>
                                <i className="ti ti-chevron-down text-[10px] text-slate-400 transition-transform group-open/sub:rotate-180" />
                              </summary>
                              <div className="space-y-0.5 pb-2 pl-2">
                                {subgroup.acts.map((act) => {
                                  const selected = act.id !== null && activeActs.includes(String(act.id));
                                  return (
                                    <button
                                      type="button"
                                      key={`${act.id}-${act.name}`}
                                      disabled={act.id === null}
                                      title={act.id === null ? 'Cet acte n’est pas encore disponible' : undefined}
                                      onClick={() => act.id !== null && toggleAct(act.id)}
                                      aria-pressed={selected}
                                      className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[11px] transition ${
                                        selected
                                          ? 'bg-[#eaf5f8] font-semibold text-[#176b83]'
                                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                                      } ${act.id === null ? 'cursor-not-allowed opacity-45' : ''}`}
                                    >
                                      <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                                        selected
                                          ? 'border-[#4fa3c7] bg-[#4fa3c7] text-white'
                                          : 'border-slate-300 bg-white'
                                      }`}>
                                        {selected && <i className="ti ti-check text-[10px]" />}
                                      </span>
                                      <span className="min-w-0 flex-1 leading-snug">{act.name}</span>
                                      <span className={`shrink-0 text-[10px] tabular-nums ${selected ? 'text-[#287d9d]' : 'text-slate-400'}`}>
                                        {act.count}
                                      </span>
                                    </button>
                                  );
                                })}
                              </div>
                            </details>
                          );
                        })}
                      </div>
                    </details>
                  );
                })}
                {!filteredFamilies.length && (
                  <p className="px-3 py-8 text-center text-xs text-slate-500">
                    Aucun acte ne correspond à « {actSearch} ».
                  </p>
                )}
              </div>
            </section>

          </aside>

          <section id="results-col" className="min-w-0">
            <div className="results-header lg:hidden">
              <div className="results-header-row">
                <div className="results-header-text">
                  <div className="rh-acte">{currentData?.title || selectedActTokens.map((act) => act.name).join(', ')}</div>
                  <div className="rh-sub">{currentData?.subtitle || 'Structures et tarifs disponibles pour votre sélection.'}</div>
                </div>
                <button type="button" className="rh-back-btn" onClick={returnToSearch}>← Prestations</button>
              </div>
              <div className="sipn-mobile-results-filters" aria-label="Trier et filtrer les résultats">
                <button type="button" className="sipn-filter-chip" onClick={(event) => toggleFilterPanel('sort', event.currentTarget)}>
                  {mobileSortLabel}<span className="sipn-filter-arr" aria-hidden="true">▼</span>
                </button>
                <button type="button" className="sipn-filter-chip" onClick={activateProximity}>
                  <i className="ti ti-map-pin" /> {filters?.proximity ? 'Position active' : 'Près de moi'}
                </button>
                <button type="button" className="sipn-filter-chip" onClick={(event) => toggleFilterPanel('assurance', event.currentTarget)}>
                  {selectedAssurances.length ? `${selectedAssurances.length} assurance${selectedAssurances.length > 1 ? 's' : ''}` : 'Assurance'}
                </button>
                <button type="button" className="sipn-filter-chip" onClick={(event) => toggleFilterPanel('zone', event.currentTarget)}>
                  {filters?.city || 'Zone'}
                </button>
                <button type="button" className="sipn-filter-chip" onClick={(event) => toggleFilterPanel('budget', event.currentTarget)}>
                  {filters?.price_max ? `${Number(filters.price_max).toLocaleString('fr-FR')} F` : 'Budget'}
                </button>
                <button type="button" className="sipn-filter-chip" onClick={(event) => toggleFilterPanel('delai', event.currentTarget)}>
                  {options?.delais.find((delay) => delay.id === filters?.delai)?.name || 'Délai'}
                </button>
                <div className="inline-flex shrink-0 rounded-lg bg-gray-100 p-0.5 text-xs font-semibold" role="radiogroup" aria-label="Régime de couverture">
                  {[
                    ['comptant', 'Comptant'],
                    ['ipm', 'IPM'],
                    ['assurance', 'Assurance'],
                  ].map(([value, label]) => {
                    const active = (filters?.regime || 'comptant') === value;
                    return (
                      <button
                        type="button"
                        key={`mobile-${value}`}
                        onClick={() => setSingle('regime', value)}
                        className={`tritarif-chip-btn rounded-md px-2 py-0.5 transition-all ${
                          active
                            ? 'bg-white text-gray-900 shadow-xs font-bold ring-1 ring-gray-200'
                            : 'text-gray-600 hover:text-gray-900 font-medium'
                        }`}
                        aria-pressed={active}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="ctx-bar fade-in sipn-ctx-bar-desktop" role="status">
              <div className="ctx-acte">{currentData?.title || 'Sélectionnez un acte dans le menu ←'}</div>
              <div className="ctx-sub">{currentData?.subtitle || 'Parcourez une famille à gauche ou utilisez la recherche.'}</div>
            </div>

            <section className="struct-panel fade-in">
              <div className="sp-head">
                <div className="sp-title">Structures disponibles</div>
                <div className="sp-meta">
                  {structureOffers.length ? (
                    <>
                      <strong>{structureOffers.length}</strong> structure{structureOffers.length === 1 ? '' : 's'}
                    </>
                  ) : (
                    <>
                      <strong>{currentData?.results_count ?? 0}</strong> offre{currentData?.results_count === 1 ? '' : 's'}
                    </>
                  )}
                </div>
              </div>
              <div className="dem-struct-inner">
                <div id="struct-list-d" className="struct-list-d scard-list">
                  {loading ? (
                    <div className="empty-state-m">
                      <p className="empty-txt-m">Recherche des offres…</p>
                    </div>
                  ) : error ? (
                    <div className="empty-state-m" role="alert">
                      <p className="empty-txt-m">La recherche n’a pas abouti.</p>
                      <p className="empty-txt-m sipn-empty-hint-sub">{error}</p>
                    </div>
                  ) : !currentData?.offers.length ? (
                    <div className="empty-state-m">
                      <div className="empty-icon-m" aria-hidden="true"><i className="ti ti-arrow-left" /></div>
                      <p className="empty-txt-m">
                        {activeActs.length || searchParams.has('lot') || filters?.service || searchParams.has('q')
                          ? 'Aucune structure ne correspond à ces critères.'
                          : 'Sélectionnez un acte dans le menu pour voir toutes les structures qui le proposent.'}
                      </p>
                      {!activeActs.length && !searchParams.has('lot') && !filters?.service && !searchParams.has('q') && (
                        <p className="empty-txt-m sipn-empty-hint-sub">Parcourez une famille à gauche ou utilisez la recherche.</p>
                      )}
                    </div>
                  ) : (
                    isMobileViewport
                      ? structureOffers.map((offers, index) => (
                        <SearchStructureCard
                          key={offers[0]?.slug || offers[0]?.id}
                          offers={offers}
                          index={index}
                          regime={filters?.regime || 'comptant'}
                          hasSelectedInsurance={selectedAssurances.length > 0}
                          cartOfferIds={cartOfferIds}
                          cartActeIds={cartActeIds}
                          onAddToCart={onAddToCart}
                          onRemoveFromCart={onRemoveFromCart}
                        />
                      ))
                      : currentData.offers.map((offer, index) => (
                        <SearchCard
                          key={offer.id}
                          result={offer}
                          index={index}
                          regime={filters?.regime || 'comptant'}
                          hasSelectedInsurance={selectedAssurances.length > 0}
                          inCart={cartOfferIds.has(offer.id)}
                          acteInCartElsewhere={
                            offer.acte_id !== undefined
                            && cartActeIds.has(offer.acte_id)
                            && !cartOfferIds.has(offer.id)
                          }
                          onAddCart={onAddToCart}
                          onRemoveCart={onRemoveFromCart}
                        />
                      ))
                  )}
                </div>
              </div>
            </section>

            {!!currentData?.pagination.pages && currentData.pagination.pages > 1 && (
              <nav className="mt-5 flex items-center justify-center gap-2" aria-label="Pagination">
                <button
                  type="button"
                  disabled={!currentData.pagination.has_previous}
                  onClick={() => {
                    if (currentData.pagination.previous !== null) goToPage(currentData.pagination.previous);
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-40"
                >
                  Précédent
                </button>
                <span className="px-2 text-sm text-slate-600">Page {currentData.pagination.number} / {currentData.pagination.pages}</span>
                <button
                  type="button"
                  disabled={!currentData.pagination.has_next}
                  onClick={() => {
                    if (currentData.pagination.next !== null) goToPage(currentData.pagination.next);
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-40"
                >
                  Suivant
                </button>
              </nav>
            )}
          </section>
          <SearchCart
            items={cartItems}
            actsOpen={actesOpen}
            hasSelection={searchParams.has('acte') || searchParams.has('lot') || searchParams.has('q')}
            onBrowseActs={() => {
              if (!searchParams.has('acte') && !searchParams.has('lot') && !searchParams.has('q')) {
                searchInputRef.current?.focus();
                return;
              }
              setActesOpen((open) => !open);
            }}
            onRemoveItem={onRemoveFromCart}
            onClear={onClearCart}
            onRequestDevis={onRequestDevis}
          />
        </div>
      </div>
    </div>
  );
}
