import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

const PATIENT_STEPS = [
  {
    num: '01',
    label: 'Recherche Intelligente',
    title: 'Cherchez votre acte ou spécialité',
    desc: "Depuis la barre de recherche, tapez directement le nom d'un examen médical (ex : NFS, Échographie, Consultation Cardiologie) ou explorez les 6 piliers paracliniques.",
    points: ['Recherche par acte ou spécialité', 'Géolocalisation automatique à Dakar', '450+ actes disponibles sans inscription'],
    icon: 'ti-search',
  },
  {
    num: '02',
    label: 'Sélection & Piliers',
    title: 'Constituez votre sélection d’actes',
    desc: 'Cochez plusieurs actes simultanément. Le panier dynamique calcule les combinaisons et affiche en direct les structures en mesure de réaliser l’intégralité de vos examens.',
    points: ['Sélection multiple en 1 clic', 'Compteur d’établissements capables de vous recevoir', 'Filtre par type (hôpital, clinique, labo)'],
    icon: 'ti-checklist',
  },
  {
    num: '03',
    label: 'Comparaison Objective',
    title: 'Comparez les prix réels & conventionnements',
    desc: 'Visualisez les tarifs officiels sans marge cachée, les mutuelles et IPM partenaires (tiers-payant), la distance kilométrique et les délais d’obtention des résultats.',
    points: ['Tarif clair en FCFA', 'Prise en charge IPM / Mutuelle indiquée', 'Badge « Établissement Vérifié »'],
    icon: 'ti-scale',
  },
  {
    num: '04',
    label: 'Devis & Panier',
    title: 'Validez votre devis estimatif gratuit',
    desc: 'Votre panier récapitule les examens retenus, le coût global estimé et l’adresse exacte de la structure choisie.',
    points: ['Devis instantané sans engagement', 'Zéro commission prélevée sur le patient', 'Traçabilité et gain de temps précieux'],
    icon: 'ti-shopping-cart-check',
  },
  {
    num: '05',
    label: 'Mise en Relation',
    title: 'Échangez directement avec la structure',
    desc: 'Finalisez votre rendez-vous via le canal officiel WhatsApp ou le contact téléphonique direct de l’établissement médical.',
    points: ['Liaison WhatsApp directe sécurisée', 'Aucun intermédiaire entre vous et le soignant', 'Consignes pré-analytiques fournies (à jeun, etc.)'],
    icon: 'ti-brand-whatsapp',
  },
];

const SOIGNANT_STEPS = [
  {
    num: '01',
    label: 'Inscription Rapide',
    title: 'Créez votre fiche établissement ou praticien',
    desc: 'Renseignez la nature de votre structure (laboratoire, clinique, cabinet médical) et vos coordonnées professionnelles.',
    points: ['Inscription en moins de 3 minutes', 'Validation par l’équipe MedCare', 'Fiche publique indexée'],
    icon: 'ti-building-hospital',
  },
  {
    num: '02',
    label: 'Catalogue Tarifaire',
    title: 'Publiez vos forfaits et actes niveau 3',
    desc: 'Définissez votre grille tarifaire, vos conventionnements assurances et composez des panels de santé attractifs.',
    points: ['Gestion simplifiée des forfaits', 'Visibilité auprès de milliers de patients', 'Respect de la déontologie médicale'],
    icon: 'ti-packages',
  },
  {
    num: '03',
    label: 'Patients Qualifiés',
    title: 'Accueillez des patients informés',
    desc: 'Recevez des demandes de devis et des rendez-vous clairs, avec des patients qui connaissent déjà vos tarifs et vos conditions de prise en charge.',
    points: ['Réduction des abandons au guichet', 'Optimisation du planning de consultations', 'Tableau de bord de suivi d’activité'],
    icon: 'ti-user-check',
  },
];

export function HowItWorksPage() {
  const [profile, setProfile] = useState<'patient' | 'soignant'>('patient');

  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b1120] text-gray-900 dark:text-gray-100">
      {/* ── 1. HERO ──────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-16 pb-20 bg-gradient-to-br from-[#0a2540] via-[#123a63] to-[#1a5276] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#0ea5e9]/20 border border-[#0ea5e9]/40 text-[#0ea5e9] text-xs font-black uppercase tracking-wider mb-6">
            <span className="w-2 h-2 rounded-full bg-[#0ea5e9] animate-ping"></span>
            Guide Pratique
          </div>

          <h1 className="font-syne font-black text-3xl sm:text-5xl text-white leading-tight mb-4 max-w-3xl mx-auto">
            Trouvez, comparez,{' '}
            <span className="text-[#0ea5e9]">réservez vos examens.</span>
          </h1>

          <p className="text-base sm:text-lg text-sky-100/90 leading-relaxed max-w-2xl mx-auto mb-10 font-medium">
            De la recherche d'un acte à la confirmation du rendez-vous — un parcours clair, sans intermédiaire et sans commission.
          </p>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mx-auto p-4 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20">
            <div>
              <div className="font-syne font-black text-2xl text-white">450+</div>
              <div className="text-[11px] font-bold text-sky-200 uppercase">Actes</div>
            </div>
            <div>
              <div className="font-syne font-black text-2xl text-white">16</div>
              <div className="text-[11px] font-bold text-sky-200 uppercase">Structures</div>
            </div>
            <div>
              <div className="font-syne font-black text-2xl text-white">6</div>
              <div className="text-[11px] font-bold text-sky-200 uppercase">Piliers</div>
            </div>
            <div>
              <div className="font-syne font-black text-2xl text-[#0ea5e9]">0 %</div>
              <div className="text-[11px] font-bold text-sky-200 uppercase">Commission</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. PROFILE SWITCHER ──────────────────────────────────────── */}
      <section className="py-8 bg-white dark:bg-[#0f172a] border-b border-gray-200 dark:border-gray-800 sticky top-18 z-30 shadow-sm">
        <div className="max-w-md mx-auto px-4 flex justify-center">
          <div className="grid grid-cols-2 p-1.5 rounded-2xl bg-gray-100 dark:bg-gray-800 w-full">
            <button
              type="button"
              onClick={() => setProfile('patient')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all ${
                profile === 'patient'
                  ? 'bg-white dark:bg-gray-700 text-[#123a63] dark:text-[#0ea5e9] shadow-md'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              <i className="ti ti-search text-base"></i>
              <span>Je suis patient</span>
            </button>

            <button
              type="button"
              onClick={() => setProfile('soignant')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all ${
                profile === 'soignant'
                  ? 'bg-white dark:bg-gray-700 text-[#123a63] dark:text-emerald-400 shadow-md'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              <i className="ti ti-building-hospital text-base"></i>
              <span>Je suis soignant / structure</span>
            </button>
          </div>
        </div>
      </section>

      {/* ── 3. STEPS CONTAINER ───────────────────────────────────────── */}
      <section className="py-16 max-w-5xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-12">
          <span className="text-xs font-black uppercase tracking-wider text-[#0ea5e9]">
            {profile === 'patient' ? 'Parcours Patient Simplifié' : 'Parcours Professionnel'}
          </span>
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-[#0f172a] dark:text-white mt-1">
            {profile === 'patient'
              ? 'Du symptôme au rendez-vous en 5 étapes'
              : 'Développez votre visibilité médicale'}
          </h2>
        </div>

        <div className="space-y-6">
          {(profile === 'patient' ? PATIENT_STEPS : SOIGNANT_STEPS).map((step, idx) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-[#0f172a] border border-gray-200 dark:border-gray-800 shadow-sm flex flex-col md:flex-row md:items-start gap-6"
            >
              <div className="flex md:flex-col items-center gap-3 shrink-0">
                <span className="font-syne font-black text-2xl sm:text-3xl text-[#0ea5e9]">
                  {step.num}
                </span>
                <div className="w-12 h-12 rounded-2xl bg-[#0a5c8a]/10 dark:bg-sky-500/10 text-[#0a5c8a] dark:text-[#0ea5e9] flex items-center justify-center text-xl">
                  <i className={`ti ${step.icon}`}></i>
                </div>
              </div>

              <div className="flex-1">
                <span className="text-[11px] font-extrabold text-gray-400 uppercase tracking-wider">
                  {step.label}
                </span>
                <h3 className="font-syne font-bold text-lg sm:text-xl text-[#0f172a] dark:text-white mt-0.5 mb-2">
                  {step.title}
                </h3>
                <p className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 leading-relaxed font-medium mb-4">
                  {step.desc}
                </p>

                <div className="flex flex-wrap gap-2">
                  {step.points.map((pt) => (
                    <span
                      key={pt}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                    >
                      <i className="ti ti-check text-xs"></i>
                      {pt}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="mt-12 text-center">
          <Link
            to={profile === 'patient' ? '/search' : '/register'}
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white font-syne font-extrabold text-sm shadow-lg hover:brightness-105 transition-all"
          >
            <span>{profile === 'patient' ? 'Commencer ma recherche' : 'Inscrire mon établissement'}</span>
            <i className="ti ti-arrow-right"></i>
          </Link>
        </div>
      </section>
    </div>
  );
}
