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

### v0.3 — task-444 : réponse enrichie — extraits, endroit trouvé, patients trouvés (api-mail, dtos-mss)

- **État** : `archived`, PRs mergées : dtos-mss [#61](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/61),
  api-mail [#360](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/360).
- **Contrat** : `HealthPlatform.Dtos.Mss` 588, rétrocompatible :
  - `SearchHitDto.Locations` (`SearchMatchLocation`), `Excerpt` (≤ 200), `ExcerptLocation`, `Highlights`
    (`SearchHighlightDto`, unités UTF-16) ;
  - `SearchResponseDto.Patients` (`SearchFoundPatientDto`, ≤ 5, sans INS, `IsInsQualified`) et `IsPatientsTruncated`.
- **api-mail** :
  - `SearchExcerpts`, `SearchHitEnrichment` : endroit et extrait en un passage par texte, positions tolérantes
    (repli caractère par caractère avec position source) ;
  - `PatientQuery` : correspondance exacte (nom/prénom, nom + date, INS) ;
  - `SemanticSearchRepository.Explain.cs` : textes de la page (filtre exact dossier + UID), candidats patients (nom
    plié par `regexp_replace(search_normalize(…))`, `MailDataContext.RegexpReplace`), INS comparée sans être lue ;
  - `SemanticSearchService` : étape 6, politique unique de mode dégradé (`excerpts`, `patients`) ; une INS n'est jamais
    envoyée au fournisseur d'embeddings ; `SearchHistoryService` ne garde jamais une requête INS ;
  - `SearchResultHelper.ToResponse` ; `MailKey` sorti du service vers les modèles.
- **Tests** : `SearchEnrichedResponseIntegrationTests` (8, mutations B1–B11 rouges, rejouées après la passe qualité) ;
  unitaires `SearchExcerptsTests`, `PatientQueryTests`, `SearchHitEnrichmentTests`,
  `SemanticSearchServiceEnrichmentTests`, `SearchHistoryServiceTests`.

  | Suite | Tests verts |
  |---|---|
  | api-mail domain | 210 |
  | api-mail application | 4 193 |
  | api-mail infrastructure | 743 |
  | api-mail api | 1 375 |
  | api-mail intégration | 1 250 (+16 ignorés) |

- **Coût** (`Docs/audits/findings/plans/20261111-task-444/`) : page de 50 sur la copie `srch_lab` (11 291 messages) :
  +21,4 ms au p50, +45,9 ms au p95.
- **E2E** : aucun parcours modifié. Voie mobile 60, voie angular 74, parité verte.
- **Sonar** : 2 itérations ; SYSLIB1045 et hotspot S6444 (regex dans une requête EF) corrigés par la fonction
  PostgreSQL déclarée à EF. Quality Gate OK, couverture 97,8 %, nouveau code 96,2 %.
- **Restes** :
  - nom de naissance et nom d'utilisation non distingués (un seul champ `LastName`) ;
  - clients : extrait à rendre en texte, `isDegraded` pas encore lu ;
  - `MailCount` compte la Corbeille.
- **Préventions** : `conventions/csharp.md` § `identite-patient-exacte` ; SYSLIB1045 variante EF (5).

---

### v0.4 — task-445 : mode « Résultats de recherche » (weda2, api-mail)

- **État** : `done`, PR api-mail [#361](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/361) en
  attente de merge humain (HAG) ; weda2 code-only, non commité (à commiter sur TFS **avant** le merge de #361 :
  `functional.e2e.ts`, `support/e2e-backend.ts`).
- **weda2** (`libs/mss/src/features/mail/`) :
  - `services/mail-search-session.ts` : `MailSearchSession` tenue par `MailStateService` — requête, lignes dans l'ordre
    du serveur, rattachement par dossier et UID (`hits`, messages lus dans leur dossier), parties par `matchGroup`,
    « N+ » (`isTruncated`), « Voir plus » (`offset` = résultats rendus par le serveur, dédoublonné), `isDegraded`,
    erreur qui vide la liste, réponse dépassée abandonnée, squelette > 300 ms ;
  - `services/mail-search-tags.ts` : étiquettes lues dans la requête, retrait, affinage ;
  - `components/mail-search-results/` : étiquettes, filtres d'affinage, bandeaux, parties, « Voir plus » ;
  - `mail-list` : en-tête du mode, « Fermer la recherche » (filtre, page, position rendus, sans rechargement) ;
  - `mail-search` : plus de croix, lance la session, suit la recherche affichée ; `minSimilarity` n'est plus envoyé ;
  - Paramètres : section « Avancé » (sensibilité) retirée.
- **api-mail** : catalogue `E2E-SEARCH-004` à `007` et `009` v1 (angular requis, mobile en divergence task-450) ; seed
  du patient fictif cherché et son test.
- **Tests** : `mail-search-session.spec.ts`, `mail-search-tags.spec.ts`, `mail-list.search-mode.spec.ts` ; mutations
  M1–M16 (composants) et E1–E6 (parcours) rouges sur l'assertion prévue.

  | Suite | Tests verts |
  |---|---|
  | weda2 `mss-lib` | 1 573 |
  | weda2 `weda2` | 2 683 |
  | api-mail (toutes suites) | 7 788 (+16 ignorés) |

- **E2E** : voie mobile 60, voie angular 79, parité verte.
- **Sonar** : 0 itération, Quality Gate OK, couverture 97,8 %, nouveau code 96,3 %.
- **Restes** (revue, non bloquants) : l'annulation d'un glisser vers la Corbeille n'est pas reportée dans les
  résultats ; position rendue au dossier suivant dans un cas limite ; enrichissement en direct ignoré hors du dossier
  affiché ; deux assertions de test à durcir ; étiquette de période approximative au rejeu.
- **Préventions** : `conventions/angular.md` § `liste-ordonnee-par-le-serveur`, § `retrait-optimiste-dans-chaque-liste`.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle dans E023 |
|---|---|
| `Client/Angular/front/libs/mss/src/features/mail/components/mail-search/` | Barre et formulaire de recherche de weda2 (task-442), sélecteurs patient et expéditeurs (task-443) |
| `Api/Mail/src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.Criteria.cs` | Critères médicaux et liste des expéditeurs (task-443) |
| `Api/Mail/src/Api/Controllers/V1/SearchController.cs` | `GET /api/v1/search/senders` (task-443) |
| `Dtos/SearchFilter*.cs`, `Dtos/SearchSenderDto.cs` | Contrat des critères, `HasAnyCriterion` (task-443) |
| `Api/Mail/src/Application/Helpers/{SearchExcerpts,SearchHitEnrichment,PatientQuery}.cs` | Extraits, endroits trouvés, patients désignés (task-444) |
| `Api/Mail/src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.Explain.cs` | Textes de la page, candidats patients (task-444) |
| `Dtos/SearchMatchLocation.cs`, `Dtos/SearchHighlightDto.cs`, `Dtos/SearchFoundPatientDto.cs` | Contrat de la réponse enrichie (task-444) |
| `Client/Angular/front/libs/mss/src/features/mail/services/mail-search-{session,tags}.ts` | Mode « Résultats de recherche » : session, étiquettes (task-445) |
| `Client/Angular/front/libs/mss/src/features/mail/components/mail-search-results/` | Espace des résultats : étiquettes, affinage, parties, « Voir plus » (task-445) |
| `Api/Mail/e2e/scenarios.yml` | Catalogue des parcours : `E2E-SEARCH-001` v2, `004` à `009` v1 |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-11)

*À compléter au fil des tasks.*

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | État | Contribution |
|---|---|---|
| task-442 | archived (PR #358 mergée) | Formulaire de critères à un seul niveau dans weda2 ; `E2E-SEARCH-001` v2 ; « De » choisi parmi les contacts |
| task-443 | archived (PRs dtos-mss #60, api-mail #359 mergées) | Critères médicaux : patient, date du document, biologie anormale, expéditeurs, nom de pièce jointe ; `E2E-SEARCH-008` v1 |
| task-444 | archived (PRs dtos-mss #61, api-mail #360 mergées) | Réponse enrichie : endroit trouvé, extrait surligné, patients trouvés par correspondance exacte |
| task-445 | done (PR api-mail #361 ; weda2 non commité) | Mode « Résultats de recherche » dans weda2 ; `E2E-SEARCH-004` à `007`, `009` v1 |
| task-446 | todo | Lire un résultat : extrait surligné et patients trouvés |
| task-447 | todo | Portée « tous les dossiers » et tri |
| task-448 | todo | Sélectionner tous les résultats et actions groupées |
| task-449 | todo | Suggestions pendant la frappe : patients et messages |
| task-452 | todo | Mesure anonyme de l'expérience |
