import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { providerCatalogApi, type ProviderActFormData } from '../lib/api';

export function ProviderActFormPage() {
  const { pk } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState<ProviderActFormData | null>(null);
  const [acte, setActe] = useState('');
  const [price, setPrice] = useState('');
  const [delai, setDelai] = useState('');
  const [available, setAvailable] = useState(true);
  const [notes, setNotes] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const formUrl = pk
    ? `/sante/prestataire/actes/${encodeURIComponent(pk)}/modifier/`
    : '/sante/prestataire/actes/ajouter/';

  useEffect(() => {
    const controller = new AbortController();
    providerCatalogApi.getActForm(formUrl, controller.signal)
      .then((response) => {
        setForm(response);
        setActe(response.acte ? String(response.acte) : '');
        setPrice(response.price || '');
        setDelai(response.delai || '');
        setAvailable(response.is_available ?? true);
        setNotes(response.notes || '');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger le formulaire.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [formUrl]);

  const groupedChoices = useMemo(() => {
    if (!form) return [];
    const query = search.trim().toLocaleLowerCase('fr');
    const groups = new Map<string, ProviderActFormData['choices']>();
    form.choices.forEach((choice) => {
      if (query && !`${choice.name} ${choice.group}`.toLocaleLowerCase('fr').includes(query)) return;
      groups.set(choice.group, [...(groups.get(choice.group) || []), choice]);
    });
    return Array.from(groups, ([label, choices]) => ({ label, choices }));
  }, [form, search]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    const data = new FormData();
    data.set('acte', acte);
    data.set('price', price);
    data.set('delai', delai);
    data.set('is_available', available ? 'on' : '');
    data.set('notes', notes);
    try {
      await providerCatalogApi.saveAct(formUrl, data);
      navigate('/sante/prestataire/actes/', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer cet acte.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <section className="mx-auto max-w-3xl px-4 py-8 text-sm text-gray-600" role="status">Chargement du formulaire…</section>;
  if (!form) return <section className="mx-auto max-w-3xl px-4 py-8"><p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error || 'Formulaire indisponible.'}</p></section>;

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-8">
      <header>
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Catalogue prestataire</p>
        <h1 className="mt-1 text-2xl font-extrabold text-[#123a63]">{form.is_edit ? 'Modifier l’acte' : 'Ajouter un acte'}</h1>
        <p className="mt-1 text-sm text-gray-500">{form.is_edit ? 'Modifiez le tarif, le délai ou la disponibilité.' : 'Choisissez un acte spécifique dans le référentiel, puis indiquez son tarif.'}</p>
      </header>
      {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}

      <form onSubmit={submit} className="mt-5 space-y-5 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7">
        <label className="block text-sm font-semibold text-gray-800">Rechercher un acte
          <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nom de l’acte ou service médical" className="mt-1.5 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
        </label>
        <label className="block text-sm font-semibold text-gray-800">Acte proposé <span className="text-rose-600">*</span>
          <select required value={acte} onChange={(event) => setActe(event.target.value)} className="mt-1.5 w-full rounded-xl border border-gray-300 bg-white px-3 py-2.5 text-sm">
            <option value="">Choisir un acte…</option>
            {groupedChoices.map((group) => <optgroup label={group.label} key={group.label}>
              {group.choices.map((choice) => <option value={choice.id} key={choice.id}>{choice.name}</option>)}
            </optgroup>)}
          </select>
          {!groupedChoices.length && <span className="mt-1 block text-xs text-amber-700">{search ? 'Aucun résultat pour cette recherche.' : 'Aucun acte disponible pour le moment.'}</span>}
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-semibold text-gray-800">Prix (FCFA) <span className="text-rose-600">*</span>
            <input type="number" name="price" required min="1" step="1" value={price} onChange={(event) => setPrice(event.target.value)} className="mt-1.5 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
          </label>
          <label className="block text-sm font-semibold text-gray-800">Délai indicatif
            <select value={delai} onChange={(event) => setDelai(event.target.value)} className="mt-1.5 w-full rounded-xl border border-gray-300 bg-white px-3 py-2.5 text-sm">
              {form.delai_choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
            </select>
          </label>
        </div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700"><input type="checkbox" checked={available} onChange={(event) => setAvailable(event.target.checked)} /> Disponible pour les patients</label>
        <label className="block text-sm font-semibold text-gray-800">Notes
          <textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Conditions particulières, précisions sur la prise en charge…" className="mt-1.5 w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm" />
        </label>
        <div className="flex flex-wrap justify-end gap-2 border-t border-gray-100 pt-4">
          <Link to="/sante/prestataire/actes/" className="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-600">Annuler</Link>
          <button type="submit" disabled={saving || !acte} className="rounded-xl bg-[#0a5c8a] px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">{saving ? 'Enregistrement…' : form.is_edit ? 'Enregistrer' : 'Ajouter au catalogue'}</button>
        </div>
      </form>
    </section>
  );
}
