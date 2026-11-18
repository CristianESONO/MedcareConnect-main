import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Check, FileDown, FileUp, Search, Settings2, Trash2 } from 'lucide-react';
import {
  providerCatalogApi,
  type ProviderCatalog,
  type ProviderCatalogAct,
} from '../lib/api';

type TarifMode = 'comptant' | 'ipm' | 'assurance';

export function ProviderCatalogPage() {
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [activePillar, setActivePillar] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [tarifMode, setTarifMode] = useState<TarifMode>('comptant');
  const [saving, setSaving] = useState(false);
  const [preparation, setPreparation] = useState<ProviderCatalogAct['preparation'] | null>(null);
  const [prepText, setPrepText] = useState('');
  const [prepActive, setPrepActive] = useState(true);
  const [reminderHours, setReminderHours] = useState('');
  const [domicileEnabled, setDomicileEnabled] = useState(false);
  const [domicileDelay, setDomicileDelay] = useState('');
  const [domicileHours, setDomicileHours] = useState('');
  const [zones, setZones] = useState<{ pk?: number; label: string; forfait_fcfa: number }[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [autoActivate, setAutoActivate] = useState(true);

  useEffect(() => {
    const stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = '/static/healthcare/css/prestataire_catalogue.css?v=8';
    stylesheet.dataset.providerCatalog = 'true';
    document.head.appendChild(stylesheet);
    return () => stylesheet.remove();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    providerCatalogApi.get(controller.signal)
      .then((response) => {
        setCatalog(response);
        setActivePillar((current) => current ?? response.selected_pilier);
        setDomicileEnabled(response.domicile.enabled);
        setDomicileDelay(response.domicile.delay);
        setDomicileHours(response.domicile.hours);
        setZones(response.domicile.zones);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger le catalogue.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const selectedPillar = catalog?.pillars.find((pillar) => pillar.id === activePillar);
  const visibleRows = useMemo(() => {
    if (!selectedPillar) return [];
    const normalizedSearch = search.trim().toLocaleLowerCase('fr');
    return selectedPillar.subgroups.flatMap((subgroup) =>
      subgroup.actes
        .filter(() => !category || category === subgroup.label)
        .filter((act) => !normalizedSearch || `${act.name} ${act.parent_name} ${act.category}`.toLocaleLowerCase('fr').includes(normalizedSearch))
        .map((act) => ({ act, subgroup: subgroup.label })),
    );
  }, [selectedPillar, search, category]);

  const updateAct = (actId: number, update: Partial<ProviderCatalogAct>) => {
    setCatalog((current) => current ? {
      ...current,
      pillars: current.pillars.map((pillar) => ({
        ...pillar,
        subgroups: pillar.subgroups.map((subgroup) => ({
          ...subgroup,
          actes: subgroup.actes.map((act) => act.id === actId ? { ...act, ...update } : act),
        })),
      })),
    } : current);
  };

  const saveCatalog = async () => {
    if (!catalog) return;
    setSaving(true);
    setError('');
    setNotice('');
    const data = new FormData();
    data.set('action', 'save_catalogue');
    data.set('catalogue_tarifs_delais', catalog.catalogue_tarifs_delais);
    catalog.pillars.flatMap((pillar) => pillar.subgroups.flatMap((group) => group.actes)).forEach((act) => {
      data.set(`price_${act.id}`, act.price);
      data.set(`delai_${act.id}`, act.delai);
      if (act.is_available) data.append('acte_ids', String(act.id));
    });
    try {
      await providerCatalogApi.save(data);
      setNotice('Catalogue enregistré.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer le catalogue.');
    } finally {
      setSaving(false);
    }
  };

  const saveDomicile = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!catalog) return;
    setSaving(true);
    setError('');
    try {
      const data = new FormData();
      data.set('action', 'save_domicile');
      data.set('domicile_op', 'save');
      data.set('prises_sang_domicile', domicileEnabled ? '1' : '0');
      data.set('domicile_delai_intervention', domicileDelay);
      data.set('domicile_plages_horaires', domicileHours);
      data.set('zones_json', JSON.stringify(zones));
      const result = await providerCatalogApi.saveDomicile(data);
      setZones(result.zones);
      setNotice(result.message);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer les prestations à domicile.');
    } finally {
      setSaving(false);
    }
  };

  const savePreparation = async () => {
    if (!catalog || !preparation) return;
    setSaving(true);
    setError('');
    try {
      const result = await providerCatalogApi.savePrerequisites(
        preparation.acte_id,
        prepText,
        prepActive,
        catalog.urls.prerequisite_tpl,
      );
      setCatalog((current) => current ? {
        ...current,
        preparation: {
          ...current.preparation,
          [preparation.acte_id]: {
            ...current.preparation[preparation.acte_id],
            custom: result.message,
            message: result.message,
            configured: result.configured,
            active: result.active,
          },
        },
        pillars: current.pillars.map((pillar) => ({
          ...pillar,
          subgroups: pillar.subgroups.map((group) => ({
            ...group,
            actes: group.actes.map((act) => act.id === preparation.acte_id
              ? { ...act, preparation: { ...act.preparation, custom: result.message, message: result.message, configured: result.configured, active: result.active } }
              : act),
          })),
        })),
      } : current);
      setPreparation((current) => current ? {
        ...current, custom: result.message, message: result.message, configured: result.configured, active: result.active,
      } : current);
      setNotice('Consignes de préparation enregistrées.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer les consignes.');
    } finally {
      setSaving(false);
    }
  };

  const addReminder = async () => {
    if (!catalog || !preparation) return;
    const hours = Number(reminderHours);
    if (!Number.isInteger(hours) || hours < 1 || hours > 168) {
      setError('Saisissez un délai compris entre 1 et 168 heures.');
      return;
    }
    try {
      const result = await providerCatalogApi.addReminder(
        preparation.acte_id,
        hours,
        catalog.urls.reminder_add_tpl,
      );
      setPreparation((current) => current ? { ...current, reminders: result.reminders } : current);
      setCatalog((current) => current ? {
        ...current,
        preparation: {
          ...current.preparation,
          [preparation.acte_id]: {
            ...current.preparation[preparation.acte_id],
            reminders: result.reminders,
          },
        },
      } : current);
      setReminderHours('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ajouter ce rappel.');
    }
  };

  const removeReminder = async (reminderId: number) => {
    if (!catalog || !preparation) return;
    try {
      const result = await providerCatalogApi.deleteReminder(
        preparation.acte_id,
        reminderId,
        catalog.urls.reminder_delete_tpl,
      );
      setPreparation((current) => current ? { ...current, reminders: result.reminders } : current);
      setCatalog((current) => current ? {
        ...current,
        preparation: {
          ...current.preparation,
          [preparation.acte_id]: {
            ...current.preparation[preparation.acte_id],
            reminders: result.reminders,
          },
        },
      } : current);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de supprimer ce rappel.');
    }
  };

  const importCatalog = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!catalog || !file) {
      setError('Sélectionnez un fichier Excel ou CSV.');
      return;
    }
    setImporting(true);
    setError('');
    setNotice('');
    const data = new FormData(event.currentTarget);
    data.set('auto_activate', autoActivate ? '1' : '0');
    try {
      const result = await providerCatalogApi.import(data);
      setNotice(result.message + (result.errors.length ? ` ${result.errors.slice(0, 3).join(' · ')}` : ''));
      const refreshed = await providerCatalogApi.get();
      setCatalog(refreshed);
      setFile(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Échec de l’import du catalogue.');
    } finally {
      setImporting(false);
    }
  };

  if (loading) return <section className="mx-auto max-w-7xl px-4 py-8 text-sm text-gray-600" role="status">Chargement du catalogue…</section>;
  if (!catalog) return <section className="mx-auto max-w-7xl px-4 py-8"><p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error || 'Catalogue indisponible.'}</p></section>;

  return (
    <section className="mx-auto w-full max-w-7xl px-4 py-7">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace prestataire · {catalog.organization}</p>
          <h1 className="mt-1 text-2xl font-extrabold text-[#123a63] sm:text-3xl">Catalogue des actes</h1>
          <p className="mt-1 text-sm text-gray-500">Gérez votre offre, vos tarifs, délais et consignes de préparation.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a href={catalog.urls.template} className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3.5 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"><FileDown size={16} aria-hidden="true" /> Modèle Excel</a>
          <button type="button" onClick={() => document.getElementById('catalog-import')?.scrollIntoView({ behavior: 'smooth' })} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700"><FileUp size={16} aria-hidden="true" /> Importer un fichier</button>
          <button type="button" disabled={saving} onClick={() => void saveCatalog()} className="rounded-xl bg-[#0a5c8a] px-4 py-2 text-sm font-bold text-white disabled:opacity-50"><Check size={15} className="mr-1 inline" aria-hidden="true" /> Enregistrer</button>
        </div>
      </header>

      {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
      {notice && <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}

      <section className="mt-5 rounded-2xl border border-gray-200 bg-white p-3 shadow-sm">
        <p className="px-2 pb-2 text-[11px] font-bold uppercase tracking-wide text-gray-400">Piliers d’activité</p>
        <div className="flex gap-2 overflow-x-auto">
          {catalog.pillars.map((pillar) => (
            <button type="button" key={pillar.id} disabled={!pillar.applicable} onClick={() => { setActivePillar(pillar.id); setCategory(''); setSearch(''); }} aria-pressed={activePillar === pillar.id} className={`shrink-0 rounded-xl px-3.5 py-2.5 text-left text-xs font-bold ${activePillar === pillar.id ? 'bg-[#0a5c8a] text-white' : pillar.applicable ? 'bg-gray-50 text-gray-700 hover:bg-sky-50' : 'cursor-not-allowed bg-gray-50 text-gray-300'}`}>
              <span className="block">{pillar.name}</span>
              <span className="mt-0.5 block text-[10px] font-medium opacity-75">{pillar.active_count} / {pillar.acte_count} actifs</span>
            </button>
          ))}
        </div>
      </section>

      {catalog.show_domicile_block && ['biologie-medicale', 'explorations-fonctionnelles', 'soins-specialises'].includes(selectedPillar?.slug || '') && (
        <section className="mt-4 rounded-2xl border border-sky-100 bg-sky-50/50 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-gray-900">Prestations à domicile</h2>
              <p className="mt-0.5 text-xs text-gray-500">Configurez les horaires et les zones desservies.</p>
            </div>
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
              <input type="checkbox" checked={domicileEnabled} onChange={(event) => setDomicileEnabled(event.target.checked)} />
              Activées
            </label>
          </div>
          {domicileEnabled && <form onSubmit={saveDomicile} className="mt-4 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs font-semibold text-gray-700">Délai d’intervention
                <select value={domicileDelay} onChange={(event) => setDomicileDelay(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm">
                  <option value="">— Choisir —</option>
                  {catalog.domicile.delay_choices.map((choice) => <option value={choice.value} key={choice.value}>{choice.label}</option>)}
                </select>
              </label>
              <label className="text-xs font-semibold text-gray-700">Plages horaires
                <input value={domicileHours} maxLength={120} onChange={(event) => setDomicileHours(event.target.value)} placeholder="Ex. 7h–10h Lun–Sam" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </label>
            </div>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold text-gray-700">Zones de déplacement et forfaits (FCFA)</p>
                <button type="button" onClick={() => setZones((current) => [...current, { label: '', forfait_fcfa: 0 }])} className="rounded-lg border border-sky-200 bg-white px-3 py-1.5 text-xs font-bold text-sky-800">+ Ajouter une zone</button>
              </div>
              {zones.map((zone, index) => <div key={zone.pk ?? `new-${index}`} className="flex flex-wrap gap-2">
                <input value={zone.label} onChange={(event) => setZones((current) => current.map((item, i) => i === index ? { ...item, label: event.target.value } : item))} placeholder="Quartier ou zone" className="min-w-[180px] flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                <input type="number" min="0" step="500" value={zone.forfait_fcfa} onChange={(event) => setZones((current) => current.map((item, i) => i === index ? { ...item, forfait_fcfa: Number(event.target.value) } : item))} aria-label={`Forfait de la zone ${zone.label || index + 1}`} className="w-36 rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                <button type="button" onClick={() => setZones((current) => current.filter((_, i) => i !== index))} aria-label={`Supprimer ${zone.label || 'cette zone'}`} className="rounded-lg border border-rose-200 bg-white px-3 text-rose-700"><Trash2 size={15} aria-hidden="true" /></button>
              </div>)}
            </div>
            <button type="submit" disabled={saving} className="rounded-lg bg-sky-700 px-4 py-2 text-xs font-bold text-white disabled:opacity-50">Enregistrer les prestations à domicile</button>
          </form>}
          {!domicileEnabled && <button type="button" onClick={() => void saveDomicile()} className="mt-3 rounded-lg bg-sky-700 px-4 py-2 text-xs font-bold text-white">Enregistrer la désactivation</button>}
        </section>
      )}

      {selectedPillar && <section className="mt-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="mr-auto text-base font-bold text-gray-900">{selectedPillar.name}</h2>
          <label className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" aria-hidden="true" />
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un acte…" aria-label="Rechercher un acte" className="rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-xs" />
          </label>
          <select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filtrer par catégorie" className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs">
            <option value="">Toutes catégories</option>
            {selectedPillar.subgroups.map((group) => <option key={group.label} value={group.label}>{group.label}</option>)}
          </select>
          <select value={tarifMode} onChange={(event) => setTarifMode(event.target.value as TarifMode)} aria-label="Régime tarifaire" className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs">
            <option value="comptant">Comptant</option><option value="ipm">IPM</option><option value="assurance">Assurance</option>
          </select>
          <Link to="/sante/prestataire/actes/ajouter/" className="rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white">+ Ajouter un acte</Link>
          <a href={catalog.urls.reminders} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600">Rappels RDV</a>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[790px] border-collapse text-left text-xs">
            <thead><tr className="border-b border-gray-200 text-[10px] font-bold uppercase tracking-wide text-gray-400"><th className="px-2 py-3">Acte</th><th className="px-2 py-3">Catégorie</th><th className="px-2 py-3">Tarif</th><th className="px-2 py-3">Délai résultat</th><th className="px-2 py-3 text-center">Préparation</th><th className="px-2 py-3 text-center">Actif</th><th className="px-2 py-3">Gérer</th></tr></thead>
            <tbody>
              {visibleRows.map(({ act, subgroup }) => <tr key={act.id} className="border-b border-gray-100 hover:bg-gray-50/70">
                <td className="px-2 py-3"><strong className="block text-gray-800">{act.name}</strong>{act.parent_name && <span className="text-[10px] text-gray-400">{act.parent_name}</span>}</td>
                <td className="px-2 py-3 text-gray-600">{subgroup}</td>
                <td className="px-2 py-3">
                  {tarifMode === 'comptant' ? <div className="flex items-center gap-1"><input type="number" min="0" step="500" value={act.price} onChange={(event) => updateAct(act.id, { price: event.target.value })} aria-label={`Tarif comptant de ${act.name}`} className="w-28 rounded-md border border-gray-200 px-2 py-1.5 text-right" /><span className="text-gray-400">F</span></div>
                    : <span className={`rounded-md px-2 py-1 text-[10px] font-bold ${((tarifMode === 'ipm' ? act.coverage_status_ipm : act.coverage_status_assurance) === 'covered') ? 'bg-emerald-50 text-emerald-700' : ((tarifMode === 'ipm' ? act.coverage_status_ipm : act.coverage_status_assurance) === 'excluded') ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'}`}>
                      {(tarifMode === 'ipm' ? act.price_ipm : act.price_assurance) ? `${Number(tarifMode === 'ipm' ? act.price_ipm : act.price_assurance).toLocaleString('fr-FR')} F` : ((tarifMode === 'ipm' ? act.coverage_status_ipm : act.coverage_status_assurance) === 'excluded' ? 'Non couvert' : 'À confirmer')}
                    </span>}
                </td>
                <td className="px-2 py-3"><select value={act.delai} onChange={(event) => updateAct(act.id, { delai: event.target.value })} aria-label={`Délai pour ${act.name}`} className="max-w-[155px] rounded-md border border-gray-200 bg-white px-2 py-1.5">
                  {catalog.delai_choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
                </select></td>
                <td className="px-2 py-3 text-center"><button type="button" onClick={() => { setPreparation(act.preparation); setPrepText(act.preparation.custom); setPrepActive(act.preparation.active); setError(''); }} className={`rounded-lg px-2.5 py-1.5 text-[10px] font-bold ${act.preparation.configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}><Settings2 size={12} className="mr-1 inline" aria-hidden="true" />{act.preparation.configured ? 'Configurée' : 'À configurer'}</button>
                  <span className="mt-1 block text-[9px] text-gray-400">{act.preparation.active ? 'Diffusée au patient' : 'Non diffusée'}</span>
                </td>
                <td className="px-2 py-3 text-center"><input type="checkbox" checked={act.is_available} onChange={(event) => updateAct(act.id, { is_available: event.target.checked })} aria-label={`${act.is_available ? 'Désactiver' : 'Activer'} ${act.name}`} /></td>
                <td className="px-2 py-3"><div className="flex gap-2">
                  <Link to={`/sante/prestataire/actes/${act.id}/modifier/`} className="font-semibold text-sky-700 hover:underline">Modifier</Link>
                  <button type="button" onClick={async () => {
                    if (!window.confirm(`Supprimer « ${act.name} » de votre catalogue ?`)) return;
                    try {
                      await providerCatalogApi.deleteAct(act.id);
                      setNotice(`« ${act.name} » a été supprimé.`);
                      const next = await providerCatalogApi.get();
                      setCatalog(next);
                    } catch (reason) {
                      setError(reason instanceof Error ? reason.message : 'Impossible de supprimer cet acte.');
                    }
                  }} className="font-semibold text-rose-600 hover:underline">Supprimer</button>
                </div></td>
              </tr>)}
              {!visibleRows.length && <tr><td colSpan={7} className="px-3 py-10 text-center text-sm text-gray-400">Aucun acte ne correspond à ces filtres.</td></tr>}
            </tbody>
          </table>
        </div>
        <label className="mt-5 block text-sm font-semibold text-gray-900">Tarifs &amp; délais (texte libre)
          <span className="mt-0.5 block text-xs font-normal text-gray-500">Informations complémentaires affichées sur votre fiche patient.</span>
          <textarea rows={3} value={catalog.catalogue_tarifs_delais} onChange={(event) => setCatalog({ ...catalog, catalogue_tarifs_delais: event.target.value })} className="mt-2 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm" />
        </label>
        <div className="mt-4 flex justify-end"><button type="button" disabled={saving} onClick={() => void saveCatalog()} className="rounded-xl bg-[#0a5c8a] px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">{saving ? 'Enregistrement…' : 'Enregistrer le catalogue'}</button></div>
      </section>}

      <section id="catalog-import" className="mt-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="font-bold text-gray-900">Importer un catalogue</h2>
        <p className="mt-1 text-xs text-gray-500">Formats pris en charge : Excel (.xlsx, .xls) ou CSV. <a className="font-semibold text-sky-700 underline" href={catalog.urls.template}>Télécharger le modèle prérempli</a>.</p>
        <form onSubmit={importCatalog} className="mt-3 flex flex-wrap items-center gap-3">
          <input type="file" name="file" required accept=".xlsx,.xls,.csv" onChange={(event) => setFile(event.target.files?.[0] || null)} className="max-w-full text-xs text-gray-600" />
          <label className="flex items-center gap-2 text-xs text-gray-600"><input type="checkbox" checked={autoActivate} onChange={(event) => setAutoActivate(event.target.checked)} /> Activer les actes importés</label>
          <button type="submit" disabled={!file || importing} className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-50">{importing ? 'Import en cours…' : 'Importer'}</button>
        </form>
      </section>

      {preparation && <div className="prep-overlay open" onMouseDown={(event) => { if (event.target === event.currentTarget) setPreparation(null); }}>
        <aside className="prep-panel open" role="dialog" aria-modal="true" aria-labelledby="prep-title">
          <div className="prep-panel-head"><div><h2 id="prep-title" className="pph-acte">{preparation.name}</h2><p className="pph-cat">{preparation.pilier} · {preparation.category}</p></div><button type="button" className="prep-panel-close" onClick={() => setPreparation(null)} aria-label="Fermer">×</button></div>
          <div className="prep-panel-body space-y-4">
            {preparation.reference_lines.length > 0 && <div className="rounded-xl bg-sky-50 p-3 text-xs text-sky-900"><strong>Consignes de référence</strong><ul className="mt-2 list-disc space-y-1 pl-4">{preparation.reference_lines.map((line, index) => <li key={`${line}-${index}`}>{line}</li>)}</ul></div>}
            <label className="block text-xs font-semibold text-gray-700">Consignes personnalisées
              <textarea rows={5} value={prepText} onChange={(event) => setPrepText(event.target.value)} placeholder="Précisez la préparation nécessaire avant le rendez-vous…" className="prep-text mt-2 w-full" />
            </label>
            <label className="flex items-center gap-2 text-xs font-semibold text-gray-700"><input type="checkbox" checked={prepActive} onChange={(event) => setPrepActive(event.target.checked)} /> Diffuser ces consignes aux patients dans les rappels</label>
            <div className="border-t border-gray-100 pt-4">
              <h3 className="text-xs font-bold text-gray-800">Rappels automatiques</h3>
              <div className="mt-2 space-y-2">{preparation.reminders.map((reminder) => <div key={reminder.pk} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-xs"><span>{reminder.display}</span><button type="button" onClick={() => void removeReminder(reminder.pk)} className="font-semibold text-rose-600">Supprimer</button></div>)}</div>
              <div className="mt-3 flex gap-2"><input type="number" min="1" max="168" value={reminderHours} onChange={(event) => setReminderHours(event.target.value)} placeholder="Heures avant le RDV" className="min-w-0 flex-1 rounded-lg border border-gray-200 px-3 py-2 text-xs" /><button type="button" onClick={() => void addReminder()} className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-bold text-sky-800">Ajouter H-</button></div>
            </div>
          </div>
          <div className="prep-panel-foot"><button type="button" onClick={() => setPreparation(null)} className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-600">Fermer</button><button type="button" disabled={saving} onClick={() => void savePreparation()} className="rounded-xl bg-[#0a5c8a] px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Enregistrer</button></div>
        </aside>
      </div>}
    </section>
  );
}
