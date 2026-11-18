import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatApiError } from '../lib/api';

type HomeData = {
  stats: {
    providers: number;
    services: number;
    assurances: number;
    acts: number;
  };
  pillars: {
    id: number;
    name: string;
    slug: string;
    act_count: number;
    sample_acts: string;
  }[];
  trending_actes: {
    id: number;
    name: string;
    struct_count: number;
    min_price: string | null;
    category: string;
    subfamily: string;
    location: string;
  }[];
};

const TRUST_ITEMS = [
  {
    icon: 'ti-users',
    title: 'Données déclarées',
    description: 'Les informations sont renseignées directement par les établissements, en toute autonomie et responsabilité.',
  },
  {
    icon: 'ti-refresh',
    title: 'Date de mise à jour',
    description: 'Les fiches affichent clairement la dernière date de mise à jour. Les structures modifient leurs infos à tout moment.',
  },
  {
    icon: 'ti-rosette',
    title: 'Badge Vérifié',
    description: "Les établissements validés par l'équipe MedCare obtiennent le badge de confiance visible sur toutes leurs fiches.",
  },
  {
    icon: 'ti-credit-card',
    title: 'Tarifs et Prise en charge',
    description: "Chaque établissement renseigne ses tarifs, les types d'assurances acceptées pour une transparence totale avant votre visite.",
  },
];

const PROCESS_STEPS = [
  { icon: 'ti-search', title: 'Rechercher', description: 'Examen ou service' },
  { icon: 'ti-scale', title: 'Comparer', description: 'Prix · Distance · Assurance' },
  { icon: 'ti-id', title: 'Consulter la fiche', description: 'Infos vérifiées' },
  { icon: 'ti-brand-whatsapp', title: 'Contacter', description: 'WhatsApp direct' },
];

function formatNumber(value: number | string) {
  return new Intl.NumberFormat('fr-FR').format(Number(value));
}

function pillarIcon(name: string) {
  const service = name.toLocaleLowerCase('fr');
  if (service.includes('biologie')) return 'ti-flask';
  if (service.includes('imagerie')) return 'ti-scan';
  if (service.includes('explorations') || service.includes('cardiologie')) return 'ti-heartbeat';
  if (service.includes('ambulance')) return 'ti-ambulance';
  if (service.includes('dentaire') || service.includes('dent')) return 'ti-dental';
  if (service.includes('spécialisés') || service.includes('infirmiers')) return 'ti-needle';
  return 'ti-activity';
}

export function LandingPage() {
  const [data, setData] = useState<HomeData | null>(null);
  const [loadError, setLoadError] = useState('');
  const [showTopButton, setShowTopButton] = useState(false);
  const [flipped, setFlipped] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/public/home/', { headers: { Accept: 'application/json' }, signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Le chargement de l'accueil a échoué (${response.status}).`);
        return (await response.json()) as HomeData;
      })
      .then(setData)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setLoadError(formatApiError(error, 'Impossible de charger les données de l’accueil.'));
      });

    const onScroll = () => setShowTopButton(window.scrollY > 400);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      controller.abort();
      window.removeEventListener('scroll', onScroll);
    };
  }, [retryCount]);

  return (
    <div className="mc-page-wrap mc-landing-page">
      {loadError && (
        <div className="mx-auto max-w-7xl px-4 pt-4" role="alert">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <span>{loadError}</span>
            <button
              type="button"
              onClick={() => setRetryCount((count) => count + 1)}
              className="rounded-lg bg-red-700 px-3 py-2 font-semibold text-white transition-colors hover:bg-red-800"
            >
              Réessayer
            </button>
          </div>
        </div>
      )}

      <section className="mc-hero">
        <div className="mc-container">
          <div className="mc-hero-tag">Première plateforme paraclinique digitale du Sénégal</div>
          <h1>Votre santé,<br /><em>au bout des doigts.</em></h1>
          <p className="mc-hero-sub">Identifiez-vous pour commencer</p>
          <div className="mc-hero-ctas">
            <div className="cta-card">
              <div className="cta-icon"><i className="ti ti-user-heart" /></div>
              <div className="cta-label">Trouvez l'examen médical dont vous avez besoin.</div>
              <Link to="/sante/recherche/" className="cta-btn">
                <span className="cta-btn-label-full">Je suis patient</span>
                <span className="cta-btn-label-short">Patient</span>
                <span className="cta-btn-arrow"> →</span>
              </Link>
            </div>
            <div className="cta-card pro">
              <div className="cta-icon"><i className="ti ti-stethoscope" /></div>
              <div className="cta-label">Référencez votre structure ou votre pratique.</div>
              <Link to="/inscription/" className="cta-btn">
                <span className="cta-btn-label-full">Je suis soignant</span>
                <span className="cta-btn-label-short">Soignant</span>
                <span className="cta-btn-arrow"> →</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mc-process" aria-label="Parcours">
        <div className="mc-process-inner">
          {PROCESS_STEPS.map((step, index) => (
            <div className={`mc-process-step${index === PROCESS_STEPS.length - 1 ? ' mc-process-step--last' : ''}`} key={step.title}>
              <div className={`mc-process-icon${index === PROCESS_STEPS.length - 1 ? ' mc-process-icon--wa' : ''}`}><i className={`ti ${step.icon}`} /></div>
              <div className="mc-process-text">
                <div className="mc-process-title">{step.title}</div>
                <div className="mc-process-desc">{step.description}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="mc-stats">
        <div className="mc-container">
          <div className="mc-stats-inner">
            <div className="mc-stat"><i className="ti ti-building-hospital mc-stat-icon" /><div><div className="mc-stat-val">{data ? formatNumber(data.stats.providers) : '—'}</div><div className="mc-stat-label">Structures</div></div></div>
            <div className="mc-stat"><i className="ti ti-flask mc-stat-icon" /><div><div className="mc-stat-val">{data ? `${formatNumber(data.stats.acts)}+` : '—'}</div><div className="mc-stat-label">Actes</div></div></div>
            <div className="mc-stat"><i className="ti ti-shield mc-stat-icon" /><div><div className="mc-stat-val">{data ? formatNumber(data.stats.assurances) : '—'}</div><div className="mc-stat-label">Assurances</div></div></div>
            <div className="mc-stat"><i className="ti ti-percentage mc-stat-icon" /><div><div className="mc-stat-val">0%</div><div className="mc-stat-label">Commission</div></div></div>
          </div>
        </div>
      </div>

      <section className="mc-section mc-section-acces">
        <div className="mc-container">
          <div className="mc-acces-grid">
            <div className="mc-acces-text">
              <div className="mc-section-tag mc-section-tag--on-dark">ACCÈS IMMÉDIAT</div>
              <h2>Prix <em>réels</em>,<br />Localisations <em>exactes</em>,<br />Assurances <em>acceptées</em>.</h2>
              <p className="mc-section-sub mc-section-sub--nowrap">Tout ce qu'il faut savoir avant de se déplacer.</p>
            </div>
            <div className="mc-acces-visual" aria-hidden="true">
              <img src="/static/images/perspective-medcare.jpg" alt="" className="mc-acces-visual-img" loading="lazy" decoding="async" />
            </div>
          </div>
        </div>
      </section>

      <section className="mc-section" style={{ background: '#ffffff' }}>
        <div className="mc-container">
          <div className="mc-section-tag">Catégories</div>
          <div className="mc-piliers-head">
            <div>
              <h2>Les 6 piliers <em>MedCare</em></h2>
              <p className="mc-section-sub">Chaque service est structuré, standardisé et accessible en quelques secondes.</p>
            </div>
            <Link to="/sante/recherche/" className="mc-pilier-link">Voir tous les services <i className="ti ti-arrow-right" /></Link>
          </div>
          <div className="mc2-piliers-grid">
            {(data?.pillars ?? []).map((pillar) => (
              <Link to={`/sante/recherche/?service=${pillar.id}`} className="mc2-pilier-card" key={pillar.id}>
                <div className="mc2-pilier-icon"><i className={`ti ${pillarIcon(pillar.name)}`} /></div>
                <div className="mc2-pilier-name">{pillar.name}</div>
                <div className="mc2-pilier-sub">{pillar.sample_acts}</div>
                <div className="mc2-pilier-link"><i className="ti ti-arrow-right" style={{ fontSize: 12 }} />Explorer nos {pillar.act_count} actes</div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="mc-trust" id="mc-trust-section">
        <div className="mc-container">
          <div className="mc-trust-intro">
            <div className="mc-section-tag">Fiabilité</div>
            <p className="mc-trust-heading">Des données <em>dont vous pouvez</em> avoir confiance.</p>
          </div>
          <div className="mc-trust-grid" id="mc-trust-tilt-grid">
            {TRUST_ITEMS.map((item) => (
              <article className="mc-trust-card mc-trust-tilt" key={item.title}>
                <div className="mc-trust-card-icon"><i className={`ti ${item.icon}`} /></div>
                <div className="mc-trust-card-title">{item.title}</div>
                <div className="mc-trust-card-desc">{item.description}</div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {!!data?.trending_actes.length && (
        <section className="mc-section">
          <div className="mc-container">
            <div className="mc-section-tag">Tendances</div>
            <div className="mc-trending-head">
              <div><h2>Services les plus <em>recherchés</em></h2></div>
              <Link to="/sante/recherche/" className="mc-pilier-link">Voir tous les services <i className="ti ti-arrow-right" /></Link>
            </div>
            <div className="mc-trending">
              {data.trending_actes.map((row) => (
                <article className="mc-trend-card" key={row.id}>
                  <div className="mc-trend-top"><span className="mc-trend-name">{row.name}</span></div>
                  <div className="mc-trend-meta">
                    {row.location && <span className="mc-trend-tag">{row.location}</span>}
                    <span className="mc-trend-tag">{row.category}</span>
                    <span className="mc-trend-tag">{row.subfamily ? `${row.subfamily} · ` : ''}{row.struct_count} structure{row.struct_count > 1 ? 's' : ''}</span>
                  </div>
                  {row.min_price !== null && Number(row.min_price) > 0 && <div className="mc-trend-price">{formatNumber(row.min_price)} <span>FCFA</span></div>}
                  <div className="mc-trend-actions"><Link to={`/sante/recherche/?acte=${row.id}&sort=price_asc`} className="btn-see">Voir résultats →</Link></div>
                </article>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="mc-pro">
        <div className="mc-container">
          <div className="mc-pro-inner">
            <div className="mc-pro-text">
              <div className="mc-section-tag">Pour les professionnels</div>
              <h2>Référencez votre structure,<br />gagnez en visibilité.</h2>
              <p>Inscrivez vos services, vos tarifs, vos assurances et votre localisation. Permettez aux patients de vous trouver en un clic.</p>
              <div className="mc-pro-features">
                <div className="mc-pro-feature"><i className="ti ti-check" /> Inscription gratuite et rapide</div>
                <div className="mc-pro-feature"><i className="ti ti-check" /> 0% de commission sur vos actes</div>
                <div className="mc-pro-feature"><i className="ti ti-check" /> Gestion autonome de votre catalogue</div>
                <div className="mc-pro-feature"><i className="ti ti-check" /> Badge de confiance MedCare</div>
              </div>
              <Link to="/inscription/" className="btn-pro-cta">Rejoindre MedCare →</Link>
            </div>
            <div className="mc-pro-visual">
              <button
                type="button"
                className={`mc-flip-card${flipped ? ' flipped' : ''}`}
                aria-label={flipped ? 'Revenir aux principes précédents' : 'Voir la suite des principes MedCare'}
                aria-pressed={flipped}
                onClick={() => setFlipped((value) => !value)}
              >
                <div className="mc-flip-inner">
                  <div className="mc-flip-front" aria-hidden={flipped}>
                    <div className="mc-face-label"><div className="mc-face-label-dot" /><span>Nos Principes · 1/2</span></div>
                    <div className="mc-principes-list">
                      <div className="mc-principe-item"><div className="mc-principe-icon"><i className="ti ti-lock-open" /></div><div><div className="mc-principe-title">Transparence</div><div className="mc-principe-sub">Prix affichés, infos vérifiables</div></div></div>
                      <div className="mc-principe-item"><div className="mc-principe-icon"><i className="ti ti-ruler-2" /></div><div><div className="mc-principe-title">Standardisation</div><div className="mc-principe-sub">Fiches homogènes et comparables</div></div></div>
                    </div>
                    <div className="mc-flip-hint"><span>Voir la suite</span><div className="mc-flip-hint-icon">↻</div></div>
                  </div>
                  <div className="mc-flip-back" aria-hidden={!flipped}>
                    <div className="mc-face-label"><div className="mc-face-label-dot" /><span>Nos Principes · 2/2</span></div>
                    <div className="mc-principes-list">
                      <div className="mc-principe-item"><div className="mc-principe-icon"><i className="ti ti-world" /></div><div><div className="mc-principe-title">Accessibilité équitable</div><div className="mc-principe-sub">Pour tout patient, partout</div></div></div>
                      <div className="mc-principe-item"><div className="mc-principe-icon"><i className="ti ti-chart-bar" /></div><div><div className="mc-principe-title">Donnée structurée</div><div className="mc-principe-sub">Information fiable et exploitable</div></div></div>
                    </div>
                    <div className="mc-flip-hint"><span>Retour</span><div className="mc-flip-hint-icon">↺</div></div>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="mc-vision">
        <div className="mc-container">
          <div className="mc-vision-layout">
            <div className="mc-vision-text">
              <div className="mc-section-tag mc-section-tag--on-dark">Notre vision</div>
              <h2>Construire l'infrastructure paraclinique digitale de <em>référence en Afrique.</em></h2>
              <p>MedCare ambitionne de devenir la couche digitale qui organise, cartographie et structure l'offre de services médicaux à travers l'Afrique en commençant par le Sénégal.</p>
              <div className="mc-phases">
                <div className="mc-phase active"><div className="mc-phase-label">Phase 1</div><div className="mc-phase-title">Dakar</div></div>
                <div className="mc-phase"><div className="mc-phase-label">Phase 2</div><div className="mc-phase-title">Sénégal</div></div>
                <div className="mc-phase"><div className="mc-phase-label">Phase 3</div><div className="mc-phase-title">Afrique</div></div>
              </div>
            </div>
            <div className="mc-vision-card">
              <div className="mc-vision-kpi"><div className="mc-vision-kpi-val">{data ? `${formatNumber(data.stats.acts)}+` : '—'}</div><div className="mc-vision-kpi-label">Actes référencés</div></div>
              <div className="mc-vision-principle"><i className="ti ti-lock-open" /><span>Transparence des prix</span></div>
              <div className="mc-vision-principle"><i className="ti ti-ruler" /><span>Standardisation des fiches</span></div>
              <div className="mc-vision-principle"><i className="ti ti-users" /><span>Accessibilité équitable</span></div>
              <div className="mc-vision-principle"><i className="ti ti-database" /><span>Donnée structurée</span></div>
              <div className="mc-vision-cta"><a href="/confiance/" className="btn-pro-cta">Découvrir notre charte de confiance →</a></div>
            </div>
          </div>
        </div>
      </section>

      <button
        type="button"
        className={`mc-fab mc-fab-top${showTopButton ? ' is-visible' : ''}`}
        aria-label="Retour en haut de page"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      >
        <i className="ti ti-arrow-up" />
      </button>
    </div>
  );
}
