import { useState } from 'react';
import { Plus, X, Search, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Panel, ProviderPanelAct } from '../../lib/api';

interface PanelBuilderProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: Omit<Panel, 'id'>) => Promise<void>;
  availableActs?: ProviderPanelAct[];
  initialPanel?: Panel | null;
}

export function PanelBuilder({ open, onClose, onSave, availableActs = [], initialPanel }: PanelBuilderProps) {
  const [nom, setNom] = useState(() => initialPanel?.nom ?? '');
  const [description, setDescription] = useState(() => initialPanel?.description ?? '');
  const [kind, setKind] = useState<'panel' | 'ticket'>(() => initialPanel?.kind ?? 'panel');
  const [selectedActs, setSelectedActs] = useState<ProviderPanelAct[]>(() => initialPanel?.actes ?? []);
  const [searchQuery, setSearchQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const filteredAvailable = availableActs.filter((a) =>
    a.nom.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleSelectAct = (acte: ProviderPanelAct) => {
    setSelectedActs((current) => current.some((a) => a.id === acte.id)
      ? current.filter((a) => a.id !== acte.id)
      : [...current, acte]);
  };

  const handleSave = async () => {
    if (!nom.trim()) return;
    setSaving(true);
    setError('');
    try {
      await onSave({
        nom: nom.trim(),
        description: description.trim(),
        kind,
        actes: selectedActs,
      });
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’enregistrer le panel.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Créer un Panel d'Actes" className="max-w-2xl">
      <div className="flex flex-col gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Type</label>
          <select value={kind} onChange={(event) => setKind(event.target.value as 'panel' | 'ticket')} className="w-full rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm p-3">
            <option value="panel">Panel d’examens</option>
            <option value="ticket">Ticket d’acte unique</option>
          </select>
        </div>
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
                  <span>{acte.cat && <span className="mr-1 text-gray-400">{acte.cat} ›</span>}{acte.nom}</span>
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
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-700">
          <Button variant="secondary" size="md" onClick={onClose}>
            Annuler
          </Button>
          <Button size="md" onClick={() => void handleSave()} disabled={!nom.trim() || saving}>
            {saving ? 'Enregistrement…' : initialPanel ? 'Enregistrer' : 'Créer le panel'}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
