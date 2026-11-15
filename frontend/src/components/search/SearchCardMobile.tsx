import { useState } from 'react';
import { motion } from 'framer-motion';
import { SearchResult } from '../../lib/api';

interface SearchCardMobileProps {
  result: SearchResult;
  index?: number;
  onSelect?: (r: SearchResult) => void;
  onAddCart?: (r: SearchResult) => void;
}

export function SearchCardMobile({ result, index = 0, onSelect, onAddCart }: SearchCardMobileProps) {
  const [selectedActs, setSelectedActs] = useState<string[]>(
    result.actes && result.actes.length > 0 ? [result.actes[0]] : []
  );

  const toggleAct = (acte: string) => {
    if (selectedActs.includes(acte)) {
      setSelectedActs(selectedActs.filter((a) => a !== acte));
    } else {
      setSelectedActs([...selectedActs, acte]);
    }
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.25 }}
      className="scard-m bg-white dark:bg-gray-800 dark:border-gray-700/80 mb-3 shadow-sm rounded-xl overflow-hidden"
    >
      {/* ── Head ────────────────────────────────────────────── */}
      <div className="scard-m-head p-3.5 pb-2">
        <div className="scard-m-head-row flex items-center justify-between gap-2">
          <div className="scard-m-name flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              className="scard-org-name font-bold font-syne dark:text-white text-left"
              onClick={() => onSelect?.(result)}
            >
              {result.nom}
            </button>
            <span className="pioneer-badge-m text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-accent text-white">
              Vérifié
            </span>
          </div>

          {result.distance_km !== undefined && (
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200/60 shrink-0">
              <i className="ti ti-map-pin text-[10px]"></i> {result.distance_km.toFixed(1)} km
            </span>
          )}
        </div>

        <div className="scard-m-type text-xs text-gray-500 dark:text-gray-400 font-medium mt-0.5">
          {result.type}
        </div>

        <div className="scard-m-meta flex items-center gap-3 text-xs text-gray-400 mt-1">
          <span className="smeta-m flex items-center gap-1">
            <i className="ti ti-map-pin"></i> {result.ville || 'Dakar'}
          </span>
          <span className="smeta-m flex items-center gap-1">
            <i className="ti ti-clock"></i> 24h/24
          </span>
        </div>
      </div>

      {/* ── Actes List ───────────────────────────────────────── */}
      <div className="border-t border-gray-100 dark:border-gray-700/60 divide-y divide-gray-100 dark:divide-gray-700/40">
        {result.actes?.map((acte) => {
          const isChecked = selectedActs.includes(acte);
          return (
            <div
              key={acte}
              onClick={() => toggleAct(acte)}
              className={`scard-m-acte flex items-center gap-2.5 p-3 cursor-pointer transition-colors ${
                isChecked
                  ? 'bg-accent/5 dark:bg-accent/15'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-750'
              }`}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => toggleAct(acte)}
                className="scard-m-checkbox accent-accent w-4 h-4 cursor-pointer"
              />
              <div className="scard-m-acte-info min-w-0 flex-1">
                <div className="scard-m-acte-nom font-semibold text-xs text-gray-800 dark:text-gray-100 truncate">
                  {acte}
                </div>
                <div className="text-[10px] text-gray-400">Tiers-payant disponible</div>
              </div>
              <div className="scard-m-pricing text-right shrink-0">
                <div className="scard-m-acte-prix font-bold text-xs text-navy dark:text-accent">
                  {(result.price_min || 15000).toLocaleString()} F
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Footer ──────────────────────────────────────────── */}
      <div className="p-2.5 bg-gray-50/80 dark:bg-gray-850 border-t border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
        <span className="text-[11px] text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <i className="ti ti-shield text-emerald-600"></i> IPM & Assurances
        </span>

        {onAddCart && (
          <button
            type="button"
            onClick={() => onAddCart(result)}
            className="px-3 py-1.5 rounded-lg bg-accent hover:bg-accent-dark text-white text-xs font-bold transition-all shadow-sm flex items-center gap-1"
          >
            <i className="ti ti-plus"></i> Panier
          </button>
        )}
      </div>
    </motion.article>
  );
}
