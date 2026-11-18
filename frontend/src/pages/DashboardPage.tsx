import { useEffect, useState } from 'react';
import {
  Activity,
  Bell,
  Building2,
  CalendarDays,
  Clock3,
  DollarSign,
  Eye,
  FlaskConical,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Ticket,
} from 'lucide-react';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { StatCard } from '../components/dashboard/StatCard';
import { Card } from '../components/ui/Card';
import { dashboardApi, type DashboardStats } from '../lib/api';

const PERIODS: { key: DashboardStats['period_key']; label: string }[] = [
  { key: '7j', label: '7 jours' },
  { key: '30j', label: '30 jours' },
  { key: 'total', label: 'Depuis le début' },
];

const VISIT_SOURCES = [
  { key: 'all', label: 'Toutes les sources' },
  { key: 'annuaire', label: 'Annuaire' },
  { key: 'whatsapp', label: 'WhatsApp' },
  { key: 'nfc', label: 'NFC' },
  { key: 'qr', label: 'QR' },
] as const;

type ActivityMetric = 'devis' | 'vues' | 'reservations' | 'valeur' | 'medplaque';

const ACTIVITY_METRICS: { key: ActivityMetric; label: string; structuresOnly?: boolean }[] = [
  { key: 'devis', label: 'Devis' },
  { key: 'vues', label: 'Vues', structuresOnly: true },
  { key: 'reservations', label: 'Réservations' },
  { key: 'valeur', label: 'Commandes' },
  { key: 'medplaque', label: 'MedPlaque', structuresOnly: true },
];

function formatCurrency(value: number) {
  return `${Math.round(value).toLocaleString('fr-FR')} FCFA`;
}

function readQueryValue(key: string, fallback: string) {
  return new URLSearchParams(window.location.search).get(key) || fallback;
}

function updateQueryValue(key: string, value: string) {
  const params = new URLSearchParams(window.location.search);
  params.set(key, value);
  window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
}

export function DashboardPage() {
  const initialPeriod = readQueryValue('period', '30j');
  const [period, setPeriod] = useState<DashboardStats['period_key']>(
    PERIODS.some((option) => option.key === initialPeriod)
      ? initialPeriod as DashboardStats['period_key']
      : '30j',
  );
  const [visitSource, setVisitSource] = useState(readQueryValue('visit_src', 'all'));
  const [metric, setMetric] = useState<ActivityMetric>('devis');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    dashboardApi.stats(period, visitSource, controller.signal)
      .then((response) => {
        setStats(response);
        setError('');
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setError(reason instanceof Error ? reason.message : 'Impossible de charger le tableau de bord.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [period, visitSource, refreshKey]);

  useEffect(() => {
    const refreshOnFocus = () => {
      setError('');
      setLoading(true);
      setRefreshKey((current) => current + 1);
    };
    window.addEventListener('focus', refreshOnFocus);
    return () => window.removeEventListener('focus', refreshOnFocus);
  }, []);

  const metricLabel = stats?.activity_chart.meta[metric]?.label || 'Devis générés';
  const metricValues = stats?.activity_chart.series[metric] || [];
  const chartData = (stats?.activity_chart.labels || [])
    .slice(0, 8)
    .map((label, index) => ({ label, value: metricValues[index] ?? null }));

  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-8">
      <header className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-accent">
            Espace prestataire de santé
          </span>
          <h1 className="mt-1 font-syne text-2xl font-extrabold text-navy dark:text-white sm:text-3xl">
            Tableau de bord
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 sm:text-sm">
            {stats ? `${stats.org_name} · ${stats.period_label}` : 'Activité réelle de votre structure'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-xl border border-gray-200 bg-white p-1 text-xs font-semibold shadow-sm">
            {PERIODS.map((option) => (
              <button
                type="button"
                key={option.key}
                onClick={() => {
                  if (period === option.key) return;
                  updateQueryValue('period', option.key);
                  setError('');
                  setLoading(true);
                  setPeriod(option.key);
                }}
                aria-pressed={period === option.key}
                className={`rounded-lg px-3 py-1.5 transition ${
                  period === option.key ? 'bg-[#0a5c8a] text-white' : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <a
            href="/messaging/"
            className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <Bell size={15} aria-hidden="true" /> Messages {stats ? `(${stats.unread_messages})` : ''}
          </a>
          <button
            type="button"
            onClick={() => {
              setError('');
              setLoading(true);
              setRefreshKey((current) => current + 1);
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} aria-hidden="true" />
            Actualiser
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <p>{error}</p>
          {error.includes('Connectez-vous') && (
            <a href={`/connexion/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`} className="mt-2 inline-block font-semibold underline">
              Se connecter à un compte prestataire
            </a>
          )}
        </div>
      )}

      {loading && !stats && (
        <Card className="mb-5 p-5 text-sm text-gray-500" role="status">
          Chargement des données du tableau de bord…
        </Card>
      )}

      {stats && (
        <>
          {!stats.is_active && (
            <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
              <Clock3 size={19} className="mt-0.5 shrink-0" aria-hidden="true" />
              <div>
                <p className="text-sm font-bold">
                  {stats.is_praticien ? 'Votre compte praticien est en attente de validation' : 'Votre établissement n’est pas encore visible'}
                </p>
                <p className="mt-1 text-xs leading-relaxed">
                  Un administrateur activera votre profil après vérification. Vous pouvez déjà configurer vos actes et vos disponibilités.
                </p>
              </div>
            </div>
          )}
          {stats.pending_devis > 0 && (
            <a href="/sante/prestataire/devis/" className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-900 hover:bg-orange-100">
              <span><strong>{stats.pending_devis} demande(s) de devis</strong> en attente depuis plus de 24 h.</span>
              <span className="font-bold">Voir les demandes →</span>
            </a>
          )}
          {stats.rdv_requested_count > 0 && (
            <a href="/rdv/pro/agenda/" className="mb-5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900 hover:bg-sky-100">
              <span><strong>{stats.rdv_requested_count} rendez-vous</strong> en attente de confirmation.</span>
              <span className="font-bold">Voir les rendez-vous →</span>
            </a>
          )}

          <Card className="mb-7 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold text-gray-700">
                Complétion {stats.is_praticien ? 'du compte' : 'du profil'} · <strong>{stats.completion_pct}%</strong>
              </p>
              <span className="text-[11px] text-gray-400">{stats.completion_done} / {stats.completion_total} étapes</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-100">
              <div className="h-full rounded-full bg-[#0a5c8a] transition-all" style={{ width: `${stats.completion_pct}%` }} />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {stats.completion.map((item) => (
                <span key={item.label} className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${item.complete ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-700'}`}>
                  {item.complete ? '✓' : '×'} {item.label}
                </span>
              ))}
            </div>
          </Card>

          <div className={`mb-7 grid grid-cols-1 gap-4 sm:grid-cols-2 ${stats.is_praticien ? 'lg:grid-cols-3' : 'lg:grid-cols-4'}`}>
            {!stats.is_praticien && (
              <StatCard title="Vues du profil" value={stats.views_period} subtitle={`${stats.period_label} · ${stats.profile_views_total} au total`} icon={<Eye size={20} />} index={0} />
            )}
            <StatCard title="Demandes de devis" value={stats.devis_period} subtitle={`${stats.pending_devis} en attente depuis plus de 24 h`} icon={<MessageSquare size={20} />} index={1} />
            <StatCard title="Lignes de panier" value={stats.items_period} subtitle={`${stats.period_label} · actes ajoutés`} icon={<Activity size={20} />} index={2} />
            <StatCard title="Valeur potentielle" value={formatCurrency(stats.devis_value)} subtitle="Montant estimé, pas un chiffre d’affaires" icon={<DollarSign size={20} />} index={3} />
          </div>

          <div className="mb-7 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card className="p-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-syne text-base font-bold text-navy dark:text-white">
                      {stats.is_praticien ? 'Activité du compte' : 'Activité du profil'}
                    </h2>
                    <p className="mt-0.5 text-[11px] text-gray-400">{metricLabel} · {stats.activity_chart.period_sub}</p>
                  </div>
                  <select
                    value={metric}
                    onChange={(event) => setMetric(event.target.value as ActivityMetric)}
                    className="rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-gray-700"
                    aria-label="Indicateur d’activité"
                  >
                    {ACTIVITY_METRICS.filter((item) => !item.structuresOnly || !stats.is_praticien).map((item) => (
                      <option key={item.key} value={item.key}>{item.label}</option>
                    ))}
                  </select>
                </div>
                <ActivityChart data={chartData} title={metricLabel} />
                <a href="/sante/prestataire/bilan/" className="mt-3 block rounded-xl border border-gray-200 px-4 py-2.5 text-center text-xs font-semibold text-gray-600 hover:bg-gray-50">
                  Voir le bilan KPI
                </a>
              </Card>
            </div>

            <Card className="p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="font-syne text-base font-bold text-navy dark:text-white">Top actes demandés</h2>
                  <p className="mt-1 text-[11px] text-gray-400">Par volume de demandes</p>
                </div>
                <FlaskConical size={20} className="text-accent" aria-hidden="true" />
              </div>
              {stats.top_actes.length ? (
                <ol className="divide-y divide-gray-100">
                  {stats.top_actes.map((item, index) => (
                    <li key={`${item.name}-${index}`} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="flex min-w-0 items-center gap-2 text-sm font-semibold text-gray-800">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-gray-100 text-[11px] text-gray-500">{index + 1}</span>
                          <span className="truncate">{item.name}</span>
                        </span>
                        <span className="shrink-0 text-xs font-bold text-[#0a5c8a]">{Math.round(item.price).toLocaleString('fr-FR')} F</span>
                      </div>
                      <p className="mt-1 pl-8 text-[11px] text-gray-500">{item.count} demande(s)</p>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="py-8 text-center text-sm text-gray-400">Aucune demande sur cette période.</p>
              )}
            </Card>
          </div>

          <div className="mb-7 grid gap-6 lg:grid-cols-2">
            {!stats.is_praticien && (
              <Card className="overflow-hidden">
                <div className="border-b border-gray-100 px-5 py-4">
                  <h2 className="font-syne text-base font-bold text-navy dark:text-white">Profil public</h2>
                  <p className="mt-1 text-[11px] text-gray-500">Aperçu de la fiche consultée par les patients</p>
                </div>
                <div className="flex items-start gap-4 p-5">
                  {stats.org_logo ? (
                    <img src={stats.org_logo} alt="" className="size-16 shrink-0 rounded-xl border border-gray-200 object-cover" />
                  ) : (
                    <span className="flex size-16 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-xl font-bold text-[#0a5c8a]">{stats.org_name.charAt(0).toUpperCase()}</span>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-gray-900">{stats.org_name}</h3>
                      {stats.is_verified && <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-700"><ShieldCheck size={12} /> Vérifié</span>}
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${stats.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                        {stats.is_active ? 'Actif' : 'En attente'}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500"><Building2 size={13} className="mr-1 inline" />{[stats.org_city, stats.org_quartier].filter(Boolean).join(', ')}</p>
                    <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-gray-600">{stats.org_description || 'Aucune description renseignée.'}</p>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-600">
                      <span>{stats.actes_count} acte(s)</span>
                      <span>{stats.insurances_count} assurance(s)</span>
                      <span>{stats.profile_views_total} vue(s)</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <a href={stats.profile_url} target="_blank" rel="noreferrer" className="rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white">Voir le profil public ↗</a>
                      <a href={stats.edit_profile_url} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50">Modifier le profil</a>
                    </div>
                  </div>
                </div>
              </Card>
            )}

            <Card className="overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4">
                <div>
                  <h2 className="font-syne text-base font-bold text-navy dark:text-white">Dernières visites</h2>
                  <p className="mt-1 text-[11px] text-gray-500">Visiteurs récents de votre fiche</p>
                </div>
                <select
                  value={visitSource}
                  onChange={(event) => {
                    updateQueryValue('visit_src', event.target.value);
                    setLoading(true);
                    setVisitSource(event.target.value);
                  }}
                  className="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-[11px] font-semibold text-gray-600"
                  aria-label="Filtrer les visites par source"
                >
                  {VISIT_SOURCES.map((source) => <option key={source.key} value={source.key}>{source.label}</option>)}
                </select>
              </div>
              {stats.recent_views.length ? (
                <ul className="divide-y divide-gray-50">
                  {stats.recent_views.map((visit, index) => (
                    <li key={`${visit.meta}-${index}`} className="flex items-center gap-3 px-5 py-3">
                      <span className={`size-2 shrink-0 rounded-full ${visit.dot_class}`} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-gray-800">{visit.action}</span>
                        <span className="block text-[11px] text-gray-400">{visit.meta}</span>
                      </span>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${visit.badge_class}`}>{visit.label}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="px-5 py-8 text-center text-sm text-gray-400">Aucune visite récente.</p>
              )}
            </Card>
          </div>

          {!stats.is_praticien && (
            <div className="mb-7 grid gap-6 lg:grid-cols-2">
              <Card className="overflow-hidden">
                <div className="border-b border-gray-100 px-5 py-4">
                  <h2 className="font-syne text-base font-bold text-navy dark:text-white">Répartition par assurance</h2>
                  <p className="mt-1 text-[11px] text-gray-500">Sur {stats.insurance_split_total} panier(s) concernés</p>
                </div>
                {stats.insurance_split.length ? (
                  <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-3">
                    {stats.insurance_split.map((item) => (
                      <div key={item.name} className="text-center">
                        <p className="text-xl font-extrabold text-[#0a5c8a]">{item.count}</p>
                        <p className="mt-1 text-xs text-gray-500">{item.name}</p>
                        <p className="text-[10px] font-semibold text-[#0a5c8a]">{item.pct}%</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="px-5 py-8 text-center text-sm text-gray-400">Pas encore de panier sur cette période.</p>}
              </Card>

              <Card className="overflow-hidden">
                <div className="border-b border-gray-100 px-5 py-4">
                  <h2 className="font-syne text-base font-bold text-navy dark:text-white">MedPlaque NFC</h2>
                  <p className="mt-1 text-[11px] text-gray-500">Activité de votre plaque · {stats.medplaque.reference}</p>
                </div>
                <div className="grid grid-cols-3 gap-3 p-5 text-center">
                  <div><p className="text-2xl font-extrabold text-violet-600">{stats.medplaque.nfc_scans}</p><p className="text-[10px] text-gray-500">Scans NFC</p></div>
                  <div><p className="text-2xl font-extrabold text-blue-600">{stats.medplaque.qr_scans}</p><p className="text-[10px] text-gray-500">Scans QR</p></div>
                  <div><p className="text-2xl font-extrabold text-[#0a5c8a]">{stats.medplaque.total_access}</p><p className="text-[10px] text-gray-500">Total accès</p></div>
                </div>
                <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3">
                  <span className={`text-xs font-semibold ${stats.medplaque.nfc_active ? 'text-emerald-700' : 'text-gray-500'}`}>
                    {stats.medplaque.nfc_active ? `NFC active · ${stats.medplaque.month_label}` : 'NFC inactive'}
                  </span>
                  <a href="/sante/prestataire/medplaque/" className="text-xs font-bold text-[#0a5c8a]">Voir détails →</a>
                </div>
              </Card>
            </div>
          )}

          <Card className="p-5">
            <h2 className="mb-4 font-syne text-base font-bold text-navy dark:text-white">Actions rapides</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <a href="/sante/prestataire/actes/ajouter/" className="flex items-center gap-3 rounded-xl border border-gray-100 p-3 hover:bg-sky-50">
                <FlaskConical size={19} className="text-[#0a5c8a]" aria-hidden="true" />
                <span><strong className="block text-sm text-gray-800">Ajouter un acte</strong><small className="text-xs text-gray-500">Catalogue de prestations</small></span>
              </a>
              <a href="/rdv/pro/agenda/" className="flex items-center gap-3 rounded-xl border border-gray-100 p-3 hover:bg-sky-50">
                <CalendarDays size={19} className="text-sky-600" aria-hidden="true" />
                <span><strong className="block text-sm text-gray-800">Rendez-vous</strong><small className="text-xs text-gray-500">{stats.rdv_upcoming_count} confirmé(s) à venir</small></span>
              </a>
              {stats.is_praticien ? (
                <a href="/sante/prestataire/tickets/" className="flex items-center gap-3 rounded-xl border border-gray-100 p-3 hover:bg-emerald-50">
                  <Ticket size={19} className="text-emerald-600" aria-hidden="true" />
                  <span><strong className="block text-sm text-gray-800">Tickets de prestation</strong><small className="text-xs text-gray-500">Créer un lien patient</small></span>
                </a>
              ) : (
                <a href="/sante/prestataire/assurances/" className="flex items-center gap-3 rounded-xl border border-gray-100 p-3 hover:bg-violet-50">
                  <ShieldCheck size={19} className="text-violet-600" aria-hidden="true" />
                  <span><strong className="block text-sm text-gray-800">Assurances</strong><small className="text-xs text-gray-500">Gérer les prises en charge</small></span>
                </a>
              )}
              <a href="/sante/prestataire/organisme/horaires/" className="flex items-center gap-3 rounded-xl border border-gray-100 p-3 hover:bg-sky-50">
                <Clock3 size={19} className="text-blue-600" aria-hidden="true" />
                <span><strong className="block text-sm text-gray-800">{stats.is_praticien ? 'Disponibilités' : 'Horaires'}</strong><small className="text-xs text-gray-500">Gérer vos créneaux</small></span>
              </a>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
