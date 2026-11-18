import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Modal } from '../components/ui/Modal';
import { Button } from '../components/ui/Button';
import {
  practitionerPortalApi,
  type PractitionerAccessData,
  type PractitionerAffiliationRow,
  type PractitionerAgendaData,
  type ProviderTicket,
  type ProviderTicketsData,
} from '../lib/api';

const pageClass = 'mx-auto w-full max-w-6xl px-4 py-8 sm:px-6';
const cardClass = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900';
const inputClass = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-sky-600 dark:border-slate-700 dark:bg-slate-950 dark:text-white';
const buttonClass = 'inline-flex items-center justify-center rounded-xl bg-sky-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-60';

function Page({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <div className={pageClass}>
      <header className="mb-6">
        <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{description}</p>}
      </header>
      {children}
    </div>
  );
}

function Notice({ error, notice }: { error?: string; notice?: string }) {
  if (!error && !notice) return null;
  return <p role={error ? 'alert' : 'status'} className={`mb-4 rounded-xl px-4 py-3 text-sm ${error ? 'bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-200' : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'}`}>{error || notice}</p>;
}

function Loading() {
  return <p className="py-12 text-center text-sm text-slate-500">Chargement…</p>;
}

function failureMessage(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}

export function ProviderTicketsPage() {
  const [data, setData] = useState<ProviderTicketsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [shareTicket, setShareTicket] = useState<ProviderTicket | null>(null);
  const [shareTargets, setShareTargets] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    practitionerPortalApi.getTickets(controller.signal)
      .then((payload) => {
        setData(payload);
        setError('');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(failureMessage(reason, 'Impossible de charger les tickets.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  const reload = () => {
    setLoading(true);
    setReloadKey((key) => key + 1);
  };

  const createTicket = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await practitionerPortalApi.createTicket(new FormData(event.currentTarget));
      setNotice(result.message);
      setCreateOpen(false);
      reload();
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible de créer le ticket.'));
    } finally {
      setBusy(false);
    }
  };

  const toggleTicket = async (ticket: ProviderTicket) => {
    setError('');
    try {
      const result = await practitionerPortalApi.toggleTicket(ticket.id);
      setNotice(result.is_active ? 'Ticket activé.' : 'Ticket désactivé.');
      reload();
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible de modifier ce ticket.'));
    }
  };

  const deleteTicket = async (ticket: ProviderTicket) => {
    if (!window.confirm(`Supprimer « ${ticket.title} » ?`)) return;
    setError('');
    try {
      const result = await practitionerPortalApi.deleteTicket(ticket.id);
      setNotice(result.message);
      reload();
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible de supprimer ce ticket.'));
    }
  };

  const sendTicket = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!shareTicket || shareTargets.length === 0) return;
    const body = new FormData();
    body.set('ticket_nom', shareTicket.title);
    body.set('ticket_url', new URL(shareTicket.public_path, window.location.origin).toString());
    shareTargets.forEach((id) => body.append('conv_ids', String(id)));
    setBusy(true);
    setError('');
    try {
      const result = await practitionerPortalApi.sendTicket(body);
      setNotice(result.message);
      setShareTicket(null);
      setShareTargets([]);
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible d’envoyer ce ticket.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Tickets de prestation" description={data?.organization}>
      <div className="mb-4 flex justify-end">
        <button type="button" className={buttonClass} onClick={() => setCreateOpen(true)}>Créer un ticket</button>
      </div>
      <Notice error={error} notice={notice} />
      {loading ? <Loading /> : (
        <div className="space-y-3">
          {data?.tickets.map((ticket) => (
            <article key={ticket.id} className={`${cardClass} flex flex-wrap items-center justify-between gap-4`}>
              <div className="min-w-[220px] flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-bold">{ticket.title}</h2>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ticket.is_active ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>{ticket.is_active ? 'Actif' : 'Inactif'}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{ticket.description || ticket.acte?.name || 'Prestation personnalisée'}</p>
                <p className="mt-1 text-xs text-slate-500">{ticket.mode_label} · {ticket.zone} · {ticket.disponibilite} · {ticket.views_count} vue(s)</p>
                <p className="mt-2 font-bold">{Number(ticket.price).toLocaleString('fr-FR')} FCFA</p>
                <a className="mt-1 inline-block text-xs font-semibold text-sky-700 underline dark:text-sky-300" href={ticket.public_path} target="_blank" rel="noreferrer">Ouvrir le lien patient</a>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => setShareTicket(ticket)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700">Envoyer</button>
                <button type="button" onClick={() => void toggleTicket(ticket)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700">{ticket.is_active ? 'Désactiver' : 'Activer'}</button>
                <button type="button" onClick={() => void deleteTicket(ticket)} className="rounded-xl border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 dark:border-red-900 dark:text-red-300">Supprimer</button>
              </div>
            </article>
          ))}
          {data?.tickets.length === 0 && <div className={cardClass}><p className="text-sm text-slate-500">Aucun ticket créé.</p></div>}
        </div>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Créer un ticket de prestation">
        <form onSubmit={createTicket} className="space-y-4">
          {error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{error}</p>}
          <label className="block text-sm font-semibold">Titre de la prestation<input name="title" required maxLength={255} className={`${inputClass} mt-1`} /></label>
          <label className="block text-sm font-semibold">Description<textarea name="description" rows={3} className={`${inputClass} mt-1`} /></label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-semibold">Tarif (FCFA)<input name="price" type="number" min="0" step="1" required className={`${inputClass} mt-1`} /></label>
            <label className="block text-sm font-semibold">Modalité<select name="mode" defaultValue="domicile" className={`${inputClass} mt-1`}><option value="domicile">À domicile</option><option value="cabinet">Au cabinet</option></select></label>
          </div>
          <label className="block text-sm font-semibold">Acte rattaché (facultatif)<select name="acte_id" defaultValue="" className={`${inputClass} mt-1`}><option value="">Aucun acte précis</option>{data?.actes.map((act) => <option key={act.id} value={act.id}>{act.name} · {Number(act.price).toLocaleString('fr-FR')} FCFA</option>)}</select></label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-semibold">Zone<input name="zone" defaultValue="Dakar" maxLength={255} className={`${inputClass} mt-1`} /></label>
            <label className="block text-sm font-semibold">Disponibilité<input name="disponibilite" defaultValue="Créneaux sur demande" maxLength={120} className={`${inputClass} mt-1`} /></label>
          </div>
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" size="md" onClick={() => setCreateOpen(false)}>Annuler</Button><Button type="submit" size="md" disabled={busy}>{busy ? 'Création…' : 'Créer le ticket'}</Button></div>
        </form>
      </Modal>

      <Modal open={Boolean(shareTicket)} onClose={() => { setShareTicket(null); setShareTargets([]); }} title={`Envoyer « ${shareTicket?.title || ''} »`}>
        <form onSubmit={sendTicket} className="space-y-4">
          {error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{error}</p>}
          <ConversationPicker conversations={data?.conversations ?? []} selected={shareTargets} onChange={setShareTargets} />
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" size="md" onClick={() => setShareTicket(null)}>Annuler</Button><Button type="submit" size="md" disabled={!shareTargets.length || busy}>{busy ? 'Envoi…' : 'Envoyer le lien'}</Button></div>
        </form>
      </Modal>
    </Page>
  );
}

function ConversationPicker({
  conversations,
  selected,
  onChange,
}: {
  conversations: { id: number; patient: string; subject: string }[];
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  if (conversations.length === 0) return <p className="text-sm text-slate-500">Aucune conversation active pour l’envoi.</p>;
  return (
    <div className="max-h-72 space-y-2 overflow-y-auto">
      {conversations.map((conversation) => (
        <label key={conversation.id} className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
          <input type="checkbox" checked={selected.includes(conversation.id)} onChange={(event) => onChange(event.target.checked ? [...selected, conversation.id] : selected.filter((id) => id !== conversation.id))} />
          <span><strong className="block">{conversation.patient}</strong><span className="text-xs text-slate-500">{conversation.subject}</span></span>
        </label>
      ))}
    </div>
  );
}

export function ProviderPractitionerAccessPage() {
  const [data, setData] = useState<PractitionerAccessData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    practitionerPortalApi.getAccess(controller.signal)
      .then((payload) => {
        setData(payload);
        setError('');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(failureMessage(reason, 'Impossible de charger les affiliations.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  const reload = () => {
    setLoading(true);
    setReloadKey((key) => key + 1);
  };

  const sendAffiliation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!data) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const body = new FormData(event.currentTarget);
      const result = data.is_practitioner
        ? await practitionerPortalApi.createAffiliation(body)
        : await practitionerPortalApi.invitePractitioner(body);
      setNotice(result.message);
      reload();
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible d’envoyer cette demande.'));
    } finally {
      setBusy(false);
    }
  };

  const runAffiliationAction = async (
    action: (id: number) => Promise<{ message: string }>,
    affiliation: PractitionerAffiliationRow,
  ) => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await action(affiliation.id);
      setNotice(result.message);
      reload();
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible de mettre à jour ce rattachement.'));
    } finally {
      setBusy(false);
    }
  };

  const removeAffiliation = async (affiliation: PractitionerAffiliationRow) => {
    if (!window.confirm(`Supprimer le rattachement avec ${affiliation.name} ?`)) return;
    await runAffiliationAction(practitionerPortalApi.deleteAffiliation, affiliation);
  };

  return (
    <Page title="Accès et affiliations" description={data?.organization}>
      <Notice error={error} notice={notice} />
      {loading ? <Loading /> : !data ? null : (
        <div className="space-y-5">
          {data.is_practitioner ? (
            <section className={cardClass}>
              <h2 className="mb-3 text-lg font-bold">Demander un accès à une structure</h2>
              {data.available_structures.length === 0 ? <p className="text-sm text-slate-500">Aucune structure disponible à proximité pour le moment.</p> : (
                <form onSubmit={sendAffiliation} className="space-y-4">
                  <label className="block text-sm font-semibold">Structure<select name="structure_id" required className={`${inputClass} mt-1`}><option value="">Choisir une structure…</option>{data.available_structures.map((structure) => <option key={structure.id} value={structure.id}>{structure.name} · {structure.city}</option>)}</select></label>
                  <label className="block text-sm font-semibold">Rôle / spécialité<input name="role_title" defaultValue="Praticien consultant" maxLength={120} className={`${inputClass} mt-1`} /></label>
                  <DaysPicker days={data.days} />
                  <button type="submit" className={buttonClass} disabled={busy}>{busy ? 'Envoi…' : 'Envoyer la demande'}</button>
                </form>
              )}
            </section>
          ) : (
            <section className={cardClass}>
              <h2 className="mb-3 text-lg font-bold">Inviter un praticien</h2>
              {data.available_practitioners.length === 0 ? <p className="text-sm text-slate-500">Aucun praticien disponible à inviter pour le moment.</p> : (
                <form onSubmit={sendAffiliation} className="space-y-4">
                  <label className="block text-sm font-semibold">Praticien<select name="praticien_id" required className={`${inputClass} mt-1`}><option value="">Choisir un praticien…</option>{data.available_practitioners.map((practitioner) => <option key={practitioner.id} value={practitioner.id}>{practitioner.name}{practitioner.profession ? ` · ${practitioner.profession}` : ''}</option>)}</select></label>
                  <label className="block text-sm font-semibold">Rôle / spécialité<input name="role_title" defaultValue="Intervenant" maxLength={120} className={`${inputClass} mt-1`} /></label>
                  <DaysPicker days={data.days} />
                  <button type="submit" className={buttonClass} disabled={busy}>{busy ? 'Envoi…' : 'Envoyer l’invitation'}</button>
                </form>
              )}
            </section>
          )}

          {data.is_practitioner && data.received_invitations.length > 0 && (
            <section className={cardClass}>
              <h2 className="mb-3 text-lg font-bold">Invitations reçues</h2>
              <div className="space-y-3">{data.received_invitations.map((affiliation) => <AffiliationCard key={affiliation.id} affiliation={affiliation} actions={<><button type="button" disabled={busy} onClick={() => void runAffiliationAction(practitionerPortalApi.acceptAffiliation, affiliation)} className="rounded-xl bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">Accepter</button><button type="button" disabled={busy} onClick={() => void removeAffiliation(affiliation)} className="rounded-xl border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 dark:border-red-900 dark:text-red-300">Refuser</button></>} />)}</div>
            </section>
          )}

          <section className={cardClass}>
            <h2 className="mb-3 text-lg font-bold">{data.is_practitioner ? 'Mes structures' : 'Praticiens rattachés'}</h2>
            {data.affiliations.length === 0 ? <p className="text-sm text-slate-500">Aucun rattachement enregistré.</p> : (
              <div className="space-y-3">
                {data.affiliations.map((affiliation) => (
                  <AffiliationCard
                    key={affiliation.id}
                    affiliation={affiliation}
                    actions={(
                      <>
                        {!data.is_practitioner && affiliation.status === 'pending' && <button type="button" disabled={busy} onClick={() => void runAffiliationAction(practitionerPortalApi.approveAffiliation, affiliation)} className="rounded-xl bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">Valider</button>}
                        {affiliation.agenda_url && <Link to={affiliation.agenda_url} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700">Agenda</Link>}
                        <button type="button" disabled={busy} onClick={() => void removeAffiliation(affiliation)} className="rounded-xl border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 dark:border-red-900 dark:text-red-300">Supprimer</button>
                      </>
                    )}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </Page>
  );
}

function DaysPicker({ days }: { days: string[] }) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold">Jours / disponibilités souhaités (facultatif)</legend>
      <div className="flex flex-wrap gap-2">{days.map((day) => <label key={day} className="flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs dark:border-slate-700"><input name="days" type="checkbox" value={day} />{day}</label>)}</div>
    </fieldset>
  );
}

function AffiliationCard({ affiliation, actions }: { affiliation: PractitionerAffiliationRow; actions: ReactNode }) {
  return (
    <article className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
      <div><h3 className="font-bold">{affiliation.name}</h3><p className="mt-1 text-sm text-slate-500">{affiliation.role_title || 'Rôle non précisé'} · {affiliation.city}</p><p className="mt-1 text-xs text-slate-500">{affiliation.status_label}{affiliation.days_schedule.length ? ` · ${affiliation.days_schedule.join(', ')}` : ''}</p></div>
      <div className="flex flex-wrap gap-2">{actions}</div>
    </article>
  );
}

export function ProviderPractitionerAgendaPage() {
  const { affiliationId } = useParams();
  const id = Number(affiliationId);
  const [data, setData] = useState<PractitionerAgendaData | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    practitionerPortalApi.getPractitionerAgenda(id, controller.signal)
      .then((payload) => {
        setData(payload);
        setSelected(payload.active_slots);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(failureMessage(reason, 'Impossible de charger cet agenda.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [id]);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = new FormData();
    selected.forEach((slot) => body.append('slots', slot));
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await practitionerPortalApi.savePractitionerAgenda(id, body);
      setNotice(result.message);
    } catch (reason) {
      setError(failureMessage(reason, 'Impossible d’enregistrer cet agenda.'));
    } finally {
      setSaving(false);
    }
  };

  const toggleSlot = (slot: string) => setSelected((current) => current.includes(slot)
    ? current.filter((value) => value !== slot)
    : [...current, slot]);

  return (
    <Page title="Agenda du praticien" description={data ? `${data.organization} · ${data.structure}` : undefined}>
      <Link to="/sante/prestataire/acces/" className="mb-4 inline-block text-sm font-semibold text-sky-700 underline dark:text-sky-300">Retour aux affiliations</Link>
      <Notice error={error} notice={notice} />
      {loading ? <Loading /> : !data ? null : (
        <form onSubmit={save} className={cardClass}>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-bold">Disponibilités hebdomadaires</h2><span className="text-sm text-slate-500">{selected.length} créneau(x) sélectionné(s)</span></div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead><tr><th className="p-2 text-left">Heure</th>{data.days.map((day) => <th key={day} className="p-2 text-center">{day}</th>)}</tr></thead>
              <tbody>{data.hours.map((hour) => <tr key={hour} className="border-t border-slate-100 dark:border-slate-800"><th className="p-2 text-left font-semibold">{hour}</th>{data.days.map((day) => { const slot = `${day}_${hour}`; return <td key={slot} className="p-2 text-center"><input type="checkbox" aria-label={`${day} ${hour}`} checked={selected.includes(slot)} onChange={() => toggleSlot(slot)} /></td>; })}</tr>)}</tbody>
            </table>
          </div>
          <button type="submit" className={`${buttonClass} mt-5`} disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer mon agenda'}</button>
        </form>
      )}
    </Page>
  );
}
