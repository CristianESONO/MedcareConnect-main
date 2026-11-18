import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { platformReviewApi, type PlatformReviewData } from '../lib/api';

export function PlatformReviewPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<PlatformReviewData | null>(null);
  const [rating, setRating] = useState('5');
  const [selectedActs, setSelectedActs] = useState<number[]>([]);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    platformReviewApi.get(controller.signal)
      .then((response) => {
        setData(response);
        setSelectedActs(response.selected_acte_ids);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger le formulaire d’avis.');
        }
      });
    return () => controller.abort();
  }, []);

  const toggleAct = (id: number) => {
    setSelectedActs((current) => current.includes(id)
      ? current.filter((value) => value !== id)
      : [...current, id]);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    const form = new FormData();
    form.set('rating', rating);
    form.set('tarifs_delais_comment', comment);
    selectedActs.forEach((id) => form.append('actes', String(id)));
    try {
      const response = await platformReviewApi.submit(form);
      navigate(response.redirect_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’envoyer votre avis.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-4xl px-4 py-8">
      <p className="mb-4 text-sm"><Link to="/users/compte/panel/" className="font-semibold text-sky-800 hover:underline">← Retour à mon compte</Link></p>
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Votre expérience</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63]">Donner un avis sur MedCare</h1>
        <p className="mt-2 text-sm text-gray-600">Votre retour aide à améliorer les informations de soins et de tarifs.</p>
      </header>
      {error && (
        <p className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">
          {error}
          {error.includes('Authentification requise') && (
            <> <a href="/connexion/?next=/sante/avis/" className="font-bold underline">Se connecter</a></>
          )}
        </p>
      )}
      {!data ? (
        <p role="status" className="text-sm text-gray-500">Chargement…</p>
      ) : data.has_review ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Vous avez déjà envoyé un avis depuis ce compte.
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7">
          <fieldset>
            <legend className="text-sm font-bold text-gray-800">Votre note</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5].map((value) => (
                <label key={value} className={`cursor-pointer rounded-lg border px-4 py-2 text-sm font-bold ${rating === String(value) ? 'border-sky-700 bg-sky-50 text-sky-800' : 'border-gray-200 text-gray-600'}`}>
                  <input className="sr-only" type="radio" name="rating" value={value} checked={rating === String(value)} onChange={() => setRating(String(value))} />
                  {value} / 5
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend className="text-sm font-bold text-gray-800">Quels actes ou examens concernent votre avis ?</legend>
            <div className="mt-3 max-h-80 space-y-4 overflow-auto rounded-xl border border-gray-100 p-3">
              {data.groups.map((group) => (
                <div key={group.service}>
                  <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-sky-800">{group.service}</h2>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {group.acts.map((act) => (
                      <label key={act.id} className="flex items-start gap-2 text-xs text-gray-700">
                        <input type="checkbox" checked={selectedActs.includes(act.id)} onChange={() => toggleAct(act.id)} />
                        {act.name}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </fieldset>
          <label className="block text-sm font-bold text-gray-800" htmlFor="review-comment">Tarifs et délais <span className="font-normal text-gray-500">(facultatif)</span>
            <textarea id="review-comment" rows={4} value={comment} onChange={(event) => setComment(event.target.value)} maxLength={2000} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-normal" placeholder="Délais d’attente, transparence des tarifs, tiers payant…" />
          </label>
          <button type="submit" disabled={busy || selectedActs.length === 0} className="rounded-lg bg-sky-700 px-5 py-3 text-sm font-bold text-white disabled:opacity-50">
            {busy ? 'Envoi…' : 'Envoyer mon avis'}
          </button>
        </form>
      )}
    </section>
  );
}

export function PlatformReviewGooglePage() {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    platformReviewApi.googleUrl(controller.signal)
      .then((response) => setUrl(response.google_reviews_url))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger le lien d’avis.');
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto max-w-2xl px-4 py-12 text-center">
      <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
        <p className="text-4xl" aria-hidden="true">✓</p>
        <h1 className="mt-3 font-syne text-2xl font-extrabold text-[#123a63]">Merci pour votre retour</h1>
        <p className="mt-2 text-sm leading-6 text-gray-600">Votre avis MedCare sera publié après modération. Vous pouvez également partager votre expérience sur Google.</p>
        {error && <p className="mt-4 text-sm text-red-700" role="alert">{error}</p>}
        {url && <a href={url} target="_blank" rel="noreferrer" className="mt-5 inline-flex rounded-lg bg-sky-700 px-5 py-3 text-sm font-bold text-white">Laisser un avis Google</a>}
        <p><Link to="/sante/recherche/" className="mt-5 inline-block text-sm font-semibold text-sky-800 hover:underline">Retour à la recherche</Link></p>
      </div>
    </section>
  );
}
