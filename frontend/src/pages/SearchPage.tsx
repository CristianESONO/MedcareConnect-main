import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { SearchBar } from '../components/search/SearchBar';
import { SearchCard } from '../components/search/SearchCard';
import { FilterPanel, FilterState } from '../components/search/FilterPanel';
import { SearchResult, searchActes } from '../lib/api';

// Realistic mock data mirroring Django structures & acts
const MOCK_RESULTS: SearchResult[] = [
  {
    id: 1,
    nom: 'Hôpital Principal de Dakar',
    type: 'Hôpital Militaire / Public',
    ville: 'Dakar-Plateau',
    distance_km: 1.2,
    note_moyenne: 4.8,
    price_min: 15000,
    price_max: 45000,
    actes: ['Consultation Générale', 'Hémogramme Complet', 'Radiographie Thoracique'],
    slug: 'hopital-principal-dakar',
  },
  {
    id: 2,
    nom: 'Clinique de la Madeleine',
    type: 'Clinique Privée',
    ville: 'Dakar-Plateau',
    distance_km: 2.4,
    note_moyenne: 4.6,
    price_min: 25000,
    price_max: 95000,
    actes: ['Échographie Abdominale', 'Consultation Cardiologie', 'Bilan Métabolique'],
    slug: 'clinique-madeleine',
  },
  {
    id: 3,
    nom: 'Centre Médical Diamniadio',
    type: 'Centre de Santé',
    ville: 'Diamniadio',
    distance_km: 14.8,
    note_moyenne: 4.3,
    price_min: 8000,
    price_max: 22000,
    actes: ['Consultation Pédiatrie', 'Test Paludisme Goutte Épaisse', 'Vaccination'],
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
    actes: ['Bilan Lipidique', 'Glycémie à jeun', 'Sérologie'],
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
        // Fallback filter on local data
        filterLocalResults(params.q, params.location);
      }
    } catch {
      // Offline / API down fallback
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

  // Apply filters & sorting
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
    <div className="min-h-screen py-8 px-4 max-w-7xl mx-auto">
      {/* Hero Section with Framer Motion */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center max-w-2xl mx-auto mb-8"
      >
        <span className="text-xs font-bold text-accent uppercase tracking-widest px-3 py-1 rounded-full bg-accent/10">
          Système Intégré de Parcours Numérique (SIPN)
        </span>
        <h1 className="font-syne font-extrabold text-3xl sm:text-4xl text-navy dark:text-white mt-3 mb-2">
          {t('search.title')}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t('search.subtitle')}
        </p>
      </motion.div>

      {/* Search Input Bar */}
      <div className="max-w-4xl mx-auto mb-6">
        <SearchBar
          onSearch={handleSearch}
          onFilterToggle={() => setFilterOpen((o) => !o)}
        />
      </div>

      {/* Collapsible Filter Panel */}
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

      {/* Results Header */}
      <div className="max-w-4xl mx-auto flex items-center justify-between mb-4">
        <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider">
          {displayedResults.length} {t('search.results')}
        </p>
      </div>

      {/* Results Cards List */}
      <div className="max-w-4xl mx-auto flex flex-col gap-4">
        {loading ? (
          <div className="py-16 text-center text-gray-400">
            <span className="inline-block w-8 h-8 border-3 border-accent border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm font-medium">{t('common.loading')}</p>
          </div>
        ) : displayedResults.length === 0 ? (
          <div className="py-16 text-center text-gray-400">
            <p className="text-base font-semibold text-gray-600 dark:text-gray-400">
              {t('search.no_results')}
            </p>
          </div>
        ) : (
          displayedResults.map((result, idx) => (
            <SearchCard
              key={result.id}
              result={result}
              index={idx}
              onAddCart={onAddToCart}
              onViewDetails={(r) => alert(`Détails pour: ${r.nom}`)}
            />
          ))
        )}
      </div>
    </div>
  );
}
