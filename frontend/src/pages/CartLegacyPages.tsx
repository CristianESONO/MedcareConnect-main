import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Printer, ShoppingBag } from 'lucide-react';
import {
  cartApi,
  type AccountQuoteDetail,
  type AccountQuoteSummary,
  type CartHistoryEntry,
} from '../lib/api';

function amount(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString('fr-FR') : '0';
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function RequestState({
  loading,
  error,
}: {
  loading: boolean;
  error: string;
}) {
  if (loading) {
    return <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement…</p>;
  }
  if (error) {
    return <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>;
  }
  return null;
}

export function LegacyDevisListPage() {
  const [entries, setEntries] = useState<AccountQuoteSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    cartApi.accountQuotes(controller.signal)
      .then((data) => setEntries(data.entries))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les devis.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace compte</p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          <FileText size={23} aria-hidden="true" />
          Mes devis
        </h1>
      </header>
      <RequestState loading={loading} error={error} />
      {!loading && !error && (entries.length ? (
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="divide-y divide-gray-100">
            {entries.map((entry) => (
              <article key={entry.reference} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="font-bold text-[#123a63]">{entry.reference}</h2>
                  <p className="mt-1 text-xs text-gray-500">
                    {dateTime(entry.created_at)} · Assurance : {entry.insurance || '—'}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3 sm:justify-end">
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">{entry.status}</span>
                  <span className="font-bold text-[#123a63]">{amount(entry.total_patient)} FCFA</span>
                  <Link
                    to={`/cart/devis/${encodeURIComponent(entry.reference)}/`}
                    className="rounded-lg bg-[#0a5c8a] px-4 py-2 text-xs font-bold text-white hover:bg-[#084b70]"
                  >
                    Voir le devis
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <FileText size={30} className="mx-auto text-gray-400" aria-hidden="true" />
          <h2 className="mt-3 font-semibold text-gray-700">Aucun devis généré</h2>
        </div>
      ))}
    </section>
  );
}

export function LegacyDevisDetailPage() {
  const { reference = '' } = useParams();
  const [devis, setDevis] = useState<AccountQuoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    cartApi.accountQuote(reference, controller.signal)
      .then((data) => setDevis(data.devis))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger ce devis.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reference]);

  return (
    <section className="mx-auto w-full max-w-4xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/cart/devis/" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-[#0a5c8a] hover:underline">
            <ArrowLeft size={16} aria-hidden="true" /> Tous mes devis
          </Link>
          <h1 className="font-syne text-2xl font-extrabold text-[#123a63]">Détail du devis</h1>
        </div>
        {devis && (
          <button type="button" onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
            <Printer size={16} aria-hidden="true" /> Imprimer / PDF
          </button>
        )}
      </div>
      <RequestState loading={loading} error={error} />
      {!loading && !error && devis && (
        <>
          <header className="mb-5 flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-gray-200 bg-white p-5">
            <div>
              <p className="text-sm font-bold text-[#123a63]">{devis.reference}</p>
              <p className="mt-1 text-xs text-gray-500">
                Généré le {dateTime(devis.created_at)}
                {devis.valid_until ? ` · Valide jusqu’au ${new Intl.DateTimeFormat('fr-FR').format(new Date(`${devis.valid_until}T00:00:00`))}` : ''}
              </p>
            </div>
            <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-800">{devis.status}</span>
          </header>

          <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
            <div className="divide-y divide-gray-100">
              {devis.details.map((line, index) => (
                <div key={`${line.acte}-${index}`} className="flex flex-col justify-between gap-2 px-5 py-4 sm:flex-row sm:items-center">
                  <div>
                    <p className="font-semibold text-gray-900">{line.acte}{line.quantity > 1 ? ` × ${line.quantity}` : ''}</p>
                    <p className="mt-1 text-xs text-gray-500">{line.organisme}</p>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="text-sm font-semibold text-gray-900">{amount(line.subtotal)} FCFA</p>
                    {line.coverage_rate && <p className="text-xs text-emerald-700">Couverture {line.coverage_rate}% · reste {amount(line.patient_cost)} FCFA</p>}
                  </div>
                </div>
              ))}
              {!devis.details.length && (
                <p className="px-5 py-8 text-center text-sm text-gray-500">Aucun détail n’est disponible pour ce devis.</p>
              )}
            </div>
            <div className="border-t border-gray-200 bg-gray-50 px-5 py-4">
              <dl className="ml-auto max-w-sm space-y-2 text-sm">
                <div className="flex justify-between gap-4"><dt className="text-gray-500">Total brut</dt><dd className="font-medium">{amount(devis.total_brut)} FCFA</dd></div>
                {devis.insurance && <div className="flex justify-between gap-4"><dt className="text-gray-500">Assurance · {devis.insurance}</dt><dd className="font-medium text-emerald-700">−{amount(devis.total_assurance)} FCFA</dd></div>}
                <div className="flex justify-between gap-4 border-t border-gray-200 pt-2"><dt className="font-bold text-gray-900">Total estimatif patient</dt><dd className="font-extrabold text-[#123a63]">{amount(devis.total_patient)} FCFA</dd></div>
              </dl>
              <p className="mt-3 text-right text-[11px] text-gray-500">Montant indicatif, à confirmer avec votre assureur ou la structure.</p>
            </div>
          </div>

          {!!devis.parts.length && (
            <section className="mt-5 space-y-3">
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Transmission aux structures</h2>
              {devis.parts.map((part) => (
                <article key={part.reference} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white p-4">
                  <div>
                    <h3 className="font-semibold text-gray-900">{part.organization}</h3>
                    <p className="mt-1 text-xs text-gray-500">{part.reference} · {part.status} · {amount(part.total_brut)} FCFA</p>
                  </div>
                  <div className="flex gap-2">
                    {part.whatsapp_url && <a href={part.whatsapp_url} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-700">WhatsApp</a>}
                    {!part.whatsapp_url && part.phone_url && <a href={part.phone_url} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-700">Appeler</a>}
                  </div>
                </article>
              ))}
            </section>
          )}
        </>
      )}
    </section>
  );
}

export function CartHistoryPage() {
  const [entries, setEntries] = useState<CartHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    cartApi.history(controller.signal)
      .then((data) => setEntries(data.entries))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger l’historique.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace compte</p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          <ShoppingBag size={23} aria-hidden="true" />
          Historique des paniers
        </h1>
      </header>
      <RequestState loading={loading} error={error} />
      {!loading && !error && (entries.length ? (
        <div className="space-y-3">
          {entries.map((entry) => (
            <article key={entry.id} className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div>
                <h2 className="font-semibold text-gray-900">{entry.name} <span className="text-xs font-normal text-gray-400">#{entry.id}</span></h2>
                <p className="mt-1 text-xs text-gray-500">{dateTime(entry.updated_at)} · {entry.item_count} article{entry.item_count === 1 ? '' : 's'}</p>
              </div>
              <div className="text-right">
                <p className="font-bold text-[#123a63]">{amount(entry.total_price)} FCFA</p>
                <span className="text-xs text-gray-500">{entry.status}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <ShoppingBag size={30} className="mx-auto text-gray-400" aria-hidden="true" />
          <p className="mt-3 font-semibold text-gray-700">Aucun historique de panier</p>
        </div>
      ))}
    </section>
  );
}
