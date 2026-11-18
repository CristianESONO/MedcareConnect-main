import { useEffect, useState } from 'react';
import { Bell, BookOpen, FlaskConical, Mail, Search, Stethoscope } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  patientAccountApi,
  type PatientNotification,
} from '../lib/api';

type Scope = 'inbox' | 'rappels';

const recommendedPanels = [
  {
    title: 'Bilan de santé général',
    badge: 'Recommandé',
    description: 'NFS, glycémie à jeun, bilan lipidique, créatinine — bilan annuel de contrôle pour suivre vos constantes vitales.',
    acts: ['NFS / Hémogramme', 'Glycémie à jeun', 'Bilan lipidique', 'Créatininémie'],
    query: 'Bilan de santé',
    color: 'emerald',
  },
  {
    title: 'Bilan prénuptial & Préconception',
    badge: 'Avant mariage',
    description: 'Groupe ABO/Rhésus, VIH, hépatites B et C, électrophorèse de l’hémoglobine (drépanocytose) — recommandé avant mariage au Sénégal.',
    acts: ['Groupe ABO/Rhésus', 'Électrophorèse Hb', 'VIH Ag/Ac', 'HBsAg'],
    query: 'Bilan prénuptial',
    color: 'sky',
  },
  {
    title: 'Suivi grossesse & Obstétrique',
    badge: 'Par trimestre',
    description: 'Bilan prénatal T1, sérologies toxoplasmose & rubéole, échographies obstétricales T1/T2/T3 pour le suivi de croissance fœtale.',
    acts: ['Échographie T1', 'Toxoplasmose', 'Rubéole', 'Échographie T2'],
    query: 'Échographie obstétricale',
    color: 'amber',
  },
  {
    title: 'Bilans OMS recommandés',
    badge: 'Tous les 2 ans',
    description: 'Dépistage diabète & HTA (glycémie, HbA1c), bilan cardiovasculaire et dépistage IST recommandé par l’OMS.',
    acts: ['Glycémie à jeun', 'HbA1c', 'ECG 12 dérivations', 'Dépistage IST'],
    query: 'Glycémie',
    color: 'cyan',
  },
] as const;

const panelColorClasses = {
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  sky: 'border-sky-200 bg-sky-50 text-sky-900',
  amber: 'border-amber-200 bg-amber-50 text-amber-900',
  cyan: 'border-cyan-200 bg-cyan-50 text-cyan-900',
} as const;

function formatNotificationDate(value: string) {
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function NotificationList({
  scope,
  notifications,
  onMarkAllRead,
  markingRead,
}: {
  scope: Scope;
  notifications: PatientNotification[];
  onMarkAllRead: () => void;
  markingRead: boolean;
}) {
  const isReminders = scope === 'rappels';
  return (
    <section className="mt-6">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">
          {isReminders ? 'Rappels de proximité & consignes de préparation' : 'Activité de votre compte'}
        </h2>
        {notifications.some((notification) => !notification.is_read) && (
          <button
            type="button"
            disabled={markingRead}
            onClick={onMarkAllRead}
            className="text-sm font-semibold text-[#0a5c8a] hover:underline disabled:opacity-50"
          >
            {markingRead ? 'Mise à jour…' : 'Tout marquer comme lu'}
          </button>
        )}
      </div>
      {notifications.length ? (
        <div className="divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          {notifications.map((notification) => (
            <a
              key={notification.id}
              href={`/messaging/notifications/${notification.id}/lu/`}
              className={`flex items-start gap-3 p-4 transition hover:bg-sky-50 sm:p-5 ${notification.is_read ? '' : 'bg-sky-50/50'}`}
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-sky-100 text-[#0a5c8a]">
                {isReminders ? <Bell size={18} aria-hidden="true" /> : <Mail size={18} aria-hidden="true" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                  <span className="text-sm font-bold text-gray-900">{notification.title}</span>
                  <time className="text-xs text-gray-500">{formatNotificationDate(notification.created_at)}</time>
                </span>
                {notification.content && (
                  <span className="mt-1 block text-sm leading-relaxed text-gray-600">{notification.content}</span>
                )}
                {notification.link && (
                  <span className="mt-2 block text-xs font-bold uppercase tracking-wide text-[#123a63]">
                    {notification.bell_cta} →
                  </span>
                )}
              </span>
              {!notification.is_read && (
                <span className="mt-2 size-2 shrink-0 rounded-full bg-sky-600" aria-label="Non lu" />
              )}
            </a>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <Bell size={30} className="mx-auto text-gray-300" aria-hidden="true" />
          <h3 className="mt-3 font-semibold text-gray-700">
            {isReminders ? 'Aucun rappel pour le moment' : 'Aucune notification'}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            {isReminders
              ? 'Les rappels liés à vos rendez-vous apparaîtront ici.'
              : 'Vous serez alerté ici lors d’un nouveau devis, d’un message ou d’une activité sur votre compte.'}
          </p>
        </div>
      )}
    </section>
  );
}

function PatientAlertsPage({ scope }: { scope: Scope }) {
  const [notifications, setNotifications] = useState<PatientNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [markingRead, setMarkingRead] = useState(false);
  const isReminders = scope === 'rappels';

  useEffect(() => {
    const controller = new AbortController();
    patientAccountApi.notifications(scope, controller.signal)
      .then((data) => setNotifications(data.notifications))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger vos notifications.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [scope]);

  const markAllRead = async () => {
    setMarkingRead(true);
    setError('');
    try {
      await patientAccountApi.markAllNotificationsRead(scope);
      setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de mettre à jour les notifications.');
    } finally {
      setMarkingRead(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
          <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl">
            {isReminders ? <Bell size={24} aria-hidden="true" /> : <Mail size={24} aria-hidden="true" />}
            {isReminders ? 'Rappels & bilans recommandés' : 'Notifications'}
          </h1>
        </div>
        <nav className="flex flex-wrap gap-2" aria-label="Liens utiles">
          <Link to="/messaging/" className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#0a5c8a] hover:bg-sky-50">
            <Mail size={15} className="mr-2 inline" aria-hidden="true" /> Messages
          </Link>
          <Link to="/sante/recherche/" className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#0a5c8a] hover:bg-sky-50">
            <Search size={15} className="mr-2 inline" aria-hidden="true" /> Prestations
          </Link>
          <Link to={isReminders ? '/messaging/notifications/' : '/messaging/rappels/'} className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-[#0a5c8a] hover:bg-sky-50">
            {isReminders ? 'Notifications' : 'Mes rappels'}
          </Link>
        </nav>
      </header>

      {isReminders && (
        <div className="mt-6 rounded-2xl bg-gradient-to-r from-[#0a5c8a] to-cyan-600 p-5 text-white">
          <h2 className="flex items-center gap-2 font-bold">
            <Bell size={18} aria-hidden="true" /> Rappels & bilans recommandés
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-white/90">
            Suggestions présentées à titre informatif, basées sur les recommandations déjà affichées dans votre espace patient. Elles ne remplacent pas l’avis d’un professionnel de santé.
          </p>
        </div>
      )}

      {loading && <p className="mt-6 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement…</p>}
      {error && <p className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
      {!loading && !error && (
        <NotificationList
          scope={scope}
          notifications={notifications}
          onMarkAllRead={markAllRead}
          markingRead={markingRead}
        />
      )}

      {isReminders && (
        <>
          <section className="mt-8">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-gray-600">
              <FlaskConical size={17} aria-hidden="true" /> Bilans de santé recommandés
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {recommendedPanels.map((panel) => (
                <article key={panel.title} className={`rounded-2xl border p-5 ${panelColorClasses[panel.color]}`}>
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="flex items-center gap-2 font-bold">
                      <Stethoscope size={17} aria-hidden="true" /> {panel.title}
                    </h3>
                    <span className="shrink-0 rounded-full bg-white/70 px-2.5 py-1 text-[10px] font-semibold">{panel.badge}</span>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed opacity-80">{panel.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {panel.acts.map((act) => (
                      <span key={act} className="rounded-full bg-white/70 px-2.5 py-1 text-xs font-medium">{act}</span>
                    ))}
                  </div>
                  <Link
                    to={`/sante/recherche/?q=${encodeURIComponent(panel.query)}`}
                    className="mt-4 inline-flex rounded-lg bg-white px-3 py-2 text-sm font-bold text-[#0a5c8a] hover:bg-white/80"
                  >
                    <Search size={15} className="mr-2" aria-hidden="true" /> Rechercher ces actes
                  </Link>
                </article>
              ))}
            </div>
          </section>
          <aside className="mt-6 rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-5 text-center">
            <BookOpen size={24} className="mx-auto text-gray-400" aria-hidden="true" />
            <h2 className="mt-2 font-bold text-gray-800">Blog santé MedCare · À venir</h2>
            <p className="mx-auto mt-1 max-w-lg text-sm text-gray-500">
              Articles, guides et rappels personnalisés rédigés par nos médecins partenaires — directement dans votre espace patient.
            </p>
          </aside>
        </>
      )}
    </section>
  );
}

export function PatientNotificationsPage() {
  return <PatientAlertsPage scope="inbox" />;
}

export function PatientRemindersPage() {
  return <PatientAlertsPage scope="rappels" />;
}
