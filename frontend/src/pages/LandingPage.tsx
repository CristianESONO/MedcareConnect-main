import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

const PROCESS_STEPS = [
  {
    step: '01',
    icon: 'ti-search',
    title: 'Rechercher',
    desc: 'Examen médical, analyse ou spécialité',
  },
  {
    step: '02',
    icon: 'ti-scale',
    title: 'Comparer',
    desc: 'Tarifs réels, distance & conventionnements',
  },
  {
    step: '03',
    icon: 'ti-id',
    title: 'Consulter la fiche',
    desc: 'Équipements certifiés & horaires d\'ouverture',
  },
  {
    step: '04',
    icon: 'ti-brand-whatsapp',
    title: 'Contacter',
    desc: 'Échange direct WhatsApp ou devis panier',
  },
];

const PILIERS = [
  {
    icon: 'ti-flask',
    title: 'Laboratoires & Biologie',
    count: '850+ analyses',
    desc: 'Hémogrammes, glycémie, bilans hépatiques et rénaux avec résultats sécurisés.',
  },
  {
    icon: 'ti-scan',
    title: 'Imagerie Médicale',
    count: '320+ examens',
    desc: 'Échographies, radiographies numériques, scanners et IRM haute définition.',
  },
  {
    icon: 'ti-stethoscope',
    title: 'Consultations Spécialisées',
    count: '45 spécialités',
    desc: 'Cardiologie, pédiatrie, gynécologie, dermatologie et médecine générale.',
  },
  {
    icon: 'ti-ambulance',
    title: 'Urgences & Ambulances',
    count: 'Disponibilité 24/7',
    desc: 'Évacuations sanitaires et transport médicalisé partout au Sénégal.',
  },
  {
    icon: 'ti-home',
    title: 'Soins & Prises de Sang à Domicile',
    count: 'Partout à Dakar',
    desc: 'Infirmiers qualifiés pour vos prélèvements à domicile ou au bureau.',
  },
  {
    icon: 'ti-pill',
    title: 'Pharmacies & Garde',
    count: '150+ officines',
    desc: 'Localisation des pharmacies de garde et disponibilité des traitements.',
  },
];

const STATS = [
  { val: '150+', label: 'Structures Référencées', icon: 'ti-building-hospital' },
  { val: '1 800+', label: 'Actes & Tarifs Réels', icon: 'ti-receipt' },
  { val: '28', label: 'IPM & Assurances Intégrées', icon: 'ti-shield-check' },
  { val: '0 %', label: 'Commission Patient', icon: 'ti-percentage' },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b1120] text-gray-900 dark:text-gray-100">
      {/* ── 1. HERO SECTION ────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-16 sm:pb-28 bg-gradient-to-b from-white via-sky-50/40 to-[#f8fafc] dark:from-[#0f172a] dark:via-[#0b1120] dark:to-[#0b1120] border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10 text-center">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#123a63]/10 dark:bg-sky-500/10 border border-[#123a63]/20 dark:border-sky-500/20 text-[#123a63] dark:text-[#0ea5e9] text-xs font-bold uppercase tracking-wider mb-6"
          >
            <i className="ti ti-heart-handshake text-base"></i>
            Première plateforme paraclinique digitale du Sénégal
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="font-syne font-black text-4xl sm:text-6xl text-[#0f172a] dark:text-white leading-[1.15] max-w-4xl mx-auto tracking-tight mb-6"
          >
            Votre santé,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#123a63] via-[#0284c7] to-[#0ea5e9]">
              au bout des doigts.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-base sm:text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto mb-10 leading-relaxed font-medium"
          >
            Comparez les tarifs d’analyses médicales, d'imagerie et de consultations. Trouvez l’établissement le plus proche et accédez à vos soins en toute sérénité.
          </motion.p>

          {/* 2 Big CTA Cards (Patient vs Soignant) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-3xl mx-auto"
          >
            {/* Card Patient */}
            <div className="p-6 sm:p-7 rounded-3xl bg-white dark:bg-gray-800/90 border-2 border-sky-100 dark:border-gray-700 shadow-xl shadow-sky-900/5 hover:border-[#0ea5e9] transition-all text-left flex flex-col justify-between group">
              <div>
                <div className="w-13 h-13 rounded-2xl bg-[#0ea5e9]/10 text-[#0ea5e9] flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">
                  <i className="ti ti-user-heart"></i>
                </div>
                <h3 className="font-syne font-extrabold text-xl text-[#123a63] dark:text-white mb-1.5">
                  Je suis Patient
                </h3>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                  Trouvez un examen médical, comparez les prix réels et vérifiez la prise en charge de votre mutuelle ou IPM.
                </p>
              </div>

              <Link
                to="/search"
                className="mt-6 w-full py-3.5 px-5 rounded-2xl bg-[#123a63] hover:bg-[#1a4f87] text-white font-bold text-sm shadow-md flex items-center justify-between transition-all"
              >
                <span>Rechercher un soin</span>
                <i className="ti ti-arrow-right text-base group-hover:translate-x-1 transition-transform"></i>
              </Link>
            </div>

            {/* Card Soignant / Professionnel */}
            <div className="p-6 sm:p-7 rounded-3xl bg-white dark:bg-gray-800/90 border-2 border-emerald-100 dark:border-gray-700 shadow-xl shadow-emerald-900/5 hover:border-emerald-500 transition-all text-left flex flex-col justify-between group">
              <div>
                <div className="w-13 h-13 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">
                  <i className="ti ti-stethoscope"></i>
                </div>
                <h3 className="font-syne font-extrabold text-xl text-[#123a63] dark:text-white mb-1.5">
                  Je suis Soignant ou Clinique
                </h3>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                  Référencez votre établissement, publiez votre catalogue d’actes et recevez des patients qualifiés.
                </p>
              </div>

              <Link
                to="/register"
                className="mt-6 w-full py-3.5 px-5 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md flex items-center justify-between transition-all"
              >
                <span>Inscrire ma structure</span>
                <i className="ti ti-arrow-right text-base group-hover:translate-x-1 transition-transform"></i>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── 2. PROCESS STRIP ──────────────────────────────────────────── */}
      <section className="py-12 bg-white dark:bg-gray-850 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {PROCESS_STEPS.map((step) => (
              <div key={step.step} className="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-gray-800/60 border border-gray-200/60 dark:border-gray-700">
                <div className="p-3 rounded-2xl bg-[#123a63]/10 dark:bg-sky-500/20 text-[#123a63] dark:text-[#0ea5e9] text-xl shrink-0">
                  <i className={`ti ${step.icon}`}></i>
                </div>
                <div>
                  <span className="text-[10px] font-extrabold text-[#0ea5e9] uppercase tracking-wider block">
                    Étape {step.step}
                  </span>
                  <h4 className="font-syne font-bold text-sm text-[#0f172a] dark:text-white mt-0.5">
                    {step.title}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {step.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. STATS BAR ──────────────────────────────────────────────── */}
      <section className="py-12 bg-gradient-to-r from-[#123a63] to-[#1a4f87] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {STATS.map((st) => (
              <div key={st.label} className="p-4 flex flex-col items-center">
                <i className={`ti ${st.icon} text-3xl text-[#0ea5e9] mb-2`}></i>
                <div className="font-syne font-black text-3xl sm:text-4xl tracking-tight">
                  {st.val}
                </div>
                <div className="text-xs sm:text-sm font-semibold text-sky-100 mt-1">
                  {st.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 4. LES 6 PILIERS MEDCARE ──────────────────────────────────── */}
      <section className="py-16 sm:py-20 max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-12">
          <div>
            <span className="text-xs font-bold text-[#0ea5e9] uppercase tracking-wider block mb-1">
              Architecture des Services
            </span>
            <h2 className="font-syne font-extrabold text-3xl sm:text-4xl text-[#0f172a] dark:text-white">
              Les 6 piliers <span className="text-[#0ea5e9]">MedCare</span>
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 max-w-xl">
              Chaque domaine médical est structuré, tarifé et transparent avant même votre consultation.
            </p>
          </div>

          <Link
            to="/search"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-[#123a63] dark:text-[#0ea5e9] hover:underline"
          >
            Explorer le catalogue complet <i className="ti ti-arrow-right"></i>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {PILIERS.map((pilier) => (
            <div
              key={pilier.title}
              className="p-6 rounded-3xl bg-white dark:bg-gray-800 border border-gray-200/80 dark:border-gray-700 shadow-sm hover:shadow-md transition-all group"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 rounded-2xl bg-sky-50 dark:bg-sky-950/40 text-[#0ea5e9] text-2xl group-hover:bg-[#123a63] group-hover:text-white transition-colors">
                  <i className={`ti ${pilier.icon}`}></i>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                  {pilier.count}
                </span>
              </div>
              <h3 className="font-syne font-bold text-lg text-[#0f172a] dark:text-white mb-2">
                {pilier.title}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-4">
                {pilier.desc}
              </p>
              <Link
                to="/search"
                className="text-xs font-bold text-[#0ea5e9] hover:text-[#0284c7] inline-flex items-center gap-1"
              >
                Consulter les tarifs <i className="ti ti-chevron-right text-xs"></i>
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ── 5. ACCÈS IMMÉDIAT & TRANSPARENCE ──────────────────────────── */}
      <section className="py-16 bg-white dark:bg-gray-850 border-t border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="rounded-3xl bg-gradient-to-br from-[#123a63] to-[#0a2540] text-white p-8 sm:p-14 shadow-2xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="max-w-xl">
              <span className="text-xs font-extrabold uppercase tracking-widest text-[#0ea5e9]">
                Transparence Totale
              </span>
              <h2 className="font-syne font-extrabold text-3xl sm:text-4xl text-white mt-2 mb-4 leading-tight">
                Prix réels. Localisations exactes. Assurances acceptées.
              </h2>
              <p className="text-sm text-sky-100 leading-relaxed font-medium mb-6">
                Fini les mauvaises surprises au guichet : avec MedCare Connect, visualisez le tarif exact de vos soins, les délais d'obtention de résultats et les conventionnements IPM.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/search"
                  className="px-6 py-3 rounded-xl bg-[#0ea5e9] hover:bg-[#0284c7] text-white font-bold text-xs shadow-lg transition-all"
                >
                  Lancer une recherche
                </Link>
                <Link
                  to="/mobile"
                  className="px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-bold text-xs backdrop-blur-md transition-all"
                >
                  Ouvrir l'application mobile
                </Link>
              </div>
            </div>

            <div className="w-full md:w-auto shrink-0 flex justify-center">
              <div className="p-5 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 text-center max-w-xs">
                <i className="ti ti-shield-check text-4xl text-[#0ea5e9] mb-2 block"></i>
                <div className="font-syne font-bold text-base">Données Certifiées</div>
                <p className="text-xs text-sky-200 mt-1">
                  Tous les professionnels et tarifs sont audités et validés par l'équipe MedCare.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 6. FOOTER COMPLET ─────────────────────────────────────────── */}
      <footer className="py-12 bg-[#0f172a] text-gray-300 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <img src="/logo.png" alt="MedCare" className="h-8 w-auto" />
                <span className="font-syne font-bold text-lg text-white">MedCare Connect</span>
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">
                Le portail national de santé et de tarification paraclinique au Sénégal. Transparence, proximité et innovation.
              </p>
            </div>

            <div>
              <h4 className="font-syne font-bold text-sm text-white mb-3">Parcours Patient</h4>
              <ul className="space-y-2 text-xs text-gray-400">
                <li><Link to="/search" className="hover:text-white">Recherche de soins</Link></li>
                <li><Link to="/mobile" className="hover:text-white">Expérience Mobile</Link></li>
                <li><Link to="/search" className="hover:text-white">Laboratoires & Radiologie</Link></li>
                <li><Link to="/search" className="hover:text-white">Urgences & Ambulances</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-syne font-bold text-sm text-white mb-3">Professionnels</h4>
              <ul className="space-y-2 text-xs text-gray-400">
                <li><Link to="/register" className="hover:text-white">Inscrire une structure</Link></li>
                <li><Link to="/dashboard" className="hover:text-white">Tableau de bord</Link></li>
                <li><Link to="/panels" className="hover:text-white">Panels & Forfaits</Link></li>
                <li><Link to="/login" className="hover:text-white">Espace Praticien</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-syne font-bold text-sm text-white mb-3">Contact & Support</h4>
              <p className="text-xs text-gray-400 mb-2">Dakar, Sénégal • 24h/24 & 7j/7</p>
              <a
                href="https://wa.me/221770000000"
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600/20 text-emerald-400 text-xs font-bold border border-emerald-500/30 hover:bg-emerald-600/30 transition-colors"
              >
                <i className="ti ti-brand-whatsapp text-sm"></i> WhatsApp Support
              </a>
            </div>
          </div>

          <div className="pt-6 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between text-xs text-gray-500 gap-4">
            <div>© {new Date().getFullYear()} MedCare Connect Sénégal. Tous droits réservés.</div>
            <div className="flex gap-4">
              <span className="hover:underline cursor-pointer">Conditions Générales</span>
              <span className="hover:underline cursor-pointer">Confidentialité & RGPD</span>
              <span className="hover:underline cursor-pointer">Mentions Légales</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
