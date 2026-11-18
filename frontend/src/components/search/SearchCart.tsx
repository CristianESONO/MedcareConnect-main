import { useEffect } from 'react';
import { useAppStore } from '../../store/appStore';
import type { CartItem } from '../../lib/api';

interface SearchCartProps {
  items: CartItem[];
  actsOpen: boolean;
  hasSelection: boolean;
  onBrowseActs: () => void;
  onRemoveItem: (id: number) => void | Promise<void>;
  onClear: () => void | Promise<void>;
  onRequestDevis: () => void;
}

function formatPrice(value: number) {
  return Math.round(value).toLocaleString('fr-FR');
}

function CartItems({
  items,
  emptyMessage,
  onRemoveItem,
}: {
  items: CartItem[];
  emptyMessage: string;
  onRemoveItem: SearchCartProps['onRemoveItem'];
}) {
  if (!items.length) {
    return <div className="cart-empty">{emptyMessage}</div>;
  }

  const groupedItems = items.reduce<Map<string, CartItem[]>>((groups, item) => {
    const group = groups.get(item.structure_nom) || [];
    group.push(item);
    groups.set(item.structure_nom, group);
    return groups;
  }, new Map());
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <div className="cart-items">
      {groupedItems.size > 1 && (
        <div className="panier-multi-warn sipn-ico-inline">
          <i className="ti ti-alert-triangle" aria-hidden="true" />
          <span>
            <strong>{itemCount} actes sélectionnés</strong>
            <br />
            Une discussion par structure.
          </span>
        </div>
      )}
      {Array.from(groupedItems, ([structure, groupItems]) => {
        const subtotal = groupItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
        return (
          <div className="cart-struct-group" key={structure}>
            <div className="csg-head">
              <span><i className="ti ti-building-hospital" aria-hidden="true" /> {structure}</span>
              <span className="csg-sub">{formatPrice(subtotal)} F</span>
            </div>
            {groupItems.map((item) => (
              <div className="citem" key={item.id}>
                <div className="ci-info">
                  <div className="ci-nom">
                    {item.acte_nom}
                    {item.quantity > 1 && <span className="ci-qty"> ×{item.quantity}</span>}
                  </div>
                </div>
                <div className="ci-prix">
                  {formatPrice(item.price * item.quantity)} F
                </div>
                <button
                  type="button"
                  className="ci-del"
                  aria-label={`Retirer ${item.acte_nom} du panier`}
                  onClick={() => void onRemoveItem(item.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

export function SearchCart({
  items,
  actsOpen,
  hasSelection,
  onBrowseActs,
  onRemoveItem,
  onClear,
  onRequestDevis,
}: SearchCartProps) {
  const { cartOpen, toggleCart } = useAppStore();
  const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);
  const structureCount = new Set(items.map((item) => item.structure_nom)).size;

  useEffect(() => {
    if (!cartOpen) return;
    document.body.classList.add('sheet-locked');
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') toggleCart();
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.classList.remove('sheet-locked');
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [cartOpen, toggleCart]);

  const cartFooter = (mobile = false) => (
    <div
      className={mobile ? 'dem-cart-sheet-foot border-t border-gray-100 px-4 py-3' : 'cart-footer'}
      data-dem-cart-footer
      hidden={!items.length}
    >
      <div className="cart-total-row">
        <span className="ct-label">Total estimé</span>
        <span className="ct-value" data-dem-cart-total>{formatPrice(total)} FCFA</span>
      </div>
      <div className="cart-structs-info" data-dem-cart-structs-info>
        {itemCount} acte{itemCount === 1 ? '' : 's'} · {structureCount} structure{structureCount === 1 ? '' : 's'}
      </div>
      {mobile ? (
        <button type="button" className="devis-btn w-full" onClick={onRequestDevis}>
          <i className="ti ti-message" aria-hidden="true" /> Obtenir mon devis
        </button>
      ) : (
        <button type="button" className="devis-btn" onClick={onRequestDevis}>
          <i className="ti ti-message" aria-hidden="true" /> Obtenir mon devis
        </button>
      )}
      <p className="cart-devis-hint">
        {mobile ? 'Un devis par acte — bouton sur chaque ligne.' : 'Un message WhatsApp est généré par structure concernée.'}
      </p>
    </div>
  );

  return (
    <>
      <aside id="dem-right-rail" className="col-right sipn-col-cart hidden lg:block" aria-label="Panier">
        <div className="panier">
          <div className="panier-head">
            <div className="panier-title">
              <span className="panier-title-txt sipn-ico-inline">
                <i className="ti ti-shopping-cart" aria-hidden="true" /> Mon panier
              </span>
              <span className="cart-count" data-dem-cart-count>{itemCount}</span>
            </div>
            <button type="button" className="cart-clear" onClick={() => void onClear()}>Vider</button>
          </div>
          <div id="cart-body" data-dem-cart-body>
            <CartItems
              items={items}
              emptyMessage={'Cochez des actes dans les structures\npour construire votre devis.'}
              onRemoveItem={onRemoveItem}
            />
          </div>
          {cartFooter()}
        </div>
      </aside>

      <div className="dem-mobile-quickbar lg:hidden" id="dem-mobile-quickbar" role="toolbar" aria-label="Actions rapides">
        <button
          type="button"
          className="dem-mq-btn"
          aria-controls="sidebar-desktop"
          aria-expanded={actsOpen}
          aria-label={hasSelection ? 'Parcourir les actes et filtres' : 'Rechercher un acte'}
          onClick={onBrowseActs}
        >
          <span className="dem-mq-ic" aria-hidden="true"><i className="ti ti-list-search" /></span>
          <span className="dem-mq-label">{hasSelection ? 'Actes & filtres' : 'Rechercher un acte'}</span>
        </button>
        <button
          type="button"
          className="dem-mq-btn dem-mq-btn--cart"
          aria-controls="dem-cart-sheet"
          aria-expanded={cartOpen}
          onClick={toggleCart}
        >
          <span className="dem-mq-ic" aria-hidden="true"><i className="ti ti-shopping-cart" /></span>
          <span className="dem-mq-label">Panier</span>
          <span className="dem-mq-cart-count cart-count" data-dem-cart-count>{itemCount}</span>
        </button>
        <a
          href="/messaging/"
          className="dem-mq-btn"
          aria-label="Ouvrir la liste des messages"
        >
          <span className="dem-mq-ic" aria-hidden="true"><i className="ti ti-mail" /></span>
          <span className="dem-mq-label">Messages</span>
        </a>
      </div>

      <div
        id="dem-cart-backdrop"
        className={`sheet-backdrop${cartOpen ? ' open' : ''}`}
        aria-hidden="true"
        onClick={toggleCart}
      />
      <aside
        id="dem-cart-sheet"
        className={`sheet-panel dem-cart-sheet flex max-h-[90dvh] flex-col${cartOpen ? ' open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Votre panier"
        aria-hidden={!cartOpen}
      >
        <div className="sheet-handle" aria-hidden="true" />
        <div className="dem-cart-sheet-head flex items-start justify-between gap-3 border-b border-gray-100 px-4 pb-3 pt-1">
          <div>
            <h2 className="dem-cart-sheet-title text-lg font-bold text-gray-900">Panier</h2>
            <p className="dem-cart-sheet-sub mt-1 text-xs text-gray-500">
              Sélection sur cette page · <a href="/cart/" className="font-semibold text-accent-600 hover:text-accent-700">Ouvrir le panier complet</a>
            </p>
          </div>
          <button type="button" className="rounded-full p-2 text-gray-400 hover:bg-gray-100" aria-label="Fermer" onClick={toggleCart}>
            <i className="ti ti-x" aria-hidden="true" />
          </button>
        </div>
        <div className="dem-cart-sheet-body min-h-0 flex-1 overflow-y-auto px-4 py-3">
          <div data-dem-cart-body>
            <CartItems
              items={items}
              emptyMessage="Ajoutez des actes depuis les cartes ci-dessous."
              onRemoveItem={onRemoveItem}
            />
          </div>
        </div>
        {cartFooter(true)}
      </aside>
    </>
  );
}
