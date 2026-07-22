# Règles — Méthode BMAD (MedCare Connect)

Ce document fixe la **méthode de travail obligatoire** pour toute évolution du produit : maintenance, nouvelles fonctionnalités et préparation au **scale**. Il complète les fichiers de référence du dossier `ressources/`.

---

## 1. Objet des documents `ressources/`

| Fichier | Rôle |
|---------|------|
| `prd.md` | Périmètre fonctionnel, règles métier, acteurs, parcours, URLs nommées — **contrat produit**. |
| `tech.md` | Stack, config, apps Django, modèles, routage, intégrations, points d’attention — **contrat technique**. |
| `FONCTIONNALITES_ET_PARCOURS_TESTS.md` | Onboarding dev, parcours de test ; à aligner quand l’UX ou les parcours changent significativement. |
| `rules.md` (ce fichier) | Méthode BMAD et obligations de documentation. |

**Règle d’or** : une modification de code qui change le comportement attendu, l’architecture ou les dépendances **doit** se refléter dans `prd.md` et/ou `tech.md` selon le cas (voir §4).

---

## 2. Définition de la méthode BMAD (projet)

Les quatre phases s’enchaînent pour **chaque** lot de travail (ticket, feature, correctif structurant) :

| Lettre | Phase | Signification | Actions typiques |
|--------|--------|---------------|-------------------|
| **B** | **Baser** | Ancrer dans le réel | Lire `prd.md` et `tech.md` ; identifier les modules, URLs et modèles concernés ; vérifier les contraintes métier (rôles, unicités, APIs). |
| **M** | **Modéliser** | Anticiper l’impact | Lister fichiers à toucher, effets de bord (migrations, templates, context processor, permissions) ; décider si le scope reste minimal. |
| **A** | **Agir** | Implémenter proprement | Coder en respectant les conventions du dépôt ; migrations versionnées ; pas de refactor gratuit hors sujet. |
| **D** | **Documenter** | Figer l’état pour la suite | Mettre à jour `prd.md` et `tech.md` **si** le périmètre fonctionnel ou technique a changé ; mettre à jour les parcours/tests dans `FONCTIONNALITES_ET_PARCOURS_TESTS.md` si l’utilisateur final est impacté. |

**BMAD n’est pas optionnel** pour les changements qui ne sont pas du typage cosmétique local (ex. renommage de variable interne sans effet observable).

---

## 3. Obligations avant toute modification

1. **Lire** `ressources/prd.md` pour les zones concernées (module, règle métier, URL).
2. **Lire** `ressources/tech.md` pour la stack, les apps, les points d’attention et les intégrations (ex. Nominatim, bundle, proxy).
3. **Parcourir** le code existant dans les fichiers cibles (pas d’hypothèse sur des APIs non lues).
4. Si le changement touche un **parcours utilisateur** ou une **procédure de test**, prévoir la mise à jour de `FONCTIONNALITES_ET_PARCOURS_TESTS.md` en phase **D**.

---

## 4. Obligations après toute modification

1. **Mettre à jour `ressources/prd.md`** si au moins un des points suivants est vrai :
   - nouvelle ou suppression de fonctionnalité visible ;
   - changement de règle métier (ex. statuts, droits, unicités) ;
   - nouvelle URL nommée ou API exposée ;
   - modification du comportement du context processor global ou des redirections login.

2. **Mettre à jour `ressources/tech.md`** si au moins un des points suivants est vrai :
   - nouveau module Python, dépendance pip, ou variable d’environnement ;
   - nouveau modèle, champ, migration structurante ;
   - changement de routage, middleware, ou fichier d’intégration (ex. `nominatim`, `bundle_planner`) ;
   - évolution du déploiement (Docker, Gunicorn, staticfiles) ;
   - nouveau script ou outil de build (CSS, tests).

3. **Mettre à jour `FONCTIONNALITES_ET_PARCOURS_TESTS.md`** si les étapes de test ou les URLs de parcours ne correspondent plus au produit.

4. **Vérifier la cohérence** : `prd.md` et `tech.md` ne doivent **pas** se contredire ; en cas de doute, le code déployé et les migrations font foi jusqu’à correction documentaire.

---

## 5. Granularité et anti-patterns

- **À jour** ne signifie pas recopier tout le code : des **ajouts ciblés** ou un **paragraphe de changelog** en tête de section suffisent si la structure du doc le permet.
- **Ne pas** laisser `prd.md` / `tech.md` décrire une ancienne version alors que la branche principale a divergé.
- **Ne pas** dupliquer massivement : renvoyer entre sections plutôt que copier-coller des listes d’URL à l’infini (une table ou une référence « voir `urls.py` » peut suffire dans `tech.md` si déjà documenté).

---

## 6. Scale et maintenance

- **Scale** (montée en charge, nouveaux environnements, équipe élargie) : toute décision qui ajoute un service (cache, file queue, autre base) est **documentée dans `tech.md`** avec variables d’env et impacts déploiement.
- **Maintenance** : les correctifs qui masquent un bug métier doivent **corriger le PRD** si la spec était ambiguë, pour éviter de réintroduire l’erreur.

---

## 7. Résumé opérationnel (check-list)

**Avant** de coder :

- [ ] `ressources/prd.md` relu (sections pertinentes)
- [ ] `ressources/tech.md` relu (sections pertinentes)
- [ ] Périmètre du ticket clarifié (BMAD **B** + **M**)

**Après** le merge ou la livraison :

- [ ] `prd.md` mis à jour si le produit a changé
- [ ] `tech.md` mis à jour si la technique a changé
- [ ] `FONCTIONNALITES_ET_PARCOURS_TESTS.md` si besoin
- [ ] Aucune contradiction entre les trois niveaux (produit / tech / tests manuels)
- [ ] **Déploiement sur le serveur** : après modification du code Python / templates / static nécessitant un rechargement de l’app, **redémarrer Gunicorn** MedCare Connect :  
  `sudo systemctl restart medcareconnect`  
  (service systemd `medcareconnect.service` — écoute en général sur `127.0.0.1:8020` derrière Apache.)

---

*Document vivant : toute évolution de la méthode d’équipe doit modifier ce fichier en premier.*
