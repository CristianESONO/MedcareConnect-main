import { useState } from 'react';
import { motion } from 'framer-motion';
import { SearchResult } from '../../lib/api';

interface SearchCardProps {
  result: SearchResult;
  index?: number;
  onAddCart?: (r: SearchResult) => void;
  onViewDetails?: (r: SearchResult) => void;
}

export function SearchCard({ result, index = 0, onAddCart, onViewDetails }: SearchCardProps) {
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

  const isAnyInCart = selectedActs.length > 0;

  return (
    <motion.article
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      className={`scard ${isAnyInCart ? 'scard--in-cart' : ''} bg-white dark:bg-gray-800 dark:border-gray-700/80`}
    >
      {/* ── Top Header ────────────────────────────────────────── */}
      <div className="scard-header">
        <div className="scard-org">
          <div className="scard-org-logo scard-org-logo--fallback">
            {result.nom.charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                className="scard-org-name font-syne dark:text-white"
                onClick={() => onViewDetails?.(result)}
              >
                {result.nom}
              </button>
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                <i className="ti ti-circle-check text-xs"></i> Vérifié
              </span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 font-medium">
              {result.type}
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1 flex-wrap">
              <span className="inline-flex items-center gap-1">
                <i className="ti ti-map-pin text-accent"></i>
                {result.ville || 'Dakar'}
              </span>
              <span className="inline-flex items-center gap-1">
                <i className="ti ti-clock text-gray-400"></i>
                24h/24 • 7j/7
              </span>
              {result.distance_km !== undefined && (
                <span className="sipn-dist-badge inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-accent/10 text-accent">
                  <i className="ti ti-navigation"></i>
                  {result.distance_km.toFixed(1)} km
                </span>
              )}
            </div>
          </div>
        </div>

        {result.note_moyenne !== undefined && (
          <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 text-xs font-bold shrink-0">
            <i className="ti ti-star-filled text-amber-500 text-xs"></i>
            {result.note_moyenne.toFixed(1)}
          </div>
        )}
      </div>

      {/* ── Actes & Grille Tarifaire ──────────────────────────── */}
      <div className="scard-actes dark:bg-gray-850 dark:border-gray-700">
        <div className="scard-actes-title dark:text-gray-300">
          <span>Tarif pour les actes sélectionnés</span>
          <span className="scard-actes-count">
            {result.actes?.length || 1} acte au catalogue
          </span>
        </div>

        <div className="flex flex-col gap-1">
          {result.actes?.map((acte) => {
            const inCart = selectedActs.includes(acte);
            return (
              <div
                key={acte}
                onClick={() => toggleAct(acte)}
                className={`acte-item ${inCart ? 'in-cart' : ''} dark:hover:bg-gray-800`}
              >
                <input
                  type="checkbox"
                  checked={inCart}
                  onChange={() => toggleAct(acte)}
                  className="ai-check"
                />
                <div className="ai-info min-w-0">
                  <div className="ai-nom dark:text-gray-100">{acte}</div>
                  <div className="ai-cat">Soin conventionné • Tiers-payant accepté</div>
                </div>
                <div className="ai-delai text-gray-400 text-xs hidden sm:block">
                  Résultats &lt; 24h
                </div>
                <div className="ai-prix dark:text-accent font-bold">
                  {(result.price_min || 15000).toLocaleString()} FCFA
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Footer & Actions ─────────────────────────────────── */}
      <div className="scard-footer dark:border-gray-700/60">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="scard-footer-left text-xs text-gray-500 dark:text-gray-400 flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 font-medium text-emerald-700 dark:text-emerald-400">
              <i className="ti ti-shield-check text-base"></i>
              Prise en charge IPM, Assurances & Mutuelles
            </span>
          </div>

          <div className="scard-footer-actions flex items-center gap-2">
            {onViewDetails && (
              <button
                type="button"
                className="scard-btn-secondary dark:bg-gray-750 dark:text-gray-200 dark:border-gray-600"
                onClick={() => onViewDetails(result)}
              >
                Fiche structure
              </button>
            )}
            {onAddCart && (
              <button
                type="button"
                className="scard-btn-primary"
                onClick={() => onAddCart(result)}
              >
                <i className="ti ti-shopping-cart text-sm mr-1"></i>
                Ajouter au panier ({selectedActs.length})
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.article>
  );
}
