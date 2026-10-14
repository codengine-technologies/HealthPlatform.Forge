# todo-task-370.md — Les appels de weda2 à api-mail restent authentifiés tant que la session est ouverte

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). À coordonner avec task-365 (surveillance de la session partagée avec Weda), qui touche aux mêmes services d'authentification.
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — hors de Weda, la messagerie tombe en 401 « jeton expiré » environ 4 min après la connexion (constaté par l'humain le 2026-10-14, révélé en local par task-326).

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-06 ✔**, et la part d'**ANG-22** dont il dépend).
>
> **Périmètre réduit le 2026-10-14 (décision humaine)** : la task couvrait aussi ANG-07, ANG-23, ANG-24, ANG-66,
> ANG-67, ANG-69 et ANG-71. Ils passent dans **task-382**, avec le scénario E2E-AUTH-003. ANG-22 reste ici : le
> rafraîchissement préventif rafraîchit toutes les ~90 s ; sans ANG-22, une micro-coupure réseau pendant l'un de
> ces rafraîchissements renverrait le médecin à la connexion.

## Ce qui est établi

- **ANG-06** — `auth-interceptor.utils.ts:101-111` (`shouldSkipRequest`) laisse passer sans rafraîchissement toute URL qui ne vise ni `apiEndpoint` ni `authEndpoint`, donc **tous les appels à api-mail**. Aucun rafraîchissement préventif n'existe. Avec un jeton de 120 s et la tolérance d'api-mail de 2 min, les appels répondent 401 environ 4 min après la connexion ; le flux SSE (jeton en query string) meurt et n'est jamais rouvert ; `error.interceptor.ts:104-107` tait ces 401.
- **ANG-22** — `auth.interceptor.ts:122-139` : le `catchError` de perte de session est placé après le rejeu ; un 409 métier ou une coupure réseau pendant un rafraîchissement déconnecte le médecin et révoque la session du proxy (partagée avec Weda). `$refreshToken` appelle `login()` sur toute erreur.

## Objective

Que le médecin qui travaille dans weda2 hors de Weda ne voie plus ses appels à api-mail refusés pour jeton expiré, et
qu'un incident réseau pendant un rafraîchissement ne le déconnecte pas.

### Périmètre

1. **api-mail origine de confiance** de l'intercepteur d'authentification : rafraîchissement sur échéance et rejeu sur 401 pour `MSS_API_URL`, Bearer posé une seule fois.
2. **Rafraîchissement préventif** avant `exp` ; le flux SSE se rouvre avec le jeton neuf.
3. **Perte de session seulement sur refus explicite** du rafraîchissement (401, 400, `invalid_grant`) ; une erreur métier de la requête rejouée remonte telle quelle ; plus de `login()` dans `$refreshToken`.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires rouges d'abord :
  - [ ] une requête vers `MSS_API_URL` avec un jeton expiré déclenche un rafraîchissement puis part avec le jeton neuf ; un 401 d'api-mail est rejoué une fois
  - [ ] le jeton est rafraîchi avant `exp` sans requête déclenchante ; le flux SSE se rouvre avec le nouveau jeton
  - [ ] un 409 sur la requête rejouée remonte en 409, sans déconnexion ; un statut 0 pendant le rafraîchissement ne déconnecte pas ; un 400 `invalid_grant` déconnecte
- [ ] Scénario E2E-AUTH-001 « Rester connecté quand le jeton d'accès expire » : passé en `headless` si le banc le permet ; sinon la raison est consignée au catalogue
- [ ] Trou du filet : ligne dans `conventions/e2e.md` (le filet simule des jetons à échéance lointaine et ne pouvait pas voir ANG-06)
- [ ] Aucun jeton, `sub` ni adresse ajouté aux journaux

## Manual Test Plan

1. weda2 en onglet autonome, AppHost de dev (Keycloak local) : travailler 10 min dans la messagerie (ouvrir des mails, rédiger) → aucun « Session expirée », aucun 401 dans Seq ; un nouveau mail reçu apparaît en direct.
2. Couper le Wi-Fi 5 s pendant que le jeton est rafraîchi → pas de déconnexion.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de la session de la plateforme
- **Exigences DSR honorées** : non applicable — rétablit le socle PGSSI-S (verrouillage de session après inactivité)
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS (niveau eIDAS substantiel) inchangés ; la déconnexion pour inactivité du poste partagé redevient effective
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : déconnexion pour inactivité et perte de session journalisées côté client (cause seulement, sans jeton ni `sub`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — protège l'accès aux DSCP sur un poste partagé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-370-session-weda2 — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-370-session-weda2 (catalogue e2e `Api/Mail/e2e/scenarios.yml` uniquement)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au `/start` : `feature/nova-rewriting-mss-weda-integration`, **21 fichiers non commités de task-371 encore présents** — à commiter sur TFS séparément) — humain gère branche, commit, push, PR TFS
- Décision au `/start` : E2E-AUTH-003 `non-applicable` côté mobile — confirmé, l'application mobile n'a aucune déconnexion pour inactivité côté client (seul le délai de session IMAP serveur existe).

## Develop log

> **Reprise (2026-10-14)** — premier passage (`/forge 368 to 381`) annulé par l'humain (control plane `50723a1`).
> Relancée après le constat humain du 2026-10-14 16 h 51 : 401 `SecurityTokenExpiredException` sur
> `…/emails/content/…` en usage normal de weda2 hors Weda. Cause : ANG-06 (aucun rafraîchissement du jeton pour
> api-mail, depuis toujours), **révélé en local par task-326** (api-mail #291) qui valide désormais l'échéance des
> jetons en développement interactif — auparavant `devPermissive` (`ValidateLifetime = false`) acceptait un jeton
> périmé indéfiniment.
>
> Méthode : commit catalogue du premier passage réutilisé, weda2 refait **test d'abord** à partir du travail annulé
> (`915a9339`) : specs posés seuls, vus rouges, puis implémentation. **Puis périmètre réduit à ANG-06 (+ ANG-22)**
> sur décision humaine : ANG-07, 23, 24, 66, 67, 69, 71 retirés de l'arbre (fichiers revenus à l'identique de `HEAD`),
> E2E-AUTH-003 retiré du catalogue et de la suite → task-382.

### Commits (api-mail)

| Commit | Contenu |
|---|---|
| `020cf959` | catalogue : E2E-AUTH-003 + raison d'E2E-AUTH-001 humain (cherry-pick du premier passage, `23f7e076`) |
| `72c4ffb5` | E2E-AUTH-003 retiré (périmètre réduit) — reste la raison d'E2E-AUTH-001 |

### client-angular (weda2) — code-only, non commité

- **api-mail origine de confiance** (ANG-06) : `AuthConfig.trustedEndpoints` (`authConfigFactory`, URL d'api-mail) ;
  `shouldSkipRequest` les accepte ; l'intercepteur y pose le Bearer, rafraîchit un jeton échu avant l'appel et
  rejoue un 401 une fois ; `mssHeadersInterceptor` ne pose plus le Bearer (une seule fois).
- **Rafraîchissement avant échéance** : `TokenRefreshSchedulerService` (30 s avant `exp`, créneau partagé, nouvel
  essai à 15 s sur coupure), démarré par `provideEnvironmentInitializer` ; le flux SSE se rouvre avec le jeton neuf
  (comportement verrouillé par `mail-events-stream.service.spec.ts`).
- **Perte de session seulement sur refus** (ANG-22) : `refreshAndReplay` / `isSessionLossError` — 400/401/403 du
  rafraîchissement → déconnexion ; 0, 5xx → l'erreur remonte ; l'erreur de la requête rejouée remonte telle quelle ;
  `$refreshToken` n'appelle plus `login()`. Dépendances injectées dans le corps de l'intercepteur
  (`injectSessionRefreshDeps`) : le gestionnaire de 401 faisait `inject()` dans un callback RxJS, hors contexte
  d'injection dès qu'une vraie réponse HTTP arrive — sans cela, le rejeu d'api-mail échouerait en vrai.
- **Laissé dans l'arbre, hors périmètre** : `loginPsc()` pose un `state` CSRF (morceau d'ANG-23), avec son test. Son
  retrait a été refusé par le contrôle de sécurité de la session (affaiblissement) ; inoffensif et dormant tant que le
  bouton PSC n'est pas rebranché — task-382 le reprend.

### Preuves

| Preuve | Résultat |
|---|---|
| Specs seuls sur le code de HEAD (périmètre complet) | 25 rouges, dont « rafraîchit un jeton échu avant d'appeler api-mail », « rejoue une fois un 401 », 409 / statut 0 / refus |
| Mutation ANG-06 (api-mail retiré des origines de confiance) | `session-continuity.spec.ts` **6/6 rouges**, restauré |
| Après réduction | specs d'authentification 777/777 ; weda2 complet : voir Validation |

### Fichiers (client-angular, non commités sur `feature/nova-rewriting-mss-weda-integration`)

`apps/weda2/src/app/app.config.ts` (+spec), `app/core/interceptors/mss-headers.interceptor.ts` (+spec),
`lib/auth/index.ts`, `lib/auth/models/auth-config.model.ts`, `lib/auth/interceptors/auth.interceptor.ts` (+spec),
`lib/auth/interceptors/session-continuity.spec.ts` (nouveau), `lib/auth/interceptors/utils/auth-interceptor.utils.ts` (+spec),
`lib/auth/services/authentication-callback.service.ts` (+spec), `lib/auth/services/token-refresh-scheduler.service.ts` (+spec, nouveaux),
`libs/mss/src/core/services/mail-events-stream.service.spec.ts` (nouveau).
⚠️ L'arbre porte aussi les fichiers de task-371, non commités.

### Validation (périmètre réduit)

- weda2 : `npm run build` ✓ ; `npm test` ✓ — 11 projets (weda2 2 699, 14 ignorés préexistants ; libs/mss 861), aucune erreur non gérée.
- ESLint des fichiers gardés : 0 erreur (8 avertissements existants). e2e : `tsc` ✓ (E2E-AUTH-003 retiré).
- Journaux : aucun jeton, `sub` ni adresse ajouté (les échecs de rafraîchissement ne journalisent que le statut).

### DOD self-check

- Build et tests weda2 verts ✓ ; les 3 points rouges d'abord ✓ (`session-continuity`, `token-refresh-scheduler`, `mail-events-stream`)
- E2E-AUTH-001 : reste humain, raison consignée au catalogue ✓ ; trou du filet consigné ✓
- ⚠️ `/e2e` à rejouer : bloqué par E2E-ATTACH-001 (mobile, test mal écrit, hors task) — `questions/task-370.md`
- ⚠️ CI de la PR api-mail : rouge attendue au Restore (avis NuGet `System.Security.Cryptography.Pkcs`) — `questions/merge-task-371.md`

## Sonar log

- Skipped : api-mail ne porte que le catalogue e2e (`e2e/scenarios.yml`), aucun code C#.

## Lint log

- Mode A, base `origin/next`, `tag:scope:mss` : 0 erreur (warnings préexistants). La task touche surtout l'application `weda2`, hors de ce périmètre : lint ciblé sur ses fichiers TypeScript pendant `/develop` — 0 erreur, 16 avertissements existants. Aucune itération, aucun fichier modifié.

## Lint mobile log

- Skipped : client-mobile non touché par la task.

## Timings

*(généré par `tools/timing/report.sh --task task-370 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 58 s | 2 (34 s) | 2 (45 s) | — | client-angular 2B/2T, réduction à ANG-06 |
| /sonar | skipped | 0.5 s | — | — | — | catalogue e2e seulement |
| /lint-angular | ok | 15 s | 1 (13 s) | 1 (19 s) | — | client-angular 1B/1T |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | failed | 13 min 43 s | — | — | — | e2e ×6 (25 min 05 s), E2E-ATTACH-001 mobile rouge (sélecteur ambigu du test) |
| /review | ok | 2 min 24 s | — | 3 (1 min 00 s) | — | client-angular 0B/2T, api-mail 0B/1T |
| /tech-writer | ok | 25 s | — | — | — | — |
| **Total cycle** | | **18 min 08 s** | **3 (47 s)** | **6 (2 min 05 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (13 s)
