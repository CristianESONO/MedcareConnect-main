import { Link, useLocation } from 'react-router-dom';
import type { AuthSession } from '../lib/api';

interface ProviderWorkspaceSidebarProps {
  authSession: AuthSession | null;
}

const commonLinks = [
  { to: '/sante/prestataire/tableau-de-bord/', label: 'Tableau de bord', icon: 'ti-layout-dashboard' },
  { to: '/sante/prestataire/devis/', label: 'Devis', icon: 'ti-file-invoice' },
  { to: '/rdv/pro/agenda/', label: 'Rendez-vous', icon: 'ti-calendar' },
  { to: '/sante/prestataire/actes/', label: 'Catalogue d’actes', icon: 'ti-stethoscope' },
  { to: '/sante/prestataire/profil-public/', label: 'Profil public', icon: 'ti-id' },
  { to: '/messaging/', label: 'Messages', icon: 'ti-message' },
  { to: '/sante/prestataire/parametres/', label: 'Paramètres', icon: 'ti-settings' },
];

const structureLinks = [
  { to: '/sante/prestataire/organisme/modifier/', label: 'Fiche structure', icon: 'ti-building-hospital' },
  { to: '/sante/prestataire/type-etablissement/', label: 'Établissement', icon: 'ti-adjustments' },
  { to: '/sante/prestataire/organisme/horaires/', label: 'Horaires', icon: 'ti-clock' },
  { to: '/sante/prestataire/assurances/', label: 'Assurances', icon: 'ti-shield-check' },
  { to: '/sante/prestataire/acces/', label: 'Accès praticiens', icon: 'ti-users' },
  { to: '/sante/prestataire/tickets/', label: 'Tickets', icon: 'ti-ticket' },
  { to: '/sante/prestataire/actes/rappels/', label: 'Rappels RDV', icon: 'ti-bell' },
  { to: '/sante/prestataire/medplaque/', label: 'MedPlaque', icon: 'ti-nfc' },
  { to: '/sante/prestataire/bilan/', label: 'Bilan KPI', icon: 'ti-chart-bar' },
];

const practitionerLinks = [
  { to: '/sante/prestataire/organisme/modifier/', label: 'Profil professionnel', icon: 'ti-id' },
  { to: '/sante/prestataire/acces/', label: 'Affiliations', icon: 'ti-users' },
  { to: '/rdv/pro/agenda/grille/', label: 'Agenda', icon: 'ti-calendar-event' },
  { to: '/sante/prestataire/tickets/', label: 'Tickets', icon: 'ti-ticket' },
];

export function ProviderWorkspaceSidebar({ authSession }: ProviderWorkspaceSidebarProps) {
  const location = useLocation();
  const isPractitioner = authSession?.is_praticien ?? false;
  const links = [
    ...commonLinks,
    ...(isPractitioner ? practitionerLinks : structureLinks),
  ];

  return (
    <aside
      aria-label={isPractitioner ? 'Navigation praticien' : 'Navigation structure'}
      className="sticky top-[72px] hidden h-[calc(100vh-72px)] w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white px-3 py-6 dark:border-slate-800 dark:bg-slate-950 lg:block"
    >
      <div className="mb-5 px-3">
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {isPractitioner ? 'Espace praticien' : 'Espace structure'}
        </p>
        <h2 className="mt-1 text-lg font-extrabold text-slate-900 dark:text-white">
          MedCare Pro
        </h2>
      </div>
      <nav className="space-y-1">
        {links.map((link) => {
          const active = location.pathname === link.to
            || (link.to === '/sante/prestataire/devis/' && location.pathname.startsWith('/sante/prestataire/devis/'))
            || (link.to === '/messaging/' && location.pathname.startsWith('/messaging/'));
          return (
            <Link
              key={link.to}
              to={link.to}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                active
                  ? 'bg-sky-50 font-bold text-sky-800 dark:bg-sky-950/50 dark:text-sky-200'
                  : 'font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900'
              }`}
            >
              <i className={`ti ${link.icon} text-lg`} aria-hidden="true" />
              <span>{link.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
