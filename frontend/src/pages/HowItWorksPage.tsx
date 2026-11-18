import { useState } from 'react';
import { Link } from 'react-router-dom';

type Profile = 'patient' | 'soignant';

type Step = {
  label: string;
  title: string;
  image: string;
  alt: string;
  points: string[];
  description: string;
};

const PATIENT_STEPS: Step[] = [
  {
    label: 'Recherche',
    title: "Cherchez votre acte sur l'accueil",
    image: "Cherchez votre acte sur l'accueil.png",
    alt: "Recherche d'un acte sur l'accueil MedCare",
    points: ['Recherche par nom ou par pilier', 'Tri par prix, couverture ou distance', '450+ actes · 16 structures · 0% commission'],
    description:
      "Depuis l'écran d'accueil, recherchez un examen par son nom ou explorez les 6 piliers paracliniques. Tout est gratuit et sans compte : 450+ actes, 16 structures partenaires, zéro commission.",
  },
  {
    label: 'Sélection',
    title: 'Sélectionnez vos actes',
    image: 'Sélectionnez vos actes.png',
    alt: "Sélection d'actes dans un pilier",
    points: ["Sélection multiple d'actes", 'Nombre de structures par acte affiché', 'Recherche et filtre dans la liste'],
    description:
      'Dans un pilier (ici Biologie médicale), cochez tous les actes dont vous avez besoin. Le compteur « sélectionnés » se met à jour, et chaque acte indique le nombre de structures qui le proposent.',
  },
  {
    label: 'Comparaison',
    title: 'Comparez les structures par couverture',
    image: 'Comparez les structures par couverture.png',
    alt: 'Comparaison des structures par couverture d’actes',
    points: ['Tri par couverture (4/4 actes)', 'Détail prix, assurances & badge Pionnier', 'Ajout groupé au panier en un geste'],
    description:
      'MedCare trie les structures selon leur couverture de votre sélection. Le Laboratoire BioSanté Mermoz couvre 4/4 actes : vous voyez le détail des prix, les assurances et le total — puis vous ajoutez tout au panier.',
  },
  {
    label: 'Panier',
    title: 'Validez votre panier',
    image: 'Validez votre panier.png',
    alt: 'Validation du panier patient',
    points: ['Panier groupé par structure', 'Pris en charge / reste à payer calculés', 'Réservation en un clic'],
    description:
      'Le panier regroupe vos actes par structure, avec le total et la part prise en charge par vos assurances. Un bouton « Réserver mes actes » lance la demande de devis.',
  },
  {
    label: 'Devis',
    title: 'Recevez un devis détaillé',
    image: 'recevez un devis détaillé.png',
    alt: 'Devis détaillé dans la conversation',
    points: ['Devis automatique avec référence unique', 'Structure, horaires, assurances & détail des actes', 'Bouton « Prendre RDV » directement dans le chat'],
    description:
      "La conversation s'ouvre avec le secrétariat de la structure. MedCare y génère automatiquement un devis chiffré et référencé, reprenant structure, horaires, assurances et le détail des actes — tarifs indicatifs, zéro commission.",
  },
  {
    label: 'Créneau',
    title: 'Choisissez votre créneau',
    image: 'Choisissez votre créneau.png',
    alt: "Choix d'un créneau de rendez-vous",
    points: ['Disponibilités réelles de la structure', 'Sélection directe dans le chat', 'Créneaux occupés grisés automatiquement'],
    description:
      'Toujours dans la conversation, la structure propose ses disponibilités réelles. Vous touchez le créneau qui vous convient — les horaires déjà pris sont grisés.',
  },
  {
    label: 'Confirmation',
    title: 'Votre RDV est confirmé',
    image: 'Votre RDV est confirmé.png',
    alt: 'Confirmation du rendez-vous',
    points: ['Transmission instantanée + WhatsApp', 'Accusé puis confirmation dans le chat', 'Référence de dossier à présenter à l’accueil'],
    description:
      "Votre demande est transmise à la structure et par WhatsApp. Vous recevez d'abord un accusé « en attente », puis la confirmation avec une référence de dossier à présenter à l'accueil.",
  },
  {
    label: 'Suivi',
    title: 'Suivez tout depuis votre tableau de bord',
    image: 'Suivez tout depuis votre tableau de bord.png',
    alt: 'Tableau de bord patient MedCare',
    points: ['KPIs : RDV, devis, assurances, panier', 'Prochain RDV confirmé avec détail complet', 'Historique et rappels centralisés'],
    description:
      "Votre espace personnel récapitule l'essentiel : RDV à venir, devis en attente, assurances et actes au panier. Le prochain rendez-vous confirmé s'affiche avec son détail complet et sa référence de paiement.",
  },
];

const PROVIDER_STEPS: Step[] = [
  {
    label: 'Inscription',
    title: 'Créez votre compte structure',
    image: 'Créez votre compte structure.png',
    alt: 'Création du compte structure prestataire',
    points: ['Formulaire unique pour tous les profils', 'Type de compte Prestataire / Patient', 'Compte protégé par chiffrement'],
    description:
      "Inscrivez-vous en quelques minutes : informations de l'établissement, contact et identifiants. Sélectionnez le type de compte « Prestataire » pour accéder à l'espace structure.",
  },
  {
    label: 'Catalogue',
    title: 'Déclarez votre type, pilier et catalogue',
    image: 'Déclarez votre type, pilier et catalogue.png',
    alt: "Déclaration du catalogue d'actes",
    points: ['8 types de structure · pilier auto-activé', 'Tarif, délai & activation par acte', 'Option prélèvement à domicile'],
    description:
      "Choisissez votre type de structure (laboratoire, imagerie, clinique…) : le pilier d'activité s'active automatiquement. Renseignez ensuite chaque acte avec son tarif, son délai de résultat et son statut actif. Activez le prélèvement à domicile si besoin.",
  },
  {
    label: 'Profil public',
    title: 'Obtenez votre fiche publique',
    image: 'Obtenez votre fiche publique.png',
    alt: 'Fiche publique de la structure',
    points: ['Fiche complète : identité, horaires, assurances', 'Actes avec tarifs selon couverture (Comptant, IPM, Assurance) & délais', 'Bouton Devis WhatsApp & itinéraire'],
    description:
      'Votre établissement dispose d’une fiche publique complète, visible par les patients : identité, horaires, assurances acceptées, prélèvement à domicile et catalogue d’actes avec tarifs selon la couverture (Comptant, IPM, Assurance) et délais. Le badge Partenaire Pionnier est affiché.',
  },
  {
    label: 'Devis',
    title: 'Recevez et traitez les devis',
    image: 'Recevez et traitez les devis.png',
    alt: 'Traitement des devis WhatsApp reçus',
    points: ['Devis automatiques avec actes & montant', 'Confirmer le RDV, refuser ou relancer', 'Suivi par statut + valeur totale active'],
    description:
      'Les demandes de devis générées par les patients arrivent automatiquement, avec actes, créneau souhaité, assurance et montant. Vous confirmez le RDV, refusez ou relancez — le tout suivi par statut (nouveaux, acceptés, expirés).',
  },
  {
    label: 'Réservations',
    title: 'Validez vos réservations',
    image: 'Validez vos réservations.png',
    alt: 'Validation des réservations prestataire',
    points: ['Tableau complet : patient, actes, assurance, créneau', 'Statuts : en attente, confirmé, honoré, no-show', 'Vue liste ou calendrier'],
    description:
      'Toutes les réservations entrantes sont centralisées dans un tableau clair : référence, patient, actes, assurance, créneau, montant et statut. Confirmez, marquez honoré ou no-show, en vue liste ou calendrier.',
  },
  {
    label: 'Paramètres',
    title: 'Pilotez votre compte et votre équipe',
    image: 'Pilotez votre compte et votre équipe.png',
    alt: "Paramètres du compte et gestion de l'équipe",
    points: ["Rôles & invitations d'utilisateurs", 'Notifications fines (devis, RDV, no-show)', 'Préférences : langue, devise, affichage tarifs'],
    description:
      "Gérez votre compte administrateur, invitez des utilisateurs avec des rôles (administrateur, secrétaire, lecture seule), réglez vos notifications et vos préférences — langue, devise, période du dashboard et affichage des tarifs sur le profil public.",
  },
];

const FAQ_ITEMS = [
  {
    question: 'Faut-il un compte pour chercher un acte ?',
    answer: "Non. La recherche, le tri et la comparaison sont libres et gratuits. Un compte n'est requis qu'au moment de générer un devis et de réserver un créneau.",
  },
  {
    question: 'MedCare prend-il une commission sur les actes ?',
    answer: 'Jamais. Le tarif affiché est le tarif net déclaré par la structure. MedCare se rémunère uniquement via l’abonnement SaaS des structures.',
  },
  {
    question: 'Où se passe la prise de rendez-vous ?',
    answer: 'Directement dans la conversation avec le secrétariat de la structure : devis, choix du créneau et confirmation se font dans le même fil, avec une référence de dossier unique.',
  },
  {
    question: 'Les prix affichés sont-ils garantis ?',
    answer: "Ce sont des tarifs indicatifs déclarés et datés par les établissements. Le devis reprend le montant au moment de la demande ; confirmez toujours à l'accueil.",
  },
  {
    question: 'Comment retrouver mes rendez-vous ?',
    answer: 'Votre tableau de bord récapitule RDV à venir, devis en attente, assurances et actes au panier, avec le détail complet de chaque réservation.',
  },
  {
    question: 'Mes assurances sont-elles prises en compte ?',
    answer: 'Oui. Les assurances acceptées par chaque structure sont affichées, et le panier estime la part prise en charge ainsi que le reste à payer.',
  },
];

function StepFlow({ profile, steps }: { profile: Profile; steps: Step[] }) {
  const isPatient = profile === 'patient';

  return (
    <div className={`mc-how-flow mc-how-flow--${isPatient ? 'patient' : 'struct'} active`}>
      <div className="mc-how-flow-intro">
        <div className="mc-container">
          <span className={`mc-how-flow-tag mc-how-flow-tag--${isPatient ? 'patient' : 'struct'}`}>
            {isPatient ? 'Côté patient · sur mobile' : 'Côté structure · sur ordinateur'}
          </span>
          <h2>
            {isPatient ? 'Du symptôme au rendez-vous, en ' : "De l'inscription aux réservations, en "}
            <em>{isPatient ? '8 étapes' : '6 étapes'}</em>
          </h2>
        </div>
      </div>

      <div className="mc-how-steps">
        {steps.map((step, index) => {
          const imageLeft = index % 2 === 0;
          const image = (
            <div className="mc-how-step-visual">
              <div className="mc-how-shot">
                <img src={`/static/images/${step.image}`} alt={step.alt} loading="lazy" />
              </div>
            </div>
          );
          const text = (
            <div className="mc-how-step-text">
              <ul className="mc-how-feats">
                {step.points.map((point) => (
                  <li key={point}>
                    <span className="mc-how-feat-check" aria-hidden="true"><i className="ti ti-check" /></span>
                    {point}
                  </li>
                ))}
              </ul>
              <p>{step.description}</p>
            </div>
          );

          return (
            <article className="mc-how-step mc-step-visible" key={step.title}>
              <div className="mc-container">
                <header className="mc-how-step-banner">
                  <span className="mc-how-step-num">{String(index + 1).padStart(2, '0')}</span>
                  <div className="mc-how-step-heading">
                    <span className="mc-how-step-label">{step.label}</span>
                    <h3>{step.title}</h3>
                  </div>
                </header>
                <div className={`mc-how-step-grid mc-how-step-grid--img-${imageLeft ? 'left' : 'right'}`}>
                  {imageLeft ? <>{image}{text}</> : <>{text}{image}</>}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

export function HowItWorksPage() {
  const [profile, setProfile] = useState<Profile>('patient');
  const [openFaqs, setOpenFaqs] = useState<number[]>([]);

  const toggleFaq = (index: number) => {
    setOpenFaqs((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index]
    );
  };

  return (
    <div className="mc-page-wrap mc-how-page">
      <header className="mc-page-hero mc-how-hero">
        <div className="mc-container">
          <div className="mc-how-kicker"><span className="mc-how-kicker-dot" aria-hidden="true" />Comment ça marche</div>
          <h1>Trouvez, comparez,<br /><em>réservez</em> vos examens</h1>
          <p>De la recherche d'un acte à la confirmation du rendez-vous — un parcours complet, sans intermédiaire et sans commission sur les actes médicaux.</p>
          <div className="mc-how-hero-stats" aria-label="Chiffres clés">
            {[
              ['450+', 'Actes'],
              ['16', 'Structures'],
              ['6', 'Piliers'],
              ['0%', 'Commission'],
            ].map(([value, label], index) => (
              <div className="mc-how-hero-stat" key={label}>
                <div className={`mc-how-hero-stat-val${index === 3 ? ' mc-how-hero-stat-val--accent' : ''}`}>{value}</div>
                <div className="mc-how-hero-stat-label">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </header>

      <section className="mc-how-switch" aria-label="Choisir votre profil">
        <div className="mc-container">
          <div className="mc-toggle-wrap" role="group" aria-label="Profil">
            <button
              type="button"
              className={`mc-toggle-btn${profile === 'patient' ? ' active' : ''}`}
              aria-pressed={profile === 'patient'}
              onClick={() => setProfile('patient')}
            >
              <span className="mc-toggle-emoji" aria-hidden="true"><i className="ti ti-search" /></span> Je suis patient
            </button>
            <button
              type="button"
              className={`mc-toggle-btn mc-toggle-btn--struct${profile === 'soignant' ? ' active' : ''}`}
              aria-pressed={profile === 'soignant'}
              onClick={() => setProfile('soignant')}
            >
              <span className="mc-toggle-emoji" aria-hidden="true"><i className="ti ti-building-hospital" /></span> Je suis une structure
            </button>
          </div>
        </div>
      </section>

      {profile === 'patient'
        ? <StepFlow profile="patient" steps={PATIENT_STEPS} />
        : <StepFlow profile="soignant" steps={PROVIDER_STEPS} />}

      <section className="mc-how-band" aria-labelledby="mc-how-band-title">
        <div className="mc-container mc-how-band-inner">
          <h2 id="mc-how-band-title">Zéro commission. Par principe.</h2>
          <p>MedCare est un annuaire paraclinique digital : un modèle d'abonnement SaaS, jamais de prélèvement sur les actes médicaux. Le prix que vous voyez est le tarif net déclaré par la structure.</p>
          <p className="mc-how-band-badge"><span aria-hidden="true"><i className="ti ti-check" /></span> Conforme Art. 11 · Décret N°67-147</p>
        </div>
      </section>

      <section className="mc-section mc-faq">
        <div className="mc-container">
          <div className="mc-section-tag">FAQ</div>
          <h2>Questions <em>fréquentes</em></h2>
          <div className="mc-faq-grid">
            {FAQ_ITEMS.map((item, index) => {
              const isOpen = openFaqs.includes(index);
              return (
                <div className={`mc-faq-item${isOpen ? ' active' : ''}`} key={item.question}>
                  <button
                    type="button"
                    className="mc-faq-question"
                    aria-expanded={isOpen}
                    onClick={() => toggleFaq(index)}
                  >
                    {item.question}<i className="ti ti-chevron-down" aria-hidden="true" />
                  </button>
                  {isOpen && <div className="mc-faq-answer">{item.answer}</div>}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mc-how-cta" aria-labelledby="mc-how-cta-title">
        <div className="mc-container mc-how-cta-inner">
          <h2 id="mc-how-cta-title">Prêt à commencer ?</h2>
          <p>Patients : trouvez et réservez vos examens en quelques minutes. Structures : rejoignez le premier annuaire paraclinique digital du Sénégal.</p>
          <div className="mc-how-cta-actions">
            <Link to="/sante/recherche/" className="mc-btn-primary">Trouver un service →</Link>
            <Link to="/inscription/" className="mc-how-btn-ghost">Rejoindre MedCare</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
