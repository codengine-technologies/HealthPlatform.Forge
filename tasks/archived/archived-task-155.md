# todo-task-155.md — Déconnexion résiliente : un 401 au logout ne bloque jamais la sortie

**Repos**: client-blazor, client-mobile
**Dependencies**: —
**Single frontend**: false

## Objective

Graver la règle métier : **la déconnexion locale aboutit toujours**, quelle que
soit la réponse du serveur d'authentification à l'appel de déconnexion.

**Scénario canonique** : le cookie de session du proxy d'authentification
(`proxy-session-id`) a expiré et a disparu du navigateur/WebView. L'appel de
déconnexion part alors sans session → le serveur répond **401**. Ce 401
signifie que la session côté serveur est déjà expirée ou invalidée —
l'objectif de la déconnexion est **déjà atteint** : l'application doit
**basculer immédiatement sur l'écran de connexion**. Ce cas (et tout autre
échec : 5xx, réseau coupé) ne doit jamais laisser le praticien coincé dans
l'application ni laisser des jetons résiduels sur le poste :

1. purge systématique de la session locale (jetons, état d'authentification) ;
2. retour à l'écran de connexion ;
3. aucun message d'erreur bloquant — au plus une trace technique côté client
   (sans jeton ni donnée de santé).

### État des lieux (audit 2026-07-06)

- **client-blazor — ❌ à corriger** : l'appel de déconnexion lève une exception
  sur tout statut non-2xx (dont 401) ; le service attrape l'exception et se
  contente de la logger, **sans purger l'authentification locale**. Sur session
  expirée, le praticien reste avec un état connecté résiduel. La purge locale
  doit s'exécuter dans tous les cas (succès, 401, 5xx, réseau), et le flux de
  la page de déconnexion doit se terminer sur l'écran de connexion.
- **client-mobile — ✅ conforme, test manquant** : l'erreur est déjà avalée et
  la purge locale + redirection login s'exécutent. Ajouter le **test unitaire
  de non-régression** qui fige le cas 401 (aucun changement de comportement).
- **client-angular — conforme, hors scope** : double filet déjà en place
  (erreur avalée + purge du state + redirection). Aucun code à écrire — repo
  volontairement non listé (justification de scope réduit).

## Definition of Done

- [ ] Build passe sur les repos listés (0 erreur) ; tests 0 échec
- [ ] `client-blazor` : logout avec réponse serveur 401 → authentification locale purgée + arrivée sur l'écran de connexion (pas d'état connecté résiduel)
- [ ] `client-blazor` : même comportement sur 5xx et sur échec réseau
- [ ] `client-blazor` : logout nominal (2xx) inchangé
- [ ] `client-blazor` : tests unitaires du service d'authentification couvrant les 4 cas (2xx, 401, 5xx, réseau) — la purge locale est appelée dans chaque branche
- [ ] `client-mobile` : test unitaire de non-régression `$logout` sur 401 → le flux complète, la session locale est purgée, redirection login (aucun changement de code attendu)
- [ ] Aucun jeton, cookie de session ou donnée de santé dans les traces client ajoutées
- [ ] `data-testid` inchangés (pas de nouvel élément interactif attendu)

## Manual Test Plan

- **Blazor** : `cd Client/Blazor && dotnet run` ; se connecter ; simuler
  l'expiration de session en **supprimant le cookie `proxy-session-id`**
  (outils développeur → Application → Cookies), puis cliquer « Déconnexion »
  → l'écran de connexion s'affiche, pas de message d'erreur bloquant ; se
  reconnecter fonctionne normalement
- **Blazor** : couper le réseau, cliquer « Déconnexion » → même résultat
  (retour connexion, pas de blocage)
- **Mobile** : `cd Client/Mobile && npm start` ; se connecter ; simuler
  l'expiration (supprimer le cookie `proxy-session-id` dans la WebView/le
  navigateur de dev) ; menu → Déconnecter → confirmation → retour à l'écran
  de connexion sans erreur
- Vérifier dans les deux cas qu'une nouvelle connexion repart de zéro (aucun
  état résiduel de l'ancienne session)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — robustesse d'un mécanisme existant
- **Exigences DSR honorées** : non applicable — durcissement de la déconnexion (hygiène de session)
- **INS** : non applicable — aucun traitement d'INS dans ce flux
- **Authentification PS** : cœur de la US — fin de session e-CPS/PSC fiable ; la purge locale inconditionnelle garantit qu'aucun jeton n'outrepasse la fin de session serveur
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : la déconnexion serveur reste journalisée par le proxy d'authentification (canal existant) ; l'échec de l'appel (401/5xx/réseau) peut être tracé côté client en technique, sans jeton ni donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — la purge locale systématique réduit le risque de persistance de jetons sur le poste

## Branches
- `client-blazor` (pushed) : fix/task-155-resilient-logout — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-155-resilient-logout
- `client-mobile` (pushed) : fix/task-155-resilient-logout — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-155-resilient-logout
- `dtos-mss` (pushed, auto-included) : fix/task-155-resilient-logout — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-155-resilient-logout (no DTO change expected — US frontend-only ; PR ouverte seulement si commits)
- `client-angular` : hors scope (déjà conforme, non listé par le PO — justification dans l'état des lieux)

## Develop log

- Repos touched : `client-blazor`, `client-mobile` (dtos-mss : aucun changement)
- DTOs published : no DTO change (US frontend-only)
- Interop published : no interop change
- Commits :
  - client-blazor : `4cb7a8a` fix(blazor): déconnexion résiliente — purge locale inconditionnelle sur 401/5xx/réseau
  - client-blazor : `ec938f0` chore(deps): pin Microsoft.OpenApi 2.7.5 pour corriger NU1903 (commit compagnon — voir note)
  - client-mobile : `380095b` test(mobile): non-régression déconnexion résiliente sur 401/5xx/réseau
  - client-mobile : `ddb7c7e` (pré-existant, WIP CIBA/Keycloak assumé par l'humain — hors task-155)
- Local build / test :
  - client-blazor : ✓ `dotnet build HealthPlatform.Client.sln` (0 erreur) · `dotnet test` (138 réussis, 2 skip pré-existants, 0 échec — dont 4 nouveaux `AuthServiceLogoutTests`)
  - client-mobile : ✓ `npm run build` (0 erreur) · `npm test … ChromeHeadless` (432 SUCCESS — +4 vs baseline 428)
- Implémentation :
  - **client-blazor (fix)** : `AuthService.LogoutAsync` purge l'authentification
    locale dans un `finally` → succès / 401 / 5xx / réseau passent tous par
    `ClearAuthentication()`. Avant, la purge n'avait lieu que sur le chemin
    succès (les `catch` ne faisaient que logger) → état connecté résiduel sur
    session expirée. La page `Logout.razor` redirige déjà vers `/` (forceLoad)
    → écran de connexion une fois l'auth purgée.
  - **client-blazor (tests)** : `AuthServiceLogoutTests` couvre les 4 cas
    (2xx/401/5xx/réseau) — purge appelée dans chaque branche, pas de rethrow.
    Ajout de la `ProjectReference` `HealthPlatform.Components.Shared` au projet
    de tests (l'`AuthService` y vivait sans être testé).
  - **client-mobile (tests seuls, déjà conforme)** : `$logout` avale déjà
    l'erreur (`catchError → of(undefined)`), le callback `complete` de l'appelant
    (inbox/settings) purge la session + redirige `/login`. Tests figés :
    service (`$logout` complète sur 401/5xx/réseau) + page Settings (purge +
    redirection `/login` une fois le logout complété).
- **Note — commit compagnon NU1903 (hors périmètre logout, validé humainement)** :
  le hook `verify-before-push` (build solution complète) échouait sur un avis
  de sécurité **pré-existant** — `Microsoft.AspNetCore.OpenApi` 10.0.3 tirait en
  transitif `Microsoft.OpenApi` 2.0.0 (GHSA-v5pm-xwqc-g5wc / CVE-2026-49451,
  NU1903), cassant `develop` comme toute branche Blazor. Décision humaine
  (2026-07-10) : commit compagnon sur cette branche → override direct vers
  `Microsoft.OpenApi` 2.7.5 (1re version patchée). Débloque le build/push.
- DOD self-check : build ✓ (les deux repos, solution complète Blazor incluse),
  tests ✓, 4 cas Blazor + purge par branche ✓, non-régression mobile 401/5xx/
  réseau + purge/redirect ✓, aucune donnée sensible ajoutée aux traces ✓,
  `data-testid` inchangés (aucun changement UI) ✓.
- Next step : /forge-simplify task-155

## Simplify log

- Repos passed : `client-blazor`, `client-mobile`
- Applied & committed : — (aucune simplification appliquée)
- No change :
  - `client-blazor` : la seule surface applicative (`AuthService.LogoutAsync`)
    est déjà un try/catch/finally minimal ; les deux `catch` portent une
    distinction d'altitude voulue (échec appel serveur vs inattendu) → pas de
    collapse. Tests déjà factorisés. Le reste du diff = pins de dépendances
    (mécaniques).
  - `client-mobile` : le diff de code (`auth.service.ts`) est le WIP CIBA de
    l'humain (commit `ddb7c7e`, assumé), hors intention task-155 → pas de passe
    cosmétique dessus. Le reste = specs (tests).
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ verts (inchangés depuis /develop — aucune édition)
- Next step : /lint-mobile task-155 (api-mail & client-angular non touchés → /sonar & /lint-angular skip)

## Lint mobile log

- Repo : `client-mobile` (fix/task-155-resilient-logout)
- Baseline `ng lint` : **All files pass linting** — 0 error, 0 warning, 0 fixable
- Iterations : aucune nécessaire (code frais = 2 specs, déjà conformes à
  `conventions/angular.md` : contrôle de flot natif non requis ici, pas de
  libellé, `data-testid` inchangés)
- Commit : aucun (rien à corriger)
- Best-effort : ✓ 0 error résiduelle
- Next step : /verify-visual task-155

## Visual verify log

- **Skip clean** — aucun écran `client-mobile` touché. Le diff mobile vs
  develop se limite à `auth.service.ts` (service, WIP CIBA humain — pas d'UI)
  et deux specs de test (`auth.service.spec.ts`, `settings.page.spec.ts`).
  Aucun template/SCSS/page modifié, aucun `## Stitch design log` sur cette task.
- Écrans capturés : 0 / 0
- Next step : /review task-155

## PRs

- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/63 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/46 — label `awaiting-human-merge`
- `dtos-mss` : aucun changement (US frontend-only) — pas de PR
- `client-angular` : hors scope (déjà conforme, non listé par le PO)

## Code Review Summary

- Verdict : **APPROVED** — 0 bloquant.
- Build ✓ (Blazor solution complète 0 erreur · Mobile 0 erreur) · Tests ✓
  (Blazor 138 réussis / 2 skip pré-existants · Mobile 432 SUCCESS) · `ng lint`
  All files pass · Vérification visuelle : skip clean (aucun écran touché).
- **Correctness** : `LogoutAsync` purge inconditionnelle via `finally` → les 4
  chemins (2xx/401/5xx/réseau) aboutissent à l'écran de connexion, plus d'état
  connecté résiduel. Mobile déjà conforme (`catchError` → `complete` purge +
  `/login`), figé par tests.
- **Security** : aucun jeton/cookie/donnée de santé ajouté aux traces. Bonus :
  correctif de la vuln transitive `Microsoft.OpenApi` 2.0.0 (NU1903, pin 2.7.5).
- **Architecture** : distinction d'altitude conservée entre les deux `catch` ;
  page `Logout.razor` inchangée.
- **Test coverage** : Blazor 4 cas (purge par branche) ; Mobile service (3 cas
  d'échec) + page (purge + redirect).
- DOD : tous les items vérifiables par commande ✓ ; ergonomie / bascule login
  déférée au test manuel humain (HAG).
- Qualité : /sonar skipped — api-mail non touché.
- Note : commit compagnon NU1903 (hors périmètre logout) validé humainement
  (2026-07-10) pour débloquer le build/push Blazor.

## Merged

- Merged (human-triggered `/merge --i-tested`) : 2026-07-10 17:35 +0200
- Squash-merged :
  - client-blazor : `2fca7b6` fix(blazor): déconnexion résiliente — purge locale sur 401/5xx/réseau (task-155) (#63) — PR #63 closed
  - client-mobile : `1de2932` test(mobile): non-régression déconnexion résiliente 401/5xx/réseau (task-155) (#46) — PR #46 closed (porte aussi le WIP CIBA `ddb7c7e` assumé)
- Remote branches deleted : `fix/task-155-resilient-logout` (blazor + mobile ; locals kept)
- Not applicable : dtos-mss (aucun changement), api-mail (non touché), client-angular (hors scope)
- develop CI :
  - client-blazor : ✓ green — https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/29103996553
  - client-mobile : run in-flight at archive time — https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/29104013676 (même commit passé green sur PR #46 pré-merge : build-android ✓)
- Note post-merge : le pin `Microsoft.OpenApi` 2.7.5 (NU1903) est désormais sur develop → le build Blazor de develop et des futures branches est débloqué.
