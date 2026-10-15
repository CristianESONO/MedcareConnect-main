# MedCare Connect — Programme Autonome d'Import & Réconciliation de Catalogues

Programme autonome et portable permettant d'importer et réconcilier n'importe quel catalogue médical (laboratoire, clinique, cabinet, ambulance) avec le référentiel officiel MedCare (Piliers 1 à 6).

Ce programme possède **sa propre interface graphique dédiée** et peut être utilisé :
- **Sans aucune installation** (directement dans le navigateur web via double-clic sur `index.html`).
- **Via un mini-serveur local** (`lancer_programme.bat` ou `python medcare_importer.py --serve`).
- **En ligne de commande (CLI)** pour le traitement batch de fichiers `.xlsx` et `.csv`.

---

## 📁 Contenu du dossier

| Fichier | Description |
| :--- | :--- |
| **`lancer_programme.bat`** | **Lanceur rapide Windows** (double-clic pour ouvrir l'interface). |
| **`index.html`** / **`MedCare_Import_Reconciliation.html`** | **Application Web graphique complète** autonome. |
| **`medcare_importer.py`** | Moteur Python (CLI & mini-serveur web HTTP). |
| **`referentiel_data.js`** | Base de données locale des 1 014 actes standardisés et 2 890 alias. |
| **`referentiel_6piliers_medcare.json`** | Référentiel complet au format JSON. |
| **`catalogue_test_bionissa_clinique.xlsx`** | Fichier Excel de test complet (25 actes types réels). |
| **`catalogue_test_bionissa_clinique.csv`** | Même catalogue de test au format CSV. |
| **`MODE_D_EMPLOI.md`** | Guide détaillé des étapes de test et validation. |

---

## ⚡ Démarrage rapide (3 options)

### Option 1 — Double-clic (Le plus simple)
1. Double-cliquez sur **`lancer_programme.bat`** ou directement sur **`index.html`**.
2. L'interface s'ouvre immédiatement dans votre navigateur habituel (Edge, Chrome, Firefox, etc.).
3. Glissez-déposez un fichier Excel/CSV ou cliquez sur **« Charger le catalogue de démo (25 actes) »**.
4. Le moteur analyse automatiquement les colonnes, normalise les libellés et affiche les correspondances en direct :
   - 🟢 **100% Reconnus** (normalisation stricte, alias officiels)
   - 🟡 **À confirmer** (flou, fautes de frappe, alertes de garde-fous)
   - 🔴 **Non reconnus / Hors référentiel**
5. Vous pouvez ajuster les correspondances manuellement avec les menus déroulants et exporter le catalogue réconcilié en **Excel (.xlsx)** ou en **JSON**.

### Option 2 — Serveur local Python
```bash
cd documents/programme_import
python medcare_importer.py --serve
```
Ouvre l'application sur `http://127.0.0.1:5050/index.html`.

### Option 3 — Ligne de commande (CLI)
```bash
python medcare_importer.py catalogue_test_bionissa_clinique.xlsx
```
Génère le fichier `catalogue_test_bionissa_clinique_reconcilie.json` avec tous les scores et avertissements.

---

## 🏥 Règles médicales intégrées (Conforme CDC 12 octobre 2026)

- **Normalisation stricte (§5.2)** : Minuscules, retrait des accents et ponctuations, normalisation des lettres grecques (`α` → `alpha`) et ligatures (`œ` → `oe`).
- **Algorithme à 4 niveaux (§5.3)** :
  1. Égalité exacte avec nom normalisé (100% automatique).
  2. Égalité exacte avec alias actif (100% automatique).
  3. Détection de libellé composite (ex: `PV CHLAM MYCO`, dissociation obligatoire).
  4. Rapprochement flou avec seuil de confiance à 65%.
- **Garde-fous discriminants (§5.5)** :
  Protection stricte contre les confusions médicales (Immunoglobulines IgG/IgM, Hépatites A/B/C, Thyroïde T3/T4, Milieu biologique urinaire/sérique, etc.).
