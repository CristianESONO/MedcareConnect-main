import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Building2, ShieldCheck } from 'lucide-react';
import {
  patientAccountApi,
  type PatientInsuranceCategoryRate,
  type PatientInsuranceData,
} from '../lib/api';

const ACCOUNT_LINKS = [
  { label: 'Tableau de bord', href: '/users/compte/panel/accueil/' },
  { label: 'Mes rendez-vous', href: '/users/compte/panel/rdv/' },
  { label: 'Mes devis', href: '/users/compte/panel/devis/' },
  { label: 'Mes informations', href: '/users/compte/panel/profil/' },
];

const COVERAGE_PRESETS = [50, 60, 70, 80, 90, 100];

export function PatientInsurancePage() {
  const [data, setData] = useState<PatientInsuranceData | null>(null);
  const [hasInsurance, setHasInsurance] = useState(false);
  const [insuranceId, setInsuranceId] = useState('');
  const [insuranceNumber, setInsuranceNumber] = useState('');
  const [coveragePercent, setCoveragePercent] = useState('');
  const [useInEstimates, setUseInEstimates] = useState(true);
  const [categoryRates, setCategoryRates] = useState<PatientInsuranceCategoryRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const applyData = (next: PatientInsuranceData) => {
    setData(next);
    setHasInsurance(next.has_insurance);
    setInsuranceId(next.insurance_id ? String(next.insurance_id) : '');
    setInsuranceNumber(next.insurance_number);
    setCoveragePercent(next.insurance_coverage_pct);
    setUseInEstimates(next.insurance_use_in_estimates);
    setCategoryRates(next.category_rates);
  };

  useEffect(() => {
    const controller = new AbortController();
    patientAccountApi.insurance(controller.signal)
      .then(applyData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger votre couverture.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (loading || !hasInsurance || !insuranceId) return;

    const controller = new AbortController();
    patientAccountApi.insuranceDetails(Number(insuranceId), controller.signal)
      .then((preview) => {
        setCategoryRates(preview.category_rates);
        setData((current) => current ? {
          ...current,
          insurance_name: preview.insurance_name,
          compatible_structures: preview.compatible_structures,
        } : current);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les taux de référence.');
        }
      });
    return () => controller.abort();
  }, [hasInsurance, insuranceId, loading]);

  const saveCoverage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');

    const formData = new FormData(event.currentTarget);
    formData.set('has_insurance', hasInsurance ? '1' : '0');
    if (hasInsurance) formData.set('insurance', insuranceId);

    try {
      const saved = await patientAccountApi.saveInsurance(formData);
      applyData(saved);
      setNotice(hasInsurance ? 'Votre couverture a été enregistrée.' : 'Paiement direct enregistré.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer votre couverture.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">Mon assurance</h1>
      </header>

      <nav className="mb-6 flex gap-2 overflow-x-auto pb-1" aria-label="Navigation du compte patient">
        {ACCOUNT_LINKS.map((item) => (
          <a key={item.href} href={item.href} className="shrink-0 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-600 hover:border-sky-300 hover:text-[#0a5c8a]">
            {item.label}
          </a>
        ))}
        <span className="shrink-0 rounded-full bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white" aria-current="page">
          Assurance
        </span>
      </nav>

      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement de votre couverture…
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
      {notice && (
        <p className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800" role="status">
          {notice}
        </p>
      )}

      {!loading && data && (
        <>
          <form onSubmit={saveCoverage} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-start gap-3">
              <ShieldCheck className="mt-0.5 shrink-0 text-[#0a5c8a]" size={22} aria-hidden="true" />
              <div>
                <h2 className="font-syne text-lg font-bold text-[#123a63]">Avez-vous une assurance maladie ?</h2>
                <p className="mt-1 text-sm leading-6 text-gray-500">
                  Cette information permet de filtrer les structures compatibles et d’estimer votre coût dans le panier.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-2 sm:grid-cols-2" role="group" aria-label="Mode de paiement">
              <button
                type="button"
                onClick={() => setHasInsurance(true)}
                aria-pressed={hasInsurance}
                className={`rounded-xl border px-4 py-3 text-sm font-bold transition ${
                  hasInsurance ? 'border-[#0a5c8a] bg-sky-50 text-[#0a5c8a]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                Oui, j’ai une assurance
              </button>
              <button
                type="button"
                onClick={() => {
                  setHasInsurance(false);
                  setCategoryRates([]);
                }}
                aria-pressed={!hasInsurance}
                className={`rounded-xl border px-4 py-3 text-sm font-bold transition ${
                  !hasInsurance ? 'border-[#0a5c8a] bg-sky-50 text-[#0a5c8a]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                Non / Paiement direct
              </button>
            </div>

            {hasInsurance ? (
              <div className="mt-6 space-y-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm font-semibold text-gray-700">
                    Organisme d’assurance
                    <select
                      name="insurance"
                      value={insuranceId}
                      onChange={(event) => {
                        setInsuranceId(event.target.value);
                        setCategoryRates([]);
                        setError('');
                      }}
                      required
                      className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm font-normal text-gray-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
                    >
                      <option value="">Choisissez votre organisme</option>
                      {data.insurance_options.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.name} · {option.segment}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-semibold text-gray-700">
                    N° adhérent / carte <span className="font-normal text-gray-400">(optionnel)</span>
                    <input
                      name="insurance_number"
                      value={insuranceNumber}
                      onChange={(event) => setInsuranceNumber(event.target.value)}
                      maxLength={100}
                      className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm font-normal text-gray-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
                      placeholder="N° carte / adhérent"
                    />
                  </label>
                </div>

                <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 p-4">
                  <input
                    type="checkbox"
                    name="insurance_use_in_estimates"
                    checked={useInEstimates}
                    onChange={(event) => setUseInEstimates(event.target.checked)}
                    className="mt-0.5 size-4 accent-[#0a5c8a]"
                  />
                  <span>
                    <span className="block text-sm font-bold text-gray-800">Inclure mon assurance dans les estimations</span>
                    <span className="mt-1 block text-xs leading-5 text-gray-500">
                      Panier, devis et couverture affichée dans la recherche. Désactivez cette option pour afficher les tarifs bruts.
                    </span>
                  </span>
                </label>

                <div>
                  <label htmlFor="insurance-coverage-percent" className="block text-sm font-semibold text-gray-700">
                    Taux global de prise en charge
                  </label>
                  <p className="mt-1 text-xs text-gray-500">
                    Appliqué par défaut à vos estimations panier et devis, sauf taux défini par catégorie.
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <input
                      id="insurance-coverage-percent"
                      name="insurance_coverage_pct"
                      type="number"
                      min="0"
                      max="100"
                      step="0.5"
                      inputMode="decimal"
                      value={coveragePercent}
                      onChange={(event) => setCoveragePercent(event.target.value)}
                      className="w-full max-w-48 rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
                      placeholder="ex. 70"
                    />
                    {COVERAGE_PRESETS.map((rate) => (
                      <button
                        key={rate}
                        type="button"
                        onClick={() => setCoveragePercent(String(rate))}
                        className={`rounded-lg border px-3 py-2 text-xs font-bold ${
                          coveragePercent === String(rate)
                            ? 'border-[#0a5c8a] bg-sky-50 text-[#0a5c8a]'
                            : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        {rate} %
                      </button>
                    ))}
                  </div>
                </div>

                {categoryRates.length > 0 && (
                  <fieldset>
                    <legend className="text-sm font-bold text-gray-800">Taux par catégorie d’acte</legend>
                    <p className="mt-1 text-xs text-gray-500">
                      Les taux de référence sont indicatifs. Une valeur saisie ici est prioritaire sur le taux global.
                    </p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      {categoryRates.map((rate) => (
                        <label key={`${insuranceId}-${rate.field}`} className="block text-sm font-medium text-gray-700">
                          {rate.label}
                          <div className="mt-1 flex items-center gap-2">
                            <input
                              name={rate.field}
                              type="number"
                              min="0"
                              max="100"
                              step="0.5"
                              inputMode="decimal"
                              defaultValue={rate.value}
                              placeholder={rate.reference || '—'}
                              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
                            />
                            <span className="text-sm text-gray-500">%</span>
                          </div>
                          {rate.reference && (
                            <span className="mt-1 block text-xs text-gray-400">Référence indicative : {rate.reference} %</span>
                          )}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                )}
              </div>
            ) : (
              <div className="mt-5 rounded-xl border border-sky-100 bg-sky-50 p-4 text-sm leading-6 text-sky-900">
                Vous paierez directement à la structure. Les tarifs affichés sur MedCare sont les tarifs pratiqués, sans frais supplémentaires de notre part.
              </div>
            )}

            <button
              type="submit"
              disabled={saving}
              className="mt-6 w-full rounded-xl bg-[#0a5c8a] px-5 py-3 text-sm font-bold text-white hover:bg-[#084b70] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {saving ? 'Enregistrement…' : hasInsurance ? 'Enregistrer ma couverture' : 'Enregistrer (paiement direct)'}
            </button>
          </form>

          {hasInsurance && data.compatible_structures.length > 0 && (
            <section className="mt-7">
              <h2 className="mb-3 font-syne text-lg font-bold text-[#123a63]">
                Structures compatibles avec {data.insurance_name || 'votre couverture'}
              </h2>
              <div className="space-y-2">
                {data.compatible_structures.map((organization) => (
                  <article key={organization.url} className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex min-w-0 items-center gap-3">
                      <Building2 size={18} className="shrink-0 text-[#0a5c8a]" aria-hidden="true" />
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-bold text-[#123a63]">{organization.name}</h3>
                        <p className="mt-1 text-xs text-gray-500">{organization.location} · {data.insurance_name}</p>
                      </div>
                    </div>
                    <a href={organization.url} target="_blank" rel="noopener noreferrer" className="shrink-0 rounded-lg border border-gray-200 px-3 py-2 text-xs font-bold text-[#0a5c8a] hover:bg-sky-50">
                      Voir
                    </a>
                  </article>
                ))}
              </div>
            </section>
          )}

          <section className="mt-7 rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="font-syne text-lg font-bold text-[#123a63]">Intégration CMU · Feuille de route</h2>
            <ol className="mt-4 space-y-3 text-sm text-gray-600">
              <li><span className="mr-2 font-bold text-emerald-700">1.</span>Scan QR Code carte CMU · Disponible maintenant</li>
              <li><span className="mr-2 font-bold text-amber-700">2.</span>Lecture puce NFC CMU · ~18–24 mois</li>
              <li><span className="mr-2 font-bold text-gray-400">3.</span>Identifiant biométrique unique · ~36+ mois</li>
            </ol>
          </section>
        </>
      )}
    </section>
  );
}
