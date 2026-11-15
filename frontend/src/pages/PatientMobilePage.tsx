import { useState } from 'react';
import { SearchCardMobile } from '../components/search/SearchCardMobile';
import { type SearchResult } from '../lib/api';
import { useGeoLocation } from '../hooks/useGeoLocation';

const MOCK_MOBILE_RESULTS: SearchResult[] = [
  {
    id: 1,
    nom: 'Hôpital Principal de Dakar',
    type: 'Hôpital Militaire / Établissement Public',
    ville: 'Dakar-Plateau',
    distance_km: 0.8,
    note_moyenne: 4.8,
    price_min: 15000,
    price_max: 45000,
    actes: ['Urgences 24h/24', 'Consultation Générale', 'Laboratoire d\'Analyses'],
  },
  {
    id: 2,
    nom: 'Clinique de la Madeleine',
    type: 'Clinique Médico-Chirurgicale Privée',
    ville: 'Dakar-Plateau',
    distance_km: 1.4,
    note_moyenne: 4.6,
    price_min: 25000,
    price_max: 95000,
    actes: ['Cardiologie Interventionnelle', 'Maternité & Néonatalogie', 'Bloc Opératoire'],
  },
  {
    id: 4,
    nom: 'Laboratoire Bio-Santé Almadies',
    type: 'Laboratoire Médical Agréé',
    ville: 'Les Almadies',
    distance_km: 3.2,
    note_moyenne: 4.9,
    price_min: 12000,
    price_max: 38000,
    actes: ['Bilan Sanguin Complet (NFS)', 'Dépistage Rapide Paludisme'],
  },
];

const QUICK_CATEGORIES = [
  { label: 'Urgences', icon: 'ti-emergency-bed', active: true },
  { label: 'Consultations', icon: 'ti-stethoscope' },
  { label: 'Laboratoires', icon: 'ti-microscope' },
  { label: 'Pharmacies', icon: 'ti-pill' },
  { label: 'Imagerie', icon: 'ti-scan' },
];

export function PatientMobilePage() {
  const geo = useGeoLocation();
  const [activeTab, setActiveTab] = useState<'proximite' | 'tarifs' | 'assurances'>('proximite');

  return (
    <div className="sipn-prestations struct-list-m max-w-md mx-auto min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      {/* ── Mobile App Header ─────────────────────────────────────── */}
      <div className="bg-gradient-to-br from-[#123a63] via-[#123a63] to-[#1a4f87] text-white p-5 rounded-b-3xl shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center font-bold font-syne text-[#4fa3c7] text-base">
              M
            </div>
            <span className="font-syne font-extrabold text-base tracking-tight">MedCare Mobile</span>
          </div>

          <button
            type="button"
            onClick={() => geo.request()}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 hover:bg-white/25 text-xs font-bold backdrop-blur-md transition-all active:scale-95"
          >
            <i className={`ti ti-location ${geo.loading ? 'animate-spin' : ''}`}></i>
            {geo.lat ? 'Localisé' : 'Me localiser'}
          </button>
        </div>

        <h2 className="font-syne font-black text-2xl leading-tight text-white">
          Trouvez un soin à proximité
        </h2>
        <p className="text-xs text-white/70 mt-1">
          Dakar & Régions • Prix transparents • Tiers-Payant
        </p>

        {/* ── Category Quick Scroll ──────────────────────────────── */}
        <div className="flex gap-2 overflow-x-auto pt-4 no-scrollbar">
          {QUICK_CATEGORIES.map((cat) => (
            <button
              key={cat.label}
              type="button"
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all ${
                cat.active
                  ? 'bg-[#4fa3c7] text-white shadow-md'
                  : 'bg-white/10 text-white/80 hover:bg-white/20'
              }`}
            >
              <i className={`ti ${cat.icon}`}></i>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Segmented Control Tabs ──────────────────────────────── */}
      <div className="px-4 mt-4">
        <div className="grid grid-cols-3 p-1 rounded-xl bg-gray-200/70 dark:bg-gray-800 text-xs font-bold">
          {(['proximite', 'tarifs', 'assurances'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`py-2 rounded-lg capitalize transition-all ${
                activeTab === tab
                  ? 'bg-white dark:bg-gray-700 text-[#123a63] dark:text-[#4fa3c7] shadow-sm'
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {tab === 'proximite' ? '📍 Proximité' : tab === 'tarifs' ? '🏷️ Tarifs' : '🛡️ Mutuelles'}
            </button>
          ))}
        </div>
      </div>

      {/* ── Cards List (.scard-m) ────────────────────────────────── */}
      <div className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between text-xs font-bold text-gray-400 uppercase tracking-wider px-1">
          <span>Structures les plus proches</span>
          <span>{MOCK_MOBILE_RESULTS.length} résultats</span>
        </div>

        {MOCK_MOBILE_RESULTS.map((res, idx) => (
          <SearchCardMobile
            key={res.id}
            result={res}
            index={idx}
            onSelect={(r) => alert(`Fiche établissement : ${r.nom}`)}
          />
        ))}
      </div>
    </div>
  );
}
