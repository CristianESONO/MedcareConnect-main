import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Plus, Search } from 'lucide-react';
import { AdminWorkspaceHeader } from '../components/AdminWorkspaceHeader';
import { LoginPage } from './LoginPage';
import {
  adminApi,
  type AdminField,
  type AdminModelForm,
  type AdminModelList,
  type AdminModelSummary,
} from '../lib/api';

function modelPath(app: string, model: string) {
  return `/admin/${app}/${model}/`;
}

function renderAdminColumnValue(columnName: string, value: string | number | boolean | undefined) {
  const text = String(value ?? '');
  if (columnName === 'icon') {
    const markupClass = text.match(/^<i\s+class=["']([^"']+)["']\s*><\/i>$/i)?.[1];
    const iconClass = (markupClass ?? text).trim();
    if (/^ti(?:\s+ti-[a-z\d-]+)+$/i.test(iconClass)) {
      return <i className={`${iconClass} text-lg text-sky-800`} aria-hidden="true" />;
    }
  }
  return text;
}

function FieldInput({ field }: { field: AdminField }) {
  const className = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900';
  if (field.type === 'boolean') {
    return (
      <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" name={field.name} defaultChecked={Boolean(field.value)} className="h-4 w-4 rounded border-slate-300" />
        {field.label}
      </label>
    );
  }
  if (field.type === 'textarea' || field.type === 'json') {
    return <textarea name={field.name} defaultValue={String(field.value ?? '')} required={field.required} rows={field.type === 'json' ? 6 : 4} className={className} />;
  }
  if (field.type === 'select' || field.type === 'multiselect') {
    const values = field.type === 'multiselect'
      ? field.values
      : String(field.value ?? '') ? [String(field.value)] : [];
    return (
      <select name={field.name} multiple={field.type === 'multiselect'} defaultValue={field.type === 'multiselect' ? values : values[0] ?? ''} required={field.required} className={className}>
        {!field.required && field.type === 'select' && <option value="">---------</option>}
        {field.choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
      </select>
    );
  }
  const value = field.type === 'datetime' && typeof field.value === 'string'
    ? field.value.replace(/([+-]\d{2}:\d{2}|Z)$/, '').slice(0, 16)
    : String(field.value ?? '');
  return (
    <input
      type={field.type === 'date' ? 'date' : field.type === 'datetime' ? 'datetime-local' : field.type === 'file' ? 'file' : field.type === 'password' ? 'password' : 'text'}
      name={field.name}
      defaultValue={field.type === 'file' ? undefined : value}
      required={field.required}
      className={className}
    />
  );
}

function ModelEditor({
  schema,
  busy,
  error,
  onSave,
  onDelete,
}: {
  schema: AdminModelForm;
  busy: boolean;
  error: string;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onDelete?: () => void;
}) {
  return (
    <form onSubmit={onSave} className="max-w-4xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
      <h2 className="mb-5 text-lg font-bold text-slate-900">{schema.label}</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {schema.fields.map((field) => {
          const isWide = field.type === 'textarea' || field.type === 'json' || field.type === 'boolean' || field.type === 'multiselect';
          const className = `block text-sm font-semibold text-slate-700 ${isWide ? 'sm:col-span-2' : ''}`;
          return field.type === 'boolean' ? (
            <div key={field.name} className={className}>
              <FieldInput field={field} />
              {field.help_text && <span className="mt-1 block text-xs font-normal text-slate-500">{field.help_text}</span>}
            </div>
          ) : (
            <label key={field.name} className={className}>
              {field.label}{field.required && <span className="text-red-600"> *</span>}
              <FieldInput field={field} />
              {field.help_text && <span className="mt-1 block text-xs font-normal text-slate-500">{field.help_text}</span>}
            </label>
          );
        })}
      </div>
      {error && <p className="mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
      <div className="mt-6 flex flex-wrap justify-between gap-3">
        {onDelete ? (
          <button type="button" onClick={onDelete} disabled={busy} className="rounded-lg border border-red-200 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50">
            Supprimer
          </button>
        ) : <span />}
        <button type="submit" disabled={busy} className="rounded-lg bg-sky-800 px-5 py-2.5 text-sm font-bold text-white hover:bg-sky-900 disabled:opacity-50">
          {busy ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </div>
    </form>
  );
}

export function AdminPortalPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const parts = useMemo(
    () => location.pathname.replace(/^\/admin\/?/, '').split('/').filter(Boolean),
    [location.pathname],
  );
  const app = parts[0] ?? '';
  const model = parts[1] ?? '';
  const third = parts[2] ?? '';
  const isAdd = third === 'add';
  const objectPk = third && third !== 'add' ? third : '';
  const selectedMode = !app || !model ? 'home' : isAdd ? 'add' : objectPk ? 'edit' : 'list';

  const [username, setUsername] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [models, setModels] = useState<AdminModelSummary[]>([]);
  const [modelList, setModelList] = useState<AdminModelList | null>(null);
  const [formSchema, setFormSchema] = useState<AdminModelForm | null>(null);
  const [query, setQuery] = useState('');
  const [queryInput, setQueryInput] = useState('');
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    adminApi.session(controller.signal)
      .then((session) => {
        setUsername(session.username);
        setAuthenticated(true);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted && !(reason instanceof Error && reason.message === 'Authentification requise.')) {
          setError(reason instanceof Error ? reason.message : 'Impossible de vérifier la session.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSessionChecked(true);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!authenticated) return undefined;
    const controller = new AbortController();
    adminApi.models(controller.signal)
      .then((data) => setModels(data.models))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger les modèles.');
      });
    return () => controller.abort();
  }, [authenticated]);

  useEffect(() => {
    if (!authenticated || !app || !model) {
      setModelList(null);
      setFormSchema(null);
      return undefined;
    }
    const controller = new AbortController();
    setError('');
    setModelList(null);
    setFormSchema(null);
    const load = selectedMode === 'list'
      ? adminApi.modelList(app, model, query, page, controller.signal).then(setModelList)
      : selectedMode === 'add'
        ? adminApi.addForm(app, model, controller.signal).then(setFormSchema)
        : adminApi.modelDetail(app, model, objectPk, controller.signal).then(setFormSchema);
    load.catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger ce modèle.');
    });
    return () => controller.abort();
  }, [authenticated, app, model, objectPk, page, query, selectedMode]);

  const signIn = async (user: string, password: string) => {
    const data = new FormData();
    data.set('username', user);
    data.set('password', password);
    const result = await adminApi.login(data);
    setUsername(result.username);
    setAuthenticated(true);
    setError('');
  };

  const signOut = async () => {
    setError('');
    try {
      await adminApi.logout();
      setAuthenticated(false);
      setModels([]);
      setModelList(null);
      setFormSchema(null);
      navigate('/connexion/', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Déconnexion impossible.');
    }
  };

  const submitModel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formSchema) return;
    setBusy(true);
    setError('');
    try {
      const data = new FormData(event.currentTarget);
      if (isAdd) await adminApi.create(app, model, data);
      else await adminApi.update(app, model, objectPk, data);
      navigate(modelPath(app, model));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Enregistrement impossible.');
    } finally {
      setBusy(false);
    }
  };

  const deleteModel = async () => {
    if (!window.confirm('Confirmez-vous la suppression de cet élément ?')) return;
    setBusy(true);
    setError('');
    try {
      await adminApi.delete(app, model, objectPk);
      navigate(modelPath(app, model));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Suppression impossible.');
    } finally {
      setBusy(false);
    }
  };

  if (!sessionChecked) {
    return (
      <div className="min-h-screen bg-slate-100 text-slate-900">
        <AdminWorkspaceHeader />
        <main className="p-8 text-sm text-slate-600" role="status">Vérification de la session administrateur…</main>
      </div>
    );
  }
  if (!authenticated) {
    return <LoginPage adminLogin={signIn} />;
  }

  const currentModel = models.find((item) => item.app_label === app && item.model_name === model);
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <AdminWorkspaceHeader username={username} onLogout={() => void signOut()} />
      <div className="mx-auto grid max-w-screen-2xl gap-5 p-4 lg:grid-cols-[250px_minmax(0,1fr)] lg:p-6">
        <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <Link to="/admin/" className="block rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">Tous les modèles</Link>
          <div className="mt-3 space-y-1">
            {models.map((item) => (
              <Link
                key={`${item.app_label}.${item.model_name}`}
                to={modelPath(item.app_label, item.model_name)}
                className={`block rounded-lg px-3 py-2 text-sm ${app === item.app_label && model === item.model_name ? 'bg-sky-50 font-semibold text-sky-900' : 'text-slate-600 hover:bg-slate-50'}`}
              >
                {item.label}
                <span className="ml-1 text-[10px] text-slate-400">{item.app_label}</span>
              </Link>
            ))}
          </div>
        </aside>
        <main className="min-w-0">
          {error && <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
          {selectedMode === 'home' && (
            <section>
              <h1 className="font-syne text-2xl font-extrabold">Administration</h1>
              <p className="mt-1 text-sm text-slate-600">Sélectionnez un modèle pour consulter ou gérer ses données.</p>
              <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {models.map((item) => (
                  <Link key={`${item.app_label}.${item.model_name}`} to={modelPath(item.app_label, item.model_name)} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-sky-300">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{item.app_label}</p>
                    <h2 className="mt-1 font-bold text-slate-800">{item.label}</h2>
                  </Link>
                ))}
              </div>
            </section>
          )}
          {selectedMode === 'list' && currentModel && (
            <section>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{app}</p>
                  <h1 className="font-syne text-2xl font-extrabold">{modelList?.label ?? currentModel.label}</h1>
                </div>
                {currentModel.can_add && <Link to={`${modelPath(app, model)}add/`} className="inline-flex items-center gap-2 rounded-lg bg-sky-800 px-4 py-2.5 text-sm font-bold text-white hover:bg-sky-900"><Plus size={16} aria-hidden="true" /> Ajouter</Link>}
              </div>
              <form onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(queryInput); }} className="my-4 flex max-w-xl gap-2">
                <input value={queryInput} onChange={(event) => setQueryInput(event.target.value)} placeholder="Rechercher…" className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
                <button className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-sky-800 bg-sky-800 px-4 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 dark:border-sky-400 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300"><Search size={16} aria-hidden="true" /> Chercher</button>
              </form>
              {!modelList && <p className="rounded-xl bg-white p-4 text-sm text-slate-500" role="status">Chargement des données…</p>}
              {modelList && (
                <>
                  <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                    <table className="min-w-full text-left text-sm">
                      <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr>{modelList.columns.map((column) => <th key={column.name} className="whitespace-nowrap px-4 py-3">{column.label}</th>)}<th className="px-4 py-3">ID</th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {modelList.rows.map((row) => (
                          <tr key={row.pk} className="hover:bg-slate-50">
                            {modelList.columns.map((column) => <td key={column.name} className="max-w-72 truncate px-4 py-3">{renderAdminColumnValue(column.name, row.values[column.name])}</td>)}
                            <td className="whitespace-nowrap px-4 py-3 font-mono text-xs">
                              {modelList.can_change
                                ? <Link className="font-semibold text-sky-800 hover:underline" to={`${modelPath(app, model)}${encodeURIComponent(row.pk)}/change/`}>{row.pk}</Link>
                                : row.pk}
                            </td>
                          </tr>
                        ))}
                        {!modelList.rows.length && <tr><td colSpan={modelList.columns.length + 1} className="px-4 py-10 text-center text-slate-400">Aucun élément.</td></tr>}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-sm text-slate-600">
                    <span>{modelList.total} résultat(s) · page {modelList.page} / {Math.max(modelList.pages, 1)}</span>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={modelList.page <= 1} className="rounded-lg border border-slate-300 bg-white p-2 disabled:opacity-40"><ChevronLeft size={17} aria-hidden="true" /></button>
                      <button type="button" onClick={() => setPage((value) => Math.min(modelList.pages, value + 1))} disabled={modelList.page >= modelList.pages} className="rounded-lg border border-slate-300 bg-white p-2 disabled:opacity-40"><ChevronRight size={17} aria-hidden="true" /></button>
                    </div>
                  </div>
                </>
              )}
            </section>
          )}
          {(selectedMode === 'add' || selectedMode === 'edit') && (
            <div className="mb-4">
              <Link to={modelPath(app, model)} className="inline-flex items-center gap-1 text-sm font-semibold text-sky-800 hover:underline"><ChevronLeft size={16} aria-hidden="true" /> Retour à la liste</Link>
              {!formSchema && !error && <p className="mt-4 rounded-xl bg-white p-4 text-sm text-slate-500" role="status">Chargement du formulaire…</p>}
              {formSchema && (
                <div className="mt-4">
                  <ModelEditor
                    schema={formSchema}
                    busy={busy}
                    error={error}
                    onSave={(event) => void submitModel(event)}
                    onDelete={selectedMode === 'edit' && formSchema.can_delete ? () => void deleteModel() : undefined}
                  />
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
