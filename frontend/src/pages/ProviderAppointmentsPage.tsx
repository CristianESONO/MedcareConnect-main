import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CalendarDays, Clock3, Pencil, Ticket, UserRound } from 'lucide-react';
import {
  providerAppointmentsApi,
  type ProviderAppointment,
  type ProviderAppointmentList,
  type ProviderAppointmentStatus,
} from '../lib/api';

const VALID_STATUSES: ProviderAppointmentStatus[] = [
  'upcoming', 'requested', 'confirmed', 'past', 'all',
];

const STATUS_CLASSES: Record<string, string> = {
  requested: 'bg-amber-100 text-amber-800',
  confirmed: 'bg-emerald-50 text-emerald-800',
  completed: 'bg-blue-50 text-blue-700',
  no_show: 'bg-rose-50 text-rose-700',
  declined: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-gray-100 text-gray-600',
};

function isStatus(value: string | null): value is ProviderAppointmentStatus {
  return VALID_STATUSES.includes(value as ProviderAppointmentStatus);
}

function formatAppointmentDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatAmount(value: string) {
  return Number(value).toLocaleString('fr-FR');
}

function AppointmentActions({
  appointment,
  onAction,
  onEdit,
  busy,
}: {
  appointment: ProviderAppointment;
  onAction: (action: 'confirm' | 'decline' | 'complete' | 'no_show' | 'cancel', appointment: ProviderAppointment) => void;
  onEdit: (appointment: ProviderAppointment) => void;
  busy: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
      {appointment.status === 'requested' && (
        <>
          <button type="button" disabled={busy} onClick={() => onAction('confirm', appointment)} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Confirmer</button>
          <button type="button" disabled={busy} onClick={() => onAction('decline', appointment)} className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-bold text-gray-600 disabled:opacity-50">Refuser</button>
        </>
      )}
      {appointment.status === 'confirmed' && (
        <>
          <button type="button" disabled={busy} onClick={() => onAction('complete', appointment)} className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Honoré</button>
          <button type="button" disabled={busy} onClick={() => onAction('no_show', appointment)} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700 disabled:opacity-50">Absent</button>
          <button type="button" disabled={busy} onClick={() => onAction('cancel', appointment)} className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-bold text-gray-600 disabled:opacity-50">Annuler</button>
        </>
      )}
      {appointment.can_edit && (
        <button type="button" onClick={() => onEdit(appointment)} className="inline-flex items-center gap-1.5 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-bold text-sky-800">
          <Pencil size={13} aria-hidden="true" /> Modifier
        </button>
      )}
    </div>
  );
}

export function ProviderAppointmentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedStatus = searchParams.get('status');
  const status = isStatus(requestedStatus) ? requestedStatus : 'all';
  const viewMode = searchParams.get('view') === 'ticket' ? 'ticket' : 'list';
  const [data, setData] = useState<ProviderAppointmentList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyReference, setBusyReference] = useState('');
  const [editing, setEditing] = useState<ProviderAppointment | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    providerAppointmentsApi.list(status, viewMode, controller.signal)
      .then((response) => {
        setData(response);
        setError('');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les rendez-vous.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [status, viewMode, refreshKey]);

  const changeFilters = (nextStatus: ProviderAppointmentStatus, nextView = viewMode) => {
    setLoading(true);
    setSearchParams({ status: nextStatus, view: nextView });
  };

  const runAction = async (
    action: 'confirm' | 'decline' | 'complete' | 'no_show' | 'cancel',
    appointment: ProviderAppointment,
  ) => {
    const prompts: Partial<Record<typeof action, string>> = {
      decline: 'Refuser cette demande de rendez-vous ?',
      no_show: 'Marquer ce rendez-vous comme absent ?',
      cancel: 'Annuler ce rendez-vous ?',
    };
    if (prompts[action] && !window.confirm(prompts[action])) return;
    setBusyReference(appointment.reference);
    setError('');
    try {
      await providerAppointmentsApi.action(appointment.reference, action, status);
      setRefreshKey((current) => current + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Cette action n’a pas pu être effectuée.');
    } finally {
      setBusyReference('');
    }
  };

  const saveAppointment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    setBusyReference(editing.reference);
    setError('');
    try {
      await providerAppointmentsApi.update(editing.reference, new FormData(event.currentTarget));
      setEditing(null);
      setRefreshKey((current) => current + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de modifier ce rendez-vous.');
    } finally {
      setBusyReference('');
    }
  };

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace prestataire</p>
          <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
            <CalendarDays size={24} aria-hidden="true" /> Rendez-vous
          </h1>
          <p className="mt-1 text-sm text-gray-500">Confirmez les demandes et suivez les rendez-vous de votre structure.</p>
        </div>
        <nav className="flex gap-1 rounded-xl border border-gray-200 bg-white p-1 text-xs font-semibold shadow-sm" aria-label="Affichage des rendez-vous">
          <button type="button" onClick={() => changeFilters(status, 'list')} aria-pressed={viewMode === 'list'} className={`rounded-lg px-3 py-2 ${viewMode === 'list' ? 'bg-[#0a5c8a] text-white' : 'text-gray-600 hover:bg-gray-50'}`}>Liste</button>
          <button type="button" onClick={() => changeFilters(status, 'ticket')} aria-pressed={viewMode === 'ticket'} className={`rounded-lg px-3 py-2 ${viewMode === 'ticket' ? 'bg-[#0a5c8a] text-white' : 'text-gray-600 hover:bg-gray-50'}`}><Ticket size={14} className="mr-1 inline" aria-hidden="true" /> Ticket</button>
          <a href="/rdv/pro/agenda/grille/" className="rounded-lg px-3 py-2 text-gray-600 hover:bg-gray-50">Agenda</a>
        </nav>
      </header>

      {data && (
        <nav className="mt-5 flex gap-1.5 overflow-x-auto rounded-xl border border-gray-200 bg-white p-1.5 shadow-sm" aria-label="Filtrer les rendez-vous">
          {data.filter_tabs.map((tab) => (
            <button type="button" key={tab.key} onClick={() => changeFilters(tab.key)} aria-pressed={status === tab.key} className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold ${status === tab.key ? 'bg-[#0a5c8a] text-white' : 'text-gray-600 hover:bg-gray-50'}`}>
              {tab.label} <span className="ml-1 opacity-75">{tab.count}</span>
            </button>
          ))}
        </nav>
      )}

      {loading && <p className="mt-5 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement des rendez-vous…</p>}
      {error && <p className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}

      {!loading && !error && data && (
        <div className={`mt-5 gap-3 ${viewMode === 'ticket' ? 'grid sm:grid-cols-2 lg:grid-cols-3' : 'space-y-3'}`}>
          {data.appointments.length ? data.appointments.map((appointment) => (
            <article key={appointment.reference} className={`rounded-2xl border bg-white p-4 shadow-sm sm:p-5 ${appointment.status === 'requested' ? 'border-amber-300 bg-amber-50/20' : ['cancelled', 'declined', 'no_show'].includes(appointment.status) ? 'border-gray-200 opacity-80' : 'border-gray-200'}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-[#0a5c8a]">{appointment.reference}</span>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase ${STATUS_CLASSES[appointment.status] || 'bg-gray-100 text-gray-700'}`}>{appointment.status_label}</span>
                    {appointment.is_walk_in && <span className="rounded-full bg-indigo-50 px-2 py-1 text-[10px] font-bold text-indigo-700">Sur place</span>}
                  </div>
                  <p className="mt-2 flex items-center gap-1.5 text-sm font-bold text-gray-900">
                    <Clock3 size={15} className="text-gray-400" aria-hidden="true" /> {formatAppointmentDate(appointment.start)}
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                    <UserRound size={15} className="text-gray-400" aria-hidden="true" /> {appointment.patient}
                    {appointment.devis_reference && <span className="text-xs font-normal text-gray-400">· devis {appointment.devis_reference}</span>}
                  </p>
                  {appointment.is_walk_in && appointment.walk_in_motif && <p className="mt-1 text-xs text-gray-500">{appointment.walk_in_motif}</p>}
                  {appointment.patient_note && <p className="mt-1 text-xs italic text-gray-500">« {appointment.patient_note} »</p>}
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400">Montant patient</p>
                  <p className="text-lg font-extrabold text-[#0a5c8a]">{formatAmount(appointment.total_patient)} F</p>
                </div>
              </div>
              {!!appointment.actes.length && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {appointment.actes.map((act, index) => (
                    <span key={`${act.acte}-${index}`} className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[11px] text-gray-700">
                      {act.acte}{act.quantity > 1 && <span className="text-gray-400"> ×{act.quantity}</span>}
                    </span>
                  ))}
                </div>
              )}
              {appointment.prestataire_note && <p className="mt-2 text-xs text-gray-500">Note interne : {appointment.prestataire_note}</p>}
              <div className="mt-3">
                <AppointmentActions
                  appointment={appointment}
                  onAction={runAction}
                  onEdit={setEditing}
                  busy={busyReference === appointment.reference}
                />
              </div>
            </article>
          )) : (
            <div className="rounded-2xl border-2 border-dashed border-gray-200 bg-white py-14 text-center">
              <CalendarDays size={30} className="mx-auto text-gray-300" aria-hidden="true" />
              <p className="mt-3 text-sm font-semibold text-gray-700">Aucun rendez-vous pour ce filtre.</p>
              <p className="mt-1 text-xs text-gray-400">Les demandes de vos patients apparaîtront ici.</p>
            </div>
          )}
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/45 p-0 sm:items-center sm:p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditing(null); }}>
          <section className="w-full max-w-lg rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl sm:p-6" role="dialog" aria-modal="true" aria-labelledby="edit-appointment-title">
            <h2 id="edit-appointment-title" className="text-base font-bold text-gray-900">Modifier le rendez-vous</h2>
            <p className="mt-1 text-xs font-semibold text-[#0a5c8a]">{editing.reference}</p>
            <form key={editing.reference} onSubmit={saveAppointment} className="mt-5 space-y-3">
              <label className="block text-xs font-semibold text-gray-700">
                Date et heure
                <input type="datetime-local" name="slot" required defaultValue={editing.local_datetime} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
              </label>
              {editing.is_walk_in && (
                <div className="space-y-3 rounded-xl border border-indigo-100 bg-indigo-50/40 p-3">
                  <label className="block text-xs font-semibold text-gray-700">Nom du patient
                    <input type="text" name="name" required maxLength={120} defaultValue={editing.walk_in_name} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
                  </label>
                  <label className="block text-xs font-semibold text-gray-700">Téléphone
                    <input type="tel" name="phone" maxLength={40} defaultValue={editing.walk_in_phone} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
                  </label>
                  <label className="block text-xs font-semibold text-gray-700">Motif
                    <input type="text" name="motif" maxLength={200} defaultValue={editing.walk_in_motif} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
                  </label>
                </div>
              )}
              <label className="block text-xs font-semibold text-gray-700">Note interne
                <textarea name="note" rows={2} maxLength={400} defaultValue={editing.prestataire_note} className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
              </label>
              <div className="flex justify-end gap-2 border-t border-gray-100 pt-3">
                <button type="button" onClick={() => setEditing(null)} className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-600">Annuler</button>
                <button type="submit" disabled={busyReference === editing.reference} className="rounded-xl bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">Enregistrer</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </section>
  );
}
