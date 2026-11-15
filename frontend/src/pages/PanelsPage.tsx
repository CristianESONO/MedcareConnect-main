import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Layers, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PanelCard } from '../components/panels/PanelCard';
import { PanelBuilder } from '../components/panels/PanelBuilder';
import { Button } from '../components/ui/Button';
import { Panel } from '../lib/api';

const MOCK_AVAILABLE_ACTS = [
  { id: 101, nom: 'Hémogramme Complet (NFS)', price: 8000 },
  { id: 102, nom: 'Glycémie à jeun', price: 3500 },
  { id: 103, nom: 'Créatininémie', price: 4500 },
  { id: 104, nom: 'Bilan Lipidique (Cholestérol, Triglycérides)', price: 12000 },
  { id: 105, nom: 'Transaminases ASAT / ALAT', price: 7000 },
  { id: 106, nom: 'Échographie Abdomino-Pelvienne', price: 25000 },
  { id: 107, nom: 'Électrocardiogramme (ECG)', price: 15000 },
  { id: 108, nom: 'Radiographie du Thorax Face', price: 18000 },
];

const INITIAL_PANELS: Panel[] = [
  {
    id: 1,
    nom: 'Bilan de Santé Annuel Adulte',
    description: 'Forfait préventif complet incluant bilan sanguin, glycémie, créatinine et ECG de repos.',
    actes: [
      { id: 101, nom: 'Hémogramme Complet (NFS)', price: 8000 },
      { id: 102, nom: 'Glycémie à jeun', price: 3500 },
      { id: 104, nom: 'Bilan Lipidique', price: 12000 },
      { id: 107, nom: 'Électrocardiogramme (ECG)', price: 15000 },
    ],
  },
  {
    id: 2,
    nom: 'Pack Check-up Métabolique & Rénal',
    description: 'Surveillance ciblée du diabète, de la fonction rénale et hépatique.',
    actes: [
      { id: 102, nom: 'Glycémie à jeun', price: 3500 },
      { id: 103, nom: 'Créatininémie', price: 4500 },
      { id: 105, nom: 'Transaminases ASAT / ALAT', price: 7000 },
    ],
  },
];

export function PanelsPage() {
  const { t } = useTranslation();
  const [panels, setPanels] = useState<Panel[]>(INITIAL_PANELS);
  const [builderOpen, setBuilderOpen] = useState(false);

  const handleSavePanel = (newPanel: Omit<Panel, 'id'>) => {
    const created: Panel = {
      id: Date.now(),
      ...newPanel,
    };
    setPanels([created, ...panels]);
  };

  const handleDeletePanel = (id: number) => {
    if (confirm('Confirmer la suppression de ce panel ?')) {
      setPanels(panels.filter((p) => p.id !== id));
    }
  };

  return (
    <div className="min-h-screen py-8 px-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <span className="text-xs font-bold text-accent uppercase tracking-widest">
            Gestion des Tarifs & Forfaits
          </span>
          <h1 className="font-syne font-extrabold text-2xl sm:text-3xl text-navy dark:text-white mt-1">
            {t('panels.title')}
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            Regroupez plusieurs actes médicaux (niveau 3) en forfaits packagés pour les patients
          </p>
        </div>

        <Button size="md" onClick={() => setBuilderOpen(true)}>
          <Plus size={16} />
          <span>{t('panels.new_panel')}</span>
        </Button>
      </div>

      {/* Info Notice */}
      <div className="p-4 rounded-xl bg-accent/10 border border-accent/20 flex items-center gap-3 mb-6 text-xs text-navy dark:text-accent font-medium">
        <AlertCircle size={18} className="shrink-0" />
        <span>
          Conformément aux règles de tarification SIPN, seuls les actes médicaux élémentaires et exécutables (niveau 3) sont combinables dans un panel.
        </span>
      </div>

      {/* Panels Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {panels.map((panel, idx) => (
          <PanelCard
            key={panel.id}
            panel={panel}
            index={idx}
            onDelete={handleDeletePanel}
          />
        ))}
      </div>

      {/* Panel Builder Modal */}
      <PanelBuilder
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onSave={handleSavePanel}
        availableActs={MOCK_AVAILABLE_ACTS}
      />
    </div>
  );
}
