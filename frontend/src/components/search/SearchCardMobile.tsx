import { motion } from 'framer-motion';
import { MapPin, Star, Plus, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../ui/Badge';
import { SearchResult } from '../../lib/api';
import { cn } from '../../lib/cn';

interface SearchCardMobileProps {
  result: SearchResult;
  index?: number;
  onSelect?: (r: SearchResult) => void;
  onAddCart?: (r: SearchResult) => void;
}

export function SearchCardMobile({ result, index = 0, onSelect, onAddCart }: SearchCardMobileProps) {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-3 shadow-sm border border-gray-100 dark:border-gray-700/60 flex flex-col gap-2.5 active:scale-[0.99] transition-transform"
      onClick={() => onSelect?.(result)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-lg bg-navy/5 dark:bg-navy/20 flex items-center justify-center font-bold text-navy dark:text-accent font-syne text-base">
            {result.nom.charAt(0)}
          </div>
          <div>
            <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-100 leading-tight font-syne">
              {result.nom}
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{result.ville || result.type}</p>
          </div>
        </div>

        {result.distance_km !== undefined && (
          <Badge
            variant={result.distance_km < 3 ? 'green' : 'gray'}
            className="text-[11px] px-1.5 py-0.5 font-semibold"
          >
            <MapPin size={10} />
            {result.distance_km.toFixed(1)} {t('search.km_away')}
          </Badge>
        )}
      </div>

      {result.actes?.length > 0 && (
        <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 no-scrollbar">
          {result.actes.slice(0, 2).map((a) => (
            <span
              key={a}
              className="text-[11px] px-2 py-0.5 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200/60 dark:border-gray-600 whitespace-nowrap"
            >
              {a}
            </span>
          ))}
          {result.actes.length > 2 && (
            <span className="text-[10px] text-gray-400">+{result.actes.length - 2}</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-1 border-t border-gray-100 dark:border-gray-700/50 mt-1">
        <div className="flex items-center gap-2 text-xs">
          {result.price_min !== undefined && (
            <span className="font-bold text-navy dark:text-accent text-sm">
              {result.price_min.toLocaleString()} <span className="text-[10px] font-normal text-gray-500">FCFA</span>
            </span>
          )}
          {result.note_moyenne !== undefined && (
            <span className="flex items-center gap-0.5 text-amber-500 text-xs">
              <Star size={11} fill="currentColor" />
              {result.note_moyenne.toFixed(1)}
            </span>
          )}
        </div>

        {onAddCart && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onAddCart(result);
            }}
            className="p-1.5 rounded-lg bg-accent/10 hover:bg-accent text-accent hover:text-white transition-colors"
            title={t('search.add_cart')}
          >
            <Plus size={16} />
          </button>
        )}
      </div>
    </motion.div>
  );
}
