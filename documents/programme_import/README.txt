================================================================================
 MEDCARE CONNECT — PROGRAMME AUTONOME D'IMPORT & RÉCONCILIATION DE CATALOGUES
 Version 1.0 · Conforme au Cahier des Charges Technique (12 Octobre 2026)
================================================================================

Ce dossier contient un programme entièrement autonome et portable permettant
de tester la réconciliation automatique et assistée des catalogues médicaux
(laboratoires, cliniques, cabinets) avec les 1 014 actes standardisés MedCare
et leurs 2 890 alias sémantiques.

AUCUNE INSTALLATION DE DJANGO NI DE BASE DE DONNÉES N'EST NÉCESSAIRE.

--------------------------------------------------------------------------------
 CONTENU DU PACK DE TEST
--------------------------------------------------------------------------------

1. MedCare_Import_Reconciliation.html (ou index.html)
   -> L'application web graphique complète.
   -> S'ouvre directement avec n'importe quel navigateur (Chrome, Edge, Firefox, Safari).

2. catalogue_test_bionissa_clinique.xlsx (et version .csv)
   -> Fichier de test réel contenant 25 actes variés :
      - Actes identiques (100% auto) : Glycémie à jeun, Créatininémie, Cholestérol...
      - Alias officiels (100% auto) : NFS, ECBU, Ionogramme sanguin...
      - Fautes de frappe réelles du CDC Bionissa : "RUGEOLE", "Scoth test", "ac anti CP 210", "TPTCK"...
      - Garde-fous discriminants (§5.5) : Sérologie Rubéole IgG vs IgM, Hépatite B vs C...
      - Libellé composite (§5.3 / §6) : "PV CHLAM MYCO"
      - Actes des Piliers 2 (Imagerie), 3 (Explorations), 4 (Ambulance), 5 (Soins spécialisés), 6 (Dentaire).

3. medcare_importer.py
   -> Programme Python autonome (Python 3.8+) pouvant être exécuté :
      - En ligne de commande (batch processing)
      - Ou comme mini-serveur web local avec l'option --serve

4. referentiel_data.js & referentiel_6piliers_medcare.json
   -> Les bases de données complètes du référentiel embarquées (Piliers 1 à 6).

--------------------------------------------------------------------------------
 COMMENT TESTER EN 10 SECONDES ?
--------------------------------------------------------------------------------

OPTION A — TEST IMMÉDIAT DANS LE NAVIGATEUR (LE PLUS SIMPLE) :
1. Faites un double-clic sur "MedCare_Import_Reconciliation.html"
2. Cliquez sur le bouton "Charger le catalogue de démo (25 actes)"
   OU glissez-déposez le fichier "catalogue_test_bionissa_clinique.xlsx"
3. Observez le tableau interactif :
   - 🟢 Reconnus automatiquement (100%)
   - 🟡 À confirmer avec alerte de garde-fou ou flou
   - 🔴 Composites et actes inconnus
4. Cliquez sur "Exporter Excel (.xlsx)" pour récupérer le fichier réconcilié.

OPTION B — TEST EN LIGNE DE COMMANDE PYTHON :
1. Ouvrez un terminal dans ce dossier.
2. Lancez :
   python medcare_importer.py catalogue_test_bionissa_clinique.xlsx
3. Le programme affiche les scores et génère automatiquement le fichier :
   catalogue_test_bionissa_clinique_reconcilie.json

OPTION C — TEST VIA MINI-SERVEUR LOCAL PYTHON :
1. Lancez :
   python medcare_importer.py --serve
2. Le navigateur s'ouvre automatiquement sur http://127.0.0.1:5050

--------------------------------------------------------------------------------
 VALIDATIONS MÉDICALES CONFORMES AU CDC
--------------------------------------------------------------------------------
- Étape 1 : Égalité exacte avec nom normalisé -> Validation 100% automatique
- Étape 2 : Égalité exacte avec un alias actif -> Validation 100% automatique
- Étape 3 : Détection de libellé composite -> Signalé, jamais automatique
- Étape 4 : Rapprochement flou avec seuil de confiance à 65%
- Garde-fous discriminants actifs sur les familles sensibles :
  Immunoglobulines (IgG/IgM), Hépatites virales (VHA/VHB/VHC), Thyroïde (T3/T4), etc.
================================================================================
