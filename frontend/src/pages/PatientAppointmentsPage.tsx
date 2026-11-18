import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, MessageCircle } from 'lucide-react';
import { appointmentsApi, type PatientAppointment } from '../lib/api';

const ACCOUNT_LINKS = [
  { label: 'Tableau de bord', href: '/users/compte/panel/accueil/' },
  { label: 'Mes devis', href: '/users/compte/panel/devis/' },
  { label: 'Assurance', href: '/users/compte/panel/assurance/' },
  { label: 'Mes informations', href: '/users/compte/panel/profil/' },
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function appointmentBadgeClass(status: string) {
  if (status === 'ok') return 'bg-emerald-50 text-emerald-800';
  if (status === 'done') return 'bg-blue-50 text-blue-800';
  if (status === 'wait') return 'bg-amber-50 text-amber-800';
  return 'bg-gray-100 text-gray-700';
}

function AppointmentCard({
  appointment,
  past = false,
  onCancel,
  cancelling,
}: {
  appointment: PatientAppointment;
  past?: boolean;
  onCancel?: (reference: string) => void;
  cancelling?: boolean;
}) {
  const rescheduleUrl = appointment.conversation_url
    ? `${appointment.conversation_url}${appointment.conversation_url.includes('?') ? '&' : '?'}reschedule=1`
    : null;

  return (
    <article className={`rounded-2xl border border-gray-200 bg-white p-5 shadow-sm ${past ? 'opacity-90' : ''}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="font-bold text-[#123a63]">{appointment.organization}</h3>
          <p className="mt-1 text-sm capitalize text-gray-700">{formatDate(appointment.start)}</p>
          <p className="mt-2 text-xs leading-5 text-gray-500">
            {[appointment.location.quartier, appointment.location.city].filter(Boolean).join(' · ')}
            {appointment.location.address && <span className="block">{appointment.location.address}</span>}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {appointment.reference}
            {!past && ` · ${Number(appointment.total_patient).toLocaleString('fr-FR')} FCFA`}
          </p>
        </div>
        <span className={`w-fit shrink-0 rounded-full px-3 py-1 text-xs font-bold ${appointmentBadgeClass(appointment.status_badge)}`}>
          {appointment.status_label}
        </span>
      </div>

      {appointment.acts.length > 0 && (
        <div className="mt-4 divide-y divide-gray-100 rounded-xl bg-gray-50 px-3">
          {appointment.acts.map((act, index) => (
            <div key={`${act.name}-${index}`} className="flex justify-between gap-3 py-2 text-xs">
              <span className="text-gray-700">{act.name}{act.quantity > 1 ? ` ×${act.quantity}` : ''}</span>
              <span className="shrink-0 font-semibold text-gray-600">
                {Number(act.subtotal).toLocaleString('fr-FR')} F
              </span>
            </div>
          ))}
        </div>
      )}

      {appointment.prerequisites && (
        <div className="mt-4 whitespace-pre-line rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
          <strong className="mb-1 block">Consignes avant le rendez-vous</strong>
          {appointment.prerequisites}
        </div>
      )}

      {!past && appointment.status === 'requested' && (
        <p className="mt-3 text-xs text-gray-500">En attente de confirmation par la structure.</p>
      )}

      {!past && (
        <div className="mt-4 flex flex-wrap gap-2">
          {appointment.conversation_url && (
            <a href={appointment.conversation_url} className="inline-flex items-center gap-2 rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white hover:bg-[#084b70]">
              <MessageCircle size={15} aria-hidden="true" />
              Conversation
            </a>
          )}
          {appointment.can_reschedule && rescheduleUrl && (
            <a href={rescheduleUrl} className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50">
              Modifier le créneau
            </a>
          )}
          {appointment.can_cancel && onCancel && (
            <button
              type="button"
              onClick={() => onCancel(appointment.reference)}
              disabled={cancelling}
              className="rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
            >
              {cancelling ? 'Annulation…' : 'Annuler ce RDV'}
            </button>
          )}
        </div>
      )}
    </article>
  );
}

export function PatientAppointmentsPage() {
  const [upcoming, setUpcoming] = useState<PatientAppointment[]>([]);
  const [past, setPast] = useState<PatientAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadAppointments = useCallback(async (signal?: AbortSignal) => {
    const data = await appointmentsApi.patientList(signal);
    setUpcoming(data.upcoming);
    setPast(data.past);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadAppointments(controller.signal)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger vos rendez-vous.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [loadAppointments]);

  const cancelAppointment = async (reference: string) => {
    if (!window.confirm('Confirmez-vous l’annulation de ce rendez-vous ?')) return;
    setCancelling(reference);
    setError('');
    setNotice('');
    try {
      const response = await appointmentsApi.cancelPatientAppointment(reference);
      setNotice(response.message);
      await loadAppointments();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’annuler ce rendez-vous.');
    } finally {
      setCancelling('');
    }
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Mes rendez-vous</h1>
      </header>

      <nav className="mb-6 flex gap-2 overflow-x-auto pb-1" aria-label="Navigation du compte patient">
        {ACCOUNT_LINKS.map((item) => (
          <a key={item.href} href={item.href} className="shrink-0 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-600 hover:border-sky-300 hover:text-[#0a5c8a]">
            {item.label}
          </a>
        ))}
        <span className="shrink-0 rounded-full bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white" aria-current="page">
          Mes rendez-vous
        </span>
      </nav>

      {notice && <p className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement des rendez-vous…</p>}

      {!loading && (
        <>
          <section>
            <h2 className="mb-3 flex items-center gap-2 font-syne text-lg font-bold text-[#123a63]">
              <CalendarDays size={19} aria-hidden="true" />
              À venir
            </h2>
            {upcoming.length ? (
              <div className="space-y-3">
                {upcoming.map((appointment) => (
                  <AppointmentCard
                    key={appointment.reference}
                    appointment={appointment}
                    onCancel={cancelAppointment}
                    cancelling={cancelling === appointment.reference}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-6 text-center">
                <p className="text-sm font-semibold text-gray-700">Aucun rendez-vous à venir</p>
                <p className="mt-1 text-xs text-gray-500">Demandez un devis depuis la recherche, puis choisissez un créneau.</p>
                <Link to="/sante/recherche/" className="mt-4 inline-block rounded-lg bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white">
                  Rechercher un soin
                </Link>
              </div>
            )}
          </section>

          <section className="mt-8">
            <h2 className="mb-3 font-syne text-lg font-bold text-[#123a63]">Historique</h2>
            {past.length ? (
              <div className="space-y-3">
                {past.map((appointment) => (
                  <AppointmentCard key={appointment.reference} appointment={appointment} past />
                ))}
              </div>
            ) : (
              <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500">
                Aucun rendez-vous passé pour le moment.
              </p>
            )}
          </section>
        </>
      )}
    </section>
  );
}
