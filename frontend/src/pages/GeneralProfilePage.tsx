import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { generalProfileApi, type GeneralUserProfile } from '../lib/api';

const EMPTY_PROFILE: GeneralUserProfile = {
  first_name: '',
  last_name: '',
  email: '',
  phone_number: '',
  avatar_url: null,
};

export function GeneralProfilePage() {
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    generalProfileApi.get(controller.signal)
      .then((data) => {
        setProfile(data);
        setLoaded(true);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger votre profil.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await generalProfileApi.save(new FormData(event.currentTarget));
      setProfile(saved);
      setNotice('Vos informations ont été enregistrées.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer votre profil.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Mon compte</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Mon profil</h1>
        <p className="mt-2 text-sm text-gray-500">Gérez vos informations personnelles.</p>
      </header>

      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement du profil…</p>}
      {error && (
        <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">
          {error}
          {error.includes('Authentification') && (
            <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">Se connecter</Link>
          )}
        </p>
      )}

      {!loading && loaded && (
        <form onSubmit={save} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="font-syne text-lg font-bold text-[#123a63]">Informations générales</h2>
          {notice && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
          {profile.avatar_url && <img src={profile.avatar_url} alt="Photo de profil" className="mt-5 size-16 rounded-full object-cover" />}
          <label className="mt-5 block text-sm font-semibold text-gray-700">
            Photo de profil
            <input name="avatar" type="file" accept="image/*" className="mt-1 block w-full text-sm font-normal text-gray-600" />
          </label>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {([
              ['first_name', 'Prénom', 'text'],
              ['last_name', 'Nom', 'text'],
              ['email', 'Adresse e-mail', 'email'],
              ['phone_number', 'Téléphone', 'tel'],
            ] as const).map(([field, label, type]) => (
              <label key={field} className="block text-sm font-semibold text-gray-700">
                {label}
                <input
                  name={field}
                  type={type}
                  value={profile[field]}
                  onChange={(change) => setProfile((current) => ({ ...current, [field]: change.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-normal text-gray-900 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-100"
                />
              </label>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <Link to="/users/mot-de-passe/" className="text-sm font-semibold text-[#0a5c8a] hover:underline">Changer le mot de passe →</Link>
            <button type="submit" disabled={saving} className="rounded-xl bg-[#0a5c8a] px-5 py-3 text-sm font-bold text-white hover:bg-[#084b70] disabled:opacity-60">
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
