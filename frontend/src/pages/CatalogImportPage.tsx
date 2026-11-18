import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  catalogAssistantApi,
  type CatalogAssistantData,
  type ReconciliationPayload,
} from '../lib/api';

type MatchChoice = { acteId: number; confirmed: boolean };
type Filter = 'all' | 'todo' | 'none';

export function CatalogImportPage() {
  const [data, setData] = useState<CatalogAssistantData | null>(null);
  const [stage, setStage] = useState<'nature' | 'pillars' | 'contact' | 'upload' | 'reconcile' | 'success'>('upload');
  const [nature, setNature] = useState('structure');
  const [type, setType] = useState('');
  const [pillarIds, setPillarIds] = useState<number[]>([]);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [city, setCity] = useState('Dakar');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ReconciliationPayload | null>(null);
  const [applyResult, setApplyResult] = useState<{
    created_count: number;
    updated_count: number;
    skipped_count: number;
    skipped_labels: string[];
  } | null>(null);
  const [choices, setChoices] = useState<Record<number, MatchChoice>>({});
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    catalogAssistantApi.initial(controller.signal)
      .then((payload) => {
        setData(payload);
        if (payload.organization) {
          setName(payload.organization.name);
          setPhone(payload.organization.phone);
          setEmail(payload.organization.email);
          setCity(payload.organization.city || 'Dakar');
          setNature(payload.organization.nature);
          setType(payload.organization.type);
          setPillarIds(payload.organization.pillar_ids);
        } else {
          setStage('nature');
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger l’assistant d’import.');
        }
      });
    return () => controller.abort();
  }, []);

  const referenceActs = useMemo(() => data?.reference_acts || [], [data]);
  const visibleRows = useMemo(() => (result?.rows || [])
    .map((row, index) => ({ row, index }))
    .filter(({ row, index }) => {
      const choice = choices[index];
      const resolved = choice?.confirmed || row.st === 'ok';
      if (filter === 'todo' && resolved) return false;
      if (filter === 'none' && (resolved || row.st !== 'none')) return false;
      const term = search.trim().toLocaleLowerCase('fr');
      return !term
        || row.raw.toLocaleLowerCase('fr').includes(term)
        || row.best_nom.toLocaleLowerCase('fr').includes(term);
    }), [choices, filter, result, search]);
  const reconciliationStats = useMemo(() => {
    const stats = { ok: 0, cf: 0, no: 0, total: result?.rows.length || 0 };
    result?.rows.forEach((row, index) => {
      const resolved = choices[index]?.confirmed || row.st === 'ok';
      if (resolved) stats.ok += 1;
      else if (row.st === 'confirm') stats.cf += 1;
      else stats.no += 1;
    });
    return stats;
  }, [choices, result]);

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] || null);
    setResult(null);
    setError('');
  };

  const loadReconciliation = async (payload: ReconciliationPayload) => {
    setResult(payload);
    setChoices(Object.fromEntries(payload.rows.map((row, index) => [
      index,
      { acteId: row.best, confirmed: row.st === 'ok' },
    ])));
    setStage('reconcile');
    setFilter('all');
    setSearch('');
  };

  const saveOrganization = async () => {
    setBusy(true);
    setError('');
    try {
      await catalogAssistantApi.submitOrganization({
        q1_nature: nature,
        q1_type_libre: type,
        q2_piliers: pillarIds,
        q4_nom: name,
        q4_telephone: phone,
        q4_email: email,
        q4_city: city,
      });
      setStage('upload');
      setNotice('Votre fiche établissement a été enregistrée.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer votre établissement.');
    } finally {
      setBusy(false);
    }
  };

  const startImport = async () => {
    if (!file) {
      setError('Sélectionnez un fichier Excel, CSV ou JSON.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await catalogAssistantApi.reconcile(file);
      await loadReconciliation(response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'La réconciliation du fichier a échoué.');
    } finally {
      setBusy(false);
    }
  };

  const loadPreset = async (preset: string) => {
    setBusy(true);
    setError('');
    try {
      await loadReconciliation(await catalogAssistantApi.loadPreset(preset));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de charger ce modèle.');
    } finally {
      setBusy(false);
    }
  };

  const applyMatches = async () => {
    if (!result) return;
    const items = result.rows.flatMap((row, index) => {
      const acteId = choices[index]?.acteId ?? row.best;
      return acteId > 0
        ? [{ acte_id: acteId, raw: row.raw, price: row.price, delai: row.delai }]
        : [];
    });
    if (!items.length) {
      setError('Aucune correspondance sélectionnée pour l’import.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await catalogAssistantApi.apply(items);
      setApplyResult(response);
      setNotice(response.message);
      setStage('success');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer les actes.');
    } finally {
      setBusy(false);
    }
  };

  const exportMatches = () => {
    if (!result) return;
    const contents = {
      fichier_origine: result.filename,
      date_export: new Date().toISOString(),
      total_lignes: result.rows.length,
      rows: result.rows.map((row, index) => ({
        ...row,
        valide: choices[index]?.confirmed ?? row.st === 'ok',
        acte_final_id: choices[index]?.acteId ?? row.best,
        acte_final_nom: referenceActs.find((act) => act.id === (choices[index]?.acteId ?? row.best))?.n || row.best_nom,
      })),
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(contents, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'rapprochement_medcare.json';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!data) {
    return (
      <section className="mx-auto max-w-5xl px-4 py-10">
        {error ? <p className="rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p> : <p role="status">Chargement de l’assistant…</p>}
      </section>
    );
  }

  const updateChoice = (index: number, patch: Partial<MatchChoice>) => {
    setChoices((current) => ({
      ...current,
      [index]: {
        ...(current[index] || {
          acteId: result?.rows[index]?.best ?? -1,
          confirmed: false,
        }),
        ...patch,
      },
    }));
  };

  const togglePillar = (id: number) => {
    setPillarIds((current) => current.includes(id)
      ? current.filter((value) => value !== id)
      : [...current, id]);
  };

  const step = (title: string, content: React.ReactNode, footer: React.ReactNode) => (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7">
      <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Assistant d’import · {title}</p>
      <div className="mt-5 space-y-5">{content}</div>
      <div className="mt-7 flex flex-wrap justify-between gap-3">{footer}</div>
    </section>
  );

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link to="/sante/prestataire/actes/" className="text-sm font-bold text-sky-800 hover:underline">← Retour au catalogue d’actes</Link>
        {data.organization && <span className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600">{data.organization.name}</span>}
      </div>
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Catalogue prestataire</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Assistant d’import MedCare</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">
          Configurez votre établissement, importez votre grille et vérifiez les correspondances avant d’ajouter les actes au catalogue.
        </p>
      </header>

      {notice && <p className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}

      {stage === 'nature' && step('Étape 1 sur 3', (
        <>
          <h2 className="text-lg font-bold text-gray-900">Quel type d’établissement êtes-vous ?</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ['structure', 'Structure de soins', 'Clinique, laboratoire, hôpital ou centre de soins.'],
              ['praticien', 'Praticien indépendant', 'Médecin, infirmier, kinésithérapeute ou autre praticien.'],
            ].map(([value, label, description]) => (
              <button key={value} type="button" aria-pressed={nature === value} onClick={() => setNature(value)} className={`rounded-xl border p-4 text-left ${nature === value ? 'border-sky-500 bg-sky-50' : 'border-gray-200 hover:bg-gray-50'}`}>
                <strong className="block text-sm text-gray-900">{label}</strong>
                <span className="mt-1 block text-xs text-gray-500">{description}</span>
              </button>
            ))}
          </div>
          <label className="block text-sm font-semibold text-gray-700" htmlFor="assistant-type">Type précis (facultatif)</label>
          <select id="assistant-type" value={type} onChange={(event) => setType(event.target.value)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm">
            <option value="">Sélectionner un type</option>
            {data.organization_types.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </>
      ), (
        <><span /><button type="button" onClick={() => setStage('pillars')} className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-bold text-white">Continuer</button></>
      ))}

      {stage === 'pillars' && step('Étape 2 sur 3', (
        <>
          <h2 className="text-lg font-bold text-gray-900">Quels domaines de soins proposez-vous ?</h2>
          <p className="text-sm text-gray-500">Sélectionnez au moins un pilier pour rattacher votre catalogue au référentiel.</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {data.pillars.map((pillar) => (
              <label key={pillar.id} className="flex items-center gap-3 rounded-xl border border-gray-200 p-3 text-sm font-medium hover:bg-sky-50">
                <input type="checkbox" checked={pillarIds.includes(pillar.id)} onChange={() => togglePillar(pillar.id)} />
                {pillar.name}
              </label>
            ))}
          </div>
        </>
      ), (
        <>
          <button type="button" onClick={() => setStage('nature')} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700">Retour</button>
          <button type="button" disabled={!pillarIds.length} onClick={() => setStage('contact')} className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">Continuer</button>
        </>
      ))}

      {stage === 'contact' && step('Étape 3 sur 3', (
        <>
          <h2 className="text-lg font-bold text-gray-900">Vos coordonnées professionnelles</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-gray-700">Nom / raison sociale *
              <input required value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
            </label>
            <label className="text-sm font-semibold text-gray-700">Téléphone *
              <input required type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
            </label>
            <label className="text-sm font-semibold text-gray-700">Email professionnel
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
            </label>
            <label className="text-sm font-semibold text-gray-700">Ville
              <input value={city} onChange={(event) => setCity(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
            </label>
          </div>
        </>
      ), (
        <>
          <button type="button" onClick={() => setStage('pillars')} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700">Retour</button>
          <button type="button" disabled={busy || !name.trim() || !phone.trim() || !pillarIds.length} onClick={() => { void saveOrganization(); }} className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">
            {busy ? 'Enregistrement…' : 'Enregistrer et continuer'}
          </button>
        </>
      ))}

      {stage === 'upload' && step('Importer le catalogue', (
        <>
          <div>
            <h2 className="text-lg font-bold text-gray-900">Importez votre fichier catalogue</h2>
            <p className="mt-1 text-sm text-gray-500">Formats acceptés : Excel (.xlsx, .xls), CSV ou JSON de réconciliation.</p>
          </div>
          <label className="flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-5 text-center hover:border-sky-400">
            <span className="font-semibold text-gray-800">{file ? file.name : 'Choisir un fichier ou le déposer ici'}</span>
            <span className="mt-1 text-xs text-gray-500">Les correspondances seront affichées avant validation.</span>
            <input type="file" accept=".xlsx,.xls,.csv,.json" onChange={chooseFile} className="sr-only" />
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={busy} onClick={() => { void loadPreset('imagerie'); }} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-bold text-gray-700 disabled:opacity-50">Charger le modèle imagerie</button>
            <button type="button" disabled={busy} onClick={() => { void loadPreset('biologie'); }} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-bold text-gray-700 disabled:opacity-50">Charger le modèle biologie</button>
          </div>
        </>
      ), (
        <>
          <Link to="/sante/prestataire/actes/" className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700">Annuler</Link>
          <button type="button" disabled={!file || busy} onClick={() => { void startImport(); }} className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">
            {busy ? 'Analyse en cours…' : 'Lancer la réconciliation'}
          </button>
        </>
      ))}

      {stage === 'reconcile' && result && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Réconciliation</p>
              <h2 className="mt-1 font-syne text-lg font-bold text-[#123a63]">{result.display_name || result.filename}</h2>
              <p className="mt-1 text-sm text-gray-500">Vérifiez les correspondances, puis validez l’import dans votre catalogue.</p>
            </div>
            <button type="button" onClick={exportMatches} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-bold text-gray-700">Exporter JSON</button>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ['Appariés', reconciliationStats.ok, 'text-emerald-700'],
              ['À confirmer', reconciliationStats.cf, 'text-amber-700'],
              ['Non appariés', reconciliationStats.no, 'text-red-700'],
              ['Total', reconciliationStats.total, 'text-gray-800'],
            ].map(([label, count, color]) => (
              <div key={String(label)} className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                <strong className={`block text-2xl ${color}`}>{count}</strong>
                <span className="text-xs text-gray-500">{label}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {(['all', 'todo', 'none'] as Filter[]).map((value) => (
              <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)} className={`rounded-full px-3 py-1.5 text-xs font-bold ${filter === value ? 'bg-[#123a63] text-white' : 'border border-gray-200 text-gray-600'}`}>
                {value === 'all' ? 'Tout' : value === 'todo' ? 'À traiter' : 'Non appariés'}
              </button>
            ))}
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un libellé…" className="min-w-52 flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </div>
          <div className="mt-4 overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead className="bg-gray-50 text-[10px] uppercase tracking-wide text-gray-500">
                <tr><th className="p-3">Libellé du fichier</th><th className="p-3">Statut</th><th className="p-3">Correspondance</th><th className="p-3">Score</th><th className="p-3">Validation</th></tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visibleRows.map(({ row, index }) => {
                  const choice = choices[index] || { acteId: row.best, confirmed: row.st === 'ok' };
                  const confirmed = choice.confirmed || row.st === 'ok';
                  return (
                    <tr key={`${row.nraw}-${index}`}>
                      <td className="p-3 font-semibold text-gray-900">{row.raw}<span className="mt-1 block text-[10px] font-normal text-gray-500">{row.price !== null ? `${row.price} FCFA` : ''}{row.delai ? ` · ${row.delai}` : ''}</span></td>
                      <td className="p-3">
                        <span className={`rounded-md px-2 py-1 font-bold ${confirmed ? 'bg-emerald-50 text-emerald-800' : row.st === 'confirm' ? 'bg-amber-50 text-amber-800' : 'bg-red-50 text-red-800'}`}>
                          {confirmed ? 'Apparié' : row.st === 'confirm' ? 'À confirmer' : 'Non apparié'}
                        </span>
                        <span className="mt-1 block text-[10px] text-gray-500">{row.via}</span>
                      </td>
                      <td className="p-3">
                        {row.st === 'ok'
                          ? <span className="font-semibold text-gray-800">{row.best_nom}</span>
                          : (
                            <select
                              value={choice.acteId > 0 ? choice.acteId : -1}
                              onChange={(event) => updateChoice(index, { acteId: Number(event.target.value), confirmed: false })}
                              className="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-2 py-1.5"
                            >
                              <option value={-1}>— Choisir un acte —</option>
                              {referenceActs.map((act) => <option key={act.id} value={act.id}>[{act.c}] {act.n}</option>)}
                            </select>
                          )}
                      </td>
                      <td className="p-3 tabular-nums text-gray-600">{row.st === 'ok' ? '100%' : row.sc ? `${row.sc}%` : '—'}</td>
                      <td className="p-3">
                        {row.st === 'ok' ? <span className="font-bold text-emerald-700">Validé</span> : (
                          <button type="button" aria-pressed={choice.confirmed} onClick={() => updateChoice(index, { confirmed: !choice.confirmed })} className={`rounded-md border px-2.5 py-1.5 font-bold ${choice.confirmed ? 'border-emerald-700 bg-emerald-700 text-white' : 'border-gray-300 text-gray-700'}`}>
                            {choice.confirmed ? 'Validé' : 'Valider'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {!visibleRows.length && <tr><td colSpan={5} className="p-8 text-center text-gray-500">Aucune ligne ne correspond au filtre.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="mt-5 flex flex-wrap justify-between gap-3">
            <button type="button" onClick={() => setStage('upload')} className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700">Changer de fichier</button>
            <button type="button" disabled={busy} onClick={() => { void applyMatches(); }} className="rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">
              {busy ? 'Enregistrement…' : 'Valider et enregistrer'}
            </button>
          </div>
        </section>
      )}

      {stage === 'success' && (
        <section className="rounded-2xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
          <p className="text-xs font-bold uppercase tracking-widest text-emerald-700">Import terminé</p>
          <h2 className="mt-2 font-syne text-2xl font-extrabold text-[#123a63]">Catalogue mis à jour</h2>
          <p className="mt-3 text-sm text-gray-600">{notice}</p>
          {applyResult && (
            <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">
              <span className="rounded-full bg-emerald-50 px-3 py-1.5 font-semibold text-emerald-800">{applyResult.created_count} nouvel acte(s)</span>
              <span className="rounded-full bg-sky-50 px-3 py-1.5 font-semibold text-sky-800">{applyResult.updated_count} mis à jour</span>
              <span className="rounded-full bg-amber-50 px-3 py-1.5 font-semibold text-amber-800">{applyResult.skipped_count} ignoré(s)</span>
            </div>
          )}
          {Boolean(applyResult?.skipped_labels.length) && (
            <details className="mx-auto mt-4 max-w-xl rounded-lg border border-amber-200 bg-amber-50 p-3 text-left text-xs text-amber-900">
              <summary className="cursor-pointer font-bold">{applyResult?.skipped_labels.length} libellé(s) non importé(s)</summary>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {applyResult?.skipped_labels.map((label, index) => <li key={`${label}-${index}`}>{label}</li>)}
              </ul>
            </details>
          )}
          <Link to="/sante/prestataire/actes/" className="mt-5 inline-flex rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-bold text-white">Accéder au catalogue</Link>
        </section>
      )}
    </section>
  );
}
