# MedCare Connect — Frontend SPA (React + Vite + Framer Motion)

Bienvenue dans l'espace de développement frontend moderne de **MedCare Connect**.
Ce projet React SPA est développé en parallèle du frontend Django SSR existant, sans altérer ni supprimer les templates ou fichiers statiques actuels.

---

## 🚀 Fonctionnalités Implémentées

1. **Recherche de soins & structures (SIPN)** :
   - Barre de recherche avec géolocalisation directe (HTML5 Geolocation API).
   - Cartes de résultats enrichies (`SearchCard`) avec animations d'entrée Framer Motion décalées.
   - Panel de filtres rétractable : type d'établissement, distance maximale, tri par tarif / proximité / note.
   - Design tokens et couleurs alignés sur `sipn_cards.css` (`--mc-navy`, `--mc-accent`, `--sipn-green`).

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
   - Ajout d'actes depuis les résultats de recherche.
   - Calcul en temps réel du total estimé en FCFA.
   - Bouton de demande de devis.

6. **Internationalisation (i18n)** :
   - Prise en charge Français (FR) et Anglais (EN) via `i18next` & `react-i18next`.
   - Sélecteur de langue dans la barre supérieure, mémorisé dans le `localStorage`.

7. **Thème Sombre / Clair** :
   - Mode clair et mode sombre complets avec transition douce.
   - Bouton de bascule rapide dans la barre de navigation.

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
npm run dev
```
L'application sera accessible sur `http://localhost:5173`.

### 2. Connecter au backend Django
Le serveur Vite est préconfiguré pour relayer les requêtes `/api`, `/healthcare`, `/cart` vers le backend Django (`http://127.0.0.1:8000`).

Lancez votre serveur Django habituel dans un autre terminal :
```bash
py manage.py runserver
```

### 3. Compiler pour la production
```bash
cd frontend
npm run build
```
Les fichiers statiques optimisés seront générés dans le dossier `frontend/dist/`.
