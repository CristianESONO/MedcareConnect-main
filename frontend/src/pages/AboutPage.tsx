import './aboutPage.css';
import { Link } from 'react-router-dom';

export function AboutPage() {
  return (
    <div className="mc-about-page min-h-screen bg-white dark:bg-[#0b1120] text-[#123a63] dark:text-gray-100 font-sans">
      {/* ── 1. Hero ── */}
      <section className="relative overflow-hidden pt-20 pb-16 bg-gradient-to-br from-[#0a2540] via-[#123a63] to-[#1a5276] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#4fa3c7]/15 border border-[#4fa3c7]/35 text-[#4fa3c7] text-xs font-bold uppercase tracking-wider mb-5">
              <span className="w-2 h-2 rounded-full bg-[#4fa3c7] animate-pulse"></span>
              Sénégal · Santé digitale
            </div>
            <h1 className="font-syne font-black text-3xl sm:text-5xl text-white leading-tight mb-4" style={{ color: '#fff' }}>
              Organiser l'offre de soins,<br />
              <em className="italic not-italic text-[#4fa3c7]">pour tous.</em>
            </h1>
            <p className="text-base sm:text-lg text-white/80 leading-relaxed font-medium">
              Medcare est la première plateforme digitale dédiée à la transparence et à l'accessibilité des services médicaux au Sénégal.
            </p>
          </div>
        </div>
      </section>

      {/* ── 2. Stats ── */}
      <section className="bg-white dark:bg-[#0f172a] border-b border-gray-200 dark:border-gray-800 shadow-sm" aria-label="Chiffres clés">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-gray-200 dark:divide-gray-800">
            <div className="p-8 text-center">
              <div className="font-syne font-black text-3xl sm:text-4xl text-[#4fa3c7] mb-1">
                100+
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Structures référencées
              </div>
            </div>
            <div className="p-8 text-center">
              <div className="font-syne font-black text-3xl sm:text-4xl text-[#123a63] dark:text-white mb-1">
                5 000+
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Actes médicaux
              </div>
            </div>
            <div className="p-8 text-center">
              <div className="font-syne font-black text-3xl sm:text-4xl text-[#4fa3c7] mb-1">
                0%
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Commission sur les actes
              </div>
            </div>
            <div className="p-8 text-center">
              <div className="font-syne font-black text-3xl sm:text-4xl text-[#123a63] dark:text-white mb-1">
                24/7
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Accessibilité
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. Vision ── */}
      <section className="py-16 sm:py-20 bg-white dark:bg-[#0f172a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            <div className="lg:col-span-7 space-y-4">
              <h2 className="font-syne font-black text-2xl sm:text-4xl text-[#123a63] dark:text-white leading-tight">
                L'infrastructure digitale de la <em className="not-italic text-[#4fa3c7]">santé de demain.</em>
              </h2>
              <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
                Né d'un besoin de simplification, Medcare centralise l'offre de soins paracliniques (biologie, imagerie, explorations) pour permettre à chaque patient de trouver le bon examen, au bon prix et à proximité.
              </p>
              <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
                Nous croyons que la donnée médicale doit être structurée et accessible pour améliorer l'efficacité du système de santé sénégalais.
              </p>
            </div>

            <div className="lg:col-span-5">
              <div className="p-8 sm:p-10 rounded-3xl bg-gradient-to-br from-[#123a63] to-[#0a2540] text-white shadow-xl relative overflow-hidden">
                <span className="text-7xl font-serif text-[#4fa3c7]/20 absolute top-2 left-4 select-none pointer-events-none">
                  “
                </span>
                <h3 className="mc-about-vision-title text-xs font-bold uppercase tracking-wider mb-3">
                  Notre Vision
                </h3>
                <p className="text-base sm:text-lg italic text-white/90 leading-relaxed relative z-10">
                  Devenir la couche digitale de référence qui organise et structure l'offre de services médicaux à travers le continent africain.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. Valeurs ── */}
      <section className="py-16 sm:py-20 bg-gray-50 dark:bg-[#0b1120] border-y border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#4fa3c7]/10 text-[#4fa3c7] text-xs font-bold uppercase tracking-wider mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4fa3c7]"></span>
              Nos engagements
            </div>
            <h2 className="font-syne font-black text-2xl sm:text-3xl text-[#123a63] dark:text-white">
              Nos Valeurs Fondamentales
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 font-medium">
              Ce qui nous guide chaque jour dans le développement de la plateforme.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-8 rounded-3xl bg-white dark:bg-[#0f172a] border border-gray-200 dark:border-gray-800 shadow-sm text-center flex flex-col items-center">
              <div className="w-14 h-14 rounded-2xl bg-[#4fa3c7]/10 text-[#123a63] dark:text-[#4fa3c7] flex items-center justify-center text-2xl mb-5">
                <i className="ti ti-eye"></i>
              </div>
              <h3 className="font-syne font-bold text-lg text-[#123a63] dark:text-white mb-2">
                Transparence
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed font-medium">
                Nous luttons contre l'asymétrie d'information en affichant les tarifs réels et les conventions d'assurance en toute clarté.
              </p>
            </div>

            <div className="p-8 rounded-3xl bg-white dark:bg-[#0f172a] border border-gray-200 dark:border-gray-800 shadow-sm text-center flex flex-col items-center">
              <div className="w-14 h-14 rounded-2xl bg-[#4fa3c7]/10 text-[#123a63] dark:text-[#4fa3c7] flex items-center justify-center text-2xl mb-5">
                <i className="ti ti-users"></i>
              </div>
              <h3 className="font-syne font-bold text-lg text-[#123a63] dark:text-white mb-2">
                Équité
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed font-medium">
                Chaque patient, quel que soit son profil, doit pouvoir accéder aux meilleurs soins au meilleur prix disponible sur le marché.
              </p>
            </div>

            <div className="p-8 rounded-3xl bg-white dark:bg-[#0f172a] border border-gray-200 dark:border-gray-800 shadow-sm text-center flex flex-col items-center">
              <div className="w-14 h-14 rounded-2xl bg-[#4fa3c7]/10 text-[#123a63] dark:text-[#4fa3c7] flex items-center justify-center text-2xl mb-5">
                <i className="ti ti-shield-check"></i>
              </div>
              <h3 className="font-syne font-bold text-lg text-[#123a63] dark:text-white mb-2">
                Fiabilité
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed font-medium">
                Nous certifions les structures de santé présentes sur notre plateforme pour garantir la qualité et l'exactitude des données.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 5. Mission / CTA ── */}
      <section className="py-16 sm:py-20 bg-white dark:bg-[#0f172a]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#4fa3c7]/10 text-[#4fa3c7] text-xs font-bold uppercase tracking-wider mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4fa3c7]"></span>
            Notre mission
          </div>
          <h2 className="font-syne font-black text-2xl sm:text-4xl text-[#123a63] dark:text-white mb-4">
            Simplifier l'accès aux soins au Sénégal
          </h2>
          <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium mb-3">
            Medcare permet à chaque patient de rechercher, comparer et réserver des examens médicaux en quelques clics — sans intermédiaire, sans commission, avec une totale transparence sur les tarifs et la couverture assurance.
          </p>
          <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium mb-8">
            Nous accompagnons les structures de santé dans leur transformation numérique en leur fournissant des outils de gestion modernes et une visibilité nationale.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/sante/recherche/"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-gradient-to-r from-[#123a63] to-[#0a2540] text-white font-bold text-sm shadow-md hover:brightness-110 transition-all"
            >
              <i className="ti ti-search"></i>
              <span>Trouver un service</span>
            </Link>
            <Link
              to="/contact"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border-2 border-gray-300 dark:border-gray-700 text-[#123a63] dark:text-white font-bold text-sm hover:border-[#4fa3c7] transition-all"
            >
              <i className="ti ti-mail"></i>
              <span>Nous contacter</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
