import { useState, type KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useGeoLocation } from '../../hooks/useGeoLocation';

interface SearchBarProps {
  onSearch: (params: { q: string; location: string; lat?: number; lon?: number }) => void;
  onFilterToggle?: () => void;
}

export function SearchBar({ onSearch, onFilterToggle }: SearchBarProps) {
  const { t } = useTranslation();
  const [q, setQ] = useState('');
  const [location, setLoc] = useState('');
  const geo = useGeoLocation();

  const handleSearch = () => {
    onSearch({ q, location, lat: geo.lat ?? undefined, lon: geo.lon ?? undefined });
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <motion.div
      className="bg-white dark:bg-gray-800 rounded-2xl shadow-[0_4px_24px_rgba(18,58,99,.08)] border border-gray-200/80 dark:border-gray-700/80 p-3.5 sm:p-4"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col sm:flex-row gap-2.5 sm:gap-3">
        {/* Acte or Specialty Input */}
        <div className="relative flex-1">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
            <i className="ti ti-search text-base"></i>
          </span>
          <input
            type="text"
            placeholder={t('search.placeholder_acte')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={handleKey}
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50/60 dark:bg-gray-750 text-gray-900 dark:text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#4fa3c7]/50 focus:border-[#4fa3c7] transition-all"
          />
        </div>

        {/* Location Input */}
        <div className="relative flex-1">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
            <i className="ti ti-map-pin text-base"></i>
          </span>
          <input
            type="text"
            placeholder={t('search.placeholder_location')}
            value={location}
            onChange={(e) => setLoc(e.target.value)}
            onKeyDown={handleKey}
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50/60 dark:bg-gray-750 text-gray-900 dark:text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-[#4fa3c7]/50 focus:border-[#4fa3c7] transition-all"
          />
        </div>

        {/* Buttons (Geo + Filters + Submit) */}
        <div className="flex gap-2 shrink-0">
          <button
            type="button"
            onClick={() => geo.request()}
            className="p-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-600 dark:text-gray-300 hover:text-[#4fa3c7] hover:border-[#4fa3c7] transition-all"
            title={t('search.btn_geolocate')}
          >
            <i className={`ti ti-current-location text-lg ${geo.loading ? 'animate-spin' : ''}`}></i>
          </button>

          {onFilterToggle && (
            <button
              type="button"
              onClick={onFilterToggle}
              className="flex items-center gap-1.5 px-3.5 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-700 dark:text-gray-300 font-bold text-xs hover:border-[#4fa3c7] transition-all"
            >
              <i className="ti ti-adjustments-horizontal text-base"></i>
              <span className="hidden sm:inline">{t('search.filters')}</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleSearch}
            className="flex-1 sm:flex-initial px-6 py-3 rounded-xl bg-gradient-to-r from-[#123a63] to-[#4fa3c7] text-white font-bold text-xs shadow-md hover:shadow-lg hover:brightness-105 active:scale-95 transition-all flex items-center justify-center gap-1.5"
          >
            <i className="ti ti-search text-sm"></i>
            <span>{t('search.btn_search')}</span>
          </button>
        </div>
      </div>

      {geo.lat && (
        <p className="mt-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
          <i className="ti ti-circle-check"></i> Position détectée : {geo.lat.toFixed(4)}, {geo.lon?.toFixed(4)}
        </p>
      )}
      {geo.error && (
        <p className="mt-2 text-xs text-red-500 flex items-center gap-1">
          <i className="ti ti-alert-circle"></i> {geo.error}
        </p>
      )}
    </motion.div>
  );
}
