import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/appStore';

interface NavbarProps {
  cartCount?: number;
  onOpenSidebar: () => void;
}

export function Navbar({ cartCount = 0, onOpenSidebar }: NavbarProps) {
  const { lang, setLang, theme, toggleTheme, toggleCart } = useAppStore();
  const { i18n } = useTranslation();
  const location = useLocation();
  const [aboutOpen, setAboutOpen] = useState(false);
  const aboutRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (aboutRef.current && !aboutRef.current.contains(event.target as Node)) {
        setAboutOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLangToggle = () => {
    const next = lang === 'fr' ? 'en' : 'fr';
    setLang(next);
    i18n.changeLanguage(next);
  };

  const isAboutActive =
    location.pathname === '/about' ||
    location.pathname === '/how-it-works' ||
    location.pathname === '/contact';

  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-md border-b border-gray-200/90 dark:border-gray-800 shadow-[0_2px_16px_rgba(18,58,99,.06)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-18 flex items-center justify-between gap-3">
        {/* ── Left: Burger Button + Brand Logo ────────────────── */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenSidebar}
            className="p-2.5 rounded-xl border border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
            title="Ouvrir le menu"
            aria-label="Ouvrir le menu"
          >
            <i className="ti ti-menu-2 text-xl font-bold"></i>
          </button>

          <Link to="/" className="flex items-center shrink-0">
            {/* Real MedCare logo without duplicate text */}
            <img
              src="/logo_MEDCARE.png"
              alt="MedCare"
              className="h-8 sm:h-10 w-auto object-contain"
            />
          </Link>
        </div>

        {/* ── Center: Main Navigation (Accueil, Annuaire, À propos) ── */}
        <nav className="hidden lg:flex items-center gap-6">
          <Link
            to="/"
            className={`text-sm font-bold transition-colors ${
              location.pathname === '/'
                ? 'text-[#0a5c8a] dark:text-[#0ea5e9]'
                : 'text-gray-700 dark:text-gray-300 hover:text-[#0a5c8a] dark:hover:text-white'
            }`}
          >
            Accueil
          </Link>

          <Link
            to="/search"
            className={`text-sm font-bold transition-colors ${
              location.pathname === '/search'
                ? 'text-[#0a5c8a] dark:text-[#0ea5e9]'
                : 'text-gray-700 dark:text-gray-300 hover:text-[#0a5c8a] dark:hover:text-white'
            }`}
          >
            Annuaire
          </Link>

          {/* À propos Dropdown */}
          <div className="relative" ref={aboutRef}>
            <button
              type="button"
              onClick={() => setAboutOpen(!aboutOpen)}
              className={`flex items-center gap-1.5 text-sm font-bold transition-colors cursor-pointer ${
                isAboutActive
                  ? 'text-[#0a5c8a] dark:text-[#0ea5e9]'
                  : 'text-gray-700 dark:text-gray-300 hover:text-[#0a5c8a] dark:hover:text-white'
              }`}
              aria-expanded={aboutOpen}
            >
              <span>À propos</span>
              <i
                className={`ti ti-chevron-down text-xs transition-transform duration-200 ${
                  aboutOpen ? 'rotate-180' : ''
                }`}
              ></i>
            </button>

            {aboutOpen && (
              <div className="absolute top-full left-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 py-2 z-50">
                <Link
                  to="/about"
                  onClick={() => setAboutOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-xs font-bold text-gray-700 dark:text-gray-200 hover:bg-sky-50 dark:hover:bg-gray-750 hover:text-[#0a5c8a] dark:hover:text-white transition-colors"
                >
                  <i className="ti ti-info-circle text-base text-[#0ea5e9]"></i>
                  <span>Qui sommes-nous ?</span>
                </Link>
                <Link
                  to="/how-it-works"
                  onClick={() => setAboutOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-xs font-bold text-gray-700 dark:text-gray-200 hover:bg-sky-50 dark:hover:bg-gray-750 hover:text-[#0a5c8a] dark:hover:text-white transition-colors"
                >
                  <i className="ti ti-route text-base text-[#0ea5e9]"></i>
                  <span>Comment ça marche</span>
                </Link>
                <Link
                  to="/contact"
                  onClick={() => setAboutOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-xs font-bold text-gray-700 dark:text-gray-200 hover:bg-sky-50 dark:hover:bg-gray-750 hover:text-[#0a5c8a] dark:hover:text-white transition-colors"
                >
                  <i className="ti ti-mail text-base text-[#0ea5e9]"></i>
                  <span>Contact</span>
                </Link>
              </div>
            )}
          </div>
        </nav>

        {/* ── Right CTAs (Connexion, Trouver un service, Rejoindre MedCare) ── */}
        <div className="flex items-center gap-2">
          {/* Action buttons (identical to landing_header.html) */}
          <div className="hidden sm:flex items-center gap-2">
            <Link
              to="/login"
              className="px-3.5 py-2 text-xs font-extrabold text-[#123a63] dark:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-all"
            >
              Connexion
            </Link>

            <Link
              to="/search"
              className="px-3.5 py-2 text-xs font-extrabold rounded-xl border-1.5 border-[#123a63] dark:border-sky-500 text-[#123a63] dark:text-sky-400 hover:bg-[#123a63] hover:text-white dark:hover:bg-sky-500 dark:hover:text-white transition-all shadow-sm"
            >
              Trouver un service
            </Link>

            <Link
              to="/register"
              className="px-4 py-2 text-xs font-extrabold rounded-xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white hover:brightness-105 transition-all shadow-md active:scale-95"
            >
              Rejoindre MedCare
            </Link>
          </div>

          {/* Language toggle */}
          <button
            type="button"
            onClick={handleLangToggle}
            className="p-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-bold text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 uppercase"
            title="Changer de langue"
          >
            {lang}
          </button>

          {/* Theme toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
            title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
          >
            <i className={`ti ${theme === 'dark' ? 'ti-sun' : 'ti-moon'} text-base`}></i>
          </button>

          {/* Cart toggle */}
          <button
            type="button"
            onClick={toggleCart}
            className="relative p-2.5 rounded-xl bg-[#123a63] text-white hover:bg-[#1a4f87] transition-all shadow-sm cursor-pointer"
            title="Panier de soins"
          >
            <i className="ti ti-shopping-cart text-base"></i>
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-[#0ea5e9] text-white rounded-full text-[10px] font-bold flex items-center justify-center border-2 border-white dark:border-gray-900">
                {cartCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
