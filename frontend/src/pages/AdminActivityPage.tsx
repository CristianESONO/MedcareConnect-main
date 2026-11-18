import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  adminActivityApi,
  type AdminActivityAppointment,
  type AdminActivityConversation,
  type AdminActivityQuote,
  type AdminReminderSchedule,
  type AdminReminderScheduleInput,
} from '../lib/adminActivityApi';
import { AdminWorkspaceHeader } from '../components/AdminWorkspaceHeader';

const links = [
  ['/dashboard/activite/', 'Vue activité'],
  ['/dashboard/devis/', 'Devis'],
  ['/dashboard/activite/rdv/', 'Rendez-vous'],
  ['/dashboard/activite/rdv/rappels/', 'Rappels RDV'],
  ['/dashboard/activite/messages/', 'Messagerie'],
];

const card = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm';
const button = 'inline-flex min-h-10 items-center justify-center rounded-lg border border-sky-800 bg-sky-800 px-4 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:opacity-50 dark:border-sky-400 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300';
const mutedButton = 'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 disabled:opacity-50';

function dateTime(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
}

function money(value: number) {
  return `${Number(value || 0).toLocaleString('fr-FR')} F`;
}

function AdminActivityShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <AdminWorkspaceHeader />
      <div className="mx-auto grid max-w-screen-2xl gap-5 p-4 lg:grid-cols-[230px_minmax(0,1fr)] lg:p-6">
        <nav className="h-fit rounded-2xl border border-slate-200 bg-white p-3 shadow-sm" aria-label="Activité administration">
          {links.map(([href, label]) => {
            const active = pathname === href
              || (href === '/dashboard/devis/' && pathname.startsWith('/dashboard/devis/'))
              || (href === '/dashboard/activite/rdv/' && pathname.startsWith('/dashboard/activite/rdv/'))
              || (href === '/dashboard/activite/messages/' && pathname.startsWith('/dashboard/activite/messages/'));
            return (
              <Link key={href} to={href} aria-current={active ? 'page' : undefined}
                className={`mb-1 block rounded-lg px-3 py-2 text-sm ${active ? 'bg-sky-50 font-semibold text-sky-900' : 'text-slate-600 hover:bg-slate-50'}`}>
                {label}
              </Link>
            );
          })}
        </nav>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Pilotage plateforme</p>
      <h1 className="mt-1 font-syne text-2xl font-extrabold">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}

function Feedback({ error, notice }: { error: string; notice?: string }) {
  return (
    <>
      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
    </>
  );
}

function Pagination({
  page, params, pathname,
}: {
  page: { page: number; pages: number; total: number; has_previous: boolean; has_next: boolean };
  params: URLSearchParams;
  pathname: string;
}) {
  const linkFor = (number: number) => {
    const next = new URLSearchParams(params);
    next.set('page', String(number));
    return `${pathname}?${next.toString()}`;
  };
  return (
    <div className="mt-4 flex items-center justify-between gap-3 text-sm text-slate-600">
      <span>{page.total} résultat(s) · page {page.page} / {Math.max(page.pages, 1)}</span>
      <div className="flex gap-2">
        <Link aria-disabled={!page.has_previous} to={linkFor(Math.max(1, page.page - 1))}
          className={`${mutedButton} ${!page.has_previous ? 'pointer-events-none opacity-40' : ''}`}>Précédent</Link>
        <Link aria-disabled={!page.has_next} to={linkFor(page.page + 1)}
          className={`${mutedButton} ${!page.has_next ? 'pointer-events-none opacity-40' : ''}`}>Suivant</Link>
      </div>
    </div>
  );
}

function useLoader<T>(loader: (signal: AbortSignal) => Promise<T>, dependencies: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const reload = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError('');
    try {
      setData(await loader(signal ?? new AbortController().signal));
    } catch (reason) {
      if (!signal?.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger les données.');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  // The caller supplies all query and route parameters as dependencies.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);
  return { data, loading, error, setError, reload };
}

function Loading({ loading }: { loading: boolean }) {
  return loading ? <p className={card} role="status">Chargement…</p> : null;
}

function Overview() {
  const { data, loading, error } = useLoader((signal) => adminActivityApi.overview(signal), []);
  return (
    <>
      <PageHeader title="Activité · Vue 360°" subtitle="Supervision des devis, rendez-vous et conversations." />
      <Feedback error={error} />
      <Loading loading={loading} />
      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[
              ['Devis', data.kpis.quotes_total, `${data.kpis.quotes_pending} en attente · ${data.kpis.quotes_expired} expirés`, money(data.kpis.quotes_value), '/dashboard/devis/'],
              ['Rendez-vous', data.kpis.appointments_total, `${data.kpis.appointments_requested} à confirmer · ${data.kpis.appointments_confirmed_upcoming} confirmés à venir`, `${data.kpis.appointments_completed_7d} honorés (7 j) · ${data.kpis.appointments_no_show} absents`, '/dashboard/activite/rdv/'],
              ['Messagerie', data.kpis.conversations_total, `${data.kpis.conversations_active} actifs · ${data.kpis.conversations_waiting} en attente`, `${data.kpis.messages_7d} messages sur 7 jours`, '/dashboard/activite/messages/'],
            ].map(([label, total, hint, detail, href]) => (
              <Link key={String(label)} to={String(href)} className={`${card} transition hover:border-sky-300`}>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-2 text-3xl font-bold">{Number(total).toLocaleString('fr-FR')}</p>
                <p className="mt-1 text-sm text-slate-500">{hint}</p>
                <p className="mt-2 text-sm font-semibold text-sky-800">{detail}</p>
                <span className="mt-3 block text-xs font-semibold text-sky-700">Voir le registre →</span>
              </Link>
            ))}
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-3">
            <RecentQuotes rows={data.recent_quotes} />
            <RecentAppointments rows={data.recent_appointments} />
            <RecentConversations rows={data.recent_conversations} />
          </div>
        </>
      )}
    </>
  );
}

function RecentQuotes({ rows }: { rows: AdminActivityQuote[] }) {
  return (
    <section className={card}>
      <div className="flex justify-between"><h2 className="font-bold">Derniers devis</h2><Link to="/dashboard/devis/" className="text-xs text-sky-700">Tout voir</Link></div>
      <ul className="mt-3 divide-y divide-slate-100">
        {rows.map((quote) => <li key={quote.reference} className="py-2 text-sm">
          <Link to={`/dashboard/devis/${quote.reference}/`} className="font-mono font-semibold text-sky-800">{quote.reference}</Link>
          <span className="float-right text-xs text-slate-500">{quote.status_label}</span>
          <p className="text-xs text-slate-500">{quote.patient?.name}</p>
        </li>)}
        {!rows.length && <li className="py-5 text-sm text-slate-500">Aucun devis.</li>}
      </ul>
    </section>
  );
}

function RecentAppointments({ rows }: { rows: AdminActivityAppointment[] }) {
  return (
    <section className={card}>
      <div className="flex justify-between"><h2 className="font-bold">Derniers rendez-vous</h2><Link to="/dashboard/activite/rdv/" className="text-xs text-sky-700">Tout voir</Link></div>
      <ul className="mt-3 divide-y divide-slate-100">
        {rows.map((rdv) => <li key={rdv.reference} className="py-2 text-sm">
          <Link to={`/dashboard/activite/rdv/${rdv.reference}/`} className="font-mono font-semibold text-sky-800">{rdv.reference}</Link>
          <span className="float-right text-xs text-slate-500">{rdv.status_label}</span>
          <p className="text-xs text-slate-500">{rdv.patient_label} · {rdv.organization.name}</p>
        </li>)}
        {!rows.length && <li className="py-5 text-sm text-slate-500">Aucun rendez-vous.</li>}
      </ul>
    </section>
  );
}

function RecentConversations({ rows }: { rows: AdminActivityConversation[] }) {
  return (
    <section className={card}>
      <div className="flex justify-between"><h2 className="font-bold">Dernières conversations</h2><Link to="/dashboard/activite/messages/" className="text-xs text-sky-700">Tout voir</Link></div>
      <ul className="mt-3 divide-y divide-slate-100">
        {rows.map((conversation) => <li key={conversation.id} className="py-2 text-sm">
          <Link to={`/dashboard/activite/messages/${conversation.id}/`} className="font-semibold text-sky-800">{conversation.label}</Link>
          <p className="text-xs text-slate-500">{conversation.patient.name} · {conversation.message_count} msg</p>
        </li>)}
        {!rows.length && <li className="py-5 text-sm text-slate-500">Aucune conversation.</li>}
      </ul>
    </section>
  );
}

function QuotesList() {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status') || 'all';
  const q = searchParams.get('q') || '';
  const page = Math.max(1, Number(searchParams.get('page') || 1));
  const { data, loading, error } = useLoader(
    (signal) => adminActivityApi.quotes({ status, q, page }, signal),
    [status, q, page],
  );
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams(search);
    const form = new FormData(event.currentTarget);
    const nextQ = String(form.get('q') || '').trim();
    const nextStatus = String(form.get('status') || 'all');
    params.delete('page');
    nextQ ? params.set('q', nextQ) : params.delete('q');
    nextStatus === 'all' ? params.delete('status') : params.set('status', nextStatus);
    navigate(`${pathname}?${params.toString()}`);
  };
  const statuses = [['all', 'Tous'], ['sent', 'Nouveau'], ['viewed', 'Consulté'], ['relanced', 'Relancé'], ['expired', 'Expiré'], ['archived', 'Archivés']];
  return (
    <>
      <PageHeader title="Devis WhatsApp" subtitle="Registre consolidé et cycle de relance des devis." />
      <Feedback error={error} />
      {data && <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ['Total générés', data.kpis.total], ['Consultés', data.kpis.consulted],
          ['En attente réponse', data.kpis.pending], ['Expirés', data.kpis.expired], ['Valeur (FCFA)', money(data.kpis.value)],
        ].map(([label, value]) => <div key={String(label)} className={card}><p className="text-xs uppercase text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>)}
      </div>}
      <Loading loading={loading} />
      {!loading && data && <section className={card}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1">
            {statuses.map(([value, label]) => <Link key={value} to={`${pathname}?${new URLSearchParams({ ...(q ? { q } : {}), ...(value !== 'all' ? { status: value } : {}) })}`}
              className={`rounded-lg px-3 py-2 text-xs font-semibold ${status === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}>
              {label} <span className="opacity-70">{data.counts[value]}</span>
            </Link>)}
          </div>
          <form onSubmit={submit} className="flex gap-2">
            <input name="status" type="hidden" value={status} />
            <input name="q" defaultValue={q} placeholder="Réf. ou patient…" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button className={button}>Rechercher</button>
          </form>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Réf.', 'Patient', 'Structure(s)', 'Sous-devis', 'Valeur', 'Généré le', 'Statut'].map((x) => <th key={x} className="p-3">{x}</th>)}<th className="p-3">Actions</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {data.rows.map((quote) => <tr key={quote.reference}>
                <td className="p-3 font-mono font-semibold"><Link className="text-sky-800" to={`/dashboard/devis/${quote.reference}/`}>{quote.reference}</Link></td>
                <td className="p-3">{quote.patient?.name}<small className="block text-xs text-slate-500">{quote.patient?.email}</small></td>
                <td className="p-3 text-xs">{quote.organizations?.join(', ') || '—'}</td>
                <td className="p-3 text-center">{quote.parts_count || 0}</td>
                <td className="p-3">{money(quote.total_brut)}</td><td className="p-3 text-xs">{dateTime(quote.created_at)}</td><td className="p-3">{quote.status_label}</td>
                <td className="p-3"><Link to={`/dashboard/devis/${quote.reference}/`} className="font-semibold text-sky-800">Détail →</Link></td>
              </tr>)}
              {!data.rows.length && <tr><td colSpan={8} className="p-8 text-center text-slate-500">Aucun devis pour ce filtre.</td></tr>}
            </tbody>
          </table>
        </div>
        <Pagination page={data.pagination} params={searchParams} pathname={pathname} />
        <p className="mt-4 text-xs text-slate-400">Chaque devis peut être relancé 2 fois maximum, puis archivé automatiquement.</p>
      </section>}
    </>
  );
}

function QuoteDetail({ reference }: { reference: string }) {
  const navigate = useNavigate();
  const { data, loading, error, setError, reload } = useLoader((signal) => adminActivityApi.quote(reference, signal), [reference]);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const action = async (value: 'relance' | 'archive') => {
    setBusy(true); setError(''); setNotice('');
    try {
      const response = await adminActivityApi.quoteAction(reference, value);
      setNotice(response.message);
      await reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de modifier le devis.');
    } finally { setBusy(false); }
  };
  const quote = data?.quote;
  return (
    <>
      <PageHeader title={`Devis · ${reference}`} />
      <Feedback error={error} notice={notice} />
      <Loading loading={loading} />
      {quote && <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(250px,1fr)]">
        <div className="space-y-4">
          <section className={card}>
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-mono text-lg font-bold text-sky-800">{quote.reference}</p><p className="mt-1 text-sm text-slate-600">{quote.patient?.name} · {quote.patient?.email}</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold">{quote.status_label}</span></div>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <DetailField label="Généré le" value={dateTime(quote.created_at)} /><DetailField label="Valide jusqu'au" value={quote.valid_until || '—'} />
              <DetailField label="Assurance" value={quote.insurance?.name || '—'} /><DetailField label="Relances" value={`${quote.relance_count} / ${quote.max_relances}`} />
            </dl>
            <div className="mt-4 flex gap-2">
              {quote.can_relance && <button disabled={busy} onClick={() => void action('relance')} className={mutedButton}>Relancer</button>}
              {!quote.is_archived && <button disabled={busy} onClick={() => void action('archive')} className={mutedButton}>Archiver</button>}
              <button onClick={() => navigate('/dashboard/devis/')} className={mutedButton}>Retour au registre</button>
            </div>
          </section>
          <section className={card}>
            <h2 className="font-bold">Lignes du devis</h2>
            <ul className="mt-3 divide-y divide-slate-100">{quote.details.map((line, index) => <li key={index} className="flex justify-between gap-3 py-3 text-sm">
              <div><p className="font-medium">{String(line.acte || 'Acte')}</p><p className="text-xs text-slate-500">{String(line.organisme || '')} · qté {String(line.quantity || 1)}</p></div>
              <div className="text-right"><p className="font-semibold">{money(Number(line.subtotal || 0))}</p><p className="text-xs text-slate-500">patient {money(Number(line.patient_cost || 0))}</p></div>
            </li>)}</ul>
            <div className="mt-3 border-t pt-3 text-sm"><p className="flex justify-between"><span>Total brut</span><strong>{money(quote.total_brut)}</strong></p><p className="mt-1 flex justify-between"><span>Reste patient</span><strong>{money(quote.total_patient)}</strong></p></div>
          </section>
          {!!quote.parts?.length && <section className={card}><h2 className="font-bold">Sous-devis par structure</h2>
            <ul className="mt-3 space-y-3">{quote.parts.map((part) => <li key={part.id} className="rounded-lg bg-slate-50 p-4">
              <p className="font-semibold">{part.organization.name} <span className="ml-1 font-mono text-xs text-slate-500">{part.reference}</span></p>
              <p className="mt-1 text-sm text-slate-600">{part.status_label} · {money(part.total_brut)} · {part.relance_count} relance(s)</p>
              <div className="mt-2 flex gap-3 text-xs">{part.conversation && <Link className="text-sky-800" to={`/dashboard/activite/messages/${part.conversation.id}/`}>{part.conversation.label}</Link>}{part.appointment && <Link className="text-sky-800" to={`/dashboard/activite/rdv/${part.appointment.reference}/`}>RDV {part.appointment.reference}</Link>}</div>
            </li>)}</ul>
          </section>}
        </div>
        <aside className={card}><h2 className="font-bold">Patient</h2><p className="mt-2">{quote.patient?.name}</p><p className="text-xs text-slate-500">{quote.patient?.email}</p><Link to={`/dashboard/utilisateurs/?q=${encodeURIComponent(quote.patient?.email || '')}`} className="mt-3 inline-block text-xs text-sky-800">Voir dans Utilisateurs →</Link></aside>
      </div>}
    </>
  );
}

function AppointmentsList() {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status') || 'all';
  const q = searchParams.get('q') || '';
  const org = searchParams.get('org') || '';
  const page = Math.max(1, Number(searchParams.get('page') || 1));
  const { data, loading, error } = useLoader(
    (signal) => adminActivityApi.appointments({ status, q, org, page }, signal),
    [status, q, org, page],
  );
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const params = new URLSearchParams(search);
    params.delete('page');
    for (const key of ['q', 'org']) {
      const value = String(form.get(key) || '').trim();
      value ? params.set(key, value) : params.delete(key);
    }
    navigate(`${pathname}?${params.toString()}`);
  };
  const filters = [['all', 'Tous'], ['upcoming', 'À venir'], ['requested', 'Demandé'], ['confirmed', 'Confirmé'], ['completed', 'Honoré'], ['no_show', 'Absent'], ['cancelled', 'Annulé']];
  return (
    <>
      <PageHeader title="Activité · Rendez-vous" subtitle="Registre consolidé des rendez-vous plateforme." />
      <Feedback error={error} />
      {data && <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ['Total RDV', data.kpis.appointments_total], ['À confirmer', data.kpis.appointments_requested],
          ['Confirmés à venir', data.kpis.appointments_confirmed_upcoming], ['Honorés (7 j)', data.kpis.appointments_completed_7d],
          ['Absents', data.kpis.appointments_no_show],
        ].map(([label, value]) => <div key={String(label)} className={card}><p className="text-xs uppercase text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>)}
      </div>}
      <Loading loading={loading} />
      {!loading && data && <section className={card}>
        <div className="mb-4 flex flex-wrap justify-between gap-3">
          <div className="flex flex-wrap gap-1">{filters.map(([value, label]) => <Link key={value} to={`${pathname}?${new URLSearchParams({ ...(q ? { q } : {}), ...(org ? { org } : {}), ...(value !== 'all' ? { status: value } : {}) })}`} className={`rounded-lg px-3 py-2 text-xs font-semibold ${status === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}>{label} <span className="opacity-70">{data.counts[value]}</span></Link>)}</div>
          <form onSubmit={submit} className="flex gap-2"><input name="q" defaultValue={q} placeholder="Réf., patient, devis…" className="w-48 rounded-lg border border-slate-300 px-3 py-2 text-sm" /><input name="org" defaultValue={org} placeholder="ID structure" className="w-28 rounded-lg border border-slate-300 px-3 py-2 text-sm" /><button className={button}>Filtrer</button></form>
        </div>
        <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Réf.', 'Patient', 'Structure', 'Créneau', 'Source', 'Devis lié', 'Statut'].map((x) => <th key={x} className="p-3">{x}</th>)}<th className="p-3" /></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.rows.map((rdv) => <tr key={rdv.reference}>
            <td className="p-3 font-mono font-semibold">{rdv.reference}</td><td className="p-3">{rdv.patient_label}<small className="block text-xs text-slate-500">{rdv.patient_phone}</small></td><td className="p-3">{rdv.organization.name}</td><td className="p-3 text-xs">{dateTime(rdv.start)}</td><td className="p-3 text-xs">{rdv.source_label}</td><td className="p-3 font-mono text-xs">{rdv.devis_reference || '—'}</td><td className="p-3">{rdv.status_label}</td><td className="p-3"><Link className="font-semibold text-sky-800" to={`/dashboard/activite/rdv/${rdv.reference}/`}>Détail →</Link></td>
          </tr>)}{!data.rows.length && <tr><td colSpan={8} className="p-8 text-center text-slate-500">Aucun rendez-vous pour ce filtre.</td></tr>}</tbody>
        </table></div>
        <Pagination page={data.pagination} params={searchParams} pathname={pathname} />
      </section>}
    </>
  );
}

function DetailField({ label, value }: { label: string; value: ReactNode }) {
  return <div><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-0.5">{value}</dd></div>;
}

function AppointmentDetail({ reference }: { reference: string }) {
  const { data, loading, error } = useLoader((signal) => adminActivityApi.appointment(reference, signal), [reference]);
  const rdv = data?.appointment;
  return (
    <>
      <PageHeader title={`Rendez-vous · ${reference}`} />
      <Feedback error={error} />
      <Loading loading={loading} />
      {rdv && <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(250px,1fr)]">
        <div className="space-y-4">
          <section className={card}>
            <div className="flex justify-between gap-3"><div><p className="font-mono text-lg font-bold text-sky-800">{rdv.reference}</p><p className="mt-1 text-sm">{rdv.organization.name}</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold">{rdv.status_label}</span></div>
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
              <DetailField label="Patient" value={rdv.patient_label} /><DetailField label="Téléphone" value={rdv.patient_phone || '—'} />
              <DetailField label="Créneau" value={`${dateTime(rdv.start)}${rdv.end ? ` → ${new Date(rdv.end).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}` : ''}`} /><DetailField label="Source" value={rdv.source_label} />
              <DetailField label="Créé le" value={dateTime(rdv.created_at)} /><DetailField label="Confirmé le" value={dateTime(rdv.confirmed_at)} />
              <DetailField label="Montant brut" value={money(rdv.total_brut)} /><DetailField label="Part patient" value={money(rdv.total_patient)} />
            </dl>
            {rdv.patient_note && <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs"><strong>Note patient :</strong> {rdv.patient_note}</p>}
            {rdv.prestataire_note && <p className="mt-2 rounded-lg bg-slate-50 p-3 text-xs"><strong>Note structure :</strong> {rdv.prestataire_note}</p>}
            {rdv.cancel_reason && <p className="mt-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-800"><strong>Annulation :</strong> {rdv.cancel_reason}</p>}
          </section>
          {!!rdv.actes_snapshot?.length && <section className={card}><h2 className="font-bold">Actes (snapshot)</h2><ul className="mt-3 space-y-2 text-sm">{rdv.actes_snapshot.map((act, index) => <li key={index} className="flex justify-between border-b border-slate-100 pb-2"><span>{String(act.acte || 'Acte')} {Number(act.quantity || 0) > 1 ? `×${act.quantity}` : ''}</span><span>{act.subtotal ? money(Number(act.subtotal)) : ''}</span></li>)}</ul></section>}
          {rdv.prerequisites && <section className="rounded-xl border border-amber-200 bg-amber-50 p-5"><h2 className="font-bold text-amber-900">Prérequis / consignes patient</h2><p className="mt-2 whitespace-pre-line text-sm">{rdv.prerequisites}</p></section>}
        </div>
        <aside className={card}><h2 className="font-bold">Parcours lié</h2><ul className="mt-3 space-y-3 text-sm">
          <li><span className="block text-xs text-slate-500">Structure</span>{rdv.organization.name}</li>
          {rdv.devis_reference && <li><span className="block text-xs text-slate-500">Devis</span><Link className="font-mono text-sky-800" to={`/dashboard/devis/${rdv.devis_reference}/`}>{rdv.devis_reference}</Link></li>}
          {rdv.devis_part_reference && <li><span className="block text-xs text-slate-500">Sous-devis</span>{rdv.devis_part_reference}</li>}
          {rdv.conversation && <li><span className="block text-xs text-slate-500">Discussion</span><Link className="text-sky-800" to={`/dashboard/activite/messages/${rdv.conversation.id}/`}>{rdv.conversation.label}</Link></li>}
          {!rdv.conversation && <li className="text-xs text-slate-500">Aucune discussion rattachée.</li>}
        </ul><p className="mt-5 text-xs text-slate-500">Les actions opérationnelles sont gérées dans l'agenda prestataire.</p></aside>
      </div>}
    </>
  );
}

function ReminderSchedules() {
  const navigate = useNavigate();
  const { data, loading, error, setError, reload } = useLoader((signal) => adminActivityApi.reminderSchedules(signal), []);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState<number | null>(null);
  const remove = async (id: number) => {
    setBusy(id); setError(''); setNotice('');
    try {
      const result = await adminActivityApi.deleteReminderSchedule(id);
      setNotice(result.message);
      await reload();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Suppression impossible.'); }
    finally { setBusy(null); }
  };
  return (
    <>
      <PageHeader title="Règles de rappel RDV" subtitle="Règles globales de rappel — les règles propres aux structures restent hors de cette administration." />
      <Feedback error={error} notice={notice} />
      <div className="mb-4 flex justify-end"><Link to="/dashboard/activite/rdv/rappels/ajouter/" className={button}>+ Nouvelle règle</Link></div>
      <Loading loading={loading} />
      {!loading && data && <section className={card}>
        <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Règle', 'Délai', 'Tolérance', 'Prérequis', 'Actes ciblés', 'Envoyés', 'Statut'].map((x) => <th key={x} className="p-3">{x}</th>)}<th className="p-3 text-right">Actions</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.rows.map((schedule) => <tr key={schedule.id}>
            <td className="p-3 font-medium">{schedule.label}</td><td className="p-3">{schedule.offset_display}</td><td className="p-3">± {schedule.tolerance_minutes} min</td><td className="p-3">{schedule.include_prerequisites ? 'Oui' : 'Non'}</td>
            <td className="p-3 text-xs">{schedule.actes.length ? `${schedule.actes.slice(0, 3).map((act) => act.name).join(', ')}${schedule.actes.length > 3 ? '…' : ''}` : 'Tous les RDV'}</td>
            <td className="p-3">{schedule.sent_count}</td><td className="p-3">{schedule.is_active ? 'Active' : 'Inactive'}</td>
            <td className="p-3 text-right whitespace-nowrap"><Link to={`/dashboard/activite/rdv/rappels/${schedule.id}/modifier/`} className="text-xs font-semibold text-sky-800">Modifier</Link><button disabled={busy === schedule.id} onClick={() => void remove(schedule.id)} className="ml-3 text-xs font-semibold text-red-700">Supprimer</button></td>
          </tr>)}{!data.rows.length && <tr><td colSpan={8} className="p-8 text-center text-slate-500">Aucune règle. Le cron n'enverra aucun rappel automatique.</td></tr>}</tbody>
        </table></div>
        <p className="mt-4 text-xs text-slate-500">Cron : <code className="rounded bg-slate-100 px-1">python manage.py send_rdv_reminders</code>.</p>
      </section>}
    </>
  );
}

function ReminderScheduleForm({ id }: { id?: number }) {
  const navigate = useNavigate();
  const [options, setOptions] = useState<{ id: number; name: string }[]>([]);
  const [initial, setInitial] = useState<AdminReminderSchedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    const schedulePromise = id ? adminActivityApi.reminderSchedule(id, controller.signal) : Promise.resolve(null);
    Promise.all([adminActivityApi.reminderSchedules(controller.signal), schedulePromise])
      .then(([list, item]) => { setOptions(list.act_options); setInitial(item?.schedule || null); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger la règle.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [id]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: AdminReminderScheduleInput = {
      label: String(form.get('label') || ''),
      offset_value: Number(form.get('offset_value') || 0),
      offset_unit: String(form.get('offset_unit') || 'days') as AdminReminderScheduleInput['offset_unit'],
      tolerance_minutes: Number(form.get('tolerance_minutes') || 0),
      include_prerequisites: form.get('include_prerequisites') === 'on',
      is_active: form.get('is_active') === 'on',
      order: Number(form.get('order') || 0),
      actes: form.getAll('actes').map(Number),
    };
    setBusy(true); setError('');
    try {
      if (id) await adminActivityApi.updateReminderSchedule(id, payload);
      else await adminActivityApi.createReminderSchedule(payload);
      navigate('/dashboard/activite/rdv/rappels/');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Enregistrement impossible.'); }
    finally { setBusy(false); }
  };
  const fieldClass = 'mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm';
  return (
    <>
      <PageHeader title={id ? 'Modifier une règle de rappel' : 'Nouvelle règle de rappel RDV'} />
      <Feedback error={error} />
      <Loading loading={loading} />
      {!loading && <form onSubmit={submit} className={`${card} mx-auto max-w-2xl space-y-4`}>
        <label className="block text-sm font-medium">Libellé<input required maxLength={80} name="label" defaultValue={initial?.label || ''} className={fieldClass} /></label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium">Délai<input required min={0} type="number" name="offset_value" defaultValue={initial?.offset_value ?? 1} className={fieldClass} /></label>
          <label className="block text-sm font-medium">Unité<select name="offset_unit" defaultValue={initial?.offset_unit || 'days'} className={fieldClass}><option value="minutes">Minutes avant</option><option value="hours">Heures avant</option><option value="days">Jours avant</option></select></label>
          <label className="block text-sm font-medium">Tolérance (minutes)<input required min={0} max={32767} type="number" name="tolerance_minutes" defaultValue={initial?.tolerance_minutes ?? 30} className={fieldClass} /></label>
          <label className="block text-sm font-medium">Ordre<input required min={0} type="number" name="order" defaultValue={initial?.order ?? 0} className={fieldClass} /></label>
        </div>
        <label className="block text-sm font-medium">Actes concernés <span className="font-normal text-slate-500">(vide = tous les rendez-vous)</span>
          <select multiple name="actes" defaultValue={initial?.actes.map((act) => String(act.id)) || []} className={`${fieldClass} min-h-40`}>{options.map((act) => <option key={act.id} value={act.id}>{act.name}</option>)}</select>
        </label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="include_prerequisites" defaultChecked={initial?.include_prerequisites ?? true} /> Inclure les prérequis des actes</label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="is_active" defaultChecked={initial?.is_active ?? true} /> Règle active</label>
        <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Exemples : 3 jours avant (3 / jours), 30 minutes avant (30 / minutes). Seules les règles globales sont gérées ici.</p>
        <div className="flex gap-2"><button disabled={busy} className={button}>Enregistrer</button><Link to="/dashboard/activite/rdv/rappels/" className={mutedButton}>Annuler</Link></div>
      </form>}
    </>
  );
}

function MessagesList() {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const kind = searchParams.get('kind') || 'all';
  const status = searchParams.get('status') || 'all';
  const q = searchParams.get('q') || '';
  const page = Math.max(1, Number(searchParams.get('page') || 1));
  const { data, loading, error } = useLoader(
    (signal) => adminActivityApi.conversations({ kind, status, q, page }, signal),
    [kind, status, q, page],
  );
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams(search);
    const value = String(new FormData(event.currentTarget).get('q') || '').trim();
    params.delete('page'); value ? params.set('q', value) : params.delete('q');
    navigate(`${pathname}?${params.toString()}`);
  };
  const setFilter = (key: 'kind' | 'status', value: string) => {
    const params = new URLSearchParams(search); params.delete('page');
    value === 'all' ? params.delete(key) : params.set(key, value);
    navigate(`${pathname}?${params.toString()}`);
  };
  return (
    <>
      <PageHeader title="Activité · Messagerie" subtitle="Supervision des conversations en lecture seule." />
      <Feedback error={error} />
      {data && <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[['Conversations', data.kpis.total], ['Actives', data.kpis.active], ['En attente', data.kpis.waiting], ['Messages (7 j)', data.kpis.messages_7d]].map(([label, value]) => <div key={String(label)} className={card}><p className="text-xs uppercase text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>)}</div>}
      <Loading loading={loading} />
      {!loading && data && <section className={card}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1">{[['all', 'Tous'], ['devis', 'Devis'], ['rdv', 'RDV'], ['general', 'Général']].map(([value, label]) => <button key={value} onClick={() => setFilter('kind', value)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${kind === value ? 'bg-slate-900 text-white' : 'bg-slate-100'}`}>{label} <span className="opacity-70">{data.counts[value]}</span></button>)}</div>
          <div className="flex flex-wrap gap-1">{[['all', 'Statut · Tous'], ['active', 'Actif'], ['waiting', 'Attente'], ['closed', 'Clos']].map(([value, label]) => <button key={value} onClick={() => setFilter('status', value)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${status === value ? 'bg-slate-700 text-white' : 'bg-slate-100'}`}>{label}</button>)}</div>
          <form onSubmit={submit} className="flex gap-2"><input name="q" defaultValue={q} placeholder="Patient, réf. devis/RDV…" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" /><button className={button}>Rechercher</button></form>
        </div>
        <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{['Dossier', 'Patient', 'Structure', 'Type', 'Statut fil', 'Messages', 'Dernière activité'].map((x) => <th key={x} className="p-3">{x}</th>)}<th className="p-3" /></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.rows.map((conversation) => <tr key={conversation.id}>
            <td className="p-3 font-semibold">{conversation.label}</td><td className="p-3">{conversation.patient.name}</td><td className="p-3">{conversation.organization?.name || '—'}</td><td className="p-3">{conversation.kind_label}</td><td className="p-3">{conversation.status_label}</td><td className="p-3 text-center">{conversation.message_count}</td>
            <td className="p-3 text-xs">{dateTime(conversation.updated_at)}{conversation.last_message && <small className="block max-w-48 truncate text-slate-500">{conversation.last_message.content}</small>}</td><td className="p-3"><Link className="font-semibold text-sky-800" to={`/dashboard/activite/messages/${conversation.id}/`}>Lire →</Link></td>
          </tr>)}{!data.rows.length && <tr><td colSpan={8} className="p-8 text-center text-slate-500">Aucune conversation.</td></tr>}</tbody>
        </table></div>
        <Pagination page={data.pagination} params={searchParams} pathname={pathname} />
        <p className="mt-4 text-xs text-slate-400">Supervision en lecture seule — l'administration ne répond pas depuis cette vue.</p>
      </section>}
    </>
  );
}

function ConversationDetail({ id }: { id: number }) {
  const { data, loading, error } = useLoader((signal) => adminActivityApi.conversation(id, signal), [id]);
  const conversation = data?.conversation;
  return (
    <>
      <PageHeader title={`Messagerie · ${conversation?.label || `Conversation #${id}`}`} />
      <Feedback error={error} />
      <Loading loading={loading} />
      {conversation && data && <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(250px,1fr)]">
        <section className={card}>
          <div className="border-b border-slate-100 pb-3"><h2 className="font-bold">{conversation.label}</h2><p className="text-xs text-slate-500">{conversation.patient.name} ↔ {conversation.prestataire.name}</p></div>
          <div className="max-h-[60vh] space-y-3 overflow-y-auto py-4">
            {data.messages.map((message) => <article key={message.id} className={`rounded-lg p-3 text-sm ${message.message_type === 'system' || message.message_type === 'status_card' ? 'bg-slate-50 text-center' : message.sender_id === conversation.patient.id ? 'bg-blue-50' : 'bg-emerald-50'}`}>
              <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{message.sender.name} · {dateTime(message.timestamp)}{message.message_type !== 'internal' ? ` · ${message.message_type_label}` : ''}</p>
              <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
            </article>)}
            {!data.messages.length && <p className="py-8 text-center text-sm text-slate-500">Aucun message.</p>}
          </div>
          <p className="border-t border-slate-100 pt-3 text-xs text-slate-400">Lecture seule — l'administration ne répond pas depuis cette vue.</p>
        </section>
        <aside className="space-y-4">
          <section className={card}><h2 className="font-bold">Métadonnées</h2><dl className="mt-3 space-y-2 text-sm"><DetailField label="Type" value={conversation.kind_label} /><DetailField label="Statut fil" value={conversation.status_label} /><DetailField label="Structure" value={conversation.organization?.name || '—'} /><DetailField label="Créé" value={dateTime(conversation.created_at)} /><DetailField label="MAJ" value={dateTime(conversation.updated_at)} /></dl></section>
          <section className={card}><h2 className="font-bold">Liens croisés</h2><ul className="mt-3 space-y-2 text-sm">
            {conversation.devis_part_reference && <li>Sous-devis <span className="font-mono">{conversation.devis_part_reference}</span></li>}
            {conversation.devis_reference && <li><Link className="text-sky-800" to={`/dashboard/devis/${conversation.devis_reference}/`}>Devis {conversation.devis_reference}</Link></li>}
            {conversation.appointment_reference && <li><Link className="text-sky-800" to={`/dashboard/activite/rdv/${conversation.appointment_reference}/`}>RDV {conversation.appointment_reference}</Link></li>}
          </ul></section>
        </aside>
      </div>}
    </>
  );
}

export function AdminActivityPage() {
  const { pathname } = useLocation();
  let page: ReactNode;
  const quoteMatch = pathname.match(/^\/dashboard\/devis\/([^/]+)\/?(?:relance|archiver)?\/?$/);
  const appointmentMatch = pathname.match(/^\/dashboard\/activite\/rdv\/([^/]+)\/?$/);
  const messageMatch = pathname.match(/^\/dashboard\/activite\/messages\/(\d+)\/?$/);
  const scheduleDeleteMatch = pathname.match(/^\/dashboard\/activite\/rdv\/rappels\/(\d+)\/supprimer\/?$/);
  const scheduleEditMatch = pathname.match(/^\/dashboard\/activite\/rdv\/rappels\/(\d+)\/modifier\/?$/);
  if (pathname === '/dashboard/devis/' || pathname === '/dashboard/devis') page = <QuotesList />;
  else if (quoteMatch) page = <QuoteDetail reference={decodeURIComponent(quoteMatch[1])} />;
  else if (pathname === '/dashboard/activite/rdv/' || pathname === '/dashboard/activite/rdv') page = <AppointmentsList />;
  else if (appointmentMatch && appointmentMatch[1] !== 'rappels') page = <AppointmentDetail reference={decodeURIComponent(appointmentMatch[1])} />;
  else if (pathname === '/dashboard/activite/rdv/rappels/ajouter/' || pathname === '/dashboard/activite/rdv/rappels/ajouter') page = <ReminderScheduleForm />;
  else if (scheduleEditMatch) page = <ReminderScheduleForm id={Number(scheduleEditMatch[1])} />;
  else if (scheduleDeleteMatch) page = <ReminderSchedules />;
  else if (pathname === '/dashboard/activite/rdv/rappels/' || pathname === '/dashboard/activite/rdv/rappels') page = <ReminderSchedules />;
  else if (pathname === '/dashboard/activite/messages/' || pathname === '/dashboard/activite/messages') page = <MessagesList />;
  else if (messageMatch) page = <ConversationDetail id={Number(messageMatch[1])} />;
  else page = <Overview />;
  return <AdminActivityShell>{page}</AdminActivityShell>;
}
