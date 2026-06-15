# todo-task-092.md — Durcissement et vérification de la politique CORS

**Repos**: api-mail
**Epic**: E009

> US mono-repo justifiée : configuration transverse de l'API. Pas de changement
> de contrat fonctionnel.

## Objective

Garantir que l'API `api-mail` n'expose **aucune politique CORS permissive** en
production. Le code conserve à la fois une policy `.AllowAnyOrigin()` et une
policy restreinte `.WithOrigins(allowedOrigins)` ; il faut confirmer que seule
la politique restreinte est active et retirer / neutraliser tout reliquat
permissif (suivi de la remarque SonarQube S5122, task-045).

## Comportement attendu

- La politique CORS appliquée par l'API n'autorise que les **origines
  explicitement déclarées** (frontends officiels), via configuration.
- Aucune réponse CORS ne renvoie `Access-Control-Allow-Origin: *` en production.
- La liste des origines autorisées est configurable (appsettings / variables
  d'environnement) et peut différer entre dev et prod.
- Une origine non autorisée se voit refuser l'accès cross-origin.
- Aucune régression : les frontends officiels (Blazor, Angular) continuent
  d'appeler l'API normalement.

## Gherkin

```gherkin
Feature: Politique CORS restreinte

  Scenario: Origine autorisée
    Given un frontend officiel déclaré dans les origines autorisées
    When il appelle l'API en cross-origin
    Then la requête est autorisée

  Scenario: Origine non autorisée
    Given une origine non déclarée
    When elle tente d'appeler l'API en cross-origin
    Then l'accès cross-origin est refusé

  Scenario: Aucune permissivité générale
    Given l'API en production
    When une réponse CORS est émise
    Then elle n'autorise jamais toutes les origines indistinctement
```

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Confirmation que la policy appliquée (`UseCors`) est la version restreinte `WithOrigins`, pas `AllowAnyOrigin`
- [ ] Retrait / neutralisation de tout reliquat `AllowAnyOrigin` actif (au moins en production)
- [ ] Origines autorisées configurables (appsettings / variables d'environnement), distinctes dev/prod
- [ ] >= 1 test d'intégration : origine autorisée → en-têtes CORS présents ; origine non autorisée → accès refusé
- [ ] Vérification de non-régression : frontends officiels fonctionnels
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Depuis une origine autorisée (frontend officiel), appeler l'API → succès
- Simuler une requête depuis une origine non déclarée (ex. `curl` avec en-tête
  `Origin` arbitraire) → vérifier l'absence d'`Access-Control-Allow-Origin: *`
  et le refus cross-origin
- Vérifier en configuration prod qu'aucune permissivité générale n'est active

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : exigence transverse de sécurité (PGSSI-S)
- **Exigences DSR honorées** : PGSSI-S § sécurité applicative — restriction des origines (suivi SonarQube S5122)
- **INS** : non applicable
- **Authentification PS** : inchangé
- **Habilitations** : inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — configuration d'infrastructure
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : empêcher l'accès cross-origin non maîtrisé à une API exposant des données de santé
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : inchangé — mesure de durcissement
