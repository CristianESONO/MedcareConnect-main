import { Link } from 'react-router-dom';

const PILLARS = [
  {
    icon: 'ti-certificate',
    title: 'Vérification rigoureuse',
    description:
      'Chaque établissement doit fournir ses agréments officiels. Nos équipes vérifient manuellement l’existence légale de chaque centre avant toute publication.',
  },
  {
    icon: 'ti-refresh',
    title: 'Transparence des prix',
    description:
      'Les tarifs sont déclarés par les structures sous leur responsabilité. Nous exigeons une mise à jour régulière pour garantir des devis précis et fiables.',
  },
  {
    icon: 'ti-shield-lock',
    title: 'Protection des données',
    description:
      'Nous respectons la loi sénégalaise sur la protection des données (CDP). Vos informations ne sont jamais partagées sans votre accord explicite.',
  },
  {
    icon: 'ti-eye',
    title: 'Neutralité éditoriale',
    description:
      'MedCare n’oriente aucun patient vers un prestataire particulier. Chaque résultat est affiché de manière neutre, sans favoritisme commercial.',
  },
  {
    icon: 'ti-currency-dollar',
    title: 'Zéro commission',
    description:
      'Nous ne prélevons aucune commission sur vos actes médicaux. Le prix affiché est celui que vous payez directement à la structure de santé.',
  },
  {
    icon: 'ti-device-mobile',
    title: 'Accessibilité totale',
    description:
      'La plateforme est accessible gratuitement, sans inscription, sur tous les appareils — pour que chaque patient puisse exercer son droit à l’information.',
  },
];

const PROCESS = [
  {
    icon: 'ti-file-check',
    title: 'Inscription vérifiée',
    description: 'Chaque structure soumet ses agréments et documents officiels lors de l’inscription sur la plateforme.',
  },
  {
    icon: 'ti-users-check',
    title: 'Contrôle manuel',
    description: 'Notre équipe valide chaque dossier avant la publication. Aucune structure n’est publiée sans validation interne.',
  },
  {
    icon: 'ti-calendar-check',
    title: 'Mises à jour régulières',
    description: 'Les structures sont notifiées pour actualiser leurs tarifs et informations tous les 3 mois minimum.',
  },
  {
    icon: 'ti-star',
    title: 'Badge de confiance',
    description: 'Les établissements conformes reçoivent le badge « Vérifié » visible sur toutes leurs fiches publiques.',
  },
];

export function TrustPage() {
  return (
    <div className="min-h-screen bg-[#f4f7fb] text-gray-900">
      <section className="relative overflow-hidden bg-gradient-to-br from-[#0d1b4b] via-[#153c58] to-[#1a5276] px-4 py-20 text-center text-white sm:py-24">
        <div className="pointer-events-none absolute inset-0 opacity-[0.04]" style={{ backgroundImage: 'radial-gradient(#00e8ff 1px, transparent 1px)', backgroundSize: '36px 36px' }} />
        <div className="relative mx-auto max-w-3xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-cyan-200">
            <i className="ti ti-shield-check" aria-hidden="true" />
            Charte de confiance MedCare
          </div>
          <h1 className="font-syne text-4xl font-black leading-tight text-white sm:text-6xl">
            Votre confiance,<br /><span className="bg-gradient-to-r from-cyan-300 to-sky-300 bg-clip-text text-transparent">notre priorité.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-white/75 sm:text-lg">
            Découvrez comment nous garantissons la fiabilité, la sécurité et la transparence de chaque donnée de santé sur notre plateforme.
          </p>
        </div>
      </section>

      <section className="border-b border-[#d4deee] bg-white" aria-label="Engagements en chiffres">
        <div className="mx-auto grid max-w-4xl grid-cols-1 divide-y divide-[#d4deee] px-6 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          {[
            ['100%', 'Structures vérifiées manuellement'],
            ['0%', 'Commission sur les actes'],
            ['24/7', 'Disponibilité de la plateforme'],
          ].map(([value, label], index) => (
            <div className="px-5 py-7 text-center" key={label}>
              <div className={`font-syne text-3xl font-black ${index !== 1 ? 'text-[#4fa3c7]' : 'text-[#0d1b4b]'}`}>{value}</div>
              <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider text-gray-500">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="px-4 py-16 sm:py-20">
        <div className="mx-auto max-w-6xl">
          <header className="mx-auto mb-12 max-w-2xl text-center">
            <span className="inline-flex rounded-full border border-[#4fa3c7]/30 bg-[#4fa3c7]/10 px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-[#287a9e]">Nos engagements</span>
            <h2 className="mt-4 font-syne text-3xl font-black text-[#0d1b4b] sm:text-4xl">Les piliers de notre confiance</h2>
            <p className="mt-3 leading-relaxed text-gray-600">Chaque donnée publiée sur MedCare repose sur des processus rigoureux de vérification et de mise à jour.</p>
          </header>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {PILLARS.map((pillar) => (
              <article className="group rounded-3xl border border-[#d4deee] bg-white p-7 text-center shadow-sm transition hover:-translate-y-1 hover:shadow-xl" key={pillar.title}>
                <div className="mx-auto mb-5 grid h-16 w-16 place-items-center rounded-2xl border border-[#4fa3c7]/20 bg-gradient-to-br from-[#4fa3c7]/15 to-[#123a63]/10 text-3xl text-[#4fa3c7] transition group-hover:scale-105">
                  <i className={`ti ${pillar.icon}`} aria-hidden="true" />
                </div>
                <h3 className="font-syne text-lg font-bold text-[#0d1b4b]">{pillar.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-gray-600">{pillar.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white px-4 py-12 sm:py-16">
        <div className="mx-auto grid max-w-5xl items-center gap-8 rounded-3xl bg-gradient-to-br from-[#4fa3c7] to-[#0d1b4b] p-8 text-white shadow-xl sm:grid-cols-[auto_1fr] sm:gap-10 sm:p-12">
          <div className="mx-auto grid h-24 w-24 place-items-center rounded-3xl border-2 border-white/30 bg-white/15 text-5xl backdrop-blur">
            <i className="ti ti-rosette-check" aria-hidden="true" />
          </div>
          <div>
            <h2 className="font-syne text-2xl font-black sm:text-3xl">Le Badge « Vérifié » MedCare</h2>
            <p className="mt-3 leading-relaxed text-white/85">
              Ce badge est attribué aux structures ayant complété l’intégralité de leur profil, fourni tous leurs justificatifs légaux et dont les tarifs ont été mis à jour il y a moins de 3 mois. C’est notre garantie de qualité, visible sur toutes leurs fiches publiques.
            </p>
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-gradient-to-br from-[#0d1b4b] to-[#152260] px-4 py-16 text-white sm:py-20">
        <div className="mx-auto max-w-6xl">
          <header className="mx-auto mb-12 max-w-2xl text-center">
            <span className="inline-flex rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-cyan-200">Notre processus</span>
            <h2 className="mt-4 font-syne text-3xl font-black text-white sm:text-4xl">Comment nous garantissons la fiabilité</h2>
            <p className="mt-3 leading-relaxed text-white/65">Un processus en 4 étapes pour vous assurer des données de qualité à chaque instant.</p>
          </header>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {PROCESS.map((step) => (
              <article className="rounded-3xl border border-white/10 bg-white/[0.06] p-7 text-center transition hover:border-cyan-300/30 hover:bg-cyan-300/10" key={step.title}>
                <div className="mx-auto mb-5 grid h-16 w-16 place-items-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-3xl text-cyan-200">
                  <i className={`ti ${step.icon}`} aria-hidden="true" />
                </div>
                <h3 className="font-syne font-bold text-white">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/60">{step.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-16 text-center sm:py-20">
        <div className="mx-auto max-w-2xl">
          <span className="inline-flex rounded-full border border-[#4fa3c7]/30 bg-[#4fa3c7]/10 px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-[#287a9e]">Support</span>
          <h2 className="mt-4 font-syne text-3xl font-black text-[#0d1b4b]">Une question sur nos processus ?</h2>
          <p className="mt-3 leading-relaxed text-gray-600">
            Notre équipe est à votre disposition pour vous apporter toutes les précisions nécessaires sur notre charte de confiance et notre engagement qualité.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/contact/" className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#0d1b4b] to-[#153c58] px-7 py-4 font-bold text-white shadow-lg transition hover:-translate-y-0.5">
              <i className="ti ti-mail" aria-hidden="true" />Contacter le support
            </Link>
            <Link to="/a-propos/" className="inline-flex items-center gap-2 rounded-xl border-2 border-[#d4deee] px-7 py-4 font-semibold text-[#0d1b4b] transition hover:border-[#4fa3c7] hover:bg-[#4fa3c7]/5">
              <i className="ti ti-info-circle" aria-hidden="true" />À propos de MedCare
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
