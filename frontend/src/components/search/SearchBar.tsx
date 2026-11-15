import { useState, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { Search, MapPin, SlidersHorizontal } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { useGeoLocation } from '../../hooks/useGeoLocation';

interface SearchBarProps {
  onSearch: (params: { q: string; location: string; lat?: number; lon?: number }) => void;
  onFilterToggle?: () => void;
}

export function SearchBar({ onSearch, onFilterToggle }: SearchBarProps) {
  const { t } = useTranslation();
  const [q, setQ]           = useState('');
  const [location, setLoc]  = useState('');
  const geo                 = useGeoLocation();

  const handleSearch = () => {
    onSearch({ q, location, lat: geo.lat ?? undefined, lon: geo.lon ?? undefined });
  };

  const handleGeo = () => {
    geo.request();
  };

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <motion.div
      className="bg-white dark:bg-gray-800 rounded-2xl shadow-[0_8px_32px_rgba(10,92,138,.12)] p-4"
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          icon={<Search size={16} />}
          placeholder={t('search.placeholder_acte')}
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={handleKey}
          className="flex-1"
        />
        <Input
          icon={<MapPin size={16} />}
          placeholder={t('search.placeholder_location')}
          value={location}
          onChange={e => setLoc(e.target.value)}
          onKeyDown={handleKey}
          className="flex-1"
        />
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="md"
            onClick={handleGeo}
            loading={geo.loading}
            title={t('search.btn_geolocate')}
            className="shrink-0"
          >
            <MapPin size={16} />
          </Button>
          {onFilterToggle && (
            <Button variant="secondary" size="md" onClick={onFilterToggle} className="shrink-0">
              <SlidersHorizontal size={16} />
              <span className="hidden sm:inline">{t('search.filters')}</span>
            </Button>
          )}
          <Button size="md" onClick={handleSearch} className="shrink-0 px-6">
            {t('search.btn_search')}
          </Button>
        </div>
      </div>
      {geo.error && (
        <p className="mt-2 text-xs text-red-500">{geo.error}</p>
      )}
      {geo.lat && (
        <p className="mt-2 text-xs text-sipn-green">
          📍 {geo.lat.toFixed(4)}, {geo.lon?.toFixed(4)}
        </p>
      )}
    </motion.div>
  );
}
