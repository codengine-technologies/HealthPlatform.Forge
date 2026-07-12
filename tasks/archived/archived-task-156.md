# todo-task-156.md — Session expirée : tout 401 irrécupérable bascule sur l'écran de connexion

**Repos**: client-blazor, client-angular, client-mobile
**Dependencies**: —

## Objective

Généraliser la règle de task-155 (déconnexion) à **tous les appels** : quand la
session du proxy d'authentification est expirée (cookie `proxy-session-id`
disparu), **n'importe quel** appel API répond 401. Le comportement attendu,
identique sur les trois clients :

1. **Une seule tentative de rétablissement silencieuse** : sur 401, tenter un
   refresh de session/jeton (mutualisé entre requêtes concurrentes,
   anti-boucle : jamais plus d'un refresh par requête rejouée) ;
2. **Si le refresh réussit** → rejouer la requête initiale, le praticien ne
   voit rien ;
3. **Si le refresh échoue** (session BFF réellement perdue) → **purge de la
   session locale + bascule immédiate sur l'écran de connexion**, avec un
   message sobre (« Votre session a expiré, veuillez vous reconnecter ») ;
   jamais de boucle de refresh, jamais d'avalanche de notifications d'erreur,
   jamais d'écran figé avec des données inaccessibles.

### État des lieux (audit 2026-07-06)

- **client-mobile — ✅ conforme (référence)** : l'intercepteur HTTP MSS fait
  exactement ce cycle (refresh unique mutualisé, rejeu, échec → purge +
  `/login?expired=1`). Aucun changement attendu — compléter si besoin les
  tests de non-régression du chemin « refresh échoué → bascule login ».
- **client-angular — 🟡 à corriger** : l'intercepteur d'authentification tente
  le refresh et rejoue, mais **le chemin « refresh échoué » se contente de
  re-propager l'erreur 401** — aucune purge, aucune bascule vers l'écran de
  connexion. Compléter ce chemin : purge du state d'authentification +
  redirection connexion (réutiliser la mécanique de déconnexion existante).
  Périmètre : couche d'authentification du host (hors module MSS) — le lint
  forge reste scopé MSS, prévoir `**LintProjects**:` si nécessaire.
- **client-blazor — 🟡 à corriger** : sur 401 API, le client force un refresh
  du jeton PSC et rejoue ; mais quand la **session BFF** est expirée, le
  refresh échoue et l'échec se termine en notification d'erreur générique,
  répétée à chaque appel. Attendu : après échec du refresh, purge de
  l'authentification locale + bascule sur l'écran de connexion (message
  sobre), en réutilisant le flux corrigé par task-155. Cas particulier
  conservé : un 401 d'origine IMAP/SMTP (mot de passe messagerie invalide)
  n'est PAS une expiration de session — il garde sa notification dédiée
  actuelle et ne déclenche pas la bascule.

## Definition of Done

- [ ] Build passe sur les trois repos (0 erreur) ; tests 0 échec
- [ ] `client-blazor` : session BFF expirée + appel API → une tentative de refresh, puis purge locale + bascule écran de connexion avec message sobre ; pas de notifications répétées
- [ ] `client-blazor` : 401 IMAP/SMTP (credentials messagerie) → comportement actuel conservé (notification dédiée, pas de bascule)
- [ ] `client-blazor` : tests unitaires des 3 chemins (refresh OK + rejeu ; refresh KO → bascule ; 401 IMAP/SMTP → notification)
- [ ] `client-angular` : refresh échoué sur 401 → purge du state + redirection connexion ; test unitaire de ce chemin ; refresh OK + rejeu inchangé (test existant vert)
- [ ] `client-mobile` : tests de non-régression présents ou complétés (401 → refresh → rejeu ; refresh KO → purge + `/login?expired=1`) — aucun changement de comportement
- [ ] Anti-boucle vérifié par test sur chaque client corrigé (une requête n'est rejouée qu'une fois ; un seul refresh pour N requêtes concurrentes)
- [ ] Aucun jeton, cookie ou donnée de santé dans les traces ajoutées
- [ ] Libellés : Blazor via Localizer ; Angular FR en dur (convention MSS/host respectée selon la couche touchée)

## Manual Test Plan

- Pré-requis : être connecté sur le client testé, puis **supprimer le cookie
  `proxy-session-id`** (outils développeur → Application → Cookies) pour
  simuler l'expiration de session.
- **Blazor** (`cd Client/Blazor && dotnet run`) : naviguer / rafraîchir la
  boîte de réception → au premier appel API, bascule sur l'écran de connexion
  avec « Votre session a expiré… » ; pas de rafale de toasts d'erreur ; la
  reconnexion fonctionne.
- **Angular** (`cd Client/Angular/front && npm start`) : même scénario → même
  résultat.
- **Mobile** (`cd Client/Mobile && npm start`) : même scénario → arrivée sur
  `/login` avec l'indication de session expirée (comportement existant,
  vérification de non-régression).
- **Blazor, cas conservé** : configurer un mot de passe IMAP invalide →
  l'erreur messagerie dédiée s'affiche, PAS de bascule sur l'écran de
  connexion.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — robustesse d'un mécanisme d'authentification existant
- **Exigences DSR honorées** : non applicable — hygiène de session (continuité d'usage sans compromis de sécurité)
- **INS** : non applicable
- **Authentification PS** : cœur de la US — cycle de vie de session e-CPS/PSC fiable de bout en bout ; l'expiration force une ré-authentification explicite, jamais un état intermédiaire ambigu
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refresh et échecs de refresh tracés côté proxy (canal existant) ; côté client, trace technique sans jeton ni donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — la purge systématique sur session perdue réduit le risque de jetons résiduels

## Branches
- `client-blazor` (pushed) : fix/task-156-expired-session-relogin — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-156-expired-session-relogin
- `client-mobile` (pushed) : fix/task-156-expired-session-relogin — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-156-expired-session-relogin
- `dtos-mss` (pushed, auto-included) : fix/task-156-expired-session-relogin — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-156-expired-session-relogin (no DTO change attendu — US frontend-only ; PR ouverte seulement si commits)
- `client-angular` (code-only) : forge écrit le code sur la branche actuellement checkout dans `Client/Angular/` — humain gère branche, commit, push, PR TFS. Périmètre : couche auth du host (hors MSS) → prévoir `**LintProjects**:` au lint si besoin.

## Develop log

- Repos touched : `client-blazor` (commit/push), `client-angular` (code-only, uncommitted). `client-mobile` : aucun changement (déjà conforme, tests présents). `dtos-mss` : aucun changement.
- DTOs published : no DTO change (US frontend-only)
- Interop published : no interop change
- Commits :
  - client-blazor : `4bba32c` fix(blazor): 401 irrécupérable → purge locale + bascule écran de connexion
- Local build / test :
  - client-blazor : ✓ `dotnet build HealthPlatform.Client.sln` (0 erreur) · `dotnet test` (142 réussis, 2 skip pré-existants, 0 échec — dont 4 nouveaux `HttpRequestServiceUnauthorizedTests`)
  - client-angular : ✓ `nx test weda2` (2575 réussis, 0 échec) · `nx build weda2` (succès ; warnings NG8107 pré-existants hors périmètre, `libs/mss`)
  - client-mobile : n/a (aucun changement) — suite existante verte au dernier run (432)
- Implémentation :
  - **client-mobile (référence, ✅ inchangé)** : `MssHeadersInterceptor` fait déjà
    le cycle complet (refresh unique mutualisé, rejeu, échec → `authSession.logout()`
    + `/login?expired=1`). Le spec `mss-headers.interceptor.spec.ts` couvre déjà :
    refresh→rejeu, refresh KO→purge+redirect, un seul refresh pour N concurrents,
    pas de boucle sur rejeu ré-expiré. **Rien à ajouter.**
  - **client-blazor (🟡→✅)** : nouveau `ISessionExpirationHandler` (Domain) +
    `SessionExpirationHandler` (Plugin : purge via `IAuthService.ClearAuthentication`
    + `UserSessionService.Clear` [flux task-155], message sobre unique, `NavigateTo("/")`
    → `Index.razor` rend le login ; garde `_handled` anti-avalanche). `HttpRequestService.
    HandleUnauthorizedAndRetryAsync` : IMAP/SMTP → notif dédiée ; toute autre 401 →
    un refresh (mutualisé par le SemaphoreSlim de `PscTokenRefreshService`), rejeu si OK,
    sinon `HandleExpiredSession()`. `NotifyErrorFromResponseAsync` ne notifie plus sur 401
    (fin de l'avalanche de toasts). Enregistré `AddScoped` (Plugin).
  - **client-angular (🟡→✅, code-only)** : `auth.interceptor.ts` (chemin token expiré)
    et `auth-interceptor.utils.ts` (`handleUnauthorizedErrorWithRefresh`) : les deux
    sites d'échec de refresh (erreur OU sans jeton) sont canalisés dans leur `catchError`
    → nouveau helper `redirectToLoginOnSessionLoss(store, router)` = `store.logout()` +
    `router.navigate(['/logout'])` (réutilise la mécanique de `installAutoLogoutEffect`).
    Anti-boucle inchangé : rejeu via `next` (pas de ré-entrée intercepteur), refresh
    mutualisé par `SharedRefreshTokenService`.
- Fichiers Angular modifiés (uncommitted sur `feature/nova-rewriting-mss` — humain commit/push TFS) :
  - `front/apps/weda2/src/lib/auth/interceptors/auth.interceptor.ts`
  - `front/apps/weda2/src/lib/auth/interceptors/utils/auth-interceptor.utils.ts`
  - `front/apps/weda2/src/lib/auth/interceptors/auth.interceptor.spec.ts`
  - `front/apps/weda2/src/lib/auth/interceptors/utils/auth-interceptor.utils.spec.ts`
  - (WIP humain pré-existant laissé intact : `apps/mss` + `apps/weda2` `environment.ts`)
- Note scope lint : le changement Angular est dans la **couche auth du host**
  (`apps/weda2/src/lib/auth`), **hors périmètre MSS** — `/lint-angular` (scopé
  `scope:mss`) ne le couvrira pas. Validé ici par `nx test weda2` + `nx build weda2`.
- Anti-boucle (DOD) : Blazor — rejeu unique testé + mutualisation refresh au niveau
  `PscTokenRefreshService` (SemaphoreSlim) ; Angular — refresh mutualisé
  (`SharedRefreshTokenService`) + rejeu via `next` sans ré-entrée ; Mobile — testé
  (single refresh N concurrents, pas de boucle).
- DOD self-check : builds ✓ (blazor sln + weda2), tests ✓ (blazor 142, angular 2575,
  mobile 432), 3 chemins blazor testés, chemin refresh-KO angular testé + nominal
  inchangé, mobile non-régression présente, aucune donnée sensible ajoutée aux traces,
  libellés (Blazor message sobre en dur côté handler ; Angular FR — aucun libellé neuf).
- Next step : /forge-simplify task-156

## Simplify log

- Repos passed : `client-blazor`, `client-angular`
- Applied & committed : — (aucune simplification appliquée)
- No change :
  - `client-blazor` : `SessionExpirationHandler` réutilise déjà les briques
    existantes (`ClearAuthentication` + `UserSessionService.Clear` +
    `IErrorNotificationService`) ; `HandleUnauthorizedAndRetryAsync` a été
    resserré (une seule branche refresh) ; tests factorisés (helpers). RAS.
  - `client-angular` : les deux sites d'échec de refresh partagent déjà le
    helper `redirectToLoginOnSessionLoss` (axe reuse/DRY appliqué d'emblée). RAS.
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ verts (inchangés depuis /develop — aucune édition)
- Next step : /lint-angular task-156 (api-mail non touché → /sonar skip ; client-angular touché)

## Lint log

- Repo : `client-angular` (code-only, branche `feature/nova-rewriting-mss`)
- Scope forge `/lint-angular` = **MSS** (`tag:scope:mss` = apps/mss + libs/mss).
  Le changement task-156 est dans la **couche auth du host**
  (`apps/weda2/src/lib/auth/interceptors`) → **hors périmètre MSS** : le pass
  scopé MSS n'a rien à corriger (aucun fichier MSS modifié).
- Hygiène : ESLint direct sur les 4 fichiers weda2 modifiés → **0 error**
  (les specs sont exclues par la config lint du repo — warnings « ignored », non
  bloquants). Les fichiers de prod (`auth.interceptor.ts`,
  `auth-interceptor.utils.ts`) passent proprement.
- Iterations : aucune (rien à corriger). Code-only : aucun git.
- Validation `/develop` déjà faite : `nx test weda2` (2575 ✓) + `nx build weda2` (✓).
- Next step : /lint-mobile task-156 (client-mobile non touché → skip → /verify-visual → /review)

## Lint mobile log

- **Skip clean** — `client-mobile` non touché par task-156 (aucun diff vs develop,
  arbre propre). L'app mobile était déjà conforme (intercepteur de référence), aucun
  code ni test à modifier.
- Next step : /verify-visual task-156

## Visual verify log

- **Skip clean** — aucun écran `client-mobile` touché (repo non modifié). Rien à capturer.
- Écrans capturés : 0 / 0
- Next step : /review task-156

## PRs

- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/64 — label `awaiting-human-merge`
- `client-angular` : **code-only** — humain gère commit/push TFS et ouverture PR. Fichiers modifiés (uncommitted sur `feature/nova-rewriting-mss`) :
  - `front/apps/weda2/src/lib/auth/interceptors/auth.interceptor.ts`
  - `front/apps/weda2/src/lib/auth/interceptors/utils/auth-interceptor.utils.ts`
  - `front/apps/weda2/src/lib/auth/interceptors/auth.interceptor.spec.ts`
  - `front/apps/weda2/src/lib/auth/interceptors/utils/auth-interceptor.utils.spec.ts`
- `client-mobile` : aucun changement (déjà conforme) — pas de PR
- `dtos-mss` : aucun changement — pas de PR

## Code Review Summary

- Verdict : **APPROVED** — 0 bloquant.
- Build ✓ (Blazor sln 0 erreur · weda2 build ✓) · Tests ✓ (Blazor 142 réussis / 2 skip
  pré-existants · Angular weda2 2575 réussis · Mobile suite existante 432) ·
  `/lint-angular` : hors scope MSS (changement host) ; ESLint direct des 4 fichiers = 0 error.
- **Correctness** : Blazor — IMAP/SMTP isolé ; toute autre 401 → un refresh → rejeu
  ou bascule ; plus de double-notification. Angular — les deux sites d'échec de refresh
  canalisés dans `catchError` → purge + `/logout` ; chemin nominal inchangé (testé).
  Mobile — inchangé (référence).
- **Anti-boucle** : refresh mutualisé (Blazor `PscTokenRefreshService` SemaphoreSlim ·
  Angular `SharedRefreshTokenService`), rejeu via `next`/single-retry (pas de ré-entrée),
  garde `_handled` (Blazor, une bascule pour N 401).
- **Security** : aucun jeton/cookie/donnée de santé ajouté aux traces.
- **Test coverage** : Blazor 4 chemins ; Angular refresh-KO (erreur + sans jeton) +
  nominal inchangé ; Mobile non-régression existante.
- **Déviation consciente (non bloquante, arbitrage HAG)** : message Blazor en FR en dur
  (via `IErrorNotificationService`, dont toute l'impl est hardcodée) plutôt que Localizer
  — cohérence du sous-système de notifications ; cf. [[project_angular_mss_no_ngx_translate]].
- Qualité : /sonar skipped — api-mail non touché.
- US-complete (règle 11) : US mono-wave, tous les volets prêts simultanément (Blazor PR
  + Angular code-only). L'humain teste blazor+angular+mobile de bout en bout puis merge
  la PR GitHub #64 **et** la PR TFS Angular ensemble.

## Merged

- Merged (human-triggered `/merge --i-tested`) : 2026-07-10 18:48 +0200
- Squash-merged :
  - client-blazor : `00195cc` fix(blazor): 401 irrécupérable → purge locale + bascule écran de connexion (task-156) (#64) — PR #64 closed
- Remote branch deleted : `fix/task-156-expired-session-relogin` (blazor ; local kept)
- Empty branches cleaned : `client-mobile` + `dtos-mss` `fix/task-156-...` (0 commit, no PR) — remote+local supprimées, repos remis sur develop
- Code-only (humain gère TFS) : `client-angular` — les 4 fichiers `apps/weda2/src/lib/auth/interceptors/**` restent **uncommitted** sur `feature/nova-rewriting-mss` ; à commit/push/PR/merger côté TFS par l'humain (pas d'action forge). Non basculé sur develop (branche de rewrite humaine, WIP CIBA + task-156 dessus).
- Not applicable : api-mail (non touché), client-mobile & dtos-mss (aucun changement)
- develop CI (client-blazor) : run in-flight at archive time — https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/29108629454 (même commit passé green sur PR #64 pré-merge : build ✓)
