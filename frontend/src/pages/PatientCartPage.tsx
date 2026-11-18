import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Minus, Plus, ShoppingBag, Trash2 } from 'lucide-react';
import { cartApi, type PatientCartLine, type PatientCartPageData } from '../lib/api';

const ACCOUNT_LINKS = [
  { label: 'Tableau de bord', href: '/users/compte/panel/accueil/' },
  { label: 'Mes rendez-vous', href: '/users/compte/panel/rdv/' },
  { label: 'Mes devis', href: '/users/compte/panel/devis/' },
  { label: 'Assurance', href: '/users/compte/panel/assurance/' },
];

function amount(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString('fr-FR') : '0';
}

function coverageBadge(status: string, insuranceSelected: boolean) {
  if (insuranceSelected) {
    if (status === 'covered') return { label: 'Couvert', classes: 'bg-emerald-50 text-emerald-700' };
    if (status === 'excluded') return { label: 'Non couvert', classes: 'bg-rose-50 text-rose-700' };
    return { label: 'À confirmer', classes: 'bg-amber-50 text-amber-800' };
  }
  if (status === 'covered') return { label: 'Couvert · IPM', classes: 'bg-emerald-50 text-emerald-700' };
  if (status === 'excluded') return { label: 'Non couvert · IPM', classes: 'bg-rose-50 text-rose-700' };
  return { label: 'IPM à confirmer', classes: 'bg-amber-50 text-amber-800' };
}

function lineAmount(line: PatientCartLine, data: PatientCartPageData) {
  if (
    data.insurance_use_in_estimates
    && data.insurance_id
    && line.status_assurance === 'covered'
    && line.price_assurance
  ) {
    return line.price_assurance;
  }
  if (
    data.insurance_use_in_estimates
    && data.insurance_id
    && line.coverage_rate
    && line.patient_cost !== line.subtotal
  ) {
    return line.patient_cost;
  }
  return line.subtotal;
}

export function PatientCartPage({
  onCartChange,
  accountMode = false,
}: {
  onCartChange: () => Promise<void>;
  accountMode?: boolean;
}) {
  const [data, setData] = useState<PatientCartPageData | null>(null);
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const loading = data === null && !error;

  const loadCart = useCallback(async (signal?: AbortSignal) => {
    const snapshot = await cartApi.accountPage(signal);
    setData(snapshot);
  }, []);
  const handleLoadError = useCallback((reason: unknown) => {
    setError(reason instanceof Error ? reason.message : 'Impossible de charger votre panier.');
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadCart(controller.signal)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          handleLoadError(reason);
        }
      });
    return () => controller.abort();
  }, [handleLoadError, loadCart]);

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

  const saveQuantity = (line: PatientCartLine, nextQuantity: number) => {
    const quantity = Math.max(1, Math.min(999, Math.trunc(nextQuantity) || 1));
    void refreshAfter(() => cartApi.updateQuantity(line.id, quantity));
  };

  const clearCart = () => {
    if (!window.confirm('Confirmez-vous que vous souhaitez vider votre panier ?')) return;
    void refreshAfter(() => cartApi.clear(), 'Votre panier a été vidé.');
  };

  const selectInsurance = (value: string) => {
    const id = value ? Number(value) : null;
    if (id !== null && !Number.isInteger(id)) {
      setError('Organisme d’assurance invalide.');
      return;
    }
    void refreshAfter(
      () => cartApi.selectInsurance(id),
      id ? 'La simulation d’assurance a été mise à jour.' : 'Simulation sans assurance activée.',
    );
  };

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">
          {accountMode ? 'Espace compte' : 'Espace patient'}
        </p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          <ShoppingBag size={24} aria-hidden="true" />
          Mon panier
        </h1>
      </header>

      <nav className="mb-6 flex gap-2 overflow-x-auto pb-1" aria-label={accountMode ? 'Navigation du compte' : 'Navigation du compte patient'}>
        {(accountMode
          ? [{ label: 'Rechercher des soins', href: '/sante/recherche/' }, { label: 'Historique panier', href: '/cart/historique/' }]
          : ACCOUNT_LINKS).map((item) => (
          <a key={item.href} href={item.href} className="shrink-0 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-600 hover:border-sky-300 hover:text-[#0a5c8a]">
            {item.label}
          </a>
        ))}
        <span className="shrink-0 rounded-full bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white" aria-current="page">
          Panier
        </span>
      </nav>

      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement du panier…
        </p>
      )}
      {error && (
        <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          {error}
          {error.includes('Authentification') && (
            <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="ml-2 font-semibold underline">
              Se connecter
            </Link>
          )}
        </p>
      )}
      {notice && <p className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}

      {!loading && data && (data.item_count > 0 ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)]">
          <div className="space-y-4">
            {data.groups.map((group) => (
              <article key={group.organization_id} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
                <header className="flex items-start justify-between gap-3 border-b border-gray-100 bg-gray-50/70 p-4">
                  <h2 className="font-bold text-[#123a63]">{group.organization}</h2>
                  <p className="shrink-0 text-right text-sm font-bold text-gray-800">
                    {data.insurance_use_in_estimates && data.insurance_id
                      ? `${amount(group.patient_subtotal)} FCFA`
                      : `${amount(group.subtotal)} FCFA`}
                    {data.insurance_use_in_estimates && data.insurance_id && group.patient_subtotal !== group.subtotal && (
                      <span className="mt-0.5 block text-xs font-normal text-gray-400 line-through">
                        {amount(group.subtotal)} F
                      </span>
                    )}
                  </p>
                </header>

                <div className="divide-y divide-gray-100 px-4">
                  {group.lines.map((line) => {
                    const selectedInsurance = Boolean(data.insurance_id && data.insurance_use_in_estimates);
                    const badge = coverageBadge(
                      selectedInsurance ? line.status_assurance : line.status_ipm,
                      selectedInsurance,
                    );
                    const quantity = quantities[line.id] ?? String(line.quantity);

                    return (
                      <div key={line.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-gray-900">
                            {line.acte}{line.quantity > 1 ? ` ×${line.quantity}` : ''}
                          </h3>
                          <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.classes}`}>
                            {badge.label}
                          </span>
                        </div>
                        <div className="flex items-center justify-between gap-3 sm:justify-end">
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              aria-label={`Diminuer la quantité de ${line.acte}`}
                              onClick={() => saveQuantity(line, line.quantity - 1)}
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
                                if (Number(quantity) !== line.quantity) saveQuantity(line, Number(quantity));
                              }}
                              className="w-14 rounded-md border border-gray-200 px-2 py-1.5 text-center text-sm"
                            />
                            <button
                              type="button"
                              aria-label={`Augmenter la quantité de ${line.acte}`}
                              onClick={() => saveQuantity(line, line.quantity + 1)}
                              disabled={busy || line.quantity >= 999}
                              className="rounded-md border border-gray-200 p-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                            >
                              <Plus size={14} aria-hidden="true" />
                            </button>
                          </div>
                          <span className="min-w-24 text-right text-sm font-bold text-[#123a63]">
                            {amount(lineAmount(line, data))} F
                          </span>
                          <button
                            type="button"
                            aria-label={`Retirer ${line.acte} du panier`}
                            onClick={() => void refreshAfter(() => cartApi.remove(line.prestataire_acte_id))}
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

                <footer className="border-t border-gray-100 bg-gray-50/50 p-4">
                  <p className="mb-3 text-xs text-gray-500">La demande regroupera les actes de cette structure dans une même discussion.</p>
                  <a
                    href={`/cart/devis/generer/?org=${group.organization_id}`}
                    onClick={(event) => {
                      const lines = group.lines.map((line) => `${line.acte}${line.quantity > 1 ? ` ×${line.quantity}` : ''}`).join(' ; ');
                      if (!window.confirm(`Envoyer une demande à ${group.organization} pour : ${lines}. Confirmer ?`)) {
                        event.preventDefault();
                      }
                    }}
                    className="inline-flex w-full items-center justify-center rounded-lg bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#084b70] sm:w-auto"
                  >
                    Réserver mes actes chez {group.organization}
                  </a>
                </footer>
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
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Simulation assurance</h2>
              <label className="mt-3 block text-sm font-semibold text-gray-700" htmlFor="cart-insurance">
                Assurance à appliquer
              </label>
              <select
                id="cart-insurance"
                value={data.insurance_id ?? ''}
                onChange={(event) => selectInsurance(event.target.value)}
                disabled={busy}
                className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100 disabled:opacity-60"
              >
                <option value="">Sans assurance</option>
                {data.insurance_options.map((group) => (
                  <optgroup key={group.segment} label={group.segment}>
                    {group.options.map((option) => (
                      <option key={option.id} value={option.id}>{option.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select>

              {data.insurance_id ? (
                data.insurance_use_in_estimates ? (
                  <div className="mt-4 rounded-xl border border-sky-100 bg-sky-50 p-3 text-sm text-sky-900">
                    <p className="font-semibold">Assurance appliquée aux estimations : {data.insurance_name}</p>
                    <p className="mt-1 text-xs">Estimation indicative selon les taux disponibles et la compatibilité des structures.</p>
                  </div>
                ) : (
                  <div className="mt-4 rounded-xl bg-gray-50 p-3 text-sm text-gray-700">
                    <p className="font-semibold">Tarifs bruts affichés</p>
                    <p className="mt-1 text-xs">Votre assurance reste enregistrée, mais n’est pas incluse dans les montants.</p>
                    {!accountMode && (
                      <Link to="/users/compte/panel/assurance/" className="mt-2 inline-block text-xs font-semibold text-[#0a5c8a] hover:underline">
                        Activer les estimations assurance →
                      </Link>
                    )}
                  </div>
                )
              ) : (
                <p className="mt-3 text-xs leading-5 text-gray-500">
                  Les montants affichés correspondent au paiement direct.
                  {' '}
                  {!accountMode && (
                    <Link to="/users/compte/panel/assurance/" className="font-semibold text-[#0a5c8a] hover:underline">
                      Renseigner mon assurance
                    </Link>
                  )}
                </p>
              )}
            </section>

            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Récapitulatif</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">Total brut</dt>
                  <dd className="font-semibold text-gray-900">{amount(data.total_brut)} FCFA</dd>
                </div>
                {data.insurance_use_in_estimates && data.insurance_id && (
                  <>
                    <div className="flex justify-between gap-3">
                      <dt className="text-gray-500">Prise en charge estimée</dt>
                      <dd className="font-semibold text-emerald-700">−{amount(data.total_coverage)} F</dd>
                    </div>
                    <div className="flex justify-between gap-3 border-t border-gray-100 pt-3">
                      <dt className="font-bold text-gray-900">Total estimatif patient</dt>
                      <dd className="font-extrabold text-[#123a63]">{amount(data.total_patient)} FCFA</dd>
                    </div>
                  </>
                )}
              </dl>
              <div className="mt-4 space-y-1.5 rounded-lg bg-gray-50 p-3 text-[11px] leading-5 text-gray-600">
                <p><strong className="text-emerald-700">Couvert</strong> — tarif conventionné déclaré par la structure.</p>
                <p><strong className="text-rose-700">Non couvert</strong> — à régler au comptant.</p>
                <p><strong className="text-amber-700">À confirmer</strong> — estimation à vérifier auprès de l’assureur.</p>
              </div>
              <p className="mt-3 text-[10px] italic text-gray-400">Estimation indicative — à confirmer avec votre assureur.</p>
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
