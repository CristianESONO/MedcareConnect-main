import { motion, AnimatePresence } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/appStore';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { i18n } = useTranslation();
  const location = useLocation();
  const { theme, toggleTheme, lang, setLang } = useAppStore();

  const handleLangToggle = () => {
    const next = lang === 'fr' ? 'en' : 'fr';
    setLang(next);
    i18n.changeLanguage(next);
  };

  const navLinks = [
    { to: '/', label: 'Accueil', icon: 'ti-home' },
    { to: '/search', label: 'Annuaire & Soins', icon: 'ti-search' },
    { to: '/mobile', label: 'Vue Mobile Patient', icon: 'ti-device-mobile' },
    { to: '/dashboard', label: 'Espace Professionnel', icon: 'ti-stethoscope' },
    { to: '/panels', label: 'Panels & Forfaits', icon: 'ti-packages' },
  ];

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Sidebar Drawer */}
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 260 }}
            className="fixed top-0 left-0 bottom-0 w-80 sm:w-96 bg-white dark:bg-[#0f172a] shadow-2xl z-50 flex flex-col border-r border-gray-200 dark:border-gray-800"
          >
            {/* Header with real brand logo */}
            <div className="p-5 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/60 dark:bg-gray-900/60">
              <img
                src="/logo_MEDCARE.png"
                alt="MedCare"
                className="h-8 w-auto object-contain"
              />

              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-xl text-gray-500 hover:text-gray-800 dark:hover:text-white hover:bg-gray-200/60 dark:hover:bg-gray-800 transition-colors"
                title="Fermer le menu"
              >
                <i className="ti ti-x text-lg"></i>
              </button>
            </div>

            {/* Rejoindre MedCare Promo Card */}
            <div className="p-4 mx-4 mt-4 rounded-2xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white shadow-md flex items-center justify-between">
              <div>
                <div className="text-[11px] font-extrabold uppercase tracking-wider text-sky-200">
                  Rejoindre le réseau
                </div>
                <div className="text-sm font-black mt-0.5">Inscription MedCare</div>
              </div>
              <Link
                to="/register"
                onClick={onClose}
                className="px-3 py-1.5 rounded-xl bg-white text-[#0a5c8a] text-xs font-bold shadow hover:bg-gray-100 transition-colors"
              >
                Commencer
              </Link>
            </div>

            {/* Menu Links */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              <div className="text-[10px] font-extrabold text-gray-400 uppercase tracking-wider px-3 mb-1">
                Navigation
              </div>

              {navLinks.map((link) => {
                const isActive = location.pathname === link.to;
                return (
                  <Link
                    key={link.to}
                    to={link.to}
                    onClick={onClose}
                    className={`flex items-center gap-3 px-3.5 py-3 rounded-xl transition-all ${
                      isActive
                        ? 'bg-[#0a5c8a]/10 dark:bg-white/10 text-[#0a5c8a] dark:text-[#0ea5e9] font-bold'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-semibold'
                    }`}
                  >
                    <i className={`ti ${link.icon} text-lg text-[#0a5c8a] dark:text-[#0ea5e9]`}></i>
                    <span className="text-xs sm:text-sm">{link.label}</span>
                  </Link>
                );
              })}

              <div className="pt-4 mt-2 border-t border-gray-200 dark:border-gray-800">
                <div className="text-[10px] font-extrabold text-gray-400 uppercase tracking-wider px-3 mb-2">
                  Mon Compte
                </div>
                <Link
                  to="/login"
                  onClick={onClose}
                  className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-semibold text-xs"
                >
                  <i className="ti ti-login text-base text-gray-500"></i>
                  <span>Se connecter</span>
                </Link>
                <Link
                  to="/register"
                  onClick={onClose}
                  className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 font-bold text-xs"
                >
                  <i className="ti ti-user-plus text-base"></i>
                  <span>Créer un compte (Patient ou Soignant)</span>
                </Link>
              </div>
            </div>

            {/* Footer with Controls */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={handleLangToggle}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-bold text-gray-700 dark:text-gray-200 uppercase hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <i className="ti ti-world"></i>
                  <span>{lang === 'fr' ? 'Français' : 'English'}</span>
                </button>

                <button
                  type="button"
                  onClick={toggleTheme}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-bold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <i className={`ti ${theme === 'dark' ? 'ti-sun' : 'ti-moon'}`}></i>
                  <span>{theme === 'dark' ? 'Mode Clair' : 'Mode Sombre'}</span>
                </button>
              </div>

              {/* WhatsApp direct contact */}
              <a
                href="https://wa.me/221770000000"
                target="_blank"
                rel="noreferrer"
                className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition-colors"
              >
                <i className="ti ti-brand-whatsapp text-base"></i>
                <span>Assistance WhatsApp MedCare</span>
              </a>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
