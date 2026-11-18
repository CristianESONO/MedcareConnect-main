import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { CalendarDays, Clock3 } from 'lucide-react';
import { appointmentsApi, type PatientBookingData } from '../lib/api';

function amount(value: string | number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString('fr-FR') : '0';
}

export function PatientBookingPage() {
  const { partRef = '' } = useParams();
  const navigate = useNavigate();
  const [booking, setBooking] = useState<PatientBookingData | null>(null);
  const [hasSlots, setHasSlots] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setBooking(null);
    setLoading(true);
    setError('');
    appointmentsApi.booking(partRef, controller.signal)
      .then((response) => {
        setBooking(response.booking_data);
        setHasSlots(response.has_slots);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les créneaux.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [partRef]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedSlot || busy) return;
    const formData = new FormData();
    formData.set('slot', selectedSlot);
    formData.set('note', note);
    setBusy(true);
    setError('');
    try {
      const response = await appointmentsApi.submitBooking(partRef, formData);
      navigate(response.redirect_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’envoyer la demande de rendez-vous.');
    } finally {
      setBusy(false);
    }
  };

  const availableSlots = booking?.days.flatMap((day) => day.slots
    .filter((slot) => slot.available)
    .map((slot) => ({ ...slot, day: day.label }))) || [];

  return (
    <section className="mx-auto w-full max-w-4xl px-4 py-8">
      <p className="mb-4 text-sm">
        <Link to="/users/compte/panel/devis/" className="font-semibold text-[#0a5c8a] hover:underline">← Retour à mes devis</Link>
      </p>
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Prise de rendez-vous</p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl"><CalendarDays size={24} /> Choisir un créneau</h1>
      </header>
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Recherche des créneaux disponibles…</p>}
      {error && <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {!loading && booking && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(260px,1fr)]">
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="font-syne text-lg font-bold text-[#123a63]">{booking.org}</h2>
            <p className="mt-1 text-sm text-gray-500">{booking.org_city}</p>
            {!hasSlots ? (
              <div className="mt-5 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-900">
                Aucun créneau n’est disponible en ligne pour le moment. Vous pouvez contacter la structure depuis votre conversation.
                <Link to="/messaging/" className="mt-3 inline-flex font-bold underline">Ouvrir mes messages</Link>
              </div>
            ) : (
              <form onSubmit={submit} className="mt-5 space-y-4">
                {booking.soonest && (
                  <button
                    type="button"
                    aria-pressed={selectedSlot === 'asap'}
                    onClick={() => setSelectedSlot('asap')}
                    className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left ${selectedSlot === 'asap' ? 'border-sky-400 bg-sky-50' : 'border-gray-200 hover:bg-gray-50'}`}
                  >
                    <Clock3 size={18} className="text-[#0a5c8a]" />
                    <span><strong className="block text-sm text-gray-900">Au plus vite</strong><span className="mt-0.5 block text-xs text-gray-500">Prochaine disponibilité : {booking.soonest.label}</span></span>
                  </button>
                )}
                <label className="block text-sm font-semibold text-gray-700" htmlFor="booking-slot">Créneaux disponibles</label>
                <select
                  id="booking-slot"
                  value={selectedSlot === 'asap' ? '' : selectedSlot}
                  onChange={(event) => setSelectedSlot(event.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm"
                >
                  <option value="">Sélectionnez une date et une heure</option>
                  {availableSlots.map((slot) => <option key={slot.value} value={slot.value}>{slot.day} · {slot.label}</option>)}
                </select>
                <label className="block text-sm font-semibold text-gray-700" htmlFor="booking-note">
                  Note pour la structure <span className="font-normal text-gray-400">(facultatif)</span>
                </label>
                <textarea id="booking-note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} rows={3} className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" placeholder="Précision utile à votre rendez-vous" />
                <button type="submit" disabled={busy || !selectedSlot} className="w-full rounded-lg bg-[#0a5c8a] px-4 py-3 text-sm font-bold text-white disabled:opacity-50">
                  {busy ? 'Envoi de la demande…' : 'Confirmer ma demande'}
                </button>
                <p className="text-xs leading-5 text-gray-500">Votre demande reste en attente jusqu’à confirmation de la structure.</p>
              </form>
            )}
          </section>

          <aside className="h-fit rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="font-syne text-lg font-bold text-[#123a63]">Récapitulatif du devis</h2>
            <div className="mt-3 divide-y divide-gray-100">
              {booking.actes.map((act, index) => <div key={`${act.acte}-${index}`} className="flex justify-between gap-3 py-2 text-xs"><span className="text-gray-700">{act.acte}{act.quantity > 1 ? ` ×${act.quantity}` : ''}</span><span className="shrink-0 font-semibold text-gray-800">{amount(act.price)} F</span></div>)}
            </div>
            <div className="mt-3 flex justify-between border-t border-gray-100 pt-3 text-sm"><span className="font-semibold text-gray-700">Total estimé</span><strong className="text-[#123a63]">{amount(booking.total)} FCFA</strong></div>
            <p className="mt-3 text-[10px] leading-4 text-gray-500">Le créneau sera confirmé par la structure. Les tarifs sont indicatifs et peuvent être ajustés.</p>
          </aside>
        </div>
      )}
    </section>
  );
}
