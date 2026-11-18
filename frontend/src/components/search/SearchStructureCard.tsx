import { useState } from 'react';
import type { SearchResult } from '../../lib/api';

interface SearchStructureCardProps {
  offers: SearchResult[];
  index: number;
  regime: string;
  hasSelectedInsurance: boolean;
  cartOfferIds: ReadonlySet<number>;
  cartActeIds: ReadonlySet<number>;
  onAddToCart: (result: SearchResult) => void | Promise<void>;
  onRemoveFromCart: (id: number) => void | Promise<void>;
}

function formatPrice(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '';
  return Number(value).toLocaleString('fr-FR');
}

export function SearchStructureCard({
  offers,
  index,
  regime,
  hasSelectedInsurance,
  cartOfferIds,
  cartActeIds,
  onAddToCart,
  onRemoveFromCart,
}: SearchStructureCardProps) {
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const structure = offers[0];
  if (!structure) return null;

  const insuranceNames = [...new Set(offers.flatMap((offer) => offer.insurance_names || []))];
  const toggleOffer = async (offer: SearchResult, selected: boolean) => {
    if (pendingId !== null) return;
    setPendingId(offer.id);
    setError('');
    try {
      if (selected) await onRemoveFromCart(offer.id);
      else await onAddToCart(offer);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de mettre à jour le panier.');
    } finally {
      setPendingId(null);
    }
  };

  const regimePrice = (offer: SearchResult) => regime === 'ipm'
    ? offer.price_ipm
    : regime === 'assurance'
      ? offer.price_assurance
      : offer.price;

  return (
    <article
      className={`scard-m fade-in-m${structure.verified ? '' : ' scard-m--unverified scard--unverified opacity-60'}`}
      id={`sm-${structure.slug || structure.id}`}
      data-org-id={structure.slug}
      style={{ animationDelay: `${index * 35}ms` }}
    >
      <div className="scard-m-head">
        <div className="scard-m-head-row flex items-center justify-between gap-2">
          <div className="scard-m-name flex items-center gap-2 flex-wrap">
            <a className="scard-org-name font-bold hover:underline" href={structure.profile_url || `/sante/${structure.slug}/`}>
              {structure.nom}
            </a>
            <span className={`scard-badge ${structure.verified ? 'scard-badge--green' : 'scard-badge--warn'}`}>
              <i className={`ti ${structure.verified ? 'ti-circle-check' : 'ti-clock'}`} aria-hidden="true" />
              {structure.verified ? 'Vérifié' : 'En cours de validation'}
            </span>
          </div>
        </div>
        {structure.type && <div className="scard-m-type">{structure.type}</div>}
        <div className="scard-m-meta flex items-center gap-3 mt-1">
          <span className="smeta-m"><i className="ti ti-map-pin" aria-hidden="true" /> {structure.ville || 'Dakar'}{structure.quartier ? `, ${structure.quartier}` : ''}</span>
          <span className="smeta-m"><i className="ti ti-clock" aria-hidden="true" /> {structure.horaires || '24h/24'}</span>
          {structure.distance_km !== undefined && structure.distance_km !== null && (
            <span className="smeta-m"><i className="ti ti-navigation" aria-hidden="true" /> {structure.distance_km.toFixed(1)} km</span>
          )}
        </div>
      </div>

      {offers.map((offer) => {
        const selected = cartOfferIds.has(offer.id);
        const acteInCartElsewhere = !selected
          && offer.acte_id !== undefined
          && cartActeIds.has(offer.acte_id);
        const price = regimePrice(offer);
        const shownPrice = price ?? offer.price;
        const coverageNeedsConfirmation = (hasSelectedInsurance && offer.insurance_match === false)
          || (regime !== 'comptant' && !price);
        return (
          <label
            className="scard-m-acte"
            key={offer.id}
            data-pa-id={offer.id}
            data-pa-acte-pk={offer.acte_id}
            data-pa-acte={offer.acte}
            data-pa-org={offer.nom}
            data-pa-price={offer.price}
            data-pa-ins-match={offer.insurance_match ? '1' : '0'}
          >
            <input
              type="checkbox"
              className="scard-m-checkbox"
              aria-label={acteInCartElsewhere
                ? `${offer.acte || 'Cet acte'} déjà au panier pour une autre structure`
                : `${selected ? 'Retirer' : 'Ajouter'} ${offer.acte || 'cet acte'} ${selected ? 'du' : 'au'} panier`}
              checked={selected}
              disabled={!structure.verified || pendingId !== null || acteInCartElsewhere}
              title={acteInCartElsewhere ? 'Retirez cet acte de l’autre structure avant de le choisir ici.' : undefined}
              onChange={() => void toggleOffer(offer, selected)}
            />
            <div className="scard-m-acte-info min-w-0 flex-1">
              <div className="scard-m-acte-nom font-semibold">{offer.acte || 'Acte médical'}</div>
              <div className="scard-m-acte-meta flex items-center gap-2 mt-0.5 flex-wrap">
                {offer.delai && <span className="scard-m-acte-delai"><i className="ti ti-clock" aria-hidden="true" /> {offer.delai}</span>}
                {coverageNeedsConfirmation && <span className="scard-ins-warn">À confirmer avec votre mutuelle</span>}
                {acteInCartElsewhere && <span className="scard-ins-warn">Déjà au panier pour une autre structure</span>}
              </div>
            </div>
            <div className="scard-m-pricing text-right">
              <div className="scard-m-acte-prix" data-base-price={offer.price}>
                {formatPrice(shownPrice)} F
              </div>
              {regime !== 'comptant' && price && (
                <div className="ai-regime-badge">{regime === 'ipm' ? 'IPM' : 'Assurance'}</div>
              )}
            </div>
          </label>
        );
      })}

      <div className="scard-m-footer flex items-center justify-between gap-2 p-3">
        <div className="scard-m-ins text-xs text-gray-500 flex items-center gap-1.5 flex-1 min-w-0">
          <i className="ti ti-shield-check" aria-hidden="true" />
          <span className="truncate">{insuranceNames.length ? insuranceNames.slice(0, 3).join(', ') : 'Couverture à confirmer'}</span>
        </div>
        <a className="scard-m-profile-btn" href={structure.profile_url || `/sante/${structure.slug}/`}>
          Profil →
        </a>
        {error && <span className="text-xs text-red-700" role="alert">{error}</span>}
      </div>

      {offers.length > 1 && (
        <div className="scard-m-multiselect-footer flex items-center justify-between gap-2 px-3.5 py-2 bg-slate-50 border-t border-slate-200">
          <span className="text-xs font-semibold text-slate-500">{offers.length} actes</span>
          <span className="font-black text-primary-700 text-sm">
            {formatPrice(offers.reduce((sum, offer) => sum + Number(offer.price || 0), 0))} F
          </span>
          <button
            type="button"
            className="btn-select-all-m bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg px-3 py-1.5 text-xs font-bold shadow-sm transition active:scale-95 cursor-pointer shrink-0"
            disabled={!structure.verified || pendingId !== null}
            onClick={async () => {
              for (const offer of offers) {
                if (!cartOfferIds.has(offer.id)) await toggleOffer(offer, false);
              }
            }}
          >
            <i className="ti ti-plus" aria-hidden="true" /> Tout
          </button>
        </div>
      )}
    </article>
  );
}
