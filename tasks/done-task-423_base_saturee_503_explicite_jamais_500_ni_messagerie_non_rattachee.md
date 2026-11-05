# todo-task-423.md — Base saturée : le médecin reçoit « service momentanément indisponible », jamais une erreur inattendue ni « messagerie non rattachée »

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1**. Quand la base sature, une partie des médecins reçoit un message **faux** : « Cette
messagerie n'est pas rattachée à votre compte ». Ils croient leur boîte détachée et peuvent tenter de la
rattacher à nouveau, alors que le service est seulement indisponible quelques instants. Une autre partie
reçoit une erreur inattendue (500) au lieu d'un 503. Les deux violent la règle 12.

> **Origine.** Campagne « limites » du 2026-11-05, itération 1 (escalier `journey`, IA simulée). Rapport :
> `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`,
> findings **F2** et **F3**. Au palier 1400, Postgres atteint `max_connections` (task-422). La plupart des routes
> répondent alors correctement **503 `DATABASE_UNAVAILABLE`** (12 017 réponses), mais pas toutes.

## Ce qui est établi

| Réponse rendue | Nombre | Route ou chemin | Ce qu'elle devrait être |
|---|---|---|---|
| 503 `DATABASE_UNAVAILABLE` | 12 017 | `GlobalExceptionHandler`, la plupart des routes | correct (règle 12) |
| **500** « An unexpected error occurred » | **4 323** | `GET /api/v1/mail/folders` | 503 `DATABASE_UNAVAILABLE` |
| **403 `MAILBOX_NOT_ATTACHED`** / `MAILBOX_REQUIRED` | **915** | toute route qui exige une boîte | 503 `DATABASE_UNAVAILABLE` |

- **F2 — le 500, cause établie** (Seq, trace `b1536922e2b4a591660bab9ec1742e48`, 2026-11-04T23:58:51Z) :
  `ImapService.GetFoldersAsync` (`Api/Mail/src/Application/Services/Implementation/ImapService.cs`, autour de
  la ligne 310) entoure `PersistAndReconcileFoldersAsync` d'un `catch (Exception)` qui journalise « Unexpected
  error getting folders » et rend `Result.Error`, donc un 500 générique. L'exception Npgsql
  (`08P01 server_login_retry`) n'atteint jamais le `GlobalExceptionHandler`, qui l'aurait classée
  `DATABASE_UNAVAILABLE`. Le même message existe dans `ImapFolderService.cs` (ligne 154) et une seconde fois
  dans `ImapService.cs` (ligne 293) : les trois sont à examiner.
- **F3 — le 403, chaîne probable, à établir trace par trace.**
  - Au même instant, `TenantRegistrySynchronizer.SynchroniseAsync` reçoit une `TenantRegistryUnavailableException`
    (`53300` en connexion directe au registre). Il journalise « Synchronisation ignorée — registre indisponible »
    et continue, par conception : « la cartographie du parc ne doit jamais coûter au praticien l'accès à sa
    messagerie ».
  - La sélection de la boîte (`UserContextEnricherMiddleware`) aboutit ensuite à `NotAttached` ou
    `MailboxRequired`, rendus en 403.
  - Une panne d'infrastructure est donc présentée comme une **réponse métier** sur les droits du médecin.
    Le contrat de `ITenantRegistryClient.GetMailboxAsync` dit pourtant : « `null` … c'est une réponse
    (403 `MAILBOX_NOT_ATTACHED`), **pas une panne** ».

## Objective

Quand la base ou le registre est indisponible, **toute** route rend un **503 `DATABASE_UNAVAILABLE`** en
`application/problem+json` (règle 12), produit par le `GlobalExceptionHandler`. Jamais un 500 générique, jamais
un 403 sur le rattachement. Le médecin lit « service momentanément indisponible, réessayez », et ses clients
gardent le comportement déjà prévu pour un 503.

Règles métier :
- **Un 403 de rattachement n'est rendu que sur une réponse du registre**, jamais sur son absence de réponse. Si
  le registre n'a pas pu être lu, on ne sait pas si la boîte est rattachée : c'est une indisponibilité.
- **La synchronisation du parc reste au mieux** : quand seule la cartographie (dernière activité, dernière
  authentification) échoue et que la sélection de la boîte peut être tranchée, la requête du médecin passe. Ce qui
  change, c'est qu'une sélection **impossible à trancher** faute de registre devient un 503, plus un 403.
- **Aucune heuristique de message** : le classement se fait par type d'exception ou par SQLSTATE, comme le fait
  déjà le `GlobalExceptionHandler`.
- **Zéro fuite** : le `detail` ne porte ni message d'exception brut, ni nom de base, ni adresse de boîte.

### Hors périmètre

- Éloigner le mur lui-même : task-422.
- Les clients (`client-mobile`, `client-blazor`, `client-angular`) : ils lisent déjà `ProblemDetails` et
  traitent le 503. Aucun écran ne change. Si `/develop` constate qu'un client traite un 503 de façon incorrecte
  sur ces routes, il ouvre une question au lieu d'élargir les `**Repos**`.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`. Exception admise : les 3 tests « du jour » de
      l'intégration, rouges connus entre 00:00 et 02:00, à condition d'être rejoués verts après 02:00
- [ ] Chaîne F3 établie et consignée dans le `## Develop log` avant le correctif : depuis l'échec du registre
      jusqu'au 403, avec les fichiers et méthodes traversés. Si la chaîne réelle diffère de celle décrite plus
      haut, le correctif suit la chaîne réelle
- [ ] Les `catch (Exception)` de `GetFoldersAsync` / `ImapFolderService` qui transforment une panne de base en
      `Result.Error` laissent passer les exceptions d'indisponibilité au `GlobalExceptionHandler`. Le task file
      liste chaque `catch` examiné et ce qui en est fait. Les autres catégories d'erreur gardent leur comportement
- [ ] Inventaire dans le task file des autres `catch (Exception)` d'`api-mail` qui rendraient une panne de base
      en 500, avec ce qui en est fait (corrigé ici, ou laissé avec sa raison)
- [ ] **Test d'intégration de bout en bout, `GET /api/v1/mail/folders`, base du praticien indisponible** : la
      réponse réelle est un **503**, `application/problem+json`, extension `code` = `DATABASE_UNAVAILABLE`, sans
      message d'exception brut dans `detail`. Cas nominal : la même route, base disponible, rend 200 et la liste
      des dossiers. Vu rouge sur le code d'avant (500) ou par mutation (règle 1b)
- [ ] **Test d'intégration de bout en bout, route exigeant une boîte (par exemple `GET /api/v1/mail/folders/{folder}`),
      registre indisponible** : la réponse réelle est un **503 `DATABASE_UNAVAILABLE`**, jamais un 403
      `MAILBOX_NOT_ATTACHED` ni `MAILBOX_REQUIRED`. Cas témoin : registre disponible et boîte réellement non
      rattachée, la même route rend toujours **403 `MAILBOX_NOT_ATTACHED`**. Vu rouge sur le code d'avant (403)
      ou par mutation (règle 1b)
- [ ] La façon dont le fixture rend la base ou le registre indisponible est décrite dans le task file. Seul le
      stockage est rendu indisponible, jamais la couche modifiée par la task
- [ ] Tests unitaires : la décision de sélection de boîte quand le registre est indisponible, ≥ 1 test par branche
      (registre indisponible ⇒ indisponibilité ; registre répond « non rattachée » ⇒ 403 inchangé)
- [ ] Trou du filet : la panne de base n'est pas rejouable par `/e2e` (le backend e2e n'injecte pas de saturation
      Postgres). Ligne ajoutée dans `conventions/e2e.md`, section des trous du filet : le bug, pourquoi `/e2e` ne
      l'a pas vu, et le test d'intégration qui le couvre désormais
- [ ] Aucune donnée de santé en clair dans les journaux : les journaux ajoutés ou modifiés ne portent ni adresse
      de boîte complète ni contenu de mail. Les SQLSTATE et les identifiants de corrélation restent
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché. Les codes 503 et
      `DATABASE_UNAVAILABLE` existent déjà

## Manual Test Plan

1. **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, avec une boîte
   rattachée.
2. **Cas nominal** : ouvrir la messagerie (`client-blazor` ou `client-mobile`). La liste des dossiers et l'inbox
   s'affichent.
3. **Base indisponible** : arrêter le conteneur PgBouncer, ou Postgres, depuis le tableau de bord Aspire ou par
   `docker stop`, puis rafraîchir l'inbox.
   - Le client affiche « service momentanément indisponible », jamais « messagerie non rattachée » ni l'écran de
     rattachement d'une boîte.
   - Dans Seq, `GET /api/v1/mail/folders` et les routes de la boîte sortent en 503 `DATABASE_UNAVAILABLE`. Aucun
     « Unexpected error getting folders » ni 500.
4. **Retour à la normale** : redémarrer le conteneur. Sans se reconnecter, l'inbox se recharge et la boîte est
   toujours rattachée.
5. **Témoin du 403** : demander une boîte qui n'est pas rattachée au compte (en-tête de boîte d'une autre
   adresse, ou boîte détachée), base disponible. La réponse reste 403 `MAILBOX_NOT_ATTACHED`.
6. **Au banc** (facultatif, skill `loadtest-skill`) : rejouer le palier 1400 de l'escalier de référence. Aucune
   réponse 500 ni 403 n'apparaît dans le journal k6, seulement des 503.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Robustesse et conformité interne à la règle 12
- **Exigences DSR honorées** : non applicable. Disponibilité et lisibilité des erreurs du service MSSanté
- **INS** : non applicable. Aucun trait d'identité n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : **renforcées dans leur lisibilité, inchangées dans leur décision**. Un refus de rattachement
  (403) ne se rend que sur une réponse du registre ; une indisponibilité ne se fait jamais passer pour un refus.
  Aucune boîte n'est ouverte quand le registre ne répond pas (règle 14 : pas d'accès sans verdict)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. L'échec reste journalisé côté serveur, corrélé par `traceId`. Aucun acte sur une
  boîte n'est ajouté ni retiré ; une requête refusée en 503 n'a pas d'acte à imputer
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau

## Arbitrage humain du 2026-11-05 (après la revue)

> Décisions de l'humain, en réponse au CHANGES REQUESTED de `/review` (`questions/task-423.md`) :
> 1. ~~Les trois routes sans test d'intégration reçoivent chacune leur test d'intégration.~~ **Amendée le même jour**
>    par l'humain (« Recentrer + nouvelle task ») : ces routes n'appellent pas la base sous les `catch` filtrés, leurs
>    500 sont des pannes IMAP. Filtres sans effet retirés, task-423 recentrée sur la base et le registre, **task-425**
>    créée pour les pannes IMAP en cours de lecture. Détail dans le `## Develop log`, « Reprise du 2026-11-05 ».
> 2. **Le 503 du registre injoignable porte `TENANT_REGISTRY_UNAVAILABLE`**, et non `DATABASE_UNAVAILABLE` comme
>    l'écrit la DOD : c'est le code catalogué de cette cause (task-420). Écart accepté par l'humain.
> 3. **Le `detail` de ce 503 devient un libellé fixe**, sans nom d'opération ni identifiant de corrélation : le
>    médecin lit « service momentanément indisponible », comme pour `DATABASE_UNAVAILABLE`. Ajouté au périmètre
>    de la task, prouvé par le test d'intégration du registre.
> 4. **Prévention** : consigne ajoutée dans `agents/develop.md` (Step 4.2), « le diff décide des endpoints, pas
>    la DOD ».

## Branches

- `api-mail` (pushed) : feat/task-423-base-saturee-503-explicite-jamais-500-ni — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-423-base-saturee-503-explicite-jamais-500-ni
  - Créée depuis `origin/develop` (`892b571a`). Le `develop` local d'api-mail porte un commit non poussé de l'humain (`4c497985 Fake IA provider`), **non inclus** dans cette branche.

## Timings

*(généré par `tools/timing/report.sh --task task-423 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 39 s | — | — | — | — |
| /develop | ok | 8 min 03 s | 8 (1 min 08 s) | 6 (27 min 16 s) | — | api-mail 8B/6T |
| /sonar | ok | 8 min 07 s | 3 (1 min 07 s) | 15 (19 min 49 s) | 6 (2 min 28 s) | 1 itération(s), api-mail 3B/15T |
| /lint-angular | skipped | 0.4 s | — | — | — | client non touché (2e reprise) |
| /lint-mobile | skipped | 0.4 s | — | — | — | client non touché (2e reprise) |
| /e2e | ok | 19 min 20 s | — | — | — | e2e ×15 (1 h 54 min) |
| /review | ok | 13 min 58 s | 5 (1 min 04 s) | 5 (27 min 44 s) | — | api-mail 5B/5T |
| **Total cycle** | | **50 min 11 s** | **16 (3 min 21 s)** | **26 (1 h 14 min)** | **6 (2 min 28 s)** | |

## Develop log

- Repos touched : `api-mail` (feat/task-423-base-saturee-503-explicite-jamais-500-ni)
- DTOs published : no DTO change — Interop published : no interop change
- Commits :
  - api-mail : `54ce89e9` fix(errors): base ou registre saturés rendus en 503, jamais en 500 ni en 403 — task-423
  - api-mail : `0e2c5172` refactor(errors): simplify pass (/simplify) — task-423
- Local build / test : ✓ `HealthPlatform.Api.Mail.sln` — domain 202, infrastructure 700, application 4 003, api 1 337, intégration 1 104 (+16 ignorés), 0 échec, aucun `FATAL`. Après la passe qualité : suite complète rejouée (un échec de harnais dans le nouveau test, corrigé), puis les 30 tests touchés depuis (nouveaux tests et suites qui partagent `ArchiveMailboxServer`) rejoués verts.

### Chaîne F3, établie avant le correctif

`UserContextEnricherMiddleware.ApplyMailboxSelectionAsync` → `MailboxSelectionService.SelectAsync` → `PostgresTenantRegistryClient.GetAccountAsync` / `GetMailboxAsync` / `ListMailboxesAsync`. Chacune attrapait `TenantRegistryUnavailableException` et rendait `null` ou `[]` (« dégradation définie », task-299, antérieure au passage du registre sur le chemin de chaque requête, task-303). La sélection lisait ce `null` comme « compte inconnu » (`MailboxRequired`) ou « non rattachée » (`NotAttached`), et le middleware écrivait le 403. Le `TenantRegistrySynchronizer` journalisait juste avant « Synchronisation ignorée — registre indisponible » (Seq, 2026-11-04T23:57Z). Chaîne conforme à celle de la task.

### Ce qui change

- **`DatabaseAvailability`** (`src/Application/Errors/`) : la seule définition des SQLSTATE d'indisponibilité (`08P01`, `08006`, `57014`, `53300`), lue par `DbException.SqlState`, sans dépendre du pilote. Le `GlobalExceptionHandler` l'appelle directement (l'ancien `IsDatabaseUnavailable` est retiré).
- **Registre** : `GetAccountAsync`, `GetMailboxAsync`, `ListMailboxesAsync` propagent la panne. Les opérations de cartographie (`ResolveTenantAsync`, `ListTenantsOfAccountAsync`, horodatages, `MarkAuthenticationOutcomeAsync`) gardent leur dégradation. Contrat écrit dans `ITenantRegistryClient` (« une absence n'est jamais une panne »).
- **Appelants examinés** :
  - `UserContextEnricherMiddleware.SelectMailboxAsync` : route `[MailboxNotRequired]` → continue sans boîte (journal `3726`) ; route qui exige une boîte → la panne remonte au `GlobalExceptionHandler`.
  - `MailboxAccessGate.FindAttachmentOrNullAsync` : au refus de l'opérateur, une panne du registre vaut absence, donc le verdict est retiré (fermeture sûre, journal `4034`).
  - `MailboxStreamAccessWatch.RecheckAsync` : le flux SSE se ferme sur `MAILBOX_ACCESS_UNVERIFIED`, jamais sur `MAILBOX_NOT_ATTACHED`.
  - `MailboxManagementService` (routes de gestion des boîtes) et `MailboxSenderIdentityService.CanEditAsync` : laissés propager, donc 503 ; avant, une panne y rendait « aucune boîte » ou « réservé au titulaire ».

### `catch (Exception)` examinés (inventaire mesuré)

Seq était injoignable pendant l'étape (conteneur sans port publié) : l'inventaire vient du journal k6 de l'escalier (`reports/2026-11-04/k6-log-k6-journey-20261104-234134.txt`, première occurrence par médecin et par geste, corps ProblemDetails avec `instance`).

| Route rendue en 500 au palier 1400 | Occurrences | `catch` | Fait |
|---|---|---|---|
| `GET /mail/folders/{folder}` | 3 841 | `ImapService.ReadFolderAsync` (→ `MapFolderAccessExceptionAsync`) | filtre `when (!DatabaseAvailability.IsUnavailable(ex))` |
| `GET …/emails/today` | 108 | `ImapService.ReadTodayAsync` (→ `MapFolderAccessExceptionAsync`) | filtre |
| `GET /mail/folders` | 108 | `ImapService.GetFoldersAsync` (×2 : lecture IMAP, persistance) et `ImapFolderService.GetFoldersAsync` | filtre |
| `GET …/emails/content/{uid}` | 135 | `ImapService.GetEmailContentInternalAsync`, lecture du message | filtre |
| `PUT …/emails/{uid}…` | 2 | non attribué : `instance` tronquée dans le journal, `EmailFlagService.UpdateEmailReadStatusAsync` n'a pas de `catch` | laissé, à confirmer au prochain tir |

Laissés avec leur raison : `ImapService.GetEmailContentInternalAsync`, `catch` de `imapClient.GetFolderAsync` (IMAP seul, aucune base). Les ~180 autres `catch (Exception)` de `src/Application` n'ont **pas** été passés un par un. Beaucoup sont volontairement au meilleur effort (nettoyages, ré-indexation après déplacement, analyse, traces), et y laisser passer une panne transformerait un effet secondaire avalé en requête échouée. Le filtre n'est posé que là où le banc a mesuré un 500.

Hors du prédicat, donc toujours 500 : une base injoignable au niveau du socket, ou le délai **client** de 30 s de Npgsql. Ces erreurs n'ont pas de SQLSTATE, comme avant task-423, côté `GlobalExceptionHandler` aussi. Le banc ne les a pas produites. À instruire si un tir les fait apparaître.

### Écart à signaler à `/review` : code du 503 du registre

La DOD écrit « 503 `DATABASE_UNAVAILABLE` » pour le registre indisponible. Le 503 rendu porte **`TENANT_REGISTRY_UNAVAILABLE`**, le code catalogué (task-420) que le `GlobalExceptionHandler` associe déjà à `TenantRegistryUnavailableException` (« les boîtes ne se listent pas ou ne se rattachent pas »). La règle 12 demande un mapping par type, et ce code dit la cause exacte. Le statut (503), le format et l'objectif (jamais un 403) sont ceux de la DOD.

### Tests

- **Intégration (règle 1b), vus rouges par mutation** :
  - `PractitionerDatabaseUnavailableEndToEndTests.ListingTheFolders_WhenThePractitionerBaseCancelsTheQuery_Returns503DatabaseUnavailable` : vrai `MailController`, vrai `ImapService`, Dovecot, base praticien réelle. Une autre session tient `MailFolders` en accès exclusif, et le serveur annule chaque requête qui l'attend (`pg_cancel_backend`, `57014`). Lu : 503, `application/problem+json`, `code` = `DATABASE_UNAVAILABLE`, `detail` fixe sans message du pilote. Témoin : `…_WhenThePractitionerBaseAnswers_Returns200WithTheInbox`.
    - **M1** : filtre retiré du `catch` de la persistance des dossiers → **500** au lieu de 503. Restauré par `cp`.
    - Premier essai écarté : `ALTER DATABASE … SET statement_timeout` ne vaut que pour les sessions neuves, l'application réutilisait la sienne et attendait le délai client de 30 s (500 sans SQLSTATE). Consigné dans le test.
  - `RegistryUnavailableEndpointIntegrationTests` : vrai schéma Bearer, vrai middleware, vraie `MailboxSelectionService`, vrai client PostgreSQL du registre. La base du registre refuse toute connexion (`ALLOW_CONNECTIONS false`, sessions coupées).
    - `MailboxRoute_WhenTheRegistryIsUnavailable_Answers503_NeverMailboxNotAttached` (compte en cache, le cas du banc) : 503 `TENANT_REGISTRY_UNAVAILABLE` pour la boîte rattachée et pour une inconnue. Témoin avant la panne : boîte inconnue → 403 `MAILBOX_NOT_ATTACHED`. **M2** : dégradation en `null` remise dans `GetMailboxAsync` → **403** (`Forbidden`). Un premier passage à cache froid n'observait pas M2, car c'est alors `GetAccountAsync` qui lève d'abord, d'où le cache qui retient.
    - `…_AndTheAccountIsNotCached_Answers503` : **M3** (dégradation remise dans `GetAccountAsync`) → **403**.
    - `MailboxOptionalRoute_WhenTheRegistryIsUnavailable_IsServedWithoutAMailbox` : 200, aucune boîte posée.
- **Unitaires** : `DatabaseAvailabilityTests` (4 SQLSTATE, chaîne enveloppée, erreurs de requête, `null`), `MailboxSelectionServiceTests` (registre indisponible sur le compte et sur le rattachement → la panne remonte), `MailboxAccessGateTests.ARefusalInUse_WhileTheRegistryIsUnavailable_StillDropsTheVerdict`, `MailboxAccessCollaboratorsTests.StreamWatch_WhenTheRegistryIsUnavailable_ClosesAsUnverified_NeverAsNotAttached`, `PostgresTenantRegistryClientTests.WhenUnavailable_GetAccountSurfacesTheFailure`. `ListMailboxes_…` et `GetMailbox_WhenUnavailable_SurfacesTheFailure` (ex-`…_DegradesTo…`) sont réécrits.
- **Trou du filet** : ligne ajoutée dans `conventions/e2e.md`, « Trous du filet ». Pas de scénario e2e, puisque le backend e2e ne sait pas saturer Postgres. Le filet est formé des deux tests d'intégration ci-dessus.

### Passe qualité (/simplify)

- Appliquée et commitée : `api-mail`, 11 fichiers (`0e2c5172`).
  - Relais `GlobalExceptionHandler.IsDatabaseUnavailable` retiré.
  - Trois commentaires qui disaient encore « le registre dégrade toujours » corrigés (`GlobalExceptionHandler`, `PostgresTenantRegistryClient`, `TenantRegistryUnavailableException`).
  - Le flux SSE passe par le `switch` existant.
  - Tests : `ArchiveMailboxServer` réutilisé, avec un accesseur `PractitionerConnectionString()`. `SqlProbe` réutilisé. `TenantRegistryTestClient.For(connection, cache)` ajouté. `try/finally` redondants retirés, doublon de test unitaire retiré.
- Écartés :
  - le helper du middleware rendant `MailboxRequired`, car « registre en panne » doit rester distinct de « aucune boîte » ;
  - la mise en commun du cache mémoire et du handler Bearer des tests d'intégration (6ᵉ copie de chacun), chantier hors périmètre ;
  - une lecture « compte puis rattachement » unique sur le registre, qui touche l'interface hors du périmètre.
- Contrôle mécanique §Q 2b : 2 S125 (« … ; … » dans deux commentaires), attrapés **après** le commit de la fonctionnalité et corrigés avant le push. Récidive comptée dans `conventions/csharp.md` (S125, 25).
- Skipped (contract/excluded) : dtos-mss, interop-cda, sdk non touchés.

- DOD self-check : 10 points sur 12 vérifiés par commande (build, tests, chaîne F3, `catch` corrigés, inventaire, deux tests d'intégration et leurs mutations, fixture décrite, tests unitaires par branche, trou du filet). Deux restent à voir :
  - « aucune donnée de santé en clair » : à relire en revue. Les journaux ajoutés ne portent qu'un chemin de route assaini, sans adresse ;
  - « contrat inchangé » : aucun fichier `Dtos/`, aucun frontend touché ; les codes existaient.
- Next step : `/sonar task-423`

### Reprise du 2026-11-05 après CHANGES REQUESTED (`questions/task-423.md`)

- **Décision 1 amendée par l'humain** (choix « Recentrer + nouvelle task », même jour) : en écrivant les trois tests
  demandés, l'analyse du code a montré que les `catch` filtrés de `GET /mail/folders/{folder}`, `…/today` et
  `…/content/{uid}` n'enveloppent **aucun** appel à la base. Leur `try` ne fait que de l'IMAP : connexion, résolution
  du serveur (configuration ou autoconfig), verrou de session (sémaphore en mémoire), `STATUS`, `SEARCH`, `FETCH`. Les
  lectures en base de ces routes (`CurrentGenerationAsync`, `GetMailAsync`) sont **hors** de ces `catch` et rendaient
  déjà 503. Des tests « base saturée » sur ces routes n'auraient rien prouvé, et la mutation de leur filtre n'aurait
  changé aucune réponse.
  - **Les 4 084 réponses 500 du banc sur ces routes sont des pannes IMAP en cours de lecture**, attrapées et rendues en
    500 générique. Elles relèvent d'un autre défaut de règle 12 : **task-425** créée (`todo-task-425_panne_imap_en_cours_de_lecture_503_jamais_500.md`).
  - L'inventaire du premier `## Develop log` les attribuait à la base : **c'était faux**.
- **Code** (`fccd6fc2`) :
  - filtres `DatabaseAvailability` **retirés** des `catch` sans appel à la base : `ImapService.GetFoldersAsync` (phase
    IMAP), `ReadFolderAsync`, `ReadTodayAsync`, `GetEmailContentInternalAsync`, et `ImapFolderService.GetFoldersAsync`
    (aucun appelant joignable par une route). **Seul reste** le filtre de la persistance des dossiers
    (`ImapService.GetFoldersAsync`, `PersistAndReconcileFoldersAsync`), prouvé par M1 ;
  - **décision 3** : le 503 `TENANT_REGISTRY_UNAVAILABLE` porte le `detail` fixe « The database is temporarily
    unavailable. Please try again in a moment. ». Le message de l'exception (opération, corrélation) reste au journal.
    Test d'abord : `ErrorHandlingCoverageTests.Map_TenantRegistryUnavailable_Returns503WithAFixedDetail` et l'assertion
    sur `detail` de `RegistryUnavailableEndpointIntegrationTests` **vus rouges** sur l'ancien message (« Le registre est
    injoignable. Opération=GetAccountA… »), verts après ;
  - commentaires corrigés (`DatabaseAvailability`, `PractitionerDatabaseUnavailableEndToEndTests`) ;
  - **décision 2** (code `TENANT_REGISTRY_UNAVAILABLE`) et **décision 4** (consigne `agents/develop.md`) : faites.
- **Comportements atteignables par un endpoint, et leur preuve** (règle 1b) :

| Comportement | Test d'intégration | Preuve rouge |
|---|---|---|
| `GET /mail/folders`, base qui annule la persistance → 503 `DATABASE_UNAVAILABLE`, `detail` fixe | `PractitionerDatabaseUnavailableEndToEndTests.ListingTheFolders_WhenThePractitionerBaseCancelsTheQuery_Returns503DatabaseUnavailable` | M1 : filtre retiré → 500 |
| Route qui exige une boîte, registre injoignable, compte en cache → 503 `TENANT_REGISTRY_UNAVAILABLE`, `detail` fixe | `RegistryUnavailableEndpointIntegrationTests.MailboxRoute_WhenTheRegistryIsUnavailable_Answers503_NeverMailboxNotAttached` | M2 : dégradation remise sur `GetMailboxAsync` → 403 ; ancien `detail` → rouge |
| Idem, cache froid | `…_AndTheAccountIsNotCached_Answers503` | M3 : dégradation remise sur `GetAccountAsync` → 403 ; ancien `detail` → rouge |
| Route `[MailboxNotRequired]`, registre injoignable → servie sans boîte | `MailboxOptionalRoute_WhenTheRegistryIsUnavailable_IsServedWithoutAMailbox` | filtre du middleware inversé → 503 au lieu de 200 (fait en revue) |

- **Build / test** : ✓ suite complète après la reprise — domain 202, infrastructure 700, application 4 003, api 1 337,
  intégration 1 104 (+16 ignorés), 0 échec.
- **Passe qualité** : le delta de la reprise est un retrait de filtres et une ligne de mapping, aucune simplification
  à appliquer. Contrôles mécaniques §Q 2b : rien.
- **Prévention** : `conventions/csharp.md`, nouvelle entrée « Filtre d'exception — il ne protège que ce que son `try`
  enveloppe » (Occurrences 1). La cause d'un 500 s'établit par sa trace, pas par sa route.
- Next step : `/sonar task-423`

### 2ᵉ reprise du 2026-11-05 (2ᵉ passage de `/review`)

- **Comportement ajouté à la preuve** : `GET /api/v1/account/mailboxes`, registre injoignable → **503
  `TENANT_REGISTRY_UNAVAILABLE`**, `detail` fixe, jamais `200 []`. Test d'intégration
  `MailboxAttachRoleIntegrationTests.Mailboxes_WhenTheRegistryIsUnavailable_Is503ProblemJson_NeverAnEmptyList` : vrai
  `AccountController`, vrai `MailboxManagementService`, vrai registre PostgreSQL, base du registre `ALLOW_CONNECTIONS
  false` (sessions coupées), rétablie en `finally`.
  - **M4** : dégradation en `null` remise dans `GetAccountAsync` → **`OK : []`**, le défaut d'origine. Restauré par
    `cp`. `ListMailboxesAsync` n'est pas atteinte avant le compte sur ce chemin (cache du test qui rate toujours) : sa
    propagation est prouvée par `PostgresTenantRegistryClientCoverageTests.ListMailboxes_WhenUnavailable_SurfacesTheFailure`.
- `MailboxSenderIdentityService.CanEditAsync` (`/account/mailboxes/current/sender-identity`) : **non joignable
  pendant une panne du registre**. La route exige une boîte (pas de `[MailboxNotRequired]`), donc la sélection du
  middleware lit le rattachement en base (`GetMailboxAsync`, sans cache) **avant** le contrôleur, et rend le 503 prouvé
  par M2 et M3. Seule une panne survenue entre la sélection et l'enregistrement atteindrait `CanEditAsync`, ce qui
  n'est pas reproductible de façon fiable. Aucun test d'intégration propre, par construction.
- Commit : `457423df` test(mailboxes). Suite d'intégration : 1 105 verts (+1), 16 ignorés, 0 échec. Code de production
  inchangé depuis `fccd6fc2`.
- Next step : `/sonar task-423`

## Sonar log

- Serveur : SonarQube 9.9.8 (`sonar.login`), conteneurs `sonarqube_db` puis `sonarqube` redémarrés (arrêtés depuis 41 h). Analyse de la branche `feat/task-423-…` : build Release, 5 passes de tests OpenCover (domain 202, application 4 003, infrastructure 700, api 1 337, intégration 1 104 + 16 ignorés, 0 échec).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,1 %, au premier passage
- Phase 1 — Issues fixées : 0 (0 bug, 0 vulnérabilité, 0 code smell, 0 hotspot à revoir)
- Phase 1 — Tests ajoutés : 0 (couverture du new code des fichiers de la task : `DatabaseAvailability` 100 %, `ImapService` 100 %, `ImapFolderService` 100 %, `MailboxStreamAccessWatch` 100 %, `MailboxAccessGate` 99,1 %, `GlobalExceptionHandler` 98,4 %, `PostgresTenantRegistryClient` 96,9 %, `MailboxSelectionService` 96,2 %)
- Phase 2 (legacy) : itérations 0 / 5 — rien à traiter (0 bug, 0 vulnérabilité, 0 code smell sur le projet)
- Build / tests : ✓ green
- `conventions/csharp.md` : rien à consigner, aucune règle corrigée à la main

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,5 % | 96,1 % | −0,4 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,9 % | 97,9 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

Baseline : analyse du 2026-11-01 (dernière sur le projet). New code period : 30 jours, depuis le 2026-10-03.

### Reprise du 2026-11-05 (commit `fccd6fc2`)

- Phase 1 : ✓ Quality Gate OK au premier passage, 0 issue new code, 0 hotspot, new_coverage = 96,0 %. Phase 2 : rien à traiter.

| Métrique | Baseline (1ᵉʳ passage) | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,1 % | 96,0 % | −0,1 pt |
| Bugs / Vulnerabilities / Hotspots / Code smells | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 |
| Coverage (projet) | 97,9 % | 97,8 % | −0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

- **2ᵉ reprise** (`457423df`, un test d'intégration ajouté) : Quality Gate OK, 0 issue new code, 0 hotspot, new_coverage 96,0 %, coverage 97,8 %, duplication 0,4 %, A/A/A — inchangé.

## Lint log
- skipped — no angular change

## Lint mobile log
- skipped — no mobile change

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 (angular), posée le 2026-10-09, correction task-350, 27 jours. Un test en quarantaine ne protège rien, sa correction est due. Vert sur ce run.

Rejoué après la 2ᵉ reprise (`457423df`). Les passages sur `0e2c5172` et `fccd6fc2` étaient verts eux aussi : 58 + 71.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte (jouée) | 58 verts, 0 flaky, 0 rouge, 0 quarantaine | ~10 min |
| angular | api-mail touché | ✅ verte (jouée) | 71 verts, 0 flaky, 0 rouge, 1 quarantaine (verte) | ~10 min |

- Code testé : api-mail `457423df` (branche de la task) ; client-mobile `19b5bf38` (`develop`, aligné sur `origin/develop`) ; client-angular `da02e583` (branche de l'humain `feature/nova-mss-weda-integration`, arbre propre).
- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (inchangé par la task)
- Quarantaines : E2E-COMPOSE-002 (angular, task-350) — vert
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun client touché)
- Démontage : complet pour ce run (ports libres, aucun conteneur e2e actif). Deux conteneurs arrêtés `e2e-greenmail-gcgjbrzp` et `e2e-dovecot-kgrndjwd` subsistent depuis le **2026-10-14**, étrangers à ce run : laissés en place, à retirer par l'humain (`docker rm`).
- Filet de la task : la panne de base ou de registre n'est pas rejouable par le banc e2e. Elle est couverte par les tests d'intégration du `## Develop log`, et consignée dans « Trous du filet » de `conventions/e2e.md`.

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
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/340 — label `awaiting-human-merge`. Branche synchronisée avec `develop` par merge (`324b2c6d`, apporte « Fake IA provider »), validée après fusion : domain 202, infrastructure 700, application 4 003, api 1 357, intégration 1 105 (+16 ignorés), 0 échec.

## Code Review Summary

**APPROVED** (3ᵉ passage, 2026-11-05) — 0 bloquant, 3 suggestions. Passages précédents : CHANGES REQUESTED ×2 (`questions/task-423.md`).

| Comportement atteignable par un endpoint | Test d'intégration | Preuve rouge |
|---|---|---|
| `GET /mail/folders`, base qui annule la persistance des dossiers → 503 `DATABASE_UNAVAILABLE`, `detail` fixe | `PractitionerDatabaseUnavailableEndToEndTests.ListingTheFolders_WhenThePractitionerBaseCancelsTheQuery_Returns503DatabaseUnavailable` | M1 : filtre retiré → 500 |
| Route qui exige une boîte, registre injoignable, compte en cache → 503 `TENANT_REGISTRY_UNAVAILABLE`, `detail` fixe | `RegistryUnavailableEndpointIntegrationTests.MailboxRoute_WhenTheRegistryIsUnavailable_Answers503_NeverMailboxNotAttached` | M2 → 403 ; ancien `detail` → rouge |
| Idem, cache froid | `…_AndTheAccountIsNotCached_Answers503` | M3 → 403 |
| Route `[MailboxNotRequired]`, registre injoignable → servie sans boîte | `MailboxOptionalRoute_WhenTheRegistryIsUnavailable_IsServedWithoutAMailbox` | filtre du middleware inversé → 503 |
| `GET /account/mailboxes`, registre injoignable → 503, jamais `[]` | `MailboxAttachRoleIntegrationTests.Mailboxes_WhenTheRegistryIsUnavailable_Is503ProblemJson_NeverAnEmptyList` | M4 → `200 []` |

- ✅ `DatabaseAvailability` : prédicat unique, sans dépendance au pilote, testé unitairement (4 SQLSTATE, chaîne enveloppée, erreurs de requête).
- ✅ `PostgresTenantRegistryClient` : les trois lectures de décision propagent ; la cartographie garde sa dégradation ; contrat écrit dans `ITenantRegistryClient`.
- ✅ Middleware, `MailboxAccessGate` (fermeture sûre au refus de l'opérateur), `MailboxStreamAccessWatch` (« à confirmer ») : bonne profondeur, chaque politique là où se prend la décision.
- ✅ Sécurité / règle 14 : aucun accès ouvert sans réponse du registre ; aucun acte ajouté ni retiré ; `detail` sans opération, corrélation, base ni adresse.
- ✅ `MailboxSenderIdentityService.CanEditAsync` : non joignable pendant une panne (la sélection du middleware rend 503 avant), argumenté dans le `## Develop log`.
- ⚠️ Les autres routes de gestion des boîtes (détacher, boîte par défaut, réauthentifier) passent par le même mécanisme, prouvé sur la liste ; pas de test propre à chacune.
- ⚠️ 6ᵉ copie du handler Bearer de test et du cache mémoire dans les tests d'intégration : à mutualiser sous `Harness/`.
- ⚠️ `GetEmailContentInternalAsync` rend `Result.Error(ex.Message)` sur une panne IMAP : task-425.
- **DOD** : tous les points vérifiés. Écart accepté par l'humain : code `TENANT_REGISTRY_UNAVAILABLE` au lieu de `DATABASE_UNAVAILABLE` pour le registre. Points d'observation (affichage client) reportés au Manual Test Plan.

