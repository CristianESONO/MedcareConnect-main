import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

const STATS = [
  { val: '450+', label: 'Actes Médicaux', icon: 'ti-receipt' },
  { val: '16', label: 'Structures Partenaires', icon: 'ti-building-hospital' },
  { val: '6', label: 'Piliers Paracliniques', icon: 'ti-packages' },
  { val: '0 %', label: 'Commission Patient', icon: 'ti-percentage', accent: true },
];

const VALUES = [
  {
    icon: 'ti-eye-check',
    title: 'Transparence Radicale',
    desc: 'Prix réels affichés avant le rendez-vous, conventionnements IPM explicites, délais d’attente constatés. Aucune mauvaise surprise au guichet.',
  },
  {
    icon: 'ti-shield-lock',
    title: 'Rigueur & Déontologie',
    desc: 'Pas de classement publicitaire, pas de promotion commerciale. La présentation des structures et des soignants respecte scrupuleusement le code de déontologie.',
  },
  {
    icon: 'ti-map-pin',
    title: 'Proximité & Accessibilité',
    desc: 'Le bon soin, au bon endroit, au bon coût. Nous rapprochons les patients des laboratoires, cliniques et centres d’imagerie partout à Dakar et dans les régions.',
  },
];

export function AboutPage() {
  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b1120] text-gray-900 dark:text-gray-100">
      {/* ── 1. HERO BANNER ────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-16 pb-20 bg-gradient-to-br from-[#0a2540] via-[#123a63] to-[#1a5276] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-3xl">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#0ea5e9]/20 border border-[#0ea5e9]/40 text-[#0ea5e9] text-xs font-black uppercase tracking-wider mb-6"
            >
              <span className="w-2 h-2 rounded-full bg-[#0ea5e9] animate-ping"></span>
              À propos de MedCare
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="font-syne font-black text-3xl sm:text-5xl text-white leading-tight mb-4"
            >
              L’accès aux soins,{' '}
              <span className="text-[#0ea5e9]">sans opacité ni frontière.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-base sm:text-lg text-sky-100/90 leading-relaxed font-medium"
            >
              MedCare Connect est la première plateforme paraclinique digitale du Sénégal, conçue pour unifier l’information médicale, éclairer le choix des patients et moderniser l’offre des praticiens.
            </motion.p>
          </div>
        </div>
      </section>

      {/* ── 2. STATS BAR ──────────────────────────────────────────────── */}
      <section className="bg-white dark:bg-[#0f172a] border-b border-gray-200 dark:border-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-gray-200 dark:divide-gray-800">
            {STATS.map((s) => (
              <div key={s.label} className="p-6 text-center">
                <div
                  className={`font-syne font-black text-3xl sm:text-4xl ${
                    s.accent ? 'text-[#0ea5e9]' : 'text-[#123a63] dark:text-white'
                  }`}
                >
                  {s.val}
                </div>
                <div className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mt-1">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. VISION & MANIFESTE ─────────────────────────────────────── */}
      <section className="py-16 sm:py-20 max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7 space-y-4">
            <span className="text-xs font-extrabold uppercase tracking-widest text-[#0ea5e9]">
              Notre Vision
            </span>
            <h2 className="font-syne font-extrabold text-2xl sm:text-4xl text-[#0f172a] dark:text-white leading-tight">
              Redéfinir le parcours de soins au Sénégal
            </h2>
            <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
              Chaque jour, des milliers de personnes parcourent les rues de Dakar à la recherche d’un examen médical disponible, comparent à l’aveugle des tarifs souvent introuvables et découvrent au comptoir que leur mutuelle n’est pas acceptée.
            </p>
            <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
              MedCare est né d’une conviction fondamentale : <strong>l’information médicale n’est pas un luxe, c’est le premier acte du soin.</strong> En répertoriant rigoureusement les actes, les prix réels et les disponibilités des structures de santé agréées, nous redonnons le pouvoir au patient.
            </p>
          </div>

          <div className="lg:col-span-5">
            <div className="p-8 sm:p-10 rounded-3xl bg-gradient-to-br from-[#123a63] to-[#0a2540] text-white shadow-xl relative overflow-hidden">
              <span className="text-6xl font-serif text-[#0ea5e9]/30 absolute top-2 left-4 select-none pointer-events-none">
                “
              </span>
              <div className="text-xs font-bold uppercase tracking-widest text-[#0ea5e9] mb-3">
                Le Manifeste MedCare
              </div>
              <p className="text-sm sm:text-base italic text-sky-100 leading-relaxed relative z-10 font-medium">
                « Un patient averti est un patient soigné plus vite. Notre mission est d’éliminer l’incertitude financière et logistique pour que chacun puisse se concentrer sur l'essentiel : sa guérison. »
              </p>
              <div className="mt-6 pt-4 border-t border-white/15 text-xs text-sky-200 font-bold">
                L’équipe de direction MedCare Connect Sénégal
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. NOS VALEURS ────────────────────────────────────────────── */}
      <section className="py-16 bg-white dark:bg-[#0f172a] border-y border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-extrabold uppercase tracking-widest text-[#0ea5e9]">
              Nos Principes Fondateurs
            </span>
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-[#0f172a] dark:text-white mt-1">
              Des valeurs ancrées dans la confiance
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {VALUES.map((val) => (
              <div
                key={val.title}
                className="p-7 rounded-3xl bg-[#f8fafc] dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="w-12 h-12 rounded-2xl bg-[#0a5c8a]/10 dark:bg-sky-500/10 text-[#0a5c8a] dark:text-[#0ea5e9] flex items-center justify-center text-2xl mb-4">
                    <i className={`ti ${val.icon}`}></i>
                  </div>
                  <h3 className="font-syne font-bold text-lg text-[#0f172a] dark:text-white mb-2">
                    {val.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-300 leading-relaxed font-medium">
                    {val.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. CALL TO ACTION ─────────────────────────────────────────── */}
      <section className="py-16 max-w-7xl mx-auto px-4 sm:px-6 text-center">
        <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-[#0f172a] dark:text-white mb-3">
          Prêt à simplifier vos démarches de santé ?
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 max-w-lg mx-auto mb-8 font-medium">
          Rejoignez des milliers de patients et de soignants qui font confiance à MedCare au Sénégal.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            to="/search"
            className="px-6 py-3 rounded-xl bg-[#123a63] hover:bg-[#1a4f87] text-white font-bold text-xs shadow-md transition-all"
          >
            Rechercher un examen médical
          </Link>
          <Link
            to="/register"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white font-bold text-xs shadow-md transition-all"
          >
            Rejoindre MedCare en tant que soignant
          </Link>
        </div>
      </section>
    </div>
  );
}
