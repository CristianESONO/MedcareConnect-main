import { useState } from 'react';
import { Plus, X, Search, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Panel } from '../../lib/api';

interface ActeItem {
  id: number;
  nom: string;
  price: number;
}

interface PanelBuilderProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Omit<Panel, 'id'>) => void;
  availableActs?: ActeItem[];
}

export function PanelBuilder({ open, onClose, onSave, availableActs = [] }: PanelBuilderProps) {
  const [nom, setNom] = useState('');
  const [description, setDescription] = useState('');
  const [selectedActs, setSelectedActs] = useState<ActeItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredAvailable = availableActs.filter((a) =>
    a.nom.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleSelectAct = (acte: ActeItem) => {
    if (selectedActs.some((a) => a.id === acte.id)) {
      setSelectedActs(selectedActs.filter((a) => a.id !== acte.id));
    } else {
      setSelectedActs([...selectedActs, acte]);
    }
  };

  const handleSave = () => {
    if (!nom.trim()) return;
    onSave({
      nom: nom.trim(),
      description: description.trim(),
      actes: selectedActs,
    });
    // Reset
    setNom('');
    setDescription('');
    setSelectedActs([]);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Créer un Panel d'Actes" className="max-w-2xl">
      <div className="flex flex-col gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            Nom du panel *
          </label>
          <Input
            placeholder="Ex: Bilan Sanguin Complet, Pack Maternité..."
            value={nom}
            onChange={(e) => setNom(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            rows={2}
            className="w-full rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-white placeholder-gray-400 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
            placeholder="Détails du forfait ou consignes pour le patient..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Selected Acts Badge List */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            Actes sélectionnés ({selectedActs.length})
          </label>
          <div className="min-h-[48px] p-2 rounded-xl bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 flex flex-wrap gap-1.5 items-center">
            {selectedActs.length === 0 ? (
              <span className="text-xs text-gray-400 italic">
                Sélectionnez uniquement les actes exécutables ci-dessous (niveau 3)
              </span>
            ) : (
              selectedActs.map((acte) => (
                <span
                  key={acte.id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-navy/10 dark:bg-navy/30 text-navy dark:text-accent text-xs font-medium"
                >
                  {acte.nom}
                  <button
                    onClick={() => toggleSelectAct(acte)}
                    className="hover:text-red-500 transition-colors"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))
            )}
          </div>
        </div>

        {/* Acts Picker: Level 3 acts only */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            Ajouter des actes médicaux
          </label>
          <Input
            icon={<Search size={15} />}
            placeholder="Filtrer parmi les actes médicaux..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="mb-2"
          />

          <div className="max-h-48 overflow-y-auto rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700/50">
            {filteredAvailable.map((acte) => {
              const selected = selectedActs.some((a) => a.id === acte.id);
              return (
                <div
                  key={acte.id}
                  onClick={() => toggleSelectAct(acte)}
                  className={`p-2.5 flex items-center justify-between text-xs cursor-pointer transition-colors ${
                    selected
                      ? 'bg-accent/10 text-accent font-semibold'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-750 text-gray-700 dark:text-gray-300'
                  }`}
                >
                  <span>{acte.nom}</span>
                  <div className="flex items-center gap-2">
                    {acte.price > 0 && (
                      <span className="text-gray-400">{acte.price.toLocaleString()} FCFA</span>
                    )}
                    {selected ? (
                      <Check size={14} className="text-accent" />
                    ) : (
                      <Plus size={14} className="text-gray-400" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-700">
          <Button variant="secondary" size="md" onClick={onClose}>
            Annuler
          </Button>
          <Button size="md" onClick={handleSave} disabled={!nom.trim()}>
            Créer le panel
          </Button>
        </div>
      </div>
    </Modal>
  );
}
