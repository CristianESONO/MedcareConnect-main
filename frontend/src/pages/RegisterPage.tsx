import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

type AccountType = 'patient' | 'pro';

export function RegisterPage() {
  const [accountType, setAccountType] = useState<AccountType>('patient');
  const [prenom, setPrenom] = useState('');
  const [nom, setNom] = useState('');
  const [telephone, setTelephone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Pro specific fields
  const [nomStructure, setNomStructure] = useState('');
  const [typeStructure, setTypeStructure] = useState('Clinique Privée');
  const [ville, setVille] = useState('Dakar');

  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen py-10 px-4 flex items-center justify-center bg-gray-50 dark:bg-[#0b1120]">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl bg-white dark:bg-gray-800 rounded-3xl shadow-xl border border-gray-200 dark:border-gray-700 p-6 sm:p-10"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-3">
            <img src="/logo.png" alt="MedCare" className="h-9 w-auto" />
            <span className="font-syne font-extrabold text-xl text-[#123a63] dark:text-white">
              MedCare<span className="text-[#0ea5e9]">Connect</span>
            </span>
          </Link>
          <h1 className="font-syne font-extrabold text-2xl text-gray-900 dark:text-white">
            Créer un compte
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
            Rejoignez le réseau de santé moderne au Sénégal
          </p>
        </div>

        {submitted ? (
          <div className="text-center py-10">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-3xl mx-auto mb-4">
              <i className="ti ti-circle-check"></i>
            </div>
            <h3 className="font-syne font-bold text-xl text-gray-900 dark:text-white">
              Inscription réussie !
            </h3>
            <p className="text-xs text-gray-500 mt-2 max-w-sm mx-auto">
              Bienvenue sur MedCare Connect. Vous pouvez désormais vous connecter à votre espace personnel.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block px-6 py-2.5 rounded-xl bg-[#123a63] text-white font-bold text-xs shadow-md"
            >
              Se connecter
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Account Type Selection (Fork) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-[11px] font-extrabold text-[#123a63] dark:text-[#0ea5e9] uppercase tracking-wider">
                  Type de compte *
                </label>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                  Sélection obligatoire
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Patient option */}
                <div
                  onClick={() => setAccountType('patient')}
                  className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 ${
                    accountType === 'patient'
                      ? 'border-[#123a63] dark:border-[#0ea5e9] bg-sky-50/50 dark:bg-sky-950/20 shadow-sm'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <i className="ti ti-user text-2xl text-[#123a63] dark:text-[#0ea5e9]"></i>
                  <div>
                    <div className="font-syne font-bold text-sm text-gray-900 dark:text-white">
                      Patient
                    </div>
                    <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 leading-tight">
                      Rechercher des examens & soins
                    </div>
                  </div>
                </div>

                {/* Soignant option */}
                <div
                  onClick={() => setAccountType('pro')}
                  className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 ${
                    accountType === 'pro'
                      ? 'border-[#123a63] dark:border-[#0ea5e9] bg-sky-50/50 dark:bg-sky-950/20 shadow-sm'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <i className="ti ti-stethoscope text-2xl text-emerald-600"></i>
                  <div>
                    <div className="font-syne font-bold text-sm text-gray-900 dark:text-white">
                      Soignant / Structure
                    </div>
                    <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 leading-tight">
                      Publier des forfaits & tarifs
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Name Fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Prénom *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Aminata"
                  value={prenom}
                  onChange={(e) => setPrenom(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Nom de famille *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Ndiaye"
                  value={nom}
                  onChange={(e) => setNom(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                />
              </div>
            </div>

            {/* Pro Specific Fields */}
            {accountType === 'pro' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="p-4 rounded-2xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-800 space-y-3"
              >
                <div>
                  <label className="block text-[11px] font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider mb-1">
                    Nom de votre établissement médical *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Clinique du Cap, Laboratoire Pasteur..."
                    value={nomStructure}
                    onChange={(e) => setNomStructure(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider mb-1">
                      Type de structure
                    </label>
                    <select
                      value={typeStructure}
                      onChange={(e) => setTypeStructure(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                    >
                      <option>Clinique Privée</option>
                      <option>Hôpital Public</option>
                      <option>Laboratoire d'Analyses</option>
                      <option>Cabinet Médical</option>
                      <option>Centre d'Imagerie</option>
                      <option>Pharmacie</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider mb-1">
                      Ville / Région
                    </label>
                    <input
                      type="text"
                      value={ville}
                      onChange={(e) => setVille(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* Telephone & Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Téléphone (Sénégal) *
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-500">
                    +221
                  </span>
                  <input
                    type="tel"
                    required
                    placeholder="77 000 00 00"
                    value={telephone}
                    onChange={(e) => setTelephone(e.target.value)}
                    className="w-full pl-13 pr-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  required
                  placeholder="nom@exemple.sn"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Mot de passe *
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="8 caractères minimum"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'} text-base`}></i>
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#123a63] to-[#0ea5e9] text-white font-bold text-sm shadow-md hover:shadow-lg transition-all active:scale-[0.99]"
            >
              Créer mon compte MedCare
            </button>

            {/* Switch to login */}
            <div className="text-center text-xs text-gray-500 pt-3 border-t border-gray-200 dark:border-gray-700">
              Déjà inscrit sur MedCare ?{' '}
              <Link to="/login" className="font-bold text-[#123a63] dark:text-[#0ea5e9] hover:underline">
                Connectez-vous ici
              </Link>
            </div>
          </form>
        )}
      </motion.div>
    </div>
  );
}
