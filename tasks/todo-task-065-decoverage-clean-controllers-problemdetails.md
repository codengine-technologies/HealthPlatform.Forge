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
