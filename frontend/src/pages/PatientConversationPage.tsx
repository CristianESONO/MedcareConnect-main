import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarDays, Paperclip, Send, X } from 'lucide-react';
import { appointmentsApi, patientAccountApi, type PatientThreadData } from '../lib/api';
import { getCsrfToken } from '../lib/auth';

function formatAmount(value: string) {
  const amount = Number(value);
  return Number.isFinite(amount) ? amount.toLocaleString('fr-FR') : '0';
}

function formatStatus(statusClass: string) {
  switch (statusClass) {
    case 'wait':
      return 'bg-amber-50 text-amber-800';
    case 'done':
      return 'bg-blue-50 text-blue-800';
    case 'expired':
      return 'bg-gray-100 text-gray-700';
    default:
      return 'bg-emerald-50 text-emerald-800';
  }
}

export function PatientConversationPage() {
  const { conversationId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const conversationRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<PatientThreadData | null>(null);
  const [loadedKey, setLoadedKey] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [attachment, setAttachment] = useState<File | null>(null);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [bookingNote, setBookingNote] = useState('');
  const invalidConversationId = !conversationId || !/^\d+$/.test(conversationId);
  const visibleError = error || (invalidConversationId ? 'Conversation introuvable.' : '');
  const loadKey = `${conversationId || ''}${location.search}`;
  const loading = loadedKey !== loadKey && !visibleError;

  useEffect(() => {
    const controller = new AbortController();
    if (invalidConversationId || !conversationId) return () => controller.abort();
    patientAccountApi.conversation(
      Number(conversationId),
      location.search,
      controller.signal,
    )
      .then((response) => {
        if (!controller.signal.aborted) {
          setData(response);
          setLoadedKey(`${conversationId}${location.search}`);
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger cette conversation.');
        }
      });
    return () => controller.abort();
  }, [conversationId, invalidConversationId, location.search]);

  useEffect(() => {
    if (loadedKey === loadKey && conversationRef.current) {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
    }
  }, [data, loadedKey, loadKey]);

  const refresh = async (query = location.search) => {
    if (!conversationId) return;
    const key = `${conversationId}${query}`;
    const response = await patientAccountApi.conversation(
      Number(conversationId),
      query,
    );
    setData(response);
    setLoadedKey(key);
  };

  const submitMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!conversationId || busy) return;
    const formData = new FormData();
    formData.set('content', message);
    if (attachment) formData.set('attachment', attachment);

    setBusy(true);
    setError('');
    try {
      await patientAccountApi.sendMessage(Number(conversationId), formData);
      setMessage('');
      setAttachment(null);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’envoyer ce message.');
    } finally {
      setBusy(false);
    }
  };

  const submitBooking = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!data?.conversation.booking_url || !selectedSlot || busy) return;
    const formData = new FormData();
    formData.set('slot', selectedSlot);
    formData.set('note', bookingNote);
    if (data.conversation.show_reschedule) {
      formData.set('next', data.conversation.url);
    }

    setBusy(true);
    setError('');
    try {
      const csrfToken = await getCsrfToken();
      const response = await fetch(data.conversation.booking_url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: formData,
      });
      const result = await response.json() as { error?: string; message?: string };
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      setBookingNote('');
      setSelectedSlot('');
      navigate(location.pathname, { replace: true });
      await refresh('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer ce créneau.');
    } finally {
      setBusy(false);
    }
  };

  const cancelAppointment = async () => {
    if (!data?.conversation.rdv_reference || busy) return;
    if (!window.confirm('Confirmez-vous l’annulation de ce rendez-vous ?')) return;
    setBusy(true);
    setError('');
    try {
      await appointmentsApi.cancelPatientAppointment(data.conversation.rdv_reference);
      navigate(location.pathname, { replace: true });
      await refresh('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’annuler ce rendez-vous.');
    } finally {
      setBusy(false);
    }
  };

  const booking = data?.conversation.booking_data;
  const slotOptions = booking?.days.flatMap((day) => day.slots
    .filter((slot) => slot.available)
    .map((slot) => ({
      value: slot.value,
      label: `${day.label} · ${slot.label}`,
    }))) || [];

  return (
    <section className="mx-auto flex h-[calc(100dvh-4.5rem)] min-h-0 w-full max-w-4xl flex-col px-3 py-3 sm:px-4 sm:py-5">
      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement de la conversation…
        </p>
      )}
      {visibleError && (
        <p className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
          {visibleError}
          {visibleError.includes('Authentification') && (
            <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">
              Se connecter
            </Link>
          )}
        </p>
      )}

      {!loading && data && (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <header className="flex items-center gap-3 border-b border-gray-100 bg-white px-3 py-3 sm:px-5">
            <Link
              to="/messaging/"
              aria-label="Retour à la liste des messages"
              className="flex size-9 shrink-0 items-center justify-center rounded-full text-gray-600 hover:bg-gray-100"
            >
              <ArrowLeft size={20} aria-hidden="true" />
            </Link>
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sm font-bold text-[#0a5c8a]">
              {data.conversation.initial}
            </span>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-sm font-bold text-[#123a63] sm:text-base">
                Secrétariat de {data.conversation.organization}
              </h1>
              <p className="truncate text-xs text-gray-500">
                {data.conversation.subject}{data.conversation.city ? ` · ${data.conversation.city}` : ''}
              </p>
            </div>
            <span className={`hidden shrink-0 rounded-full px-3 py-1 text-[10px] font-bold sm:inline-flex ${formatStatus(data.conversation.status_banner?.class || 'ok')}`}>
              {data.conversation.status_banner?.text || data.conversation.status}
            </span>
          </header>

          {data.conversation.status_banner && (
            <p className={`border-b border-gray-100 px-4 py-2 text-center text-xs font-semibold sm:hidden ${formatStatus(data.conversation.status_banner.class)}`}>
              {data.conversation.status_banner.text}
            </p>
          )}

          <div ref={conversationRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-[#f5f7fa] px-3 py-4 sm:px-6">
            {data.devis && (
              <>
                <div className="mx-auto w-fit rounded-full bg-gray-200/80 px-3 py-1 text-[10px] font-semibold text-gray-600">
                  Estimation · {new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(data.devis.created_at))}
                </div>
                <div className="ml-auto max-w-[90%] rounded-2xl rounded-tr-sm bg-[#0a5c8a] p-3 text-sm text-white sm:max-w-[75%]">
                  Bonjour, je souhaite un devis pour {data.devis.lines.length} acte{data.devis.lines.length !== 1 ? 's' : ''} via MedCare.
                </div>
                <article className="max-w-[95%] overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm sm:max-w-[82%]">
                  <header className="flex items-center justify-between bg-[#123a63] px-4 py-3 text-white">
                    <span className="font-syne text-sm font-extrabold">Med<span className="text-sky-300">Care</span></span>
                    <span className="font-mono text-[10px]">Réf. {data.devis.reference}</span>
                  </header>
                  <div className="space-y-3 p-4">
                    <div className="flex justify-between gap-3 text-xs">
                      <span className="text-gray-500">Structure</span>
                      <span className="text-right font-semibold text-gray-800">{data.devis.organization || '—'}</span>
                    </div>
                    {(data.devis.city || data.devis.quartier) && (
                      <div className="flex justify-between gap-3 text-xs">
                        <span className="text-gray-500">Zone</span>
                        <span className="text-right font-semibold text-gray-800">
                          {[data.devis.city, data.devis.quartier].filter(Boolean).join(', ')}
                        </span>
                      </div>
                    )}
                    <div className="border-t border-gray-100 pt-2">
                      <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-gray-500">
                        {data.devis.lines.length} acte{data.devis.lines.length !== 1 ? 's' : ''}
                      </p>
                      {data.devis.lines.map((line, index) => (
                        <div key={`${line.name}-${index}`} className="flex justify-between gap-3 py-1.5 text-xs">
                          <span className="text-gray-700">{line.name}{line.quantity > 1 ? ` ×${line.quantity}` : ''}</span>
                          <span className="shrink-0 font-semibold text-gray-800">{formatAmount(line.price)} FCFA</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-between bg-sky-50 px-4 py-3 text-sm">
                    <span className="font-semibold text-gray-700">Total estimé</span>
                    <strong className="text-[#123a63]">{formatAmount(data.devis.total_patient)} FCFA</strong>
                  </div>
                  <p className="px-4 py-2 text-[10px] leading-4 text-gray-500">
                    Montants indicatifs, sous validation du prestataire de santé et de votre assureur.
                  </p>
                </article>
              </>
            )}

            {data.timeline.map((item, index) => {
              if (item.kind === 'date') {
                return (
                  <div key={`date-${item.label}-${index}`} className="mx-auto w-fit rounded-full bg-gray-200/80 px-3 py-1 text-[10px] font-semibold text-gray-600">
                    {item.label}
                  </div>
                );
              }
              const systemMessage = item.message_type === 'system';
              const fromPatient = Boolean(item.from_patient);
              const statusCard = item.message_type === 'status_card';
              return (
                <div
                  key={item.id}
                  className={`flex ${systemMessage ? 'justify-center' : fromPatient ? 'justify-end' : 'justify-start'}`}
                >
                  <article className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm shadow-sm sm:max-w-[75%] ${
                    systemMessage
                      ? 'bg-gray-200/80 text-center text-xs text-gray-600 shadow-none'
                      : statusCard
                        ? 'border border-sky-100 bg-white text-gray-800'
                        : fromPatient
                          ? 'rounded-tr-sm bg-[#0a5c8a] text-white'
                          : 'rounded-tl-sm border border-gray-100 bg-white text-gray-800'
                  }`}>
                    {!systemMessage && item.sender && (
                      <p className={`mb-1 text-[10px] font-bold ${fromPatient ? 'text-sky-100' : 'text-[#0a5c8a]'}`}>
                        {item.sender}
                      </p>
                    )}
                    {item.content && <p className="whitespace-pre-wrap break-words">{item.content}</p>}
                    {item.payload?.type === 'panel_link' && (
                      <a href={String(item.payload.panel_url || (item.payload.panel_token ? `/t/${item.payload.panel_token}/` : '#'))} className="mt-2 inline-flex rounded-lg bg-white px-3 py-2 text-xs font-bold text-[#0a5c8a]">
                        Ouvrir le panel →
                      </a>
                    )}
                    {item.attachment_url && (
                      <a
                        href={item.attachment_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`mt-2 block break-all text-xs underline ${fromPatient ? 'text-sky-100' : 'text-[#0a5c8a]'}`}
                      >
                        📎 {item.attachment_name || 'Pièce jointe'}
                      </a>
                    )}
                    {item.time_label && !systemMessage && (
                      <p className={`mt-1 text-right text-[9px] ${fromPatient ? 'text-sky-100/80' : 'text-gray-400'}`}>
                        {item.time_label}
                      </p>
                    )}
                  </article>
                </div>
              );
            })}

            {data.conversation.show_book || data.conversation.show_reschedule ? (
              <section className="mx-auto w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                <h2 className="flex items-center gap-2 font-bold text-[#123a63]">
                  <CalendarDays size={18} aria-hidden="true" />
                  {data.conversation.show_reschedule ? 'Modifier le créneau' : 'Prendre un rendez-vous'}
                </h2>
                {!data.conversation.has_slots ? (
                  <p className="mt-3 text-sm text-gray-600">
                    Aucun créneau disponible en ligne pour le moment. La structure vous recontactera.
                  </p>
                ) : (
                  <form onSubmit={submitBooking} className="mt-3 space-y-3">
                    <label className="block text-xs font-semibold text-gray-700">
                      Choisir un créneau
                      <select
                        required
                        value={selectedSlot}
                        onChange={(event) => setSelectedSlot(event.target.value)}
                        className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm font-normal text-gray-900"
                      >
                        <option value="">Sélectionnez une date et une heure</option>
                        {booking?.soonest && <option value="asap">Au plus vite · {booking.soonest.label}</option>}
                        {slotOptions.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                    <label className="block text-xs font-semibold text-gray-700">
                      Note (facultative)
                      <input
                        value={bookingNote}
                        onChange={(event) => setBookingNote(event.target.value)}
                        maxLength={200}
                        className="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-normal text-gray-900"
                        placeholder="Précision pour la structure"
                      />
                    </label>
                    <button disabled={busy || !selectedSlot} className="w-full rounded-lg bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">
                      {busy ? 'Envoi…' : data.conversation.show_reschedule ? 'Demander ce nouveau créneau' : 'Demander ce rendez-vous'}
                    </button>
                  </form>
                )}
              </section>
            ) : null}
          </div>

          {(data.conversation.can_book || data.conversation.can_reschedule || data.conversation.can_cancel) && (
            <div className="flex flex-wrap gap-2 border-t border-gray-100 bg-white px-3 py-3 sm:px-5">
              {data.conversation.can_book && !data.conversation.show_book && (
                <Link to="?book=1" className="rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white">
                  Prendre rendez-vous
                </Link>
              )}
              {data.conversation.can_reschedule && !data.conversation.show_reschedule && (
                <Link to="?reschedule=1" className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-bold text-gray-700">
                  Modifier le créneau
                </Link>
              )}
              {data.conversation.can_cancel && (
                <button type="button" onClick={cancelAppointment} disabled={busy} className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700 disabled:opacity-50">
                  <X size={14} aria-hidden="true" />
                  Annuler le RDV
                </button>
              )}
            </div>
          )}

          {data.conversation.closed ? (
            <p className="border-t border-gray-100 bg-gray-50 px-4 py-3 text-center text-xs text-gray-500">
              Cette conversation est clôturée.
            </p>
          ) : data.conversation.can_send_free_message || data.conversation.can_attach ? (
            <form onSubmit={submitMessage} className="flex items-end gap-2 border-t border-gray-100 bg-white p-3 sm:p-4">
              {data.conversation.can_attach && (
                <label className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full text-gray-500 hover:bg-gray-100" title="Joindre un fichier">
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,image/*,application/pdf"
                    className="sr-only"
                    onChange={(event) => setAttachment(event.target.files?.[0] || null)}
                  />
                  <Paperclip size={19} aria-hidden="true" />
                </label>
              )}
              <div className="min-w-0 flex-1">
                {attachment && (
                  <div className="mb-1 flex items-center justify-between gap-2 text-[10px] text-gray-500">
                    <span className="truncate">{attachment.name}</span>
                    <button type="button" onClick={() => setAttachment(null)} className="font-bold text-red-600">Retirer</button>
                  </div>
                )}
                <input
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  maxLength={500}
                  disabled={!data.conversation.can_send_free_message}
                  placeholder={data.conversation.can_send_free_message ? 'Écrire un message…' : 'Joindre un document…'}
                  className="w-full rounded-full border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-900 outline-none focus:border-sky-400 disabled:opacity-70"
                />
              </div>
              <button
                type="submit"
                disabled={busy || (!message.trim() && !attachment)}
                aria-label="Envoyer"
                className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#0a5c8a] text-white hover:bg-[#084b70] disabled:opacity-50"
              >
                <Send size={17} aria-hidden="true" />
              </button>
            </form>
          ) : null}
        </div>
      )}
    </section>
  );
}
