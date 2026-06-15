# todo-task-091.md — En-têtes de sécurité HTTP (CSP, X-Frame-Options, HSTS…)

**Repos**: api-mail
**Epic**: E009

> US mono-repo justifiée : durcissement transverse des réponses HTTP de l'API.
> Pas de changement de contrat fonctionnel.

## Objective

Renforcer la posture de sécurité des réponses HTTP de l'API en ajoutant les
**en-têtes de sécurité** standards, aujourd'hui absents. Inspiré du
`x_frame_options = sameorigin` de Roundcube, mais élargi aux en-têtes modernes.
La **Content-Security-Policy** constitue par ailleurs une seconde barrière
contre le risque XSS traité par la task-088 (défense en profondeur).

## Comportement attendu

- L'API émet, sur ses réponses, les en-têtes de sécurité :
  - `Content-Security-Policy` (politique restrictive adaptée aux frontends)
  - `X-Frame-Options: SAMEORIGIN` (ou directive CSP `frame-ancestors` équivalente)
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy` (ex. `no-referrer` ou `strict-origin-when-cross-origin`)
  - `Strict-Transport-Security` (HSTS) en environnement HTTPS
- La CSP est suffisamment stricte pour limiter l'exécution de scripts inline non
  maîtrisés, tout en laissant fonctionner les frontends Blazor et Angular.
- Les en-têtes sont configurables (au moins la CSP) pour distinguer
  développement et production.
- L'ajout des en-têtes ne casse pas le fonctionnement des clients existants.

## Gherkin

```gherkin
Feature: En-têtes de sécurité HTTP

  Scenario: Présence des en-têtes de sécurité
    Given l'API de messagerie en fonctionnement
    When un client effectue une requête
    Then la réponse contient les en-têtes de sécurité attendus

  Scenario: Protection contre l'encadrement (clickjacking)
    Given l'API de messagerie en fonctionnement
    When une page tierce tente d'encadrer une réponse de l'API
    Then la politique d'encadrement l'en empêche

  Scenario: Les frontends légitimes continuent de fonctionner
    Given les frontends Blazor et Angular officiels
    When ils consomment l'API
    Then la politique de sécurité du contenu ne bloque pas leur fonctionnement
```

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Middleware d'en-têtes de sécurité : CSP, X-Frame-Options (ou frame-ancestors), X-Content-Type-Options, Referrer-Policy, HSTS
- [ ] CSP configurable (dev vs prod) sans recompilation
- [ ] HSTS activé uniquement en contexte HTTPS
- [ ] >= 1 test par en-tête (présence + valeur attendue) via test d'intégration sur une réponse réelle
- [ ] Vérification de non-régression : les frontends officiels fonctionnent avec la CSP active
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Effectuer une requête sur un endpoint et inspecter les en-têtes de réponse
  (outils navigateur / `curl -I`) → vérifier la présence de CSP,
  X-Frame-Options, X-Content-Type-Options, Referrer-Policy, (HSTS en HTTPS)
- Lancer Blazor et Angular contre cette API → vérifier qu'aucune ressource
  légitime n'est bloquée par la CSP (console navigateur sans violation)
- Tenter d'encadrer une réponse dans une page tierce → vérifier le blocage

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : exigence transverse de sécurité (PGSSI-S)
- **Exigences DSR honorées** : PGSSI-S § sécurité applicative — durcissement des en-têtes, défense en profondeur anti-XSS / anti-clickjacking
- **INS** : non applicable
- **Authentification PS** : inchangé
- **Habilitations** : inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — mesure préventive d'infrastructure
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : durcissement des réponses HTTP (CSP comme seconde barrière anti-XSS, anti-clickjacking, anti-sniffing, transport strict HSTS)
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : amélioration du niveau de sécurité — à mentionner dans l'AIPD
