import { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Navigation, Heart, Shield, Activity, Compass } from 'lucide-react';
import { SearchCardMobile } from '../components/search/SearchCardMobile';
import { SearchResult } from '../lib/api';
import { useGeoLocation } from '../hooks/useGeoLocation';

const MOCK_MOBILE_RESULTS: SearchResult[] = [
  {
    id: 1,
    nom: 'Hôpital Principal de Dakar',
    type: 'Hôpital Public',
    ville: 'Dakar-Plateau',
    distance_km: 0.8,
    note_moyenne: 4.8,
    price_min: 15000,
    price_max: 45000,
    actes: ['Urgences 24/7', 'Consultation Générale', 'Laboratoire'],
  },
  {
    id: 2,
    nom: 'Clinique de la Madeleine',
    type: 'Clinique Privée',
    ville: 'Dakar-Plateau',
    distance_km: 1.4,
    note_moyenne: 4.6,
    price_min: 25000,
    price_max: 95000,
    actes: ['Cardiologie', 'Maternité', 'Chirurgie'],
  },
  {
    id: 4,
    nom: 'Laboratoire Bio-Santé Almadies',
    type: 'Laboratoire',
    ville: 'Les Almadies',
    distance_km: 3.2,
    note_moyenne: 4.9,
    price_min: 12000,
    price_max: 38000,
    actes: ['Bilan Sanguin', 'Test COVID/Paludisme'],
  },
];

const QUICK_CATEGORIES = [
  { label: 'Urgences', icon: '🚨', active: true },
  { label: 'Consultation', icon: '🩺' },
  { label: 'Laboratoire', icon: '🧪' },
  { label: 'Pharmacie', icon: '💊' },
  { label: 'Imagerie', icon: '🩻' },
];

export function PatientMobilePage() {
  const geo = useGeoLocation();
  const [activeTab, setActiveTab] = useState<'proximite' | 'tarifs' | 'assurances'>('proximite');

  return (
    <div className="max-w-md mx-auto min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      {/* Mobile Header */}
      <div className="bg-gradient-to-br from-navy via-navy to-navyLight text-white p-5 rounded-b-3xl shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center font-bold font-syne">
              M
            </div>
            <span className="font-syne font-bold text-base">MedCare Mobile</span>
          </div>
          <button
            onClick={() => geo.request()}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 hover:bg-white/25 text-xs font-semibold backdrop-blur-sm transition-colors"
          >
            <Navigation size={12} className={geo.loading ? 'animate-spin' : ''} />
            {geo.lat ? 'Actualisé' : 'Me localiser'}
          </button>
        </div>

        <h2 className="font-syne font-extrabold text-2xl leading-tight">
          Soins de santé à proximité
        </h2>
        <p className="text-xs text-white/70 mt-1">
          Dakar & Régions • Prix transparents • Accès rapide
        </p>

        {/* Quick category scroll */}
        <div className="flex gap-2 overflow-x-auto pt-4 no-scrollbar">
          {QUICK_CATEGORIES.map((cat) => (
            <button
              key={cat.label}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                cat.active
                  ? 'bg-accent text-white shadow-sm'
                  : 'bg-white/10 text-white/80 hover:bg-white/20'
              }`}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Segmented control tabs */}
      <div className="px-4 mt-4">
        <div className="grid grid-cols-3 p-1 rounded-xl bg-gray-200/70 dark:bg-gray-800 text-xs font-semibold">
          {(['proximite', 'tarifs', 'assurances'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 rounded-lg capitalize transition-all ${
                activeTab === tab
                  ? 'bg-white dark:bg-gray-700 text-navy dark:text-accent shadow-sm'
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {tab === 'proximite' ? '📍 Proximité' : tab === 'tarifs' ? '🏷️ Tarifs' : '🛡️ Tiers-Payant'}
            </button>
          ))}
        </div>
      </div>

      {/* Main card list */}
      <div className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between text-xs font-semibold text-gray-400 uppercase tracking-wider">
          <span>Structures les plus proches</span>
          <span>{MOCK_MOBILE_RESULTS.length} trouvées</span>
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
