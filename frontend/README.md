# MedCare Connect — Frontend SPA (React + Vite + Framer Motion)

Bienvenue dans l'espace de développement frontend de **MedCare Connect**. React est la cible de migration des pages Django, tandis que Django conserve l'authentification, les sessions, les permissions et la logique métier. Les templates des parcours qui n'ont pas encore été migrés restent servis par Django.

---

## 🚀 Fonctionnalités Implémentées

1. **Recherche de soins & structures (SIPN)** :
   - URL canonique française `/sante/recherche/` ; `/search` reste une redirection de compatibilité.
   - Résultats, familles d'actes, assurances, régions, délais et pagination chargés depuis la recherche métier Django.
   - Filtres synchronisés avec les paramètres d'URL : actes multiples, tarifs, régime, ville, type, région, domicile, délai et géolocalisation.
   - Cartes de prestations alignées sur les templates SIPN et alimentées par les vraies offres et leurs tarifs.

2. **Expérience Mobile Dédiée (`/mobile`)** :
   - Interface inspirée de `templates/healthcare/patient_mobile.html`.
   - Cartes compactes (`SearchCardMobile` / `.scard-m`).
   - Accès rapide aux catégories d'urgences, consultations, analyses.
   - Navigation fluide optimisée tactile.

3. **Tableau de Bord Prestataire (`/dashboard`)** :
   - Cartes d'indicateurs de performance (Patients, Revenus, Actes réalisés, Taux de complétion).
   - Graphique d'activité hebdomadaire animé.
   - Barres de progression de complétude du profil de santé.

4. **Panels & Tickets de Soins (`/panels`)** :
   - Création et gestion de forfaits d'actes packagés.
   - **Règle métier respectée** : Seuls les actes médicaux élémentaires exécutables (**niveau 3**) peuvent être sélectionnés pour composer un panel.

5. **Panier de Soins & Devis (`CartDrawer`)** :
   - Tiroir latéral animé (Framer Motion spring physics).
   - Ajout, retrait et vidage reliés aux vues panier Django ; contenu et quantités restaurés depuis la session.
   - Total calculé à partir des prix et quantités du panier.
   - Le bouton de devis ouvre le parcours Django existant.

6. **Internationalisation (i18n)** :
   - Prise en charge Français (FR) et Anglais (EN) via `i18next` & `react-i18next`.
   - Sélecteur de langue dans la barre supérieure, mémorisé dans le `localStorage`.

7. **Thème Sombre / Clair** :
   - Mode clair et mode sombre complets avec transition douce.
   - Bouton de bascule rapide dans la barre de navigation.

8. **Pages publiques migrées** :
   - Accueil, inscription et connexion.
   - À propos, comment ça marche, contact et charte de confiance.
   - Les URL canoniques Django de ces pages chargent maintenant l'application React.

---

## 🛠️ Stack Technique

- **Framework** : React 19 + TypeScript
- **Bundler** : Vite 8
- **Animations** : Framer Motion
- **Styles** : Tailwind CSS + CSS Variables (`lib/tokens.ts`)
- **Icônes** : Lucide React
- **Routage** : React Router DOM v7
- **Gestion d'état** : Zustand
- **Internationalisation** : i18next + react-i18next

---

## 💻 Démarrage Rapide

### 1. Démarrer le serveur de développement React
```bash
cd frontend
npm ci  # première installation seulement
npm run dev
```
L'application sera accessible sur `http://localhost:5173`.

### 2. Connecter au backend Django
Le serveur Vite relaie les appels API et les requêtes nécessaires vers le backend Django (`http://127.0.0.1:8000`). Les pages d'accueil, d'inscription, de connexion et `/sante/recherche/` sont servies par React ; Django conserve l'authentification, les sessions et la logique métier.

Dans un second terminal ouvert à la racine du dépôt, lancez Django :
```bash
py -m venv .venv  # première installation seulement
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt  # première installation seulement
python backend/manage.py migrate
python backend/manage.py runserver
```
En développement, ouvrez `http://localhost:5173`. La connexion et l'inscription patient utilisent les vues et la base de données Django. Les pages métier non encore migrées continuent d'utiliser leurs templates Django jusqu'à ce que leur équivalent React soit prêt.

### 3. Compiler pour la production
```bash
cd frontend
npm run build
```
Les fichiers sont générés dans `backend/static/react/` et servis par Django sous `/static/react/`. La construction Docker produit automatiquement ce bundle avant `collectstatic`.
