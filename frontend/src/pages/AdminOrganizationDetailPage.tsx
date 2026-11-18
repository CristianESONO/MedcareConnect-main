import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  adminDashboardApi,
  type AdminDashboardOrganizationDetail,
} from '../lib/api';
import { AdminDashboardShell } from './AdminDashboardPage';

function formatDate(value: string) {
  return new Date(value).toLocaleString('fr-FR');
}

function RecentList({
  title,
  rows,
}: {
  title: string;
  rows: { id: string; title: string; subtitle: string; status: string; date: string }[];
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="font-bold">{title}</h2>
      <ul className="mt-3 divide-y divide-slate-100">
        {rows.map((row) => <li key={row.id} className="py-2"><p className="text-sm font-semibold">{row.title}</p><p className="truncate text-xs text-slate-500">{row.subtitle}</p><p className="text-xs text-slate-400">{row.status ? `${row.status} · ` : ''}{formatDate(row.date)}</p></li>)}
        {!rows.length && <li className="py-4 text-sm text-slate-400">Aucune donnée récente.</li>}
      </ul>
    </section>
  );
}

export function AdminOrganizationDetailPage() {
  const { pk = '' } = useParams();
  const [detail, setDetail] = useState<AdminDashboardOrganizationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    adminDashboardApi.organization(Number(pk), controller.signal)
      .then(setDetail)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger la structure.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [pk]);

  const setOrganizationStatus = async (action: 'approve' | 'reject') => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await adminDashboardApi.organizationAction(Number(pk), action);
      setNotice(action === 'approve' ? 'La structure a été approuvée.' : 'La structure a été rejetée.');
      setDetail((current) => current ? {
        ...current,
        organization: {
          ...current.organization,
          is_active: action === 'approve',
          is_verified: action === 'approve',
        },
      } : current);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de modifier le statut.');
    } finally {
      setBusy(false);
    }
  };

  const organization = detail?.organization;
  const authError = error.toLowerCase().includes('authentification') || error.toLowerCase().includes('accès réservé');

  return (
    <AdminDashboardShell active="/dashboard/organismes/">
      <Link to="/dashboard/organismes/" className="text-sm font-semibold text-sky-800 hover:underline">← Retour aux structures</Link>
      {notice && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}{authError && <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 underline">Se connecter</Link>}</p>}
      {loading && <p className="mt-4 rounded-xl bg-white p-5 text-sm text-slate-500" role="status">Chargement…</p>}
      {!loading && organization && detail && (
        <main className="mt-4 space-y-5">
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{organization.type || 'Type non renseigné'} · {organization.nature}</p>
                <h1 className="mt-1 font-syne text-2xl font-extrabold">{organization.name}</h1>
                <p className="mt-1 text-sm text-slate-500">{organization.address}{organization.city ? `, ${organization.city}` : ''}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${organization.is_active ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>{organization.is_active ? (organization.is_verified ? 'Vérifiée' : 'Active') : 'En attente'}</span>
                <button type="button" disabled={busy} onClick={() => void setOrganizationStatus('approve')} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Approuver</button>
                <button type="button" disabled={busy} onClick={() => void setOrganizationStatus('reject')} className="rounded-lg border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 disabled:opacity-50">Rejeter</button>
              </div>
            </div>
            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
              <div><dt className="text-xs text-slate-500">Compte</dt><dd className="font-semibold">{organization.account || '—'}</dd></div>
              <div><dt className="text-xs text-slate-500">Abonnement</dt><dd className="font-semibold">{organization.subscription_plan || '—'}</dd></div>
              <div><dt className="text-xs text-slate-500">Inscription</dt><dd className="font-semibold">{formatDate(organization.created_at)}</dd></div>
              <div><dt className="text-xs text-slate-500">Profil public</dt><dd><a href={organization.public_url} className="font-semibold text-sky-800 hover:underline">Ouvrir le profil</a></dd></div>
            </dl>
          </section>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ['Rendez-vous', detail.stats.appointments],
              ['RDV à confirmer', detail.stats.pending_appointments],
              ['Sous-devis', detail.stats.quotes],
              ['Conversations', detail.stats.conversations],
            ].map(([label, value]) => <article key={String(label)} className="rounded-xl border border-slate-200 bg-white p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></article>)}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="font-bold">Bilan de complétion · {detail.bilan.score}/100</h2>
            <p className="mt-1 text-sm text-slate-600">{detail.bilan.signal_label} · {detail.bilan.reco}</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-sky-700" style={{ width: `${detail.bilan.completion_pct}%` }} /></div>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500"><span>{detail.bilan.devis_total} devis</span><span>{detail.bilan.actes_count} actes</span><span>{detail.bilan.insurances_count} assurances</span><span>{detail.bilan.completion_pct}% de profil complété</span></div>
          </section>

          <section className="grid gap-5 xl:grid-cols-3">
            <RecentList title="Derniers rendez-vous" rows={detail.recent_appointments.map((item) => ({ id: item.reference, title: item.reference, subtitle: item.patient, status: item.status, date: item.start }))} />
            <RecentList title="Derniers sous-devis" rows={detail.recent_quotes.map((item) => ({ id: item.reference, title: item.reference, subtitle: `${item.patient} · ${item.parent_reference}`, status: item.status, date: item.created_at }))} />
            <RecentList title="Conversations récentes" rows={detail.recent_conversations.map((item) => ({ id: String(item.id), title: item.label, subtitle: item.patient, status: '', date: item.updated_at }))} />
          </section>
        </main>
      )}
      {!loading && !detail && !error && <p className="mt-4 text-sm text-slate-500">Structure introuvable.</p>}
    </AdminDashboardShell>
  );
}
