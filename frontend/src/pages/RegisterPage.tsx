import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getCsrfToken } from '../lib/auth';
import './visitorRegister.css';

type Mode = 'patient' | 'structure' | 'praticien';
type Topologie = 'simple' | 'multiservice' | 'multisite';
type Profession = 'medecin' | 'infirmier' | 'kine' | 'sagefemme' | 'psy' | 'autre';

const PROFESSIONS: { id: Profession; label: string; sub: string; icon: string }[] = [
  { id: 'medecin', label: 'Médecin', sub: "Inscription à l'Ordre", icon: 'ti-stethoscope' },
  { id: 'infirmier', label: 'Infirmier(ère)', sub: 'Soins et gestes', icon: 'ti-needle' },
  { id: 'kine', label: 'Kinésithérapeute', sub: 'Rééducation', icon: 'ti-stretching' },
  { id: 'sagefemme', label: 'Sage-femme', sub: 'Santé de la femme', icon: 'ti-woman' },
  { id: 'psy', label: 'Psychologue', sub: 'Santé mentale', icon: 'ti-brain' },
  { id: 'autre', label: 'Autre paramédical', sub: 'Diététique, etc.', icon: 'ti-bandage' },
];

const SPECIALITES_MEDECIN = [
  'Médecine générale',
  'Cardiologie',
  'Pédiatrie',
  'Gynécologie · Obstétrique',
  'Dermatologie',
  'Ophtalmologie',
  'ORL',
  'Gastro-entérologie',
  'Pneumologie',
  'Chirurgie générale',
  'Neurologie',
  'Rhumatologie',
];

function slugify(str: string): string {
  return (str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function RegisterMarketing({ mode, onModeChange }: { mode: Mode; onModeChange: (mode: Mode) => void }) {
  const patientMode = mode === 'patient';
  return (
    <>
      <header className="hdr hdr--toggle-only mc-register-marketing-toggle">
        <div className="hdr__in">
          <div className="toggle" role="tablist" aria-label="Choisir votre profil">
            <span className="toggle__pill" style={{ transform: patientMode ? 'translateX(0)' : 'translateX(calc(100% + 6px))' }} />
            <button type="button" className="toggle__btn" role="tab" aria-selected={patientMode} onClick={() => onModeChange('patient')}>
              <span className="dot"><i className="ti ti-search" /></span> Patient
            </button>
            <button type="button" className="toggle__btn" role="tab" aria-selected={!patientMode} onClick={() => onModeChange('structure')}>
              <span className="dot"><i className="ti ti-building-hospital" /></span> Soignant
            </button>
          </div>
        </div>
      </header>

      <section className={`stage stage--patient${patientMode ? ' is-active' : ''}`}>
        <div className="hero">
          <div className="hero__in">
            <div>
              <span className="eyebrow">Sénégal · Pour les patients</span>
              <h1 className="h1">Votre santé,<br /><em>au bout des doigts.</em></h1>
              <p className="lead">Trouvez, comparez et réservez vos examens paracliniques au Sénégal. Prix réels, assurances acceptées et localisation exacte, avant même de vous déplacer.</p>
              <div className="cta-row">
                <a className="btn btn--primary" href="#inscription-form">Créer mon compte →</a>
                <a className="btn btn--ghost" href="#patient-flow"><i className="ti ti-help-circle" /> Voir comment ça marche</a>
              </div>
            </div>
            <div className="mock">
              <div className="mc-marketing-mock">
                <div className="appcard__search"><i className="ti ti-search" /> NFS, Scanner cérébral, Échographie…</div>
                <div className="appcard__chips"><span className="chip"><i className="ti ti-flask" /> Biologie</span><span className="chip"><i className="ti ti-scan" /> Imagerie</span><span className="chip chip--on"><i className="ti ti-map-pin" /> Proche</span></div>
                <div className="res">
                  <div className="res__head"><div className="res__nm">Labo Analyses Liberté VI</div><div className="res__ty">Laboratoire d'analyses médicales</div><div className="res__loc"><i className="ti ti-map-pin" /> Dakar, Liberté VI</div></div>
                  <div className="acte"><span className="acte__check"><i className="ti ti-check" /></span><div className="acte__body"><div className="acte__name">Réticulocytes</div><div className="acte__delai"><i className="ti ti-clock" /> Délai résultats : dans la journée (≤ 4h)</div></div><div className="acte__price">5 500 F</div></div>
                  <div className="res__foot"><span className="res__ins"><i className="ti ti-check" /> CMU · CNAM · FNR +3</span><a href="/sante/recherche/" className="res__btn">Obtenir mon devis</a></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="sec" id="patient-flow">
          <div className="sec__eyebrow">Du symptôme au rendez-vous</div>
          <h2 className="sec__title">En <em>4 gestes simples</em></h2>
          <p className="sec__sub">Sur mobile, en quelques minutes, sans intermédiaire.</p>
          <div className="flow">
            <div className="flow__item"><div className="flow__ico"><i className="ti ti-search" /></div><h4>Cherchez</h4><p>Un acte par son nom ou par pilier.</p></div>
            <div className="flow__item"><div className="flow__ico"><i className="ti ti-scale" /></div><h4>Comparez</h4><p>Prix, assurances et distance.</p></div>
            <div className="flow__item"><div className="flow__ico"><i className="ti ti-message" /></div><h4>Recevez un devis</h4><p>Chiffré, référencé, dans le chat.</p></div>
            <div className="flow__item"><div className="flow__ico"><i className="ti ti-calendar" /></div><h4>Réservez</h4><p>Créneau confirmé, référence à l'accueil.</p></div>
          </div>
        </div>
        <div className="sec">
          <div className="sec__eyebrow">Pourquoi passer par MedCare</div>
          <h2 className="sec__title">Tout savoir <em>avant</em> de vous déplacer</h2>
          <p className="sec__sub">Toutes les structures paracliniques du Sénégal réunies. Gratuit, sans compte pour chercher, sans commission sur les actes.</p>
          <div className="grid-3">
            <article className="card"><div className="card__ico"><i className="ti ti-coin" /></div><h3>Les prix, avant de venir</h3><p>Chaque acte affiche son tarif déclaré et daté par la structure. Fini les mauvaises surprises à l'accueil.</p></article>
            <article className="card"><div className="card__ico"><i className="ti ti-shield-check" /></div><h3>Vos assurances vérifiées</h3><p>CMU, IPM, CNAM, assureurs privés. Vous voyez ce qui est accepté et la part prise en charge estimée.</p></article>
            <article className="card"><div className="card__ico"><i className="ti ti-map-pin" /></div><h3>La structure la plus proche</h3><p>Localisation exacte, horaires et itinéraire. Comparez par prix, couverture ou distance.</p></article>
            <article className="card"><div className="card__ico"><i className="ti ti-clipboard-list" /></div><h3>Plusieurs actes, un panier</h3><p>Regroupez vos examens et voyez d'un coup quelle structure couvre votre ordonnance complète.</p></article>
            <article className="card"><div className="card__ico"><i className="ti ti-message" /></div><h3>Devis et RDV en un fil</h3><p>Un devis chiffré et référencé, puis le choix du créneau, directement dans la conversation.</p></article>
            <article className="card"><div className="card__ico"><i className="ti ti-device-mobile" /></div><h3>Tout suivi au même endroit</h3><p>RDV à venir, devis en attente, assurances et références de dossier dans votre tableau de bord.</p></article>
          </div>
        </div>
        <div className="finalcta"><div className="finalcta__in"><h3>100% gratuit pour les patients</h3><p>La recherche, la comparaison et le devis ne vous coûtent rien. MedCare ne prend aucune commission sur les actes médicaux.</p><div className="cta-row"><a className="btn btn--primary" href="#inscription-form">Créer mon compte gratuit →</a></div></div></div>
      </section>

      <section className={`stage stage--structure${patientMode ? '' : ' is-active'}`}>
        <div className="hero">
          <div className="hero__in">
            <div>
              <span className="eyebrow">Offre de lancement · CPP-2026</span>
              <h1 className="h1">Devenez<br /><em>Partenaire Pionnier</em></h1>
              <p className="lead">Rejoignez les premières structures qui construisent l'annuaire paraclinique de référence du Sénégal. Un canal d'acquisition actif de patients, sans commission sur vos actes, jamais.</p>
              <div className="cta-row"><a className="btn btn--primary" href="#inscription-form">Devenir Partenaire Pionnier →</a><a className="btn btn--ghost" href="https://wa.me/221781673189" target="_blank" rel="noreferrer"><i className="ti ti-message" /> Parler à l'équipe</a></div>
              <div className="pill-badge"><i className="ti ti-star" /> <b>50 places</b> · Dakar</div>
            </div>
            <div className="mock"><div className="dash"><div className="dash__bar"><span className="dash__badge"><i className="ti ti-star" /> Partenaire Pionnier</span><span className="dash__dots"><i /><i /><i /></span></div><div className="dash__title">Tableau de bord · période Pionnière</div><div className="kpis"><div className="kpi"><div className="lbl">Vues profil</div><div className="val">347</div><div className="up">↑ +42 / semaine</div></div><div className="kpi"><div className="lbl">Devis WhatsApp</div><div className="val">62</div><div className="up">↑ +8 / semaine</div></div><div className="kpi"><div className="lbl">Réservations</div><div className="val">28</div><div className="up">↑ +4 / semaine</div></div><div className="kpi kpi--accent"><div className="lbl">Valeur générée</div><div className="val">1,24M</div><div className="up">FCFA · actes</div></div></div><div className="spark"><i /><i /><i /><i /><i /><i /><i /><i className="g" /></div></div></div>
          </div>
        </div>
        <div className="sec">
          <div className="sec__eyebrow">Ce que vous obtenez</div>
          <h2 className="sec__title">Quatre avantages <em>réservés aux pionniers</em></h2>
          <p className="sec__sub">Votre vitrine digitale prête en 15 jours, et une présence conservée à vie.</p>
          <div className="grid-2">
            <article className="card num-card"><span className="num">01</span><div className="card__ico"><i className="ti ti-gift" /></div><h3>6 mois d'accès Pro</h3><p><b>Gratuit.</b> Annuaire, devis WhatsApp, réservations, tableau de bord et support prioritaire.</p></article>
            <article className="card num-card"><span className="num">02</span><div className="card__ico"><i className="ti ti-device-mobile" /></div><h3>MedPlaque NFC offerte</h3><p><b>Posée à votre accueil.</b> Un scan renvoie le patient vers votre profil public MedCare.</p></article>
            <article className="card num-card"><span className="num">03</span><div className="card__ico"><i className="ti ti-circle-check" /></div><h3>Badge Pionnier à vie</h3><p><b>Permanent</b> sur votre profil. Le symbole de la confiance accordée dès le lancement.</p></article>
            <article className="card num-card"><span className="num">04</span><div className="card__ico"><i className="ti ti-chart-bar" /></div><h3>Bilan d'activité au M5</h3><p><b>Avant toute décision.</b> Vues, devis, réservations et scans NFC en données réelles.</p></article>
          </div>
          <div className="band band--blue"><div className="band__left"><div className="band__ico"><i className="ti ti-infinity" /></div><div><h4>Votre présence digitale à vie, sans frais</h4><p>Profil public actif à vie et badge Pionnier conservés, quel que soit votre plan ou une pause d'abonnement.</p></div></div></div>
        </div>
        <div className="sec">
          <div className="grid-2">
            <div className="guar"><div className="guar__ico"><i className="ti ti-scale" /></div><div><h4>Modèle 100% sans commission</h4><p>MedCare ne prélève aucune commission sur vos actes médicaux. Conforme Art. 11 · Décret N°67-147.</p></div></div>
            <div className="guar"><div className="guar__ico"><i className="ti ti-shield-check" /></div><div><h4>Sécurité de vos données</h4><p>Données de santé hébergées au Sénégal, pour la souveraineté numérique.</p></div></div>
          </div>
        </div>
        <div className="sec"><div className="steps"><div className="step"><div className="n">1</div><h4>OUI de principe</h4><p>Entretien avec le responsable de la structure.</p></div><div className="step"><div className="n">2</div><h4>Signature CPP</h4><p>Convention de Partenariat Pionnier, formelle et numérotée.</p></div><div className="step"><div className="n">3</div><h4>Onboarding J+15</h4><p>Profil public complet et MedPlaque livrée.</p></div></div></div>
        <div className="finalcta"><div className="finalcta__in"><h3>Prêt à rejoindre les pionniers ?</h3><p>Créez votre compte établissement en quelques minutes, ou découvrez d'abord comment rejoindre le programme.</p><div className="cta-row"><a className="btn btn--primary" href="#inscription-form">Créer mon compte →</a></div></div></div>
      </section>
    </>
  );
}

export function RegisterPage() {
  const [mode, setMode] = useState<Mode>(() => (
    new URLSearchParams(window.location.search).get('type') === 'patient'
      ? 'patient'
      : 'structure'
  ));
  const [topologie, setTopologie] = useState<Topologie>('simple');
  const [profession, setProfession] = useState<Profession>('medecin');
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [exerciseModes, setExerciseModes] = useState<string[]>(['cabinet', 'domicile']);

  // Shared Form Fields
  const [prenom, setPrenom] = useState('');
  const [nom, setNom] = useState('');
  const [username, setUsername] = useState('');
  const [usernameTouched, setUsernameTouched] = useState(false);
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Structure specific
  const [enseigne, setEnseigne] = useState('');
  const [adresse, setAdresse] = useState('');
  const [quartier, setQuartier] = useState('');
  const [ville, setVille] = useState('Dakar');
  const [telPro, setTelPro] = useState('');

  // Praticien specific
  const [numOrdre, setNumOrdre] = useState('');
  const [zoneIntervention, setZoneIntervention] = useState('');

  const [submitErrors, setSubmitErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // Auto-generate username if not manually edited
  const handleNameChange = (first: string, last: string) => {
    setPrenom(first);
    setNom(last);
    if (!usernameTouched) {
      setUsername(slugify(`${first} ${last}`));
    }
  };

  const handleEnseigneChange = (val: string) => {
    setEnseigne(val);
    if (!usernameTouched) {
      setUsername(slugify(val));
    }
  };

  const toggleSpecialty = (sp: string) => {
    if (specialties.includes(sp)) {
      setSpecialties(specialties.filter((s) => s !== sp));
    } else {
      setSpecialties([...specialties, sp]);
    }
  };

  const toggleExercise = (m: string) => {
    if (exerciseModes.includes(m)) {
      setExerciseModes(exerciseModes.filter((x) => x !== m));
    } else {
      setExerciseModes([...exerciseModes, m]);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (password !== passwordConfirm) {
      setSubmitErrors(['Les deux mots de passe ne correspondent pas.']);
      return;
    }

    setSubmitErrors([]);
    setLoading(true);
    try {
      const formData = new FormData(e.currentTarget);
      const next = new URLSearchParams(window.location.search).get('next');
      if (next) formData.set('next', next);
      formData.set('organisme_topology', topologie);
      formData.set('praticien_profession', profession);
      formData.set('praticien_specialties', JSON.stringify(specialties));
      formData.set('praticien_modes', exerciseModes.join(','));
      const csrfToken = await getCsrfToken();

      const response = await fetch('/api/auth/register/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: formData,
      });
      const data = (await response.json()) as {
        redirect_url?: string;
        errors?: Record<string, string[]>;
      };
      if (!response.ok) {
        setSubmitErrors(Object.values(data.errors || {}).flat());
        return;
      }
      if (!data.redirect_url) {
        throw new Error('Le serveur n’a pas indiqué la page de destination.');
      }
      window.location.assign(data.redirect_url);
    } catch (error) {
      setSubmitErrors([
        error instanceof Error
          ? error.message
          : 'Une erreur inattendue a empêché l’inscription.',
      ]);
    } finally {
      setLoading(false);
    }
  };

  const titleText =
    mode === 'structure'
      ? 'Créer un compte établissement'
      : mode === 'praticien'
      ? 'Créer un compte praticien'
      : 'Créer un compte Patient';

  const subtitleText =
    mode === 'structure'
      ? 'Renseignez vos informations pour créer votre fiche publique.'
      : mode === 'praticien'
      ? 'Renseignez vos informations professionnelles pour créer votre fiche.'
      : 'Vos informations personnelles pour réserver et suivre vos soins.';

  const submitBtnText =
    mode === 'structure'
      ? 'Créer le compte établissement →'
      : mode === 'praticien'
      ? 'Créer le compte praticien →'
      : 'Créer mon compte Patient →';

  return (
    <div className="mc-page-wrap mc-landing-page mc-react-register">
      <RegisterMarketing mode={mode} onModeChange={setMode} />
      <section id="inscription-form" className="sec landing-register-sec">
        <div className="mc-react-form-wrap">
          <div className="card mc-react-form-card">
            <h1>{titleText}</h1>
            <p className="mc-react-form-subtitle">{subtitleText}</p>
        <form onSubmit={handleSubmit} className="space-y-5">
            <input type="hidden" name="user_type" value={mode === 'patient' ? 'patient' : 'prestataire'} />
            <input type="hidden" name="account_nature" value={mode === 'praticien' ? 'praticien' : 'structure'} />
            <input type="hidden" name="organisme_topology" value={topologie} />
            <input type="hidden" name="praticien_profession" value={profession} />
            <input type="hidden" name="praticien_specialties" value={JSON.stringify(specialties)} />
            <input type="hidden" name="praticien_modes" value={exerciseModes.join(',')} />
            {submitErrors.length > 0 && (
              <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                <ul className="list-disc space-y-1 pl-5">
                  {submitErrors.map((error, index) => <li key={`${error}-${index}`}>{error}</li>)}
                </ul>
              </div>
            )}
            {/* ── Fork Soignant / Structure ── */}
            {mode !== 'patient' ? (
              <div id="fork-container">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-extrabold uppercase tracking-wider text-[#123a63] dark:text-[#0ea5e9]">
                    Type de compte <span className="text-red-500">*</span>
                  </span>
                  <span className="text-[9.5px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-300">
                    Mode soignant
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Structure Card */}
                  <div
                    onClick={() => setMode('structure')}
                    className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 ${
                      mode === 'structure'
                        ? 'border-[#0a5c8a] bg-[#eef6fb] dark:bg-sky-950/30 shadow-sm'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <i className="ti ti-building-hospital text-2xl text-[#0a5c8a] dark:text-[#0ea5e9]"></i>
                    <div>
                      <div className="font-syne font-bold text-sm text-[#123a63] dark:text-white">
                        Structure de soins
                      </div>
                      <div className="text-[11.5px] text-gray-500 dark:text-gray-400 mt-0.5 leading-snug">
                        Laboratoire, cabinet, centre, clinique, hôpital, réseau.
                      </div>
                    </div>
                  </div>

                  {/* Praticien Card */}
                  <div
                    onClick={() => setMode('praticien')}
                    className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 ${
                      mode === 'praticien'
                        ? 'border-[#0a5c8a] bg-[#eef6fb] dark:bg-sky-950/30 shadow-sm'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <i className="ti ti-stethoscope text-2xl text-emerald-600"></i>
                    <div>
                      <div className="font-syne font-bold text-sm text-[#123a63] dark:text-white">
                        Praticien indépendant
                      </div>
                      <div className="text-[11.5px] text-gray-500 dark:text-gray-400 mt-0.5 leading-snug">
                        Médecin, infirmier, kiné, sage-femme, psychologue.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Switch to Patient Link */}
                <button
                  type="button"
                  onClick={() => setMode('patient')}
                  className="mt-2 text-xs font-bold text-[#0a5c8a] dark:text-[#0ea5e9] hover:underline block text-left"
                >
                  Vous êtes un particulier ? Basculer sur compte Patient →
                </button>
              </div>
            ) : (
              <div className="p-3.5 rounded-2xl bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-800 flex items-center justify-between">
                <span className="text-xs font-bold text-[#123a63] dark:text-sky-300">
                  Mode Patient activé
                </span>
                <button
                  type="button"
                  onClick={() => setMode('structure')}
                  className="text-xs font-bold text-[#0a5c8a] dark:text-[#0ea5e9] hover:underline"
                >
                  ← Basculer sur compte Soignant / Structure
                </button>
              </div>
            )}

            {/* ── Prénom & Nom (Praticien & Patient) ── */}
            {(mode === 'patient' || mode === 'praticien') && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Prénom <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="first_name"
                    required
                    placeholder="Ex : Cheikh"
                    value={prenom}
                    onChange={(e) => handleNameChange(e.target.value, nom)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0a5c8a]/40"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Nom de famille <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="last_name"
                    required
                    placeholder="Ex : Diagne"
                    value={nom}
                    onChange={(e) => handleNameChange(prenom, e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0a5c8a]/40"
                  />
                </div>
              </div>
            )}

            {/* ── Identifiant & Email & Téléphone ── */}
            <div>
              <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Nom d'utilisateur <span className="text-gray-400 font-normal">(identifiant de connexion)</span> <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="username"
                required
                placeholder="ex : polyclinique_de_libe, dr_diagne"
                value={username}
                onChange={(e) => {
                  setUsernameTouched(true);
                  setUsername(e.target.value);
                }}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0a5c8a]/40"
              />
              <p className="text-[11px] text-[#0a5c8a] dark:text-sky-400 mt-1 flex items-center gap-1 font-medium">
                <i className="ti ti-bulb"></i> Cet identifiant est le username unique de connexion.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  name="email"
                  required
                  placeholder="votre@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0a5c8a]/40"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  {mode === 'structure' ? 'Téléphone du responsable' : 'Téléphone personnel'}
                </label>
                <input
                  type="tel"
                  name="phone_number"
                  placeholder="+221 77 000 00 00"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0a5c8a]/40"
                />
              </div>
            </div>

            {/* ── BLOC STRUCTURE (Exclusif Mode Structure) ── */}
            {mode === 'structure' && (
              <div className="p-5 rounded-2xl bg-[#f4f8fd] dark:bg-gray-800/60 border border-[#dce6f2] dark:border-gray-700 space-y-4">
                <div>
                  <div className="text-[11px] font-extrabold uppercase tracking-wider text-[#123a63] dark:text-[#0ea5e9]">
                    Votre établissement
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Ces informations créent votre fiche publique. La géolocalisation précise (GPS) s'ajoute après connexion.
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Nom commercial / enseigne <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="organisme_name"
                    required
                    placeholder="Ex : Clinique Les Almadies, Laboratoire Bio-Santé"
                    value={enseigne}
                    onChange={(e) => handleEnseigneChange(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0a5c8a]/40"
                  />
                </div>

                {/* Topologie selector */}
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Type d'établissement <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div
                      onClick={() => setTopologie('simple')}
                      className={`p-3 rounded-xl border-1.5 cursor-pointer transition-all ${
                        topologie === 'simple'
                          ? 'border-[#0a5c8a] bg-[#eef6fb] dark:bg-sky-950/30'
                          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                      }`}
                    >
                      <i className="ti ti-building text-lg text-[#0a5c8a]"></i>
                      <div className="font-syne font-bold text-xs text-gray-900 dark:text-white mt-1">
                        Structure simple
                      </div>
                      <div className="text-[10.5px] text-gray-500">Un seul site.</div>
                      <div className="text-[9.5px] text-gray-400 mt-1">Ex : labo, cabinet</div>
                    </div>

                    <div
                      onClick={() => setTopologie('multiservice')}
                      className={`p-3 rounded-xl border-1.5 cursor-pointer transition-all ${
                        topologie === 'multiservice'
                          ? 'border-[#0a5c8a] bg-[#eef6fb] dark:bg-sky-950/30'
                          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                      }`}
                    >
                      <i className="ti ti-building-bank text-lg text-[#0a5c8a]"></i>
                      <div className="font-syne font-bold text-xs text-gray-900 dark:text-white mt-1">
                        Multi-services
                      </div>
                      <div className="text-[10.5px] text-gray-500">Un lieu, plusieurs services.</div>
                      <div className="text-[9.5px] text-gray-400 mt-1">Ex : clinique, hôpital</div>
                    </div>

                    <div
                      onClick={() => setTopologie('multisite')}
                      className={`p-3 rounded-xl border-1.5 cursor-pointer transition-all ${
                        topologie === 'multisite'
                          ? 'border-[#0a5c8a] bg-[#eef6fb] dark:bg-sky-950/30'
                          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                      }`}
                    >
                      <i className="ti ti-map text-lg text-[#0a5c8a]"></i>
                      <div className="font-syne font-bold text-xs text-gray-900 dark:text-white mt-1">
                        Réseau multi-sites
                      </div>
                      <div className="text-[10.5px] text-gray-500">Un métier, plusieurs lieux.</div>
                      <div className="text-[9.5px] text-gray-400 mt-1">Ex : réseau labos</div>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Adresse du siège <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="organisme_address"
                    required
                    placeholder="Rue, numéro"
                    value={adresse}
                    onChange={(e) => setAdresse(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Quartier
                    </label>
                    <input
                      type="text"
                      name="organisme_quartier"
                      placeholder="Ex : Plateau, Mermoz"
                      value={quartier}
                      onChange={(e) => setQuartier(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Ville
                    </label>
                    <input
                      type="text"
                      name="organisme_city"
                      value={ville}
                      onChange={(e) => setVille(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Téléphone professionnel <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="tel"
                    name="organisme_contact_phone"
                    required
                    placeholder="+221 33 000 00 00"
                    value={telPro}
                    onChange={(e) => setTelPro(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Logo ou photo de l'établissement <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="file"
                    name="organisme_logo"
                    accept="image/*"
                    required
                    className="w-full rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3.5 py-2.5 text-sm text-gray-700 dark:text-gray-200"
                  />
                </div>
              </div>
            )}

            {/* ── BLOC PRATICIEN (Exclusif Mode Praticien) ── */}
            {mode === 'praticien' && (
              <div className="p-5 rounded-2xl bg-[#f4f8fd] dark:bg-gray-800/60 border border-[#dce6f2] dark:border-gray-700 space-y-4">
                <div>
                  <div className="text-[11px] font-extrabold uppercase tracking-wider text-[#123a63] dark:text-[#0ea5e9]">
                    Votre profil praticien
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    En exercice indépendant, votre nom est assumé sur votre fiche publique.
                  </div>
                </div>

                {/* Profession cards */}
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1.5">
                    Profession <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {PROFESSIONS.map((p) => (
                      <div
                        key={p.id}
                        onClick={() => setProfession(p.id)}
                        className={`p-2.5 rounded-xl border-1.5 cursor-pointer transition-all ${
                          profession === p.id
                            ? 'border-[#0a5c8a] bg-[#eef6fb] dark:bg-sky-950/30'
                            : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                        }`}
                      >
                        <i className={`ti ${p.icon} text-lg text-[#0a5c8a]`}></i>
                        <div className="font-syne font-bold text-xs text-gray-900 dark:text-white mt-1">
                          {p.label}
                        </div>
                        <div className="text-[10px] text-gray-500">{p.sub}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Inscription à l'ordre */}
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Numéro d'inscription à l'Ordre <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="praticien_ordre"
                    required
                    placeholder="Ex : N° Ordre National des Médecins"
                    value={numOrdre}
                    onChange={(e) => setNumOrdre(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  />
                  <div className="mt-1.5 p-2 rounded-lg bg-amber-50 text-amber-900 border border-amber-200 text-[11px] leading-relaxed">
                    La présentation reste factuelle : pas de classement, pas de mise en avant promotionnelle. Le titre est vérifié avant mise en ligne.
                  </div>
                </div>

                {/* Spécialités si Médecin */}
                {profession === 'medecin' && (
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Vos spécialités médicales (choix multiple)
                    </label>
                    <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-2 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                      {SPECIALITES_MEDECIN.map((sp) => {
                        const checked = specialties.includes(sp);
                        return (
                          <button
                            key={sp}
                            type="button"
                            onClick={() => toggleSpecialty(sp)}
                            className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                              checked
                                ? 'bg-emerald-600 text-white border-emerald-600 font-bold'
                                : 'bg-gray-50 dark:bg-gray-750 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600'
                            }`}
                          >
                            {checked ? '✓ ' : '+ '}
                            {sp}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Modes d'exercice */}
                <div>
                  <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                    Mode d'exercice
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => toggleExercise('cabinet')}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                        exerciseModes.includes('cabinet')
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300 font-bold'
                          : 'bg-white dark:bg-gray-800 border-gray-200'
                      }`}
                    >
                      {exerciseModes.includes('cabinet') ? '✓ ' : ''}Au cabinet
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleExercise('domicile')}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                        exerciseModes.includes('domicile')
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300 font-bold'
                          : 'bg-white dark:bg-gray-800 border-gray-200'
                      }`}
                    >
                      {exerciseModes.includes('domicile') ? '✓ ' : ''}À domicile
                    </button>
                    <span className="px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-100 text-gray-400 text-xs font-medium cursor-not-allowed">
                      Téléconsultation · V2
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Zone d'intervention
                    </label>
                    <input
                      type="text"
                      name="praticien_zone"
                      placeholder="Ex : Dakar, Almadies"
                      value={zoneIntervention}
                      onChange={(e) => setZoneIntervention(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Téléphone professionnel <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="tel"
                      name="praticien_phone"
                      required
                      placeholder="+221 77 000 00 00"
                      value={telPro}
                      onChange={(e) => setTelPro(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* ── Mot de passe & Confirmation ── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Mot de passe <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password1"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm pr-9"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="mc-password-toggle"
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Confirmer le mot de passe <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password2"
                    required
                    placeholder="••••••••"
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm pr-9"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="mc-password-toggle"
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
                  </button>
                </div>
              </div>
            </div>

            {/* ── Submit Button ── */}
            <button
              type="submit"
              disabled={loading}
              className="mc-react-submit"
            >
              {loading ? 'Création du compte…' : submitBtnText}
            </button>

            {/* ── Sign in link ── */}
            <div className="text-center text-xs text-gray-500 pt-3 border-t border-gray-200 dark:border-gray-700">
              Déjà un compte ?{' '}
              <Link to="/connexion/" className="font-bold text-[#0a5c8a] dark:text-[#0ea5e9] hover:underline">
                Se connecter
              </Link>
            </div>
        </form>
          </div>
        </div>
      </section>
    </div>
  );
}
