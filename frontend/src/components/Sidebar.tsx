import { motion, AnimatePresence } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore } from '../store/appStore';
import type { AuthSession } from '../lib/api';

interface SidebarProps {
  open: boolean;
  authSession: AuthSession | null;
  authSessionError: string;
  onClose: () => void;
}

export function Sidebar({ open, authSession, authSessionError, onClose }: SidebarProps) {
  const location = useLocation();
  const { theme, toggleTheme } = useAppStore();

  const providerLinks = [
    { to: '/sante/prestataire/tableau-de-bord/', label: 'Tableau de bord', icon: 'ti-layout-dashboard' },
    { to: '/sante/prestataire/devis/', label: 'Devis', icon: 'ti-file-invoice' },
    { to: '/rdv/pro/agenda/', label: 'Rendez-vous', icon: 'ti-calendar' },
    { to: '/sante/prestataire/actes/', label: 'Catalogue d’actes', icon: 'ti-stethoscope' },
    { to: '/sante/prestataire/profil-public/', label: 'Profil public', icon: 'ti-id' },
    { to: '/sante/prestataire/organisme/modifier/', label: authSession?.is_praticien ? 'Profil professionnel' : 'Fiche structure', icon: 'ti-building-hospital' },
    ...(!authSession?.is_praticien ? [
      { to: '/sante/prestataire/organisme/horaires/', label: 'Horaires', icon: 'ti-clock' },
      { to: '/sante/prestataire/assurances/', label: 'Assurances', icon: 'ti-shield-check' },
      { to: '/sante/prestataire/acces/', label: 'Accès praticiens', icon: 'ti-users' },
    ] : [
      { to: '/sante/prestataire/acces/', label: 'Affiliations', icon: 'ti-users' },
      { to: '/rdv/pro/agenda/grille/', label: 'Agenda', icon: 'ti-calendar-event' },
    ]),
    { to: '/messaging/', label: 'Messages', icon: 'ti-message' },
    { to: '/sante/prestataire/parametres/', label: 'Paramètres', icon: 'ti-settings' },
  ];

  const navLinks = authSession?.is_prestataire
    ? providerLinks
    : authSession?.is_patient
      ? [
        { to: '/sante/recherche/', label: 'Annuaire & Soins', icon: 'ti-search' },
        { to: '/users/compte/panel/', label: 'Mon compte patient', icon: 'ti-user' },
        { to: '/users/compte/panel/profil/', label: 'Mes informations', icon: 'ti-id' },
        { to: '/users/compte/panel/assurance/', label: 'Mon assurance', icon: 'ti-shield-check' },
        { to: '/users/compte/panel/chariot/', label: 'Mon panier', icon: 'ti-shopping-cart' },
        { to: '/users/compte/panel/devis/', label: 'Mes devis', icon: 'ti-file-invoice' },
        { to: '/users/compte/panel/rdv/', label: 'Mes rendez-vous', icon: 'ti-calendar' },
        { to: '/messaging/notifications/', label: 'Notifications', icon: 'ti-bell' },
        { to: '/messaging/rappels/', label: 'Rappels', icon: 'ti-alarm' },
      ]
      : [
        { to: '/', label: 'Accueil Vitrine', icon: 'ti-home' },
        { to: '/sante/recherche/', label: 'Annuaire & Soins', icon: 'ti-search' },
        { to: '/mobile', label: 'Vue Mobile Patient', icon: 'ti-device-mobile' },
      ];

  const aboutLinks = [
    { to: '/about', label: 'Qui sommes-nous ?', icon: 'ti-info-circle' },
    { to: '/how-it-works', label: 'Comment ça marche', icon: 'ti-route' },
    { to: '/contact', label: 'Contact & Support', icon: 'ti-mail' },
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
                src="/static/images/logo_MEDCARE.png"
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

            {authSession && !authSession.authenticated && !authSessionError && (
              <Link
                to="/sante/recherche/"
                onClick={onClose}
                className="mx-4 mt-4 flex items-center justify-center gap-2 rounded-xl bg-[#0a5c8a] px-4 py-3 text-sm font-bold text-white shadow-sm transition-colors hover:bg-[#084b70]"
              >
                <i className="ti ti-search text-base" aria-hidden="true" />
                Trouver un service
              </Link>
            )}

            {/* Rejoindre MedCare Promo Card */}
            {authSession && !authSession.authenticated && !authSessionError && (
              <div className="p-4 mx-4 mt-4 rounded-2xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white shadow-md flex items-center justify-between">
                <div>
                  <div className="text-[11px] font-extrabold uppercase tracking-wider text-sky-200">
                    Rejoindre le réseau
                  </div>
                  <div className="text-sm font-black mt-0.5">Inscription MedCare</div>
                </div>
                <Link
                  to="/inscription/"
                  onClick={onClose}
                  className="px-3 py-1.5 rounded-xl bg-white text-[#0a5c8a] text-xs font-bold shadow hover:bg-gray-100 transition-colors"
                >
                  Commencer
                </Link>
              </div>
            )}

            {/* Menu Links */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div>
                <div className="text-[10px] font-extrabold text-gray-400 uppercase tracking-wider px-3 mb-1">
                  {authSession?.is_praticien ? 'Espace praticien' : authSession?.is_prestataire ? 'Espace structure' : authSession?.is_patient ? 'Espace patient' : 'Navigation'}
                </div>
                <div className="space-y-1">
                  {navLinks.map((link) => {
                    const isActive = location.pathname === link.to;
                    return (
                      <Link
                        key={link.to}
                        to={link.to}
                        onClick={onClose}
                        className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all ${
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
                </div>
              </div>

              <div>
                <div className="text-[10px] font-extrabold text-gray-400 uppercase tracking-wider px-3 mb-1">
                  À propos
                </div>
                <div className="space-y-1">
                  {aboutLinks.map((link) => {
                    const isActive = location.pathname === link.to;
                    return (
                      <Link
                        key={link.to}
                        to={link.to}
                        onClick={onClose}
                        className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all ${
                          isActive
                            ? 'bg-[#0a5c8a]/10 dark:bg-white/10 text-[#0a5c8a] dark:text-[#0ea5e9] font-bold'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-semibold'
                        }`}
                      >
                        <i className={`ti ${link.icon} text-base text-[#0ea5e9]`}></i>
                        <span className="text-xs sm:text-sm">{link.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>

              <div className="pt-2 border-t border-gray-200 dark:border-gray-800">
                <div className="text-[10px] font-extrabold text-gray-400 uppercase tracking-wider px-3 mb-1">
                  Mon Compte
                </div>
                {authSession?.authenticated ? (
                  <a
                    href="/users/deconnexion/"
                    className="flex items-center gap-3 px-3.5 py-2 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-semibold text-xs"
                  >
                    <i className="ti ti-logout text-base text-gray-500"></i>
                    <span>Déconnexion</span>
                  </a>
                ) : authSession && !authSessionError ? (
                  <>
                    <Link
                      to="/connexion/"
                      onClick={onClose}
                      className="flex items-center gap-3 px-3.5 py-2 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 font-semibold text-xs"
                    >
                      <i className="ti ti-login text-base text-gray-500"></i>
                      <span>Se connecter</span>
                    </Link>
                    <Link
                      to="/inscription/"
                      onClick={onClose}
                      className="flex items-center gap-3 px-3.5 py-2 rounded-xl text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 font-bold text-xs"
                    >
                      <i className="ti ti-user-plus text-base"></i>
                      <span>Créer un compte (Patient / Soignant)</span>
                    </Link>
                  </>
                ) : (
                  <p className="px-3.5 py-2 text-xs text-gray-500 dark:text-gray-400" role="status" aria-live="polite">
                    {authSessionError ? 'Session indisponible' : 'Vérification de la session…'}
                  </p>
                )}
              </div>
            </div>

            {/* Footer with Controls */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 flex flex-col gap-3">
              <div className="flex items-center justify-end">
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
                href="https://wa.me/221781673189"
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
