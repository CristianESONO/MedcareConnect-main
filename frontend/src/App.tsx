import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import './i18n';
import '../../backend/static/css/ai_agent.css';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { CartDrawer } from './components/cart/CartDrawer';
import { VisitorFooter, VisitorHeader, VisitorStyles } from './components/VisitorChrome';
import { LandingPage } from './pages/LandingPage';
import { SearchPage } from './pages/SearchPage';
import { AnnuairePage } from './pages/AnnuairePage';
import { FavoritesPage } from './pages/FavoritesPage';
import { OrganizationProfilePage, PractitionerProfilePage } from './pages/PublicProfilePage';
import { ServiceDetailPage } from './pages/ServiceDetailPage';
import { BundlePlannerPage } from './pages/BundlePlannerPage';
import { CatalogImportPage } from './pages/CatalogImportPage';
import { PublicTicketPage } from './pages/PublicTicketPage';
import { PasswordChangePage } from './pages/PasswordChangePage';
import { PasswordResetPage } from './pages/PasswordResetPage';
import { PlatformReviewGooglePage, PlatformReviewPage } from './pages/PlatformReviewPage';
import { PatientAccountHomePage } from './pages/PatientAccountHomePage';
import { PatientAppointmentsPage } from './pages/PatientAppointmentsPage';
import { PatientBookingPage } from './pages/PatientBookingPage';
import { PatientCartPage } from './pages/PatientCartPage';
import { CartRoutePage } from './pages/CartRoutePage';
import { GuestCartPage } from './pages/GuestCartPage';
import {
  CartHistoryPage,
  LegacyDevisDetailPage,
  LegacyDevisListPage,
} from './pages/CartLegacyPages';
import { PatientRemindersPage } from './pages/PatientNotificationsPage';
import { PatientInsurancePage } from './pages/PatientInsurancePage';
import {
  MessagingConversationRoute,
  MessagingInboxRoute,
  MessagingNotificationsRoute,
} from './pages/ProviderMessagingPages';
import { NotificationPreferencesPage } from './pages/NotificationPreferencesPage';
import { NotificationAdminPage } from './pages/NotificationAdminPage';
import { GeneralProfilePage } from './pages/GeneralProfilePage';
import { PatientMobilePage } from './pages/PatientMobilePage';
import { ProviderSearchHistoryPage } from './pages/ProviderSearchHistoryPage';
import { PatientProfilePage } from './pages/PatientProfilePage';
import { PatientQuotesPage } from './pages/PatientQuotesPage';
import { PatientSearchHistoryPage } from './pages/PatientSearchHistoryPage';
import { ProviderDevisPage } from './pages/ProviderDevisPage';
import { ProviderAppointmentsPage } from './pages/ProviderAppointmentsPage';
import { ProviderAgendaPage } from './pages/ProviderAgendaPage';
import { ProviderCatalogPage } from './pages/ProviderCatalogPage';
import { ProviderActFormPage } from './pages/ProviderActFormPage';
import {
  ProviderAnalyticsPage,
  ProviderHoursPage,
  ProviderInsurancePage,
  ProviderOrganizationCreatePage,
  ProviderOrganizationEditPage,
  ProviderPublicProfilePage,
  ProviderReminderFormPage,
  ProviderRemindersPage,
  ProviderSettingsPage,
  ProviderSubscriptionPage,
  ProviderTypeSetupPage,
} from './pages/ProviderPortalPages';
import {
  ProviderPractitionerAccessPage,
  ProviderPractitionerAgendaPage,
  ProviderTicketsPage,
} from './pages/ProviderPractitionerPages';
import { DashboardPage } from './pages/DashboardPage';
import { PanelsPage } from './pages/PanelsPage';
import { RegisterPage } from './pages/RegisterPage';
import { LoginPage } from './pages/LoginPage';
import { AboutPage } from './pages/AboutPage';
import { HowItWorksPage } from './pages/HowItWorksPage';
import { ContactPage } from './pages/ContactPage';
import { TrustPage } from './pages/TrustPage';
import { AdminPortalPage } from './pages/AdminPortalPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminOrganizationDetailPage } from './pages/AdminOrganizationDetailPage';
import { AdminReviewsPage } from './pages/AdminReviewsPage';
import { AdminActivityPage } from './pages/AdminActivityPage';
import { AdminReportsPage } from './pages/AdminReportsPage';
import { cartApi, type AuthSession, type CartItem, type SearchResult } from './lib/api';
import { useAppStore } from './store/appStore';
import { ProviderWorkspaceSidebar } from './components/ProviderWorkspaceSidebar';
import { AiAssistantWidget } from './components/AiAssistantWidget';

function AppLayout() {
  const location = useLocation();
  const reduceMotion = useReducedMotion();
  const toggleCart = useAppStore((state) => state.toggleCart);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartError, setCartError] = useState('');
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [authSessionError, setAuthSessionError] = useState('');
  const [mobileSearchTabOverride, setMobileSearchTabOverride] = useState<{
    search: string;
    tab: 'prestations' | 'resultats';
  } | null>(null);
  const isSearchPage = location.pathname === '/sante/recherche/';
  const isAdminPage = location.pathname.startsWith('/admin/')
    || location.pathname.startsWith('/dashboard/')
    || location.pathname.startsWith('/notifications/admin/');
  const isProviderMessagingPage = (
    location.pathname === '/messaging/'
    || location.pathname === '/messaging/notifications/'
    || (location.pathname.startsWith('/messaging/') && location.pathname !== '/messaging/rappels/')
  ) && Boolean(authSession?.is_prestataire || authSession?.is_praticien);
  const isProviderPage = location.pathname.startsWith('/sante/prestataire/')
    || location.pathname.startsWith('/rdv/pro/')
    || isProviderMessagingPage;
  const searchParams = new URLSearchParams(location.search);
  const defaultMobileSearchTab = searchParams.has('acte') || searchParams.has('lot') || searchParams.has('q')
    ? 'resultats'
    : 'prestations';
  const loginDestination = authSession?.is_patient
    ? '/users/compte/panel/'
    : authSession?.is_admin
      ? '/dashboard/'
      : authSession?.is_prestataire
        ? '/sante/prestataire/tableau-de-bord/'
        : '/';
  const loginRoute = authSession?.authenticated
    ? <Navigate to={loginDestination} replace />
    : authSession || authSessionError
      ? <LoginPage />
      : <p className="p-8 text-center text-sm text-slate-600" role="status">Vérification de la session…</p>;
  const mobileSearchTab = mobileSearchTabOverride?.search === location.search
    ? mobileSearchTabOverride.tab
    : defaultMobileSearchTab;

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [location.pathname]);

  const refreshCart = async () => {
    setCartItems(await cartApi.get());
  };

  const showMobileSearchTab = (tab: 'prestations' | 'resultats') => {
    setMobileSearchTabOverride({ search: location.search, tab });
    document.body.classList.toggle('sipn-mobile-view-prestations', tab === 'prestations');
    document.body.classList.toggle('sipn-mobile-view-results', tab === 'resultats');
    if (tab === 'prestations') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    window.requestAnimationFrame(() => {
      document.getElementById('results-col')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  useEffect(() => {
    if (isAdminPage) return undefined;
    let active = true;
    cartApi.get()
      .then((items) => {
        if (active) setCartItems(items);
      })
      .catch((error: unknown) => {
        if (active) {
          setCartError(error instanceof Error ? error.message : 'Impossible de charger le panier.');
        }
      });
    return () => { active = false; };
  }, [isAdminPage]);

  useEffect(() => {
    const controller = new AbortController();
    cartApi.session(controller.signal)
      .then((session) => {
        setAuthSession(session);
        setAuthSessionError('');
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setAuthSessionError(
          error instanceof Error ? error.message : 'Impossible de vérifier la session.',
        );
      });
    return () => controller.abort();
  }, []);

  const handleAddToCart = async (result: SearchResult) => {
    try {
      await cartApi.add(result.id);
      await refreshCart();
      setCartError('');
    } catch (error) {
      setCartError(error instanceof Error ? error.message : 'Impossible d’ajouter cet acte au panier.');
      throw error;
    }
  };

  const handleRemoveCartItem = async (id: number) => {
    try {
      await cartApi.remove(id);
      await refreshCart();
      setCartError('');
    } catch (error) {
      setCartError(error instanceof Error ? error.message : 'Impossible de retirer cet acte du panier.');
    }
  };

  const handleClearCart = async () => {
    try {
      await cartApi.clear();
      await refreshCart();
      setCartError('');
    } catch (error) {
      setCartError(error instanceof Error ? error.message : 'Impossible de vider le panier.');
    }
  };

  const handleRequestDevis = () => window.location.assign('/cart/');
  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const handleOpenCart = () => {
    if (isSearchPage && window.matchMedia('(min-width: 1024px)').matches) {
      document.getElementById('dem-right-rail')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }
    toggleCart();
  };

  const visitorPage = [
    '/',
    '/medcare-sn/',
    '/inscription/',
    '/register',
    '/connexion/',
    '/login',
    '/about',
    '/about/',
    '/a-propos/',
    '/how-it-works',
    '/how-it-works/',
    '/comment-ca-marche/',
    '/contact',
    '/contact/',
    '/confiance/',
    '/trust',
    '/trust/',
  ].includes(location.pathname) || location.pathname.startsWith('/mot-de-passe-oublie/');
  const mobileDemoPage = [
    '/patient-mobile/',
    '/demo-patient/',
    '/sante/patient-mobile/',
  ].includes(location.pathname);
  const registerPage = location.pathname === '/inscription/' || location.pathname === '/register';

  return (
    <>
      {visitorPage && <VisitorStyles registerPage={registerPage} landingPage={location.pathname === '/'} />}
      <div className={visitorPage ? 'mc-visitor-app' : mobileDemoPage || isAdminPage ? 'min-h-screen bg-white dark:bg-gray-900' : 'sipn-prestations min-h-screen flex flex-col bg-white dark:bg-[#0b1120] text-gray-900 dark:text-gray-100 font-sans transition-colors duration-200'}>
        <a
          href="#main-content"
          className="sr-only z-[100] rounded-lg bg-white px-4 py-3 font-semibold text-[#123a63] shadow-lg focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
        >
          Aller au contenu
        </a>
        {visitorPage ? (
          <VisitorHeader authSession={authSession} authSessionError={authSessionError} />
        ) : !mobileDemoPage && !isAdminPage ? (
          <>
            <Navbar
              cartCount={cartCount}
              authSession={authSession}
              authSessionError={authSessionError}
              onOpenSidebar={() => setSidebarOpen(true)}
              onOpenCart={handleOpenCart}
            />
            <Sidebar
              open={sidebarOpen}
              authSession={authSession}
              authSessionError={authSessionError}
              onClose={() => setSidebarOpen(false)}
            />
          </>
        ) : null}
        <div className={isProviderPage ? 'mx-auto flex w-full max-w-screen-2xl flex-1' : 'flex flex-1'}>
          {isProviderPage && <ProviderWorkspaceSidebar authSession={authSession} />}
          <main id="main-content" tabIndex={-1} className={`min-w-0 flex-1 outline-none${isSearchPage ? ' react-search-main' : ''}`}>
          {cartError && (
            <p className="mx-auto mt-3 max-w-6xl px-4 text-sm text-red-700" role="alert">
              {cartError}
            </p>
          )}
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: reduceMotion ? 0 : 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: reduceMotion ? 0 : -4 }}
              transition={{ duration: reduceMotion ? 0.12 : 0.22, ease: 'easeOut' }}
            >
          <Routes location={location}>
            <Route path="/admin/*" element={<AdminPortalPage />} />
            <Route path="/dashboard/utilisateurs/" element={<AdminDashboardPage />} />
            <Route path="/dashboard/organismes/" element={<AdminDashboardPage />} />
            <Route path="/dashboard/organismes/:pk/approuver/" element={<AdminOrganizationDetailPage />} />
            <Route path="/dashboard/organismes/:pk/rejeter/" element={<AdminOrganizationDetailPage />} />
            <Route path="/dashboard/organismes/:pk/" element={<AdminOrganizationDetailPage />} />
            <Route path="/dashboard/services/*" element={<Navigate to="/admin/healthcare/servicemedical/" replace />} />
            <Route path="/dashboard/actes/*" element={<Navigate to="/admin/healthcare/actemedical/" replace />} />
            <Route path="/dashboard/assurances/*" element={<Navigate to="/admin/healthcare/assurance/" replace />} />
            <Route path="/dashboard/abonnements/fonctionnalites/*" element={<Navigate to="/admin/healthcare/subscriptionfeature/" replace />} />
            <Route path="/dashboard/avis/*" element={<AdminReviewsPage />} />
            <Route path="/dashboard/activite/*" element={<AdminActivityPage />} />
            <Route path="/dashboard/devis/*" element={<AdminActivityPage />} />
            <Route path="/dashboard/abonnements/*" element={<AdminReportsPage />} />
            <Route path="/dashboard/finances/" element={<AdminReportsPage />} />
            <Route path="/dashboard/pionniers/" element={<AdminReportsPage />} />
            <Route path="/dashboard/bilans/" element={<AdminReportsPage />} />
            <Route path="/dashboard/conformite/" element={<AdminReportsPage />} />
            <Route path="/dashboard/*" element={<AdminDashboardPage />} />
            <Route path="/" element={<LandingPage />} />
            <Route path="/medcare-sn/" element={<LandingPage />} />
            <Route path="/search" element={<Navigate to={`/sante/recherche/${location.search}`} replace />} />
            <Route
              path="/sante/recherche/"
              element={(
                <SearchPage
                  cartItems={cartItems}
                  onAddToCart={handleAddToCart}
                  onRemoveFromCart={handleRemoveCartItem}
                  onClearCart={handleClearCart}
                  onRequestDevis={handleRequestDevis}
                />
              )}
            />
            <Route path="/sante/annuaire/" element={<AnnuairePage />} />
            <Route path="/sante/favoris/" element={<FavoritesPage />} />
            <Route path="/sante/historique/" element={<ProviderSearchHistoryPage />} />
            <Route path="/sante/service/:slug/" element={<ServiceDetailPage />} />
            <Route path="/sante/parcours/" element={<BundlePlannerPage />} />
            <Route path="/sante/assistant-collecte/" element={<CatalogImportPage />} />
            <Route path="/t/:token/" element={<PublicTicketPage />} />
            <Route path="/sante/avis/" element={<PlatformReviewPage />} />
            <Route path="/sante/avis/google/" element={<PlatformReviewGooglePage />} />
            <Route path="/sante/praticien/:slug/" element={<PractitionerProfilePage onCartChange={refreshCart} />} />
            <Route path="/sante/:slug/" element={<OrganizationProfilePage onCartChange={refreshCart} />} />
            <Route path="/cart/" element={<CartRoutePage onCartChange={refreshCart} />} />
            <Route path="/cart/invite/" element={<GuestCartPage onCartChange={refreshCart} />} />
            <Route path="/cart/devis/" element={<LegacyDevisListPage />} />
            <Route path="/cart/devis/:reference/" element={<LegacyDevisDetailPage />} />
            <Route path="/cart/historique/" element={<CartHistoryPage />} />
            <Route path="/messaging/" element={<MessagingInboxRoute />} />
            <Route path="/messaging/notifications/" element={<MessagingNotificationsRoute />} />
            <Route path="/messaging/rappels/" element={<PatientRemindersPage />} />
            <Route path="/messaging/:conversationId/" element={<MessagingConversationRoute />} />
            <Route path="/users/compte/panel/" element={<PatientAccountHomePage />} />
            <Route path="/users/compte/panel/accueil/" element={<PatientAccountHomePage />} />
            <Route path="/users/compte/panel/assurance/" element={<PatientInsurancePage />} />
            <Route path="/users/compte/panel/profil/" element={<PatientProfilePage />} />
            <Route path="/users/compte/panel/rdv/" element={<PatientAppointmentsPage />} />
            <Route path="/users/compte/panel/devis/" element={<PatientQuotesPage />} />
            <Route path="/users/compte/panel/chariot/" element={<PatientCartPage onCartChange={refreshCart} />} />
            <Route path="/users/compte/panel/recherches/" element={<PatientSearchHistoryPage />} />
            <Route path="/users/mot-de-passe/" element={<PasswordChangePage />} />
            <Route path="/users/profil/" element={<GeneralProfilePage />} />
            <Route path="/rdv/reserver/:partRef/" element={<PatientBookingPage />} />
            <Route path="/mot-de-passe-oublie/" element={<PasswordResetPage />} />
            <Route path="/mot-de-passe-oublie/envoye/" element={<PasswordResetPage />} />
            <Route path="/mot-de-passe-oublie/confirmer/:uid/:token/" element={<PasswordResetPage />} />
            <Route path="/mot-de-passe-oublie/succes/" element={<PasswordResetPage />} />
            <Route path="/notifications/admin/*" element={<NotificationAdminPage />} />
            <Route path="/notifications/preferences/" element={<NotificationPreferencesPage />} />
            <Route path="/patient-mobile/" element={<PatientMobilePage />} />
            <Route path="/demo-patient/" element={<PatientMobilePage />} />
            <Route path="/sante/patient-mobile/" element={<PatientMobilePage />} />
            <Route path="/mobile" element={<Navigate to={`/sante/recherche/${location.search}`} replace />} />
            <Route path="/dashboard" element={location.pathname === '/dashboard/' ? <AdminDashboardPage /> : <DashboardPage />} />
            <Route path="/sante/prestataire/tableau-de-bord/" element={<DashboardPage />} />
            <Route path="/sante/prestataire/devis/" element={<ProviderDevisPage />} />
            <Route path="/sante/prestataire/devis/partie/:reference/" element={<ProviderDevisPage />} />
            <Route path="/rdv/pro/agenda/" element={<ProviderAppointmentsPage />} />
            <Route path="/rdv/pro/agenda/grille/" element={<ProviderAgendaPage />} />
            <Route path="/sante/prestataire/actes/" element={<ProviderCatalogPage />} />
            <Route path="/sante/prestataire/actes/import-excel/" element={<ProviderCatalogPage />} />
            <Route path="/sante/prestataire/actes/rappels/" element={<ProviderRemindersPage />} />
            <Route path="/sante/prestataire/actes/rappels/ajouter/" element={<ProviderReminderFormPage />} />
            <Route path="/sante/prestataire/actes/rappels/:id/modifier/" element={<ProviderReminderFormPage />} />
            <Route path="/sante/prestataire/actes/ajouter/" element={<ProviderActFormPage />} />
            <Route path="/sante/prestataire/actes/:pk/modifier/" element={<ProviderActFormPage />} />
            <Route path="/sante/prestataire/assurances/" element={<ProviderInsurancePage />} />
            <Route path="/sante/prestataire/organisme/creer/" element={<ProviderOrganizationCreatePage />} />
            <Route path="/sante/prestataire/organisme/modifier/" element={<ProviderOrganizationEditPage />} />
            <Route path="/sante/prestataire/organisme/horaires/" element={<ProviderHoursPage />} />
            <Route path="/sante/prestataire/tickets/" element={<ProviderTicketsPage />} />
            <Route path="/sante/prestataire/acces/" element={<ProviderPractitionerAccessPage />} />
            <Route path="/sante/prestataire/acces/agenda/:affiliationId/" element={<ProviderPractitionerAgendaPage />} />
            <Route path="/sante/prestataire/type-etablissement/" element={<ProviderTypeSetupPage />} />
            <Route path="/sante/prestataire/profil-public/" element={<ProviderPublicProfilePage />} />
            <Route path="/sante/prestataire/parametres/" element={<ProviderSettingsPage />} />
            <Route path="/sante/prestataire/abonnement/" element={<ProviderSubscriptionPage />} />
            <Route path="/sante/prestataire/medplaque/" element={<ProviderAnalyticsPage mode="medplaque" />} />
            <Route path="/sante/prestataire/bilan/" element={<ProviderAnalyticsPage mode="bilan" />} />
            <Route path="/panels" element={<PanelsPage />} />
            <Route path="/panels/" element={<PanelsPage />} />
            <Route path="/sante/prestataire/panels/" element={<PanelsPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/inscription/" element={<RegisterPage />} />
            <Route path="/login" element={<Navigate to={`/connexion/${location.search}`} replace />} />
            <Route path="/connexion/" element={loginRoute} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/about/" element={<AboutPage />} />
            <Route path="/a-propos/" element={<AboutPage />} />
            <Route path="/how-it-works" element={<HowItWorksPage />} />
            <Route path="/how-it-works/" element={<HowItWorksPage />} />
            <Route path="/comment-ca-marche/" element={<HowItWorksPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/contact/" element={<ContactPage />} />
            <Route path="/confiance/" element={<TrustPage />} />
            <Route path="/trust" element={<TrustPage />} />
            <Route path="/trust/" element={<TrustPage />} />
          </Routes>
            </motion.div>
          </AnimatePresence>
          </main>
        </div>
        {isSearchPage && (
          <nav className="react-mobile-search-nav" aria-label="Navigation principale">
            <button
              type="button"
              data-active={mobileSearchTab === 'prestations'}
              aria-pressed={mobileSearchTab === 'prestations'}
              onClick={() => showMobileSearchTab('prestations')}
            >
              <i className="ti ti-flask" aria-hidden="true" />
              <span>Prestations</span>
            </button>
            <button
              type="button"
              data-active={mobileSearchTab === 'resultats'}
              aria-pressed={mobileSearchTab === 'resultats'}
              onClick={() => showMobileSearchTab('resultats')}
            >
              <i className="ti ti-search" aria-hidden="true" />
              <span>Résultats</span>
            </button>
            <button type="button" onClick={toggleCart} aria-label={`Panier${cartCount ? `, ${cartCount} actes` : ''}`}>
              <span className="react-mobile-search-nav__icon">
                <i className="ti ti-shopping-cart" aria-hidden="true" />
                {cartCount > 0 && <span>{cartCount}</span>}
              </span>
              <span>Panier</span>
            </button>
            <a href="/messaging/" aria-label="Ouvrir les messages">
              <i className="ti ti-message" aria-hidden="true" />
              <span>Messages</span>
            </a>
            <a href="/users/compte/" aria-label="Ouvrir mon compte">
              <i className="ti ti-user" aria-hidden="true" />
              <span>Mon compte</span>
            </a>
          </nav>
        )}
        {visitorPage ? <VisitorFooter /> : !mobileDemoPage && !isSearchPage && !isAdminPage ? (
          <CartDrawer
            items={cartItems}
            onRemoveItem={handleRemoveCartItem}
            onClear={handleClearCart}
            onRequestDevis={handleRequestDevis}
          />
        ) : null}
      </div>
      <AiAssistantWidget />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
