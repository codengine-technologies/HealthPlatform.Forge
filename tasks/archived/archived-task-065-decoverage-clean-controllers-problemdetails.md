# todo-task-065-decoverage-clean-controllers-problemdetails.md — Dé-exclusion + tests des controllers sans boilerplate

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Finaliser l'harmonisation RFC 7807 (task-055) sur les controllers qui **n'ont
pas de `try/catch` boilerplate** mais restent `[ExcludeFromCodeCoverage]` :

- `SyncController` (~154 lignes, ~7 actions)
- `SignatureController` (~133 lignes, ~7 actions)
- `SettingsController` (~75 lignes, ~4 actions)
- `MailTemplateController` (~118 lignes, ~7 actions)
- `MailExportController` (~169 lignes, ~3 actions)
- `FeatureFlagController` (~42 lignes, ~2 actions)
- `DraftController` (~102 lignes, ~6 actions)

Ces controllers délèguent déjà implicitement au `GlobalExceptionHandler` (pas de
boilerplate à retirer) ou passent par `ToActionResult` (uniformisé en task-059).
Le travail consiste à :
1. **Auditer** chaque controller : confirmer qu'aucune erreur n'est avalée /
   reformattée à la main ; remplacer les éventuels `BadRequest("...")` /
   not-found manuels par les exceptions métier typées si pertinent.
2. Retirer `[ExcludeFromCodeCoverage]`.
3. Couvrir chaque action par ≥ 1 test unitaire (`MailExportControllerTests`
   existe déjà — l'étendre ; créer les autres fichiers de tests).

Aucun changement de comportement attendu hormis l'uniformisation déjà acquise.
api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Branches
- `api-mail` (pushed) : refactor/task-065-decoverage-clean-controllers-problemdetails
- `dtos-mss` (pushed, auto-included) : branche probablement vide, pas de PR.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] Audit fait : aucun des 7 controllers n'avale / ne reformatte une erreur à
      la main (sinon converti en exception typée)
- [ ] `[ExcludeFromCodeCoverage]` retiré des 7 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec quand applicable)
      pour les 7 controllers
- [ ] À l'issue de cette task : **0 controller V1 ne porte encore
      `[ExcludeFromCodeCoverage]`** ni `catch (Exception)` boilerplate (audit grep
      global sur `src/Api/Controllers/V1/`)
- [ ] Aucune donnée de santé dans les `ProblemDetails`

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- Pour chaque controller : appeler une action nominale (succès) puis, quand
  applicable, provoquer une erreur → vérifier `problem+json` cohérent.
- `MailExportController` : export PDF/EML d'un mail inexistant → 404 `problem+json`.
- Vérifier en UI MSS qu'aucune fonctionnalité (signatures, modèles, paramètres,
  brouillons, sync, export, feature flags) ne régresse.

## Conformité santé / Ségur / ANS

Hors couloir Ségur — finalisation technique (couverture + dé-exclusion),
iso-comportement métier. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair dans les `ProblemDetails`
- [ ] Détail technique réservé aux logs serveur, corrélé par `traceId`

## Develop log
- Repos touched : api-mail (pushed). dtos-mss : aucun changement (branche vide, pas de PR).
- Commit : api-mail 1d8ca19 refactor(api): de-exclude clean controllers + typed exceptions (task-065)
- Changes :
  - 7 controllers de-`[ExcludeFromCodeCoverage]` : Sync, Signature, Settings, MailTemplate,
    MailExport, FeatureFlag, Draft.
  - Audit : aucun n'avale/reformatte une erreur à la main. `BadRequest`/`NotFound` manuels
    convertis en exceptions typées (`NotFoundException` → 404, `ValidationException` → 400,
    `ConflictException` → 409 pour le verrou d'envoi de brouillon).
  - `MailExportController` : `NotFound` → `NotFoundException` ; échec de Result → exception
    mappée en 500 générique (la string "Failed to ..." n'est plus exposée au client).
  - `DraftController` send : `SmtpFailure` conserve son 502 dédié (pas d'équivalent
    RFC 7807 typé pour une erreur de gateway SMTP — comportement iso, documenté inline).
- Tests : 61 (tous actions des 7 controllers ; DraftControllerTests + MailExportControllerTests
  existants mis à jour pour les nouveaux throws typés). Build ✓, tests task-065 ✓ 61/61.

### Audit global DOD — `0 controller V1 [ExcludeFromCodeCoverage]` / `catch(Exception)`
- **[ExcludeFromCodeCoverage]** : ✅ atteint au niveau de la campagne. Sur la branche
  task-065 (basée sur `develop`), les 13 controllers des tasks 061-064 apparaissent encore
  exclus car leurs PRs (#81-#84) **ne sont pas encore mergées** (HAG, règle 10). Une fois
  les 5 PRs (061-065) mergées sur `develop`, **0 controller V1 ne portera [ExcludeFromCodeCoverage]**.
- **`catch (Exception)`** : ✅ pour les 20 controllers de la campagne (061-065). **Exception
  documentée** : `MailController` (1393 lignes, **hors scope des 5 tasks**) conserve 2
  `catch (Exception)`. Sa taille impose une task dédiée avec tests de caractérisation —
  **follow-up recommandé : `todo-task-066-mailcontroller-problemdetails`**. Ne pas l'inclure
  ici relève de la règle 6 (scopes isolés) ; le signaler relève de la transparence DOD.
- Next step : `/sonar task-065` → `/review` (skip `/lint-angular`).

## Sonar log
- Mode A, branche `refactor/task-065-...`. **New code task-065 — zéro dette dès le 1er
  passage** : `new_violations`=0, `new_bugs`=0, `new_vulnerabilities`=0, `new_code_smells`=0,
  hotspots 100%. Aucun fix Sonar nécessaire.
- Couverture fichiers : Settings 100%, MailTemplate 100%, FeatureFlag 100%, Sync 94.6%,
  Draft 94.1%, Signature 89.4%, MailExport 63.6% (branches File/inline-disposition/
  SanitizeFileName non toutes exercées).
- Quality Gate projet RED uniquement sur `new_coverage` global — dette pré-existante baseline 2026-04-27.
- 3 échecs de tests pré-existants documentés (middleware DB-name, IMAP flaky, MailExport-service PDF flaky) — non liés.
- Next step : skip `/lint-angular` → `/review task-065`.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/85 — label `awaiting-human-merge`
- `dtos-mss` : branche vide — pas de PR.

## Code Review Summary
- Verdict : **APPROVED**. 7 controllers de-excluded, exceptions typées, 61 tests, Sonar new-code 0 violation.
- Audit global : [ExcludeFromCodeCoverage] → 0 après merge des 5 PRs ; catch(Exception) → 0 sur la
  campagne, sauf `MailController` (hors scope, follow-up task-066 recommandé).
- 3 échecs pré-existants documentés (non liés).

## Merged

- Merged: 2026-06-09  UTC (squash, HAG human attestation via /merge --i-merged)
- api-mail :  (PR # squash-merged into develop, remote branch deleted)
- dtos-mss : no PR (branch empty — no contract change)
- develop CI run : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions?query=branch%3Adevelop
