# Guide de Test — Programme Autonome d'Import & Réconciliation MedCare

Ce kit de test autonome permet d'évaluer le **moteur de réconciliation de catalogues médicaux** de MedCare sans avoir besoin d'installer Django, ni de base de données.

---

## 📦 Contenu du kit de test

| Fichier | Rôle |
| :--- | :--- |
| **`MedCare_Import_Reconciliation.html`** | **Application Web graphique autonome** (s'ouvre directement avec Chrome, Edge, Safari, Firefox). |
| **`catalogue_test_bionissa_clinique.xlsx`** | Fichier Excel de test contenant 25 actes représentatifs (fautes de frappe Bionissa, composites, garde-fous). |
| **`catalogue_test_bionissa_clinique.csv`** | Équivalent au format CSV. |
| **`medcare_importer.py`** | Script Python autonome (ligne de commande batch & mini-serveur local). |
| **`referentiel_data.js`** | Base embarquée des 1 014 actes et 2 890 alias MedCare (Piliers 1 à 6). |
| **`referentiel_6piliers_medcare.json`** | Référentiel source au format JSON. |
| **`README.txt`** | Résumé rapide en texte brut. |

---

## 🚀 3 façons de tester

### 1. Test Web immédiat (Sans rien installer)
1. Double-cliquez sur **`MedCare_Import_Reconciliation.html`** (ou `index.html`).
2. Cliquez sur **« Charger le catalogue de démo (25 actes) »** ou glissez-déposez n'importe quel fichier Excel.
3. Le tableau s'affiche instantanément :
   - 🟢 **Reconnus automatiquement (100%)** : `Glycémie à jeun`, `NFS`, `Créatininémie`, etc.
   - 🟡 **À confirmer** : Les fautes de frappe (`RUGEOLE`, `Scoth test`, `ac anti CP 210`) et les cas sensibles avec garde-fou (`Sérologie Rubéole IgG` vs `IgM`).
   - 🔴 **Composites / Inconnus** : `PV CHLAM MYCO`, `Prestation spéciale non répertoriée XYZ`.
4. Vous pouvez corriger un rattachement via le menu déroulant ou les puces de suggestions, cocher l'apprentissage d'alias et cliquer sur **« Exporter Excel (.xlsx) »**.

### 2. Test en Ligne de Commande (Python)
Pour tester le traitement automatisé par lot :
```bash
python medcare_importer.py catalogue_test_bionissa_clinique.xlsx
```
Le programme produit un rapport détaillé dans le terminal et génère un fichier JSON réconcilié :
`catalogue_test_bionissa_clinique_reconcilie.json`.

### 3. Test via Mini-Serveur Web Local (Python)
```bash
python medcare_importer.py --serve
```
Ouvre l'application web dans votre navigateur sur `http://127.0.0.1:5050`.

---

## 🛡️ Règles médicales intégrées (CDC 12 octobre 2026)

- **Normalisation stricte (§5.2)** : minuscules, suppression des accents, ligatures (`œ` → `oe`), lettres grecques (`α` → `alpha`), ponctuation nettoyée.
- **Cascade en 4 étapes (§5.3)** :
  1. Égalité exacte avec nom normalisé ➔ 100% automatique.
  2. Égalité exacte avec alias actif ➔ 100% automatique.
  3. Détection de libellé composite (ex: `PV CHLAM MYCO`) ➔ Bloqué, validation humaine requise.
  4. Rapprochement flou avec seuil de confiance à 65%.
- **Garde-fous discriminants (§5.5)** :
  Bloque la validation automatique si une divergence critique existe sur :
  * Immunoglobulines : `IgG`, `IgM`, `IgA`, `IgE`
  * Hépatites virales : `VHA`, `VHB`, `VHC`, `VHD`, `VHE`
  * Marqueurs d'Hépatite B : `HBs`, `HBe`, `HBc`
  * Thyroïde : `T3`, `T4`
  * Milieu biologique : `urinaire`, `sérique`
