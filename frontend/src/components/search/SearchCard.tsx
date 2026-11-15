import { motion } from 'framer-motion';
import { MapPin, Star, ShoppingCart, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { SearchResult } from '../../lib/api';
import { cn } from '../../lib/cn';

interface SearchCardProps {
  result: SearchResult;
  index?: number;
  onAddCart?: (r: SearchResult) => void;
  onViewDetails?: (r: SearchResult) => void;
}

export function SearchCard({ result, index = 0, onAddCart, onViewDetails }: SearchCardProps) {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.35 }}
    >
      <Card hover className="p-4 flex gap-4">
        {/* Logo placeholder */}
        <div className="shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-navy/10 to-accent/10 flex items-center justify-center text-navy dark:text-accent font-bold text-xl font-syne">
          {result.nom.charAt(0)}
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div>
              <h3 className="font-semibold text-gray-800 dark:text-white truncate font-syne">{result.nom}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{result.type}</p>
            </div>
            {result.note_moyenne !== undefined && (
              <Badge variant="green" className="shrink-0">
                <Star size={10} fill="currentColor" />
                {result.note_moyenne.toFixed(1)}
              </Badge>
            )}
          </div>

          {/* Actes */}
          {result.actes?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {result.actes.slice(0, 3).map((a) => (
                <Badge key={a} variant="accent">{a}</Badge>
              ))}
              {result.actes.length > 3 && (
                <Badge variant="gray">+{result.actes.length - 3}</Badge>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="mt-3 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
              {result.distance_km !== undefined && (
                <span className={cn(
                  'flex items-center gap-1 font-medium',
                  result.distance_km < 2 ? 'text-sipn-green' : result.distance_km < 10 ? 'text-accent' : 'text-gray-500'
                )}>
                  <MapPin size={12} />
                  {result.distance_km.toFixed(1)} {t('search.km_away')}
                </span>
              )}
              {result.price_min !== undefined && (
                <span>
                  {result.price_min.toLocaleString()} – {result.price_max?.toLocaleString()} FCFA
                </span>
              )}
            </div>

            <div className="flex gap-2">
              {onViewDetails && (
                <Button variant="ghost" size="sm" onClick={() => onViewDetails(result)}>
                  <ExternalLink size={14} />
                  {t('search.see_details')}
                </Button>
              )}
              {onAddCart && (
                <Button size="sm" onClick={() => onAddCart(result)}>
                  <ShoppingCart size={14} />
                  {t('search.add_cart')}
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
