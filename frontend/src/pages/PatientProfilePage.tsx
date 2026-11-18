import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { patientAccountApi, type PatientProfile } from '../lib/api';

const EMPTY_PROFILE: PatientProfile = {
  first_name: '',
  last_name: '',
  email: '',
  phone_number: '',
  avatar_url: null,
  date_of_birth: '',
  address: '',
  city: '',
  quartier: '',
  last_known_latitude: '',
  last_known_longitude: '',
};

const ACCOUNT_LINKS = [
  { label: 'Tableau de bord', href: '/users/compte/panel/accueil/' },
  { label: 'Mes rendez-vous', href: '/users/compte/panel/rdv/' },
  { label: 'Mes devis', href: '/users/compte/panel/devis/' },
  { label: 'Assurance', href: '/users/compte/panel/assurance/' },
];

export function PatientProfilePage() {
  const [profile, setProfile] = useState<PatientProfile>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [locationError, setLocationError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordNotice, setPasswordNotice] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    patientAccountApi.profile(controller.signal)
      .then((data) => {
        setProfile(data);
        setProfileLoaded(true);
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

  const handleProfileSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setNotice('');
    setSaving(true);
    try {
      const saved = await patientAccountApi.saveProfile(new FormData(event.currentTarget));
      setProfile(saved);
      setNotice('Vos informations ont été enregistrées.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer votre profil.');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordError('');
    setPasswordNotice('');
    setPasswordSaving(true);
    try {
      await patientAccountApi.changePassword(new FormData(event.currentTarget));
      event.currentTarget.reset();
      setPasswordNotice('Votre mot de passe a été modifié.');
    } catch (reason) {
      setPasswordError(reason instanceof Error ? reason.message : 'Impossible de modifier le mot de passe.');
    } finally {
      setPasswordSaving(false);
    }
  };

  const locatePatient = () => {
    setLocationError('');
    if (!navigator.geolocation) {
      setLocationError('La géolocalisation n’est pas disponible sur cet appareil.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setProfile((current) => ({
        ...current,
        last_known_latitude: coords.latitude.toFixed(6),
        last_known_longitude: coords.longitude.toFixed(6),
      })),
      () => setLocationError('Position inaccessible. Vérifiez les autorisations de votre navigateur.'),
      { timeout: 10000, enableHighAccuracy: true },
    );
  };

  const update = (field: keyof PatientProfile, value: string) => {
    setProfile((current) => ({ ...current, [field]: value }));
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Mes informations</h1>
      </header>

      <nav className="mb-6 flex gap-2 overflow-x-auto pb-1" aria-label="Navigation du compte patient">
        {ACCOUNT_LINKS.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="shrink-0 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-600 hover:border-sky-300 hover:text-[#0a5c8a]"
          >
            {item.label}
          </a>
        ))}
        <span className="shrink-0 rounded-full bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white" aria-current="page">
          Mes informations
        </span>
      </nav>

      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement de votre profil…</p>}
      {error && <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}

      {!loading && profileLoaded && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <form onSubmit={handleProfileSubmit} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="font-syne text-lg font-bold text-[#123a63]">Profil personnel</h2>
            <p className="mt-1 text-sm text-gray-500">Vos coordonnées servent à personnaliser les recherches et le suivi de vos soins.</p>

            {notice && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
            {profile.avatar_url && (
              <img src={profile.avatar_url} alt="Photo de profil" className="mt-5 h-16 w-16 rounded-full object-cover" />
            )}
            <label className="mt-4 block text-sm font-semibold text-gray-700">
              Photo de profil
              <input name="avatar" type="file" accept="image/*" className="mt-1 block w-full text-sm text-gray-600" />
            </label>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {([
                ['first_name', 'Prénom', 'text'],
                ['last_name', 'Nom', 'text'],
                ['email', 'Adresse e-mail', 'email'],
                ['phone_number', 'Téléphone', 'tel'],
                ['date_of_birth', 'Date de naissance', 'date'],
                ['city', 'Ville / zone', 'text'],
                ['quartier', 'Quartier', 'text'],
                ['address', 'Adresse', 'text'],
                ['last_known_latitude', 'Latitude', 'number'],
                ['last_known_longitude', 'Longitude', 'number'],
              ] as const).map(([field, label, type]) => (
                <label key={field} className="block text-sm font-semibold text-gray-700">
                  {label}
                  <input
                    name={field}
                    type={type}
                    step={type === 'number' ? 'any' : undefined}
                    value={profile[field]}
                    onChange={(event) => update(field, event.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-normal text-gray-900 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-100"
                  />
                </label>
              ))}
            </div>

            <div className="mt-4">
              <button
                type="button"
                onClick={locatePatient}
                className="rounded-lg border border-sky-200 px-3 py-2 text-sm font-bold text-[#0a5c8a] hover:bg-sky-50"
              >
                Utiliser ma position actuelle
              </button>
              {locationError && <p className="mt-2 text-sm text-red-700" role="alert">{locationError}</p>}
            </div>

            <button type="submit" disabled={saving} className="mt-6 rounded-xl bg-[#0a5c8a] px-5 py-3 text-sm font-bold text-white hover:bg-[#084b70] disabled:opacity-60">
              {saving ? 'Enregistrement…' : 'Enregistrer mes informations'}
            </button>
          </form>

          <form onSubmit={handlePasswordSubmit} className="h-fit rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="font-syne text-lg font-bold text-[#123a63]">Sécurité</h2>
            <p className="mt-1 text-sm text-gray-500">Choisissez un mot de passe difficile à deviner.</p>
            {passwordNotice && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{passwordNotice}</p>}
            {passwordError && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{passwordError}</p>}
            {([
              ['old_password', 'Mot de passe actuel', 'current-password'],
              ['new_password1', 'Nouveau mot de passe', 'new-password'],
              ['new_password2', 'Confirmer le nouveau mot de passe', 'new-password'],
            ] as const).map(([name, label, autoComplete]) => (
              <label key={name} className="mt-4 block text-sm font-semibold text-gray-700">
                {label}
                <input
                  required
                  name={name}
                  type="password"
                  autoComplete={autoComplete}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-normal text-gray-900 outline-none focus:border-sky-600 focus:ring-2 focus:ring-sky-100"
                />
              </label>
            ))}
            <button type="submit" disabled={passwordSaving} className="mt-5 rounded-xl border border-[#0a5c8a] px-5 py-3 text-sm font-bold text-[#0a5c8a] hover:bg-sky-50 disabled:opacity-60">
              {passwordSaving ? 'Modification…' : 'Modifier mon mot de passe'}
            </button>
          </form>
        </div>
      )}

      <Link to="/users/compte/panel/accueil/" className="mt-6 inline-block text-sm font-semibold text-[#0a5c8a] hover:underline">
        ← Retour au tableau de bord
      </Link>
    </section>
  );
}
