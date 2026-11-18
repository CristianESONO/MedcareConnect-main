import { Fragment, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { providerAgendaApi, providerAppointmentsApi, type ProviderAgenda, type ProviderAgendaAppointment } from '../lib/api';

const STATUS_LABELS: Record<string, string> = {
  requested: 'À confirmer',
  confirmed: 'Confirmé',
  completed: 'Honoré',
  no_show: 'Absent',
  cancelled: 'Annulé',
  declined: 'Refusé',
};

function localDateIso() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function formatWeekRange(monday: string, sunday: string) {
  const start = new Date(`${monday}T12:00:00`);
  const end = new Date(`${sunday}T12:00:00`);
  const startLabel = new Intl.DateTimeFormat('fr-FR', { day: 'numeric' }).format(start);
  const endLabel = new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(end);
  return `${startLabel} – ${endLabel}`;
}

function formatAmount(amount: string) {
  return Number(amount).toLocaleString('fr-FR');
}

function isMovable(status: string) {
  return status === 'requested' || status === 'confirmed';
}

export function ProviderAgendaPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedDate = searchParams.get('date') || localDateIso();
  const [data, setData] = useState<ProviderAgenda | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [addSlot, setAddSlot] = useState<{ value: string; label: string } | null>(null);
  const [detail, setDetail] = useState<ProviderAgendaAppointment | null>(null);
  const [busy, setBusy] = useState('');
  const [draggingReference, setDraggingReference] = useState('');
  const dragReference = useRef('');
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = '/static/appointments/css/prestataire_agenda.css?v=2';
    stylesheet.dataset.providerAgenda = 'true';
    document.head.appendChild(stylesheet);
    return () => stylesheet.remove();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    providerAgendaApi.get(selectedDate, controller.signal)
      .then((response) => {
        setData(response);
        setError('');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger l’agenda.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [selectedDate, refreshKey]);

  useEffect(() => () => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
  }, []);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setAddSlot(null);
        setDetail(null);
      }
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, []);

  const notify = (message: string, isError = false) => {
    setToast({ message, error: isError });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2800);
  };

  const refresh = () => {
    setLoading(true);
    setRefreshKey((current) => current + 1);
  };
  const openWeek = (date: string) => {
    setLoading(true);
    setSearchParams({ date });
  };

  const moveAppointment = async (reference: string, slot: string) => {
    setBusy(reference);
    try {
      const response = await providerAgendaApi.move(reference, slot);
      notify(`Rendez-vous déplacé — ${response.label}`);
      setDetail(null);
      refresh();
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'Déplacement impossible.', true);
    } finally {
      setBusy('');
    }
  };

  const dropOnSlot = (event: React.DragEvent<HTMLDivElement>, slot: string) => {
    event.preventDefault();
    if (!slot || !dragReference.current) return;
    const reference = event.dataTransfer.getData('text/plain') || dragReference.current;
    const source = data?.rows
      .flatMap((row) => row.cells)
      .flatMap((cell) => cell.rdvs.map((rdv) => ({ reference: rdv.reference, slot: cell.value })))
      .find((rdv) => rdv.reference === reference);
    if (source?.slot === slot) return;
    void moveAppointment(reference, slot);
  };

  const createWalkIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!addSlot || !data) return;
    const formData = new FormData(event.currentTarget);
    formData.set('slot', addSlot.value);
    formData.set('date', data.monday);
    setBusy('create');
    try {
      const response = await providerAgendaApi.createWalkIn(formData);
      setAddSlot(null);
      notify(response.message);
      refresh();
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'Impossible d’ajouter ce rendez-vous.', true);
    } finally {
      setBusy('');
    }
  };

  const runAction = async (
    action: 'confirm' | 'decline' | 'complete' | 'no_show' | 'cancel',
    appointment: ProviderAgendaAppointment,
  ) => {
    if ((action === 'decline' || action === 'cancel') && !window.confirm(
      action === 'decline' ? 'Refuser cette demande de rendez-vous ?' : 'Annuler ce rendez-vous ?',
    )) return;
    setBusy(appointment.ref);
    try {
      const response = await providerAppointmentsApi.action(appointment.ref, action, 'all');
      setDetail(null);
      notify(response.message);
      refresh();
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'Cette action n’a pas pu être effectuée.', true);
    } finally {
      setBusy('');
    }
  };

  const reschedule = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!detail) return;
    const formData = new FormData(event.currentTarget);
    setBusy(detail.ref);
    try {
      await providerAppointmentsApi.update(detail.ref, formData);
      setDetail(null);
      notify('Rendez-vous modifié.');
      refresh();
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'Impossible de modifier ce rendez-vous.', true);
    } finally {
      setBusy('');
    }
  };

  return (
    <section className="mx-auto w-full max-w-7xl px-3 py-6 sm:px-5 sm:py-8">
      <header className="ag-toolbar">
        <div>
          <h1 className="ag-toolbar-title">Agenda</h1>
          <p className="ag-toolbar-sub">Glissez-déposez un rendez-vous à confirmer ou confirmé, ou cliquez sur + pour ajouter un rendez-vous sur place.</p>
        </div>
        <nav className="ag-view-toggle" aria-label="Affichage des rendez-vous">
          <span aria-current="page">Agenda</span>
          <Link to="/rdv/pro/agenda/">Liste</Link>
          <Link to="/rdv/pro/agenda/?view=ticket">Ticket</Link>
        </nav>
      </header>

      <div className="ag-nav">
        <button type="button" className="ag-nav-btn" aria-label="Semaine précédente" disabled={!data || loading} onClick={() => data && openWeek(data.prev_week)}>
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
        <button type="button" className="ag-nav-btn" aria-label="Semaine suivante" disabled={!data || loading} onClick={() => data && openWeek(data.next_week)}>
          <ChevronRight size={16} aria-hidden="true" />
        </button>
        <button type="button" className={`ag-nav-btn${data?.is_current_week ? ' opacity-50' : ''}`} disabled={!data || data.is_current_week || loading} onClick={() => data && openWeek(data.today)}>
          Aujourd’hui
        </button>
        {data && <span className="ag-nav-range">{formatWeekRange(data.monday, data.sunday)}</span>}
        {!!data?.new_rdv_count && <span className="ag-badge-pending">{data.new_rdv_count} à confirmer</span>}
      </div>

      <div className="ag-legend" aria-label="Légende des statuts">
        {[
          ['ag-requested', 'À confirmer'],
          ['ag-confirmed', 'Confirmé'],
          ['ag-completed', 'Honoré'],
          ['ag-no_show', 'Absent'],
        ].map(([className, label]) => (
          <span className="ag-legend-item" key={className}><span className={`ag-legend-dot ${className}`} />{label}</span>
        ))}
        <span className="ag-legend-item"><span className="ag-legend-dot" style={{ background: '#fff', borderColor: '#e5e7eb' }} />Créneau · plusieurs rendez-vous possibles</span>
      </div>

      {loading && <p className="mb-3 rounded-xl border border-gray-200 bg-white p-3 text-sm text-gray-600" role="status">Chargement de l’agenda…</p>}
      {error && <p className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}

      {!loading && data && (
        <>
          {data.days.every((day) => !day.is_open) && (
            <p className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Aucun horaire d’ouverture n’est défini. <a href="/sante/prestataire/organisme/horaires/" className="font-semibold underline">Renseigner vos horaires</a>
            </p>
          )}
          <div className="ag-wrap">
            <div className="ag-grid">
              <div className="ag-corner" />
              {data.days.map((day) => (
                <div key={day.date} className={`ag-dayhead${day.is_today ? ' is-today' : ''}${!day.is_open ? ' is-closed' : ''}`}>
                  <span className="ag-dow">{day.weekday.slice(0, 3)}</span>
                  <span className="ag-dnum">{Number(day.date.slice(-2))}</span>
                </div>
              ))}
              {data.rows.map((row) => (
                <Fragment key={row.time}>
                  <div className="ag-time">{row.time}</div>
                  {row.cells.map((cell, index) => {
                    const day = data.days[index];
                    if (!cell.in_hours || (cell.is_past && !cell.rdvs.length)) {
                      return <div key={`${day.date}-${row.time}`} className={`ag-cell${cell.is_past ? ' ag-past' : ' ag-off'}`} />;
                    }
                    return (
                      <div
                        key={`${day.date}-${row.time}`}
                        className={`ag-slot${cell.rdvs.length ? ' ag-slot--busy' : ''}`}
                        data-slot={cell.value}
                        onDragOver={(event) => {
                          if (!cell.is_past && draggingReference) {
                            event.preventDefault();
                            event.currentTarget.classList.add('ag-drop-over');
                          }
                        }}
                        onDragLeave={(event) => event.currentTarget.classList.remove('ag-drop-over')}
                        onDrop={(event) => {
                          event.currentTarget.classList.remove('ag-drop-over');
                          if (!cell.is_past) dropOnSlot(event, cell.value);
                        }}
                      >
                        {cell.rdv_count > 1 && <span className="ag-slot-count">{cell.rdv_count} RDV</span>}
                        {cell.rdvs.map((appointment) => {
                          const detailData = data.appointments[appointment.reference];
                          return (
                            <button
                              type="button"
                              key={appointment.reference}
                              className={`ag-rdv ag-rdv--stacked ag-${appointment.status}${!isMovable(appointment.status) ? ' is-locked' : ''}${draggingReference === appointment.reference ? ' is-dragging' : ''}`}
                              data-rdv={appointment.reference}
                              data-status={appointment.status}
                              draggable={isMovable(appointment.status)}
                              onDragStart={(event) => {
                                dragReference.current = appointment.reference;
                                setDraggingReference(appointment.reference);
                                event.dataTransfer.effectAllowed = 'move';
                                event.dataTransfer.setData('text/plain', appointment.reference);
                              }}
                              onDragEnd={() => {
                                dragReference.current = '';
                                setDraggingReference('');
                                document.querySelectorAll('.ag-drop-over').forEach((element) => element.classList.remove('ag-drop-over'));
                              }}
                              onClick={() => detailData && setDetail(detailData)}
                            >
                              <span className="ag-rdv-name">{appointment.patient_label}</span>
                              {appointment.is_walk_in && <span className="ag-tag">sur place</span>}
                            </button>
                          );
                        })}
                        {!cell.is_past && (
                          <button
                            type="button"
                            className="ag-free ag-free--inline"
                            data-slot={cell.value}
                            aria-label={`Ajouter un rendez-vous — ${cell.label}`}
                            onClick={() => setAddSlot({ value: cell.value, label: cell.label })}
                          >+</button>
                        )}
                      </div>
                    );
                  })}
                </Fragment>
              ))}
            </div>
          </div>
          <p className="ag-hint"><strong>Astuce :</strong> un même créneau peut accueillir plusieurs patients. Déposez un rendez-vous sur n’importe quel créneau ouvert.</p>
        </>
      )}

      {toast && <div className={`ag-toast show${toast.error ? ' error' : ''}`} role={toast.error ? 'alert' : 'status'}>{toast.message}</div>}

      {addSlot && (
        <div className="ag-modal open" aria-hidden="false" onMouseDown={(event) => { if (event.target === event.currentTarget) setAddSlot(null); }}>
          <section className="ag-sheet" role="dialog" aria-modal="true" aria-labelledby="agenda-add-title">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 id="agenda-add-title" className="text-base font-bold text-gray-900">Rendez-vous sur place</h2>
                <p className="mt-1 text-xs font-semibold text-sky-700">{addSlot.label}</p>
              </div>
              <button type="button" onClick={() => setAddSlot(null)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" aria-label="Fermer">×</button>
            </div>
            <form onSubmit={createWalkIn} className="mt-5 space-y-3">
              <label className="block text-xs font-semibold text-gray-700">Nom du patient <span className="text-rose-500">*</span>
                <input type="text" name="name" required maxLength={120} placeholder="Ex. Awa Diop" className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-xs font-semibold text-gray-700">Téléphone
                  <input type="tel" name="phone" maxLength={40} placeholder="77 000 00 00" className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
                </label>
                <label className="block text-xs font-semibold text-gray-700">Motif
                  <input type="text" name="motif" maxLength={200} placeholder="Ex. Consultation" className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
                </label>
              </div>
              <label className="block text-xs font-semibold text-gray-700">Note interne
                <textarea name="note" rows={2} maxLength={400} placeholder="Visible uniquement par votre équipe" className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
              </label>
              <div className="flex justify-end gap-2 border-t border-gray-100 pt-3">
                <button type="button" onClick={() => setAddSlot(null)} className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-600">Annuler</button>
                <button type="submit" disabled={busy === 'create'} className="rounded-xl bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">Ajouter le rendez-vous</button>
              </div>
            </form>
          </section>
        </div>
      )}

      {detail && (
        <div className="ag-modal open" aria-hidden="false" onMouseDown={(event) => { if (event.target === event.currentTarget) setDetail(null); }}>
          <section className="ag-sheet" role="dialog" aria-modal="true" aria-labelledby="agenda-detail-title">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${detail.status === 'requested' ? 'bg-amber-100 text-amber-800' : detail.status === 'confirmed' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}>
                    {STATUS_LABELS[detail.status] || detail.status_label}
                  </span>
                  {detail.is_walk_in && <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-700">Sur place</span>}
                </div>
                <h2 id="agenda-detail-title" className="mt-2 truncate text-base font-bold text-gray-900">{detail.name}</h2>
                <p className="text-xs font-semibold text-gray-500">{detail.when} · {detail.ref}</p>
              </div>
              <button type="button" onClick={() => setDetail(null)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" aria-label="Fermer">×</button>
            </div>
            <dl className="mt-5 space-y-2.5 text-sm">
              {detail.phone && <div className="text-gray-700">Téléphone : <a className="font-semibold text-sky-700 hover:underline" href={`tel:${detail.phone}`}>{detail.phone}</a></div>}
              {detail.motif && <div className="text-gray-700">Motif : {detail.motif}</div>}
              {!!detail.actes.length && <div className="flex flex-wrap gap-1.5">{detail.actes.map((act, index) => <span key={`${act}-${index}`} className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-700">{act}</span>)}</div>}
              {detail.devis && <div className="text-xs text-gray-500">Devis lié : <span className="font-mono font-semibold text-gray-700">{detail.devis}</span></div>}
              {!!Number(detail.total) && <div className="flex items-center justify-between rounded-xl bg-gray-50 px-3 py-2.5"><span className="text-xs font-medium text-gray-500">Montant patient</span><strong className="text-base text-sky-700">{formatAmount(detail.total)} F</strong></div>}
              {detail.note && <div className="rounded-xl bg-gray-50 px-3 py-2.5 text-xs italic text-gray-600">{detail.note}</div>}
            </dl>

            {isMovable(detail.status) && (
              <form onSubmit={reschedule} className="mt-4 space-y-2 border-t border-gray-100 pt-4">
                <p className="text-xs font-semibold text-gray-700">Changer le créneau</p>
                <div className="flex flex-wrap items-end gap-2">
                  <input type="datetime-local" name="slot" required defaultValue={detail.slot_iso} className="min-w-0 flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm" />
                  <button type="submit" disabled={busy === detail.ref} className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-bold text-sky-800 disabled:opacity-50">Déplacer</button>
                </div>
                {detail.is_walk_in && <input type="hidden" name="name" value={detail.name} />}
              </form>
            )}

            <div className="mt-5 flex flex-wrap gap-2 border-t border-gray-100 pt-4">
              {detail.status === 'requested' && <>
                <button type="button" disabled={busy === detail.ref} onClick={() => void runAction('confirm', detail)} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Confirmer</button>
                <button type="button" disabled={busy === detail.ref} onClick={() => void runAction('decline', detail)} className="rounded-xl border border-gray-200 px-3 py-2 text-xs font-bold text-gray-600 disabled:opacity-50">Refuser</button>
              </>}
              {detail.status === 'confirmed' && <>
                <button type="button" disabled={busy === detail.ref} onClick={() => void runAction('complete', detail)} className="rounded-xl bg-blue-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Honoré</button>
                <button type="button" disabled={busy === detail.ref} onClick={() => void runAction('no_show', detail)} className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700 disabled:opacity-50">Absent</button>
                <button type="button" disabled={busy === detail.ref} onClick={() => void runAction('cancel', detail)} className="rounded-xl border border-gray-200 px-3 py-2 text-xs font-bold text-gray-600 disabled:opacity-50">Annuler</button>
              </>}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
