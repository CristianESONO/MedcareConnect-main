import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './i18n';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { CartDrawer } from './components/cart/CartDrawer';
import { LandingPage } from './pages/LandingPage';
import { SearchPage } from './pages/SearchPage';
import { PatientMobilePage } from './pages/PatientMobilePage';
import { DashboardPage } from './pages/DashboardPage';
import { PanelsPage } from './pages/PanelsPage';
import { RegisterPage } from './pages/RegisterPage';
import { LoginPage } from './pages/LoginPage';
import { AboutPage } from './pages/AboutPage';
import { HowItWorksPage } from './pages/HowItWorksPage';
import { ContactPage } from './pages/ContactPage';
import { type CartItem, type SearchResult } from './lib/api';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
    alert(
      `Demande de devis transmise pour ${cartItems.length} acte(s) ! Total : ${cartItems
        .reduce((s, i) => s + i.price, 0)
        .toLocaleString()} FCFA`
    );
  };

  return (
    <BrowserRouter>
      <div className="sipn-prestations min-h-screen flex flex-col bg-[#f8fafc] dark:bg-[#0b1120] text-gray-900 dark:text-gray-100 font-sans transition-colors duration-200">
        {/* Navigation Bar */}
        <Navbar
          cartCount={cartItems.length}
          onOpenSidebar={() => setSidebarOpen(true)}
        />

        {/* Global Sliding Sidebar */}
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Routed Content */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/search" element={<SearchPage onAddToCart={handleAddToCart} />} />
            <Route path="/mobile" element={<PatientMobilePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/panels" element={<PanelsPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/how-it-works" element={<HowItWorksPage />} />
            <Route path="/contact" element={<ContactPage />} />
          </Routes>
        </main>

        {/* Slide-over Cart Drawer */}
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
