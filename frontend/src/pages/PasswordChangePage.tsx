import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { accountSecurityApi } from '../lib/api';

export function PasswordChangePage() {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    const form = new FormData();
    form.set('old_password', oldPassword);
    form.set('new_password1', newPassword);
    form.set('new_password2', confirmation);
    try {
      const response = await accountSecurityApi.changePassword(form);
      setNotice(response.message);
      setOldPassword('');
      setNewPassword('');
      setConfirmation('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de modifier le mot de passe.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-xl px-4 py-10">
      <p className="mb-4 text-sm"><Link to="/users/compte/panel/profil/" className="font-semibold text-sky-800 hover:underline">← Retour au profil</Link></p>
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Sécurité du compte</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63]">Modifier le mot de passe</h1>
        {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
        {notice && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
        <form onSubmit={submit} className="mt-5 space-y-4">
          <label className="block text-sm font-semibold text-gray-700" htmlFor="old-password">Mot de passe actuel
            <input id="old-password" type="password" autoComplete="current-password" required value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
          </label>
          <label className="block text-sm font-semibold text-gray-700" htmlFor="new-password">Nouveau mot de passe
            <input id="new-password" type="password" autoComplete="new-password" required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
          </label>
          <label className="block text-sm font-semibold text-gray-700" htmlFor="confirm-password">Confirmer le nouveau mot de passe
            <input id="confirm-password" type="password" autoComplete="new-password" required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
          </label>
          <button type="submit" disabled={busy} className="w-full rounded-lg bg-sky-700 px-4 py-3 text-sm font-bold text-white disabled:opacity-50">
            {busy ? 'Enregistrement…' : 'Mettre à jour le mot de passe'}
          </button>
        </form>
      </div>
    </section>
  );
}
