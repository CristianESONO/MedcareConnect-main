import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { MapPin, MessageCircle, Phone, ShieldCheck } from 'lucide-react';
import { FavoriteButton } from '../components/FavoriteButton';
import './publicProfilePage.css';
import {
  cartApi,
  discoveryApi,
  type OrganizationPublicProfile,
  type PractitionerPublicProfile,
} from '../lib/api';

function amount(value: string | null) {
  if (!value) return '';
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString('fr-FR') : value;
}

function usePublicData<T>(load: (slug: string, signal?: AbortSignal) => Promise<T>) {
  const { slug = '' } = useParams();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setLoading(true);
    setError('');
    load(slug, controller.signal)
      .then(setData)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger cette fiche.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [load, slug]);

  return { data, loading, error };
}

function PageStatus({ loading, error }: { loading: boolean; error: string }) {
  if (loading) return <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement de la fiche…</p>;
  if (error) return <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>;
  return null;
}

function AddActButton({
  id,
  onCartChange,
}: {
  id: number;
  onCartChange: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const add = async () => {
    setBusy(true);
    setError('');
    try {
      await cartApi.add(id);
      await onCartChange();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’ajouter cet acte au panier.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="inline-flex flex-col items-end">
      <button type="button" onClick={() => void add()} disabled={busy} className="rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white disabled:opacity-50">
        {busy ? 'Ajout…' : 'Ajouter au panier'}
      </button>
      {error && <span className="mt-1 text-[10px] text-red-700" role="alert">{error}</span>}
    </span>
  );
}

export function OrganizationProfilePage({ onCartChange }: { onCartChange: () => Promise<void> }) {
  const { data, loading, error } = usePublicData(discoveryApi.organization);
  const profile = data as OrganizationPublicProfile | null;
  const [hoursOpen, setHoursOpen] = useState(false);
  const [insurancesOpen, setInsurancesOpen] = useState(false);
  const [actQuery, setActQuery] = useState('');
  const todayHours = profile?.hours.find((row) => row.today);
  const filteredActs = (profile?.acts || []).filter((act) =>
    `${act.name} ${act.category}`.toLocaleLowerCase().includes(actQuery.trim().toLocaleLowerCase())
  );
  const actGroups = new Map<string, OrganizationPublicProfile['acts']>();
  for (const act of filteredActs) {
    const category = act.category || 'Autres prestations';
    const group = actGroups.get(category) || [];
    group.push(act);
    actGroups.set(category, group);
  }

  return (
    <section className="org-fiche-page-bg">
      <PageStatus loading={loading} error={error} />
      {profile && (
        <div className="org-fiche-card">
          <header className="profil-drawer-header">
            <div className="profil-drawer-close-row">
              <Link to="/sante/recherche/" className="profil-drawer-back-btn">← Retour</Link>
              <FavoriteButton
                slug={profile.slug}
                initialFavorite={profile.is_favorite}
                className="profil-drawer-fav-btn"
              />
            </div>

            <div className="profil-drawer-head-body">
              <div className="profil-drawer-identity">
                <div className="profil-drawer-avatar">
                  {profile.logo
                    ? <img src={profile.logo} alt={profile.name} />
                    : <i className="ti ti-building-hospital" aria-hidden="true" />}
                </div>
                <div className="profil-drawer-titles">
                  <div className="profil-drawer-name-row">
                    <h1 className="profil-drawer-name">{profile.name}</h1>
                    {profile.pioneer ? (
                      <span className="profil-drawer-pioneer"><i className="ti ti-star" aria-hidden="true" /> Pionnier</span>
                    ) : profile.verified ? (
                      <span className="profil-drawer-verified"><i className="ti ti-check" aria-hidden="true" /> Vérifié</span>
                    ) : null}
                  </div>
                  <div className="profil-drawer-type-row">
                    <span className="profil-drawer-sub">{profile.type || 'Établissement de santé'}</span>
                    {todayHours && (
                      <span className={`profil-drawer-open-badge ${todayHours.closed ? 'profil-drawer-open-badge--closed' : 'profil-drawer-open-badge--open'}`}>
                        <span className="profil-drawer-open-dot" />
                        {todayHours.closed ? 'Fermé' : 'Ouvert'}
                      </span>
                    )}
                  </div>
                  <p className="profil-drawer-address-row">
                    <MapPin size={13} aria-hidden="true" />
                    {[profile.quartier, profile.city].filter(Boolean).join(', ')}
                    {profile.address ? ` — ${profile.address}` : ''}
                  </p>
                  {profile.hours_summary && <p className="profil-drawer-hours-inline">{profile.hours_summary}</p>}
                </div>
              </div>

              <div className="profil-drawer-actions">
                {profile.phone && (
                  <a href={`tel:${profile.phone}`} className="profil-drawer-action-btn">
                    <Phone size={15} aria-hidden="true" /> Appeler
                  </a>
                )}
                {profile.whatsapp_url && (
                  <a href={profile.whatsapp_url} target="_blank" rel="noreferrer" className="profil-drawer-action-btn">
                    <MessageCircle size={15} aria-hidden="true" /> WhatsApp
                  </a>
                )}
                {profile.maps_url && (
                  <a href={profile.maps_url} target="_blank" rel="noreferrer" className="profil-drawer-action-btn">
                    <MapPin size={15} aria-hidden="true" /> Itinéraire
                  </a>
                )}
                <button
                  type="button"
                  className="profil-drawer-action-btn"
                  aria-expanded={hoursOpen}
                  aria-controls="public-profile-hours"
                  onClick={() => setHoursOpen((open) => !open)}
                >
                  <i className="ti ti-clock" aria-hidden="true" /> Horaires
                </button>
              </div>

              {hoursOpen && (
                <div id="public-profile-hours" className="profil-drawer-horaires-pop">
                  <div className="profil-drawer-horaires-title">Horaires d’ouverture</div>
                  {profile.hours.length ? profile.hours.map((row) => (
                    <div className={`profil-drawer-horaires-line${row.today ? ' profil-drawer-horaires-line--today' : ''}`} key={row.day}>
                      <span>{row.day}{row.today ? ' · Aujourd’hui' : ''}</span>
                      <span>{row.closed ? 'Fermé' : row.display}</span>
                    </div>
                  )) : <p className="profil-drawer-horaires-line">{profile.hours_summary || 'Horaires non renseignés'}</p>}
                  {todayHours && <p className={`profil-drawer-horaires-status${todayHours.closed ? ' profil-drawer-horaires-status--closed' : ' profil-drawer-horaires-status--open'}`}>
                    {todayHours.closed ? '● Fermé aujourd’hui' : '● Ouvert aujourd’hui'}
                  </p>}
                </div>
              )}
            </div>
          </header>

          <div className="profil-drawer-body">
            {profile.description && <p className="profil-drawer-desc">{profile.description}</p>}
            {!!profile.practical_chips.length && (
              <div className="profil-drawer-practical">
                {profile.practical_chips.map((chip) => (
                  <span className="profil-drawer-practical-chip" key={`${chip.icon}-${chip.label}`}>
                    <i className={`ti ti-${chip.icon}`} aria-hidden="true" /> {chip.label}
                  </span>
                ))}
              </div>
            )}

            {profile.insurance_match && (
              <div className="profil-drawer-ins-match" role="status">
                <ShieldCheck size={17} aria-hidden="true" />
                <span>Votre assurance est acceptée ici (<strong>{profile.insurance_match}</strong>).</span>
              </div>
            )}
            <button
              type="button"
              className="profil-drawer-assur-toggle"
              aria-expanded={insurancesOpen}
              aria-controls="public-profile-insurances"
              onClick={() => setInsurancesOpen((open) => !open)}
            >
              <span><ShieldCheck size={16} aria-hidden="true" /> Assurances acceptées ({profile.insurances.length})</span>
              <span aria-hidden="true">{insurancesOpen ? '▲' : '▼'}</span>
            </button>
            {insurancesOpen && (
              <div id="public-profile-insurances" className="profil-drawer-assur-list">
                {profile.insurances.length ? profile.insurances.map((insurance) => (
                  <div
                    className={`profil-drawer-assur-row${insurance.patient_match ? ' profil-drawer-assur-row--match' : ''}`}
                    key={`${insurance.name}-${insurance.segment}`}
                  >
                    <span>{insurance.patient_match && <i className="ti ti-check" aria-hidden="true" />} {insurance.name}</span>
                    {insurance.patient_match && <span className="profil-drawer-assur-tag">Acceptée pour vous</span>}
                  </div>
                )) : <p className="profil-drawer-empty">Aucune assurance déclarée.</p>}
              </div>
            )}

            <h2 className="profil-drawer-actes-label">
              Actes disponibles ({profile.acte_count})
            </h2>
            <label className="profil-drawer-actes-search">
              <input
                type="search"
                value={actQuery}
                onChange={(event) => setActQuery(event.target.value)}
                placeholder="Rechercher un acte…"
                aria-label="Rechercher un acte"
              />
              <i className="ti ti-search" aria-hidden="true" />
            </label>

            <div className="profil-drawer-actes-list">
              {Array.from(actGroups.entries()).map(([category, acts]) => (
                <details className="profil-drawer-cat" key={category} open>
                  <summary className="profil-drawer-cat-head">
                    <span>{category}</span>
                    <span className="profil-drawer-cat-head-right">
                      <span className="profil-drawer-cat-count">{acts.length}</span>
                      <span className="profil-drawer-cat-arrow" aria-hidden="true">▼</span>
                    </span>
                  </summary>
                  <div className="profil-drawer-cat-body">
                    {acts.map((act) => (
                      <article className="profil-pa-row" key={act.id}>
                        <div className="profil-pa-info">
                          <h3 className="profil-pa-nom">{act.name}</h3>
                          {act.notes && <p className="profil-pa-note">{act.notes}</p>}
                          {act.delay && <p className="profil-pa-delai"><i className="ti ti-clock" aria-hidden="true" /> {act.delay}</p>}
                        </div>
                        <div className="profil-pa-right">
                          {profile.show_prices && act.price && <strong className="profil-pa-prix">{amount(act.price)} FCFA</strong>}
                          <AddActButton id={act.id} onCartChange={onCartChange} />
                        </div>
                      </article>
                    ))}
                  </div>
                </details>
              ))}
              {!filteredActs.length && (
                <p className="profil-drawer-empty">
                  {profile.acts.length ? 'Aucun acte ne correspond à votre recherche.' : 'Aucun acte publié pour cette structure.'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export function PractitionerProfilePage({ onCartChange }: { onCartChange: () => Promise<void> }) {
  const { data, loading, error } = usePublicData(discoveryApi.practitioner);
  const profile = data as PractitionerPublicProfile | null;

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <p className="mb-4 text-sm"><Link to="/sante/annuaire/" className="font-semibold text-[#0a5c8a] hover:underline">← Retour à l’annuaire</Link></p>
      <PageStatus loading={loading} error={error} />
      {profile && (
        <>
          <header className="rounded-2xl bg-gradient-to-br from-[#0a4a72] to-[#054a38] p-5 text-white sm:p-7">
            <div className="flex items-center gap-4">
              {profile.logo && <img src={profile.logo} alt="" className="size-20 rounded-2xl border border-white/20 object-cover" />}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-sky-100">{profile.profession || profile.specialty || 'Praticien'}</p>
                <h1 className="mt-1 font-syne text-2xl font-extrabold sm:text-3xl">{profile.name}</h1>
                <p className="mt-2 flex items-center gap-1 text-sm text-white/85"><MapPin size={15} /> {[profile.quartier, profile.city].filter(Boolean).join(', ')}</p>
              </div>
            </div>
            {profile.description && <p className="mt-4 max-w-3xl whitespace-pre-line text-sm leading-6 text-white/90">{profile.description}</p>}
            {profile.phone && <a href={`tel:${profile.phone}`} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs font-bold text-[#123a63]"><Phone size={14} /> Appeler</a>}
          </header>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <section className="rounded-2xl border border-gray-200 bg-white p-5">
              <h2 className="font-syne text-lg font-bold text-[#123a63]">Prestations</h2>
              <div className="mt-3 divide-y divide-gray-100">
                {profile.acts.map((act) => <div key={act.id} className="flex items-center justify-between gap-3 py-3"><div><p className="text-sm font-semibold text-gray-900">{act.name}</p><p className="mt-1 text-xs text-gray-500">{act.category}{act.delay ? ` · ${act.delay}` : ''}</p></div><div className="flex items-center gap-3"><strong className="text-sm text-[#123a63]">{amount(act.price)} FCFA</strong><AddActButton id={act.id} onCartChange={onCartChange} /></div></div>)}
                {!profile.acts.length && <p className="py-3 text-sm text-gray-500">Aucune prestation publiée.</p>}
              </div>
            </section>
            <div className="space-y-5">
              {profile.affiliations.length > 0 && <section className="rounded-2xl border border-gray-200 bg-white p-5"><h2 className="font-syne text-lg font-bold text-[#123a63]">Affiliations</h2><div className="mt-3 space-y-3">{profile.affiliations.map((item) => <Link key={`${item.structure}-${item.role}`} to={item.profile_url} className="block rounded-xl bg-gray-50 p-3 hover:bg-sky-50"><p className="text-sm font-semibold text-gray-900">{item.structure}</p><p className="mt-1 text-xs text-gray-500">{[item.role, item.city, item.days.join(', ')].filter(Boolean).join(' · ')}</p></Link>)}</div></section>}
              {profile.tickets.length > 0 && <section className="rounded-2xl border border-gray-200 bg-white p-5"><h2 className="font-syne text-lg font-bold text-[#123a63]">Prestations sur rendez-vous</h2><div className="mt-3 space-y-3">{profile.tickets.map((ticket) => <article key={ticket.url} className="rounded-xl border border-gray-100 p-3"><h3 className="font-semibold text-gray-900">{ticket.title}</h3>{ticket.description && <p className="mt-1 text-xs text-gray-600">{ticket.description}</p>}<p className="mt-2 text-xs text-gray-500">{ticket.mode} · {ticket.zone} · {ticket.availability}</p><strong className="mt-2 block text-sm text-[#123a63]">{amount(ticket.price)} FCFA</strong><a href={ticket.url} className="mt-2 inline-flex rounded-lg bg-[#0a5c8a] px-3 py-2 text-xs font-bold text-white">Voir le ticket</a></article>)}</div></section>}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
