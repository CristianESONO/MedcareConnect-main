import { useState } from 'react';
import { motion } from 'framer-motion';
import { type SearchResult } from '../../lib/api';

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
      className="scard-m bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 mb-3.5 shadow-sm rounded-2xl overflow-hidden"
    >
      {/* ── Head ────────────────────────────────────────────── */}
      <div className="scard-m-head p-4 pb-2.5">
        <div className="scard-m-head-row flex items-center justify-between gap-2">
          <div className="scard-m-name flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              className="scard-org-name font-black font-syne text-sm text-[#0f172a] dark:text-white text-left"
              onClick={() => onSelect?.(result)}
            >
              {result.nom}
            </button>
            <span className="pioneer-badge-m text-[9.5px] font-extrabold px-2 py-0.5 rounded-full bg-[#0ea5e9] text-white">
              Vérifié
            </span>
          </div>

          {result.distance_km !== undefined && (
            <span className="text-[11.5px] font-black px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-300 shrink-0">
              <i className="ti ti-map-pin text-[11px]"></i> {result.distance_km.toFixed(1)} km
            </span>
          )}
        </div>

        <div className="scard-m-type text-xs text-gray-700 dark:text-gray-300 font-bold mt-0.5">
          {result.type}
        </div>

        <div className="scard-m-meta flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400 mt-1 font-medium">
          <span className="smeta-m flex items-center gap-1">
            <i className="ti ti-map-pin text-[#0ea5e9]"></i> {result.ville || 'Dakar'}
          </span>
          <span className="smeta-m flex items-center gap-1">
            <i className="ti ti-clock"></i> 24h/24
          </span>
        </div>
      </div>

      {/* ── Actes List ───────────────────────────────────────── */}
      <div className="border-t border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700/50">
        {result.actes?.map((acte) => {
          const isChecked = selectedActs.includes(acte);
          return (
            <div
              key={acte}
              onClick={() => toggleAct(acte)}
              className={`scard-m-acte flex items-center gap-3 p-3.5 cursor-pointer transition-colors ${
                isChecked
                  ? 'bg-sky-50/70 dark:bg-sky-950/30'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-750'
              }`}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => toggleAct(acte)}
                className="scard-m-checkbox accent-[#0ea5e9] w-4 h-4 cursor-pointer shrink-0"
              />
              <div className="scard-m-acte-info min-w-0 flex-1">
                <div className="scard-m-acte-nom font-bold text-xs text-gray-900 dark:text-gray-100 truncate">
                  {acte}
                </div>
                <div className="text-[11px] text-gray-600 dark:text-gray-400 font-medium">
                  Tiers-payant disponible
                </div>
              </div>
              <div className="scard-m-pricing text-right shrink-0">
                <div className="scard-m-acte-prix font-black text-xs text-[#123a63] dark:text-[#0ea5e9]">
                  {(result.price_min || 15000).toLocaleString()} F
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Footer ──────────────────────────────────────────── */}
      <div className="p-3 bg-gray-50 dark:bg-gray-850 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <span className="text-[11px] font-bold text-gray-600 dark:text-gray-400 flex items-center gap-1">
          <i className="ti ti-shield text-emerald-600"></i> IPM & Assurances
        </span>

        {onAddCart && (
          <button
            type="button"
            onClick={() => onAddCart(result)}
            className="px-3.5 py-1.5 rounded-xl bg-[#0ea5e9] hover:bg-[#0284c7] text-white text-xs font-black transition-all shadow-sm flex items-center gap-1 active:scale-95"
          >
            <i className="ti ti-plus"></i> Panier
          </button>
        )}
      </div>
    </motion.article>
  );
}
