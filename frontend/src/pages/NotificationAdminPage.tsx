import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  notificationAdminApi,
  type NotificationAdminLog,
  type NotificationAdminRule,
  type NotificationAdminSettings,
  type NotificationAdminTemplate,
} from '../lib/api';
import { AdminWorkspaceHeader } from '../components/AdminWorkspaceHeader';

type AdminTab = 'settings' | 'rules' | 'templates' | 'patient-whatsapp' | 'logs';

const TABS: { id: AdminTab; label: string }[] = [
  { id: 'settings', label: 'Configuration' },
  { id: 'rules', label: 'Règles' },
  { id: 'templates', label: 'Templates' },
  { id: 'patient-whatsapp', label: 'WhatsApp patient (wa.me)' },
  { id: 'logs', label: 'Journal' },
];

const TAB_PATHS: Record<AdminTab, string> = {
  settings: '/notifications/admin/parametres/',
  rules: '/notifications/admin/regles/',
  templates: '/notifications/admin/modeles/',
  'patient-whatsapp': '/notifications/admin/messages-whatsapp-patient/',
  logs: '/notifications/admin/journaux/',
};

function tabFromPath(path: string): AdminTab {
  if (path.includes('/regles/')) return 'rules';
  if (path.includes('/modeles/')) return 'templates';
  if (path.includes('/messages-whatsapp-patient/')) return 'patient-whatsapp';
  if (path.includes('/journaux/')) return 'logs';
  return 'settings';
}

const inputClass = 'mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900';
const buttonClass = 'inline-flex min-h-10 items-center justify-center rounded-lg border border-sky-800 bg-sky-800 px-4 py-2 text-sm font-bold text-white shadow-sm transition-colors hover:bg-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:opacity-60 dark:border-sky-400 dark:bg-sky-400 dark:text-slate-950 dark:hover:bg-sky-300';

function formValues(form: HTMLFormElement) {
  return Object.fromEntries(new FormData(form).entries());
}

function Notice({ error, notice }: { error: string; notice: string }) {
  return (
    <>
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}{(error.includes('Authentification') || error.includes('Accès réservé')) && <a href={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">Se connecter</a>}</p>}
      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
    </>
  );
}

export function NotificationAdminPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [tab, setTab] = useState<AdminTab>(() => tabFromPath(location.pathname));
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [settings, setSettings] = useState<NotificationAdminSettings | null>(null);
  const [channels, setChannels] = useState<{ id: number; code: string; label: string; description?: string; is_enabled?: boolean }[]>([]);
  const [rulesData, setRulesData] = useState<Awaited<ReturnType<typeof notificationAdminApi.getRules>> | null>(null);
  const [selectedRule, setSelectedRule] = useState<(NotificationAdminRule & { users: { id: number; label: string }[] }) | null>(null);
  const [templatesData, setTemplatesData] = useState<Awaited<ReturnType<typeof notificationAdminApi.getTemplates>> | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<NotificationAdminTemplate | null>(null);
  const [patientMessages, setPatientMessages] = useState<Record<string, string>>({});
  const [logs, setLogs] = useState<NotificationAdminLog[]>([]);
  const [logChannels, setLogChannels] = useState<{ code: string; label: string }[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [pagination, setPagination] = useState<{ number: number; pages: number; total: number; has_previous: boolean; previous: number | null; has_next: boolean; next: number | null } | null>(null);
  const [logFilters, setLogFilters] = useState({ q: '', status: '', channel: '' });
  const [logPage, setLogPage] = useState(1);

  useEffect(() => {
    setTab(tabFromPath(location.pathname));
  }, [location.pathname]);

  const loadLogs = useCallback(async (page = logPage, filters = logFilters) => {
    const params = new URLSearchParams({ page: String(page) });
    if (filters.q) params.set('q', filters.q);
    if (filters.status) params.set('status', filters.status);
    if (filters.channel) params.set('channel', filters.channel);
    const result = await notificationAdminApi.getLogs(params);
    setLogs(result.logs);
    setLogChannels(result.channels);
    setCounts(result.counts_by_status);
    setPagination(result.pagination);
  }, [logFilters, logPage]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    const load = async () => {
      try {
        if (tab === 'settings') {
          const result = await notificationAdminApi.getSettings(controller.signal);
          setSettings(result.settings);
          setChannels(result.channels);
        } else if (tab === 'rules') {
          setRulesData(await notificationAdminApi.getRules(controller.signal));
        } else if (tab === 'templates') {
          setTemplatesData(await notificationAdminApi.getTemplates(controller.signal));
        } else if (tab === 'patient-whatsapp') {
          const result = await notificationAdminApi.getPatientWaMessages(controller.signal);
          setPatientMessages(result.messages);
        } else {
          await loadLogs(logPage, logFilters);
        }
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger les données.');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    void load();
    return () => controller.abort();
  }, [tab, logPage, logFilters, loadLogs]);

  const runSave = async (save: () => Promise<unknown>, message: string) => {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      await save();
      setNotice(message);
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Enregistrement impossible.');
      return false;
    } finally {
      setSaving(false);
    }
  };

  const saveSettings = (action: string) => async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    await runSave(
      async () => {
        const result = await notificationAdminApi.saveSettings(action, formValues(form));
        if (result.settings) setSettings(result.settings);
      },
      action.startsWith('test_') ? 'Test envoyé.' : 'Configuration enregistrée.',
    );
  };

  const openRule = async (eventId: number, channelId: number) => {
    setError('');
    try {
      const result = await notificationAdminApi.getRule(eventId, channelId);
      setSelectedRule(result.rule);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de charger la règle.');
    }
  };

  const saveRule = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedRule) return;
    const form = event.currentTarget;
    const values: Record<string, unknown> = formValues(form);
    values.target_roles = Array.from(form.querySelectorAll<HTMLInputElement>('input[name="target_roles"]:checked'), (item) => item.value);
    values.target_users = Array.from(form.querySelector<HTMLSelectElement>('select[name="target_users"]')?.selectedOptions ?? [], (item) => Number(item.value));
    const ok = await runSave(
      async () => {
        await notificationAdminApi.saveRule(selectedRule.event_id, selectedRule.channel_id, values);
        setSelectedRule(null);
        setRulesData(await notificationAdminApi.getRules());
      },
      'Règle enregistrée.',
    );
    if (ok) setSelectedRule(null);
  };

  const saveTemplate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!templatesData) return;
    const values = formValues(event.currentTarget);
    const isEnabled = values.is_enabled === 'on';
    const body = { ...values, is_enabled: isEnabled };
    const id = editingTemplate?.id ?? null;
    const ok = await runSave(async () => {
      await notificationAdminApi.saveTemplate(id, body);
      setTemplatesData(await notificationAdminApi.getTemplates());
      setEditingTemplate(null);
    }, 'Template enregistré.');
    if (ok) setEditingTemplate(null);
  };

  const savePatientMessages = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const ok = await runSave(async () => {
      const result = await notificationAdminApi.savePatientWaMessages(formValues(event.currentTarget));
      setNotice(result.message);
    }, 'Messages WhatsApp enregistrés.');
  };

  const applyLogFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = formValues(event.currentTarget);
    setLogFilters({ q: String(values.q ?? ''), status: String(values.status ?? ''), channel: String(values.channel ?? '') });
    setLogPage(1);
  };

  const resend = async (logId: number) => {
    await runSave(() => notificationAdminApi.resendLog(logId), 'Renvoi effectué.');
    try {
      await loadLogs();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’actualiser le journal.');
    }
  };

  return (
    <>
      <AdminWorkspaceHeader />
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
      <header className="mb-5">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Administration</p>
        <h1 className="mt-1 text-2xl font-extrabold text-[#123a63] sm:text-3xl">Notifications</h1>
      </header>
      <nav className="mb-5 flex gap-2 overflow-x-auto border-b border-gray-200 pb-2" aria-label="Administration des notifications">
        {TABS.map((item) => (
          <button key={item.id} type="button" onClick={() => { setTab(item.id); navigate(TAB_PATHS[item.id]); setError(''); setNotice(''); }}
            className={`shrink-0 rounded-lg px-3 py-2 text-sm font-semibold ${tab === item.id ? 'bg-[#e6f4f9] text-[#075985]' : 'text-gray-600 hover:bg-gray-100'}`}>
            {item.label}
          </button>
        ))}
      </nav>
      <Notice error={error} notice={notice} />
      {loading && <p className="mb-4 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement…</p>}

      {tab === 'settings' && settings && (
        <div className="grid gap-5 lg:grid-cols-2">
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900">Email (SMTP)</h2>
            <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={saveSettings('save_smtp')}>
              <label className="flex items-center gap-2 sm:col-span-2"><input name="email_enabled" type="checkbox" defaultChecked={settings.email_enabled} /> Activer l’envoi d’email</label>
              <TextField name="smtp_host" label="Hôte SMTP" initial={settings.smtp_host} />
              <TextField name="smtp_port" label="Port" initial={String(settings.smtp_port)} type="number" />
              <TextField name="smtp_user" label="Utilisateur" initial={settings.smtp_user} />
              <TextField name="smtp_password" label="Mot de passe" type="password" placeholder={settings.smtp_password_configured ? 'Configuré — vide pour conserver' : 'Mot de passe SMTP'} />
              <label className="flex items-center gap-2"><input name="smtp_use_tls" type="checkbox" defaultChecked={settings.smtp_use_tls} /> TLS</label>
              <label className="flex items-center gap-2"><input name="smtp_use_ssl" type="checkbox" defaultChecked={settings.smtp_use_ssl} /> SSL</label>
              <TextField name="smtp_from_email" label="Email expéditeur" initial={settings.smtp_from_email} type="email" />
              <TextField name="smtp_from_name" label="Nom expéditeur" initial={settings.smtp_from_name} />
              <TextField name="smtp_reply_to" label="Reply-To" initial={settings.smtp_reply_to} type="email" />
              <button className={`${buttonClass} sm:col-span-2`} disabled={saving}>Enregistrer SMTP</button>
            </form>
            <form className="mt-5 flex flex-wrap items-end gap-2 border-t border-gray-100 pt-4" onSubmit={saveSettings('test_email')}>
              <TextField name="to_email" label="Email de test" type="email" />
              <button className={buttonClass} disabled={saving}>Envoyer un test</button>
            </form>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900">WhatsApp Cloud API</h2>
            <p className="mt-1 text-xs text-gray-500">Le jeton n’est jamais renvoyé par l’API ; laissez le champ vide pour le conserver.</p>
            <form className="mt-4 space-y-3" onSubmit={saveSettings('save_wa')}>
              <label className="flex items-center gap-2"><input name="whatsapp_enabled" type="checkbox" defaultChecked={settings.whatsapp_enabled} /> Activer WhatsApp Cloud API</label>
              <TextField name="wa_phone_number_id" label="Phone number ID" initial={settings.wa_phone_number_id} />
              <TextField name="wa_business_account_id" label="Business account ID" initial={settings.wa_business_account_id} />
              <label className="block text-sm">Access token {settings.wa_access_token_configured ? <span className="text-xs text-gray-500">(configuré)</span> : null}
                <textarea className={inputClass} name="wa_access_token" rows={3} autoComplete="new-password" />
              </label>
              <TextField name="wa_api_version" label="Version API" initial={settings.wa_api_version} />
              <button className={buttonClass} disabled={saving}>Enregistrer WhatsApp</button>
            </form>
            <form className="mt-5 grid gap-3 border-t border-gray-100 pt-4" onSubmit={saveSettings('test_wa')}>
              <TextField name="to_number" label="Numéro WhatsApp de test" placeholder="+221 77 000 00 00" />
              <label className="block text-sm">Message<textarea className={inputClass} name="message" rows={3} defaultValue="Test MedCare — la configuration WhatsApp Cloud est opérationnelle." /></label>
              <button className={buttonClass} disabled={saving}>Envoyer un test</button>
            </form>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2">
            <h2 className="text-lg font-bold text-gray-900">Réglages généraux</h2>
            <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={saveSettings('save_general')}>
              <label className="flex items-center gap-2"><input name="in_app_enabled" type="checkbox" defaultChecked={settings.in_app_enabled} /> Notifications in-app</label>
              <TextField name="log_retention_days" label="Rétention des journaux (jours)" initial={String(settings.log_retention_days)} type="number" />
              <TextField name="google_reviews_url" label="URL Avis Google" initial={settings.google_reviews_url} type="url" />
              <button className={buttonClass}>Enregistrer les réglages généraux</button>
            </form>
            <h3 className="mt-5 font-semibold">Canaux disponibles</h3>
            <ul className="mt-2 divide-y divide-gray-100 text-sm">
              {channels.map((channel) => <li key={channel.id} className="flex justify-between py-2"><span>{channel.label} <small className="text-gray-400">{channel.code}</small></span><span>{channel.is_enabled ? 'Activé' : 'Désactivé'}</span></li>)}
            </ul>
          </section>
        </div>
      )}

      {tab === 'rules' && rulesData && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">Chaque cellule correspond aux destinataires configurés pour un événement et un canal. Une cellule vide n’a pas encore de règle.</p>
          <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Événement</th>{rulesData.channels.map((channel) => <th key={channel.id} className="px-4 py-3 text-center">{channel.label}</th>)}</tr></thead>
              <tbody className="divide-y divide-gray-100">
                {rulesData.events.map((event) => <tr key={event.id}>
                  <th className="px-4 py-3 font-semibold">{event.label}<span className="block text-xs font-normal text-gray-500">{event.code} · {event.audience}</span></th>
                  {rulesData.channels.map((channel) => {
                    const rule = rulesData.rules.find((item) => item.event_id === event.id && item.channel_id === channel.id)?.rule ?? null;
                    return <td key={channel.id} className="px-3 py-3 text-center">
                      <button type="button" onClick={() => void openRule(event.id, channel.id)} className={`rounded-lg border px-3 py-2 text-xs ${rule?.is_active ? 'border-sky-200 bg-sky-50 text-sky-800' : 'border-gray-200 bg-gray-50 text-gray-600'}`}>
                        {rule ? `${rule.target_roles.join(', ') || 'Aucun destinataire'}${rule.is_active ? '' : ' · désactivée'}` : '+ configurer'}
                      </button>
                    </td>;
                  })}
                </tr>)}
              </tbody>
            </table>
          </div>
          {selectedRule && <RuleEditor rule={selectedRule} onCancel={() => setSelectedRule(null)} onSave={saveRule} saving={saving} />}
        </div>
      )}

      {tab === 'templates' && templatesData && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-gray-600">Modèles de messages d’événement (distincts des textes wa.me ouverts par le patient).</p>
            <button type="button" className={buttonClass} onClick={() => setEditingTemplate({
              id: 0, event_id: templatesData.events[0]?.id ?? 0, event_label: '', event_code: '',
              channel_id: templatesData.channels[0]?.id ?? 0, channel_label: '', channel_code: '',
              subject: '', body: '', is_enabled: true, updated_at: '',
            })}>Nouveau template</button>
          </div>
          {editingTemplate && <form onSubmit={saveTemplate} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 font-bold">{editingTemplate.id ? 'Modifier le template' : 'Créer un template'}</h2>
            {!editingTemplate.id && <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm">Événement<select className={inputClass} name="event_id" defaultValue={editingTemplate.event_id}>{templatesData.events.map((item) => <option value={item.id} key={item.id}>{item.label} ({item.code})</option>)}</select></label>
              <label className="text-sm">Canal<select className={inputClass} name="channel_id" defaultValue={editingTemplate.channel_id}>{templatesData.channels.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
            </div>}
            <label className="mt-3 block text-sm">Sujet / Titre<input className={inputClass} name="subject" defaultValue={editingTemplate.subject} /></label>
            <label className="mt-3 block text-sm">Corps<textarea className={inputClass} name="body" rows={8} required defaultValue={editingTemplate.body} /></label>
            <label className="mt-3 flex items-center gap-2 text-sm"><input name="is_enabled" type="checkbox" defaultChecked={editingTemplate.is_enabled} /> Template actif</label>
            <div className="mt-4 flex justify-end gap-2"><button type="button" className="rounded-lg border px-4 py-2 text-sm" onClick={() => setEditingTemplate(null)}>Annuler</button><button className={buttonClass} disabled={saving}>Enregistrer</button></div>
          </form>}
          <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full min-w-[650px] text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Événement</th><th className="px-4 py-3">Canal</th><th className="px-4 py-3">Sujet / Titre</th><th className="px-4 py-3">État</th><th /></tr></thead>
              <tbody className="divide-y divide-gray-100">{templatesData.templates.map((template) => <tr key={template.id}><td className="px-4 py-3">{template.event_label}<span className="block text-xs text-gray-500">{template.event_code}</span></td><td className="px-4 py-3">{template.channel_label}</td><td className="px-4 py-3">{template.subject || '—'}</td><td className="px-4 py-3">{template.is_enabled ? 'Activé' : 'Désactivé'}</td><td className="px-4 py-3 text-right"><button className="font-semibold text-sky-800 underline" onClick={() => setEditingTemplate(template)}>Éditer</button></td></tr>)}</tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'patient-whatsapp' && (
        <form onSubmit={savePatientMessages} className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-4">
            {[
              ['patient_wa_me_message_general', 'Message WhatsApp — contact général'],
              ['patient_wa_me_message_acte', 'Message WhatsApp — par examen'],
              ['patient_wa_me_message_devis_formal', 'Message WhatsApp — devis / sous-devis'],
            ].map(([name, label]) => <label key={name} className="block rounded-2xl border border-gray-200 bg-white p-5 text-sm font-semibold shadow-sm">{label}<textarea className={inputClass} name={name} rows={name.endsWith('formal') ? 12 : 6} required value={patientMessages[name] ?? ''} onChange={(event) => setPatientMessages((previous) => ({ ...previous, [name]: event.target.value }))} /></label>)}
            <div className="flex justify-end"><button className={buttonClass} disabled={saving}>Enregistrer les messages</button></div>
          </div>
          <aside className="h-fit rounded-2xl border border-sky-100 bg-sky-50 p-5 text-sm text-sky-950">
            <h2 className="font-bold">Variables de modèle disponibles</h2>
            <p className="mt-2"><code>{'{{ org.name }}'}</code> établissement, <code>{'{{ acte.name }}'}</code> examen.</p>
            <p className="mt-2">Pour les devis : <code>{'{{ devis.reference }}'}</code>, <code>{'{{ devis_part.reference }}'}</code>, <code>{'{{ total_display }}'}</code> et la boucle <code>{'{% for line in lines %}'}</code>.</p>
          </aside>
        </form>
      )}

      {tab === 'logs' && (
        <section>
          <form key={`${logFilters.q}|${logFilters.status}|${logFilters.channel}`} onSubmit={applyLogFilters} className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4">
            <label className="min-w-[220px] flex-1 text-xs font-semibold text-gray-600">Recherche<input className={inputClass} type="search" name="q" defaultValue={logFilters.q} placeholder="email, sujet, erreur…" /></label>
            <label className="text-xs font-semibold text-gray-600">Statut<select className={inputClass} name="status" defaultValue={logFilters.status}><option value="">Tous</option><option value="sent">Envoyée ({counts.sent ?? 0})</option><option value="failed">Échec ({counts.failed ?? 0})</option><option value="skipped">Ignorée ({counts.skipped ?? 0})</option><option value="queued">En file ({counts.queued ?? 0})</option></select></label>
            <label className="text-xs font-semibold text-gray-600">Canal<select className={inputClass} name="channel" defaultValue={logFilters.channel}><option value="">Tous</option>{logChannels.map((channel) => <option key={channel.code} value={channel.code}>{channel.label}</option>)}</select></label>
            <button className={buttonClass}>Filtrer</button>
            <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={() => { setLogFilters({ q: '', status: '', channel: '' }); setLogPage(1); }}>Réinitialiser</button>
          </form>
          <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-3 py-3">Date</th><th className="px-3 py-3">Événement</th><th className="px-3 py-3">Canal</th><th className="px-3 py-3">Destinataire</th><th className="px-3 py-3">Statut</th><th className="px-3 py-3">Sujet / Erreur</th><th className="px-3 py-3">Action</th></tr></thead>
              <tbody className="divide-y divide-gray-100">
                {logs.map((log) => <tr key={log.id}>
                  <td className="px-3 py-3 text-xs text-gray-500">{new Date(log.created_at).toLocaleString('fr-FR')}</td><td className="px-3 py-3">{log.event_label || '—'}<span className="block text-xs text-gray-500">{log.event_code}</span></td><td className="px-3 py-3">{log.channel_label || '—'}</td>
                  <td className="px-3 py-3">{log.recipient_name || log.recipient_address || '—'}{log.recipient_name && <span className="block text-xs text-gray-500">{log.recipient_address}</span>}</td>
                  <td className="px-3 py-3">{log.status_label}</td><td className="max-w-[260px] px-3 py-3 text-xs">{log.subject || '—'}{log.error && <p className="mt-1 text-red-700">{log.error}</p>}</td>
                  <td className="px-3 py-3">{log.can_resend && <button type="button" className="rounded-lg border px-3 py-1 text-xs font-bold text-sky-800" disabled={saving} onClick={() => void resend(log.id)}>Renvoyer</button>}</td>
                </tr>)}
                {!logs.length && <tr><td className="p-8 text-center text-gray-500" colSpan={7}>Aucun envoi enregistré.</td></tr>}
              </tbody>
            </table>
          </div>
          {pagination && pagination.pages > 1 && <div className="mt-4 flex items-center justify-center gap-3 text-sm">
            <button className="rounded border px-3 py-1 disabled:opacity-50" disabled={!pagination.has_previous} onClick={() => setLogPage(pagination.previous ?? 1)}>←</button>
            <span>Page {pagination.number} / {pagination.pages} · {pagination.total} journal(aux)</span>
            <button className="rounded border px-3 py-1 disabled:opacity-50" disabled={!pagination.has_next} onClick={() => setLogPage(pagination.next ?? pagination.number)}>→</button>
          </div>}
        </section>
      )}
      </main>
    </>
  );
}

function TextField({ name, label, initial, type = 'text', placeholder }: { name: string; label: string; initial?: string; type?: string; placeholder?: string }) {
  return <label className="block text-sm">{label}<input className={inputClass} name={name} type={type} defaultValue={initial} placeholder={placeholder} /></label>;
}

function RuleEditor({ rule, onCancel, onSave, saving }: {
  rule: NotificationAdminRule & { users: { id: number; label: string }[] };
  onCancel: () => void;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  saving: boolean;
}) {
  const roleChoices = [['admin', 'Admins'], ['prestataire', 'Prestataires'], ['patient', 'Patients']];
  return <form onSubmit={onSave} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
    <h2 className="text-lg font-bold">Modifier la règle</h2>
    <div className="mt-4 grid gap-4 sm:grid-cols-3">
      {roleChoices.map(([value, label]) => <label key={value} className="flex items-center gap-2 rounded-lg border p-3"><input type="checkbox" name="target_roles" value={value} defaultChecked={rule.target_roles.includes(value)} /> {label}</label>)}
    </div>
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <label className="block text-sm">Utilisateurs explicites<select className={inputClass} name="target_users" multiple size={8} defaultValue={rule.target_user_ids.map(String)}>{rule.users.map((user) => <option key={user.id} value={user.id}>{user.label}</option>)}</select></label>
      <div className="space-y-3">
        <label className="block text-sm">Adresses e-mail supplémentaires<textarea className={inputClass} name="extra_emails" rows={3} defaultValue={rule.extra_emails} /></label>
        <label className="block text-sm">Note<input className={inputClass} name="note" defaultValue={rule.note} /></label>
        <label className="flex items-center gap-2"><input name="notify_event_actor" type="checkbox" defaultChecked={rule.notify_event_actor} /> Notifier l’acteur de l’événement</label>
        <label className="flex items-center gap-2"><input name="is_active" type="checkbox" defaultChecked={rule.is_active} /> Règle active</label>
        {!rule.template_exists && <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Aucun template n’est configuré pour ce couple événement/canal.</p>}
      </div>
    </div>
    <div className="mt-4 flex justify-end gap-2"><button type="button" className="rounded-lg border px-4 py-2 text-sm" onClick={onCancel}>Annuler</button><button className={buttonClass} disabled={saving}>Enregistrer la règle</button></div>
  </form>;
}
