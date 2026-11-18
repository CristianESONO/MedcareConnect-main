import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Minus, Plus, ShoppingBag, Trash2 } from 'lucide-react';
import { cartApi, type GuestCartPageData } from '../lib/api';

function amount(value: string | number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString('fr-FR') : '0';
}

export function GuestCartPage({ onCartChange }: { onCartChange: () => Promise<void> }) {
  const [data, setData] = useState<GuestCartPageData | null>(null);
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const loading = data === null && !error;

  const loadCart = useCallback(async (signal?: AbortSignal) => {
    setData(await cartApi.guestPage(signal));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    cartApi.guestPage(controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger votre panier.');
        }
      });
    return () => controller.abort();
  }, []);

  const refreshAfter = async (action: () => Promise<unknown>, successMessage?: string) => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      await loadCart();
      await onCartChange();
      setQuantities({});
      if (successMessage) setNotice(successMessage);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de mettre à jour votre panier.');
    } finally {
      setBusy(false);
    }
  };

  const saveQuantity = (paId: number, quantity: number) => {
    const next = Math.max(1, Math.min(999, Math.trunc(quantity) || 1));
    void refreshAfter(() => cartApi.updateGuestQuantity(paId, next));
  };

  const selectInsurance = (value: string) => {
    const id = value ? Number(value) : null;
    if (id !== null && !Number.isInteger(id)) {
      setError('Organisme d’assurance invalide.');
      return;
    }
    void refreshAfter(
      () => cartApi.selectGuestInsurance(id),
      id ? 'La simulation indicative a été mise à jour.' : 'Simulation sans assurance activée.',
    );
  };

  const clearCart = () => {
    if (!window.confirm('Confirmez-vous que vous souhaitez vider votre panier ?')) return;
    void refreshAfter(() => cartApi.clear(), 'Votre panier a été vidé.');
  };

  const next = encodeURIComponent('/cart/');

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="mb-5">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Visiteur</p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          <ShoppingBag size={24} aria-hidden="true" />
          Votre chariot
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">
          Votre sélection est conservée dans cette session. Connectez-vous avec un compte patient pour la fusionner à votre panier et envoyer une demande de devis.
        </p>
      </header>

      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement du panier…
        </p>
      )}
      {error && <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {notice && <p className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}

      {!loading && data && (data.item_count > 0 ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)]">
          <div className="space-y-4">
            {data.groups.map((group) => (
              <article key={group.organization_id} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
                <header className="flex items-start justify-between gap-3 border-b border-gray-100 bg-gray-50/70 p-4">
                  <h2 className="font-bold text-[#123a63]">{group.organization}</h2>
                  <p className="shrink-0 text-right text-sm font-bold text-gray-800">{amount(group.subtotal)} FCFA</p>
                </header>
                <div className="divide-y divide-gray-100 px-4">
                  {group.lines.map((line) => {
                    const quantity = quantities[line.id] ?? String(line.quantity);
                    return (
                      <div key={line.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-gray-900">{line.acte}</h3>
                          <p className="mt-1 text-xs text-gray-500">{line.category}</p>
                        </div>
                        <div className="flex items-center justify-between gap-3 sm:justify-end">
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              aria-label={`Diminuer la quantité de ${line.acte}`}
                              onClick={() => saveQuantity(line.id, line.quantity - 1)}
                              disabled={busy || line.quantity <= 1}
                              className="rounded-md border border-gray-200 p-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                            >
                              <Minus size={14} aria-hidden="true" />
                            </button>
                            <input
                              aria-label={`Quantité de ${line.acte}`}
                              type="number"
                              min="1"
                              max="999"
                              value={quantity}
                              onChange={(event) => setQuantities((current) => ({ ...current, [line.id]: event.target.value }))}
                              onBlur={() => {
                                if (Number(quantity) !== line.quantity) saveQuantity(line.id, Number(quantity));
                              }}
                              className="w-14 rounded-md border border-gray-200 px-2 py-1.5 text-center text-sm"
                            />
                            <button
                              type="button"
                              aria-label={`Augmenter la quantité de ${line.acte}`}
                              onClick={() => saveQuantity(line.id, line.quantity + 1)}
                              disabled={busy || line.quantity >= 999}
                              className="rounded-md border border-gray-200 p-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                            >
                              <Plus size={14} aria-hidden="true" />
                            </button>
                          </div>
                          <span className="min-w-24 text-right text-sm font-bold text-[#123a63]">{amount(line.subtotal)} F</span>
                          <button
                            type="button"
                            aria-label={`Retirer ${line.acte} du panier`}
                            onClick={() => void refreshAfter(() => cartApi.remove(line.id))}
                            disabled={busy}
                            className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                          >
                            <Trash2 size={16} aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </article>
            ))}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <Link to="/sante/recherche/" className="text-sm font-semibold text-[#0a5c8a] hover:underline">
                ← Continuer la recherche
              </Link>
              <button type="button" onClick={clearCart} disabled={busy} className="text-sm font-semibold text-red-600 hover:underline disabled:opacity-50">
                Vider le panier
              </button>
            </div>
          </div>

          <aside className="space-y-4">
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Assurance (simulation)</h2>
              <label className="mt-3 block text-sm font-semibold text-gray-700" htmlFor="guest-cart-insurance">
                Assurance à simuler
              </label>
              <select
                id="guest-cart-insurance"
                value={data.insurance_id ?? ''}
                onChange={(event) => selectInsurance(event.target.value)}
                disabled={busy}
                className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:opacity-60"
              >
                <option value="">Sans assurance</option>
                {data.insurance_options.map((group) => (
                  <optgroup key={group.segment} label={group.segment}>
                    {group.options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
                  </optgroup>
                ))}
              </select>
              <p className="mt-3 text-xs leading-5 text-gray-500">
                La simulation est indicative. Le devis définitif et la prise en charge nécessitent un compte patient.
              </p>
            </section>

            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Récapitulatif</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">Total brut</dt>
                  <dd className="font-semibold text-gray-900">{amount(data.total_brut)} FCFA</dd>
                </div>
                {data.coverage && (
                  <>
                    <div className="flex justify-between gap-3">
                      <dt className="text-gray-500">Prise en charge estimée</dt>
                      <dd className="font-semibold text-emerald-700">−{amount(data.coverage.total_assurance)} F</dd>
                    </div>
                    <div className="flex justify-between gap-3 border-t border-gray-100 pt-3">
                      <dt className="font-bold text-gray-900">Reste estimatif</dt>
                      <dd className="font-extrabold text-[#123a63]">{amount(data.coverage.total_patient)} FCFA</dd>
                    </div>
                  </>
                )}
              </dl>
              <p className="mt-3 text-[10px] italic text-gray-400">Montants indicatifs, à confirmer auprès de la structure et de votre assureur.</p>
              <a href={`/connexion/?next=${next}`} className="mt-5 block w-full rounded-lg bg-[#0a5c8a] px-4 py-2.5 text-center text-sm font-bold text-white hover:bg-[#084b70]">
                Connexion pour demander un devis
              </a>
              <a href={`/inscription/?next=${next}`} className="mt-2 block w-full rounded-lg border border-gray-200 px-4 py-2.5 text-center text-sm font-semibold text-gray-700 hover:bg-gray-50">
                Créer un compte patient
              </a>
            </section>
          </aside>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <ShoppingBag size={34} className="mx-auto text-gray-300" aria-hidden="true" />
          <h2 className="mt-3 font-semibold text-gray-700">Votre panier est vide</h2>
          <p className="mt-1 text-sm text-gray-500">Sélectionnez des actes depuis la page prestations pour construire votre parcours.</p>
          <Link to="/sante/recherche/" className="mt-4 inline-block rounded-lg bg-[#0a5c8a] px-5 py-2.5 text-sm font-bold text-white">
            Rechercher des soins
          </Link>
        </div>
      ))}
    </section>
  );
}
