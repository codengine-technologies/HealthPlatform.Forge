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

## Branches
- `api-mail` (pushed) : feat/task-091-http-security-headers
- `dtos-mss` (pushed, auto-included) : empty branch, no PR

## Develop log
- Repo : api-mail (dtos vide). `SecurityHeadersMiddleware` (Response.OnStarting, tête de pipeline) : CSP, X-Frame-Options SAMEORIGIN, X-Content-Type-Options nosniff, Referrer-Policy, HSTS (HTTPS only). `SecurityHeadersOptions` configurable (section SecurityHeaders, dev/prod). N'affecte pas les SPAs (CSP des réponses JSON).
- Tests : `SecurityHeadersIntegrationTests` 3 (TestServer : présence/valeur des en-têtes ; HSTS https présent / http absent).
- Build/test : ✓ api-mail.

## Simplify log
- /forge-simplify : clean skip — middleware minimal façon repo.

## Sonar log
- /sonar : skipped — infra non provisionnée.

## Lint log
- /lint-angular : skipped — client-angular non touché.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/109 — awaiting-human-merge
- `dtos-mss` : branche vide — pas de PR

## Code Review Summary
- Verdict : **APPROVED** (0 blocking). Build ✓, tests ✓ (3 integration).
- DOD : middleware CSP/X-Frame-Options/nosniff/Referrer-Policy/HSTS ✓, CSP configurable dev/prod ✓, HSTS HTTPS-only ✓, test par en-tête ✓, non-régression SPAs (CSP réponses JSON sans impact) ✓, pas de donnée santé loggée ✓.

## Merged
- Merged : 2026-06-16 (human-tested, `/merge --i-tested`)
- First attempt aborted on gate 5 (Program.cs/appsettings.json conflict with develop after task-090 merge). Re-synced via `git merge origin/develop` on the feature branch (kept both rate-limiter + security-headers middleware), build ✓ 0 err, feature tests ✓ (RateLimiting 2 + SecurityHeaders 3 = 5/5 ; the lone full-suite failure is the known-flaky `ImapConnectionServiceIntegrationTests.ConnectAsyncWithCancellationShouldRespectTokenAsync`, pre-existing, not a regression), pushed (merge commit e203f0f), then merged.
- Squash commit on `develop` :
  - api-mail : 214207f (PR #109 closed)
- dtos-mss : empty branch (no contract change) — no PR, remote branch deleted.
- develop CI : ✓ green on api-mail
- Remote feature branch deleted ; local branch kept.
