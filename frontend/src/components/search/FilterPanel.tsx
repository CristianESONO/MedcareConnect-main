import { motion, AnimatePresence } from 'framer-motion';
import { X, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/Button';

export interface FilterState {
  type: string;
  maxDistance: number;
  maxPrice: number;
  sortBy: 'distance' | 'price' | 'note';
}

interface FilterPanelProps {
  open: boolean;
  filters: FilterState;
  onChange: (f: FilterState) => void;
  onReset: () => void;
  onClose: () => void;
}

const STRUCTURE_TYPES = [
  'Tous',
  'Hôpital',
  'Clinique',
  'Cabinet Médical',
  'Centre de Santé',
  'Pharmacie',
  'Laboratoire',
];

export function FilterPanel({ open, filters, onChange, onReset, onClose }: FilterPanelProps) {
  const { t } = useTranslation();

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="overflow-hidden bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 p-5 mb-6 shadow-sm"
        >
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-700">
            <h3 className="font-syne font-semibold text-navy dark:text-white text-base">
              {t('search.filters')}
            </h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <X size={18} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 py-4">
            {/* Structure Type */}
            <div>
              <label className="block text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider mb-2">
                {t('search.type')}
              </label>
              <div className="flex flex-wrap gap-1.5">
                {STRUCTURE_TYPES.map((type) => {
                  const isSelected = (type === 'Tous' && !filters.type) || filters.type === type;
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => onChange({ ...filters, type: type === 'Tous' ? '' : type })}
                      className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                        isSelected
                          ? 'bg-navy text-white border-navy dark:bg-accent dark:border-accent'
                          : 'bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-gray-300'
                      }`}
                    >
                      {type}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Max Distance */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
                  {t('search.distance')} max
                </label>
                <span className="text-xs font-medium text-navy dark:text-accent">
                  {filters.maxDistance} km
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={filters.maxDistance}
                onChange={(e) => onChange({ ...filters, maxDistance: Number(e.target.value) })}
                className="w-full accent-navy dark:accent-accent cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                <span>1 km</span>
                <span>50 km</span>
                <span>100 km</span>
              </div>
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider mb-2">
                {t('search.sort_by')}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['distance', 'price', 'note'] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onChange({ ...filters, sortBy: s })}
                    className={`text-xs py-2 px-1 text-center rounded-xl border font-medium capitalize transition-all ${
                      filters.sortBy === s
                        ? 'border-accent bg-accent/10 text-accent font-semibold'
                        : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-750'
                    }`}
                  >
                    {t(`search.sort_${s}`)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-700">
            <Button variant="ghost" size="sm" onClick={onReset}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" onClick={onClose}>
              <Check size={14} />
              Appliquer
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
