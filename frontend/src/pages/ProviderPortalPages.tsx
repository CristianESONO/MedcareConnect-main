import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import {
  providerPortalApi,
  type DjangoFormField,
  type ProviderAnalyticsData,
  type ProviderReminder,
} from '../lib/api';

const pageClass = 'mx-auto w-full max-w-6xl px-4 py-8 sm:px-6';
const cardClass = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900';
const inputClass = 'w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-sky-600 dark:border-slate-700 dark:bg-slate-950 dark:text-white';
const buttonClass = 'inline-flex items-center justify-center rounded-xl bg-sky-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-60';

function useRemote<T>(loader: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    loader(controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger cette page.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [loader, refreshKey]);

  return {
    data,
    loading,
    error,
    setData,
    version: refreshKey,
    reload: () => {
      setLoading(true);
      setError('');
      setRefreshKey((key) => key + 1);
    },
    setError,
  };
}

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

function Message({ error, notice }: { error?: string; notice?: string }) {
  if (!error && !notice) return null;
  return (
    <p
      role={error ? 'alert' : 'status'}
      className={`mb-4 rounded-xl px-4 py-3 text-sm ${error ? 'bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-200' : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'}`}
    >
      {error || notice}
    </p>
  );
}

function Loading() {
  return <p className="py-12 text-center text-sm text-slate-500">Chargement…</p>;
}

function FieldInput({ field }: { field: DjangoFormField }) {
  const selected = Array.isArray(field.value) ? field.value.map(String) : [String(field.value ?? '')];
  if (field.type === 'hidden') {
    return <input type="hidden" name={field.name} value={String(field.value ?? '')} />;
  }
  if (field.type === 'checkbox') {
    return (
      <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
        <input type="checkbox" name={field.name} defaultChecked={Boolean(field.value)} required={field.required} />
        {field.label}
      </label>
    );
  }
  if (field.type === 'checkboxes') {
    return (
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">{field.label}</legend>
        {field.choices.map((choice) => (
          <label key={`${field.name}-${choice.value}`} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input type="checkbox" name={field.name} value={choice.value} defaultChecked={selected.includes(choice.value)} />
            {choice.label}
          </label>
        ))}
      </fieldset>
    );
  }
  if (field.type === 'textarea') {
    return (
      <textarea
        id={`field-${field.name}`}
        name={field.name}
        defaultValue={String(field.value ?? '')}
        required={field.required}
        rows={4}
        className={inputClass}
      />
    );
  }
  if (field.type === 'select') {
    const multiple = Array.isArray(field.value);
    return (
      <select
        id={`field-${field.name}`}
        name={field.name}
        defaultValue={multiple ? selected : selected[0]}
        required={field.required}
        multiple={multiple}
        className={`${inputClass}${multiple ? ' min-h-32' : ''}`}
      >
        {!multiple && <option value="">Sélectionner…</option>}
        {field.choices.map((choice) => (
          <option key={`${field.name}-${choice.value}`} value={choice.value}>{choice.label}</option>
        ))}
      </select>
    );
  }
  const inputType = ['file', 'email', 'tel', 'number', 'url', 'date', 'time', 'password'].includes(field.type)
    ? field.type
    : 'text';
  return (
    <input
      id={`field-${field.name}`}
      type={inputType}
      name={field.name}
      defaultValue={inputType === 'file' || inputType === 'password' ? undefined : String(field.value ?? '')}
      required={field.required}
      className={inputClass}
    />
  );
}

function DynamicFields({ fields }: { fields: DjangoFormField[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((field) => (
        <div key={field.name} className={field.type === 'textarea' || field.type === 'checkboxes' ? 'sm:col-span-2' : ''}>
          {field.type !== 'checkbox' && field.type !== 'hidden' && field.type !== 'checkboxes' && (
            <label htmlFor={`field-${field.name}`} className="mb-1.5 block text-sm font-semibold text-slate-800 dark:text-slate-100">
              {field.label}{field.required && <span className="text-red-600"> *</span>}
            </label>
          )}
          <FieldInput field={field} />
          {field.help_text && <p className="mt-1 text-xs text-slate-500">{field.help_text}</p>}
        </div>
      ))}
    </div>
  );
}

function getError(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}

export function ProviderInsurancePage() {
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getInsurance(signal), []);
  const { data, loading, error, reload, setError } = useRemote(load);
  const [selectedOverride, setSelectedOverride] = useState<number[] | null>(null);
  const [tarifsOverride, setTarifsOverride] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);

  const selected = selectedOverride ?? data?.selected_ids ?? [];
  const tarifs = tarifsOverride ?? data?.tarifs_delais ?? '';

  const toggle = (id: number) => setSelectedOverride((current) => {
    const rows = current ?? data?.selected_ids ?? [];
    return rows.includes(id) ? rows.filter((item) => item !== id) : [...rows, id];
  });

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = new FormData();
    body.set('action', 'save_assurances');
    body.set('assurances_tarifs_delais', tarifs);
    selected.forEach((id) => body.append('assurance_ids', String(id)));
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await providerPortalApi.saveInsurance(body);
      setNotice(result.message);
    } catch (reason) {
      setError(getError(reason, 'Impossible d’enregistrer les assurances.'));
    } finally {
      setSaving(false);
    }
  };

  const addCustom = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const body = new FormData(event.currentTarget);
    body.set('action', 'add_custom_assurance');
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await providerPortalApi.addInsurance(body);
      setNotice(result.message);
      setSelectedOverride(null);
      setTarifsOverride(null);
      reload();
    } catch (reason) {
      setError(getError(reason, 'Impossible d’ajouter cette assurance.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page title="Assurances acceptées" description={data?.organization}>
      {loading ? <Loading /> : (
        <>
          <Message error={error} notice={notice} />
          <form onSubmit={save} className="space-y-5">
            <section className={cardClass}>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-bold">Catalogue des assurances</h2>
                <span className="rounded-full bg-sky-50 px-3 py-1 text-sm font-semibold text-sky-800 dark:bg-sky-950 dark:text-sky-200">
                  {selected.length} sélectionnée(s)
                </span>
              </div>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher une assurance" className={`${inputClass} mb-5`} />
              <div className="space-y-6">
                {data?.segments.map((segment) => {
                  const rows = segment.assurances.filter((insurance) => `${insurance.name} ${insurance.description}`.toLocaleLowerCase('fr').includes(search.trim().toLocaleLowerCase('fr')));
                  if (rows.length === 0) return null;
                  return (
                    <div key={segment.segment}>
                      <div className="mb-3 flex items-center justify-between border-b border-slate-200 pb-2 dark:border-slate-700">
                        <div>
                          <h3 className="font-bold">{segment.title}</h3>
                          <p className="text-xs text-slate-500">{segment.hint}</p>
                        </div>
                        <span className="text-xs text-slate-500">{segment.assurances.filter((insurance) => selected.includes(insurance.id)).length}/{segment.total_count}</span>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {rows.map((insurance) => (
                          <label key={insurance.id} className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 p-3 text-sm hover:border-sky-400 dark:border-slate-700">
                            <input type="checkbox" checked={selected.includes(insurance.id)} onChange={() => toggle(insurance.id)} />
                            <span><span className="font-semibold">{insurance.name}</span>{insurance.description && <span className="mt-0.5 block text-xs text-slate-500">{insurance.description}</span>}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
            <section className={cardClass}>
              <label htmlFor="insurance-tarifs" className="mb-2 block font-bold">Tarifs et délais</label>
              <textarea id="insurance-tarifs" value={tarifs} onChange={(event) => setTarifsOverride(event.target.value)} rows={4} className={inputClass} />
              <button type="submit" className={`${buttonClass} mt-4`} disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer les assurances'}</button>
            </section>
          </form>
          <form onSubmit={addCustom} className={`${cardClass} mt-5`}>
            <h2 className="mb-3 text-lg font-bold">Ajouter une assurance locale</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <input name="name" required placeholder="Nom de l’assurance" className={inputClass} />
              <select name="segment" required className={inputClass}>
                <option value="">Type d’assurance…</option>
                {data?.segment_choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
              </select>
              <input name="description" placeholder="Description (facultative)" className={`${inputClass} sm:col-span-2`} />
            </div>
            <button type="submit" className={`${buttonClass} mt-3`} disabled={saving}>Ajouter</button>
          </form>
        </>
      )}
    </Page>
  );
}

export function ProviderHoursPage() {
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getHours(signal), []);
  const { data, loading, error, setError } = useRemote(load);
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await providerPortalApi.saveHours(new FormData(event.currentTarget));
      setNotice(result.message);
    } catch (reason) {
      setError(getError(reason, 'Impossible d’enregistrer les horaires.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page title="Horaires d’ouverture" description={data?.organization}>
      {loading ? <Loading /> : (
        <>
          <Message error={error} notice={notice} />
          <form onSubmit={submit} className={`${cardClass} space-y-3`}>
            <div className="hidden grid-cols-[1fr_1fr_1fr_auto] gap-3 px-2 text-xs font-bold uppercase text-slate-500 sm:grid">
              <span>Jour</span><span>Ouverture</span><span>Fermeture</span><span>Fermé</span>
            </div>
            {data?.days.map((day) => (
              <div key={day.name} className="grid items-center gap-2 rounded-xl border border-slate-100 p-3 dark:border-slate-800 sm:grid-cols-[1fr_1fr_1fr_auto]">
                <strong className="text-sm">{day.name}</strong>
                <label className="text-xs text-slate-500">Ouverture<input name={`${day.name}_open`} type="time" defaultValue={day.open} className={inputClass} /></label>
                <label className="text-xs text-slate-500">Fermeture<input name={`${day.name}_close`} type="time" defaultValue={day.close} className={inputClass} /></label>
                <label className="flex items-center gap-2 text-sm"><input name={`${day.name}_closed`} type="checkbox" defaultChecked={day.closed} />Fermé</label>
              </div>
            ))}
            <button type="submit" className={buttonClass} disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer les horaires'}</button>
          </form>
        </>
      )}
    </Page>
  );
}

function OrganizationFormPage({ create = false }: { create?: boolean }) {
  const url = create ? '/sante/prestataire/organisme/creer/' : '/sante/prestataire/organisme/modifier/';
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getOrganizationForm(url, signal), [url]);
  const { data, loading, error, setError } = useRemote(load);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  if (data?.redirect) return <Navigate to={data.redirect} replace />;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const result = await providerPortalApi.saveOrganizationForm(url, new FormData(event.currentTarget));
      navigate(result.redirect);
    } catch (reason) {
      setError(getError(reason, 'Impossible d’enregistrer la fiche.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page title={create ? 'Créer la fiche de votre structure' : 'Fiche de la structure'} description={data?.organization}>
      {loading ? <Loading /> : (
        <>
          <Message error={error} />
          {data?.profile_completion !== undefined && (
            <div className={`${cardClass} mb-4`}>
              <div className="mb-2 flex justify-between text-sm"><span>Complétion du profil</span><strong>{data.profile_completion}%</strong></div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${data.profile_completion}%` }} /></div>
            </div>
          )}
          <form onSubmit={submit} encType="multipart/form-data" className={`${cardClass} space-y-5`}>
            {data?.logo_url && <img src={data.logo_url} alt="Logo actuel" className="h-20 w-20 rounded-xl object-cover" />}
            {data?.fields && <DynamicFields fields={data.fields} />}
            <div className="flex flex-wrap gap-3">
              <button type="submit" className={buttonClass} disabled={saving}>{saving ? 'Enregistrement…' : create ? 'Créer ma fiche' : 'Enregistrer les modifications'}</button>
              {!create && <Link to="/sante/prestataire/profil-public/" className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold dark:border-slate-700">Aperçu du profil public</Link>}
            </div>
          </form>
        </>
      )}
    </Page>
  );
}

export function ProviderOrganizationCreatePage() {
  return <OrganizationFormPage create />;
}

export function ProviderOrganizationEditPage() {
  return <OrganizationFormPage />;
}

export function ProviderPublicProfilePage() {
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getPublicProfile(signal), []);
  const { data, loading, error } = useRemote(load);
  if (loading) return <Page title="Profil public"><Loading /></Page>;
  if (!data) return <Page title="Profil public"><Message error={error} /></Page>;
  return (
    <Page title="Aperçu du profil public" description={data.organization.name}>
      <Message error={error} />
      <section className={`${cardClass} overflow-hidden p-0`}>
        <div className="bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white">
          <div className="flex items-center gap-4">
            {data.organization.logo_url && <img src={data.organization.logo_url} alt="" className="h-16 w-16 rounded-2xl bg-white object-contain p-1" />}
            <div><h2 className="text-xl font-black">{data.organization.name}</h2><p>{data.organization.address}{data.organization.city ? `, ${data.organization.city}` : ''}</p></div>
          </div>
          {data.show_pioneer_badge && <span className="mt-4 inline-block rounded-full bg-amber-300 px-3 py-1 text-xs font-bold text-amber-950">Structure pionnière</span>}
        </div>
        <div className="space-y-6 p-5">
          <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-200">{data.organization.description || 'Aucune description renseignée.'}</p>
          <div className="flex flex-wrap gap-2 text-sm">
            {data.organization.phone && <a className="rounded-full bg-slate-100 px-3 py-1 dark:bg-slate-800" href={`tel:${data.organization.phone}`}>{data.organization.phone}</a>}
            {data.organization.website && <a className="rounded-full bg-slate-100 px-3 py-1 dark:bg-slate-800" href={data.organization.website} target="_blank" rel="noreferrer">Site web</a>}
            {data.maps_url && <a className="rounded-full bg-slate-100 px-3 py-1 dark:bg-slate-800" href={data.maps_url} target="_blank" rel="noreferrer">Itinéraire</a>}
            {data.whatsapp_url && <a className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200" href={data.whatsapp_url} target="_blank" rel="noreferrer">WhatsApp</a>}
          </div>
          {data.hours.length > 0 && <div><h3 className="mb-2 font-bold">Horaires</h3><div className="grid gap-2 sm:grid-cols-2">{data.hours.map((row, index) => <div key={`${row.day}-${index}`} className="flex justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800"><span>{row.day}</span><strong>{row.hours}</strong></div>)}</div></div>}
          {data.insurances.length > 0 && <div><h3 className="mb-2 font-bold">Assurances</h3><div className="flex flex-wrap gap-2">{data.insurances.map((insurance, index) => <span key={`${insurance.name}-${index}`} className="rounded-full bg-sky-50 px-3 py-1 text-xs text-sky-800 dark:bg-sky-950 dark:text-sky-200">{insurance.name}</span>)}</div></div>}
          {data.pillars.map((pillar) => (
            <div key={pillar.id}><h3 className="mb-2 font-bold">{pillar.name}</h3><div className="grid gap-3 sm:grid-cols-2">{pillar.actes.map((act, index) => <article key={`${act.name}-${index}`} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"><strong>{act.name}</strong>{data.show_prices && <p className="text-sm text-slate-600 dark:text-slate-300">{act.price} FCFA · {act.delai}</p>}</article>)}</div></div>
          ))}
          <div className="border-t border-slate-200 pt-4 dark:border-slate-700"><p className="text-sm text-slate-500">{data.actes_visible_count} prestation(s) visible(s)</p><a className="mt-2 inline-block text-sm font-semibold text-sky-700 underline dark:text-sky-300" href={data.public_url} target="_blank" rel="noreferrer">Ouvrir la fiche publique</a></div>
        </div>
      </section>
      <Link to="/sante/prestataire/organisme/modifier/" className={`${buttonClass} mt-4`}>Modifier la fiche</Link>
    </Page>
  );
}

export function ProviderTypeSetupPage() {
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getTypeSetup(signal), []);
  const { data, loading, error, setError } = useRemote(load);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');
  const [topologyTypeOverride, setTopologyTypeOverride] = useState<string | null>(null);
  const [selectedPillarsOverride, setSelectedPillarsOverride] = useState<number[] | null>(null);
  const navigate = useNavigate();
  const topologyType = topologyTypeOverride ?? data?.topology_type ?? '';
  const selectedPillars = selectedPillarsOverride
    ?? data?.pillars.filter((pillar) => pillar.active).map((pillar) => pillar.id)
    ?? [];
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form);
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await providerPortalApi.saveTypeSetup(body);
      setNotice(result.message);
      navigate('/sante/prestataire/tableau-de-bord/');
    } catch (reason) {
      setError(getError(reason, 'Impossible d’enregistrer la configuration.'));
    } finally {
      setSaving(false);
    }
  };
  const chooseType = (name: string) => {
    setTopologyTypeOverride(name);
    const suggestions = data?.type_pillars_map[name];
    if (suggestions) setSelectedPillarsOverride(suggestions);
  };
  return (
    <Page title="Configuration de l’établissement" description={data?.organization}>
      {loading ? <Loading /> : !data ? <Message error={error} /> : (
        <>
          <Message error={error} notice={notice} />
          <form onSubmit={submit} className="space-y-5">
            <section className={cardClass}>
              <h2 className="mb-3 text-lg font-bold">Type d’établissement</h2>
              <label className="mb-1 block text-sm font-semibold" htmlFor="topology-type">Type / organisation</label>
              <input id="topology-type" name="topology_type" value={topologyType} onChange={(event) => setTopologyTypeOverride(event.target.value)} className={inputClass} />
              <div className="mt-3 flex flex-wrap gap-2">{data.types.map((type) => <button key={type.name} type="button" onClick={() => chooseType(type.name)} className="rounded-full border border-slate-300 px-3 py-1.5 text-sm hover:border-sky-500 dark:border-slate-700">{type.icon} {type.name}{type.proposed ? ' · proposé' : ''}</button>)}</div>
              <label className="mb-1 mt-4 block text-sm font-semibold" htmlFor="type-libre">Précision (facultative)</label>
              <input id="type-libre" name="type_libre" defaultValue={data.type_libre} className={inputClass} />
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  ['name', 'Nom', data.organization],
                  ['address', 'Adresse', data.address],
                  ['city', 'Ville', data.city],
                  ['ninea', 'NINEA', data.ninea],
                ].map(([name, label, value]) => <label key={name} className="text-sm font-semibold">{label}<input name={name} defaultValue={value} className={`${inputClass} mt-1`} /></label>)}
              </div>
            </section>
            <section className={cardClass}>
              <h2 className="mb-1 text-lg font-bold">Domaines d’activité</h2>
              <p className="mb-4 text-sm text-slate-500">Choisissez les services proposés par votre structure.</p>
              <div className="grid gap-2 sm:grid-cols-2">{data.pillars.map((pillar) => <label key={pillar.id} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700"><input type="checkbox" name="piliers" value={pillar.id} checked={selectedPillars.includes(pillar.id)} onChange={(event) => setSelectedPillarsOverride((current) => { const rows = current ?? data.pillars.filter((item) => item.active).map((item) => item.id); return event.target.checked ? [...rows, pillar.id] : rows.filter((id) => id !== pillar.id); })} /><span>{pillar.icon} {pillar.name}</span></label>)}</div>
            </section>
            <button type="submit" className={buttonClass} disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer la configuration'}</button>
          </form>
        </>
      )}
    </Page>
  );
}

export function ProviderSettingsPage() {
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getSettings(signal), []);
  const { data, loading, error, reload, setError, version } = useRemote(load);
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form);
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    if (submitter instanceof HTMLButtonElement && submitter.name) body.set(submitter.name, submitter.value);
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await providerPortalApi.saveSettings(body);
      if (!result.ok) throw new Error(result.errors?.join(' ') || 'Vérifiez les informations saisies.');
      setNotice(result.message || 'Paramètres enregistrés.');
      reload();
    } catch (reason) {
      setError(getError(reason, 'Impossible d’enregistrer les paramètres.'));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Page title="Paramètres" description={data?.organization}>
      {loading ? <Loading /> : !data ? <Message error={error} /> : (
        <>
          <Message error={error} notice={notice} />
          <form key={version} onSubmit={submit} encType="multipart/form-data" className="space-y-5">
            <section className={cardClass}><h2 className="mb-4 text-lg font-bold">Compte — {data.user.username}</h2><DynamicFields fields={data.user.fields} /><div className="mt-4 grid gap-4 sm:grid-cols-2"><label className="text-sm font-semibold">Nouveau mot de passe<input name="new_password" type="password" autoComplete="new-password" minLength={8} className={`${inputClass} mt-1`} /></label><label className="text-sm font-semibold">Confirmer le mot de passe<input name="confirm_password" type="password" autoComplete="new-password" minLength={8} className={`${inputClass} mt-1`} /></label></div></section>
            <section className={cardClass}><h2 className="mb-4 text-lg font-bold">Notifications</h2><div className="space-y-3">{data.notifications.map((row) => <label key={row.field_name} className="flex items-center justify-between gap-4 rounded-xl border border-slate-100 p-3 dark:border-slate-800"><span><strong className="block text-sm">{row.label}</strong><span className="text-xs text-slate-500">{row.subtitle}</span></span><input name={row.field_name} type="checkbox" defaultChecked={row.enabled} /></label>)}</div></section>
            <section className={cardClass}>
              <h2 className="mb-4 text-lg font-bold">Préférences</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-semibold">
                  Période du tableau de bord
                  <select name="settings_dashboard_period" defaultValue={data.preferences.settings_dashboard_period} className={`${inputClass} mt-1`}>
                    <option value="7j">7 derniers jours</option>
                    <option value="30j">30 derniers jours</option>
                    <option value="total">Depuis le début</option>
                  </select>
                </label>
                <div className="text-sm font-semibold">
                  Langue de l’interface
                  <p className={`${inputClass} mt-1 font-normal`}>Français</p>
                </div>
                <label className="text-sm font-semibold">
                  Devise
                  <select name="settings_currency" defaultValue={data.preferences.settings_currency} className={`${inputClass} mt-1`}>
                    <option value="XOF">FCFA (XOF)</option>
                    <option value="EUR">Euro (EUR)</option>
                    <option value="USD">Dollar (USD)</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 text-sm font-semibold">
                  <input name="show_prices_on_public_profile" type="checkbox" defaultChecked={data.preferences.show_prices_on_public_profile} />
                  Afficher les prix sur mon profil public
                </label>
              </div>
            </section>
            <section className={cardClass}><h2 className="mb-4 text-lg font-bold">Équipe</h2><div className="space-y-2">{data.team.map((member) => <div key={`${member.email}-${member.index}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800"><span><strong>{member.name}</strong> · {member.email} <span className="text-slate-500">({member.role_label}, {member.status})</span></span><button type="submit" name="team_remove" value={member.index} className="text-red-700 underline dark:text-red-300">Retirer</button></div>)}</div><div className="mt-4 grid gap-3 sm:grid-cols-3"><input name="team_invite_name" placeholder="Nom du membre" className={inputClass} /><input name="team_invite_email" type="email" placeholder="Adresse e-mail" className={inputClass} /><select name="team_invite_role" defaultValue="secretaire" className={inputClass}><option value="secretaire">Secrétaire</option><option value="gestionnaire">Gestionnaire</option><option value="praticien">Praticien</option></select></div><button type="submit" name="team_invite" value="1" className="mt-3 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold dark:border-slate-700">Inviter un membre</button></section>
            <section className={cardClass}><h2 className="text-lg font-bold">Abonnement</h2><p className="mt-2 text-sm">{data.subscription.plan?.name || 'Aucune formule active'}{data.subscription.plan && ` · ${data.subscription.plan.monthly_price_fcfa} FCFA / mois`}</p>{data.subscription.plan?.short_description && <p className="mt-1 text-sm text-slate-500">{data.subscription.plan.short_description}</p>}{data.subscription.pending_request && <p className="mt-3 text-sm text-amber-700 dark:text-amber-300">Demande en cours : {data.subscription.pending_request.plan} ({data.subscription.pending_request.status})</p>}{data.subscription.recent_requests.length > 0 && <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700"><h3 className="mb-2 text-sm font-bold">Demandes récentes</h3><div className="space-y-2">{data.subscription.recent_requests.map((request, index) => <p key={`${request.created_at}-${index}`} className="flex justify-between gap-3 text-xs text-slate-600 dark:text-slate-300"><span>{request.plan} · {request.status}</span><span>{request.created_at.slice(0, 10)}</span></p>)}</div></div>}<Link to="/contact/" className="mt-4 inline-flex rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold dark:border-slate-700">Contacter MedCare au sujet de mon abonnement</Link></section>
            <button type="submit" className={buttonClass} disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer les paramètres'}</button>
          </form>
        </>
      )}
    </Page>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return <div className={cardClass}><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-black text-slate-900 dark:text-white">{value}</p></div>;
}

export function ProviderAnalyticsPage({ mode }: { mode: 'medplaque' | 'bilan' }) {
  const load = useCallback((signal: AbortSignal) => mode === 'medplaque' ? providerPortalApi.getMedPlaque(signal) : providerPortalApi.getBilan(signal), [mode]);
  const { data, loading, error } = useRemote(load);
  if (loading) return <Page title={mode === 'medplaque' ? 'MedPlaque' : 'Bilan KPI'}><Loading /></Page>;
  if (!data) return <Page title={mode === 'medplaque' ? 'MedPlaque' : 'Bilan KPI'}><Message error={error} /></Page>;
  return mode === 'medplaque' ? <MedPlaqueContent data={data} /> : <BilanContent data={data} />;
}

function MedPlaqueContent({ data }: { data: ProviderAnalyticsData }) {
  const stats = data.stats;
  if (!stats) return <Page title="MedPlaque"><Message error="Les statistiques MedPlaque sont indisponibles." /></Page>;
  return (
    <Page title="MedPlaque" description={`${data.organization} · Référence ${stats.reference}`}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Stat label="Accès totaux" value={stats.total_access} /><Stat label="Scans NFC" value={stats.nfc_scans} /><Stat label="Scans QR" value={stats.qr_scans} /><Stat label="Progression" value={stats.month_label} /></div>
      <div className={`${cardClass} mt-5`}><h2 className="mb-3 text-lg font-bold">Conversion</h2><div className="grid gap-3 sm:grid-cols-2"><p className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800">Scan vers visite <strong className="float-right">{stats.scan_to_visit_pct}%</strong></p><p className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800">Visite vers devis <strong className="float-right">{stats.visit_to_devis_pct}%</strong></p></div><p className="mt-3 text-sm">{stats.nfc_active ? 'NFC activé' : 'NFC non activé'}</p><div className="mt-4 flex flex-wrap gap-3"><a href={stats.profile_url_nfc} className="text-sm font-semibold text-sky-700 underline dark:text-sky-300" target="_blank" rel="noreferrer">Ouvrir le lien NFC</a><a href={stats.profile_url_qr} className="text-sm font-semibold text-sky-700 underline dark:text-sky-300" target="_blank" rel="noreferrer">Ouvrir le lien QR</a></div></div>
      <div className={`${cardClass} mt-5`}><h2 className="mb-3 text-lg font-bold">Visites récentes</h2>{data.recent_visits?.length ? <div className="space-y-2">{data.recent_visits.map((visit, index) => <div key={index} className="flex justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800"><span>{String(visit.label || visit.source || 'Visite')}</span><span className="text-right text-slate-500">{String(visit.meta || visit.viewed_at || '')}</span></div>)}</div> : <p className="text-sm text-slate-500">Aucune visite enregistrée.</p>}</div>
    </Page>
  );
}

function BilanContent({ data }: { data: ProviderAnalyticsData }) {
  const bilan = data.bilan;
  if (!bilan) return <Page title="Bilan KPI"><Message error="Le bilan KPI est indisponible." /></Page>;
  const sections = [
    ['Visibilité', bilan.section_a],
    ['Engagement', bilan.section_b],
    ['Valeur', bilan.section_c],
  ] as const;
  return (
    <Page title="Bilan de performance" description={data.organization}>
      <div className={`${cardClass} mb-5`}><div className="mb-2 flex justify-between"><strong>Complétion du profil</strong><strong>{data.completion_pct ?? 0}%</strong></div><div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${data.completion_pct ?? 0}%` }} /></div>{data.completion && <div className="mt-4 grid gap-2 sm:grid-cols-2">{data.completion.map((item) => <Link key={item.label} to={item.url || '#'} className="text-sm">{item.ok ? '✓' : '○'} {item.label}</Link>)}</div>}</div>
      <div className="grid gap-4 sm:grid-cols-3">{sections.map(([title, rows]) => <section key={title} className={cardClass}><h2 className="mb-3 text-lg font-bold">{title}</h2><div className="space-y-4">{rows.map((row) => <div key={row.label}><div className="flex justify-between gap-2 text-sm"><span>{row.label}</span><strong>{row.val}</strong></div><div className="mt-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-1.5 rounded-full bg-sky-600" style={{ width: `${Math.min(100, Math.max(0, row.pct))}%` }} /></div><p className="mt-1 text-xs text-slate-500">Objectif : {row.cible} · {row.signal}</p></div>)}</div></section>)}</div>
      <section className={`${cardClass} mt-5`}><h2 className="text-lg font-bold">Offre pionnier</h2><p className="mt-2 text-sm">{bilan.pioneer.label}</p>{bilan.pioneer.days_remaining !== null && <p className="mt-1 text-sm text-slate-500">{bilan.pioneer.days_remaining} jour(s) restant(s){bilan.pioneer.end_date ? ` · échéance ${bilan.pioneer.end_date}` : ''}</p>}<div className="mt-3 h-2 rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-2 rounded-full bg-amber-500" style={{ width: `${Math.min(100, Math.max(0, bilan.pioneer.progress_pct))}%` }} /></div><p className="mt-3 text-sm">Ratio de retour : {bilan.roi_ratio}</p>{bilan.pioneer.available_upgrade && <Link to="/sante/prestataire/parametres/" className="mt-3 inline-flex text-sm font-semibold text-sky-700 underline dark:text-sky-300">Découvrir les formules dans Paramètres</Link>}</section>
    </Page>
  );
}

export function ProviderRemindersPage() {
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getReminders(signal), []);
  const { data, loading, error, reload, setError } = useRemote(load);
  const [notice, setNotice] = useState('');
  const [deleting, setDeleting] = useState<number | null>(null);
  const remove = async (id: number) => {
    if (!window.confirm('Supprimer cette règle de rappel ?')) return;
    setDeleting(id);
    setError('');
    try {
      await providerPortalApi.deleteReminder(id);
      setNotice('Règle supprimée.');
      reload();
    } catch (reason) {
      setError(getError(reason, 'Impossible de supprimer cette règle.'));
    } finally {
      setDeleting(null);
    }
  };
  return (
    <Page title="Rappels de rendez-vous" description={data?.organization}>
      {loading ? <Loading /> : (
        <>
          <Message error={error} notice={notice} />
          <Link to="/sante/prestataire/actes/rappels/ajouter/" className={`${buttonClass} mb-4`}>Créer une règle</Link>
          <div className="space-y-3">{data?.reminders.map((reminder) => <ReminderCard key={reminder.id} reminder={reminder} deleting={deleting === reminder.id} onDelete={() => remove(reminder.id)} />)}{data?.reminders.length === 0 && <div className={cardClass}><p className="text-sm text-slate-500">Aucune règle de rappel configurée.</p></div>}</div>
        </>
      )}
    </Page>
  );
}

function ReminderCard({ reminder, deleting, onDelete }: { reminder: ProviderReminder; deleting: boolean; onDelete: () => void }) {
  return (
    <article className={`${cardClass} flex flex-wrap items-center justify-between gap-4`}>
      <div><h2 className="font-bold">{reminder.label}</h2><p className="mt-1 text-sm text-slate-500">Envoi {reminder.offset_value} {reminder.offset_unit} avant le rendez-vous · tolérance {reminder.tolerance_minutes} min</p><p className="mt-1 text-xs text-slate-500">{reminder.actes.length ? reminder.actes.join(', ') : 'Tous les actes'} · {reminder.sent_count} envoi(s) · {reminder.is_active ? 'Actif' : 'Inactif'}</p></div>
      <div className="flex gap-2"><Link to={`/sante/prestataire/actes/rappels/${reminder.id}/modifier/`} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700">Modifier</Link><button type="button" onClick={onDelete} disabled={deleting} className="rounded-xl border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 dark:border-red-900 dark:text-red-300">{deleting ? 'Suppression…' : 'Supprimer'}</button></div>
    </article>
  );
}

export function ProviderReminderFormPage() {
  const { id } = useParams();
  const url = id ? `/sante/prestataire/actes/rappels/${id}/modifier/` : '/sante/prestataire/actes/rappels/ajouter/';
  const load = useCallback((signal: AbortSignal) => providerPortalApi.getReminderForm(url, signal), [url]);
  const { data, loading, error, setError } = useRemote(load);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await providerPortalApi.saveReminderForm(url, new FormData(event.currentTarget));
      navigate('/sante/prestataire/actes/rappels/');
    } catch (reason) {
      setError(getError(reason, 'Impossible d’enregistrer cette règle.'));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Page title={data?.is_edit ? 'Modifier le rappel' : 'Nouvelle règle de rappel'}>
      {loading ? <Loading /> : (
        <>
          <Message error={error} />
          {data && <form onSubmit={submit} className={`${cardClass} space-y-5`}><DynamicFields fields={data.fields} /><div className="flex gap-3"><button type="submit" className={buttonClass} disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer'}</button><Link to="/sante/prestataire/actes/rappels/" className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold dark:border-slate-700">Annuler</Link></div></form>}
        </>
      )}
    </Page>
  );
}

export function ProviderSubscriptionPage() {
  return <Navigate to="/sante/prestataire/parametres/" replace />;
}
