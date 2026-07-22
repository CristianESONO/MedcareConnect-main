# Données de référence (catalogue Medcare)

Les fichiers `catalog_pillars.py` et `catalog_assurances.py` reprennent la **hiérarchie** et les intitulés des documents :

- `documents/SEGMENTATION_DES_SERVICES (1).pdf` — 6 piliers, types de service (niveau 2), actes (niveau 3)
- `documents/ASSURANCES_SENEGAL.pdf` — assureurs et dispositifs par segment (privée IARD, digitale, régime public, mutuelle)

Chargement en base :

```bash
python seed_data.py --reset-catalog
```

⚠️ `--reset-catalog` supprime tous les `ServiceMedical`, `ActeMedical`, `Assurance`, `PrestataireActe` et prises en charge, puis recharge le catalogue. Les comptes utilisateurs et organismes sont conservés ; les offres sont régénérées pour les organismes de démo.
