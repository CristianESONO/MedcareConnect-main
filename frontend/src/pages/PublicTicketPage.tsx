import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { CalendarDays, MapPin, ShoppingCart } from 'lucide-react';
import { publicTicketApi, type PublicTicketData } from '../lib/api';

function price(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0
    ? `${new Intl.NumberFormat('fr-FR').format(parsed)} FCFA`
    : 'Tarif sur demande';
}

export function PublicTicketPage() {
  const { token = '' } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState<PublicTicketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    publicTicketApi.get(token, location.search, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger cette prestation.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [location.search, token]);

  const addToCart = async () => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const response = await publicTicketApi.action(token, 'add_cart');
      setNotice(response.message || 'Prestation ajoutée au panier.');
      if (response.cart_url) navigate(response.cart_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ajouter cette prestation au panier.');
    } finally {
      setBusy(false);
    }
  };

  const requestQuote = async () => {
    if (!data) return;
    setBusy(true);
    setError('');
    try {
      if (data.kind === 'panel') {
        window.location.assign(data.contact_url);
        return;
      }
      const response = await publicTicketApi.action(token, 'request_devis');
      if (response.login_url) {
        window.location.assign(response.login_url);
      } else if (response.redirect_url) {
        window.location.assign(response.redirect_url);
      } else {
        setNotice(response.message || 'Votre demande a été envoyée.');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de contacter ce prestataire.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <p className="mx-auto max-w-5xl px-4 py-10 text-sm text-gray-600" role="status">Chargement de la prestation…</p>;
  }
  if (error && !data) {
    return <p className="mx-auto mt-8 max-w-5xl rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>;
  }
  if (!data) return null;

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <p className="mb-4 text-sm">
        <Link to={`/sante/${data.provider.slug}/`} className="font-semibold text-sky-800 hover:underline">← Voir la fiche de {data.provider.name}</Link>
      </p>
      <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <header className="bg-gradient-to-br from-[#0a4a72] to-[#054a38] p-6 text-white sm:p-8">
          <p className="text-xs font-bold uppercase tracking-widest text-white/75">{data.kind === 'panel' ? 'Panel d’examens' : 'Prestation'}</p>
          <h1 className="mt-2 font-syne text-2xl font-extrabold sm:text-3xl">{data.title}</h1>
          <p className="mt-2 flex items-center gap-2 text-sm text-white/85">
            <MapPin size={16} aria-hidden="true" /> {data.provider.name}{data.provider.city ? ` · ${data.provider.city}` : ''}
          </p>
        </header>
        <div className="grid gap-6 p-5 sm:p-8 md:grid-cols-[minmax(0,1.5fr)_minmax(240px,1fr)]">
          <div>
            {data.description && <p className="whitespace-pre-line text-sm leading-6 text-gray-700">{data.description}</p>}
            {data.kind === 'ticket' && (
              <dl className="mt-5 grid gap-3 sm:grid-cols-2">
                {data.mode && <div className="rounded-xl bg-gray-50 p-3"><dt className="text-xs text-gray-500">Modalité</dt><dd className="mt-1 text-sm font-semibold text-gray-900">{data.mode}</dd></div>}
                {data.zone && <div className="rounded-xl bg-gray-50 p-3"><dt className="text-xs text-gray-500">Zone</dt><dd className="mt-1 text-sm font-semibold text-gray-900">{data.zone}</dd></div>}
                {data.availability && <div className="rounded-xl bg-gray-50 p-3 sm:col-span-2"><dt className="text-xs text-gray-500">Disponibilités</dt><dd className="mt-1 flex items-center gap-2 text-sm font-semibold text-gray-900"><CalendarDays size={15} />{data.availability}</dd></div>}
                {data.act && <div className="rounded-xl bg-gray-50 p-3 sm:col-span-2"><dt className="text-xs text-gray-500">Acte associé</dt><dd className="mt-1 text-sm font-semibold text-gray-900">{data.act}</dd></div>}
              </dl>
            )}
            {data.acts && data.acts.length > 0 && (
              <div className="mt-5">
                <h2 className="font-syne text-lg font-bold text-[#123a63]">Examens inclus</h2>
                <ul className="mt-2 divide-y divide-gray-100 rounded-xl border border-gray-100">
                  {data.acts.map((act, index) => (
                    <li key={`${act.name}-${index}`} className="flex justify-between gap-3 px-3 py-2.5 text-sm">
                      <span className="text-gray-700">{act.name}</span>
                      <span className="shrink-0 font-semibold text-gray-900">{price(act.price)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <aside className="h-fit rounded-xl border border-gray-100 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Tarif estimatif</p>
            <p className="mt-1 font-syne text-2xl font-extrabold text-[#123a63]">{price(data.price)}</p>
            <p className="mt-2 text-xs leading-5 text-gray-500">Le prestataire confirmera les conditions et le tarif définitif.</p>
            {error && <p className="mt-3 text-xs text-red-700" role="alert">{error}</p>}
            {notice && <p className="mt-3 text-xs text-emerald-700" role="status">{notice}</p>}
            <div className="mt-5 grid gap-2">
              <button type="button" disabled={busy || data.preview_only} onClick={() => { void addToCart(); }} className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-700 px-4 py-3 text-sm font-bold text-white hover:bg-sky-800 disabled:opacity-50">
                <ShoppingCart size={16} aria-hidden="true" />{busy ? 'En cours…' : 'Ajouter au panier'}
              </button>
              <button type="button" disabled={busy || data.preview_only} onClick={() => { void requestQuote(); }} className="rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-bold text-gray-800 hover:bg-gray-100 disabled:opacity-50">
                Contacter le prestataire
              </button>
            </div>
            <p className="mt-3 text-center text-xs text-gray-500">
              Nouveau sur MedCare ? <a href={data.signup_url} className="font-semibold text-sky-800 hover:underline">Créer un compte</a>
            </p>
          </aside>
        </div>
      </article>
    </section>
  );
}
