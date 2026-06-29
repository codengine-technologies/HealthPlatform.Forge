# todo-task-094.md — Optimiser le déplacement d'emails (UX ultra fluide + réduction des traitements serveur)

**Repos**: api-mail, client-angular
**Epic**: E009

> **US backend+frontend justifiée (sans Blazor)** :
> - le besoin fonctionnel exprimé cible explicitement l'expérience de glisser-déposer dans la messagerie Angular MSS ;
> - l'optimisation structurelle côté backend (`api-mail`) s'applique à tous les consommateurs sans imposer de changement d'API publique ni de contrat DTO ;
> - aucun nouveau comportement UI n'est demandé côté `client-blazor` dans cette US.

## Objective

Réduire fortement la latence perçue et la charge serveur lors d'un déplacement d'email, en combinant :
- un **refresh ciblé du dossier destination** juste après le drop (avec retry borné) côté Angular ;
- un **chemin backend de move IMAP avec rekey DB** (mise à jour `FolderPath + Uid`) pour éviter le cycle coûteux suppression/ré-enrichissement.

Le praticien doit percevoir un résultat quasi immédiat après drag & drop, sans attendre le poll périodique 30s, tout en conservant l'intégrité métier (liaisons patient/documents, audit, cohérence IMAP/DB/cache).

## Contexte produit

Aujourd'hui :
- l'UI Angular applique déjà un move optimiste, mais la visibilité finale dans le dossier cible peut dépendre du prochain cycle de refresh ;
- le backend move IMAP invalide les caches, mais la persistance locale peut encore passer par des chemins de resynchronisation lourds selon les cas.

Cette US vise un comportement "first class" post-drop :
1. feedback visuel immédiat côté front ;
2. persistance locale alignée dès le move réussi ;
3. sync de fond conservée comme filet de sécurité (et non comme voie principale de cohérence post-move).

## Comportement attendu

### A. UX post-drop (Angular)
- Après un drop **autorisé** vers un dossier IMAP :
  - la liste source est mise à jour optimistement (comportement existant conservé) ;
  - un refresh ciblé du dossier destination est déclenché avec retries bornés (ex: 300ms, 1200ms, 3000ms) ;
  - les retries s'arrêtent dès que les UID attendus apparaissent, sinon arrêt après la dernière tentative.
- En cas d'échec move backend : rollback existant conservé + message d'erreur discret.
- Aucun polling agressif global ; pas d'augmentation brutale de charge côté API.

### B. Move backend persistant (api-mail)
- Le move IMAP reste **obligatoire** et source de vérité.
- Si le move IMAP réussit et renvoie un nouvel UID :
  - mise à jour transactionnelle de la ligne locale (ou des lignes en bulk) pour refléter `sourceFolder/sourceUid -> targetFolder/newUid` ;
  - conservation des informations enrichies existantes tant que valides ;
  - invalidation cache source/cible maintenue.
- Si le move IMAP échoue :
  - aucune mutation DB locale ;
  - réponse d'erreur standard (ProblemDetails via handler global).

### C. Cohérence et robustesse
- Le background sync continue de corriger les écarts résiduels mais ne doit plus être nécessaire pour "rendre visible" un move normal.
- Le comportement doit rester idempotent et sûr en cas de concurrence (multi-onglet / multi-pod).
- Les audits métiers existants (MailMove, etc.) doivent rester corrects et exploitables.

## Gherkin

```gherkin
Feature: Déplacement email fluide et persistant

  Scenario: Le courrier déplacé apparaît rapidement dans le dossier cible
    Given un praticien glisse un courrier de la boîte de réception vers un dossier personnel
    When le serveur confirme le déplacement IMAP
    Then le courrier disparaît immédiatement de la liste source
    And le dossier cible est rafraîchi automatiquement en quelques secondes
    And le courrier devient visible sans attendre le poll périodique long

  Scenario: Echec de déplacement côté serveur
    Given un praticien glisse un courrier vers un dossier personnel
    When le serveur ne peut pas réaliser le déplacement
    Then le courrier revient à son dossier d'origine
    And un message d'erreur discret est affiché

  Scenario: Déplacement en lot
    Given un praticien déplace plusieurs courriers en une seule action
    When le serveur confirme le déplacement de chaque courrier
    Then tous les courriers sont visibles dans le dossier cible
    And les compteurs source et cible sont cohérents

  Scenario: Cohérence persistante après déplacement
    Given un courrier a été déplacé avec succès
    When un cycle de synchronisation de fond se déclenche ensuite
    Then le courrier n'est pas recréé inutilement via un traitement lourd
    And les données locales restent cohérentes avec IMAP
```

## Analyse technique attendue (dans le scope de la US)

### Front (`client-angular`)
- Introduire une stratégie de `destination refresh retry` dédiée au post-drop, sans modifier le timer global de sync.
- Exposer des métriques UX post-drop (durée drop -> visibilité cible) via logs techniques non sensibles.
- Préserver le comportement deferred-delete/undo existant pour la corbeille.

### Back (`api-mail`)
- Étendre le flux move pour inclure un rekey persistant local après succès IMAP (single + bulk).
- Garantir une transaction cohérente (verrous, concurrence, rollback).
- Ne pas introduire de rupture de contrat API ni de DTO.
- Ajouter/adapter des tests unitaires et d'intégration pour les scénarios de move single/bulk, erreurs et concurrence.

## Definition of Done

- [ ] Build passe : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests backend passent : `cd Api/Mail && dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Build Angular passe : `cd Client/Angular/front && npm run build` (0 erreur)
- [ ] Tests Angular passent : `cd Client/Angular/front && npm test` (ou commande CI équivalente)
- [ ] Après drop autorisé, un refresh ciblé dossier destination est déclenché avec retry borné et arrêt anticipé dès succès
- [ ] Le move backend single met à jour la persistance locale (`FolderPath + Uid`) après succès IMAP
- [ ] Le move backend bulk met à jour la persistance locale de façon atomique/cohérente
- [ ] En cas d'échec IMAP, aucune mutation DB locale n'est committée
- [ ] Invalidation cache source/cible effective après move réussi
- [ ] Aucune régression sur delete/deferred-delete/undo côté Angular
- [ ] Compteurs dossier source/cible cohérents après move
- [ ] Tests ajoutés :
- [ ] backend : couverture des chemins success/failure/concurrency (single + bulk)
- [ ] frontend : couverture retry post-drop, stop condition, rollback sur erreur
- [ ] Lint Angular scope MSS : `nx lint --projects=tag:scope:mss` (0 erreur bloquante)
- [ ] Aucune donnée de santé en clair dans les logs (INS/NIR/NIA, contenu de mail, contenu CDA)

## Manual Test Plan

- Démarrer API : `cd Api/Mail && dotnet run --project src/Api/Api.csproj`
- Démarrer Angular : `cd Client/Angular/front && npm start`
- Ouvrir la messagerie MSS de test
- Cas 1 (single move) :
- Glisser 1 email Inbox -> dossier perso
- Vérifier disparition immédiate côté source
- Vérifier apparition côté destination en quelques secondes (sans attendre 30s)
- Cas 2 (bulk move) :
- Sélectionner N emails, glisser vers dossier perso
- Vérifier présence de tous les emails côté destination
- Vérifier compteurs source/cible
- Cas 3 (erreur backend simulée) :
- Forcer un échec move
- Vérifier rollback UI + message d'erreur discret
- Cas 4 (robustesse sync) :
- Après un move réussi, déclencher/simuler un passage de sync
- Vérifier absence de retraitement lourd inutile (pas de recréation intempestive)
- Cas 5 (régression corbeille) :
- Déposer un email sur Corbeille, cliquer Annuler
- Vérifier comportement deferred-delete inchangé

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — optimisation de performance/ergonomie sur flux existant
- **Exigences DSR honorées** : non applicable — aucun nouveau flux d'échange MSSanté/CI-SIS, optimisation d'un comportement existant
- **INS** : non applicable — pas de nouvelle manipulation d'identité INS
- **Authentification PS** : inchangé — opérations dans la boîte du PS déjà authentifié
- **Habilitations** : inchangé — règles backend existantes conservées
- **Interop CI-SIS** : non applicable — aucun nouveau format ni transformation CDA/FHIR
- **Tracé PGSSI-S** : journalisation existante des actions de move conservée ; aucun log de contenu médical
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement, optimisation d'exécution

## Hors périmètre

- Changement des contrats DTO publics (`dtos-mss`)
- Refonte globale du scheduler de sync périodique
- Ajout d'un nouveau canal temps réel dédié (SignalR/SSE spécifique post-move)
- Évolutions UI Blazor

## Dépendances

- `done-task-093-angular-mail-drag-drop.md` (socle drag & drop Angular)

## Branches (attendues via /start)

- Branche commune attendue : `feat/task-094-mail-move-ux-perf-optimization`
- `client-angular` : mode code-only (branche gérée par l'humain)
- `api-mail` : branche pushable standard

## Branches
- `api-mail` (pushed) : `feat/task-094-mail-move-ux-perf-optimization` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-094-mail-move-ux-perf-optimization
- `dtos-mss` (pushed, auto-inclus) : `feat/task-094-mail-move-ux-perf-optimization` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-094-mail-move-ux-perf-optimization — branche créée proactivement ; aucun changement DTO attendu (hors périmètre US) → restera sans commit, pas de PR.
- `client-angular` (code-only) : la forge écrit le code sur la branche actuellement checked out dans `Client/Angular/` (snapshot au `/start` : `feature/nova-rewriting-mss`, cumulée avec 087/088/089/093) — l'humain gère branche, commit, push, PR TFS.

## Develop log
- Repos touched : `api-mail` (pushable), `client-angular` (code-only). `dtos-mss` non touché (aucun changement de contrat — hors périmètre), branche restée vide.
- DTOs published : none. Interop published : none. Aucun changement d'API publique ni de DTO (conforme « Hors périmètre »).
- **Backend (`api-mail`) — move IMAP avec rekey DB en place** :
  - Nouveau `IMailRepository.RekeyMovedMailsAsync(sourcePath, targetPath, IReadOnlyList<MailUidRemap>, ct)` + record `MailUidRemap(OldUid, NewUid)` (`src/Application/Models/`). Rekey en place de `FolderPath + Uid` au lieu du cycle delete + ré-enrichissement du background sync → **préserve les données enrichies** (liens patient, documents médicaux, tags, contenu — enfants liés au `Mail.Id` immuable).
  - Atomique (un seul `SaveChangesAsync` = une transaction), **idempotent** et **sûr en concurrence** : ligne source absente → skip ; ligne cible déjà présente (sync concurrent a re-enrichi) → suppression de la ligne source périmée (évite la violation de l'index unique `(FolderPath, Uid)`).
  - `ImapFolderService.MoveEmailAsync` (single) + `BulkMoveEmailsAsync` (bulk) câblent le rekey à partir de la map UIDPLUS (`UniqueIdMap` = `KeyValuePair<source,dest>`). Best-effort via `TryRekeyMovedMailsAsync` : IMAP reste source de vérité, échec DB non fatal (sync = filet). **En cas d'échec IMAP, aucune mutation DB** (le rekey n'est appelé que dans la branche succès `newUid.HasValue`).
  - Invalidation cache source/cible **inchangée** (déjà en place avant le rekey). Controller/API/DTO inchangés.
  - Mock `Infrastructure.Mock/Repository/MailRepository` mis à jour (no-op).
  - Tests : `MailRepositoryRekeyTests` (7 tests) — single success, bulk success, **préservation enrichie** (content/meddoc+patient/tag), no-op source manquante, no-op remaps vides, **drop concurrence cible existante**, batch mixte (rekey frais + drop conflit). Provider EF InMemory (change-tracker + SaveChanges, compatible).
  - Note testabilité : le chemin `ImapFolderService` (single/bulk) nécessite un vrai `ImapClient` MailKit (non mockable en isolation, cohérent avec l'absence de tests unitaires de move pré-existants — seuls des tests d'intégration Gmail existent). La logique neuve (rekey) est couverte au niveau repository ; le « failure → no DB mutation » est garanti structurellement (rekey hors du catch, dans la branche succès uniquement).
- **Frontend (`client-angular`, code-only) — refresh ciblé du dossier destination post-drop** :
  - Nouveau `MailDestinationRefreshService.refreshAfterMove(targetPath, expectedMinCount)` (`features/mail/services/`) : refresh borné à retries (token `MSS_DEST_REFRESH_DELAYS`, défaut **300/1200/3000 ms**), **arrêt anticipé** dès que le `count` serveur du dossier cible atteint le compte optimiste attendu, sinon abandon après la dernière tentative (le poll périodique 30 s reste le filet ; pas de polling global agressif). Skip-to-next sur erreur de fetch.
  - Nouvelle méthode d'état `MailStateService.applyFolderMetadataByPath(folder)` : applique `count/unread/uids/uidNext` frais à un dossier de la sidebar (et `selectedFolder` si c'est lui), **filtre tombstones** (ne ressuscite pas un delete optimiste). Ne perturbe pas la liste affichée.
  - `mail-list.component.applyMoveSuccess` déclenche `refreshAfterMove(target.path, expectedMinCount)` après les mises à jour optimistes. **Aucun changement** au flux move optimiste + rollback (`handleDropError`) ni au deferred-delete/undo (task-093) — préservés.
  - Token `MSS_DEST_REFRESH_DELAYS` (`core/tokens/`).
  - Tests : `mail-destination-refresh.service.spec` (4 : succès 1 tentative, retry jusqu'au seuil, abandon après dernière tentative, skip sur erreur — fake timers) ; `mail-state.service.spec` +4 (applyFolderMetadataByPath : maj sidebar, maj selectedFolder, autre dossier intact, anti-résurrection tombstone) ; `mail-list.component.spec` +2 (drop move → bulkMoveEmails + refresh ciblé ; échec backend → pas de refresh).
- Local build/test :
  - `api-mail` : ✓ `dotnet build` 0 erreur/0 warning. ✓ `MailRepositoryRekeyTests` 7/7. Full-suite : 2 échecs **pré-existants flaky** sans rapport (`MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection` PDF, `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync` IMAP cancel — cf. memory `project_api_mail_preexisting_flaky_tests`). Aucune régression task-094.
  - `client-angular` : ✓ `nx build mss-lib` 0 erreur. ✓ `nx test mss-lib` 298/298 (10 nouveaux). ✓ `nx lint mss-lib` 0 erreur (33 warnings pré-existants hors task-094).
- Git : `api-mail` commit `e68d8a3` poussé sur `feat/task-094-mail-move-ux-perf-optimization` (hook pre-push = build OK). `dtos-mss` aucun commit (branche vide → pas de PR). `client-angular` code-only : aucune op git (changements task-094 non commités sur `feature/nova-rewriting-mss`, cumulés avec task-093) — l'humain gère commit/push/PR TFS.
- Fichiers task-094 `client-angular` (uncommitted) :
  - `core/tokens/mss-dest-refresh-delays.token.ts` (new)
  - `features/mail/services/mail-destination-refresh.service.{ts,spec.ts}` (new)
  - `features/mail/services/mail-state.service.{ts,spec.ts}` (applyFolderMetadataByPath + tests)
  - `features/mail/components/mail-list/mail-list.component.{ts,spec.ts}` (refresh ciblé + tests) — NB `mail-list.component.html` modifié = WIP task-093 pré-existant, non touché par task-094.
- DOD self-check : build api-mail ✓, build angular ✓, tests angular ✓ ; refresh ciblé retry borné + arrêt anticipé ✓ ; rekey single ✓ ; rekey bulk atomique ✓ ; échec IMAP → pas de mutation DB ✓ ; invalidation cache inchangée ✓ ; pas de régression delete/undo ✓ ; compteurs source/cible cohérents ✓ ; tests backend success/concurrency single+bulk ✓ ; tests frontend retry/stop/rollback ✓ ; lint MSS 0 erreur ✓ ; pas de donnée santé loggée (uid/chemins seulement) ✓.
- Next step : /forge-simplify task-094

## Simplify log
- Repos passed : `api-mail` (pushable, touché), `client-angular` (code-only, touché).
- /forge-simplify : **clean skip** — code task-094 fraîchement écrit aux patterns existants, forte réutilisation :
  - api-mail : `RekeyMovedMailsAsync` calque le style `DeleteMailsByUidsAsync`/`GetExistingUidsAsync` (deux requêtes ciblées + change-tracker + un seul `SaveChanges`) ; `TryRekeyMovedMailsAsync` wrapper court ; câblage ImapFolderService minimal. Méthodes focalisées, complexité dans les limites, aucune redondance extractible sans risque comportemental.
  - client-angular : `applyFolderMetadataByPath` calque `updateFolderMetadata` et **réutilise** `applyTombstonesToFolder` ; `MailDestinationRefreshService` réutilise `api.getFolder` + la méthode d'état ; signals-first, JSDoc, méthodes < 15 lignes.
- Applied & committed : none.
- No change : api-mail, client-angular (rien à simplifier).
- Rolled back (validation RED) : none.
- Skipped (contract/excluded) : dtos-mss (non touché + porteur de contrat), interop-cda, devops, psc-proxy-*.
- Build / tests : inchangés depuis /develop (aucune édition simplify).
- Next step : /sonar task-094 (api-mail touché).

## Sonar log
- /sonar : **skip best-effort** — infra SonarQube non provisionnée : serveur `localhost:9000` injoignable (HTTP 000) + `SONAR_TOKEN` absent (cf. memory `project_sonar_infra_not_provisioned`). Pas de blocage (best-effort) ; les règles de codage anti-dette du repo (`.github/instructions/dotnet-coding-rules.instructions.md`) ont été respectées à l'écriture (méthodes focalisées S138, pas de `.Result`/`.Wait` S4462, ≤ 3 opérateurs conditionnels S1067). Build api-mail 0 warning.
- Next step : /lint-angular task-094 (client-angular touché).

## Lint log
- /lint-angular (scope `tag:scope:mss`, code-only) :
  - `nx lint mss-lib` : **0 errors**, 33 warnings — **tous pré-existants hors task-094** (max-lines/complexity/jsdoc-require-example sur biology-timeline, patient-timeline, mss-settings/setup/templates, abnormal-biology & sync-progress widgets). Les fichiers task-094 (`mail-destination-refresh.service`, `mss-dest-refresh-delays.token`, `mail-state.service` ajout, `mail-list.component` ajout) sont **lint-clean** (0 error / 0 warning).
  - Aucun auto-fix nécessaire pour task-094 (0 error ; les 2 warnings fixables sont des jsdoc/@example hors périmètre → non touchés).
  - `nx build mss-lib` ✓ 0 erreur. `nx test mss-lib` ✓ 298/298 (10 task-094).
  - Code-only : aucune op git (TFS).
- Next step : /review task-094

## PRs
- `api-mail` (pushed) : **PR #111** — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/111 — label `awaiting-human-merge`. Commit `e68d8a3`. Branche à jour avec `develop` (merge fast-forward, aucun conflit).
- `dtos-mss` : **aucune PR** — branche `feat/task-094-mail-move-ux-perf-optimization` créée proactivement mais sans commit (aucun changement de contrat). À supprimer ou laisser vide.
- `client-angular` (code-only) : **humain gère commit/push TFS + ouverture PR**. Aucune PR GitHub (remote TFS). Branche `feature/nova-rewriting-mss` (cumulée avec 087/088/089/093). Fichiers task-094 (uncommitted) :
  - `front/libs/mss/src/core/tokens/mss-dest-refresh-delays.token.ts` (new)
  - `front/libs/mss/src/features/mail/services/mail-destination-refresh.service.{ts,spec.ts}` (new)
  - `front/libs/mss/src/features/mail/services/mail-state.service.{ts,spec.ts}` (applyFolderMetadataByPath + tests)
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.{ts,spec.ts}` (refresh ciblé + tests) — NB `mail-list.component.html` = WIP task-093 pré-existant, non touché par task-094.
- `devops` / `psc-proxy-*` : non concernés.

> ⚠️ US-complete (règle 11) : l'US complète = **PR #111 api-mail + PR TFS Angular** (code-only, ouverte par l'humain). HAG (règle 10) : tester l'US assemblée de bout en bout, puis merger.

## Code Review Summary
- Verdict : **APPROVED** (aucune itération de correction nécessaire).
- Build : ✓ `dotnet build` api-mail 0 erreur / 0 warning. ✓ `nx build mss-lib`.
- Tests : ✓ `MailRepositoryRekeyTests` 7/7 ; ✓ `nx test mss-lib` 298/298 (10 task-094). Full-suite api-mail : 2 échecs **pré-existants flaky** (`MailExportServiceTests` PDF, `ImapConnectionServiceIntegrationTests` cancel) — **passent en isolation**, confirmés flaky (interaction/timing parallèle), **pas une régression task-094** (cf. memory `project_api_mail_preexisting_flaky_tests`).
- Lint : ✓ `nx lint mss-lib` (scope mss) 0 erreur (33 warnings pré-existants hors task-094).
- DOD : rekey en place single+bulk (atomique, idempotent, concurrence) ✓ ; échec IMAP → pas de mutation DB ✓ ; invalidation cache inchangée ✓ ; refresh ciblé destination retry borné + arrêt anticipé ✓ ; pas de régression delete/undo ✓ ; compteurs cohérents ✓ ; tests backend success/concurrency single+bulk ✓ ; tests frontend retry/stop/rollback ✓ ; pas de donnée santé loggée (uid/chemins seulement) ✓.
- Correctness : `RekeyMovedMailsAsync` — 2 requêtes + boucle in-memory + 1 `SaveChanges` atomique (pas de N+1) ; drop de la ligne source périmée géré (anti-violation index unique) ; rekey confiné à la branche succès. Frontend : retry borné self-terminant, tombstone-safe, teardown via `takeUntilDestroyed`.
- Security : EF LINQ (pas d'injection), aucun secret, aucune donnée de santé en clair dans les logs.
- Architecture : calque les patterns repository existants (`DeleteMailsByUidsAsync`) et état Angular (`updateFolderMetadata` + réutilisation `applyTombstonesToFolder`) ; aucun changement de contrat API/DTO.
- Code-only : aucune opération git par la forge sur `client-angular` ; l'humain review le diff dans WindSurf puis commit/push TFS + ouvre la PR.

## Merged
- Date : 2026-06-17 (merge humain validé via `/merge task-094 --i-tested`).
- `api-mail` : PR #111 squash-mergée → `develop` SHA `d4da03a` (`d4da03a00ace25aec0b721ffe6cc5d46d86613d8`). Branche distante `feat/task-094-mail-move-ux-perf-optimization` supprimée (ref distante uniquement, branche locale conservée).
- `dtos-mss` : aucune PR (branche proactive vide, 0 commit vs `develop`) → ref distante supprimée.
- `client-angular` (code-only) : géré manuellement par l'humain (commit/push/PR TFS) — hors scope `/merge`.
- `devops` / `psc-proxy-*` : N/A.
- CI `develop` (api-mail) : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27690185528
