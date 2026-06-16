# todo-task-088.md — Assainissement HTML des courriers (anti-XSS)

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009
**EpicTitle**: Durcissement sécurité de la messagerie MSSanté

## Objective

Neutraliser le risque **XSS** porté par le corps HTML des courriers MSSanté.
Aujourd'hui le HTML reçu est stocké et affiché tel quel : le backend conserve
`BodyHtml` brut, Angular appelle `bypassSecurityTrustHtml` directement (la
protection native d'Angular est désactivée) et Blazor injecte `(MarkupString)`
sans filtrage. Inspiré du sanitiseur `rcube_washtml` de Roundcube, on assainit
le HTML **côté serveur** (source de vérité) avant de le transmettre aux
frontends, et on supprime le contournement de sécurité côté clients.
Enjeu fort : un courrier de santé piégé pourrait exécuter du JavaScript dans le
contexte applicatif et exposer des données patient.

## Comportement attendu

- Le HTML d'un courrier est **assaini côté backend** avant stockage / envoi au
  client : suppression des `<script>`, des attributs `on*` (onclick, onerror…),
  des URI `javascript:`/`data:` exécutables, des balises dangereuses
  (`<object>`, `<embed>`, `<iframe>` non maîtrisée), du CSS à risque
  (`expression`, `behavior`).
- Le contenu textuel et la mise en forme légitime du courrier (titres,
  paragraphes, listes, tableaux, liens `http(s)`, images) restent préservés.
- Côté frontends, le corps de courrier n'est plus rendu via un contournement de
  sécurité non filtré : soit on consomme le HTML déjà assaini du backend via la
  sanitization native (Angular `DomSanitizer` standard, Blazor rendu maîtrisé),
  soit on isole le rendu dans une **iframe sandboxée** (à l'image de la
  `medical-html-frame` existante pour le CDA).
- Le rendu des documents médicaux CDA (déjà en iframe) n'est pas régressé.

## Gherkin

```gherkin
Feature: Assainissement HTML des courriers

  Scenario: Un courrier contenant un script est neutralisé
    Given un courrier dont le corps HTML contient un script malveillant
    When le médecin ouvre ce courrier
    Then le script n'est pas exécuté
    And le contenu lisible du courrier reste affiché

  Scenario: La mise en forme légitime est préservée
    Given un courrier contenant des titres, listes, tableaux et liens
    When le médecin ouvre ce courrier
    Then la mise en forme est correctement affichée
    And les liens externes restent cliquables

  Scenario: Un gestionnaire d'évènement inline est retiré
    Given un courrier contenant une image avec un attribut onerror
    When le médecin ouvre ce courrier
    Then l'attribut onerror est supprimé et aucun code ne s'exécute
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Assainisseur HTML côté backend (bibliothèque éprouvée, ex. HtmlSanitizer/Ganss) appliqué au corps HTML des courriers avant stockage et avant exposition API
- [ ] Suppression des vecteurs XSS : `<script>`, attributs `on*`, `javascript:`/`data:` exécutables, `<object>`/`<embed>`, CSS `expression`/`behavior`
- [ ] Préservation de la mise en forme légitime (titres, listes, tableaux, liens http(s), images)
- [ ] Angular : suppression du `bypassSecurityTrustHtml` brut sur le corps de courrier (rendu via sanitization standard ou iframe sandboxée), `data-testid` inchangés
- [ ] Blazor : corps de courrier rendu de façon maîtrisée (HTML pré-assaini ou iframe sandboxée), plus d'injection `(MarkupString)` de HTML non filtré
- [ ] Le rendu CDA en iframe existant n'est pas régressé
- [ ] >= 1 test unitaire backend par vecteur (script retiré, on* retiré, javascript: retiré, mise en forme préservée)
- [ ] >= 1 test d'intégration : courrier piégé récupéré via l'API → HTML retourné exempt de vecteur exécutable
- [ ] >= 1 test de composant par frontend (le corps assaini s'affiche, aucun script exécuté)
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (corps du courrier jamais loggué)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Préparer (en boîte de test) un courrier HTML contenant
  `<script>alert('xss')</script>` et une `<img src=x onerror="alert(1)">`
- Ouvrir ce courrier sur chaque frontend → vérifier qu'aucune alerte ne
  s'exécute et que le texte reste lisible
- Ouvrir un courrier riche (titres, tableau, liens) → vérifier la mise en forme
- Ouvrir un document CDA → vérifier l'absence de régression du rendu en iframe

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : exigence transverse de sécurité (PGSSI-S) — la messagerie MSSanté référencée doit protéger l'intégrité du poste du PS
- **Exigences DSR honorées** : sécurité applicative — PGSSI-S § intégrité / protection contre le code malveillant
- **INS** : non applicable — pas de manipulation de l'identité patient
- **Authentification PS** : inchangé
- **Habilitations** : inchangé
- **Interop CI-SIS** : non applicable — l'assainissement ne modifie pas les documents CDA (traités via `interop-cda`), seulement le corps HTML d'affichage
- **Tracé PGSSI-S** : journaliser la détection/neutralisation d'un contenu actif dans un courrier (sans logguer le contenu)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : objectif central — prévenir l'exécution de code (XSS) susceptible d'exfiltrer des données de santé ; PGSSI-S § cryptographie/intégrité
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : amélioration du niveau de sécurité — noter la mesure de réduction de risque dans l'AIPD

## Branches
- `api-mail` (pushed) : feat/task-088-html-sanitization-xss
- `client-blazor` (pushed) : feat/task-088-html-sanitization-xss
- `dtos-mss` (pushed, auto-included) : feat/task-088-html-sanitization-xss
- `client-angular` (code-only) : forge writes on `feature/nova-rewriting-mss` — humain gère git/PR TFS

## Develop log
- Repos touched : api-mail, client-blazor, client-angular (code-only). dtos-mss : **no contract change** (MailContentDto.BodyHtml existait déjà) → branche vide, pas de PR.
- DTOs published : none (pas de changement de contrat).
- Backend (api-mail) : `IHtmlBodySanitizer`/`HtmlBodySanitizer` — assainisseur allowlist bâti sur **AngleSharp 1.5.0** (déjà dépendance du repo ; HtmlSanitizer/Ganss écarté car il épingle AngleSharp [0.17.1] incompatible + advisory NU1902). Appliqué **au stockage** (`EmailBuildingService.BuildMailDtoAsync`) et **à l'exposition** (`ImapService.GetEmailContentAsync`, couvre lignes DB legacy + fetch frais). Retire `<script>`, attributs `on*`, `javascript:`/`vbscript:`/`data:` exécutables (autorise `data:image/*` sur `<img>`), `<object>/<embed>/<iframe>/...`, CSS `expression`/`behavior`/`@import`/`-moz-binding` ; préserve titres/listes/tableaux/liens http(s)/images. CDA non touché (chemin séparé).
- Blazor : `MailReadOnlyView` — corps rendu dans l'iframe sandboxée (`loadHtmlInShadowDom`) au lieu de `(MarkupString)` brut. `MailBodyComponent` utilisait déjà l'iframe (inchangé).
- Angular (code-only, `feature/nova-rewriting-mss`) : `mail-read-only-view` — corps rendu via `mss-medical-html-frame` (iframe sandboxée déjà utilisée par `mail-body`) au lieu de `bypassSecurityTrustHtml`. Fichiers : `mail-read-only-view.component.{ts,html}` + `.spec.ts`.
- Tests : api-mail `HtmlBodySanitizerTests` 12 (script/on*/javascript:/data:/css/iframe/unwrap/idempotence/formatage préservé) + `EmailBuildingServiceTests` (ctor) + `ImapService` tests (65) + intégration `MailHtmlSanitizationIntegrationTests` (courrier piégé stocké → exposition assainie) ; Blazor `MailReadOnlyViewTests` 2 ; Angular `mail-read-only-view.component.spec` 2, `nx test mss-lib` 223/223, lint 0 erreur.
- Local build/test : ✓ api-mail, ✓ client-blazor, ✓ client-angular.

## Simplify log
- /forge-simplify : clean skip — code neuf aligné sur les patterns existants (réutilise AngleSharp, EmailBuildingService/ImapService chokepoints, medical-html-frame, loadHtmlInShadowDom). Pas de commit.

## Sonar log
- /sonar : skipped — infra SonarQube non provisionnée (serveur injoignable, SONAR_TOKEN absent). Best-effort. Code écrit selon dotnet-coding-rules.

## Lint log
- /lint-angular (scope tag:scope:mss, base origin/next) : 0 erreur sur le code task-088 ; 33 warnings pré-existants hors scope acceptés ; `nx build mss-lib` ✓, `nx test mss-lib` 223/223. Code-only (pas de git).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/107 — awaiting-human-merge
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/61 — awaiting-human-merge
- `dtos-mss` : branche vide (aucun changement de contrat) — pas de PR
- `client-angular` (code-only) : humain gère commit/push TFS + PR. Fichiers : `libs/mss/src/features/mail/components/mail-read-only-view/{*.ts,*.html,*.spec.ts}` (uncommitted sur `feature/nova-rewriting-mss`)

## Code Review Summary
- Verdict : **APPROVED** (0 blocking).
- Build ✓ api-mail / client-blazor / client-angular(nx). Tests ✓ api-mail (sanitizer 12 + integration 1 + services 65), Blazor bUnit 2, Angular mss-lib 223/223, lint 0 erreur.
- DOD : assainisseur backend (allowlist AngleSharp) ✓, vecteurs XSS retirés ✓, formatage légitime préservé ✓, Angular bypassSecurityTrustHtml retiré sur le corps ✓, Blazor plus de MarkupString brut ✓, CDA iframe non régressé ✓, tests par vecteur + intégration + composant ✓, ProblemDetails (GlobalExceptionHandler) ✓, aucun corps loggué ✓.

## Merged
- Merged : 2026-06-16 (human-tested, `/merge --i-tested`)
- First attempt aborted on gate 5 (conflict with develop after task-087 merge) ; human re-synced the api-mail branch onto develop, then re-ran /merge.
- Squash commits on `develop` :
  - api-mail      : a8a0c08 (PR #107 closed)
  - client-blazor : 42b06aa (PR #61 closed)
- dtos-mss : empty branch (no contract change) — no PR, remote branch deleted.
- client-angular (code-only) : managed manually by the human (TFS)
- develop CI : ✓ green on api-mail, client-blazor
- Remote feature branches deleted ; local branches kept.
