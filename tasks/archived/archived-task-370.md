# todo-task-370.md — Les appels de weda2 à api-mail restent authentifiés tant que la session est ouverte

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement), client-mobile (correctif du test e2e E2E-ATTACH-001 seulement — décision humaine du 2026-10-14)
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
- `client-mobile` (pushed) : fix/task-370-session-weda2 — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-370-session-weda2 (ajouté le 2026-10-14 : correctif du sélecteur d'E2E-ATTACH-001, qui bloquait `/e2e`)
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

### Ajouts du 2026-10-14 (soir) — débloquer `/e2e`

- **client-mobile** (`fix/task-370-session-weda2`) : `a6166a4` — E2E-ATTACH-001, `.first()` sur l'union du `or`
  (la pièce et « Tout télécharger (ZIP) » visibles ensemble → strict mode violation, rouge au `/e2e` sur `develop`) ;
  `1ca0417` — merge de `develop` (task-374, test mobile d'E2E-MAILBOX-001). Build ✓, tests 1 101/1 101, e2e `tsc` ✓.
- **client-angular** — `mail-detail.loadContent` ne referme plus le menu « Plus d'actions » ni l'aperçu de pièce jointe
  sur un enrichissement temps réel du **même** mail (E2E-COMPOSE-001 rouge, puis flaky : le mail tout juste reçu est
  enrichi juste après son ouverture). Test `mail-detail.stale-content.spec.ts` rouge d'abord (`expected false to be
  true`), vert après ; un autre mail les referme toujours. weda2 : build ✓, 11 projets verts (libs/mss 884).
- `Client/Angular` : `git pull` de « Task 374 » (`c00f1a57`) intégré à la demande de l'humain, changements locaux
  réappliqués (conflits d'imports résolus, spec SSE fusionnée : 3 tests de task-374 + celui de task-370).

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

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | client-mobile et api-mail touchés | ✅ verte | 37 verts, 0 flaky, 0 rouge | ~6 min |
| angular | client-angular et api-mail touchés | ✅ verte | 41 verts, 0 flaky, 0 rouge, 1 quarantaine (passée) | ~6 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ fix/task-370-session-weda2 (après merge de `develop` : task-374, task-383)
- Historique : 1er passage rouge (E2E-ATTACH-001 mobile, sélecteur ambigu) ; 2e en échec d'outillage (Restore bloqué par l'avis Pkcs, corrigé par task-383) ; E2E-COMPOSE-001 corrigé (menu refermé par l'enrichissement temps réel).
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

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
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
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
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/299 — label `awaiting-human-merge` (catalogue)
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/96 — label `awaiting-human-merge` (test E2E-ATTACH-001)
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-rewriting-mss-weda-integration`. L'arbre porte les fichiers de task-371 **et** de task-370 (dont le correctif du menu) :


## Code Review Summary

**APPROVED** — 0 bloquant, 1 suggestion (`state` CSRF de `loginPsc()` dormant jusqu'à task-382).

- Règle 1b : aucun comportement d'endpoint api-mail modifié (4 lignes de catalogue).
- Double verrou e2e : `## E2E log` vert (mobile 37/37, angular 41/41, parité verte, 0 flaky).
- Validation `/review` : api-mail build ✓, tests ✓ (1 rouge d'intégration au 1er passage, `SemanticSearchRepositoryIntegrationTests…WithTagFolder` — base partagée polluée, vert au rejeu 887/887, consigné dans `conventions/csharp.md`) ; mobile build ✓, 1 101/1 101 ; weda2 build ✓, 11 projets verts.

## Timings

*(généré par `tools/timing/report.sh --task task-370 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 58 s | 5 (1 min 24 s) | 5 (1 min 50 s) | — | client-angular 4B/4T, client-mobile 1B/1T, réduction à ANG-06 |
| /sonar | skipped | 0.5 s | — | — | — | catalogue e2e seulement |
| /lint-angular | ok | 15 s | 1 (13 s) | 1 (19 s) | — | client-angular 1B/1T |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 12 min 56 s | — | — | — | e2e ×11 (37 min 52 s) |
| /review | ok | 9 min 21 s | 3 (18 s) | 7 (8 min 49 s) | — | client-angular 1B/3T, api-mail 1B/3T, client-mobile 1B/1T |
| /tech-writer | ok | 32 s | — | — | — | — |
| **Total cycle** | | **24 min 25 s** | **9 (1 min 56 s)** | **13 (10 min 59 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (13 s)

## Merged

- 2026-10-14 — `/merge task-370 --i-tested`
- api-mail : PR #299 squashée — `16689c40` ; CI `develop` ✅ https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38633154660
- client-mobile : PR #96 squashée — `01f67c88` ; CI `develop` ✅ https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/38633181092
- client-angular : managed manually by the human
- Branches `fix/task-370-session-weda2` supprimées (distantes et locales) ; pas de branche de staging (supprimée le 2026-10-14 au matin)
