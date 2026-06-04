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
