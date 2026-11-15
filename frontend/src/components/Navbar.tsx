import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Sun, Moon, Globe, ShoppingBag, Activity, Search, Layers, Smartphone } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { Button } from './ui/Button';

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
    { to: '/', label: t('nav.search'), icon: <Search size={16} /> },
    { to: '/dashboard', label: t('nav.dashboard'), icon: <Activity size={16} /> },
    { to: '/panels', label: t('nav.panels'), icon: <Layers size={16} /> },
    { to: '/mobile', label: 'Vue Mobile', icon: <Smartphone size={16} /> },
  ];

  return (
    <header className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-100 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-navy to-accent flex items-center justify-center text-white font-bold font-syne text-lg shadow-sm">
            M
          </div>
          <div className="flex flex-col">
            <span className="font-syne font-bold text-lg leading-none text-navy dark:text-white tracking-tight">
              MedCare<span className="text-accent">Connect</span>
            </span>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">
              Santé & Forfaits
            </span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1 bg-gray-50 dark:bg-gray-800/60 p-1 rounded-xl border border-gray-200/50 dark:border-gray-700/50">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-white dark:bg-gray-700 text-navy dark:text-accent shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-navy dark:hover:text-white'
                }`}
              >
                {link.icon}
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right actions: Theme, Lang, Cart */}
        <div className="flex items-center gap-2">
          {/* Lang toggle */}
          <button
            onClick={handleLangToggle}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors uppercase"
            title="Changer de langue"
          >
            <Globe size={14} />
            {lang}
          </button>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* Cart toggle */}
          <button
            onClick={toggleCart}
            className="relative p-2 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent transition-colors"
            title="Panier"
          >
            <ShoppingBag size={18} />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-navy dark:bg-accent text-white rounded-full text-[10px] font-bold flex items-center justify-center">
                {cartCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
