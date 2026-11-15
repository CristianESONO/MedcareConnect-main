import { Trash2 } from 'lucide-react';
import { CartItem as ICartItem } from '../../lib/api';

interface CartItemProps {
  item: ICartItem;
  onRemove: (id: number) => void;
}

export function CartItem({ item, onRemove }: CartItemProps) {
  return (
    <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-750/50 border border-gray-100 dark:border-gray-700/60 gap-3">
      <div className="min-w-0 flex-1">
        <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate font-syne">
          {item.acte_nom}
        </h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
          {item.structure_nom}
        </p>
        <span className="inline-block mt-1 font-bold text-xs text-navy dark:text-accent">
          {item.price.toLocaleString()} FCFA
        </span>
      </div>

      <button
        type="button"
        onClick={() => onRemove(item.id)}
        className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
        title="Supprimer"
      >
        <Trash2 size={16} />
      </button>
    </div>
  );
}
