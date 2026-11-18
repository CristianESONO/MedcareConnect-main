import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { accountSecurityApi } from '../lib/api';

export function PasswordResetPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const path = window.location.pathname;
  const isSent = path.endsWith('/envoye/');
  const isComplete = path.endsWith('/succes/');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [tokenValid, setTokenValid] = useState(false);
  const [checking, setChecking] = useState(Boolean(uid && token));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!uid || !token) return undefined;
    const controller = new AbortController();
    accountSecurityApi.checkResetToken(uid, token, controller.signal)
      .then(() => setTokenValid(true))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Ce lien est invalide ou expiré.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false);
      });
    return () => controller.abort();
  }, [uid, token]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    const form = new FormData();
    try {
      if (uid && token) {
        form.set('new_password1', password);
        form.set('new_password2', confirmation);
        const response = await accountSecurityApi.resetPassword(uid, token, form);
        navigate(response.redirect_url);
      } else {
        form.set('email', email);
        await accountSecurityApi.requestPasswordReset(form);
        navigate('/mot-de-passe-oublie/envoye/');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de traiter cette demande.');
    } finally {
      setBusy(false);
    }
  };

  const title = isComplete
    ? 'Mot de passe modifié'
    : isSent
      ? 'Vérifiez votre messagerie'
      : uid
        ? 'Créer un nouveau mot de passe'
        : 'Réinitialiser votre mot de passe';

  return (
    <section className="mx-auto w-full max-w-xl px-4 py-12">
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Compte MedCare</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63]">{title}</h1>
        {isSent ? (
          <p className="mt-4 text-sm leading-6 text-gray-600">Si cette adresse correspond à un compte, un lien de réinitialisation vous a été envoyé.</p>
        ) : isComplete ? (
          <p className="mt-4 text-sm leading-6 text-gray-600">Votre mot de passe a été modifié. Vous pouvez maintenant vous connecter.</p>
        ) : (
          <>
            {checking && <p className="mt-4 text-sm text-gray-500" role="status">Vérification du lien…</p>}
            {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
            {!checking && (!uid || (tokenValid && uid && token)) && (
              <form onSubmit={submit} className="mt-5 space-y-4">
                {uid && token ? (
                  <>
                    <label className="block text-sm font-semibold text-gray-700" htmlFor="reset-password">Nouveau mot de passe
                      <input id="reset-password" type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
                    </label>
                    <label className="block text-sm font-semibold text-gray-700" htmlFor="reset-confirm">Confirmer le mot de passe
                      <input id="reset-confirm" type="password" autoComplete="new-password" required minLength={8} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
                    </label>
                  </>
                ) : (
                  <label className="block text-sm font-semibold text-gray-700" htmlFor="reset-email">Adresse e-mail
                    <input id="reset-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 font-normal" />
                  </label>
                )}
                <button type="submit" disabled={busy} className="w-full rounded-lg bg-sky-700 px-4 py-3 text-sm font-bold text-white disabled:opacity-50">
                  {busy ? 'Envoi…' : uid ? 'Enregistrer le mot de passe' : 'Envoyer le lien'}
                </button>
              </form>
            )}
          </>
        )}
        <p className="mt-5 text-sm text-gray-600"><Link to="/connexion/" className="font-semibold text-sky-800 hover:underline">Retour à la connexion</Link></p>
      </div>
    </section>
  );
}
