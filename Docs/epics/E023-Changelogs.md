# E023 — Expérience de recherche — Changelogs

> **Audience** : équipes techniques (ingénierie, backlog, dette)
> **Vue produit** : [E023-experience-de-recherche.md](E023-experience-de-recherche.md)
> **Dernière mise à jour** : 2026-11-11

---

## Historique détaillé des changelogs

### v0.1 — task-442 : formulaire de critères à un seul niveau (weda2)

- **État** : `done`, PR en attente de merge humain (HAG).
- **PR** : api-mail [#358](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/358)
  (catalogue e2e seul). client-angular en code-only : non commité sur `feature/nova-mss-weda-integration`, PR TFS à la
  main de l'humain.
- **Fichiers (client-angular)** : `libs/mss/src/features/mail/components/mail-search/mail-search.component.{ts,html,scss,spec.ts}`,
  `e2e/mss-e2e/specs/functional.e2e.ts`.
- **Comportement** :
  - panneau « Recherche avancée » retiré (`showAdvanced`, `openAdvanced`, `closeAdvanced`, `applyAdvancedAndSearch`) ;
  - les bascules ne lancent plus `executeSearch` ;
  - `launch()` lance puis ferme, et `canLaunch` le désactive sans critère ; Entrée appelle `launch()` ;
  - `resetParameters()` vide sans fermer ni lancer ;
  - l'instantané `appliedCriteria` (`SearchCriteria`) est restauré par `closeDropdown()` : le brouillon est abandonné ;
  - les requêtes persistées passent par la fonction pure `criteriaFromRequest` ;
  - pied collant avec deux `ds-button` (`mail-search-reset`, `mail-search-launch`) ; `aria-pressed` sur les puces.
- **Tests** : spec du composant 18 tests ; mutations M1–M7 toutes rouges. Les totaux sont pris en `/review`, avec le
  code de la task.

  | Suite | Tests verts |
  |---|---|
  | weda2 | 2 683 |
  | mss-lib | 1 497 |
  | api-mail domain | 210 |
  | api-mail application | 4 054 |
  | api-mail infrastructure | 737 |
  | api-mail api | 1 375 |
  | api-mail intégration | 1 232 (+16 ignorés) |

- **E2E** : `E2E-SEARCH-001` passe en version 2 (« Composer ses critères puis lancer la recherche »).
  - Divergence temporaire `mobile` jusqu'à task-450 : le test mobile reste en v1.
  - Voie mobile : 60 tests verts. Voie Angular : 73 tests verts, au 2ᵉ passage. Le 1ᵉʳ passage s'est arrêté en code 2
    au montage du backend ; la cause est perdue, car le rejeu a écrasé `backend.log`.
  - Parité verte. Quarantaine : E2E-COMPOSE-002 (task-350).
- **Sonar** (api-mail) :
  - Quality Gate OK, 0 issue nouvelle ou ancienne.
  - Couverture 97,8 %, nouveau code 96,0 %, duplication 0,4 %, notes A/A/A.
  - L'analyse coûte 11 min 25 s alors que le scanner ne voit pas `scenarios.yml`.
- **Lint** : 0 erreur, aucune itération ; `max-lines` sur le composant (723 → 789 lignes, déjà au-dessus de 500).
- **Prévention** : `conventions/angular.md` § `formulaire-qui-lance-avant-son-bouton`.
- **Règle 1b** : aucun comportement d'endpoint modifié ; le parcours est prouvé par `E2E-SEARCH-001` v2.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle dans E023 |
|---|---|
| `Client/Angular/front/libs/mss/src/features/mail/components/mail-search/` | Barre et formulaire de recherche de weda2 (task-442) |
| `Api/Mail/e2e/scenarios.yml` | Catalogue des parcours : `E2E-SEARCH-001` v2 |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-11)

*À compléter au fil des tasks.*

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | État | Contribution |
|---|---|---|
| task-442 | done (PR #358) | Formulaire de critères à un seul niveau dans weda2 ; `E2E-SEARCH-001` v2 |
| task-443 | todo | Critères médicaux du formulaire |
| task-444 | todo | Réponse enrichie : extraits, endroit trouvé, patients trouvés |
| task-445 | todo | Mode « Résultats de recherche » dans weda2 |
| task-446 | todo | Lire un résultat : extrait surligné et patients trouvés |
| task-447 | todo | Portée « tous les dossiers » et tri |
| task-448 | todo | Sélectionner tous les résultats et actions groupées |
| task-449 | todo | Suggestions pendant la frappe : patients et messages |
| task-452 | todo | Mesure anonyme de l'expérience |
