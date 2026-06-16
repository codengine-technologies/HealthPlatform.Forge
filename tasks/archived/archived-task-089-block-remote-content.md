# todo-task-089.md — Blocage du contenu distant des courriers (anti-pistage)

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009

## Objective

Empêcher le **chargement automatique des ressources distantes** (images, pixels
traceurs, ressources externes) contenues dans le corps HTML des courriers.
Inspiré du mécanisme `show_images` / « charger les images » de Roundcube. Sur
une messagerie de santé, le chargement silencieux d'un pixel distant confirme à
un tiers la lecture d'un courrier (fuite d'information et confidentialité
patient) et expose l'IP/poste du professionnel.

## Comportement attendu

- Par défaut, les ressources distantes (`<img src="http…">`, arrière-plans CSS
  distants, ressources externes) ne sont **pas chargées** à l'ouverture d'un
  courrier ; les sources distantes sont neutralisées (réécriture / suppression).
- Une **bannière non bloquante** informe le PS que des images distantes ont été
  bloquées, avec une action « Afficher les images ».
- Le clic sur « Afficher les images » charge les ressources distantes **pour ce
  courrier uniquement** (pas de mémorisation par défaut).
- Les images **embarquées** (pièces jointes inline `cid:`) restent affichées
  normalement — seules les ressources **distantes** sont bloquées.
- Le comportement est cohérent entre Blazor et Angular.

## Gherkin

```gherkin
Feature: Blocage du contenu distant des courriers

  Scenario: Images distantes bloquées par défaut
    Given un courrier contenant une image hébergée sur un serveur externe
    When le médecin ouvre ce courrier
    Then l'image distante n'est pas chargée
    And une bannière propose d'afficher les images

  Scenario: Affichage à la demande
    Given un courrier dont les images distantes ont été bloquées
    When le médecin choisit d'afficher les images
    Then les images distantes de ce courrier sont chargées

  Scenario: Les images embarquées restent affichées
    Given un courrier contenant une image embarquée en pièce jointe
    When le médecin ouvre ce courrier
    Then l'image embarquée est affichée sans blocage
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Neutralisation des ressources distantes dans le HTML de courrier (réécriture des `src`/url() distants) — cohérente avec l'assainissement de la task-088
- [ ] Distinction ressource distante (bloquée) vs ressource embarquée `cid:` (affichée)
- [ ] Blazor : bannière « images bloquées » + action « Afficher les images » (ce courrier), aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] L'affichage à la demande ne mémorise pas l'expéditeur par défaut
- [ ] >= 1 test unitaire par comportement (distant bloqué, embarqué préservé, affichage à la demande)
- [ ] >= 1 test de composant par frontend (bannière affichée, action recharge les images)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir un courrier contenant une image distante (`<img src="https://…">`)
  → vérifier qu'elle n'est pas chargée et que la bannière apparaît
- Cliquer « Afficher les images » → vérifier le chargement pour ce courrier
- Ouvrir un courrier avec image inline (`cid:`) → vérifier l'affichage direct
- Surveiller les requêtes réseau : aucune requête vers le serveur distant avant
  l'action explicite du PS

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : exigence transverse de sécurité / confidentialité (PGSSI-S)
- **Exigences DSR honorées** : PGSSI-S § confidentialité — non-divulgation de la lecture d'un courrier de santé
- **INS** : non applicable
- **Authentification PS** : inchangé
- **Habilitations** : inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : optionnel — journaliser l'action « afficher les images » (sans contenu)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : empêcher la fuite d'accusé de lecture implicite (pixel traceur) et l'exposition de l'IP/poste du PS à un tiers
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : amélioration de la confidentialité — mesure à mentionner dans l'AIPD

## Branches
- `client-blazor` (pushed) : feat/task-089-block-remote-content
- `client-angular` (code-only) : forge writes on `feature/nova-rewriting-mss`
- `api-mail` (pushed) : feat/task-089-block-remote-content — **frontend-only US, no backend change expected → empty branch, no PR**
- `dtos-mss` (pushed, auto-included) : empty branch, no PR

## Develop log
- Repos touched : client-blazor, client-angular (code-only). **api-mail / dtos-mss : branches vides** (US frontend-only — le blocage de contenu distant est un contrôle de confidentialité au moment du rendu, là où vit l'état "afficher à la demande, ce courrier uniquement"). Aucun changement backend ni de contrat → pas de PR sur api-mail/dtos.
- Approche : neutralisation des ressources distantes (`src`/`background`/`srcset` http(s), `url()` CSS distant) **avant** l'injection dans l'iframe sandboxée existante (cohérent avec task-088). `cid:`/`data:` préservés. Bannière "images bloquées" + "Afficher les images" (ce courrier uniquement, pas de mémorisation). Implémenté à l'identique dans les 2 fronts (pattern task-084).
- Blazor : helper pur `RemoteContentBlocker` (`Domain/Helpers`) + `MailBodyComponent` (bannière au-dessus du conteneur shadow-DOM, `loadHtmlInShadowDom` reçoit le HTML bloqué ou l'original selon `_showRemoteImages` ; reset par courrier). Clés `Localizer` `RemoteImagesBlocked`/`ShowImages` (en+fr), `data-testid` `remote-images-banner`/`show-remote-images-btn`.
- Angular (code-only, `feature/nova-rewriting-mss`) : util pur `remote-content.util.ts` (`core/utils`) + `mail-body.component` (getter `mailBodyHtml` renvoie bloqué/original, getter `hasBlockedRemoteContent`, `showImages()`) ; bannière FR en dur, tokens `var(--ds-color-*)`.
- Tests : Blazor `RemoteContentBlockerTests` 9 + `MailBodyRemoteContentTests` 2 (bannière affichée, action masque la bannière), suite plugin 126/128 (2 skips pré-existants) ; Angular `remote-content.util.spec` 7 + `mail-body.component.spec` 3, `nx test mss-lib` 233/233, lint 0 erreur.
- Local build/test : ✓ client-blazor, ✓ client-angular.

## Simplify log
- /forge-simplify : clean skip — code aligné sur les patterns existants (helper pur façon task-084, iframe sandboxée réutilisée). Pas de commit.

## Sonar log
- /sonar : skipped — api-mail non touché (US frontend-only) + infra SonarQube non provisionnée.

## Lint log
- /lint-angular (scope tag:scope:mss, base origin/next) : 2 erreurs prettier auto-fixées sur `remote-content.util.ts` → 0 erreur ; 33 warnings pré-existants hors scope acceptés ; fix lint hors-scope sur `problem-details.utils.ts` reverté ; `nx build mss-lib` ✓, `nx test mss-lib` 233/233.

## PRs
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/62 — awaiting-human-merge
- `api-mail` : branche vide (US frontend-only) — pas de PR
- `dtos-mss` : branche vide — pas de PR
- `client-angular` (code-only) : humain gère commit/push TFS + PR. Fichiers task-089 : `libs/mss/src/core/utils/remote-content.util.{ts,spec.ts}`, `libs/mss/src/features/mail/components/mail-body/{*.ts,*.html,*.scss,*.spec.ts}` (uncommitted sur `feature/nova-rewriting-mss`, cumulés avec 087/088).

## Code Review Summary
- Verdict : **APPROVED** (0 blocking).
- Build ✓ client-blazor / client-angular(nx). Tests ✓ Blazor 126/128 (2 skips pré-existants), Angular mss-lib 233/233, lint 0 erreur.
- DOD : neutralisation distant cohérente task-088 ✓, distinction distant/cid: ✓, bannière + action (Blazor+Angular) ✓, i18n (Blazor) / FR en dur (Angular) ✓, pas de mémorisation expéditeur ✓, tests par comportement + composant ✓, aucune donnée santé loggée ✓.

## Merged
- Merged : 2026-06-16 (human-tested, `/merge --i-tested`)
- US frontend-only : seule la PR Blazor portait du code.
- Squash commit on `develop` :
  - client-blazor : 6b899da (PR #62 closed)
- api-mail / dtos-mss : empty branches (frontend-only US, no backend/contract change) — no PR, remote branches deleted.
- client-angular (code-only) : managed manually by the human (TFS, `feature/nova-rewriting-mss`).
- develop CI : ✓ green on client-blazor
- Remote feature branches deleted ; local branches kept.
