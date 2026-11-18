import { motion, AnimatePresence } from 'framer-motion';
import { X, ShoppingBag, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CartItem } from './CartItem';
import { Button } from '../ui/Button';
import { useAppStore } from '../../store/appStore';
import { CartItem as ICartItem } from '../../lib/api';

interface CartDrawerProps {
  items: ICartItem[];
  onRemoveItem: (id: number) => void;
  onClear: () => void;
  onRequestDevis: () => void;
}

export function CartDrawer({ items, onRemoveItem, onClear, onRequestDevis }: CartDrawerProps) {
  const { t } = useTranslation();
  const { cartOpen, toggleCart } = useAppStore();

  const total = items.reduce((acc, curr) => acc + curr.price * curr.quantity, 0);
  const itemCount = items.reduce((count, item) => count + item.quantity, 0);

  return (
    <AnimatePresence>
      {cartOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={toggleCart}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />

          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 250 }}
            className="fixed top-0 right-0 h-full w-full max-w-md bg-white dark:bg-gray-850 shadow-2xl z-50 flex flex-col border-l border-gray-100 dark:border-gray-800"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <ShoppingBag className="text-accent" size={20} />
                <h3 className="font-syne font-bold text-navy dark:text-white text-lg">
                  {t('cart.title')}
                </h3>
                <span className="text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent font-semibold">
                  {itemCount}
                </span>
              </div>
              <button
                onClick={toggleCart}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X size={20} />
              </button>
            </div>

            {/* Items list */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-2.5">
              {items.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-gray-400">
                  <ShoppingBag size={48} className="stroke-[1.2] mb-3 opacity-50" />
                  <p className="font-medium text-sm text-gray-600 dark:text-gray-400">
                    {t('cart.empty')}
                  </p>
                </div>
              ) : (
                items.map((item) => (
                  <CartItem key={item.id} item={item} onRemove={onRemoveItem} />
                ))
              )}
            </div>

            {/* Footer */}
            {items.length > 0 && (
              <div className="p-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/40 flex flex-col gap-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs font-semibold uppercase text-gray-500 tracking-wider">
                    {t('cart.total')}
                  </span>
                  <div className="text-right">
                    <span className="font-syne font-bold text-xl text-navy dark:text-white">
                      {total.toLocaleString()}
                    </span>{' '}
                    <span className="text-xs text-gray-500 font-medium">FCFA</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Button variant="secondary" size="md" onClick={onClear}>
                    {t('cart.clear')}
                  </Button>
                  <Button size="md" onClick={onRequestDevis}>
                    <span>{t('cart.request_devis')}</span>
                    <ArrowRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
