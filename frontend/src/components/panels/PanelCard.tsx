import { motion } from 'framer-motion';
import { Layers, Trash2, Edit3 } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Panel } from '../../lib/api';

interface PanelCardProps {
  panel: Panel;
  onEdit?: (p: Panel) => void;
  onDelete?: (id: number | string) => void;
  onToggle?: (id: number | string) => void;
  onSend?: (p: Panel) => void;
  index?: number;
}

export function PanelCard({ panel, onEdit, onDelete, onToggle, onSend, index = 0 }: PanelCardProps) {
  const totalTarif = panel.total_price ?? panel.actes?.reduce((sum, a) => sum + (a.price || 0), 0) ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Card className="p-5 flex flex-col justify-between h-full">
        <div>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-navy/5 dark:bg-navy/20 text-navy dark:text-accent">
                <Layers size={18} />
              </div>
              <div>
                <h3 className="font-syne font-bold text-navy dark:text-white text-base">
                  {panel.nom}
                </h3>
                <span className="text-xs text-gray-400">
                  {panel.actes?.length || 0} actes inclus · {panel.is_active === false ? 'Inactif' : 'Actif'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              {onEdit && (
                <button
                  onClick={() => onEdit(panel)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-navy dark:hover:text-white transition-colors"
                  title="Modifier"
                >
                  <Edit3 size={15} />
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(panel.id)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
                  title="Supprimer"
                >
                  <Trash2 size={15} />
                </button>
              )}
              {onToggle && (
                <button
                  type="button"
                  onClick={() => onToggle(panel.id)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-accent transition-colors"
                  title={panel.is_active === false ? 'Activer' : 'Désactiver'}
                  aria-label={panel.is_active === false ? `Activer ${panel.nom}` : `Désactiver ${panel.nom}`}
                >
                  <i className={`ti ${panel.is_active === false ? 'ti-player-play' : 'ti-player-pause'}`} aria-hidden="true" />
                </button>
              )}
              {onSend && (
                <button
                  type="button"
                  onClick={() => onSend(panel)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-sky-600 transition-colors"
                  title="Envoyer à un patient"
                  aria-label={`Envoyer ${panel.nom} à un patient`}
                >
                  <i className="ti ti-send" aria-hidden="true" />
                </button>
              )}
            </div>
          </div>

          {panel.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 line-clamp-2">
              {panel.description}
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {panel.actes?.map((a) => (
              <Badge key={a.id} variant="gray" className="text-[11px]">
                {a.nom}
              </Badge>
            ))}
          </div>
        </div>

        <div className="mt-5 pt-3 border-t border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
          <span className="text-xs text-gray-400 uppercase font-semibold">Tarif forfaitaire</span>
          <span className="font-syne font-bold text-base text-navy dark:text-accent">
            {totalTarif > 0 ? `${totalTarif.toLocaleString()} FCFA` : 'Sur devis'}
          </span>
        </div>
        {(panel.public_path || panel.views_count !== undefined) && (
          <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
            {panel.public_path && <a className="font-semibold text-sky-700 hover:underline dark:text-sky-300" href={panel.public_path} target="_blank" rel="noreferrer">Ouvrir le lien patient</a>}
            {panel.views_count !== undefined && <span>{panel.views_count} vue(s)</span>}
          </div>
        )}
      </Card>
    </motion.div>
  );
}
