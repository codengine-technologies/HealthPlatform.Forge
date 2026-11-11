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

### v0.2 — task-443 : critères médicaux du formulaire (api-mail, dtos-mss, weda2)

- **État** : `archived`, mergée le 2026-11-11 :
  - dtos-mss [#60](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/60) → `96db8c7` ;
  - api-mail [#359](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/359) → `291f7d3b` ;
  - client-angular en code-only, non commité sur `feature/nova-mss-weda-integration`.
- **Contrat** : `HealthPlatform.Dtos.Mss` 584 puis 585 :
  - `SearchFilterFieldDto.FromAddresses` (20 au plus, OU) et `AttachmentName` ;
  - `SearchFilterContentTypeDto.HasAbnormalBiology` ;
  - `SearchSenderDto` ;
  - `SearchFilterDto.HasAnyCriterion()`, seule définition de « au moins un critère ».

  Trois copies avaient divergé : 400 sur une recherche sans texte portant un critère nouveau, et un patient seul jamais
  enregistré dans l'historique.
- **api-mail** :
  - `SemanticSearchRepository.Criteria.cs` : expéditeurs choisis (`lower(FromAddress) = ANY`), nom de pièce jointe
    (`search_normalize(FileName) LIKE` par mot), biologie anormale (`IsFlagged`), `PatientExistsAsync`,
    `ListSendersAsync` ;
  - `MailDataContext.Search.cs` : `search_normalize` déclarée à EF ;
  - patient inconnu → `NotFoundException` (`search_patient_unknown`, 404) ;
  - `GET /api/v1/search/senders` (`[Audited(MailSearch)]`) ;
  - dépendances : Aspire.Hosting 13.6.5 (GHSA-f7vh-h5g3-7jrh), WebUtilities 2.3.14 (GHSA-6527-9fp8-r4x6).
- **weda2** :
  - `mss-mail-search-patient-picker` : `GET /Patients/search` après 300 ms de frappe, Entrée seulement sur un seul
    patient proposé ;
  - `mss-mail-search-sender-picker` ;
  - date du document, nom de pièce jointe, puce « Biologie anormale » ;
  - rejeu avec relecture du nom du patient (`getPatientById`) ;
  - `_mail-search-combobox.scss`.
- **Tests** :
  - `SearchMedicalCriteriaIntegrationTests` : 9 tests, mutations B1–B11 rouges ;
  - `MailboxAccessLockIntegrationTests` : refus de `/search/senders` sans verdict ;
  - unitaires `SearchFilterCriterionTests`, `SemanticSearchServiceMedicalCriteriaTests`, `SearchHistoryServiceTests`,
    `SemanticSearchRepositoryCriteriaTests` ;
  - weda2 : spec du formulaire 42, spec du libellé du patient 5, mutations A1–A11 rouges.

  | Suite | Tests verts |
  |---|---|
  | api-mail domain | 210 |
  | api-mail application | 4 098 |
  | api-mail infrastructure | 743 |
  | api-mail api | 1 375 |
  | api-mail intégration | 1 242 (+16 ignorés) |
  | weda2 | 2 683 |
  | mss-lib | 1 526 |

- **E2E** : `E2E-SEARCH-008` v1, divergence mobile task-451. Voie mobile 60, voie angular 74, parité verte. Deux passages
  rouges corrigés dans le test :
  - lignes CDA et HPRIM désignées par l'objet du message (récidive de `ligne-de-cda`) ;
  - hypothèse fausse sur le seed : le CDA de `PAT-TROIS` porte une thyroxine marquée.
- **Sonar** : 2 itérations, 4 issues de nouveau code corrigées (CA1862, xUnit1045 ×3). Quality Gate OK, couverture
  97,8 %, nouveau code 96,0 %.
- **Restes** :
  - la recherche de patients ne porte que sur le nom ;
  - le nom de pièce jointe ne lit pas l'index trigramme (à mesurer) ;
  - « De » et « Expéditeurs » se combinent en ET (question produit).
- **Préventions** :
  - `conventions/csharp.md` : `critere-de-recherche-sur-toutes-les-sources` ; CA1862 variante EF ; xUnit1045 (3) ;
  - `conventions/e2e.md` : `ligne-de-cda` élargie au HPRIM (3).

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle dans E023 |
|---|---|
| `Client/Angular/front/libs/mss/src/features/mail/components/mail-search/` | Barre et formulaire de recherche de weda2 (task-442), sélecteurs patient et expéditeurs (task-443) |
| `Api/Mail/src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.Criteria.cs` | Critères médicaux et liste des expéditeurs (task-443) |
| `Api/Mail/src/Api/Controllers/V1/SearchController.cs` | `GET /api/v1/search/senders` (task-443) |
| `Dtos/SearchFilter*.cs`, `Dtos/SearchSenderDto.cs` | Contrat des critères, `HasAnyCriterion` (task-443) |
| `Api/Mail/e2e/scenarios.yml` | Catalogue des parcours : `E2E-SEARCH-001` v2 |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-11)

*À compléter au fil des tasks.*

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | État | Contribution |
|---|---|---|
| task-442 | archived (PR #358 mergée) | Formulaire de critères à un seul niveau dans weda2 ; `E2E-SEARCH-001` v2 ; « De » choisi parmi les contacts |
| task-443 | archived (PRs dtos-mss #60, api-mail #359 mergées) | Critères médicaux : patient, date du document, biologie anormale, expéditeurs, nom de pièce jointe ; `E2E-SEARCH-008` v1 |
| task-444 | todo | Réponse enrichie : extraits, endroit trouvé, patients trouvés |
| task-445 | todo | Mode « Résultats de recherche » dans weda2 |
| task-446 | todo | Lire un résultat : extrait surligné et patients trouvés |
| task-447 | todo | Portée « tous les dossiers » et tri |
| task-448 | todo | Sélectionner tous les résultats et actions groupées |
| task-449 | todo | Suggestions pendant la frappe : patients et messages |
| task-452 | todo | Mesure anonyme de l'expérience |
