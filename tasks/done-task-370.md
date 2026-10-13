# todo-task-370.md — La session de weda2 reste valide tant que le médecin travaille, et se ferme vraiment quand il s'absente

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). À coordonner avec task-365 (surveillance de la session partagée avec Weda), qui touche aux mêmes services d'authentification.
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — hors de Weda, la messagerie tombe en « session expirée » environ 4 min après la connexion ; sur un poste de cabinet partagé, la session d'un médecin absent ne se ferme jamais.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-06 ✔, ANG-07 ✔, ANG-22, ANG-23, ANG-24, ANG-66, ANG-67, ANG-69, ANG-71**).

## Ce qui est établi

- **ANG-06** — `auth-interceptor.utils.ts:101-111` (`shouldSkipRequest`) laisse passer sans rafraîchissement toute URL qui ne vise ni `apiEndpoint` ni `authEndpoint`, donc **tous les appels à api-mail**. Aucun rafraîchissement préventif n'existe. Avec un jeton de 120 s et la tolérance d'api-mail de 2 min, les appels répondent 401 environ 4 min après la connexion ; le flux SSE (jeton en query string) meurt et n'est jamais rouvert ; `error.interceptor.ts:104-107` tait ces 401.
- **ANG-07** — `auto-logout.service.ts:207-240` : `initialize()` n'est appelé nulle part ; à l'échéance, `triggerLogout()` journalise « Auth store not initialized » et ne déconnecte pas. Le bouton « Se déconnecter » du dialogue ne fait rien. Un réveil de veille au-delà de la fenêtre n'ouvre aucun dialogue.
- **ANG-22** — `auth.interceptor.ts:122-139` : le `catchError` de perte de session est placé après le rejeu ; un 409 métier ou une coupure réseau pendant un rafraîchissement déconnecte le médecin et révoque la session du proxy (partagée avec Weda). `$refreshToken` appelle `login()` sur toute erreur.
- **ANG-23** — « Se connecter avec Pro Santé Connect » (écran « PSC requis ») navigue vers `/login`, une route qui n'existe pas ; `loginPsc()` n'est jamais appelé.
- **ANG-24 / ANG-66** — Aucun garde-fou contre une boucle callback ↔ proxy ; un retour d'erreur OAuth (annulation PSC) laisse un spinner infini.
- **ANG-67 / ANG-69 / ANG-71** — Créneau de rafraîchissement partagé libéré au désabonnement d'un appelant ; rechargement inutile au callback qui perd la page demandée ; repli sur `preferred_username` jamais appliqué (`??` après `join`).

## Objective

Que le médecin qui travaille ne soit **jamais** déconnecté par un défaut technique (jeton, coupure réseau, erreur métier), et que le médecin qui s'absente le soit **toujours** à l'échéance prévue, en mode autonome comme dans un onglet ouvert depuis Weda.

### Périmètre

1. **api-mail origine de confiance** de l'intercepteur d'authentification : rafraîchissement sur échéance et rejeu sur 401 pour `MSS_API_URL`, Bearer posé une seule fois.
2. **Rafraîchissement préventif** avant `exp` ; le flux SSE se rouvre avec le jeton neuf.
3. **Perte de session seulement sur refus explicite** du rafraîchissement (401, 400, `invalid_grant`) ; une erreur métier de la requête rejouée remonte telle quelle ; plus de `login()` dans `$refreshToken`.
4. **Déconnexion pour inactivité réelle** : le service reçoit le store ; `timeRemaining <= 0` (réveil de veille) déconnecte sans dialogue ; le bouton du dialogue déconnecte. Le mode embarqué reste régi par Weda (inchangé).
5. **« Se connecter avec Pro Santé Connect »** branché sur `loginPsc()`, avec `state` CSRF.
6. **Callback** : relances bornées puis écran d'erreur avec « Réessayer » ; `error` / `error_description` affichés ; pas de rechargement superflu.
7. Corrections mineures : `finalize` du créneau partagé avant `shareReplay` ; `||` pour le repli `preferred_username`.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires rouges d'abord :
  - [ ] une requête vers `MSS_API_URL` avec un jeton expiré déclenche un rafraîchissement puis part avec le jeton neuf ; un 401 d'api-mail est rejoué une fois
  - [ ] le jeton est rafraîchi avant `exp` sans requête déclenchante ; le flux SSE se rouvre avec le nouveau jeton
  - [ ] un 409 sur la requête rejouée remonte en 409, sans déconnexion ; un statut 0 pendant le rafraîchissement ne déconnecte pas ; un 400 `invalid_grant` déconnecte
  - [ ] à l'échéance d'inactivité, `logout()` du store est appelé ; au réveil après l'échéance, aussi ; le bouton du dialogue aussi
  - [ ] « Se connecter avec Pro Santé Connect » appelle `loginPsc()` avec un `state` stocké
  - [ ] au-delà de N relances du callback, l'écran d'erreur s'affiche ; un `?error=` affiche son message
  - [ ] l'annulation d'un abonné ne libère pas le créneau de rafraîchissement en vol
- [ ] Scénario E2E-AUTH-001 « Rester connecté quand le jeton d'accès expire » : passé du mode `humain` à `headless` si le banc le permet (jeton simulé à courte échéance), version montée, implémenté dans weda2 ; sinon la raison est consignée au catalogue
- [ ] Scénario E2E-AUTH-003 « Déconnexion après inactivité » ajouté au catalogue (angular `requis` en mode autonome ; mobile `non-applicable` — pas de déconnexion pour inactivité dans l'application mobile, à confirmer au `/start`)
- [ ] Trou du filet : ligne ajoutée dans `conventions/e2e.md` (le filet simule des jetons à échéance lointaine et ne pouvait pas voir ANG-06)
- [ ] Aucun jeton, `sub` ni adresse ajouté aux journaux

## Manual Test Plan

1. weda2 en onglet autonome, AppHost de dev (Keycloak local) : travailler 10 min dans la messagerie (ouvrir des mails, rédiger) → aucun « Session expirée » ; un nouveau mail reçu apparaît en direct.
2. Couper le Wi-Fi 5 s pendant que le jeton est rafraîchi → pas de déconnexion.
3. Rester inactif jusqu'au dialogue, ne rien faire → déconnexion et écran de connexion. Recommencer en cliquant « Se déconnecter ».
4. Mettre le poste en veille au-delà de la durée d'inactivité, le réveiller → déconnexion immédiate.
5. Compte sans boîte ni jeton PSC : écran « PSC requis », bouton « Se connecter avec Pro Santé Connect » → redirection PSC.
6. Annuler la connexion PSC → message d'erreur avec « Réessayer », pas de spinner infini.

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
- `client-angular` (code-only) : branche courante `feature/nova-rewriting-mss-weda-integration` (instantané au `/start`) — humain gère commit, push, PR TFS
- `api-mail` (pushed) : fix/task-370-session-weda2 — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-370-session-weda2 (catalogue e2e seulement)
- `dtos-mss` (paresseuse) : aucune branche

> **Constat au `/start`** : client-mobile n'a aucune déconnexion pour inactivité (`logout.service.ts` ne gère que la déconnexion volontaire) → E2E-AUTH-003 `non-applicable` côté mobile.

## Develop log

### Livré

**client-angular** (code-only, non commité) :

- **api-mail origine de confiance** (ANG-06) : `AuthConfig.trustedEndpoints` (`authConfigFactory`, URL d'api-mail) ; `authInterceptorFn` y pose le Bearer, rafraîchit un jeton échu avant l'appel et rejoue un 401 une fois. `mssHeadersInterceptor` ne pose plus le Bearer (une seule fois).
- **Rafraîchissement avant échéance** : `TokenRefreshSchedulerService` (30 s avant `exp`, créneau partagé, nouvel essai à 15 s sur coupure), démarré par `provideEnvironmentInitializer`. Le flux SSE se rouvre avec le jeton neuf (effet existant, désormais verrouillé par un test).
- **Perte de session seulement sur refus** (ANG-22) : `refreshAndReplay` examine l'échec du **rafraîchissement** seul — 400/401/403 → purge et `/logout` ; 0, 5xx → l'erreur remonte, session intacte ; l'erreur de la requête rejouée (409…) remonte telle quelle. `$refreshToken` et `$exchangeCodeForToken` n'appellent plus `login()`.
- **Défaut trouvé en lisant** : le gestionnaire de 401 faisait `inject()` dans un callback RxJS — hors contexte d'injection dès qu'une vraie réponse HTTP arrive (les tests, synchrones, le masquaient). Les dépendances sont désormais injectées dans le corps de l'intercepteur et passées (`injectSessionRefreshDeps`).
- **Inactivité** (ANG-07) : `AutoLogoutService` déconnecte par le store de l'application (résolu à l'usage) ; échéance atteinte ou dépassée au réveil → déconnexion sans dialogue ; bouton « Se déconnecter » effectif ; mode embarqué inchangé (régi par Weda).
- **PSC** (ANG-23) : `pscSignInFactory` → `loginPsc()`, qui pose désormais un `state` CSRF stocké.
- **Callback** (ANG-24, ANG-66, ANG-69) : `?error=` affiché avec « Réessayer » ; relances bornées à 2 (`sessionStorage`) puis écran d'erreur ; sans code → écran d'erreur ; page demandée mémorisée avant la pose du jeton, rejointe par `location.assign` si la pose recharge (changement d'identité).
- **Mineurs** : `finalize` avant `shareReplay` (ANG-67) ; `practitionerDisplayName` avec `||` (ANG-71).
- **e2e** : spec weda2 E2E-AUTH-003 (horloge Playwright, `page.clock`).

**api-mail** (`23f7e076`) : catalogue — E2E-AUTH-003 ajouté (angular `requis`, mobile `non-applicable` : constaté au `/start`) ; E2E-AUTH-001 reste `humain`, raison consignée (le banc authentifie api-mail par test-bypass, l'échéance du jeton n'y est pas examinée).

### Preuves (tests rouges d'abord)

| DOD | Test | Rouge |
|---|---|---|
| jeton échu → rafraîchi puis jeton neuf vers api-mail ; 401 rejoué une fois | `session-continuity.spec.ts` | 6/6 rouges avant correctif |
| 409 rejoué remonte sans déconnexion ; statut 0 ne déconnecte pas ; 400 `invalid_grant` déconnecte | `session-continuity.spec.ts` | idem |
| rafraîchi avant `exp` sans requête | `token-refresh-scheduler.service.spec.ts` | mutation (planification neutralisée) → 3 rouges |
| flux SSE rouvert avec le jeton neuf | `mail-events-stream.service.spec.ts` | comportement existant, verrouillé |
| inactivité : échéance, réveil, bouton | `auto-logout.service.spec.ts` | 4 rouges |
| PSC : `loginPsc()` avec `state` stocké | `authentication-callback.service.spec.ts`, `app.config.spec.ts` | rouge ; mutation (`state` non stocké) → rouge |
| callback : > 2 relances → écran d'erreur ; `?error=` affiché | `authentication-callback.component.spec.ts` | 6 rouges |
| abonné annulé ne libère pas le créneau | `refresh-token-shared.service.spec.ts` | rouge |
| api-mail origine de confiance ; repli `preferred_username` | `app.config.spec.ts` | rouges (fonctions absentes) |

Deux tests existants décrivaient l'ancienne règle (toute erreur de rafraîchissement déconnecte) : réécrits sur un refus 401, même intention.

### Validation

- `vitest` weda2 : 2 723 verts ; `tsc` (app) : propre hors deux erreurs existantes de `antecedents` (TS4023/TS4029, hors task).
- Suites e2e compilées (`tsc`), eslint 0 erreur sur le spec.
- Journaux : aucun jeton, `sub` ni adresse ajouté (les erreurs de rafraîchissement ne journalisent plus que le statut).

### Fichiers modifiés (client-angular, cette task)

`front/apps/weda2/src/app/app.config.ts`, `app.config.spec.ts`, `app/core/interceptors/mss-headers.interceptor.ts`, `.spec.ts`,
`app/features/authentication/authentication-callback.component.{ts,html,scss,spec.ts}`,
`lib/auth/index.ts`, `lib/auth/models/auth-config.model.ts`, `lib/auth/interceptors/auth.interceptor.ts`, `auth.interceptor.spec.ts`,
`lib/auth/interceptors/session-continuity.spec.ts` (nouveau), `lib/auth/interceptors/utils/auth-interceptor.utils.ts`, `.spec.ts`,
`lib/auth/services/authentication-callback.service.ts`, `.spec.ts`, `lib/auth/services/auto-logout.service.ts`, `.spec.ts`,
`lib/auth/services/refresh-token-shared.service.ts`, `.spec.ts`, `lib/auth/services/token-refresh-scheduler.service.ts` (nouveau), `.spec.ts` (nouveau),
`lib/auth/services/utils/authentication-callback.utils.ts`, `lib/auth/store/authentication-store.ts`,
`front/libs/mss/src/core/services/mail-events-stream.service.spec.ts` (nouveau), `front/e2e/mss-e2e/specs/functional.e2e.ts`.

## Sonar log

- skipped — api-mail ne porte que le catalogue e2e (`e2e/scenarios.yml`), hors analyse Sonar ; aucun code C# modifié. KPIs inchangés (Quality Gate OK au dernier passage, task-368).

## Lint log

- Mode A, lint ciblé sur les 25 fichiers de la task (application `weda2` hors portée `tag:scope:mss`, plus un spec `mss`).
- Base : 10 erreurs (6 `prettier/prettier`, 4 `jsdoc/require-param` / `require-jsdoc`), toutes dans le code de la task. JSDoc écrite à la main, prettier par `--fix`. Final : **0 erreur**, 12 avertissements `jsdoc/require-example` existants.
- Tests weda2 : 2 723 verts après correction ; spec `mail-events-stream` vert. Build weda2 (`npm run build`) : vert.

## Lint mobile log

- skipped — no mobile change : `client-mobile` absent des `**Repos**`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché (catalogue) | ✅ verte | 35 verts, 0 flaky, 0 rouge | ~6 min |
| angular | api-mail, client-angular touchés | ✅ verte | 40 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, humain) | ~6 min 30 s |

- **Banc** : api-mail sur une branche locale non poussée `e2e-bench-task-370` = staging du run (task-368) + `fix/task-370-session-weda2` (l'arbre weda2 porte aussi task-368, dont E2E-SECURITY-001) ; client-mobile sur la staging. Branche de banc supprimée, repos remis sur leur branche ensuite. Écart assumé à la règle « aucun checkout ».
- Catalogue : celui du banc (E2E-AUTH-003 ajouté).
- **Preuve rouge d'E2E-AUTH-003** : mutation — l'effet de déconnexion à l'échéance d'`AutoLogoutService` neutralisé → rouge sur « la déconnexion part vers le service de connexion » (aucun `DELETE /auth/logout` après 11 min d'horloge simulée). Fichier restauré depuis la copie.
- Parcours touchés sans spec e2e modifié : l'écran de callback (erreur, « Réessayer ») n'a pas de scénario e2e — le faux proxy du banc ne sait pas rendre `?error=` ; couvert par `authentication-callback.component.spec.ts`.
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-003 | 1 | headless | Être déconnecté après une période d'inactivité | ✅ | — |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/294 (label awaiting-human-merge) — catalogue e2e seulement (E2E-AUTH-003, raison d'E2E-AUTH-001).
- client-angular : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-rewriting-mss-weda-integration`. Fichiers de cette task : liste du `## Develop log` (25 fichiers, dont 4 nouveaux).

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 4 suggestions. Validation : weda2 `npm run build` ✓, `npm test` ✓ (11 projets, sans erreur non gérée) ; api-mail : tests du catalogue e2e ✓ (101).

- **Retour en `/develop` pendant la revue** : `npm test` signalait une erreur non gérée (tests tous verts) — le double de `AuthenticationCallbackService` d'un spec existant n'avait pas `login()`, que le callback appelle désormais sur un échange raté. Double complété ; leçon `double-incomplet-erreur-non-geree` (conventions/angular.md).
- **Règle 1b** : non applicable — aucun comportement servi par un endpoint (api-mail : catalogue seulement).
- `auth-interceptor.utils.ts` / `auth.interceptor.ts` ✅ — refus explicite seul déclencheur de perte de session ; dépendances injectées dans le contexte d'injection (corrige aussi un `inject()` qui aurait levé NG0203 sur une vraie réponse 401).
- `token-refresh-scheduler.service.ts` ✅ — un minuteur, replanifié à chaque publication du store ; pas de boucle (un rafraîchissement raté sans refus est retenté à 15 s).
- `auto-logout.service.ts` ✅ — garde `logoutInProgress` contre les déclenchements multiples ; ne s'arme qu'avec une session ; mode embarqué exclu.
- `authentication-callback.*` ✅ — messages affichés en texte (interpolation) : aucune injection depuis `error_description`.
- `app.config.ts` ✅ — `trustedEndpoints` dérivé de `mssApiUrl` ; `mssHeadersInterceptor` ne pose plus le Bearer.

### Suggestions (non bloquantes)

1. ⚠️ `error_description` vient de l'URL : affiché tel quel (échappé par Angular). Un message générique côté weda2, avec le code d'erreur seul, serait plus prudent contre un lien piégé « faites ceci ».
2. ⚠️ Le rafraîchissement préventif tourne aussi en mode embarqué (session du proxy partagée avec Weda) : comportement attendu, à confirmer au plan de test embarqué.
3. ⚠️ E2E-AUTH-001 reste humain : le 401 d'un jeton échu à api-mail n'est prouvé que par les tests unitaires. Un banc qui valide l'échéance (Keycloak de test) le rendrait jouable.
4. ⚠️ Coordination avec task-365 (surveillance de session partagée avec Weda) : mêmes services d'authentification.

## Timings

*(généré par `tools/timing/report.sh --task task-370 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 22 s | — | — | — | — |
| /develop | ok | 17 min 18 s | — | — | — | — |
| /sonar | skipped | 0.5 s | — | — | — | catalogue e2e seulement |
| /lint-angular | ok | 1 min 16 s | 1 (13 s) | 1 (19 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 14 min 05 s | — | — | — | e2e ×3 (12 min 03 s) |
| /review | ok | 2 min 24 s | — | 3 (1 min 00 s) | — | client-angular 0B/2T, api-mail 0B/1T |
| **Total cycle** | | **35 min 27 s** | **1 (13 s)** | **4 (1 min 20 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×1 (4.4 s)
