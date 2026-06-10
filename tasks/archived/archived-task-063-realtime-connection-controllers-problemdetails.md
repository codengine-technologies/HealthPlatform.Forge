# todo-task-063-realtime-connection-controllers-problemdetails.md — Migration controllers temps réel / connexion / annuaire

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer sur le pattern RFC 7807 de task-055 :

- `MailEventsController` (~203 lignes, 1 action SSE, ~4 `catch`)
- `NotificationsController` (~140 lignes, 1 action SSE, ~2 `catch`)
- `ConnectionController` (~82 lignes, ~2 actions, ~3 `catch`)
- `DirectoryController` (~73 lignes, ~3 actions, ~3 `catch`)

Pour chaque controller : retirer les `try/catch` boilerplate, lever les
exceptions métier typées pour les erreurs métier, retirer
`[ExcludeFromCodeCoverage]`, couvrir chaque action par ≥ 1 test unitaire.

**Spécificité SSE** : `MailEventsController.Stream` et
`NotificationsController.Stream` produisent des flux Server-Sent Events. Comme
pour task-062, le `GlobalExceptionHandler` ne peut pas réécrire une réponse
déjà commencée — conserver une gestion d'erreur in-stream pour ce qui survient
après le premier octet, et ne déléguer au handler que les échecs **avant**
l'ouverture du flux (résolution claim email manquant → 400 `problem+json`,
etc., comportement task-022 préservé). Ne pas réintroduire de lecture
`?email=` (sécurité task-022).

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] `try/catch` boilerplate retiré des 4 controllers (hors gestion in-stream
      légitime, documentée)
- [ ] Erreurs métier → exceptions typées (mapping par type)
- [ ] `[ExcludeFromCodeCoverage]` retiré des 4 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec typé)
- [ ] Les flux SSE (`MailEvents`, `Notifications`) restent fonctionnels ;
      l'email reste résolu **exclusivement** depuis le claim JWT (sécurité task-022
      non régressée — `?email=` ignoré)
- [ ] Aucune donnée de santé dans les `ProblemDetails`

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- `ConnectionController` / `DirectoryController` : provoquer une erreur (annuaire
  indisponible, paramètre invalide) → `problem+json` avec le bon code.
- Ouvrir le flux SSE `MailEvents` / `Notifications` côté UI MSS → vérifier que
  les notifications temps réel arrivent toujours (pas de régression).
- Tenter `?email=victim@x.fr` sur le stream avec son propre JWT → le flux
  s'ouvre sur SON email (sécurité task-022 préservée).

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique de controllers existants, iso-comportement.
La sécurité SSE (résolution email par claim, scrub token en query) de task-022
ne doit pas régresser. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair dans les `ProblemDetails`
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`
- [ ] Sécurité SSE task-022 préservée (email depuis claim, `?email=` ignoré)

## Develop log
- Repos touched : api-mail (pushed). dtos-mss : aucun changement (branche vide, pas de PR).
- Commit : api-mail ea47419 refactor(api): migrate realtime/connection controllers to RFC 7807 (task-063)
- Changes :
  - `ConnectionController`, `DirectoryController`, `MailEventsController`,
    `NotificationsController` : suppression des `try/catch` boilerplate + 500/499 codés en dur.
  - `ConnectionController` : garde offline-mode → `ValidationException` (400).
  - `DirectoryController` : suppression du `catch (ArgumentException)` **mort** (le service
    `AnnuaireSanteService` wrappe déjà les erreurs de validation en `InvalidOperationException`,
    comportement testé) → iso-comportement (critères invalides restent 500 côté service).
  - **SSE** (`MailEvents`, `Notifications`) : la validation **pré-flux** (claim `mssEmail`
    manquant) → `ValidationException` (400 problem+json via handler, avant 1er octet) ;
    gestion in-stream (annulation client, forwarders) **conservée**. **Sécurité task-022
    préservée** : email résolu exclusivement depuis le claim JWT, `?email=` ignoré
    (test anti-spoofing vert).
  - `[ExcludeFromCodeCoverage]` retiré des 4 controllers.
- Tests : 14 (Connection/Directory behavioural, MailEvents real-broker open+spoofing+validation,
  Notifications missing-claim mis à jour). Build ✓, tests ✓.
- Next step : `/sonar task-063` → `/review` (skip `/lint-angular`).

## Sonar log
- Mode A, branche `refactor/task-063-...`. **New code task-063 — zéro dette dès le 1er
  passage** : `new_violations`=0, `new_bugs`=0, `new_vulnerabilities`=0, `new_code_smells`=0,
  `new_security_hotspots_reviewed`=100%. Aucun fix Sonar nécessaire.
- Couverture fichiers : ConnectionController 96.7%, DirectoryController 90.9%,
  NotificationsController 90.8%, MailEventsController 70.8% (les forwarders multi-brokers
  + heartbeat in-stream ne sont pas tous exercés par le happy path — plomberie lifecycle).
- Quality Gate projet RED uniquement sur `new_coverage` global (~73%) — dette pré-existante
  baseline 2026-04-27, hors périmètre.
- 3 échecs de tests pré-existants documentés (middleware DB-name stale, IMAP flaky,
  MailExport PDF flaky) — non liés à task-063.
- Next step : skip `/lint-angular` → `/review task-063`.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/83 — label `awaiting-human-merge`
- `dtos-mss` : branche vide (aucun changement) — pas de PR.

## Code Review Summary
- Verdict : **APPROVED**. Correctness/Security task-022/Architecture/Tests ✅.
- Sonar new-code : 0 violation. 3 échecs pré-existants documentés (non liés).

## Merged

- Merged: 2026-06-09  UTC (squash, HAG human attestation via /merge --i-merged)
- api-mail :  (PR # squash-merged into develop, remote branch deleted)
- dtos-mss : no PR (branch empty — no contract change)
- develop CI run : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions?query=branch%3Adevelop
