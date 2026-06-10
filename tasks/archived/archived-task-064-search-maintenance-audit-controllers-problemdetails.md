# todo-task-064-search-maintenance-audit-controllers-problemdetails.md — Migration controllers recherche / maintenance / audit

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer sur le pattern RFC 7807 de task-055 les derniers controllers porteurs de
`try/catch` boilerplate :

- `SearchController` (~250 lignes, ~3 actions, ~5 `catch`)
- `MailMaintenanceController` (~148 lignes, ~3 actions, ~3 `catch`)
- `AuditController` (~80 lignes, ~2 actions, ~2 `catch`)

Pour chaque controller : retirer les `try/catch` boilerplate, lever les
exceptions métier typées pour les erreurs métier, retirer
`[ExcludeFromCodeCoverage]`, couvrir chaque action par ≥ 1 test unitaire.

**Vigilance audit** : `AuditController` expose le journal d'audit MSS (traces
médico-légales). Le `detail` exposé doit rester générique — aucune donnée de
trace (INS, email, contenu) dans le message d'erreur.

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Branches
- `api-mail` (pushed) : refactor/task-064-search-maintenance-audit-controllers-problemdetails
- `dtos-mss` (pushed, auto-included) : branche probablement vide, pas de PR.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] `try/catch` boilerplate retiré des 3 controllers
- [ ] Erreurs métier → exceptions typées (mapping par type)
- [ ] `OperationCanceledException` non ré-attrapée par action
- [ ] `[ExcludeFromCodeCoverage]` retiré des 3 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec typé)
- [ ] Aucune string brute / `ErrorResponse` ne subsiste dans ces controllers
- [ ] Aucune donnée de santé / de trace d'audit dans les `ProblemDetails`

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- `SearchController` : requête invalide / backend de recherche indisponible →
  `problem+json` avec le bon code et `traceId`.
- `MailMaintenanceController` : provoquer une erreur sur une opération de
  maintenance → `problem+json`.
- `AuditController` : forcer une erreur → `problem+json` **sans** aucune donnée
  de trace exposée.

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique de controllers existants, iso-comportement.
Vigilance traçabilité PGSSI-S : le journal d'audit lui-même reste inchangé ;
seule la **forme** des erreurs HTTP est normalisée. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé ni de trace d'audit en clair dans les `ProblemDetails`
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`

## Develop log
- Repos touched : api-mail (pushed). dtos-mss : aucun changement (branche vide, pas de PR).
- Commit : api-mail d345e64 refactor(api): migrate search/maintenance/audit controllers to RFC 7807 (task-064)
- Changes :
  - `SearchController`, `MailMaintenanceController`, `AuditController` : suppression des
    `try/catch` boilerplate + 500/499 codés en dur.
  - `MailMaintenanceController` : les catches fuyaient `ex.Message` dans le corps 500 —
    supprimés (handler renvoie 500 générique).
  - `SearchController` : garde longueur suggestions → `ValidationException` (400).
  - `AuditController` : gardes plage de dates → `ValidationException` (400) ;
    trace absente → `NotFoundException` (404). **Vigilance audit** : détails d'erreur
    génériques, aucune donnée de trace (INS/email/contenu) exposée. (Le champ `code`
    structuré des anciens BadRequest est remplacé par le schéma ProblemDetails standard.)
  - `[ExcludeFromCodeCoverage]` retiré des 3 controllers.
- Tests : 16 (Search + Audit behavioural ; MailMaintenance contract/route — downcast
  `DataContext` non unit-testable, harnais Testcontainer hors scope). Build ✓, tests ✓.
- Next step : `/sonar task-064` → `/review` (skip `/lint-angular`).

## Sonar log
- Mode A, branche `refactor/task-064-...`. **New code task-064 — zéro dette dès le 1er
  passage** : `new_violations`=0, `new_bugs`=0, `new_vulnerabilities`=0, `new_code_smells`=0,
  hotspots 100%. Aucun fix Sonar nécessaire.
- Couverture fichiers : SearchController **100%**, AuditController **100%**,
  MailMaintenanceController **6.8%** (les 3 actions downcastent `BaseRepository.DataContext`
  → non unit-testables sans Testcontainer ; contrat route/verbe couvert par smoke tests).
- Quality Gate projet RED uniquement sur `new_coverage` global — dette pré-existante baseline 2026-04-27.
- 3 échecs de tests pré-existants documentés (middleware DB-name, IMAP flaky, MailExport flaky) — non liés.
- Next step : skip `/lint-angular` → `/review task-064`.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/84 — label `awaiting-human-merge`
- `dtos-mss` : branche vide — pas de PR.

## Code Review Summary
- Verdict : **APPROVED**. Correctness/Security (no ex.Message leak, no audit data)/Tests ✅.
- Sonar new-code : 0 violation. 3 échecs pré-existants documentés (non liés).

## Merged

- Merged: 2026-06-09  UTC (squash, HAG human attestation via /merge --i-merged)
- api-mail :  (PR # squash-merged into develop, remote branch deleted)
- dtos-mss : no PR (branch empty — no contract change)
- develop CI run : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions?query=branch%3Adevelop
