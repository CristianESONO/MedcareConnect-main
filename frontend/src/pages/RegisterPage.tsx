import { useState, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';

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

export function RegisterPage() {
  const [mode, setMode] = useState<Mode>('structure');
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
  const [region, setRegion] = useState('');
  const [telPro, setTelPro] = useState('');

  // Praticien specific
  const [numOrdre, setNumOrdre] = useState('');
  const [zoneIntervention, setZoneIntervention] = useState('');

  const [submitted, setSubmitted] = useState(false);

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== passwordConfirm) {
      alert('Les deux mots de passe ne correspondent pas.');
      return;
    }
    setSubmitted(true);
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
    <div className="min-h-screen py-10 px-4 flex items-center justify-center bg-[#f8fafc] dark:bg-[#0b1120]">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-2xl bg-white dark:bg-[#0f172a] rounded-3xl shadow-xl border border-gray-200 dark:border-gray-800 p-6 sm:p-10"
      >
        {/* Brand Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-block mb-3">
            <img src="/logo_MEDCARE.png" alt="MedCare" className="h-10 w-auto mx-auto object-contain" />
          </Link>
          <h1 className="font-syne font-extrabold text-2xl sm:text-3xl text-[#123a63] dark:text-white">
            {titleText}
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1 font-medium">
            {subtitleText}
          </p>
        </div>

        {submitted ? (
          <div className="text-center py-10">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-3xl mx-auto mb-4">
              <i className="ti ti-circle-check"></i>
            </div>
            <h3 className="font-syne font-bold text-xl text-gray-900 dark:text-white">
              Votre inscription est validée !
            </h3>
            <p className="text-xs text-gray-500 mt-2 max-w-sm mx-auto">
              Bienvenue sur MedCare Connect. Vous pouvez maintenant vous connecter à votre compte.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block px-8 py-3 rounded-xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white font-bold text-xs shadow-md"
            >
              Se connecter à MedCare
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
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
                    required
                    placeholder="+221 33 000 00 00"
                    value={telPro}
                    onChange={(e) => setTelPro(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
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
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm pr-9"
                  />
                  <span
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 cursor-pointer"
                  >
                    <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`}></i>
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Confirmer le mot de passe <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm pr-9"
                  />
                  <span
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 cursor-pointer"
                  >
                    <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`}></i>
                  </span>
                </div>
              </div>
            </div>

            {/* ── Submit Button ── */}
            <button
              type="submit"
              className="w-full py-4 rounded-xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white font-syne font-extrabold text-sm sm:text-base shadow-lg hover:brightness-105 active:scale-[0.99] transition-all cursor-pointer"
            >
              {submitBtnText}
            </button>

            {/* ── Sign in link ── */}
            <div className="text-center text-xs text-gray-500 pt-3 border-t border-gray-200 dark:border-gray-700">
              Déjà un compte ?{' '}
              <Link to="/login" className="font-bold text-[#0a5c8a] dark:text-[#0ea5e9] hover:underline">
                Se connecter
              </Link>
            </div>
          </form>
        )}
      </motion.div>
    </div>
  );
}
