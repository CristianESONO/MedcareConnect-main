import { LogOut } from 'lucide-react';
import { Link } from 'react-router-dom';

interface AdminWorkspaceHeaderProps {
  username?: string;
  onLogout?: () => void;
}

export function AdminWorkspaceHeader({ username, onLogout }: AdminWorkspaceHeaderProps) {
  const logoutClassName = 'inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400';

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 bg-slate-950 px-5 py-4 text-white">
      <div className="flex min-w-0 flex-wrap items-center gap-x-6 gap-y-3">
        <Link to="/dashboard/" className="font-bold">MedCare · Administration</Link>
        <nav className="flex flex-wrap items-center gap-2 text-sm" aria-label="Navigation administrateur">
          <Link to="/dashboard/" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800 hover:text-white">Menu principal</Link>
          <Link to="/admin/" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800 hover:text-white">Gestion des modèles</Link>
          <Link to="/" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800 hover:text-white">Retour au site</Link>
        </nav>
      </div>
      <div className="flex items-center gap-3 text-sm">
        {username && <span className="text-slate-300">{username}</span>}
        {onLogout ? (
          <button type="button" onClick={onLogout} className={logoutClassName}>
            <LogOut size={15} aria-hidden="true" /> Déconnexion
          </button>
        ) : (
          <a href="/users/deconnexion/" className={logoutClassName}>
            <LogOut size={15} aria-hidden="true" /> Déconnexion
          </a>
        )}
      </div>
    </header>
  );
}
