# E022 — Recherche fiable — Changelogs

> **Audience** : équipes techniques (backlog, dette, revue de PR).
> **Vue produit** : [E022-recherche-fiable.md](E022-recherche-fiable.md)
> **Dernière mise à jour** : 2026-11-10

---

## Historique détaillé des changelogs

### v0.1 — task-438 : le filet d'abord, un corpus et des requêtes de référence (2026-11-10)

- **PRs** : api-mail [#354](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/354), client-mobile
  [#122](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/122), label `awaiting-human-merge` ;
  client-angular code-only, `front/e2e/mss-e2e/specs/functional.e2e.ts` non commité sur `feature/nova-mss-weda-integration`.
- **NuGet** : aucun (pas de changement de contrat).
- **Origine** : campagne du 2026-11-09 sur la boîte de formation de Virginie (11 178 mails), défauts R1 à R9,
  `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`.
- **Filet** (`Api/Mail/tests/mss.mail.integration.tests/Search/Reference/`) :
  - corpus fictif de 560 messages, dont 30 porteurs d'embeddings réels (`text-embedding-3-small`, 48 vecteurs
    pré-calculés dans `search-reference-embeddings.json`, aucun appel externe en test) ;
  - 18 requêtes × 2 profils (weda2 `minSimilarity` 0,7, mobile 0,1), en mode hybride, 50 résultats, sur
    `POST /api/v1/Search/semantic` à travers la vraie pile ;
  - verdict selon quatre règles (rappel, tous les mots d'abord, mot absent, dossier courant) et tableau
    `search-reference-report.md`.
- **Défauts prouvés rouges** (`SEARCH_REFERENCE_KNOWN_DEFECTS=1`) : 11 sur 36, marqués avec la task qui les corrige.
  - task-439 : accent, majuscules, objet, ponctuation (weda2) ; expéditeur, pièce jointe, patient au long historique
    (deux profils) ;
  - task-440 : mot absent (mobile).
- **Mutation des verts** : `SemanticSearchRepository.InFolder` sans filtre de dossier → 14 cas verts tombent.
- **e2e** : `E2E-SEARCH-002` v1 (mot rare accentué) et `E2E-SEARCH-003` v1 (numéro de dossier), requis sur mobile et
  Angular, seed `mail-non-lu-2` (`E2eSeedMessage.ExtraBodyText`). Mutation « le plein texte ne lit plus le corps »
  (`lower(d."Body")` → `lower(left(d."Body", 0))`) : 002 et 003 rouges sur les deux clients, 0 résultat au lieu de 1,
  alors qu'`E2E-SEARCH-001` restait vert.
- **Outillage** : `tests/search-quality/embed_corpus.py` (embeddings manquants), `tests/search-quality/campagne.py`
  (campagne sur une boîte de développement, API locale et session réelle seulement, jamais le test-bypass).
- **Tests** :
  - api-mail : domain 210, infrastructure 728, application 4 031, api 1 378, intégration 1 166 (+ 28 écartés), 0 échec ;
    `ImapServiceTests` instable connu, rejoué isolé ;
  - client-mobile : 1 417 tests ;
  - weda2 et mss-lib : 107 + 136 fichiers de test ;
  - e2e : mobile 60, Angular 73, parité verte.
- **Sonar** : Quality Gate OK.
  - Baseline : 0 bug, 0 vulnérabilité, 0 code smell, couverture 97,9 %.
  - Après correction : CA1859 ×3 corrigés, et 1 `xUnit1004` assumé sur `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails`.
    Ce test fige R3 ; il reste marqué task-439, qui le réécrit.
- **Préventions** :
  - `conventions/csharp.md` : `recherche-jugee-comme-un-medecin`, CA1859 (17 occurrences), xUnit1004 ;
  - `conventions/e2e.md` : ligne « trou du filet » de la recherche ;
  - `agents/sonar.md` : un `Skip` qui cite une task n'est jamais retiré.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Fichiers |
|---|---|
| Filet de référence | `Api/Mail/tests/mss.mail.integration.tests/Search/Reference/` (`SearchReferenceCorpus`, `SearchReferenceOracle`, `SearchReferenceQueries`, `SearchReferenceVerdict`, `SearchReferenceFixture`, `SearchReferenceQualityTests`, `PrecomputedEmbeddings`) |
| Moteur de recherche (inchangé) | `Api/Mail/src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs`, `Api/Mail/src/Application/Services/Implementation/SemanticSearchService.cs`, `SearchQueryHelper` |
| Seed et catalogue e2e | `Api/Mail/tests/mss.mail.testing.shared/E2eSeedPlan.cs`, `Api/Mail/e2e/scenarios.yml` |
| Parcours e2e | `Client/Mobile/e2e/specs/functional.spec.ts`, `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` |
| Outillage | `Api/Mail/tests/search-quality/` |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-10)

- Requêtes de référence : 18, sur 2 profils, soit 36 cas. 25 verts, 11 défauts connus marqués (task-439 : 10, task-440 : 1).
- Parcours e2e de recherche : 3 (`E2E-SEARCH-001` à `003`), sur 2 clients.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | Règles |
|---|---|---|---|
| task-438 | done (PRs ouvertes) | Filet : corpus et requêtes de référence, E2E-SEARCH-002/003, outil de campagne | RG-E022-01 à 05 mesurées |
| task-439 | todo | Plein texte : accents, champs, tous les mots, tout l'historique (absorbe task-436) | RG-E022-01, 02, 03 |
| task-440 | todo | Sémantique : exacts d'abord, proches ensuite, seuil unique serveur | RG-E022-04 |
| task-441 | todo | Clients weda2 et mobile fidèles au serveur | RG-E022-04 (affichage) |
