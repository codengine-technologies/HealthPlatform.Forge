# todo-task-090.md — Limitation de débit des requêtes API (rate limiting)

**Repos**: api-mail
**Epic**: E009

> US mono-repo justifiée : durcissement transverse de l'API. Aucun changement
> de contrat fonctionnel ni d'UI ; comportement uniquement défensif.

## Objective

Protéger l'API `api-mail` contre les abus et le déni de service (rafales de
requêtes, énumération, force brute applicative) en introduisant une
**limitation de débit** (rate limiting) sur les endpoints. Inspiré du
`login_rate_limit` de Roundcube. L'authentification PS repose sur PSC/Keycloak
(le throttling d'identité est côté fournisseur), mais les endpoints applicatifs
de la messagerie ne sont aujourd'hui débrayés par aucun quota.

## Comportement attendu

- Une politique de rate limiting (middleware .NET `AddRateLimiter`) est appliquée
  à l'API, avec une fenêtre et un quota configurables par configuration.
- Le partitionnement se fait par identité du PS authentifié (et/ou par IP pour
  les requêtes non authentifiées), afin qu'un utilisateur n'impacte pas les
  autres.
- Au dépassement du quota, l'API répond **HTTP 429 (Too Many Requests)** au
  format `ProblemDetails`, avec en-tête `Retry-After`.
- Les seuils sont paramétrables sans recompilation (appsettings / variables
  d'environnement) et peuvent différer entre endpoints sensibles et endpoints
  courants.
- Le rate limiting n'altère pas le fonctionnement nominal sous charge normale.

## Gherkin

```gherkin
Feature: Limitation de débit des requêtes API

  Scenario: Trafic normal non impacté
    Given un professionnel de santé utilisant la messagerie normalement
    When il enchaîne ses actions habituelles
    Then aucune de ses requêtes n'est rejetée pour cause de débit

  Scenario: Rafale au-delà du quota
    Given un quota de requêtes configuré pour une fenêtre de temps
    When un client dépasse ce quota dans la fenêtre
    Then les requêtes excédentaires sont rejetées avec un code 429
    And la réponse indique le délai avant nouvelle tentative

  Scenario: Isolation entre utilisateurs
    Given deux professionnels de santé distincts
    When l'un dépasse son quota
    Then l'autre continue d'utiliser la messagerie sans restriction
```

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Middleware `AddRateLimiter` configuré, partitionné par identité PS (et/ou IP pour non authentifié)
- [ ] Seuils (fenêtre, quota) configurables via appsettings / variables d'environnement
- [ ] Réponse 429 au format `ProblemDetails` (RFC 7807) avec en-tête `Retry-After`
- [ ] Possibilité d'une politique plus stricte sur les endpoints sensibles
- [ ] >= 1 test par comportement (sous quota → 200, dépassement → 429, isolation par partition)
- [ ] >= 1 test d'intégration vérifiant le 429 et l'en-tête `Retry-After`
- [ ] Aucune donnée de santé en clair dans les logs (seules les métriques de débit/partition techniques sont loggées)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Configurer un quota bas en environnement de test (ex. 5 requêtes / 10 s)
- Envoyer une rafale de requêtes sur un endpoint au-delà du quota
  → vérifier les réponses 429 + en-tête `Retry-After`
- Vérifier qu'un usage normal (sous le quota) n'est jamais rejeté
- Vérifier (deux tokens PS distincts) qu'un utilisateur saturé n'impacte pas
  l'autre

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : exigence transverse de sécurité (PGSSI-S § disponibilité / protection contre l'abus)
- **Exigences DSR honorées** : PGSSI-S — protection contre le déni de service et la force brute applicative
- **INS** : non applicable
- **Authentification PS** : inchangé — complète le throttling d'identité PSC/Keycloak au niveau applicatif
- **Habilitations** : inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : journaliser les dépassements de quota (partition, endpoint, horodatage) — utile à la détection d'abus
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : réduction de la surface d'abus (DoS applicatif, énumération)
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle nouvelle traitée (attention à ne pas logguer d'IP au-delà du nécessaire)

## Branches
- `api-mail` (pushed) : feat/task-090-api-rate-limiting
- `dtos-mss` (pushed, auto-included) : empty branch, no PR

## Develop log
- Repo : api-mail (dtos vide). Middleware `AddRateLimiter`/`UseRateLimiter` (après auth), partition par identité PS (repli IP), 429 ProblemDetails + Retry-After, seuils configurables (`RateLimiting`), policy "sensitive" dispo, no-op si désactivé. `RateLimitingOptions` + `RateLimitingSetup` (extraits, testés à l'identique de la prod).
- Tests : `RateLimitingPartitionKeyTests` 4 (api.tests), `RateLimitingIntegrationTests` 2 (TestServer : 200 / 429+Retry-After+problem+json).
- Build/test : ✓ api-mail.

## Simplify log
- /forge-simplify : clean skip — config extraite façon `ResponseCompressionSetup`, rien à simplifier.

## Sonar log
- /sonar : skipped — infra SonarQube non provisionnée. Code selon dotnet-coding-rules.

## Lint log
- /lint-angular : skipped — client-angular non touché.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/108 — awaiting-human-merge
- `dtos-mss` : branche vide — pas de PR

## Code Review Summary
- Verdict : **APPROVED** (0 blocking). Build ✓, tests ✓ (4 unit + 2 integration).
- DOD : AddRateLimiter partitionné PS/IP ✓, seuils configurables ✓, 429 ProblemDetails + Retry-After ✓, policy stricte sensitive ✓, tests comportements + intégration ✓, pas de donnée santé loggée ✓.

## Merged
- Merged : 2026-06-16 (human-tested, `/merge --i-tested`)
- Squash commit on `develop` :
  - api-mail : 4a8ce8a (PR #108 closed)
- dtos-mss : empty branch (no contract change) — no PR, remote branch deleted.
- develop CI : ✓ green on api-mail
- Remote feature branch deleted ; local branch kept.
