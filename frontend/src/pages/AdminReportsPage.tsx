import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  adminReportApi,
  type AdminReportPlan,
  type BilansReport,
  type ComplianceReport,
  type FinancesReport,
  type PioneersReport,
  type SubscriptionsReport,
} from '../lib/adminReportApi';
import { AdminWorkspaceHeader } from '../components/AdminWorkspaceHeader';

const navigation = [
  ['/dashboard/abonnements/', 'Abonnements'],
  ['/dashboard/finances/', 'Finances'],
  ['/dashboard/pionniers/', 'Pionniers'],
  ['/dashboard/bilans/', 'Bilans consolidés'],
  ['/dashboard/conformite/', 'Conformité'],
];

const money = (value: number) => `${Number(value || 0).toLocaleString('fr-FR')} FCFA`;
const date = (value: string | null) => value ? new Date(value).toLocaleDateString('fr-FR') : '—';

function signalClass(signal: string) {
  if (signal === 'green') return 'bg-emerald-50 text-emerald-800';
  if (signal === 'amber') return 'bg-amber-50 text-amber-800';
  return 'bg-rose-50 text-rose-800';
}

function AdminReportsShell({ active, children }: { active: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <AdminWorkspaceHeader />
      <div className="mx-auto grid max-w-screen-2xl gap-5 p-4 lg:grid-cols-[230px_minmax(0,1fr)] lg:p-6">
        <nav className="h-fit rounded-2xl border border-slate-200 bg-white p-3 shadow-sm" aria-label="Administration">
          <Link to="/dashboard/" className="mb-1 block rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50">Vue générale</Link>
          {navigation.map(([href, label]) => (
            <Link key={href} to={href} aria-current={active === href ? 'page' : undefined}
              className={`mb-1 block rounded-lg px-3 py-2 text-sm ${active === href ? 'bg-sky-50 font-semibold text-sky-900' : 'text-slate-600 hover:bg-slate-50'}`}>
              {label}
            </Link>
          ))}
        </nav>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}>{children}</section>;
}

function Kpis({ items }: { items: [string, string | number, string?][] }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    {items.map(([label, value, hint]) => <Card key={label}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>)}
  </div>;
}

function PlanForm({
  plan,
  features,
  onSave,
  onCancel,
  busy,
}: {
  plan: AdminReportPlan | null;
  features: SubscriptionsReport['features'];
  onSave: (payload: Record<string, unknown>, planId?: number) => Promise<void>;
  onCancel: () => void;
  busy: boolean;
}) {
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload: Record<string, unknown> = {
      name: data.get('name'),
      slug: data.get('slug'),
      short_description: data.get('short_description'),
      long_description: data.get('long_description'),
      monthly_price_fcfa: Number(data.get('monthly_price_fcfa') || 0),
      is_default: data.has('is_default'),
      is_public: data.has('is_public'),
      is_pioneer_offer: data.has('is_pioneer_offer'),
      trial_months: data.get('trial_months') ? Number(data.get('trial_months')) : null,
      order: Number(data.get('order') || 0),
      included_features: data.getAll('included_features').map(Number),
    };
    await onSave(payload, plan?.id);
  };
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-bold">{plan ? `Modifier ${plan.name}` : 'Créer une formule'}</h2>
        <button type="button" onClick={onCancel} className="text-sm text-slate-500">Fermer</button>
      </div>
      <form key={plan?.id || 'new-plan'} onSubmit={(event) => void submit(event)} className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">Nom<input name="name" required defaultValue={plan?.name || ''} className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">Identifiant (slug)<input name="slug" defaultValue={plan?.slug || ''} className="mt-1 w-full rounded-lg border px-3 py-2" /><small className="text-xs text-slate-500">Laisser vide pour génération automatique.</small></label>
        <label className="text-sm">Tarif mensuel (FCFA)<input name="monthly_price_fcfa" type="number" min="0" defaultValue={plan?.monthly_price_fcfa || 0} className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">Durée d'essai (mois)<input name="trial_months" type="number" min="0" defaultValue={plan?.trial_months ?? ''} className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">Ordre<input name="order" type="number" min="0" defaultValue={plan?.order || 0} className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">Description courte<input name="short_description" defaultValue={plan?.short_description || ''} className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm sm:col-span-2">Description détaillée<textarea name="long_description" rows={3} defaultValue={plan?.long_description || ''} className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <div className="flex flex-wrap gap-4 text-sm sm:col-span-2">
          <label><input name="is_default" type="checkbox" defaultChecked={plan?.is_default || false} /> Plan par défaut</label>
          <label><input name="is_public" type="checkbox" defaultChecked={plan?.is_public ?? true} /> Visible publiquement</label>
          <label><input name="is_pioneer_offer" type="checkbox" defaultChecked={plan?.is_pioneer_offer || false} /> Offre Pionnier</label>
        </div>
        <fieldset className="rounded-lg border p-3 sm:col-span-2">
          <legend className="px-1 text-sm font-semibold">Fonctionnalités incluses</legend>
          {features.length ? <div className="grid gap-2 sm:grid-cols-2">
            {features.map((feature) => <label key={feature.id} className="text-sm">
              <input name="included_features" type="checkbox" value={feature.id}
                defaultChecked={plan?.included_feature_ids.includes(feature.id) || false} /> {feature.label}
            </label>)}
          </div> : <p className="text-sm text-slate-500">Aucune fonctionnalité configurée.</p>}
        </fieldset>
        <div className="flex gap-2 sm:col-span-2">
          <button disabled={busy} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Enregistrement…' : 'Enregistrer la formule'}</button>
          <button type="button" onClick={onCancel} className="rounded-lg border px-4 py-2 text-sm">Annuler</button>
        </div>
      </form>
    </Card>
  );
}

function ScenarioChart({ report }: { report: FinancesReport }) {
  const values = [...report.scenarios.pessimiste, ...report.scenarios.median, ...report.scenarios.optimiste];
  const max = Math.max(...values, 1);
  const points = (series: number[]) => series.map((value, index) =>
    `${30 + index * 55},${230 - (value / max) * 205}`).join(' ');
  return <Card className="mt-5">
    <h2 className="font-bold">Projection MRR — M0 à M12</h2>
    <p className="mb-3 text-xs text-slate-500">Projections composées : +2 %, +6 % et +12 % mensuels.</p>
    <div className="overflow-x-auto">
      <svg viewBox="0 0 740 270" className="h-64 min-w-[600px] w-full" role="img" aria-label="Projections MRR sur douze mois">
        <line x1="25" y1="230" x2="730" y2="230" stroke="#cbd5e1" />
        <polyline points={points(report.scenarios.pessimiste)} fill="none" stroke="#f43f5e" strokeWidth="3" />
        <polyline points={points(report.scenarios.median)} fill="none" stroke="#3b82f6" strokeWidth="3" />
        <polyline points={points(report.scenarios.optimiste)} fill="none" stroke="#10b981" strokeWidth="3" />
        {report.months.map((month, index) => <text key={month} x={30 + index * 55} y="255" textAnchor="middle" fontSize="10" fill="#64748b">{month}</text>)}
      </svg>
    </div>
    <p className="text-xs text-slate-600">Pessimiste (+2 %/mois) · Médian (+6 %/mois) · Optimiste (+12 %/mois)</p>
  </Card>;
}

export function AdminReportsPage() {
  const location = useLocation();
  const pathname = location.pathname;
  const active = navigation.find(([href]) => pathname.startsWith(href))?.[0] || navigation[0][0];
  const reportType = active.split('/')[2];
  const filter = new URLSearchParams(location.search).get('plan') || 'all';
  const [subscriptions, setSubscriptions] = useState<SubscriptionsReport | null>(null);
  const [finance, setFinance] = useState<FinancesReport | null>(null);
  const [pioneer, setPioneer] = useState<PioneersReport | null>(null);
  const [bilan, setBilan] = useState<BilansReport | null>(null);
  const [compliance, setCompliance] = useState<ComplianceReport | null>(null);
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [editingPlan, setEditingPlan] = useState<AdminReportPlan | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const handledPlanPath = useRef('');

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError('');
    try {
      if (reportType === 'abonnements') setSubscriptions(await adminReportApi.subscriptions(filter, signal));
      else if (reportType === 'finances') setFinance(await adminReportApi.finances(signal));
      else if (reportType === 'pionniers') setPioneer(await adminReportApi.pioneers(signal));
      else if (reportType === 'bilans') setBilan(await adminReportApi.bilans(signal));
      else if (reportType === 'conformite') {
        const data = await adminReportApi.compliance(signal);
        setCompliance(data);
        setChecks(Object.fromEntries(data.checklist.map((item) => [item.key, item.ok])));
      }
    } catch (reason) {
      if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger le rapport.');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filter, reportType]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    if (handledPlanPath.current === pathname) return;
    if (reportType !== 'abonnements') {
      handledPlanPath.current = pathname;
      return;
    }
    if (/^\/dashboard\/abonnements\/formules\/ajouter\/?$/.test(pathname)) {
      handledPlanPath.current = pathname;
      setEditingPlan(null);
      return;
    }
    const editMatch = pathname.match(/^\/dashboard\/abonnements\/formules\/(\d+)\/modifier\/?$/);
    if (editMatch) {
      if (!subscriptions) return;
      handledPlanPath.current = pathname;
      const plan = subscriptions.plans.find((item) => item.id === Number(editMatch[1]));
      if (plan) setEditingPlan(plan);
      else setError('Formule introuvable.');
      return;
    }
    handledPlanPath.current = pathname;
    setEditingPlan(undefined);
  }, [pathname, reportType, subscriptions]);

  const act = async (key: string, operation: () => Promise<unknown>, message: string) => {
    setBusy(key);
    setError('');
    setNotice('');
    try {
      await operation();
      setNotice(message);
      setEditingPlan(undefined);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'La modification a échoué.');
    } finally {
      setBusy('');
    }
  };

  const savePlan = (payload: Record<string, unknown>, id?: number) =>
    act('plan', () => adminReportApi.savePlan(payload, id), id ? 'Formule mise à jour.' : 'Formule créée.');

  const title = useMemo(() => ({
    abonnements: 'Gestion des abonnements',
    finances: 'Finances & MRR',
    pionniers: 'Slots Partenaires Pionniers CPP-2025',
    bilans: 'Bilans KPI consolidés',
    conformite: 'Données & Conformité CDP',
  }[reportType] || 'Rapports administrateur'), [reportType]);

  return (
    <AdminReportsShell active={active}>
      <div className="mb-5">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Pilotage plateforme</p>
        <h1 className="mt-1 text-2xl font-extrabold">{title}</h1>
      </div>
      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
      {loading && <Card><p role="status" className="text-sm text-slate-500">Chargement…</p></Card>}

      {!loading && reportType === 'abonnements' && subscriptions && <>
        <Kpis items={[
          ['Structures actives', subscriptions.kpis.active_organizations],
          ['Expire sous 30 jours', subscriptions.kpis.expiring_soon],
          ['Demandes upgrade', subscriptions.kpis.pending_upgrades],
          ['MRR actuel', money(subscriptions.kpis.mrr)],
        ]} />
        <Card className="mt-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-bold">Structures abonnées</h2>
            <div className="flex flex-wrap gap-2">
              {[
                ['all', 'Toutes'], ['pionnier', 'Pionniers'], ...subscriptions.plans.map((plan) => [plan.slug, plan.name]),
                ['expire', 'Expire bientôt'], ['inactif', 'Inactif'],
              ].map(([value, label]) => <Link key={value} to={`${active}?plan=${encodeURIComponent(value)}`}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${filter === value ? 'border-slate-900 bg-slate-900 text-white' : 'bg-white text-slate-600'}`}>{label}</Link>)}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Structure', 'Plan / affectation', 'Statut', 'Début', 'Échéance', 'Renouv. auto', 'Tarif/mois'].map((item) => <th key={item} className="p-3">{item}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">
                {subscriptions.organizations.map((org) => <tr key={org.id} className={org.expires_soon ? 'bg-rose-50/50' : ''}>
                  <td className="p-3 font-medium">{org.name}<small className="block text-xs text-slate-500">{org.type || '—'} · {org.city}</small></td>
                  <td className="p-3"><select aria-label={`Formule de ${org.name}`} value={org.is_active ? org.plan_slug : ''} disabled={busy === `org-${org.id}`}
                    onChange={(event) => void act(`org-${org.id}`, () => adminReportApi.assignPlan(org.id, event.target.value), `Formule de « ${org.name} » mise à jour.`)}
                    className="max-w-56 rounded border px-2 py-1 text-xs">
                    <option value="" disabled>Choisir une formule</option>
                    {subscriptions.plans.map((plan) => <option key={plan.id} value={plan.slug}>{plan.name}</option>)}
                    <option value="__desactiver__">Désactiver</option>
                  </select></td>
                  <td className="p-3">{org.is_active ? 'Actif' : 'Inactif'}</td>
                  <td className="p-3 text-xs">{date(org.subscription_started_at)}</td>
                  <td className={`p-3 text-xs ${org.expires_soon ? 'font-bold text-rose-700' : ''}`}>{date(org.subscription_renewal_at)}</td>
                  <td className="p-3 text-xs">{org.subscription_auto_renew ? 'Oui' : 'Non'}</td>
                  <td className="p-3 text-xs">{money(org.monthly_price_fcfa)}</td>
                </tr>)}
                {!subscriptions.organizations.length && <tr><td colSpan={7} className="p-8 text-center text-slate-500">Aucune structure pour ce filtre.</td></tr>}
              </tbody>
            </table>
          </div>
        </Card>
        <Card className="mt-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="font-bold">Formules et fonctionnalités</h2><p className="text-xs text-slate-500">Les inclusions modifient les fonctionnalités de l'offre.</p></div>
            <button type="button" onClick={() => setEditingPlan(null)} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Créer une formule</button>
          </div>
          {editingPlan !== undefined && <div className="mb-5"><PlanForm plan={editingPlan} features={subscriptions.features} onSave={savePlan} onCancel={() => setEditingPlan(undefined)} busy={busy === 'plan'} /></div>}
          <div className="grid gap-4 lg:grid-cols-2">
            {subscriptions.plans.map((plan) => <article key={plan.id} className="rounded-xl border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><h3 className="font-bold">{plan.name} {plan.is_default && <span className="text-xs text-blue-700">· Par défaut</span>} {plan.is_pioneer_offer && <span className="text-xs text-amber-700">· Pionnier</span>}</h3><p className="text-xs text-slate-500">{plan.short_description || 'Aucune description courte'}</p></div>
                <p className="text-right text-xs">{money(plan.monthly_price_fcfa)}<small className="block text-slate-500">{plan.orgs_count} structure(s)</small></p>
              </div>
              <div className="mt-3 space-y-2">{subscriptions.features.map((feature) => {
                const included = plan.included_feature_ids.includes(feature.id);
                return <button key={feature.id} type="button" disabled={busy === `feature-${plan.id}-${feature.id}`}
                  onClick={() => void act(`feature-${plan.id}-${feature.id}`, () => adminReportApi.toggleFeature(plan.id, feature.id), 'Fonctionnalité du plan mise à jour.')}
                  className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-xs ${included ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'bg-slate-50 text-slate-500'}`}>
                  <span>{feature.label}</span><strong>{included ? 'Activé' : 'Désactivé'}</strong>
                </button>;
              })}</div>
              <div className="mt-3 flex gap-3 border-t pt-3">
                <button type="button" onClick={() => setEditingPlan(plan)} className="text-xs font-semibold text-sky-800">Modifier</button>
                <button type="button" disabled={busy === `delete-${plan.id}`} onClick={() => {
                  if (window.confirm(`Supprimer la formule « ${plan.name} » ?`)) {
                    void act(`delete-${plan.id}`, () => adminReportApi.deletePlan(plan.id), 'Formule supprimée.');
                  }
                }} className="text-xs font-semibold text-rose-700 disabled:opacity-50">Supprimer</button>
              </div>
            </article>)}
            {!subscriptions.plans.length && <p className="text-sm text-slate-500">Aucune formule assignable.</p>}
          </div>
        </Card>
      </>}

      {!loading && reportType === 'finances' && finance && <>
        <Kpis items={[
          ['MRR actuel', money(finance.kpis.mrr), 'Cumul des plans'],
          ['ARR projeté an 1', money(finance.kpis.arr), 'MRR × 12'],
          ['Frais de service (500 F)', money(finance.kpis.service_fees), 'Actif à M6'],
          ['Taux de conversion estimé M6', finance.kpis.estimated_conversion, 'Signal vert Pionniers'],
        ]} />
        <ScenarioChart report={finance} />
        <Card className="mt-5">
          <h2 className="mb-3 font-bold">Répartition par formule</h2>
          <div className="space-y-4">{finance.plan_rows.map(({ plan, subtotal }) => <div key={plan.id}>
            <div className="flex justify-between gap-3 text-sm"><span>{plan.name} · {plan.orgs_count} structure(s)</span><strong>{money(subtotal)}</strong></div>
            <div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-sky-600" style={{ width: `${finance.kpis.mrr ? Math.min(100, subtotal / finance.kpis.mrr * 100) : 0}%` }} /></div>
            <p className="text-xs text-slate-500">Tarif {money(plan.monthly_price_fcfa)}</p>
          </div>)}
          {!finance.plan_rows.length && <p className="text-sm text-slate-500">Aucune formule.</p>}</div>
          <p className="mt-5 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Projections mathématiques, sans données réelles de paiement. Hypothèses : croissance composée de +2 %, +6 % ou +12 % par mois.</p>
        </Card>
      </>}

      {!loading && reportType === 'pionniers' && pioneer && <>
        <Kpis items={[
          ['Signés', `${pioneer.signed} / ${pioneer.target}`, `${pioneer.remaining} slots restants`],
          ['Actifs', pioneer.active], ['En attente', pioneer.pending], ['Onboarding', pioneer.onboarding],
        ]} />
        <Card className="mt-5">
          <h2 className="font-bold">Progression CPP-2025</h2>
          <div className="mt-3 h-3 rounded-full bg-amber-100"><div className="h-3 rounded-full bg-amber-500" style={{ width: `${pioneer.progress_pct}%` }} /></div>
          <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Réf. CPP', 'Structure', 'Zone', 'Statut', 'Plan', 'Actes', 'Signal M5', 'Profil'].map((x) => <th key={x} className="p-3">{x}</th>)}</tr></thead>
            <tbody className="divide-y">{pioneer.rows.map((row) => <tr key={row.reference}>
              <td className="p-3 font-mono text-xs font-bold text-amber-700">{row.reference}</td><td className="p-3">{row.organization.name}<small className="block text-xs text-slate-500">{row.organization.type}</small></td>
              <td className="p-3">{row.organization.city}</td><td className="p-3">{row.organization.is_active ? 'Actif' : 'Onboarding'}</td><td className="p-3">{row.organization.plan_name}</td><td className="p-3">{row.acts}</td>
              <td className="p-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${signalClass(row.signal)}`}>{row.signal_label} ({row.score})</span></td>
              <td className="p-3"><a className="text-sky-700 underline" href={`/sante/${row.organization.slug}/`} target="_blank" rel="noreferrer">Profil ↗</a></td>
            </tr>)}
            {!pioneer.rows.length && <tr><td colSpan={8} className="p-8 text-center text-slate-500">Aucune structure n'est rattachée à une formule Pionnier.</td></tr>}</tbody>
          </table></div>
        </Card>
      </>}

      {!loading && reportType === 'bilans' && bilan && <>
        <Kpis items={[
          ['Signal vert', bilan.counts.green], ['Signal orange', bilan.counts.amber], ['Signal rouge', bilan.counts.red], ['Structures actives', bilan.total],
        ]} />
        <Card className="mt-5">
          <h2 className="mb-3 font-bold">Scoring conversion M5 par structure · classement par score</h2>
          <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Structure', 'Plan', 'Vues', 'Devis', 'Actes', 'Compl.', 'Score', 'Signal M5', 'Reco M6'].map((x) => <th key={x} className="p-3">{x}</th>)}</tr></thead>
            <tbody className="divide-y">{bilan.rows.map((row) => <tr key={row.organization.id}>
              <td className="p-3 font-medium">{row.organization.name}<small className="block text-xs text-slate-500">{row.organization.city} · {row.organization.type || '—'}</small></td><td className="p-3">{row.organization.plan_name || '—'}</td>
              <td className="p-3">{row.organization.profile_views_count ?? '—'}</td><td className="p-3">{row.devis_total}</td><td className="p-3">{row.actes_count}</td><td className="p-3">{row.completion_pct} %</td><td className="p-3 font-bold">{row.score}</td>
              <td className="p-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${signalClass(row.signal)}`}>{row.signal_label}</span></td><td className="p-3 text-xs">{row.recommendation}</td>
            </tr>)}
            {!bilan.rows.length && <tr><td colSpan={9} className="p-8 text-center text-slate-500">Aucune structure active.</td></tr>}</tbody>
          </table></div>
        </Card>
      </>}

      {!loading && reportType === 'conformite' && compliance && <>
        <Card>
          <p className="text-xs uppercase tracking-wide text-slate-500">Score de conformité</p>
          <p className="mt-1 text-3xl font-bold">{compliance.completed} / {compliance.total}</p>
          <p className="mt-1 text-xs text-slate-500">Dernière sauvegarde : {compliance.updated_at ? new Date(compliance.updated_at).toLocaleString('fr-FR') : '—'}</p>
          <div className="mt-3 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${compliance.total ? compliance.completed / compliance.total * 100 : 0}%` }} /></div>
        </Card>
        <div className="mt-5 grid gap-5 xl:grid-cols-2">
          <Card>
            <h2 className="font-bold">Statut conformité</h2>
            <p className="mb-4 mt-1 text-xs text-slate-500">Les suggestions par défaut doivent être validées avant de marquer un point comme traité.</p>
            <form onSubmit={(event) => {
              event.preventDefault();
              void act('compliance', () => adminReportApi.saveCompliance(checks), 'Checklist conformité enregistrée.');
            }} className="space-y-3">
              {compliance.checklist.map((item) => <label key={item.key} className="flex gap-3 rounded-lg border p-3">
                <input type="checkbox" checked={checks[item.key] || false} onChange={(event) => setChecks((current) => ({ ...current, [item.key]: event.target.checked }))} className="mt-1" />
                <span><strong className="block text-sm">{item.label}</strong><small className="text-xs text-slate-500">{item.detail}</small></span>
              </label>)}
              <button disabled={busy === 'compliance'} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Enregistrer la checklist</button>
            </form>
          </Card>
          <Card>
            <div className="mb-3 flex items-center justify-between"><h2 className="font-bold">Logs d'audit récents</h2><span className="text-xs text-slate-500">30 derniers</span></div>
            <div className="overflow-x-auto"><table className="w-full text-left text-sm">
              <thead className="text-xs text-slate-500"><tr>{['Date', 'Acteur', 'Action', 'Cible'].map((x) => <th key={x} className="pb-2">{x}</th>)}</tr></thead>
              <tbody className="divide-y">{compliance.logs.map((log) => <tr key={log.id}>
                <td className="py-2 pr-2 text-xs">{new Date(log.action_time).toLocaleString('fr-FR')}</td><td className="py-2 pr-2 text-xs">{log.actor}</td>
                <td className="py-2 pr-2 text-xs">{log.action_flag === 1 ? 'Création' : log.action_flag === 2 ? 'Modif.' : log.action_flag === 3 ? 'Suppression' : '—'}</td>
                <td className="py-2 text-xs">{log.content_type} · {log.object_repr}</td>
              </tr>)}
              {!compliance.logs.length && <tr><td colSpan={4} className="py-6 text-center text-slate-500">Aucun log d'audit.</td></tr>}</tbody>
            </table></div>
          </Card>
        </div>
      </>}
    </AdminReportsShell>
  );
}
