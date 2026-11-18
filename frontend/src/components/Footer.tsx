import { Link } from 'react-router-dom';

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mc-landing-footer relative overflow-hidden bg-gradient-to-b from-[#0f3052] via-[#123a63] to-[#15406d] text-white pt-12 font-sans">
      {/* Footer Glow */}
      <div
        className="pointer-events-none absolute -top-30 -right-20 w-96 h-96 bg-[radial-gradient(circle,rgba(79,163,199,0.18)_0%,transparent_68%)]"
        aria-hidden="true"
      ></div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8 pb-10">
          {/* ── Col 1: Brand & Newsletter ── */}
          <div className="lg:col-span-4 flex flex-col items-center sm:items-start text-center sm:text-left">
            <Link to="/" className="inline-block mb-3">
              <img
                src="/static/images/logo_MEDCARE.png"
                alt="MedCare"
                className="h-10 w-auto brightness-0 invert opacity-95"
              />
            </Link>
            <p className="text-sm font-bold text-white mb-6 max-w-xs">
              L'infrastructure paraclinique digitale du Sénégal.
            </p>

            <div className="w-full max-w-xs">
              <h5 className="font-syne font-bold text-sm text-white mb-3">Newsletter</h5>
              <form onSubmit={(e) => e.preventDefault()} className="flex flex-col gap-2">
                <input
                  type="text"
                  placeholder="Prénom *"
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl border border-white/20 bg-white/10 text-white placeholder-white/60 text-xs focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]"
                />
                <input
                  type="email"
                  placeholder="Adresse e-mail *"
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl border border-white/20 bg-white/10 text-white placeholder-white/60 text-xs focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]"
                />
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-[#0ea5e9] hover:bg-[#0284c7] text-white font-bold text-xs shadow-md transition-all cursor-pointer"
                >
                  S'abonner
                </button>
              </form>
            </div>
          </div>

          {/* ── Col 2: Services ── */}
          <div className="lg:col-span-3">
            <h5 className="font-syne font-bold text-sm text-white mb-4 uppercase tracking-wider">
              Services
            </h5>
            <ul className="space-y-2.5 text-xs text-sky-100/90 font-medium">
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  BIOLOGIE MÉDICALE
                </Link>
              </li>
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  IMAGERIE MÉDICALE
                </Link>
              </li>
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  EXPLORATIONS FONCTIONNELLES
                </Link>
              </li>
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  AMBULANCE MÉDICALISÉE
                </Link>
              </li>
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  SOINS DENTAIRES
                </Link>
              </li>
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  SOINS SPÉCIALISÉS
                </Link>
              </li>
            </ul>
          </div>

          {/* ── Col 3: Navigation ── */}
          <div className="lg:col-span-2">
            <h5 className="font-syne font-bold text-sm text-white mb-4 uppercase tracking-wider">
              Navigation
            </h5>
            <ul className="space-y-2.5 text-xs text-sky-100/90 font-medium">
              <li>
                <Link to="/sante/recherche/" className="hover:text-[#0ea5e9] transition-colors">
                  Trouver un service
                </Link>
              </li>
              <li>
                <Link to="/inscription/" className="hover:text-[#0ea5e9] transition-colors">
                  Rejoindre MedCare
                </Link>
              </li>
              <li>
                <Link to="/how-it-works" className="hover:text-[#0ea5e9] transition-colors">
                  Comment ça marche
                </Link>
              </li>
              <li>
                <Link to="/about" className="hover:text-[#0ea5e9] transition-colors">
                  À propos
                </Link>
              </li>
              <li>
                <Link to="/about" className="hover:text-[#0ea5e9] transition-colors">
                  Politique de confidentialités
                </Link>
              </li>
              <li>
                <Link to="/about" className="hover:text-[#0ea5e9] transition-colors">
                  Mentions légales
                </Link>
              </li>
            </ul>
          </div>

          {/* ── Col 4: Contactez-nous & Socials ── */}
          <div className="lg:col-span-3">
            <h5 className="font-syne font-bold text-sm text-white mb-4 uppercase tracking-wider">
              Contactez-nous
            </h5>
            <ul className="space-y-3 text-xs text-sky-100/90 font-medium mb-6">
              <li className="flex items-start gap-2.5">
                <i className="ti ti-map-pin text-[#0ea5e9] text-sm shrink-0 mt-0.5"></i>
                <span>Point E-Dakar Sénégal, 4890</span>
              </li>
              <li className="flex items-center gap-2.5">
                <i className="ti ti-mail text-[#0ea5e9] text-sm shrink-0"></i>
                <a href="mailto:contact@medcare.sn" className="hover:text-[#0ea5e9] transition-colors">
                  contact@medcare.sn
                </a>
              </li>
              <li className="flex items-center gap-2.5">
                <i className="ti ti-phone text-[#0ea5e9] text-sm shrink-0"></i>
                <a href="tel:+221781673189" className="hover:text-[#0ea5e9] transition-colors font-bold">
                  +221 78 167 31 89
                </a>
              </li>
            </ul>

            {/* Social Links */}
            <div className="flex items-center gap-2.5">
              <a
                href="#facebook"
                aria-label="Facebook"
                className="w-9 h-9 rounded-xl bg-white/10 hover:bg-[#0ea5e9] flex items-center justify-center text-white transition-colors"
              >
                <i className="ti ti-brand-facebook text-base"></i>
              </a>
              <a
                href="#x"
                aria-label="X"
                className="w-9 h-9 rounded-xl bg-white/10 hover:bg-[#0ea5e9] flex items-center justify-center text-white transition-colors"
              >
                <i className="ti ti-brand-x text-base"></i>
              </a>
              <a
                href="#linkedin"
                aria-label="LinkedIn"
                className="w-9 h-9 rounded-xl bg-white/10 hover:bg-[#0ea5e9] flex items-center justify-center text-white transition-colors"
              >
                <i className="ti ti-brand-linkedin text-base"></i>
              </a>
              <a
                href="#instagram"
                aria-label="Instagram"
                className="w-9 h-9 rounded-xl bg-white/10 hover:bg-[#0ea5e9] flex items-center justify-center text-white transition-colors"
              >
                <i className="ti ti-brand-instagram text-base"></i>
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom Bar ── */}
      <div className="border-t border-white/10 py-5 bg-[#0a2540]/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between text-xs text-sky-200/80 gap-3">
          <p>© {currentYear} MedCare.sn – Tous droits réservés</p>
          <nav className="flex items-center gap-5">
            <Link to="/about" className="hover:text-white transition-colors">
              Privacy policy
            </Link>
            <Link to="/about" className="hover:text-white transition-colors">
              Terms &amp; Conditions
            </Link>
            <Link to="/how-it-works" className="hover:text-white transition-colors">
              FAQs
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
