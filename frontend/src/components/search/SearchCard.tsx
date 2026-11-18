import { useState } from 'react';
import { motion } from 'framer-motion';
import { type SearchResult } from '../../lib/api';

interface SearchCardProps {
  result: SearchResult;
  index?: number;
  regime: string;
  hasSelectedInsurance: boolean;
  inCart?: boolean;
  acteInCartElsewhere?: boolean;
  onAddCart?: (result: SearchResult) => void | Promise<void>;
  onRemoveCart?: (id: number) => void | Promise<void>;
}

function formatPrice(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '';
  return Number(value).toLocaleString('fr-FR');
}

export function SearchCard({
  result,
  index = 0,
  regime,
  hasSelectedInsurance,
  inCart = false,
  acteInCartElsewhere = false,
  onAddCart,
  onRemoveCart,
}: SearchCardProps) {
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const regimePrice = regime === 'ipm'
    ? result.price_ipm
    : regime === 'assurance'
      ? result.price_assurance
      : result.price;
  const selectedPrice = regimePrice ?? result.price;
  const coverageNeedsConfirmation = (hasSelectedInsurance && result.insurance_match === false)
    || (regime !== 'comptant' && !regimePrice);

  const addToCart = async () => {
    if (!onAddCart || adding) return;
    setAdding(true);
    setError('');
    try {
      if (inCart) await onRemoveCart?.(result.id);
      else await onAddCart?.(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ajouter cet acte au panier.');
    } finally {
      setAdding(false);
    }
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.035, duration: 0.25 }}
      className={`scard${inCart ? ' scard--in-cart' : ''}${result.verified ? '' : ' scard--unverified'}`}
      data-pa-id={result.id}
      data-pa-unverified={result.verified ? '0' : '1'}
      data-pa-price={result.price}
      data-pa-ins-match={result.insurance_match ? '1' : '0'}
    >
      <div className="scard-header">
        <div className="scard-org">
          {result.logo ? (
            <img className="scard-org-logo" src={result.logo} alt="" />
          ) : (
            <div className="scard-org-logo scard-org-logo--fallback" aria-hidden="true">
              {result.nom.charAt(0)}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <a className="scard-org-name" href={result.profile_url || `/sante/${result.slug}/`}>
                {result.nom}
              </a>
              <span className={`scard-badge ${result.verified ? 'scard-badge--green' : 'scard-badge--warn'}`}>
                <i className={`ti ${result.verified ? 'ti-circle-check' : 'ti-clock'}`} />
                {result.verified ? 'Vérifié' : 'En cours de validation'}
              </span>
            </div>
            <div className="scard-type">{result.type}</div>
            <div className="scard-meta">
              <span><i className="ti ti-map-pin" /> {result.ville}{result.quartier ? `, ${result.quartier}` : ''}</span>
              {result.horaires && <span><i className="ti ti-clock" /> {result.horaires}</span>}
              {result.distance_km !== undefined && result.distance_km !== null && (
                <span className="scard-distance"><i className="ti ti-navigation" /> {result.distance_km.toFixed(1)} km</span>
              )}
            </div>
          </div>
        </div>
        <div className="scard-price-block">
          <span className="scard-price">{formatPrice(selectedPrice)} FCFA</span>
          <span className="scard-price-unit">
            {regime === 'comptant' || !regimePrice
              ? 'Tarif affiché'
              : regime === 'ipm' ? 'Tarif IPM' : 'Tarif assurance'}
          </span>
        </div>
      </div>

      <div className="scard-actes">
        <div>
          <h3 className="scard-acte-name">{result.acte}</h3>
          {(result.categorie || result.catalog_count) && (
            <p className="scard-acte-meta">
              {[result.categorie, result.catalog_count
                ? `${result.catalog_count} acte${result.catalog_count === 1 ? '' : 's'} au catalogue`
                : '']
                .filter(Boolean)
                .join(' · ')}
            </p>
          )}
        </div>
        <div className="scard-chips">
          {result.delai && <span className="scard-chip"><i className="ti ti-clock" /> Délai : {result.delai}</span>}
          {result.insurance_names?.slice(0, 3).map((name) => (
            <span className="scard-chip" key={name}><i className="ti ti-shield-check" /> {name}</span>
          ))}
          {!!result.insurance_names && result.insurance_names.length > 3 && (
            <span className="scard-chip">+{result.insurance_names.length - 3} autres</span>
          )}
          {result.home_collection && <span className="scard-chip"><i className="ti ti-home" /> À domicile</span>}
          {result.ambulance && <span className="scard-chip"><i className="ti ti-ambulance" /> Ambulance</span>}
        </div>
      </div>

      <div className="scard-footer">
        <div className="scard-footer-left">
          {coverageNeedsConfirmation && (
            <span className="scard-ins-warn">
              {regime === 'comptant' ? 'Prise en charge à confirmer' : 'Tarif couvert à confirmer avec votre organisme'}
            </span>
          )}
          {acteInCartElsewhere && (
            <span className="scard-ins-warn" role="status">
              Déjà dans le panier pour une autre structure
            </span>
          )}
          {error && <span className="text-xs text-red-700" role="alert">{error}</span>}
        </div>
        <div className="scard-footer-actions">
          <a className="scard-btn-secondary" href={result.profile_url || `/sante/${result.slug}/`}>
            Voir profil
          </a>
          {result.verified && result.ambulance && (
            <a className="scard-btn-primary" href={result.profile_url || `/sante/${result.slug}/`}>
              <i className="ti ti-ambulance" /> Configurer le trajet
            </a>
          )}
          {result.verified && !result.ambulance && (onAddCart || (inCart && onRemoveCart)) && (
            <button
              type="button"
              className={inCart ? 'scard-btn-secondary' : 'scard-btn-primary'}
              onClick={addToCart}
              disabled={adding || acteInCartElsewhere}
              title={acteInCartElsewhere ? 'Retirez cet acte de l’autre structure avant de le choisir ici.' : undefined}
            >
              <i className={`ti ${adding ? 'ti-loader-2 animate-spin' : inCart ? 'ti-trash' : 'ti-shopping-cart'}`} />
              {adding ? 'Mise à jour…' : inCart ? 'Retirer du panier' : acteInCartElsewhere ? 'Déjà au panier' : 'Ajouter au panier'}
            </button>
          )}
        </div>
      </div>
    </motion.article>
  );
}
