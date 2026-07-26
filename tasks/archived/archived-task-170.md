# todo-task-170.md — Tests E2E visuels client-mobile avec login PSC assisté humain

**Repos**: client-mobile
**Dependencies**: —
**Single frontend**: true

## Branches
- `client-mobile` (pushed) : `feat/task-170-e2e-visual-client-mobile-psc` — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-170-e2e-visual-client-mobile-psc

> **Companion control-plane (hors PR repo)** : cette US remplace aussi
> l'outillage `/qa`. La réécriture de `agents/qa.md`, la suppression du
> scaffold Blazor `tests/E2E/`, et la mise à jour de la ligne `/qa` dans
> `CLAUDE.md` sont des changements **control-plane** (racine du workspace,
> jamais poussée — cf. « Workspace layout — POLYREPO »). Ils font partie du
> périmètre de la US mais ne transitent pas par la PR `client-mobile` : le
> humain (ou une passe d'édition control-plane) les applique. Voir la section
> « Livrables » ci-dessous.

## Objective

Remplacer la suite E2E actuelle — orientée `client-blazor` (4 specs Playwright
sous `tests/E2E/`, ciblant `https://localhost:7213`, bringup Aspire+Blazor) —
par une suite E2E **orientée `client-mobile`**, **visuelle**, dont
l'**authentification Pro Santé Connect est réalisée à la main par un humain**
à chaque run (pas d'automatisation du login PSC).

Chaque test :
1. ouvre l'app mobile servie localement (`ng serve`, viewport 390×844) en mode
   **headed** ;
2. **attend que l'humain complète le login PSC** dans la fenêtre ouverte (le
   test poll l'apparition de la coquille `ion-tabs` post-login, timeout large
   ~5 min) ;
3. navigue **chaque écran touché** de l'app et en produit une **capture
   390×844 pour revue humaine** (pas de comparaison pixel) ;
4. n'échoue **que** sur écran blanc / crash de navigation (même contrat que
   `/verify-visual`) — l'écart design est jugé par l'humain à la revue.

La commande `/qa` est **repurposée** pour piloter ce flux mobile (elle était
Blazor). La suite Blazor `tests/E2E/` est **supprimée**.

**Pourquoi mono-frontend** : l'US ne touche que l'outillage de test de
`client-mobile`. Aucun code produit backend/Blazor/Angular n'est modifié.

## Contexte technique (pour `/develop`)

- L'app mobile se sert via `npm start` = `ng serve --proxy-config
  proxy.conf.json` (Angular CLI, port 4200 par défaut) — le proxy route les
  appels API vers le backend réel.
- Le backend réel est démarré via Aspire AppHost (`Api/Mail/src/AppHost`,
  profil `https`) — le login PSC exerce **la vraie chaîne OIDC** (pas de
  bypass, pas de fixtures).
- `Client/Mobile/e2e/` est **vide** aujourd'hui → c'est là que vit la nouvelle
  suite Playwright (repo `client-mobile`, remote GitHub, donc **committée**).
- Ne pas confondre avec `/verify-visual` (`tools/visual-verify/capture.mjs`) qui
  reste **inchangé** : lui mocke l'API par fixtures + session factice, **aucun
  auth**. La présente US est le pendant **auth réelle PSC + backend réel**.
- Contrat de wait post-login : la coquille `ion-tabs`
  (Messages/Patients/Paramètres) devient visible après un login PSC réussi
  (cf. mémoire coquille ion-tabs). C'est le signal « login OK » que le test
  attend.

## Écrans à couvrir (tous les écrans mobiles touchés à ce jour)

Un spec (ou un data-driven loop) produit une capture par écran :

- `login` — écran d'entrée PSC (pré-auth, avant login)
- `tabs/home`
- `tabs/messages` — inbox / liste des mails
- liste des dossiers (`mail-folder-list`)
- `mail-detail` — ouverture d'un mail (1er mail de l'inbox)
- `mail-search`
- `tabs/patients`
- `tabs/settings`
- `signatures`
- `contacts`
- `mss-onboarding` : `mss-setup` / `mss-unconfigured` (si atteignables dans
  l'état du compte de test)

Si un écran n'est pas atteignable dans l'état du compte de test (ex. onboarding
déjà fait), le logguer comme **skip explicite** (pas un échec).

## Livrables

### A. Repo `client-mobile` (PR)

- `Client/Mobile/e2e/playwright.config.ts` — `testDir`, viewport 390×844
  (`devices['Pixel 5']` ou config manuelle), `headless: false` par défaut pour
  ce projet (login humain), `workers: 1`, `fullyParallel: false`, reporters
  `list` + `html`, `baseURL` = URL du `ng serve` (`http://localhost:4200`),
  `ignoreHTTPSErrors`, capture screenshot systématique.
- Un **helper de login PSC assisté** : ouvre `/login`, laisse l'humain faire le
  PSC, `await expect(page.locator('ion-tabs')).toBeVisible({ timeout:
  300_000 })`. Réutilisé en tête de chaque spec (ou via un fixture Playwright).
- Les **specs de capture** couvrant les écrans listés — assertion **anti-écran
  blanc** (`ion-content` visible + `body.innerText` non vide, en s'appuyant sur
  la leçon `reference_verify_visual_innertext_blank_gap` : ne pas se contenter
  de `innerText`, vérifier aussi un locator visible car un contenu clippé
  largeur 0 passe le check texte) + `page.screenshot()` rangé par run.
- Sortie des captures : `Client/Mobile/e2e/screenshots/{run-date}/{écran}.png`
  (git-ignorées par défaut — voir garde-fou données de santé ci-dessous).
- `Client/Mobile/e2e/.gitignore` : `node_modules/`, `playwright-report/`,
  `test-results/`, `screenshots/` (les captures ne sont **pas** committées par
  défaut à cause du risque DSCP).
- Script `package.json` mobile : `"e2e": "playwright test --config
  e2e/playwright.config.ts"` (ou équivalent).

### B. Control-plane (workspace root — hors PR, appliqué par l'humain)

- **Réécrire `agents/qa.md`** : playbook mobile — pré-vol (ports, Docker,
  Node), start backend AppHost, `ng serve` client-mobile, lancement Playwright
  **headed**, attente login PSC humain, captures, teardown, rapport. Retirer
  toute la logique bypass/TestAuthService/Blazor `:7213`.
- **Supprimer** le scaffold Blazor `tests/E2E/` (4 specs + config + report).
- **Mettre à jour la ligne `/qa`** dans `CLAUDE.md` (table Commands) pour
  refléter la cible mobile + login PSC humain.
- **Mettre à jour `.claude/commands/qa.md`** (le slash-command) en cohérence.

## Definition of Done

Vérifiable par le forge (repo `client-mobile`) :
- [ ] `Client/Mobile/e2e/playwright.config.ts` présent, viewport 390×844,
      headed par défaut, `workers: 1`
- [ ] Helper de login PSC assisté présent (attente `ion-tabs`, timeout ≥ 5 min)
- [ ] Un spec/capture par écran de la liste « Écrans à couvrir » (skip explicite
      si écran non atteignable)
- [ ] Assertion anti-écran-blanc = `ion-content` visible **ET** texte non vide
      (pas `innerText` seul — cf. leçon connue)
- [ ] `npm ci && npm run build` du repo `client-mobile` reste vert (l'ajout du
      projet e2e ne casse pas le build app)
- [ ] `npm test -- --watch=false --browsers=ChromeHeadless` reste vert
- [ ] `e2e/.gitignore` exclut `screenshots/`, `test-results/`,
      `playwright-report/`, `node_modules/`
- [ ] Aucune capture committée dans la PR (ou, si committée, prouvée issue d'un
      **compte + mailbox de test anonymisés** sans DSCP)

Vérifiable control-plane (humain) :
- [ ] `agents/qa.md` réécrit en playbook mobile (plus aucune réf. Blazor/bypass)
- [ ] `tests/E2E/` Blazor supprimé
- [ ] Ligne `/qa` de `CLAUDE.md` + `.claude/commands/qa.md` mises à jour

Vérifiable par l'humain (run réel `/qa`, hors chaîne autonome) :
- [ ] `/qa` ouvre l'app mobile en headed, le login PSC manuel aboutit, la
      coquille `ion-tabs` s'affiche
- [ ] Une capture 390×844 est produite pour chaque écran atteignable
- [ ] Aucun écran blanc / crash de navigation

## Manual Test Plan

Prérequis : un **compte Pro Santé Connect de test** (e-CPS / bac à sable) dont
la **boîte MSSanté ne contient que des messages de test anonymisés** (aucune
donnée patient réelle — voir garde-fou).

1. Backend : `cd Api/Mail/src/AppHost && dotnet run --launch-profile https`
   (attendre l'api sur `:5052`).
2. App mobile : `cd Client/Mobile && npm start` (ng serve `:4200`, proxy vers
   le backend).
3. Lancer `/qa` (repurposé) — il ouvre Playwright **en fenêtre visible** sur
   l'écran `login`.
4. **Réaliser le login Pro Santé Connect à la main** dans la fenêtre (e-CPS /
   OTP). Le test attend l'affichage de la coquille `ion-tabs`.
5. Laisser la suite naviguer chaque écran et produire les captures.
6. Vérifier le rapport : une capture 390×844 par écran, aucun écran blanc.
   Ouvrir `Client/Mobile/e2e/playwright-report/index.html`.
7. Teardown auto : arrêt du `ng serve`, de l'AppHost, des conteneurs Docker.

Données de test : **jamais** de mailbox de production. Compte PSC de test +
messages synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de test (QA) de `client-mobile` ;
  ne produit ni n'échange de document métier. Soutient indirectement la qualité
  des exigences messagerie MSSanté du couloir médecine de ville.
- **Vague Ségur** : hors Ségur — tooling de test.
- **Exigences DSR honorées** : non applicable — tooling de test. (Le flux
  exercé — auth PSC bout-en-bout — recoupe l'exigence socle d'authentification,
  mais l'US ne livre pas la fonctionnalité, seulement son test.)
- **INS** : non applicable en soi. **Attention** : les captures d'une session
  PSC réelle peuvent afficher des INS/traits patient → couvert par le garde-fou
  données de santé (mailbox de test anonymisée + captures non committées).
- **Authentification PS** : **Pro Santé Connect / e-CPS**, niveau eIDAS
  substantiel — **cœur de l'US**. Réalisée **manuellement par l'humain** à
  chaque run ; aucune automatisation, aucun secret PSC stocké, aucun bypass.
- **Habilitations** : le compte de test porte un RPPS de test ; aucun contrôle
  d'habilitation ajouté par l'US.
- **Interop CI-SIS** : non applicable — pas d'échange CDA/FHIR/HL7v2 produit.
- **Tracé PGSSI-S** : non applicable à l'outil de test lui-même (le backend réel
  journalise sa propre auth comme en prod ; l'US n'ajoute pas de traçabilité).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : non — exécution locale poste développeur (dev), jamais
  contre un environnement HDS/production.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données
  réelles, sous réserve du garde-fou (mailbox de test anonymisée).

### Garde-fou données de santé (non négociable)

Un login PSC réel ouvre une **boîte MSSanté réelle** → une capture d'écran peut
contenir des DSCP (nom/INS patient, contenu MSSanté, contenu CDA). Donc :

- [ ] Le run officiel `/qa` utilise **exclusivement** un **compte PSC de test**
      dont la mailbox ne contient que des **messages synthétiques anonymisés**.
- [ ] Les captures sont **git-ignorées par défaut** ; aucune capture n'est
      committée/poussée/jointe à une PR sans preuve d'absence de DSCP.
- [ ] Interdiction absolue de logguer / capturer contre une **mailbox de
      production** ou un patient réel.

Si aucun compte + mailbox de test anonymisés n'est disponible → **blocker** :
ouvrir `questions/task-170.md` avant tout run réel, ne pas improviser avec de la
donnée réelle.

## Develop log

- Repos touched : `client-mobile` (pushable). No DTO / interop change.
- Deliverable A (repo, PR) — new Playwright visual E2E project under
  `Client/Mobile/e2e/` :
  - `playwright.config.ts` (headed, viewport 390×844, workers 1, timeout 15 min)
  - `support/psc-login.ts` (human-assisted PSC login wait — `ion-tabs`, 5 min)
  - `support/screens.ts` (URL-addressable screen inventory)
  - `support/visual.ts` (capture + soft anti-blank guard — `ion-content`
    visible + real bounding box + non-empty text, covering the clipped-width-0
    gap)
  - `specs/visual-tour.spec.ts` (login → wait PSC → capture every screen →
    folder list → mail detail)
  - `.gitignore` (screenshots/ git-ignored — health-data guardrail), `README.md`
  - `package.json` : `e2e` / `e2e:report` scripts + `@playwright/test`,
    `@types/node` devDeps
- Isolation verified : `e2e/` is outside `ng build` (src/main.ts entry),
  `ng test` (src/**/*.spec.ts) and `ng lint` (src/** patterns) → app CI
  unaffected.
- Validation :
  - `npx tsc -p e2e/tsconfig.json --noEmit` : ✓ e2e typechecks clean
  - `npm run build` : ✓ (exit 0, only pre-existing SCSS budget warnings)
  - `npm test -- --watch=false --browsers=ChromeHeadless` : ✓ 761/761
- Commit : `client-mobile` 70bdd9f `test(mobile): add visual E2E suite with
  human-assisted PSC login (task-170)` — pushed to
  `feat/task-170-e2e-visual-client-mobile-psc`.
- Deliverable B (control-plane, workspace root, local-only — NOT in the repo PR) :
  - `agents/qa.md` rewritten → mobile playbook (AppHost + `ng serve` :4200 +
    headed Playwright + human PSC login + captures + teardown ; all
    Blazor/bypass logic removed).
  - `tests/E2E/` (Blazor bypass suite) deleted (`git rm` in the local-only
    workspace-root repo — uncommitted, human owns control-plane commits).
  - `.claude/commands/qa.md` rewritten to match.
  - `CLAUDE.md` : no `/qa` row existed → nothing to update (N/A).
- DOD self-check : repo items ✓ (build/test/typecheck green, `e2e/` present,
  `.gitignore` excludes screenshots, no capture committed). Control-plane items
  ✓ (agents/qa.md + command doc rewritten, tests/E2E removed). Human-run items
  (real `/qa` with PSC login, one capture per screen, no blank) → deferred to
  manual `/qa` (HAG) — the suite is headed + human login, not runnable in the
  autonomous chain.
- Next step : /forge-simplify task-170 → (client-mobile touched) → /lint-mobile
  → /verify-visual (no screen touched → skip) → /review.

## Simplify log

- Touched eligible repo : `client-mobile` (e2e/ Playwright harness). `dtos-mss`/`interop-cda` never touched (contract carriers).
- Applied : dropped the misleading `devices['Desktop Chrome']` spread + redundant per-project overrides in `e2e/playwright.config.ts` → single named chromium project, all settings from top-level `use`.
- Re-validation : `tsc -p e2e/tsconfig.json --noEmit` ✓ ; `playwright test --list` ✓ (1 spec discovered). App build/test unaffected (e2e isolated).
- Commit : `client-mobile` c3a8a43 `refactor(mobile): simplify e2e Playwright project config` — pushed.
- Next step : /lint-mobile task-170.

## Lint mobile log

- Skip clean : task-170 touched `client-mobile` but only `e2e/` (Playwright harness, outside `ng lint`'s `src/**` scope) + package files. 0 `src/` files changed.
- `npm run lint` baseline : ✓ « All files pass linting » (no fresh lintable code to fix, no commit).
- Next step : /review task-170 (/verify-visual skips — no mobile screen touched).

## Visual verify log

- Skip clean : task-170 ne touche aucun écran `client-mobile` (0 fichier `src/` modifié) et n'a pas de `## Stitch design log`. C'est de l'outillage de test E2E, pas un écran produit → rien à capturer ici.
- La vérification visuelle réelle des écrans se fait via la suite livrée (`/qa`, login PSC humain), hors chaîne autonome.
- Next step : /review task-170.

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/61 — label `awaiting-human-merge`
- Control-plane (workspace root, local-only, hors PR — human owns the commit) : `agents/qa.md` réécrit, `.claude/commands/qa.md` réécrit, `tests/E2E/` supprimé.

## Code Review Summary

- Verdict : **APPROVED** (1 DOD gap trouvé et corrigé en review : ajout des écrans mss-onboarding au tour).
- Validation : `ng build` ✓ · `ng test` ✓ 761/761 · `tsc` e2e ✓ · `playwright --list` ✓.
- ⚠️ Non-bloquant : suite headed + login PSC humain → preuve runtime = run manuel `/qa` (HAG). Hors chaîne autonome.
- Qualité : /sonar skipped — api-mail non touché.
- Vérification visuelle : /verify-visual skip clean — aucun écran produit touché.

## Merged

- **Date** : 2026-07-25 08:24 UTC (`/merge 170 --i-tested`)
- `client-mobile` : PR #61 squash-merged → `develop` @ `c91b9aff3aa2563a8012a85ebcc18b2bb4da0c88`
  - Remote `feat/task-170-e2e-visual-client-mobile-psc` supprimée ; branche locale conservée.
  - ⚠️ CI PR rouge au moment du merge — **override humain explicite** : échec limité à
    l'upload de l'APK debug (`Artifact storage quota has been hit`, infra GitHub),
    le build compilait. CI develop : https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/30151038991
- Control-plane (workspace root, hors PR) : `agents/qa.md` + `.claude/commands/qa.md`
  réécrits, `tests/E2E/` Blazor supprimé — commits humains.
- Staging : aucune branche `forge/staging-task-*` sur les repos pushables — rien à nettoyer.
