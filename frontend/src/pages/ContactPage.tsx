import { useState } from 'react';
import { motion } from 'framer-motion';

export function ContactPage() {
  const [nom, setNom] = useState('');
  const [email, setEmail] = useState('');
  const [typeUser, setTypeUser] = useState('Un Patient');
  const [message, setMessage] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSent(true);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b1120] text-gray-900 dark:text-gray-100">
      {/* ── 1. HERO ──────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-16 pb-18 bg-gradient-to-br from-[#0a2540] via-[#123a63] to-[#1a5276] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#0ea5e9]/20 border border-[#0ea5e9]/40 text-[#0ea5e9] text-xs font-black uppercase tracking-wider mb-5">
            <span className="w-2 h-2 rounded-full bg-[#0ea5e9] animate-ping"></span>
            Support & Écoute
          </div>

          <h1 className="font-syne font-black text-3xl sm:text-5xl text-white leading-tight mb-3">
            Parlons de votre santé.
          </h1>
          <p className="text-base sm:text-lg text-sky-100/90 leading-relaxed max-w-xl mx-auto font-medium">
            Une question ? Un partenariat ? Notre équipe est à votre écoute pour vous accompagner partout au Sénégal.
          </p>
        </div>
      </section>

      {/* ── 2. CONTACT GRID ──────────────────────────────────────────── */}
      <section className="py-16 max-w-6xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* Left Info Column */}
          <div className="lg:col-span-5 space-y-6">
            <div>
              <span className="text-xs font-extrabold uppercase tracking-widest text-[#0ea5e9]">
                Coordonnées Officielles
              </span>
              <h2 className="font-syne font-extrabold text-2xl text-[#0f172a] dark:text-white mt-1">
                Nous sommes à votre <span className="text-[#0ea5e9]">écoute</span>
              </h2>
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-2 font-medium leading-relaxed">
                Que vous soyez un patient ayant besoin d'assistance pour localiser un soin ou un professionnel souhaitant adhérer au réseau, n'hésitez pas à nous joindre.
              </p>
            </div>

            <div className="space-y-4">
              {/* Email */}
              <div className="flex items-start gap-4 p-4 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="p-3 rounded-xl bg-sky-50 dark:bg-sky-950/40 text-[#0ea5e9] text-xl shrink-0">
                  <i className="ti ti-mail"></i>
                </div>
                <div>
                  <h4 className="font-syne font-bold text-sm text-[#0f172a] dark:text-white">
                    Email de Support
                  </h4>
                  <p className="text-sm font-semibold text-[#123a63] dark:text-[#0ea5e9]">
                    contact@medcare.sn
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Réponse garantie sous 24h ouvrées.</p>
                </div>
              </div>

              {/* WhatsApp */}
              <div className="flex items-start gap-4 p-4 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 text-xl shrink-0">
                  <i className="ti ti-brand-whatsapp"></i>
                </div>
                <div>
                  <h4 className="font-syne font-bold text-sm text-[#0f172a] dark:text-white">
                    WhatsApp Direct
                  </h4>
                  <a
                    href="https://wa.me/221781673189"
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-semibold text-emerald-700 dark:text-emerald-400 hover:underline block"
                  >
                    +221 78 167 31 89
                  </a>
                  <p className="text-xs text-gray-500 mt-0.5">Disponible du lundi au samedi (8h - 20h).</p>
                </div>
              </div>

              {/* Siège social */}
              <div className="flex items-start gap-4 p-4 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="p-3 rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xl shrink-0">
                  <i className="ti ti-map-pin"></i>
                </div>
                <div>
                  <h4 className="font-syne font-bold text-sm text-[#0f172a] dark:text-white">
                    Siège Social
                  </h4>
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                    Point E, Dakar
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Sénégal</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Form Card */}
          <div className="lg:col-span-7">
            <div className="p-6 sm:p-9 rounded-3xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-xl">
              <h3 className="font-syne font-extrabold text-xl text-[#0f172a] dark:text-white mb-1">
                Envoyez-nous un message
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-6 font-medium">
                Remplissez ce formulaire et notre équipe vous recontactera rapidement.
              </p>

              {sent ? (
                <div className="py-12 text-center">
                  <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-3xl mx-auto mb-4">
                    <i className="ti ti-circle-check"></i>
                  </div>
                  <h4 className="font-syne font-bold text-xl text-gray-900 dark:text-white">
                    Message envoyé avec succès !
                  </h4>
                  <p className="text-xs text-gray-500 mt-2 max-w-sm mx-auto">
                    Merci d'avoir contacté MedCare Connect. Un conseiller vous répondra dans les plus brefs délais.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setSent(false);
                      setNom('');
                      setEmail('');
                      setMessage('');
                    }}
                    className="mt-6 px-6 py-2.5 rounded-xl bg-[#123a63] text-white font-bold text-xs shadow-md"
                  >
                    Envoyer un autre message
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Nom complet *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Ex : Moussa Diop"
                      value={nom}
                      onChange={(e) => setNom(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Adresse Email *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="votre@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Vous êtes
                    </label>
                    <select
                      value={typeUser}
                      onChange={(e) => setTypeUser(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm"
                    >
                      <option>Un Patient</option>
                      <option>Un Professionnel de santé</option>
                      <option>Une Clinique / Hôpital / Laboratoire</option>
                      <option>Un Partenaire (Assurance / IPM)</option>
                      <option>Autre</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                      Votre message *
                    </label>
                    <textarea
                      required
                      rows={5}
                      placeholder="Comment pouvons-nous vous aider ?"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
                    ></textarea>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#0a5c8a] to-[#0d9488] text-white font-syne font-extrabold text-sm shadow-md hover:brightness-105 active:scale-[0.99] transition-all cursor-pointer"
                  >
                    Envoyer le message →
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
