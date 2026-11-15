import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './i18n';
import { Navbar } from './components/Navbar';
import { CartDrawer } from './components/cart/CartDrawer';
import { SearchPage } from './pages/SearchPage';
import { PatientMobilePage } from './pages/PatientMobilePage';
import { DashboardPage } from './pages/DashboardPage';
import { PanelsPage } from './pages/PanelsPage';
import { type CartItem, type SearchResult } from './lib/api';

export default function App() {
  const [cartItems, setCartItems] = useState<CartItem[]>([
    {
      id: 1,
      acte_nom: 'Hémogramme Complet (NFS)',
      structure_nom: 'Hôpital Principal de Dakar',
      price: 15000,
    },
    {
      id: 2,
      acte_nom: 'Consultation Spécialisée',
      structure_nom: 'Clinique de la Madeleine',
      price: 25000,
    },
  ]);

  const handleAddToCart = (result: SearchResult) => {
    const newItem: CartItem = {
      id: Date.now(),
      acte_nom: result.actes?.[0] || 'Consultation Médicale',
      structure_nom: result.nom,
      price: result.price_min || 15000,
    };
    setCartItems((prev) => [newItem, ...prev]);
  };

  const handleRemoveCartItem = (id: number) => {
    setCartItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleClearCart = () => {
    setCartItems([]);
  };

  const handleRequestDevis = () => {
    alert(`Demande de devis transmise pour ${cartItems.length} acte(s) ! Total : ${cartItems.reduce((s, i) => s + i.price, 0).toLocaleString()} FCFA`);
  };

  return (
    <BrowserRouter>
      <div className="sipn-prestations min-h-screen flex flex-col bg-[#f8fafc] dark:bg-[#0f172a] text-gray-900 dark:text-gray-100 font-sans transition-colors duration-200">
        <Navbar cartCount={cartItems.length} />

        <main className="flex-1">
          <Routes>
            <Route path="/" element={<SearchPage onAddToCart={handleAddToCart} />} />
            <Route path="/mobile" element={<PatientMobilePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/panels" element={<PanelsPage />} />
          </Routes>
        </main>

        <CartDrawer
          items={cartItems}
          onRemoveItem={handleRemoveCartItem}
          onClear={handleClearCart}
          onRequestDevis={handleRequestDevis}
        />
      </div>
    </BrowserRouter>
  );
}
