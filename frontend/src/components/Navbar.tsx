import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/appStore';

interface NavbarProps {
  cartCount?: number;
}

export function Navbar({ cartCount = 0 }: NavbarProps) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const { theme, toggleTheme, lang, setLang, toggleCart } = useAppStore();

  const handleLangToggle = () => {
    const next = lang === 'fr' ? 'en' : 'fr';
    setLang(next);
    i18n.changeLanguage(next);
  };

  const navLinks = [
    { to: '/', label: t('nav.search'), icon: 'ti-search' },
    { to: '/dashboard', label: t('nav.dashboard'), icon: 'ti-layout-dashboard' },
    { to: '/panels', label: t('nav.panels'), icon: 'ti-packages' },
    { to: '/mobile', label: 'Vue Mobile', icon: 'ti-device-mobile' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-b border-gray-200/80 dark:border-gray-800 shadow-[0_2px_16px_rgba(18,58,99,.06)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-18 flex items-center justify-between gap-4">
        {/* Brand Logo & Tagline */}
        <Link to="/" className="flex items-center gap-3 shrink-0">
          <img
            src="/logo.png"
            alt="MedCare Connect"
            className="h-9 sm:h-11 w-auto object-contain"
            onError={(e) => {
              // Fallback if image path fails
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          <div className="hidden sm:flex flex-col">
            <span className="font-syne font-extrabold text-xl leading-none text-[#123a63] dark:text-white tracking-tight">
              MedCare<span className="text-[#4fa3c7]">Connect</span>
            </span>
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mt-0.5">
              Marketplace Médicale & SIPN
            </span>
          </div>
        </Link>

        {/* Center Navigation Links (Pill Style) */}
        <nav className="hidden md:flex items-center gap-1.5 p-1 rounded-2xl bg-gray-100/80 dark:bg-gray-800/80 border border-gray-200/60 dark:border-gray-700/60">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-white dark:bg-gray-700 text-[#123a63] dark:text-[#4fa3c7] shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-[#123a63] dark:hover:text-white'
                }`}
              >
                <i className={`ti ${link.icon} text-sm`}></i>
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Tools (Language, Theme, Cart) */}
        <div className="flex items-center gap-2">
          {/* Language Switcher */}
          <button
            type="button"
            onClick={handleLangToggle}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 text-xs font-bold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors uppercase"
            title="Changer de langue"
          >
            <i className="ti ti-world text-sm"></i>
            {lang}
          </button>

          {/* Theme Switcher */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
          >
            <i className={`ti ${theme === 'dark' ? 'ti-sun' : 'ti-moon'} text-base`}></i>
          </button>

          {/* Cart Trigger */}
          <button
            type="button"
            onClick={toggleCart}
            className="relative flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-[#123a63] to-[#1a4f87] text-white text-xs font-bold shadow-sm hover:shadow-md transition-all active:scale-95"
            title="Ouvrir le panier"
          >
            <i className="ti ti-shopping-cart text-base"></i>
            <span className="hidden sm:inline">Panier</span>
            {cartCount > 0 && (
              <span className="w-5 h-5 bg-[#4fa3c7] text-white rounded-full text-[11px] font-bold flex items-center justify-center">
                {cartCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
