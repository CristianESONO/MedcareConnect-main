import { motion, AnimatePresence } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/appStore';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const { theme, toggleTheme, lang, setLang } = useAppStore();

  const handleLangToggle = () => {
    const next = lang === 'fr' ? 'en' : 'fr';
    setLang(next);
    i18n.changeLanguage(next);
  };

  const menuSections = [
    {
      title: 'Navigation Principale',
      links: [
        { to: '/', label: 'Accueil Vitrine', icon: 'ti-home', desc: 'Présentation & services' },
        { to: '/search', label: 'Recherche SIPN', icon: 'ti-search', desc: 'Comparer soins & tarifs' },
        { to: '/mobile', label: 'Vue Mobile Patient', icon: 'ti-device-mobile', desc: 'Interface tactile rapide' },
      ],
    },
    {
      title: 'Espace Professionnel',
      links: [
        { to: '/dashboard', label: 'Tableau de Bord', icon: 'ti-layout-dashboard', desc: 'Statistiques & activité' },
        { to: '/panels', label: 'Panels & Forfaits', icon: 'ti-packages', desc: 'Forfaits d\'actes niveau 3' },
      ],
    },
    {
      title: 'Compte & Accès',
      links: [
        { to: '/login', label: 'Connexion', icon: 'ti-login', desc: 'Accéder à votre espace' },
        { to: '/register', label: 'Créer un compte', icon: 'ti-user-plus', desc: 'Patient ou Professionnel' },
      ],
    },
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

          {/* Sidebar drawer */}
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 260 }}
            className="fixed top-0 left-0 bottom-0 w-80 sm:w-96 bg-white dark:bg-[#0f172a] shadow-2xl z-50 flex flex-col border-r border-gray-200 dark:border-gray-800"
          >
            {/* Header */}
            <div className="p-5 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-900/50">
              <div className="flex items-center gap-3">
                <img src="/logo.png" alt="MedCare" className="h-8 w-auto object-contain" />
                <div>
                  <h3 className="font-syne font-extrabold text-base text-[#123a63] dark:text-white leading-tight">
                    MedCare Connect
                  </h3>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400 font-semibold uppercase tracking-wider">
                    Menu & Navigation
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-xl text-gray-500 hover:text-gray-800 dark:hover:text-white hover:bg-gray-200/60 dark:hover:bg-gray-800 transition-colors"
                title="Fermer le menu"
              >
                <i className="ti ti-x text-lg"></i>
              </button>
            </div>

            {/* Quick Account Banner */}
            <div className="p-4 mx-4 mt-4 rounded-2xl bg-gradient-to-r from-[#123a63] to-[#1a4f87] text-white shadow-md flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-[#0ea5e9]">Nouveau sur MedCare ?</div>
                <div className="text-sm font-extrabold mt-0.5">Rejoignez le réseau</div>
              </div>
              <Link
                to="/register"
                onClick={onClose}
                className="px-3 py-1.5 rounded-xl bg-white text-[#123a63] text-xs font-bold shadow hover:bg-gray-100 transition-colors"
              >
                S'inscrire
              </Link>
            </div>

            {/* Menu Sections */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {menuSections.map((section) => (
                <div key={section.title}>
                  <h4 className="text-[11px] font-extrabold text-gray-400 uppercase tracking-wider px-2 mb-2">
                    {section.title}
                  </h4>
                  <div className="space-y-1">
                    {section.links.map((link) => {
                      const isActive = location.pathname === link.to;
                      return (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={onClose}
                          className={`flex items-center gap-3 p-2.5 rounded-xl transition-all ${
                            isActive
                              ? 'bg-[#123a63]/10 dark:bg-white/10 text-[#123a63] dark:text-[#0ea5e9] font-bold'
                              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-medium'
                          }`}
                        >
                          <div
                            className={`p-2 rounded-lg ${
                              isActive
                                ? 'bg-[#123a63] text-white dark:bg-[#0ea5e9] dark:text-[#0f172a]'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                            }`}
                          >
                            <i className={`ti ${link.icon} text-base`}></i>
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-xs font-bold text-gray-900 dark:text-white">
                              {link.label}
                            </div>
                            <div className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                              {link.desc}
                            </div>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Footer with Controls (Theme + Lang + WhatsApp) */}
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
