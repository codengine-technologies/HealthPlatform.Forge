# todo-task-275.md — Le mobile garde sa session tant que le refresh PSC vit : validation du modèle « token Keycloak jetable »

**Repos**: client-mobile
**Dependencies**: psc-auth-proxy/task-015 (refresh PSC-primaire par re-échange — autre forge, dépôt `D:\Workspaces\psc-auth-proxy`)
**Epic**: E012

## Objectif

Côté proxy (psc-auth-proxy/task-015), le refresh de session mobile change de
modèle : **le seul refresh token consommé est celui de PSC** ; le jeton Keycloak
n'est plus rafraîchi mais **re-frappé** à chaque `/auth/refresh` (re-échange JWT
Authorization Grant), porteur des claims `mssEmail`/`mssRpps` à jour. Il n'existe
plus ni session Keycloak ni refresh token Keycloak — l'agrégat rendu au mobile a
un champ `refreshToken` **vide**, et son `refreshTokenExpirationDateUtc` vaut
l'échéance du refresh token **PSC**.

L'analyse du code mobile (étude psc-auth-proxy
`questions/task-014-session-persistante.md` §7.6, 2026-08-29) conclut que
`client-mobile` est **déjà compatible** : le refresh est cookie-based sur
`authEndpoint` (`/auth/refresh`, single-flight dans `mss-headers.interceptor`),
l'échéance préventive est lue de l'`exp` du JWT lui-même, et le champ
`refreshToken` de l'agrégat n'est jamais lu (`AuthSession` ne le porte pas).

Cette US **verrouille** cette compatibilité au lieu de la supposer : tests qui
épinglent les invariants, et validation E2E du parcours complet sur le nouveau
modèle. Elle n'introduit **aucun changement de comportement**.

**Endpoints — aucune bascule.** Le refresh reste sur `authEndpoint`
(`/auth/refresh` du proxy Keycloak, :8081 en local) : c'est l'instance qui
détient les credentials Keycloak du re-échange (le déploiement PSC les exclut
volontairement — bordereau psc-auth-proxy). Fonctionnellement, ce refresh ne
consomme QUE le refresh token PSC ; le CIBA (`/auth/connect`, cookie BFF) reste
sur `cibaEndpoint` (:7129). Toute bascule du refresh vers `cibaEndpoint` est
**hors périmètre** et exigerait un arbitrage bordereau (credentials Keycloak sur
le déploiement PSC).

**Hors périmètre** : tout changement du proxy (porté par psc-auth-proxy/task-015) ;
toute modification des endpoints d'environnement ; tout nouveau traitement du code
d'erreur de re-échange (RG-3 côté proxy : l'échec de refresh conserve le
comportement actuel — purge locale + `/login?expired=1`).

## Definition of Done

- [ ] Build passes (`npm ci && npm run build`), tests pass
      (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Test unitaire : la construction d'`AuthSession` depuis un agrégat dont
      `refreshToken` est **vide** produit une session valide (accessToken,
      `mssEmail`, `accessTokenExpiresAt` lus normalement)
- [ ] Test unitaire : `refreshSession()` avec une réponse `/auth/refresh` au
      nouveau format (refreshToken vide, accessToken re-frappé avec un `exp`
      neuf) met à jour `accessTokenExpiresAt` ET `mssEmail` (claims re-dérivés)
- [ ] Test unitaire : l'intercepteur déclenche le refresh préventif sur
      l'échéance du jeton re-frappé (pas de dépendance à
      `refreshTokenExpirationDateUtc`)
- [ ] Test unitaire : un échec de `/auth/refresh` (ProblemDetails, code proxy
      de re-échange) suit le chemin existant purge + `/login?expired=1` —
      aucun traitement spécial du nouveau code
- [ ] Aucun changement dans `src/environments/*` ni dans les URL d'auth
- [ ] Aucune régression sur les specs existantes d'`auth.service` /
      `mss-headers.interceptor` / `auth-session.service`

## Manual Test Plan

Pré-requis : psc-auth-proxy sur la branche portant task-015 (les deux AppHost
lancés), api-mail lancé, app mobile `npm start` (http://localhost:8100).

1. Login e-CPS complet (RPPS de test, code d'appairage validé dans l'appli) →
   boîte de réception affichée (`mssEmail` résolu, pas d'onboarding).
2. Laisser l'app ouverte **> 5 minutes** (expiration de l'access token
   Keycloak), puis ouvrir un dossier et un mail avec pièce jointe :
   **attendu** — navigation fluide, aucun retour au login, la PJ s'ouvre
   (chemin IMAP complet re-validé après refresh).
3. Répéter l'attente et la navigation une seconde fois (2 refresh successifs =
   la rotation PSC est bien re-persistée par le proxy à chaque tour).
4. Dans Seq (seq-local) : événements de refresh PSC-primaire visibles, aucun
   jeton en clair.
5. Console Keycloak (realm weda-realm) : **aucune session** pour le client
   `weda` — comportement attendu du modèle (session transiente), ne pas
   instruire comme un défaut.
6. Mode dégradé : arrêter le conteneur Keycloak, attendre l'expiration du
   jeton, naviguer → retour `/login?expired=1` propre (pas d'écran blanc, pas
   de boucle) ; redémarrer Keycloak, re-login e-CPS → OK.

## Notes pour /develop

- Les invariants à épingler vivent dans `src/app/core/auth/`
  (`session.model.ts`, `auth.service.ts`, `auth-session.service.ts`) et
  `src/app/core/http/mss-headers.interceptor.ts`. **Aucun code de production ne
  devrait changer** — si un test révèle une dépendance réelle au refreshToken de
  l'agrégat ou à `refreshTokenExpirationDateUtc`, la corriger fait partie de
  l'US (et la consigner).
- Le champ `refreshToken` reste déclaré dans `TokenAggregate` (contrat de
  réponse proxy inchangé, RG-6 de task-015) — ne pas le supprimer du type.

## Branches

- `client-mobile` (pushed) : `feat/task-275-mobile-psc-horizon` —
  https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-275-mobile-psc-horizon

Pré-flight `/start` du 2026-08-30 : `api-mail`, `client-blazor`,
`client-mobile`, `dtos-mss`, `sdk`, `interop-cda` tous sur `develop`.
Dépendance `psc-auth-proxy/task-015` en état `done-*` (PR !9039 ouverte,
branche `feature/task-015-refresh-mobile-par-re-echange-psc` checkée dans
`D:\Workspaces\psc-auth-proxy`) — condition du plan de test manuel satisfaite.

Pas d'auto-inclusion de `dtos-mss` : ni `api-mail` ni `client-blazor` n'est
listé dans `**Repos**:`.

> ### ⚠️ Note du `/start` — le point 2 du plan de test manuel ne peut pas passer aujourd'hui
>
> Le plan de test manuel §2 (« laisser l'app ouverte > 5 minutes, puis ouvrir un
> dossier et un mail avec pièce jointe → navigation fluide, la PJ s'ouvre ») est
> **actuellement non passant**, pour une cause **extérieure à cette US** :
>
> L'auth IMAP/SMTP d'`api-mail` utilise le **jeton PSC** (`UserContextInfo.JwtToken`
> est un alias de `PscToken`), qui vit **~2 min**, alors que `client-mobile` ne
> déclenche son refresh préventif que sur l'`exp` du jeton **Keycloak** (5 min).
> Résultat mesuré le 2026-08-30 : ~3 min sur 5 avec un `X-PSC-Token` périmé, et
> un **HTTP 500 corps vide** à 16:21:03 sur `GET /api/v1/mail/folders/INBOX`
> (2 min 20 d'indisponibilité avant réparation accidentelle au refresh suivant).
>
> **C'est le périmètre de `todo-task-283`**, pas une régression introduite ici,
> et pas un élargissement de cette US. L'affirmation du corps de tâche selon
> laquelle le mobile est « déjà compatible » reste **vraie du côté Keycloak** —
> qui est bien ce que change `psc-auth-proxy/task-015`. Le DOD (tests unitaires
> + aucun changement d'environnement) reste intégralement atteignable.
>
> À l'arrivée au HAG : ne pas rejeter la PR sur l'échec du §2 tant que `283`
> n'est pas livrée ; le tester après, ou l'accepter comme connu.

## Simplify log

**Passe qualité `/forge-simplify` du 2026-08-30 — skip clean, aucun changement.**

| Repo | Éligible | Verdict |
|---|---|---|
| `client-mobile` | oui | **rien à simplifier** — diff 100 % test, conforme à l'idiome du fichier |
| tous les autres | non touchés | skip |

Diff examiné : 204 lignes réparties sur 3 fichiers de specs, aucun code de
production. Deux pistes envisagées puis **écartées, motif consigné** :

1. **Factoriser la configuration `TestBed`** du nouveau `describe` avec celle du
   `describe` « preventive refresh ». Écartée : `mss-headers.interceptor.spec.ts`
   porte **déjà 5 blocs `TestBed.configureTestingModule`** indépendants (un par
   `describe`, lignes 15 / 124 / 263 / 352 / 488). Extraire un constructeur
   commun pour le seul nouveau bloc serait *incohérent* avec le fichier ; le
   faire pour les cinq est un refactor de tout le fichier, hors périmètre d'une
   US dont le contrat est « aucun changement de comportement » — et il ferait
   porter un risque de régression à des tests qui, eux, ne changent pas.
2. **Réutiliser les helpers `validSession()` / `expiredSession()`** du
   `describe` voisin. Écartée : ils sont à valeurs figées et surtout adossés à
   un spy dont la propriété `session` est **immuable**. Or l'invariant à
   verrouiller est précisément que l'intercepteur **relit** une session
   différente après re-frappe — un stub mutable est nécessaire, pas cosmétique.

Réutilisation effective là où elle était pertinente : `session.model.spec.ts`
s'appuie sur le helper `tokens()` déjà présent dans le fichier, aucun second
constructeur d'agrégat introduit.

Aucun commit, aucun push : la passe n'a rien produit.

## Lint mobile log

**`/lint-mobile` du 2026-08-30 — baseline déjà propre, 0 itération.**

| Mesure | Valeur |
|---|---|
| Commande | `npm run lint` (`ng lint`, projet `app`) |
| Erreurs baseline | **0** |
| Warnings baseline | **0** |
| Itérations exécutées | **0** (arrêt immédiat : zéro erreur) |
| Fixes appliqués | aucun |
| Commit / push | aucun — rien à corriger |

Sortie : `Linting "app"… All files pass linting.`

Le diff de la task est exclusivement du code de test (3 fichiers `.spec.ts`,
204 lignes) écrit dans l'idiome des specs voisines ; l'auto-fixer n'avait rien
à reprendre. Build et suite de tests étaient déjà verts à l'issue de
`/develop` (780/780) et n'ont pas eu à être rejoués, aucune modification
n'ayant été produite par cette étape.

## Visual verify log

**`/verify-visual` du 2026-08-30 — skip clean, aucun écran concerné.**

| Condition de skip | Constat |
|---|---|
| `client-mobile` touché ? | oui, mais **test uniquement** |
| `## Stitch design log` présent ? | **non** — aucun écran n'a été conçu ni codé |
| Fichiers d'écran modifiés (`*.html`, `*.scss`, `*.component.ts`, `*.page.ts`) | **0** |

Diff intégral de la task : `auth.service.spec.ts`, `session.model.spec.ts`,
`mss-headers.interceptor.spec.ts`. Aucun composant, aucun gabarit, aucune
feuille de style. Il n'y a donc **rien à capturer** : ni Playwright lancé, ni
serveur `npm start` démarré, ni PNG produit ou commité.

L'état visuel global de l'application dans `Docs/epics/img/screens/client-mobile/`
est **inchangé** — cette US ne peut pas l'avoir altéré.

## PRs

- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/64
  — label `awaiting-human-merge`, base `develop`, head `feat/task-275-mobile-psc-horizon`
  (commit `4c9c663`).

Aucun autre repo : `**Repos**: client-mobile` seul, pas d'auto-inclusion
`dtos-mss` (ni `api-mail` ni `client-blazor` listés). `client-angular`,
`devops`, `psc-proxy-*` — hors périmètre, non touchés.

**Coordination avec l'autre forge** : la dépendance
`psc-auth-proxy/task-015` est elle aussi en PR ouverte (`!9039`, état `done-*`).
Cette PR-ci ne change aucun code de production : elle est **inoffensive à
merger dans n'importe quel ordre** vis-à-vis de task-015. Elle ne devient
*utile* qu'une fois task-015 déployée, mais elle ne casse rien avant.

## Code Review Summary

**Verdict : APPROVED** — 3 fichiers revus, 1 suggestion non bloquante, 0 blocage.

| Fichier | Verdict |
|---|---|
| `src/app/core/auth/session.model.spec.ts` | ✅ réutilise le helper `tokens()` existant ; échéance en constante figée → déterministe, pas de flaky temporel |
| `src/app/core/auth/auth.service.spec.ts` | ✅ idiome du fichier respecté ; vérifie session émise **et** persistée (c'est la persistée que relit l'intercepteur) |
| `src/app/core/http/mss-headers.interceptor.spec.ts` | ✅ stub de session mutable **nécessaire** (les spies voisins ont une propriété `session` figée qui masquerait l'invariant) — ⚠️ suggestion : le stub est un littéral non typé là où les `describe` voisins utilisent `jasmine.createSpyObj<AuthSessionService>` ; sans effet fonctionnel |

- **Correction** : les 6 tests portent des assertions réelles (en-tête
  `Authorization` effectif, nombre d'appels, identité de l'erreur propagée),
  aucun `expect(true)`.
- **Sécurité** : aucun secret, aucune donnée de santé — adresses et jetons
  entièrement fictifs.
- **Architecture** : aucun code de production modifié, conforme au contrat de
  l'US ; specs écrites dans l'idiome des `describe` voisins.
- **Couverture** : 780/780 verts (774 → 780), build vert.

### Validation

| Contrôle | Résultat |
|---|---|
| Build (`npm run build`) | ✓ |
| Tests (`npm test -- --watch=false --browsers=ChromeHeadless`) | ✓ 780 / 780 |
| DOD | ✓ 7/7 items (les 6 vérifiables par commande + « aucun changement d'environnement » — 0 fichier sous `src/environments/`) |
| Merge `origin/develop` | ✓ already up to date, aucun conflit |
