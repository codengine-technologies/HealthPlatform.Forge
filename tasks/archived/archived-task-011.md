# todo-task-011.md — Indicateur document deja integre

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune
**Single frontend**: false
**Epic**: E009

## Objectif

Le systeme doit informer le professionnel lorsqu'un document medical recu par MSSante
a deja ete rattache au dossier patient, afin d'eviter les doublons et de savoir d'un
coup d'oeil quels documents restent a traiter.

## Contexte

Le modele `MailMedicalDocument` possede un champ `EnrichmentStatus` qui trace l'etat
du traitement et un champ `PatientId` (nullable) qui indique le rattachement a un
patient. Le rattachement se fait via l'INS extrait du `METADATA.XML` de l'archive
IHE_XDM (conformement a ECO.2.1.2 du Ref#2).

Il manque un indicateur visuel dans l'interface pour que le professionnel distingue,
dans la liste des messages, ceux dont les documents ont deja ete traites de ceux qui
restent en attente.

## Critere d'integration

Un document est considere comme "integre" si `MailMedicalDocument.PatientId` est
non null (le document est rattache a un patient dans la base).

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/IndicateurDocumentIntegre.feature`

## Exigence Segur couverte

- LGC.MDV.06 — Informer que le document a deja ete integre

## References reglementaires

- REM Segur LGC.MDV.06
- Referentiel socle MSSante #2 v1.0.1 — ECO.2.1.2 (identification du patient par
  `patientId` dans METADATA.XML)

## Definition of Done

- [ ] Build passes (0 errors) sur `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Indicateur visuel dans la liste des messages : distinguer les messages dont
  tous les documents sont rattaches (integres) de ceux qui ont des documents
  en attente
- [ ] Indicateur visuel par document dans le detail du message : rattache / en attente
- [ ] Critere d'integration : `MailMedicalDocument.PatientId` non null
- [ ] L'indicateur se met a jour dynamiquement apres un rattachement patient
- [ ] Blazor : indicateur dans la liste des messages + par document dans le detail
- [ ] Angular : indicateur dans la liste des messages + par document dans le detail
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Recevoir un message avec un document CDA rattache automatiquement a un patient
  (INS connu dans `MailPatient`)
  - Verifier dans la liste : indicateur "integre" (icone, badge vert, etc.)
  - Ouvrir le message → verifier l'indicateur sur le document
- Recevoir un message avec un document CDA dont le patient n'est pas identifie
  - Verifier dans la liste : indicateur "en attente" (icone, badge orange, etc.)
- Recevoir un message avec 2 documents : 1 rattache, 1 non rattache
  - Verifier dans le detail : indicateurs differents par document
  - Rattacher manuellement le 2e document → verifier que l'indicateur se met a jour
- Repeter sur les deux frontends (Blazor et Angular)

## Branches

- `api-mail` (pushed, scope-extended via questions/task-011.md option A on 2026-04-28) : feat/task-011-indicateur-document-integre — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-011-indicateur-document-integre
- `client-blazor` (pushed) : feat/task-011-indicateur-document-integre — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-011-indicateur-document-integre
- `dtos-mss` (pushed, auto-included) : feat/task-011-indicateur-document-integre — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-011-indicateur-document-integre
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` — humain gère branche, commit, push, PR TFS. Snapshot at /start : branch `feature/nova-rewriting-mss-fixes-20260410`, working tree clean.

## Develop log

- Repos touched : `dtos-mss`, `api-mail`, `client-blazor`, `client-angular` (code-only)
- DTOs published : 210.0.0 → 215.0.0 (CI run 25036715621)
- Interop published : no interop change
- Commits :
  - `dtos-mss`     : 4b74fd3 feat(dto): expose PatientId and PendingIntegrationsCount (task-011)
  - `api-mail`     : 5f84677 chore(deps): bump HealthPlatform.Dtos.Mss to 215.0.0
  - `api-mail`     : 7b0e673 feat(mail): expose document patient attachment status (task-011)
  - `client-blazor`: e0488af feat(mss): integration indicator on inbox row + per-document tab badge (task-011)
  - `client-angular`: **uncommitted** — code-only mode, humain gère commit/push TFS. Files modified :
    - `front/libs/mss/src/core/models/mail.model.ts` (added `patientId?` + `pendingIntegrationsCount?`)
    - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts` (3 new getters)
    - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html` (indicator markup with `data-testid` hooks)
    - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss` (badge styling)
    - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts` (per-document `integrationStatus` on tabs)
    - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.html` (per-tab badge markup)
    - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.spec.ts` (3 new vitest tests, **new file**)
- Local build / test :
  - api-mail : 0 errors / 1622 passed (21 env-skipped, 0 failures)
  - client-blazor : 0 errors / 18 passed (15 existing + 3 new bUnit, 0 failures)
  - dtos-mss : 0 errors
  - client-angular : `npx nx run mss-lib:test` 85 / 85 passed (82 existing + 3 new vitest, 0 failures), `tsc --noEmit` 0 errors. **Note** : `npx nx run mss:build` fails on `weda2:build:production` — pre-existing budget violation on the branch, verified by stash+rebuild before applying task-011 changes (same failure). Same for `mss-lib:lint` (1676 errors pre-existing). The human triages these independently of task-011.
- DOD self-check :
  - Build passes (0 errors) sur `client-blazor`, `client-angular` (mss-lib component compile + tests) ✓ ; `api-mail` (added in scope per questions/task-011.md option A) ✓
  - Tests pass (0 failures) sur tous les repos ✓
  - Indicateur visuel dans la liste des messages — `mail-integration-indicator-integrated` / `-pending` data-testid sur Blazor (MailHeader) + Angular (mail-header) ✓
  - Indicateur visuel par document dans le détail — `document-integration-indicator-integrated` / `-pending` sur Blazor (MailBodyComponent tab) + Angular (mail-body tab) ✓
  - Critère d'intégration `MailMedicalDocument.PatientId` non null — exposé via `MailMedicalDocumentDto.PatientId` (DTO) et agrégé via `MailDto.PendingIntegrationsCount` ✓ (3 tests d'intégration `MailRepositoryTests`)
  - Indicateur dynamique après rattachement — couvert par recomputation server-side à chaque GetMailAsync ; le frontend rafraîchit le mail après une action (mécanisme préservé) ✓
  - Blazor : indicateur dans la liste + détail ✓
  - Angular : indicateur dans la liste + détail ✓ (uncommitted, humain handles commit/push TFS)
  - ≥ 1 test par scénario Gherkin — couvert par 3 tests xUnit + 3 bUnit + 3 vitest sur les 3 scénarios (all-integrated, pending-with-count, no-medical-documents) ✓
  - Aucune régression — full suites green sur tous les repos ✓
- Operational note : task-011 a démarré avec `**Repos**: client-blazor, client-angular`. La forge a halté en early-/develop pour scope ambiguity (le DOD requiert `MailMedicalDocument.PatientId` mais le DTO ne l'exposait pas, mapping backend nécessaire). Humain a tranché Option A → ajout de `api-mail` au `**Repos**:`. Branche `api-mail` créée a posteriori. Documenté dans `questions/task-011.md`.
- Next step : /sonar (api-mail)

## Sonar log

- Mode : A (chained from /develop, reuses `feat/task-011-indicateur-document-integre`)
- Iterations : 0 / 5 (best-effort early-stop)
- SonarQube : v25.6.0 sur `http://localhost:9001`, project key `healthplatform`

### Baseline (snapshot)

| Métrique | Valeur | Hard target |
|---|---|---|
| Bugs | 0 | 0 ✓ |
| Vulnerabilities | 0 | 0 ✓ |
| Maintainability rating | A (1.0) | A ✓ |
| Coverage | 50.2 % | ≥ 95 % ❌ |
| Reliability rating | A | — |
| Security rating | A | — |
| Security hotspots | 9 | — |
| Code smells | 728 | — |
| Duplication | 4.4 % | — |
| NCLOC | 27 790 | — |

Coverage progresse de +0.6 pt (49.6 % → 50.2 %) grâce aux 3 nouveaux tests
d'intégration `MailRepositoryTests` ajoutés par task-011.

### Stop reason — best-effort acceptance, 0 productive iteration

Filtered issues attributable to task-011 changes : `Sonar API search` returned 19
issues sur les 3 fichiers touchés (`MailRepository.cs`, `PatientRepository.cs`,
`MailRepositoryTests.cs`), toutes pré-existantes :

- 11 × `CA1873` (logger.IsEnabled guards) — INFO. Excluded per task-001 et
  task-014 precedent : "low-value-per-diff, awaiting team logging policy".
- 5 × `S3776` (cognitive complexity) — **BLACKLISTED** in
  `agents/sonar-blacklist.yml` ; handled by `/sonar-s3776` one method at a time.
- 1 × `S6617` at `MailRepository.cs:1825` — pré-existant, hors zone task-011
  (mes changes sont aux lignes ~480-500, ~880-900).
- 1 × `S1192` at `MailRepository.cs:1315` — pré-existant, literal 'INBOX' x 4
  (hors zone task-011).
- 1 × `CA1822` (`ProcessPatientSummary` could be static) — pré-existant.

Total fixable in scope : 0. Hard targets `bugs = 0`, `vulnerabilities = 0`,
`sqale_rating = A` remain preserved. Coverage 50.2 % unchanged from the
project baseline (other than the +0.6 pt task-011 contribution itself).
Closing the 45-point coverage gap is not achievable in a single feature task —
project-level initiative.

Hand-off : /review.

## Code Review Summary

✅ APPROVED — 1 observation non-blocking.

- **Correctness** : DTO additif (zéro breaking change) ; `RenderIntegrationIndicator` côté Blazor centralise la logique des 2 layouts ; agrégation in-memory sur les documents déjà chargés (no N+1) ; mapping aux 3 sites repository couvert par tests d'intégration.
- **Security** : aucun input externe nouveau, pas de secret, pas d'injection.
- **Architecture** : repository pattern préservé, signature DTO additive, séparation smart/dumb maintenue côté front.
- **Code Quality** : XML doc / JSDoc partout, commentaires "pourquoi" (LGC.MDV.06 référencé), pas de duplication.
- **Performance** : agrégation in-memory `medDocs.Count(d => d.PatientId == null)` sur collection déjà loaded ; coût négligeable.
- **Test Coverage** : 9 tests sur 3 scénarios (3 xUnit `MailRepositoryTests` + 3 bUnit `MailHeaderIntegrationIndicatorTests` + 3 vitest `mail-header.component.spec.ts`). Coverage projet : 49.6 % → 50.2 %.
- **Observation (non-blocking)** : les libellés français des badges Angular sont hardcodés (vs. `Localizer` côté Blazor). Cohérent avec les voisins du même fichier mais à aligner si i18n stricte devient nécessaire.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/10  (label `awaiting-human-merge`)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/32  (label `awaiting-human-merge`)
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/37  (label `awaiting-human-merge`)
- `client-angular` : **code-only** — humain gère commit/push TFS et ouverture PR. Branche en cours : `feature/nova-rewriting-mss-fixes-20260410`. 7 fichiers modifiés (uncommitted) :
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.html`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.spec.ts` (nouveau)

> **Merge order** : `dtos-mss` PR #10 d'abord (le `Directory.Packages.props` d'`api-mail` et `client-blazor` sont pinned sur 215.0.0 produit par cette PR), puis `api-mail` PR #32, puis `client-blazor` PR #37. Le merge Angular suit son propre cycle TFS.

## Merged

- Date : 2026-04-28
- Mode : `/merge task-011 --i-tested` (humain a attesté avoir validé end-to-end)
- Squash commits sur `develop` :
  - `dtos-mss` : `7825ab987fd280e5f4befc68ed68a52b7c22b86f` (PR #10 closed)
  - `api-mail` : `80865138d8913f9adc69c283b0320d1f9786e99b` (PR #32 closed)
  - `client-blazor` : `9c588ed1a63d1208f35816f73e932178fddf352b` (PR #37 closed)
- Develop CI :
  - `dtos-mss` : ✅ green (run 25041129743)
  - `api-mail` : pas de workflow CI configuré sur ce repo (gate empty-checks ≠ failure, accepté)
  - `client-blazor` : ✅ green (run 25041170397)
- Branches feature supprimées (locale + remote) sur les 3 repos pushable.
- Clones locaux switched back to `develop` et pull --ff-only.
- `client-angular` : managed manually by the human.
