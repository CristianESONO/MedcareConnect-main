import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  notificationPreferencesApi,
  type NotificationPreferenceData,
} from '../lib/api';

function preferenceKey(eventId: number, channelId: number) {
  return `${eventId}:${channelId}`;
}

export function NotificationPreferencesPage() {
  const [data, setData] = useState<NotificationPreferenceData | null>(null);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    notificationPreferencesApi.get(controller.signal)
      .then((response) => {
        setData(response);
        setEnabled(Object.fromEntries(
          response.preferences.map((preference) => [
            preferenceKey(preference.event_id, preference.channel_id),
            preference.enabled,
          ]),
        ));
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les préférences.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!data) return;
    setSaving(true);
    setError('');
    setNotice('');
    const formData = new FormData();
    data.events.forEach((notificationEvent) => {
      data.channels.forEach((channel) => {
        const key = preferenceKey(notificationEvent.id, channel.id);
        if (enabled[key]) formData.set(`pref-${notificationEvent.id}-${channel.id}`, 'on');
      });
    });
    try {
      await notificationPreferencesApi.save(formData);
      setNotice('Vos préférences ont été enregistrées.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer les préférences.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Mon compte</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Préférences de notifications</h1>
        <p className="mt-2 max-w-3xl text-sm text-gray-500">
          Choisissez les événements et les canaux pour lesquels vous souhaitez recevoir des notifications. Les règles de destinataires restent gérées par MedCare.
        </p>
      </header>

      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && (
        <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">
          {error}
          {error.includes('Authentification') && (
            <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">Se connecter</Link>
          )}
        </p>
      )}
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement des préférences…</p>}
      {!loading && data && (
        <form onSubmit={save} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {data.channels.length && data.events.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                <thead className="bg-gray-50 text-xs font-bold uppercase tracking-wide text-gray-500">
                  <tr>
                    <th scope="col" className="px-4 py-3 sm:px-5">Événement</th>
                    {data.channels.map((channel) => (
                      <th key={channel.id} scope="col" title={channel.description} className="px-4 py-3 text-center sm:px-5">{channel.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.events.map((notificationEvent) => (
                    <tr key={notificationEvent.id}>
                      <th scope="row" className="px-4 py-4 font-medium text-gray-800 sm:px-5">
                        <span className="block">{notificationEvent.label}</span>
                        <span className="mt-1 block text-xs font-normal text-gray-500" title={notificationEvent.description}>
                          {notificationEvent.description || notificationEvent.audience}
                        </span>
                      </th>
                      {data.channels.map((channel) => {
                        const key = preferenceKey(notificationEvent.id, channel.id);
                        return (
                          <td key={channel.id} className="px-4 py-4 text-center sm:px-5">
                            <input
                              type="checkbox"
                              aria-label={`${notificationEvent.label} — ${channel.label}`}
                              checked={enabled[key] ?? true}
                              onChange={(change) => setEnabled((current) => ({ ...current, [key]: change.target.checked }))}
                              className="size-4 accent-[#0a5c8a]"
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="p-6 text-sm text-gray-500">Aucune préférence configurable pour le moment.</p>
          )}
          <div className="flex justify-end border-t border-gray-100 bg-gray-50/60 px-5 py-4">
            <button type="submit" disabled={saving} className="rounded-xl bg-[#0a5c8a] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#084b70] disabled:opacity-60">
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
