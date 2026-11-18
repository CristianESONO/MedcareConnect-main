import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Archive, ArrowLeft, CalendarDays, FileText, MessageCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import {
  providerDevisApi,
  type ProviderDevisEntry,
  type ProviderDevisList,
  type ProviderDevisStatus,
} from '../lib/api';

const FILTERS: { key: ProviderDevisStatus; label: string }[] = [
  { key: 'active', label: 'Actifs' },
  { key: 'sent', label: 'Nouveaux' },
  { key: 'viewed', label: 'Consultés' },
  { key: 'accepted', label: 'Acceptés' },
  { key: 'relanced', label: 'Relancés' },
  { key: 'expired', label: 'Expirés' },
  { key: 'archived', label: 'Archivés' },
  { key: 'all', label: 'Tous' },
];

const STATUS_CLASSES: Record<string, string> = {
  sent: 'bg-emerald-100 text-emerald-800',
  viewed: 'bg-blue-50 text-blue-700',
  relanced: 'bg-amber-100 text-amber-800',
  expired: 'bg-rose-50 text-rose-700',
  archived: 'bg-gray-200 text-gray-700',
};

function isProviderDevisStatus(value: string | null): value is ProviderDevisStatus {
  return FILTERS.some((filter) => filter.key === value);
}

function formatDate(value: string | null) {
  if (!value) return '';
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatAmount(value: string | number) {
  return Number(value).toLocaleString('fr-FR');
}

function statusLabel(entry: ProviderDevisEntry) {
  if (entry.is_accepted) return 'Accepté · RDV confirmé';
  return entry.status_label;
}

function entryStatusClass(entry: ProviderDevisEntry) {
  if (entry.is_accepted) return 'bg-blue-100 text-blue-800';
  return STATUS_CLASSES[entry.status] || 'bg-gray-100 text-gray-700';
}

function EntryActions({
  entry,
  status,
  onAction,
  pending,
}: {
  entry: ProviderDevisEntry;
  status: ProviderDevisStatus;
  onAction: (action: 'relance' | 'archive' | 'confirm' | 'decline', entry: ProviderDevisEntry) => void;
  pending: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
      <Link
        to={`${entry.detail_url}?status=${status}`}
        className="rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white hover:bg-[#084c73]"
      >
        Ouvrir la fiche
      </Link>
      {entry.thread_url && (
        <a href={entry.thread_url} className="inline-flex items-center gap-1.5 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-800">
          <MessageCircle size={14} aria-hidden="true" /> Fil messagerie
        </a>
      )}
      {entry.show_confirm && entry.pending_rdv && (
        <>
          <button type="button" disabled={pending} onClick={() => onAction('confirm', entry)} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">
            Confirmer le RDV
          </button>
          <button type="button" disabled={pending} onClick={() => onAction('decline', entry)} className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-bold text-rose-800 disabled:opacity-50">
            Refuser
          </button>
        </>
      )}
      {entry.is_accepted && entry.active_rdv && (
        <a href="/rdv/pro/agenda/?status=upcoming" className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-800">
          <CalendarDays size={14} aria-hidden="true" /> RDV {entry.active_rdv.reference}
        </a>
      )}
      {entry.show_relance && (
        <button type="button" disabled={pending} onClick={() => onAction('relance', entry)} className="inline-flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-2 text-xs font-bold text-amber-900 disabled:opacity-50">
          <RefreshCw size={13} aria-hidden="true" /> Relancer ({entry.relance_count}/{entry.max_relances})
        </button>
      )}
      {!entry.show_relance && entry.status !== 'archived' && !entry.can_relance && (
        <span className="rounded-lg bg-gray-100 px-3 py-2 text-xs font-bold text-gray-400">Relances épuisées</span>
      )}
      {entry.status !== 'archived' && (
        <button type="button" disabled={pending} onClick={() => onAction('archive', entry)} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-bold text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          <Archive size={13} aria-hidden="true" /> Archiver
        </button>
      )}
    </div>
  );
}

function ProviderDevisListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedStatus = searchParams.get('status');
  const status = isProviderDevisStatus(requestedStatus) ? requestedStatus : 'active';
  const page = Math.max(1, Number(searchParams.get('page')) || 1);
  const [data, setData] = useState<ProviderDevisList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyReference, setBusyReference] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    providerDevisApi.list(status, page, controller.signal)
      .then((response) => {
        setData(response);
        setError('');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les devis.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [status, page, refreshKey]);

  const updateFilter = (nextStatus: ProviderDevisStatus) => {
    setLoading(true);
    setSearchParams({ status: nextStatus });
  };

  const runAction = async (
    action: 'relance' | 'archive' | 'confirm' | 'decline',
    entry: ProviderDevisEntry,
  ) => {
    if (action === 'archive' && !window.confirm(`Archiver le sous-devis ${entry.reference} ?`)) return;
    if (action === 'decline' && !window.confirm('Refuser le créneau de rendez-vous ?')) return;
    setBusyReference(entry.reference);
    setError('');
    try {
      if (action === 'relance') await providerDevisApi.relance(entry.reference, status);
      if (action === 'archive') await providerDevisApi.archive(entry.reference, status);
      if (action === 'confirm' && entry.pending_rdv) {
        await providerDevisApi.appointmentAction(entry.pending_rdv.reference, 'confirm');
      }
      if (action === 'decline' && entry.pending_rdv) {
        await providerDevisApi.appointmentAction(entry.pending_rdv.reference, 'decline');
      }
      setRefreshKey((current) => current + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Cette action n’a pas pu être effectuée.');
    } finally {
      setBusyReference('');
    }
  };

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace prestataire</p>
          <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Devis reçus</h1>
          <p className="mt-1 text-sm text-gray-500">Demandes générées par les patients via MedCare.</p>
        </div>
        <Link to="/sante/prestataire/tableau-de-bord/" className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#0a5c8a] hover:bg-sky-50">
          Tableau de bord
        </Link>
      </header>

      {data && (
        <div className="mt-5 grid grid-cols-2 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm sm:grid-cols-4">
          <div className="border-b border-r border-gray-100 p-4 text-center sm:border-b-0"><p className="text-2xl font-extrabold text-[#0a5c8a]">{data.kpis.active}</p><p className="mt-1 text-xs text-gray-500">Devis en cours</p></div>
          <div className="border-b border-gray-100 p-4 text-center sm:border-b-0 sm:border-r"><p className="text-2xl font-extrabold text-emerald-600">{data.kpis.new}</p><p className="mt-1 text-xs text-gray-500">Nouveaux</p></div>
          <div className="border-r border-gray-100 p-4 text-center"><p className="text-2xl font-extrabold text-amber-600">{data.kpis.accepted}</p><p className="mt-1 text-xs text-gray-500">Acceptés · RDV confirmé</p></div>
          <div className="p-4 text-center"><p className="text-lg font-extrabold text-[#0a5c8a]">{formatAmount(data.kpis.total_value)} FCFA</p><p className="mt-1 text-xs text-gray-500">Valeur totale active</p></div>
        </div>
      )}

      {data && (
        <nav className="mt-5 flex gap-1.5 overflow-x-auto rounded-xl border border-gray-200 bg-white p-1.5 shadow-sm" aria-label="Filtrer les devis">
          {FILTERS.map((filter) => (
            <button
              type="button"
              key={filter.key}
              onClick={() => updateFilter(filter.key)}
              aria-pressed={status === filter.key}
              className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold transition ${status === filter.key ? 'bg-[#0a5c8a] text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              {filter.label} <span className="ml-1 opacity-75">{data.counts[filter.key] || 0}</span>
            </button>
          ))}
        </nav>
      )}

      {loading && <p className="mt-5 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement des devis…</p>}
      {error && <p className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}

      {!loading && !error && data && (
        <>
          <div className="mt-5 space-y-3">
            {data.entries.length ? data.entries.map((entry) => (
              <article key={entry.reference} className={`rounded-2xl border bg-white p-4 shadow-sm sm:p-5 ${entry.status === 'sent' ? 'border-emerald-300 bg-emerald-50/20' : entry.status === 'archived' ? 'border-gray-200 opacity-80' : entry.status === 'relanced' ? 'border-amber-200' : 'border-gray-200'}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[10px] font-semibold text-gray-500">Devis {entry.parent_reference}</span>
                      <span className="font-mono text-xs font-bold text-[#0a5c8a]">{entry.reference}</span>
                      <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase ${entryStatusClass(entry)}`}>{statusLabel(entry)}</span>
                      {entry.valid_until && <span className="text-[11px] text-gray-400">Valide jusqu’au {formatDate(entry.valid_until)}</span>}
                    </div>
                    <p className="mt-2 text-sm font-semibold text-gray-900">
                      {entry.patient}{entry.insurance && <span className="ml-1 text-xs font-medium text-gray-500">· {entry.insurance}</span>}
                    </p>
                    <p className="text-[11px] text-gray-400">
                      Sous-devis · {formatDate(entry.created_at)}
                      {entry.last_relanced_at && ` · Dernière relance ${formatDate(entry.last_relanced_at)}`}
                      {entry.archived_at && ` · Archivé ${formatDate(entry.archived_at)}`}
                    </p>
                    <p className={`mt-2 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ${entry.creneau ? 'bg-blue-50 text-blue-700' : 'border border-amber-200 bg-amber-50 text-amber-800'}`}>
                      <CalendarDays size={13} aria-hidden="true" />
                      {entry.creneau ? `Créneau demandé : ${entry.creneau}` : 'Aucun créneau choisi par le patient'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400">Votre part</p>
                    <p className="text-lg font-extrabold text-[#0a5c8a]">{formatAmount(entry.subtotal)} F</p>
                    <p className="text-[11px] text-gray-400">{entry.items_count} acte(s)</p>
                  </div>
                </div>
                {!!entry.items.length && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {entry.items.map((item, index) => (
                      <span key={`${item.acte}-${index}`} className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[11px] text-gray-700">
                        {item.acte}{item.quantity > 1 && <span className="text-gray-400">×{item.quantity}</span>}
                        <span className="text-gray-400">·</span><strong>{formatAmount(item.subtotal)} F</strong>
                      </span>
                    ))}
                  </div>
                )}
                {entry.archived_reason && <p className="mt-2 text-xs text-gray-500">Motif d’archivage : {entry.archived_reason}</p>}
                {entry.status !== 'archived' && (
                  <div className="mt-3">
                    <EntryActions entry={entry} status={status} onAction={runAction} pending={busyReference === entry.reference} />
                  </div>
                )}
              </article>
            )) : (
              <div className="rounded-2xl border-2 border-dashed border-gray-200 bg-white py-14 text-center">
                <FileText size={30} className="mx-auto text-gray-300" aria-hidden="true" />
                <h2 className="mt-3 text-sm font-semibold text-gray-700">Aucun devis pour ce filtre.</h2>
                <p className="mt-1 text-xs text-gray-400">Les demandes de devis des patients apparaîtront ici.</p>
              </div>
            )}
          </div>

          {data.pagination.pages > 1 && (
            <nav className="mt-6 flex items-center justify-center gap-3" aria-label="Pagination">
              <button type="button" disabled={!data.pagination.has_previous} onClick={() => { setLoading(true); setSearchParams({ status, page: String(data.pagination.previous) }); }} className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 disabled:opacity-40">← Précédent</button>
              <span className="rounded-xl bg-gray-100 px-4 py-2 text-sm font-semibold">{data.pagination.page} / {data.pagination.pages}</span>
              <button type="button" disabled={!data.pagination.has_next} onClick={() => { setLoading(true); setSearchParams({ status, page: String(data.pagination.next) }); }} className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 disabled:opacity-40">Suivant →</button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}

function ProviderDevisDetailPage({ reference }: { reference: string }) {
  const [searchParams] = useSearchParams();
  const status = isProviderDevisStatus(searchParams.get('status')) ? searchParams.get('status') as ProviderDevisStatus : 'active';
  const [entry, setEntry] = useState<ProviderDevisEntry | null>(null);
  const [validUntil, setValidUntil] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    providerDevisApi.detail(reference, controller.signal)
      .then((data) => {
        setEntry(data.entry);
        setValidUntil(data.devis.valid_until);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger le détail du devis.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reference]);

  const runAction = async (action: 'relance' | 'archive' | 'confirm' | 'decline') => {
    if (!entry) return;
    if (action === 'archive' && !window.confirm(`Archiver le sous-devis ${entry.reference} ?`)) return;
    if (action === 'decline' && !window.confirm('Refuser le créneau de rendez-vous ?')) return;
    setBusy(true);
    setError('');
    try {
      if (action === 'relance') await providerDevisApi.relance(entry.reference, status);
      if (action === 'archive') await providerDevisApi.archive(entry.reference, status);
      if (action === 'confirm' && entry.pending_rdv) await providerDevisApi.appointmentAction(entry.pending_rdv.reference, 'confirm');
      if (action === 'decline' && entry.pending_rdv) await providerDevisApi.appointmentAction(entry.pending_rdv.reference, 'decline');
      const fresh = await providerDevisApi.detail(reference);
      setEntry(fresh.entry);
      setValidUntil(fresh.devis.valid_until);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Cette action n’a pas pu être effectuée.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <Link to={`/sante/prestataire/devis/?status=${status}`} className="inline-flex items-center gap-2 text-sm font-semibold text-[#0a5c8a] hover:underline">
        <ArrowLeft size={16} aria-hidden="true" /> Retour aux devis
      </Link>
      {loading && <p className="mt-5 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement du devis…</p>}
      {error && <p className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {entry && (
        <>
          <header className="mt-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs text-gray-500">Devis patient <strong className="font-mono text-[#0a5c8a]">{entry.parent_reference}</strong></p>
              <h1 className="mt-1 font-mono text-2xl font-extrabold text-[#123a63]">{entry.reference}</h1>
              <p className="mt-1 text-sm text-gray-600">{entry.patient}{entry.insurance && ` · ${entry.insurance}`}</p>
            </div>
            <span className={`rounded-full px-3 py-1.5 text-xs font-bold ${entryStatusClass(entry)}`}>{statusLabel(entry)}</span>
          </header>

          {entry.creneau && (
            <p className="mt-5 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-800">
              <CalendarDays size={16} className="mr-2 inline" aria-hidden="true" />
              Créneau souhaité : {entry.creneau}{entry.show_confirm && ' · en attente de votre confirmation'}
            </p>
          )}
          {!entry.creneau && entry.status !== 'archived' && !entry.is_accepted && (
            <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Aucun créneau choisi par le patient — vous pouvez le contacter par la messagerie.</p>
          )}

          <div className="mt-5 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-100 bg-gray-50 px-5 py-3 text-xs font-bold uppercase tracking-wide text-gray-500">Actes concernant votre structure</div>
            <div className="divide-y divide-gray-100">
              {entry.items.length ? entry.items.map((item, index) => (
                <div key={`${item.acte}-${index}`} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                  <div><p className="text-sm font-semibold text-gray-900">{item.acte}</p><p className="text-xs text-gray-400">Quantité {item.quantity}</p></div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-[#0a5c8a]">{formatAmount(item.subtotal)} XOF</p>
                    {item.coverage_rate !== null && <p className="text-xs text-gray-500">{item.coverage_rate}% pris en charge · reste patient {formatAmount(item.patient_cost)} XOF</p>}
                  </div>
                </div>
              )) : <p className="px-5 py-8 text-center text-sm text-gray-400">Aucune ligne.</p>}
            </div>
            <div className="flex flex-wrap justify-between gap-3 border-t border-gray-200 bg-gray-50 px-5 py-4 text-sm">
              <span className="text-gray-500">Total brut · votre part <strong className="ml-2 text-gray-900">{formatAmount(entry.subtotal)} XOF</strong></span>
              {entry.insurance && <span className="text-gray-500">Reste patient estimé <strong className="ml-2 text-[#0a5c8a]">{formatAmount(entry.total_patient)} XOF</strong></span>}
              {validUntil && <span className="w-full text-xs text-gray-400">Devis valide jusqu’au {formatDate(validUntil)}</span>}
            </div>
          </div>

          {entry.status !== 'archived' && (
            <div className="mt-5 rounded-2xl border border-gray-200 bg-white p-4">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-gray-400">Actions</p>
              <EntryActions entry={entry} status={status} onAction={(action) => void runAction(action)} pending={busy} />
              <p className="mt-3 text-[10px] text-gray-400">Deux relances maximum avant archivage automatique.</p>
            </div>
          )}
          {entry.thread_url && (
            <a href={entry.thread_url} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm font-semibold text-sky-800">
              <MessageCircle size={16} aria-hidden="true" /> Ouvrir le fil de discussion
            </a>
          )}
          {entry.is_accepted && <p className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-emerald-700"><ShieldCheck size={16} aria-hidden="true" /> Rendez-vous confirmé</p>}
        </>
      )}
    </section>
  );
}

export function ProviderDevisPage() {
  const { reference } = useParams();
  return reference
    ? <ProviderDevisDetailPage reference={reference} />
    : <ProviderDevisListPage />;
}
