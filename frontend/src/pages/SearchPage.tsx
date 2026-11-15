import { useState } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { SearchBar } from '../components/search/SearchBar';
import { SearchCard } from '../components/search/SearchCard';
import { FilterPanel, type FilterState } from '../components/search/FilterPanel';
import { type SearchResult, searchActes } from '../lib/api';

const MOCK_RESULTS: SearchResult[] = [
  {
    id: 1,
    nom: 'Hôpital Principal de Dakar',
    type: 'Hôpital Militaire / Établissement Public',
    ville: 'Dakar-Plateau',
    distance_km: 1.2,
    note_moyenne: 4.8,
    price_min: 15000,
    price_max: 45000,
    actes: ['Consultation Médecine Générale', 'Hémogramme Complet (NFS)', 'Radiographie Thoracique'],
    slug: 'hopital-principal-dakar',
  },
  {
    id: 2,
    nom: 'Clinique de la Madeleine',
    type: 'Clinique Médico-Chirurgicale Privée',
    ville: 'Dakar-Plateau',
    distance_km: 2.4,
    note_moyenne: 4.6,
    price_min: 25000,
    price_max: 95000,
    actes: ['Échographie Abdomino-Pelvienne', 'Consultation Cardiologie', 'Bilan Métabolique'],
    slug: 'clinique-madeleine',
  },
  {
    id: 3,
    nom: 'Centre de Santé Pasteur Diamniadio',
    type: 'Centre de Santé Polyvalent',
    ville: 'Diamniadio',
    distance_km: 14.8,
    note_moyenne: 4.3,
    price_min: 8000,
    price_max: 22000,
    actes: ['Consultation Pédiatrique', 'Test Paludisme Goutte Épaisse', 'Vaccination'],
    slug: 'centre-diamniadio',
  },
  {
    id: 4,
    nom: 'Laboratoire Bio-Santé Almadies',
    type: 'Laboratoire d\'Analyses Médicales',
    ville: 'Les Almadies',
    distance_km: 5.1,
    note_moyenne: 4.9,
    price_min: 12000,
    price_max: 38000,
    actes: ['Bilan Lipidique Complet', 'Glycémie à jeun', 'Sérologie'],
    slug: 'labo-bio-sante-almadies',
  },
];

interface SearchPageProps {
  onAddToCart: (result: SearchResult) => void;
}

export function SearchPage({ onAddToCart }: SearchPageProps) {
  const { t } = useTranslation();
  const [results, setResults] = useState<SearchResult[]>(MOCK_RESULTS);
  const [loading, setLoading] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    type: '',
    maxDistance: 50,
    maxPrice: 100000,
    sortBy: 'distance',
  });

  const handleSearch = async (params: { q: string; location: string; lat?: number; lon?: number }) => {
    setLoading(true);
    try {
      const res = await searchActes(params);
      if (res?.results?.length) {
        setResults(res.results);
      } else {
        filterLocalResults(params.q, params.location);
      }
    } catch {
      filterLocalResults(params.q, params.location);
    } finally {
      setLoading(false);
    }
  };

  const filterLocalResults = (query: string, loc: string) => {
    let filtered = [...MOCK_RESULTS];
    if (query) {
      const q = query.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.nom.toLowerCase().includes(q) ||
          r.actes.some((a) => a.toLowerCase().includes(q))
      );
    }
    if (loc) {
      filtered = filtered.filter((r) =>
        r.ville?.toLowerCase().includes(loc.toLowerCase())
      );
    }
    setResults(filtered);
  };

  const displayedResults = results
    .filter((r) => !filters.type || r.type.toLowerCase().includes(filters.type.toLowerCase()))
    .filter((r) => r.distance_km === undefined || r.distance_km <= filters.maxDistance)
    .sort((a, b) => {
      if (filters.sortBy === 'distance') return (a.distance_km || 999) - (b.distance_km || 999);
      if (filters.sortBy === 'price') return (a.price_min || 0) - (b.price_min || 0);
      if (filters.sortBy === 'note') return (b.note_moyenne || 0) - (a.note_moyenne || 0);
      return 0;
    });

  return (
    <div className="min-h-screen py-8 px-4 max-w-6xl mx-auto">
      {/* ── MedCare Hero Banner ─────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center max-w-3xl mx-auto mb-8"
      >
        <span className="inline-flex items-center gap-1.5 text-xs font-extrabold text-[#4fa3c7] uppercase tracking-wider px-3.5 py-1.5 rounded-full bg-[#4fa3c7]/10 mb-3">
          <i className="ti ti-shield-heart text-sm"></i>
          Plateforme Nationale de Santé • Parcours SIPN
        </span>
        <h1 className="font-syne font-extrabold text-3xl sm:text-4xl text-[#123a63] dark:text-white leading-tight mb-3">
          Trouvez un professionnel & comparez les tarifs
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xl mx-auto leading-relaxed">
          Recherchez un acte, une spécialité ou un hôpital à Dakar et dans les régions. Transparence des prix, conventionnement assurances et prise de rendez-vous.
        </p>
      </motion.div>

      {/* ── Search Bar Input ───────────────────────────────────── */}
      <div className="max-w-4xl mx-auto mb-5">
        <SearchBar
          onSearch={handleSearch}
          onFilterToggle={() => setFilterOpen((o) => !o)}
        />
      </div>

      {/* ── Filter Panel ───────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto">
        <FilterPanel
          open={filterOpen}
          filters={filters}
          onChange={setFilters}
          onReset={() =>
            setFilters({ type: '', maxDistance: 50, maxPrice: 100000, sortBy: 'distance' })
          }
          onClose={() => setFilterOpen(false)}
        />
      </div>

      {/* ── Search Results Container (with authentic #search-form wrapper) ── */}
      <div id="search-form" className="search-page--dem max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-4 px-1">
          <p className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
            <i className="ti ti-building-hospital text-accent text-sm"></i>
            {displayedResults.length} {t('search.results')} trouvés
          </p>

          <span className="text-xs text-gray-400">
            Tri actuel : <strong className="text-gray-700 dark:text-gray-200 capitalize">{filters.sortBy}</strong>
          </span>
        </div>

        {/* ── Results Cards List ── */}
        <div id="results-col">
          <div className="space-y-4 flex flex-col gap-4">
            {loading ? (
              <div className="py-20 text-center text-gray-400">
                <span className="inline-block w-8 h-8 border-3 border-accent border-t-transparent rounded-full animate-spin mb-3" />
                <p className="text-sm font-medium">{t('common.loading')}</p>
              </div>
            ) : displayedResults.length === 0 ? (
              <div className="py-16 text-center text-gray-400 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-8">
                <i className="ti ti-search-off text-4xl text-gray-300 dark:text-gray-600 mb-3 block"></i>
                <p className="text-base font-bold text-gray-700 dark:text-gray-300">
                  {t('search.no_results')}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Essayez d'ajuster vos critères ou élargissez le rayon de recherche.
                </p>
              </div>
            ) : (
              displayedResults.map((result, idx) => (
                <SearchCard
                  key={result.id}
                  result={result}
                  index={idx}
                  onAddCart={onAddToCart}
                  onViewDetails={(r) => alert(`Fiche structure : ${r.nom} (${r.type})`)}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
