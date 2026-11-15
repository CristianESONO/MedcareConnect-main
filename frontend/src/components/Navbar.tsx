import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/appStore';

interface NavbarProps {
  cartCount?: number;
  onOpenSidebar: () => void;
}

export function Navbar({ cartCount = 0, onOpenSidebar }: NavbarProps) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const { theme, toggleTheme, lang, setLang, toggleCart } = useAppStore();

  const handleLangToggle = () => {
    const next = lang === 'fr' ? 'en' : 'fr';
    setLang(next);
    i18n.changeLanguage(next);
  };

  const navLinks = [
    { to: '/', label: 'Accueil', icon: 'ti-home' },
    { to: '/search', label: 'Rechercher', icon: 'ti-search' },
    { to: '/mobile', label: 'Vue Mobile', icon: 'ti-device-mobile' },
    { to: '/dashboard', label: 'Soignants', icon: 'ti-stethoscope' },
    { to: '/panels', label: 'Panels & Forfaits', icon: 'ti-packages' },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-md border-b border-gray-200 dark:border-gray-800 shadow-[0_2px_16px_rgba(18,58,99,.06)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-18 flex items-center justify-between gap-3">
        {/* Left: Burger Menu + Brand Logo */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenSidebar}
            className="p-2.5 rounded-xl border border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="Ouvrir le menu"
          >
            <i className="ti ti-menu-2 text-xl font-bold"></i>
          </button>

          <Link to="/" className="flex items-center gap-2.5 shrink-0">
            <img
              src="/logo.png"
              alt="MedCare Connect"
              className="h-9 sm:h-11 w-auto object-contain"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
            <div className="hidden sm:flex flex-col">
              <span className="font-syne font-extrabold text-xl leading-none text-[#123a63] dark:text-white tracking-tight">
                MedCare<span className="text-[#0ea5e9]">Connect</span>
              </span>
              <span className="text-[10px] text-gray-500 dark:text-gray-400 font-bold uppercase tracking-wider mt-0.5">
                Plateforme Médicale • Sénégal
              </span>
            </div>
          </Link>
        </div>

        {/* Center: Desktop Navigation Pills */}
        <nav className="hidden lg:flex items-center gap-1 p-1 rounded-2xl bg-gray-100/90 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-white dark:bg-gray-700 text-[#123a63] dark:text-[#0ea5e9] shadow-sm'
                    : 'text-gray-700 dark:text-gray-300 hover:text-[#123a63] dark:hover:text-white'
                }`}
              >
                <i className={`ti ${link.icon} text-sm font-semibold`}></i>
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Tools: Auth Links + Lang + Theme + Cart */}
        <div className="flex items-center gap-2">
          {/* Connexion / Inscription Links for Desktop */}
          <div className="hidden md:flex items-center gap-2 mr-1">
            <Link
              to="/login"
              className="px-3 py-1.5 text-xs font-bold text-gray-700 dark:text-gray-300 hover:text-[#123a63] dark:hover:text-white transition-colors"
            >
              Connexion
            </Link>
            <Link
              to="/register"
              className="px-3.5 py-1.5 text-xs font-bold rounded-xl bg-[#123a63] text-white hover:bg-[#1a4f87] transition-all shadow-sm"
            >
              Créer un compte
            </Link>
          </div>

          {/* Lang toggle */}
          <button
            type="button"
            onClick={handleLangToggle}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-bold text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors uppercase"
            title="Changer de langue"
          >
            <i className="ti ti-world text-sm"></i>
            {lang}
          </button>

          {/* Theme toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
          >
            <i className={`ti ${theme === 'dark' ? 'ti-sun' : 'ti-moon'} text-base`}></i>
          </button>

          {/* Cart toggle */}
          <button
            type="button"
            onClick={toggleCart}
            className="relative flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-[#123a63] to-[#1a4f87] text-white text-xs font-bold shadow-sm hover:shadow transition-all active:scale-95"
            title="Ouvrir le panier de soins"
          >
            <i className="ti ti-shopping-cart text-base"></i>
            {cartCount > 0 && (
              <span className="w-5 h-5 bg-[#0ea5e9] text-white rounded-full text-[11px] font-bold flex items-center justify-center">
                {cartCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
