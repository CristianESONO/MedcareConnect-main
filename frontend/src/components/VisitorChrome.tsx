import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

type VisitorStylesProps = {
  registerPage: boolean;
  landingPage: boolean;
};

const BASE_STYLES: [string, string][] = [
  ['/static/css/visitor_chrome.css?v=41', 'visitor-chrome'],
  ['/static/css/visitor_charte.css?v=20', 'visitor-charte'],
];
const CURRENT_YEAR = new Date().getFullYear();

export function VisitorStyles({ registerPage, landingPage }: VisitorStylesProps) {
  useEffect(() => {
    const styles: [string, string][] = [...BASE_STYLES];
    if (registerPage) styles.push(['/static/css/rejoindre_marketing.css?v=1', 'visitor-register']);
    if (landingPage) styles.push(['/static/css/landing.css?v=34', 'visitor-landing']);
    const links = styles.map(([href, id]) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.dataset.visitorStyle = id;
      document.head.appendChild(link);
      return link;
    });

    document.body.classList.add('mc-visitor-body', 'mc-vitrine-page');
    return () => {
      document.body.classList.remove('mc-visitor-body', 'mc-vitrine-page', 'mc-visitor-drawer-open');
      links.forEach((link) => link.remove());
    };
  }, [landingPage, registerPage]);

  return null;
}

export function VisitorHeader() {
  const location = useLocation();
  const [aboutOpen, setAboutOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isLoginPage = location.pathname === '/connexion/';

  useEffect(() => {
    document.body.classList.toggle('mc-visitor-drawer-open', drawerOpen);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawerOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.classList.remove('mc-visitor-drawer-open');
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [drawerOpen]);

  return (
    <>
      <header className="mc-landing-header" id="header_pop">
        <div className="mc-container mc-landing-header-bar">
          <Link
            to="/"
            className={`mc-landing-header-logo${isLoginPage ? ' mc-landing-header-logo--login' : ''}`}
            aria-label="MedCare — Accueil"
          >
            <img className="mc-brand-logo" src="/static/images/logo_MEDCARE.png" alt="MedCare Connect" />
          </Link>
          <div className="mc-landing-header-actions">
            <nav className="mc-landing-nav" aria-label="Navigation principale">
              <ul className="mc-landing-nav-list">
                <li><Link to="/" className="mc-landing-nav-link is-active">Accueil</Link></li>
                <li><a href="/sante/annuaire/" className="mc-landing-nav-link">Annuaire</a></li>
                <li className={`mc-landing-nav-dropdown${aboutOpen ? ' is-open' : ''}`}>
                  <button
                    type="button"
                    className="mc-landing-nav-link mc-landing-nav-dropdown-trigger"
                    aria-expanded={aboutOpen}
                    aria-haspopup="true"
                    onClick={() => setAboutOpen((open) => !open)}
                  >
                    À propos <i className="ti ti-chevron-down mc-landing-nav-chevron" aria-hidden="true" />
                  </button>
                  <ul className="mc-landing-nav-dropdown-menu">
                    <li><a href="/about" className="mc-landing-nav-link mc-landing-nav-dropdown-link">Qui sommes-nous ?</a></li>
                    <li><a href="/how-it-works" className="mc-landing-nav-link mc-landing-nav-dropdown-link">Comment ça marche</a></li>
                    <li><a href="/contact" className="mc-landing-nav-link mc-landing-nav-dropdown-link">Contact</a></li>
                  </ul>
                </li>
              </ul>
            </nav>
            <div className="mc-landing-header-ctas">
              <a href="/connexion/" className="mc-landing-btn mc-landing-btn-login">Connexion</a>
              <a href="/sante/recherche/" className="mc-landing-btn mc-landing-btn-search">Trouver un service</a>
              <a href="/inscription/" className="mc-landing-btn mc-landing-btn-join">Rejoindre MedCare</a>
            </div>
          </div>
          <button
            type="button"
            className="mc-landing-burger"
            aria-label={drawerOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
            aria-expanded={drawerOpen}
            aria-controls="mcLandingDrawer"
            onClick={() => setDrawerOpen((open) => !open)}
          >
            <svg className="mc-landing-burger-open" viewBox="0 0 1000 1000" aria-hidden="true">
              <path d="M104 333H896C929 333 958 304 958 271S929 208 896 208H104C71 208 42 237 42 271S71 333 104 333ZM104 583H896C929 583 958 554 958 521S929 458 896 458H104C71 458 42 487 42 521S71 583 104 583ZM104 833H896C929 833 958 804 958 771S929 708 896 708H104C71 708 42 737 42 771S71 833 104 833Z" />
            </svg>
          </button>
        </div>
      </header>

      <div
        className={`mc-landing-drawer-backdrop${drawerOpen ? ' is-visible' : ''}`}
        hidden={!drawerOpen}
        aria-hidden="true"
        onClick={() => setDrawerOpen(false)}
      />
      <aside
        className={`mc-landing-drawer${drawerOpen ? ' is-open' : ''}`}
        id="mcLandingDrawer"
        aria-hidden={!drawerOpen}
        aria-label="Menu navigation mobile"
      >
        <div className="mc-landing-drawer-header">
          <div className="mc-drawer-header-top">
            <Link to="/" className="mc-landing-drawer-logo" onClick={() => setDrawerOpen(false)}>
              <img className="mc-brand-logo" src="/static/images/logo_MEDCARE.png" alt="MedCare Connect" />
            </Link>
            <button type="button" className="mc-landing-drawer-close" aria-label="Fermer le menu" onClick={() => setDrawerOpen(false)}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
            </button>
          </div>
          <div className="mc-drawer-tagline-box">
            <span className="mc-drawer-status-pill"><span className="mc-status-dot" />Plateforme Officielle</span>
            <p className="mc-landing-drawer-tagline">L'infrastructure paraclinique digitale du Sénégal.</p>
          </div>
        </div>
        <nav className="mc-landing-drawer-nav" aria-label="Menu mobile">
          <ul>
            <li><Link to="/" className="mc-landing-drawer-link is-active" onClick={() => setDrawerOpen(false)}><i className="ti ti-home mc-landing-drawer-icon" />Accueil</Link></li>
            <li><a href="/sante/annuaire/" className="mc-landing-drawer-link"><i className="ti ti-building-hospital mc-landing-drawer-icon" />Annuaire des centres</a></li>
            <li className="mc-landing-drawer-group">
              <span className="mc-landing-drawer-group-label"><i className="ti ti-info-circle mc-landing-drawer-icon" />En savoir plus</span>
              <ul className="mc-landing-drawer-sublist">
                <li><a href="/about" className="mc-landing-drawer-link"><i className="ti ti-user-search mc-landing-drawer-icon" />Qui sommes-nous ?</a></li>
                <li><a href="/how-it-works" className="mc-landing-drawer-link"><i className="ti ti-help-circle mc-landing-drawer-icon" />Comment ça marche</a></li>
                <li><a href="/confiance/" className="mc-landing-drawer-link"><i className="ti ti-shield-check mc-landing-drawer-icon" />Charte de confiance</a></li>
                <li><a href="/contact" className="mc-landing-drawer-link"><i className="ti ti-mail mc-landing-drawer-icon" />Contact</a></li>
              </ul>
            </li>
          </ul>
        </nav>
        <div className="mc-landing-drawer-cta">
          <a href="/connexion/" className="mc-landing-drawer-btn mc-landing-drawer-btn-login"><i className="ti ti-login" />Connexion</a>
          <a href="/inscription/" className="mc-landing-drawer-btn mc-landing-drawer-btn-join"><i className="ti ti-user-plus" />Rejoindre MedCare</a>
        </div>
      </aside>
    </>
  );
}

export function VisitorFooter() {
  return (
    <footer className="mc-landing-footer" id="mc-landing-footer">
      <div className="mc-footer-glow" aria-hidden="true" />
      <div className="mc-container mc-footer-inner">
        <div className="mc-footer-grid">
          <div className="mc-footer-col mc-footer-col--newsletter">
            <div className="mc-footer-brand-col">
              <a href="/" className="mc-footer-logo-link" aria-label="MedCare">
                <img src="/static/images/logo.png" alt="MedCare Connect" className="mc-brand-logo" width="176" height="40" />
              </a>
              <p className="mc-footer-tagline">L'infrastructure paraclinique digitale du Sénégal.</p>
            </div>
            <div className="mc-footer-newsletter-block">
              <h5 className="mc-footer-newsletter-title">Newsletter</h5>
              <form className="mc-footer-newsletter" onSubmit={(event) => event.preventDefault()}>
                <label className="mc-footer-sr-only" htmlFor="mc-footer-prenom">Prénom</label>
                <input type="text" id="mc-footer-prenom" className="mc-footer-input" placeholder="Prénom *" required autoComplete="given-name" />
                <label className="mc-footer-sr-only" htmlFor="mc-footer-email">Adresse de messagerie</label>
                <input type="email" id="mc-footer-email" className="mc-footer-input" placeholder="Adresse e-mail *" required autoComplete="email" />
                <button type="submit" className="mc-footer-submit">S'abonner</button>
              </form>
            </div>
          </div>
          <div className="mc-footer-col">
            <h5 className="mc-footer-title">Services</h5>
            <ul className="mc-footer-links">
              <li><a href="/sante/recherche/">Biologie médicale</a></li>
              <li><a href="/sante/recherche/">Imagerie médicale</a></li>
              <li><a href="/sante/recherche/">Explorations fonctionnelles</a></li>
              <li><a href="/sante/recherche/">Ambulance médicalisée</a></li>
              <li><a href="/sante/recherche/">Soins dentaires</a></li>
              <li><a href="/sante/recherche/">Soins spécialisés</a></li>
            </ul>
          </div>
          <div className="mc-footer-col">
            <h5 className="mc-footer-title">Navigation</h5>
            <ul className="mc-footer-links">
              <li><a href="/sante/recherche/">Trouver un service</a></li>
              <li><a href="/inscription/">Rejoindre MedCare</a></li>
              <li><a href="/how-it-works">Comment ça marche</a></li>
              <li><a href="/about">À propos</a></li>
              <li><a href="/confiance/">Politique de confidentialité</a></li>
            </ul>
          </div>
          <div className="mc-footer-col">
            <div className="mc-footer-contact-info">
              <h5 className="mc-footer-title">Contactez-nous</h5>
              <ul className="mc-footer-contact">
                <li><span className="mc-footer-contact-icon"><i className="ti ti-map-pin" /></span><span>Point E-Dakar Sénégal, 4890</span></li>
                <li><span className="mc-footer-contact-icon"><i className="ti ti-mail" /></span><a href="mailto:contact@medcare.sn">contact@medcare.sn</a></li>
                <li><span className="mc-footer-contact-icon"><i className="ti ti-phone" /></span><a href="tel:+221781673189">+221 78 167 31 89</a></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      <div className="mc-footer-bottom-bar">
        <div className="mc-container mc-footer-inner">
          <div className="mc-footer-bottom">
            <p className="mc-footer-copy">©{CURRENT_YEAR} MedCare.sn – Tous droits réservés</p>
            <nav className="mc-footer-legal" aria-label="Liens légaux">
              <a href="/confiance/">Confidentialité</a>
              <a href="/confiance/">Conditions générales</a>
              <a href="/confiance/">Mentions légales</a>
            </nav>
          </div>
        </div>
      </div>
    </footer>
  );
}
