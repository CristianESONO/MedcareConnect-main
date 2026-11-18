"""
Liste des assureurs / dispositifs — source : documents/ASSURANCES_SENEGAL.pdf
Les valeurs `segment` correspondent à healthcare.models.Assurance.Segment.
"""

ASSURANCES_FROM_DOCS = [
    # Privées traditionnelles (complément liste opérationnelle)
    {"name": "ASKIA Assurances", "segment": "privee_iard", "description": "Assureur privé — produits IARD incluant assurance maladie."},
    {"name": "NSIA Sénégal Assurances", "segment": "privee_iard", "description": "Compagnie d'assurances — couverture santé entreprises et particuliers."},
    {"name": "SUNU Assurances IARDT Sénégal", "segment": "privee_iard", "description": "Assurances IARD et santé."},
    {"name": "WAFA Assurance Sénégal", "segment": "privee_iard", "description": "Assurance maladie et produits IARD."},
    {"name": "SONAC", "segment": "privee_iard", "description": "Société nationale d'assurances — produits incluant santé."},
    {"name": "CNAAS", "segment": "privee_iard", "description": "Compagnie d'assurances (libellé et périmètre santé à vérifier)."},
    {"name": "Finafrica Assurances", "segment": "privee_iard", "description": "Assureur régional — produits incluant assurance maladie."},
    {"name": "AMSA IARDT", "segment": "privee_iard", "description": "Assurance maladie incluse dans les produits IARD."},
    {"name": "AXA Assurances Sénégal", "segment": "privee_iard", "description": "Assurances santé individuelles ou entreprise."},
    {"name": "Allianz / SanlamAllianz Sénégal", "segment": "privee_iard", "description": "Couverture santé salariés et particuliers."},
    {"name": "Assurances La Providence du Sénégal", "segment": "privee_iard", "description": "Produits incluant assurance santé."},
    {"name": "Société Africaine d'Assurance et de Réassurance (SAAR IARDT)", "segment": "privee_iard", "description": "Produits variés dont santé."},
    {"name": "La Mutuelle d'Assurances Agricoles du Sénégal (MAAS)", "segment": "privee_iard", "description": "Couverture santé dans certaines formules."},
    {"name": "La Prévoyance Assurances (PA)", "segment": "privee_iard", "description": "Couverture santé."},
    {"name": "Assurance Sécurité Sénégalaise (ASS)", "segment": "privee_iard", "description": "Produits incluant santé."},
    {"name": "SONAM SA et SONAM Mutuelle", "segment": "privee_iard", "description": "Couverture maladie incluse."},
    {"name": "Salama Assurances Sénégal", "segment": "privee_iard", "description": "Acteur local, assurance maladie."},
    {"name": "Compagnie Nationale d'Assurances et de Réassurance des Transporteurs (CNART)", "segment": "privee_iard", "description": "Divers produits d'assurance dont santé selon formules."},
    {"name": "GGA Sénégal — Ma Santé Plus", "segment": "privee_iard", "description": "Assurance santé locale et internationale, garanties modulables."},
    {"name": "Tanel Health (Afiyah by Tanél)", "segment": "digitale", "description": "Assurance santé 100 % digitale, cartes et gestion en ligne."},
    {"name": "Reliance Health Sénégal", "segment": "digitale", "description": "Plateforme de santé digitale et couverture associée."},
    {"name": "Susu Africa", "segment": "digitale", "description": "Assurance santé numérique (familles, diaspora)."},
    {"name": "Sammanté", "segment": "digitale", "description": "Vouchers de santé, prise en charge soins essentiels."},
    {"name": "Munasaili", "segment": "digitale", "description": "Assurance santé numérique, QR code pour accès aux soins."},
    {"name": "Couverture Maladie Universelle (CMU)", "segment": "regime_public", "description": "Dispositif national d'accès aux soins (mutuelles communautaires, régimes solidaires)."},
    {"name": "IPM (Institutions de Prévoyance Maladie)", "segment": "regime_public", "description": "Couverture maladie du secteur privé formel au Sénégal."},
    {"name": "ICAMO (Institution de Coordination de l'Assurance Maladie Obligatoire)", "segment": "regime_public", "description": "Coordination nationale de l'assurance maladie obligatoire."},
    {"name": "CSS (Caisse de Sécurité Sociale)", "segment": "regime_public", "description": "Régime de sécurité sociale — couverture des assurés affiliés."},
    {"name": "Plan Sésame", "segment": "regime_public", "description": "Personnes âgées de 60 ans et plus — consultations, médicaments, paraclinique, hospitalisation."},
    {"name": "IPRES — Institution de Prévoyance Retraite du Sénégal", "segment": "regime_public", "description": "Régime obligatoire secteur privé : retraite et soins des retraités et ayants droit."},
    {"name": "FNR — Fonds National de Retraite", "segment": "regime_public", "description": "Fonctionnaires et agents publics : retraite et couverture santé."},
    {"name": "Mutuelles de santé communautaires (CMU — locales)", "segment": "mutuelle", "description": "Populations non couvertes par régimes obligatoires (informel, rural)."},
    {"name": "MSAE — Mutuelle de Santé des Agents de l'État", "segment": "mutuelle", "description": "Soins complémentaires pour les agents de l'État."},
    {"name": "Mutualités professionnelles et communautaires", "segment": "mutuelle", "description": "Mutuelles sectorielles (professions, groupes sociaux) : loterie nationale, militaires, informel, artisanat, etc."},
    # Section 8 du PDF — programmes / gratuités (pas des polices IARD classiques)
    {
        "name": "Autres initiatives publiques de gratuité / assistance médicale",
        "segment": "programme",
        "description": "Prises en charge gratuites ou subventionnées (politiques sanitaires, populations vulnérables).",
    },
    {
        "name": "Gratuité soins enfants de moins de 5 ans (dispositif public)",
        "segment": "programme",
        "description": "Consultations, médicaments essentiels, vaccinations (selon dispositifs nationaux).",
    },
    {
        "name": "Gratuité césarienne (dispositif public)",
        "segment": "programme",
        "description": "Mesure de gratuité pour femmes enceintes (conditions des structures publiques).",
    },
    {
        "name": "Gratuité dialyse (indications ciblées)",
        "segment": "programme",
        "description": "Prise en charge dialyse pour certaines indications (selon politiques sanitaires).",
    },
]
