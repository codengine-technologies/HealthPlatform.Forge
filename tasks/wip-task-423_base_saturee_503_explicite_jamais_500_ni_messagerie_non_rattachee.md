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

## Branches

- `api-mail` (pushed) : feat/task-423-base-saturee-503-explicite-jamais-500-ni — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-423-base-saturee-503-explicite-jamais-500-ni
  - Créée depuis `origin/develop` (`892b571a`). Le `develop` local d'api-mail porte un commit non poussé de l'humain (`4c497985 Fake IA provider`), **non inclus** dans cette branche.

## Timings

*(généré par `tools/timing/report.sh --task task-423 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 39 s | — | — | — | — |
| /develop | ok | 1 h 06 min | 5 (48 s) | 4 (16 min 26 s) | — | api-mail 5B/4T |
| /sonar | ok | 10 min 34 s | 1 (22 s) | 5 (6 min 53 s) | 2 (47 s) | 1 itération(s), api-mail 1B/5T |
| **Total cycle** | | **1 h 18 min** | **6 (1 min 11 s)** | **9 (23 min 20 s)** | **2 (47 s)** | |

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
