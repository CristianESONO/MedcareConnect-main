import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  adminDashboardApi,
  type AdminDashboardList,
  type AdminDashboardOrganization,
  type AdminDashboardSummary,
  type AdminDashboardUser,
} from '../lib/api';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { AdminWorkspaceHeader } from '../components/AdminWorkspaceHeader';
import type { ReactNode } from 'react';

type DashboardView = 'summary' | 'users' | 'organizations';

const navigation: { href: string; label: string }[] = [
  { href: '/dashboard/', label: 'Vue générale' },
  { href: '/dashboard/utilisateurs/', label: 'Utilisateurs' },
  { href: '/dashboard/organismes/', label: 'Structures' },
  { href: '/dashboard/services/', label: 'Services médicaux' },
  { href: '/dashboard/actes/', label: 'Actes médicaux' },
  { href: '/dashboard/assurances/', label: 'Assurances' },
  { href: '/dashboard/abonnements/fonctionnalites/', label: 'Fonctionnalités' },
  { href: '/dashboard/avis/', label: 'Avis plateforme' },
  { href: '/admin/', label: 'Gestion des modèles' },
  { href: '/notifications/admin/parametres/', label: 'Notifications' },
];

function displayDate(value: string) {
  return new Date(value).toLocaleDateString('fr-FR');
}

export function AdminDashboardShell({
  active,
  children,
}: {
  active: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <AdminWorkspaceHeader />
      <div className="mx-auto grid max-w-screen-2xl gap-5 p-4 lg:grid-cols-[230px_minmax(0,1fr)] lg:p-6">
        <nav className="h-fit rounded-2xl border border-slate-200 bg-white p-3 shadow-sm" aria-label="Administration">
          {navigation.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              aria-current={active === item.href ? 'page' : undefined}
              className={`mb-1 block rounded-lg px-3 py-2 text-sm ${active === item.href ? 'bg-sky-50 font-semibold text-sky-900' : 'text-slate-600 hover:bg-slate-50'}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}

export function AdminDashboardPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [summary, setSummary] = useState<AdminDashboardSummary | null>(null);
  const [users, setUsers] = useState<AdminDashboardList<AdminDashboardUser> | null>(null);
  const [organizations, setOrganizations] = useState<AdminDashboardList<AdminDashboardOrganization> | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const view: DashboardView = location.pathname.startsWith('/dashboard/utilisateurs/')
    ? 'users'
    : location.pathname.startsWith('/dashboard/organismes/')
      ? 'organizations'
      : 'summary';
  const page = Math.max(1, Number(searchParams.get('page') || 1));
  const query = searchParams.get('q') || '';
  const type = searchParams.get('type') || '';
  const status = searchParams.get('status') || '';
  const nature = searchParams.get('nature') || '';
  const period = searchParams.get('period') || '7j';

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError('');
    try {
      if (view === 'summary') {
        setSummary(await adminDashboardApi.summary(period, signal));
      } else if (view === 'users') {
        setUsers(await adminDashboardApi.users({ type, q: query, page }, signal));
      } else {
        setOrganizations(await adminDashboardApi.organizations({ status, nature, q: query, page }, signal));
      }
    } catch (reason) {
      if (!signal?.aborted) {
        setError(reason instanceof Error ? reason.message : 'Impossible de charger le tableau de bord.');
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [nature, page, period, query, status, type, view]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const search = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const params = new URLSearchParams(location.search);
    params.delete('page');
    for (const key of ['q', 'type', 'status', 'nature']) {
      const value = String(data.get(key) || '');
      if (value) params.set(key, value);
      else params.delete(key);
    }
    navigate(`${location.pathname}?${params.toString()}`);
  };

  const toggleUser = async (user: AdminDashboardUser) => {
    setBusyId(user.id);
    setError('');
    setNotice('');
    try {
      await adminDashboardApi.toggleUser(user.id);
      setNotice(`Le compte ${user.username} a été mis à jour.`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de modifier ce compte.');
    } finally {
      setBusyId(null);
    }
  };

  const changeOrganization = async (org: { id: number; name: string }, action: 'approve' | 'reject') => {
    setBusyId(org.id);
    setError('');
    setNotice('');
    try {
      await adminDashboardApi.organizationAction(org.id, action);
      setNotice(action === 'approve' ? `« ${org.name} » a été approuvé.` : `« ${org.name} » a été rejeté.`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de traiter cette structure.');
    } finally {
      setBusyId(null);
    }
  };

  const authError = error.toLowerCase().includes('authentification') || error.toLowerCase().includes('accès réservé');
  const activeHref = view === 'users'
    ? '/dashboard/utilisateurs/'
    : view === 'organizations'
      ? '/dashboard/organismes/'
      : '/dashboard/';

  return (
    <AdminDashboardShell active={activeHref}>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Pilotage plateforme</p>
          <h1 className="mt-1 font-syne text-2xl font-extrabold text-slate-900">
            {view === 'users' ? 'Utilisateurs' : view === 'organizations' ? 'Structures' : 'Vue générale'}
          </h1>
        </div>
        {view === 'summary' && (
          <div className="flex gap-2">
            {[
              ['7j', '7 jours'],
              ['30j', '30 jours'],
              ['M0', 'Depuis M0'],
            ].map(([value, label]) => (
              <Link
                key={value}
                to={`/dashboard/?period=${value}`}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${period === value ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700'}`}
              >
                {label}
              </Link>
            ))}
          </div>
        )}
      </div>
      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && (
        <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">
          {error}
          {authError && <Link to={`/connexion/?next=${encodeURIComponent(location.pathname)}`} className="ml-2 font-semibold underline">Se connecter</Link>}
        </p>
      )}
      {loading && <p className="rounded-xl bg-white p-5 text-sm text-slate-500" role="status">Chargement…</p>}
      {!loading && view === 'summary' && summary && (
        <section>
          <p className="mb-4 text-sm text-slate-500">{summary.period_label}</p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ['Structures actives', summary.kpis.active_structures, `+${summary.kpis.new_structures} sur la période`],
              ['Patients inscrits', summary.kpis.patients, 'sur la période'],
              ['Devis générés', summary.kpis.quotes, `${summary.kpis.quotes_total} au total`],
              ['Rendez-vous confirmés', summary.kpis.confirmed_appointments, `${summary.kpis.upcoming_appointments} à venir`],
              ['Valeur générée', `${summary.kpis.quote_value.toLocaleString('fr-FR')} FCFA`, 'estimée par les devis'],
              ['Actes référentiel', summary.kpis.acts, ''],
              ['Slots Pionniers', summary.kpis.pioneer_slots_remaining, `restants / ${summary.kpis.pioneer_target}`],
              ['MRR actuel', `${summary.kpis.mrr.toLocaleString('fr-FR')} FCFA`, 'plans actifs'],
            ].map(([label, value, hint]) => (
              <article key={String(label)} className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
                <p className="mt-1 text-xs text-slate-500">{hint}</p>
              </article>
            ))}
          </div>
          <div className="mt-5 grid gap-5 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <ActivityChart
                title={`Devis générés · ${summary.period_label}`}
                data={summary.chart.labels.map((label, index) => ({ label, value: summary.chart.quotes[index] ?? 0 }))}
              />
            </div>
            <section className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-bold">Structures en attente</h2>
                <Link to="/dashboard/organismes/?status=pending" className="text-xs font-semibold text-sky-700">Tout voir</Link>
              </div>
              <ul className="mt-3 divide-y divide-slate-100">
                {summary.pending_organizations.map((org) => (
                  <li key={org.id} className="py-3">
                    <p className="text-sm font-semibold">{org.name}</p>
                    <p className="text-xs text-slate-500">{org.city} · {org.type || 'Non classé'}</p>
                    <div className="mt-2 flex gap-2">
                      <button type="button" disabled={busyId === org.id} onClick={() => void changeOrganization(org, 'approve')} className="rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800 disabled:opacity-50">Approuver</button>
                      <button type="button" disabled={busyId === org.id} onClick={() => void changeOrganization(org, 'reject')} className="rounded bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 disabled:opacity-50">Rejeter</button>
                    </div>
                  </li>
                ))}
                {!summary.pending_organizations.length && <li className="py-5 text-sm text-slate-500">Aucune structure en attente.</li>}
              </ul>
            </section>
          </div>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <section className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex justify-between"><h2 className="font-bold">Derniers inscrits</h2><Link to="/dashboard/utilisateurs/" className="text-xs font-semibold text-sky-700">Voir tout</Link></div>
              <ul className="mt-3 divide-y divide-slate-100">
                {summary.recent_users.map((user) => <li key={user.id} className="flex justify-between gap-3 py-2 text-sm"><span>{user.name}<small className="block text-xs text-slate-500">{user.email}</small></span><span className="text-xs text-slate-500">{user.type}</span></li>)}
              </ul>
            </section>
            <section className="rounded-xl border border-slate-200 bg-white p-5">
              <h2 className="font-bold">Répartition des actes par service</h2>
              <ul className="mt-3 divide-y divide-slate-100">
                {summary.services.map((service) => <li key={service.id} className="flex justify-between py-2 text-sm"><span>{service.name}</span><span className="text-slate-500">{service.acts} actes</span></li>)}
              </ul>
            </section>
          </div>
          <section className="mt-5 rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="font-bold">Structures géolocalisées</h2>
            <p className="mt-1 text-xs text-slate-500">{summary.map.length} structures avec coordonnées GPS · affichage limité à 200.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {summary.map.slice(0, 12).map((org) => <p key={org.id} className="rounded-lg bg-slate-50 p-3 text-sm"><span className="font-semibold">{org.name}</span><span className="block text-xs text-slate-500">{org.city} · {org.latitude.toFixed(3)}, {org.longitude.toFixed(3)}</span></p>)}
            </div>
          </section>
        </section>
      )}
      {!loading && view !== 'summary' && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
          <form onSubmit={search} className="mb-4 flex flex-wrap gap-2">
            <input name="q" defaultValue={query} placeholder="Rechercher…" className="min-w-48 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            {view === 'users' ? (
              <select name="type" defaultValue={type} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="">Tous les types</option><option value="patient">Patients</option><option value="structure">Structures</option><option value="praticien">Praticiens</option><option value="admin">Admins</option>
              </select>
            ) : (
              <>
                <select name="status" defaultValue={status} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">Tous les états</option><option value="pending">En attente</option><option value="active">Actives</option></select>
                <select name="nature" defaultValue={nature} className="rounded-lg border border-slate-300 px-3 py-2 text-sm"><option value="">Toutes les natures</option><option value="structure">Structures</option><option value="praticien">Praticiens</option></select>
              </>
            )}
            <button type="submit" className="inline-flex min-h-10 items-center justify-center rounded-lg border border-sky-800 bg-sky-800 px-4 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 dark:border-sky-400 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300">Filtrer</button>
          </form>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{view === 'users' ? <><th className="p-3">Utilisateur</th><th className="p-3">Type</th><th className="p-3">Structure</th><th className="p-3">État</th><th className="p-3">Inscription</th><th className="p-3">Action</th></> : <><th className="p-3">Structure</th><th className="p-3">Compte</th><th className="p-3">Ville</th><th className="p-3">État</th><th className="p-3">Inscription</th><th className="p-3">Actions</th></>}</tr></thead>
              <tbody className="divide-y divide-slate-100">
                {view === 'users' && users?.rows.map((user) => (
                  <tr key={user.id}>
                    <td className="p-3 font-medium">{user.name}<small className="block text-xs text-slate-500">{user.email || user.username}</small></td>
                    <td className="p-3">{user.type_label}</td><td className="p-3">{user.organization || '—'}</td>
                    <td className="p-3">{user.is_active ? 'Actif' : 'Désactivé'}</td><td className="p-3">{displayDate(user.date_joined)}</td>
                    <td className="p-3"><button type="button" disabled={busyId === user.id} onClick={() => void toggleUser(user)} className="text-xs font-semibold text-sky-800 disabled:opacity-50">{user.is_active ? 'Désactiver' : 'Activer'}</button></td>
                  </tr>
                ))}
                {view === 'organizations' && organizations?.rows.map((org) => (
                  <tr key={org.id}>
                    <td className="p-3 font-medium"><Link to={`/dashboard/organismes/${org.id}/`} className="text-sky-800 hover:underline">{org.name}</Link><small className="block text-xs text-slate-500">{org.type || 'Non classé'}</small></td>
                    <td className="p-3">{org.user}</td><td className="p-3">{org.city || '—'}</td><td className="p-3">{org.is_active ? (org.is_verified ? 'Vérifiée' : 'Active') : 'En attente'}</td><td className="p-3">{displayDate(org.created_at)}</td>
                    <td className="p-3"><div className="flex gap-2"><button type="button" disabled={busyId === org.id} onClick={() => void changeOrganization(org, 'approve')} className="text-xs font-semibold text-emerald-800 disabled:opacity-50">Approuver</button><button type="button" disabled={busyId === org.id} onClick={() => void changeOrganization(org, 'reject')} className="text-xs font-semibold text-red-700 disabled:opacity-50">Rejeter</button></div></td>
                  </tr>
                ))}
                {((view === 'users' && !users?.rows.length) || (view === 'organizations' && !organizations?.rows.length)) && <tr><td colSpan={6} className="p-8 text-center text-slate-500">Aucun résultat.</td></tr>}
              </tbody>
            </table>
          </div>
          {(() => {
            const pagination = view === 'users' ? users?.pagination : organizations?.pagination;
            if (!pagination) return null;
            return <div className="mt-4 flex items-center justify-between text-sm text-slate-600"><span>{pagination.total} résultat(s) · page {pagination.page} / {Math.max(pagination.pages, 1)}</span><div className="flex gap-2"><Link aria-disabled={!pagination.has_previous} to={`?${new URLSearchParams({ ...(query ? { q: query } : {}), ...(type ? { type } : {}), ...(status ? { status } : {}), ...(nature ? { nature } : {}), page: String(Math.max(1, page - 1)) })}`} className={`rounded border px-3 py-1.5 ${pagination.has_previous ? 'bg-white' : 'pointer-events-none opacity-40'}`}>Précédent</Link><Link aria-disabled={!pagination.has_next} to={`?${new URLSearchParams({ ...(query ? { q: query } : {}), ...(type ? { type } : {}), ...(status ? { status } : {}), ...(nature ? { nature } : {}), page: String(page + 1) })}`} className={`rounded border px-3 py-1.5 ${pagination.has_next ? 'bg-white' : 'pointer-events-none opacity-40'}`}>Suivant</Link></div></div>;
          })()}
        </section>
      )}
    </AdminDashboardShell>
  );
}
