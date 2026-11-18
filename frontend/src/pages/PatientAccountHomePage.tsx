import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, FileText, MapPin, ShieldCheck, ShoppingBag } from 'lucide-react';
import { patientAccountApi, type PatientOverview } from '../lib/api';

const QUICK_LINKS = [
  { label: 'Mes rendez-vous', href: '/users/compte/panel/rdv/', icon: CalendarDays },
  { label: 'Mes devis', href: '/users/compte/panel/devis/', icon: FileText },
  { label: 'Mon assurance', href: '/users/compte/panel/assurance/', icon: ShieldCheck },
  { label: 'Mon panier', href: '/users/compte/panel/chariot/', icon: ShoppingBag },
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function PatientAccountHomePage() {
  const [overview, setOverview] = useState<PatientOverview | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    patientAccountApi.overview(controller.signal)
      .then(setOverview)
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setError(reason instanceof Error ? reason.message : 'Impossible de charger votre espace patient.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="mb-7">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
          Bonjour{overview?.first_name ? `, ${overview.first_name}` : ''}
        </h1>
        <p className="mt-2 text-sm text-gray-500">Retrouvez ici le suivi de vos soins et demandes.</p>
      </header>

      {loading && (
        <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Chargement de votre espace…
        </p>
      )}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
          <p>{error}</p>
          {error.includes('Authentification') && (
            <Link to={`/connexion/?next=${encodeURIComponent(window.location.pathname)}`} className="mt-2 inline-block font-semibold underline">
              Se connecter
            </Link>
          )}
        </div>
      )}

      {overview && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'RDV à venir', value: overview.stats.upcoming_appointments, icon: CalendarDays, color: 'text-blue-700' },
              { label: 'Devis en attente', value: overview.stats.pending_quotes, icon: FileText, color: 'text-emerald-700' },
              { label: 'Assurances', value: overview.stats.insurances, icon: ShieldCheck, color: 'text-violet-700' },
              { label: 'Actes au panier', value: overview.stats.cart_items, icon: ShoppingBag, color: 'text-amber-700' },
            ].map(({ label, value, icon: Icon, color }) => (
              <article key={label} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                <Icon size={20} className={color} aria-hidden="true" />
                <p className="mt-3 text-2xl font-extrabold text-[#123a63]">{value}</p>
                <p className="mt-1 text-xs font-semibold text-gray-500">{label}</p>
              </article>
            ))}
          </div>

          <section className="mt-7 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="font-syne text-lg font-bold text-[#123a63]">Prochain rendez-vous</h2>
            {overview.next_appointment ? (
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-bold text-gray-900">{overview.next_appointment.organization}</p>
                  <p className="mt-1 text-sm capitalize text-gray-600">{formatDate(overview.next_appointment.start)}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    Référence {overview.next_appointment.reference} · {overview.next_appointment.status}
                  </p>
                </div>
                {overview.next_appointment.conversation_url && (
                  <a
                    href={overview.next_appointment.conversation_url}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0a5c8a] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#084b70]"
                  >
                    Ouvrir la conversation
                  </a>
                )}
              </div>
            ) : (
              <p className="mt-3 text-sm text-gray-500">
                Aucun rendez-vous à venir. Recherchez un acte pour demander un devis et réserver un créneau.
              </p>
            )}
          </section>

          <section className="mt-7">
            <h2 className="mb-3 font-syne text-lg font-bold text-[#123a63]">Accès rapides</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {QUICK_LINKS.map(({ label, href, icon: Icon }) => (
                <a
                  key={label}
                  href={href}
                  className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 text-sm font-bold text-[#123a63] shadow-sm transition hover:border-sky-300 hover:bg-sky-50"
                >
                  <Icon size={19} aria-hidden="true" />
                  {label}
                </a>
              ))}
              <a
                href="/sante/recherche/"
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 text-sm font-bold text-[#123a63] shadow-sm transition hover:border-sky-300 hover:bg-sky-50"
              >
                <MapPin size={19} aria-hidden="true" />
                Rechercher un soin
              </a>
            </div>
          </section>
        </>
      )}
    </section>
  );
}
