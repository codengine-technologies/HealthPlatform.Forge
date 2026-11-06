# todo-task-425.md — Panne de la messagerie MSSanté en cours de lecture : le médecin reçoit « messagerie momentanément injoignable » (503), jamais une erreur inattendue (500)

**Repos**: api-mail
**Dependencies**: — (aucune ; task-423 a établi que ces 500 ne viennent pas de la base)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Sous charge, des milliers de lectures rendent un 500 « An unexpected error occurred » au lieu
d'un 503 qui dit au médecin que sa messagerie est momentanément injoignable. Règle 12.

> **Origine.** Campagne « limites » du 2026-11-05, itération 1 (escalier `journey`, IA simulée), palier 1400.
> Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`.
> Écartée de task-423 par décision humaine du 2026-11-05 : l'analyse du code a montré que les `catch` de ces routes
> n'enveloppent **aucun** appel à la base. Voir `questions/task-423.md` et le `## Develop log` de task-423.

## Ce qui est établi

| Route | 500 au palier 1400 (journal k6, première occurrence par médecin et par geste) | `catch` qui rend le 500 |
|---|---|---|
| `GET /api/v1/mail/folders/{folder}` | 3 841 | `ImapService.ReadFolderAsync` → `MapFolderAccessExceptionAsync`, branche `default` |
| `GET /api/v1/mail/folders/{folder}/emails/today` | 108 | `ImapService.ReadTodayAsync` → `MapFolderAccessExceptionAsync`, branche `default` |
| `GET /api/v1/mail/folders/{folder}/emails/content/{uid}` | 135 | `ImapService.GetEmailContentInternalAsync`, lecture du message ; rend `Result.Error(ex.Message)` |

- Le `try` de ces `catch` ne fait que de l'IMAP : connexion, verrou de session (en mémoire), `STATUS`, `SEARCH`,
  `FETCH`, lecture des parties. Une panne IMAP **survenue après la connexion** (session coupée, délai dépassé, réponse
  `NO`/`BAD`) y est attrapée et rendue en 500 générique.
- Au même palier, 5 931 réponses étaient déjà des **503** « Impossible de joindre le serveur de messagerie » : la
  panne **à la connexion** est bien classée. C'est la panne **en cours de lecture** qui ne l'est pas.
- **Cause exacte à confirmer par la trace avant tout correctif** (consigne « Filtre d'exception » de
  `conventions/csharp.md`) : Seq était injoignable lors de task-423. Le type d'exception attrapé (MailKit
  `ImapProtocolException`, `IOException`, `ServiceNotConnectedException`, délai…) décide du correctif.

- **Reproduit le 2026-11-05 (tir task-422, jambe B)** : le pod Toxiproxy du banc a
  redémarré vers 17:27 UTC et IMAP/SMTP ont répondu `ConnectionRefused`. Sur 4 min 30 du palier 1400 :
  ≈ 6 934 réponses 503 (IMAP « Impossible de joindre le serveur de messagerie », SMTP « SMTP connection
  failed ») mais ≈ 11 328 réponses
  **500** « An unexpected error occurred » sur `dashboard` et `read_list`. Une messagerie **injoignable dès la
  connexion** produit donc aussi des 500 sur ces routes, pas seulement une panne en cours de lecture. Rapport :
  `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261105-task422-pool1-185011.md`.

## Objective

Une panne de la messagerie MSSanté survenue pendant la lecture d'un dossier, de « aujourd'hui » ou du contenu d'un mail
rend un **503 `MAIL_SERVER_UNAVAILABLE`** (`application/problem+json`, règle 12), comme la panne à la connexion. Jamais
un 500 générique, jamais le message brut de l'exception dans `detail`.

Règles :
- **Classement par type d'exception**, jamais par le texte du message. Les familles « transport / session IMAP »
  deviennent une indisponibilité. Les autres erreurs gardent leur comportement (un dossier disparu reste un 404
  `FOLDER_NOT_FOUND`, task-352).
- **Une session morte reste rejouée une fois** avant d'être déclarée indisponible (task-277, `DeadSessionPolicy`).
- **Zéro fuite** : le `detail` ne porte ni message d'exception, ni nom de dossier, ni adresse de boîte. Le contenu de
  mail rend aujourd'hui `Result.Error(ex.Message)`, à fermer.

### Hors périmètre

- Les pannes de base : task-423. Le seuil de connexions Postgres : task-422.
- Les clients : ils lisent déjà le 503 `MAIL_SERVER_UNAVAILABLE`. Aucun écran ne change.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] Cause établie et consignée dans le `## Develop log` avant le correctif : types d'exception attrapés sur les trois
      routes, relevés dans Seq lors d'un tir ou d'une panne provoquée, avec leur pile
- [ ] **Test d'intégration de bout en bout, `GET /api/v1/mail/folders/{folder}`, IMAP coupé en cours de lecture** :
      503, `code` = `MAIL_SERVER_UNAVAILABLE`, `detail` fixe. Cas nominal : 200 et la liste. Vu rouge (500) sur le code
      d'avant ou par mutation (règle 1b)
- [ ] Même test pour `GET …/emails/today` et pour `GET …/emails/content/{uid}` (message déposé au préalable)
- [ ] Le serveur IMAP est le seul élément rendu défaillant (fournisseur externe, règle 1b) : la manière (interruption de
      Dovecot, enveloppe de client IMAP du banc d'intégration, proxy) est décrite dans le task file
- [ ] Tests unitaires du classement : une exception de transport → indisponibilité ; un dossier disparu → 404 inchangé ;
      une autre erreur → comportement inchangé
- [ ] Trou du filet : ligne ajoutée dans `conventions/e2e.md` (panne IMAP en cours de lecture non rejouable par `/e2e`)
- [ ] Aucune donnée de santé ni nom de dossier dans les journaux ajoutés ou modifiés
- [ ] Contrat inchangé : aucun fichier `Dtos/`, aucun frontend ; le code `MAIL_SERVER_UNAVAILABLE` existe déjà

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, une boîte rattachée.
2. Ouvrir l'inbox (`client-blazor` ou `client-mobile`) : la liste s'affiche.
3. Pendant l'ouverture d'un dossier, arrêter le conteneur Dovecot (tableau de bord Aspire ou `docker stop`) : le client
   affiche « messagerie momentanément injoignable », jamais « erreur inattendue ». Dans Seq, la route sort en 503
   `MAIL_SERVER_UNAVAILABLE`.
4. Redémarrer Dovecot : sans se reconnecter, l'inbox se recharge.
5. Supprimer un dossier depuis un autre client IMAP puis l'ouvrir : toujours 404 « le dossier n'existe plus »
   (task-352, inchangé).
6. Au banc (facultatif, skill `loadtest-skill`) : rejouer le palier 1400 de l'escalier de référence ; plus de 500 sur ces
   trois routes.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Robustesse et conformité interne à la règle 12
- **Exigences DSR honorées** : non applicable. Lisibilité des erreurs du service MSSanté
- **INS** : non applicable. Aucun trait d'identité n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées. Aucune action sur une boîte n'est ajoutée ni retirée (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. L'échec reste journalisé côté serveur, corrélé par `traceId`
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau

## Develop log

### Cause établie (Seq, avant le correctif)

Relevé dans Seq sur les deux pannes du 2026-11-05 (escalier IA simulée, nuit du 04 au 05, et jambe B de task-422,
pod Toxiproxy redémarré à 17:27 UTC). Requêtes filtrées sur `Result-mapped 500` et les routes `/api/v1/mail/folders…`,
puis chaque famille exclue tour à tour jusqu'à n'en plus trouver : **aucun 500 ne venait d'une panne survenue après
une lecture réussie**. Trois familles, avec leur pile :

| Famille | Exception et pile | Où le statut se perdait |
|---|---|---|
| Connexion refusée | `SocketException (10061)` dans `ImapConnectionService.PerformConnectAndAuthenticateAsync` → `Result.Unavailable("Impossible de joindre le serveur de messagerie. Erreur réseau: ConnectionRefused")` | `ImapService.FailureOf` réécrivait tout statut autre que NotFound en `Result.Error` : `Result-mapped 500 … (ResultStatus=Error): Impossible de joindre…` |
| Poignée de main TLS coupée | `MailKit.Security.SslHandshakeException` → `IOException` → `SocketException (10054)` « forcibly closed by the remote host », dans `ImapClient.SslHandshakeAsync` | le `catch` générique de la connexion : `Erreur inattendue lors de la connexion: SslHandshakeException` (`Error`, 500) |
| Requête annulée par le client | `OperationCanceledException` (k6 abandonne après 60 s d'attente du verrou de session) | `MapFolderAccessExceptionAsync` et `GetFoldersAsync` rendaient `Result.Error("Request cancelled.")` (500 au lieu de 499, règle 12) |

Les mêmes familles touchent `GET /api/v1/mail/folders` (tableau de bord). Deux défauts latents du même chemin, non
observés au banc mais visés par la DoD (« IMAP coupé en cours de lecture ») :
- `TryResolveFolderAsync` avalait toute exception en `null` → « Failed to access folder » (500), sans passer par la
  reprise de session morte de task-277 ;
- le contenu d'un message rendait `Result.Error(ex.Message)` (fuite du texte de l'exception), et l'échec de la
  fermeture du dossier sur une session morte remplaçait le résultat de la lecture.

Hors périmètre, relevé au passage : `GET …/download/attachment/…` rend aussi un 500 « Error retrieving attachment: A
task was canceled. » (même famille, autre route).

### Correctif (`api-mail`)

- `Session/MailServerOutage.cs` : classement par type, jamais par le texte. `IsUnreachable` = session morte de
  task-277 (`DeadSessionPolicy`) + `TimeoutException` ; `IsInterruptedHandshake` = poignée de main dont la cause est
  une session morte (un certificat refusé reste une erreur) ; `IsRequestCancellation` ; `UnreachableDetail`, texte fixe.
- `ImapConnectionService` : `SslHandshakeException` interrompue par le transport → `Unavailable` ; `IsPropagated`
  réutilise `IsRequestCancellation`.
- `ImapService` :
  - `FailureOf` propage le statut (`PropagateFailure`, le point unique de task-283) ;
  - `ReadFailure<T>` : panne de messagerie → `Unavailable` + `detail` fixe (journal en Warning, sans dossier ni
    adresse), autre erreur → `Error` + message générique ;
  - l'annulation de la requête n'est plus rattrapée (filtre `when`) : le gestionnaire global la rend en 499 ;
  - `TryResolveFolderAsync(…, propagateOutage: true)` pour les deux lectures de dossier : la coupure atteint la reprise
    et le classement. Les trois autres appelants (analyse, traitement par lot, lecture d'un message seul) gardent leur
    contrat `null`, hors périmètre ;
  - contenu : plus de `ex.Message`, ouverture dans le `try`, fermeture best-effort par `TryCloseFolderAsync`.
- `ResultModelExtensions` : un 503 issu d'un `Result.Unavailable` porte `code` = `MAIL_SERVER_UNAVAILABLE` (le client
  mobile n'affiche son bandeau de panne que sur ce code) ; `detail` inchangé, celui du service.

### Comment la messagerie est rendue défaillante (règle 1b)

`Fixtures/ScriptedImapClientWrapperFactory` (ex-`CapabilityStrippingImapClientWrapperFactory`, renommée : elle ne fait
plus seulement retirer des capacités). C'est le vrai `ImapClientWrapper` de production, contre le vrai Dovecot de la
collection `UseCases`. Pour la seule boîte inscrite par un test (`CutSession(email)`), la résolution et la liste des
dossiers lèvent l'exception relevée au banc (`IOException` sur `SocketException` 10054). La connexion et
l'authentification restent réelles, et la reprise unique de task-277 se heurte à la même coupure. Tout le reste est
réel : `MailController`, `ImapService`, gestion d'erreurs RFC 7807, base PostgreSQL du praticien.

### Tests

- **Intégration de bout en bout** (`FolderOperationsEndToEndTests.MailServerOutage.cs`, 4 tests) : `GET
  /api/v1/mail/folders/INBOX`, `…/emails/today`, `…/emails/content/{uid}` (message déposé par un autre client, jamais
  analysé, donc lu sur le serveur) et `GET /api/v1/mail/folders`. Chacun : 200 avant la coupure, puis **503**,
  `application/problem+json`, `code` = `MAIL_SERVER_UNAVAILABLE`, `detail` égal au texte fixe. La lecture du dossier
  vérifie aussi la liste, et sa relecture à 200 une fois la session rétablie (étape 4 du Manual Test Plan).
- **Vus rouges sur le code d'avant** : les 4 tests, avant tout correctif, rendaient **500** « An unexpected error
  occurred », le symptôme exact du banc.
- **Preuve par mutation** (`t425_mutate.sh` : réinjection, rejeu, restauration par réécriture **puis recompilation**,
  contrôle `cmp`) :

  | Mutation | Tests d'intégration rouges |
  |---|---|
  | M1, `FailureOf` aplatit le statut en `Error` (rejouée après la passe qualité) | dossier, « aujourd'hui » |
  | M2, plus de `code` sur le 503 | les 4 |
  | M3, coupure non classée (`ReadFailure` ignore `IsUnreachable`) | les 4 |
  | M4, la résolution du dossier avale la coupure (rejouée après la passe qualité) | dossier, « aujourd'hui » |
  | Garde `Result.Unavailable` : un producteur hors messagerie ajouté | `OnlyTheMailServerPathsProduceAResultUnavailable` |

- **Unitaires** : 10 cas dans `ImapServiceCoverageTests` (connexion refusée → Unavailable, session morte deux fois,
  coupure à la résolution avec reprise, délai, autre erreur restée `Error`, « aujourd'hui », liste des dossiers,
  contenu : coupure à la résolution, au FETCH avec fermeture qui échoue, à l'ouverture) ; 2 dans
  `ImapConnectionServiceCoverageTests` (TLS coupé → Unavailable, certificat refusé → Error) ; 9 dans
  `MailServerOutageTests` ; 3 dans `ResultExtensionsTests` ; la garde d'architecture
  `ResultUnavailableIsAMailServerOutageScanTests`.
- **Réécrits** (ils figeaient l'ancien comportement) : trois tests d'annulation attendent désormais la propagation de
  l'annulation ; deux tests du contenu attendaient le texte brut de l'exception (« LIST broke », « fetch broke »).
- Le 404 du dossier disparu (task-352) est inchangé : tests existants verts.

### Passe qualité §Q (`/simplify`, 4 relectures)

- **Appliqué** : `FailureOf` entièrement par `PropagateFailure` ; clause de relance au lieu d'une double négation dans
  `TryResolveFolderAsync` ; fermeture par l'aide existante `TryCloseFolderAsync` au lieu d'une seconde ; `IsPropagated`
  réutilise `IsRequestCancellation` ; `IsInterruptedHandshake` s'appuie sur `DeadSessionPolicy` ; le message
  « Connexion interrompue » écrit une fois ; aide de test pour l'arrangement répété, assertion exacte pour le délai ;
  trois `DoesNotContain` qui ne pouvaient pas échouer retirés ; garde d'architecture sur les producteurs de
  `Result.Unavailable`, puisque le mappeur leur attribue `MAIL_SERVER_UNAVAILABLE`.
- **Écarté (changerait le comportement d'autres routes)** : supprimer le paramètre `propagateOutage` pour tous les
  appelants (la lecture d'un message seul passerait de 404 à 503, l'analyse et le traitement par lot changeraient de
  contrat) ; convertir les pièces jointes et les écritures (brouillons, envoyés) qui rendent encore `ex.Message` ;
  supprimer la surface de lecture de `ImapFolderService`, sans appelant ; unifier l'échelle de `catch` de la connexion.
  À instruire dans une task de suite.

### Validation

Build 0 erreur, 0 avertissement. Tests : domain 202, infrastructure 700, api 1 361, application 4 024, intégration
1 118 (+16 ignorés), **0 échec**.

### Prévention (règle d'or)

- `conventions/csharp.md` : « Panne de messagerie — elle garde son statut jusqu'à la route, et l'annulation n'est jamais
  rattrapée », avec la règle `Result.Unavailable` réservé à la messagerie.
- `conventions/e2e.md` : ligne « trou du filet » (panne non rejouable par `/e2e`, filet = les 4 tests d'intégration).
- Garde d'architecture `ResultUnavailableIsAMailServerOutageScanTests`.

### Retour de revue (règle 1b) : deux preuves de bout en bout ajoutées

La revue a relevé deux comportements atteignables par une route qui n'avaient que des tests unitaires. Ils ont été
prouvés de bout en bout avant d'ouvrir la PR (commit `test(mail): preuves de bout en bout…`, tests seuls, code de
production inchangé) :
- **poignée de main TLS coupée à la connexion** → 503 `MAIL_SERVER_UNAVAILABLE`, puis relecture à 200
  (`ConnectingWhileTheServerCutsTheTlsHandshake_Returns503MailServerUnavailable`). L'enveloppe IMAP lève, à la
  connexion, l'exception relevée au banc (`SslHandshakeException` sur `IOException` 10054). **M5** (clause TLS
  neutralisée) : rouge ;
- **lecture abandonnée par le client** → statut final 499, aucun `Result-mapped` journalisé
  (`AReadCancelledByTheClient_IsAClientClosedRequest_NeverAServerError`). La lecture du dossier reste bloquée jusqu'à
  l'annulation, et le statut final est relevé en tête de pipeline par un `IStartupFilter`. Depuis .NET 8, c'est le
  middleware d'exceptions d'ASP.NET Core qui pose ce 499 quand la requête est déjà abandonnée, sans appeler
  `GlobalExceptionHandler`. **M6** (annulation à nouveau avalée par la résolution du dossier) : rouge.

Suite d'intégration complète rejouée : 1 120 tests (+16 ignorés), 0 échec.

## Sonar log

- **Mode A (chaîné)**, `api-mail` sur `feat/task-425-panne-imap-en-cours-de-lecture-503`, 1 itération.
- **Résultat** : 0 issue sur le nouveau code, Quality Gate OK, 0 hotspot. Rien à corriger. La consigne
  « Filtre d'exception » et celle des `record` positionnels étaient appliquées d'emblée.
- **Tests sous couverture** : domain 202, application 4 024, infrastructure 700, api 1 361, intégration 1 118
  (+16 ignorés), **0 échec**.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 | 0 | = |
| New coverage | 96,0 % | 95,9 % | −0,1 |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,8 % | 97,9 % | +0,1 |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

- `/lint-angular` : **skipped** — `client-angular` n'est pas dans les `**Repos**` de la task.
- `/lint-mobile` : **skipped** — `client-mobile` n'est pas dans les `**Repos**` de la task.

## E2E log

| Voie | Déclenchée par | Résultat |
|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | ✅ 71 verts, 0 flaky, 0 rouge, parité verte (port 47399 vérifié libre avant la voie) |

**Porte** (`mss.mail.e2e gate`, catalogue `Api/Mail/e2e/scenarios.yml` inchangé face à `origin/develop`) :

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

- Démontage vérifié : port 47399 libre, aucun conteneur e2e laissé par ce run.
- La panne de messagerie en cours de lecture n'est pas rejouable par le banc e2e : son filet est le test d'intégration
  (`conventions/e2e.md`, Trous du filet, task-425).

## Branches

- `api-mail` (pushed) : feat/task-425-panne-imap-en-cours-de-lecture-503 — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-425-panne-imap-en-cours-de-lecture-503
  - Créée depuis `origin/develop` (`0e977535`).

## Timings

*(généré par `tools/timing/report.sh --task task-425 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 46 min 03 s | 4 (56 s) | 4 (11 min 33 s) | — | api-mail 4B/4T, 3 familles établies dans Seq ; 4 tests d'intégration vus rouges ; 5 mutations |
| /sonar | ok | 9 min 22 s | 1 (20 s) | 5 (7 min 26 s) | 2 (42 s) | 1 itération(s), api-mail 1B/5T, QG OK, 0 issue |
| /lint-angular | skipped | 0.5 s | — | — | — | repo non listé dans Repos |
| /lint-mobile | skipped | 0.5 s | — | — | — | repo non listé dans Repos |
| /e2e | ok | 19 min 26 s | — | — | — | e2e ×3 (18 min 57 s), mobile 58, angular 71, parité verte |
| /review | ok | 1 min 07 s | — | 1 (5 min 24 s) | — | api-mail 0B/1T, PR #344 ; 2 preuves 1b ajoutées au retour de revue |
| /tech-writer | ok | 1.2 s | — | — | — | E015 v1.82 |
| /merge | ok | 3 min 58 s | — | — | — | PR #344 squash b0cf4143, CI develop verte |
| **Total cycle** | | **1 h 20 min** | **5 (1 min 16 s)** | **10 (24 min 24 s)** | **2 (42 s)** | |

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/344 — label `awaiting-human-merge`.

## Code Review Summary

**APPROVED** — 4 fichiers de production, 8 de tests ; 0 point bloquant après retour de revue, 3 suggestions.

- Build : 0 erreur, 0 avertissement. Tests : 0 échec. Validation complète au passage de `/sonar`, sur le même code de
  production. Suite d'intégration rejouée après l'ajout des deux preuves : 1 120 (+16 ignorés), 0 échec.
- DoD : tous les critères tenus.
  - Cause établie dans Seq avec ses piles.
  - Tests d'intégration des trois routes (et de la liste des dossiers), nominal et panne, vus rouges sur le code
    d'avant.
  - Défaillance décrite (enveloppe IMAP du banc d'intégration).
  - Tests unitaires du classement : transport → 503, dossier disparu → 404 inchangé, autre erreur → inchangée.
  - Trou du filet consigné dans `conventions/e2e.md`.
  - Contrat inchangé.
  - Journaux ajoutés sans dossier ni adresse. Seule exception : la fermeture best-effort réutilise un gabarit existant,
    qui cite le dossier (suggestion ci-dessous).
- **Règle 1b — comportement → test → preuve rouge** :
  - dossier, « aujourd'hui », contenu, liste des dossiers → `…_WhenTheMailServerCutsTheSession_Returns503…` → rouges
    sur le code d'avant (500), et M1 à M4 ;
  - `code` sur le 503 → les quatre → M2 ;
  - poignée de main TLS → `ConnectingWhileTheServerCutsTheTlsHandshake_…` → M5 ;
  - annulation → 499 → `AReadCancelledByTheClient_…` → M6.
- **Retour de revue traité avant la PR** : deux comportements n'étaient prouvés que par des tests unitaires (poignée de
  main TLS, annulation). Les deux preuves de bout en bout ont été ajoutées (tests seuls) et vues rouges par mutation.
- E2E : vert, mobile 58/58, Angular 71/71, sur le code de production de la PR.
- Suggestions non bloquantes :
  - la fermeture best-effort cite le dossier (gabarit existant de `TryCloseFolderAsync`) ;
  - même famille de défaut hors périmètre, pour une task de suite : pièces jointes, écritures de brouillons et
    d'envoyés, lecture d'un message seul, surface de lecture morte d'`ImapFolderService` ;
  - l'hypothèse « `Result.Unavailable` = messagerie » est gardée par un test d'architecture.

## Merged

- 2026-11-06 — `api-mail` PR [#344](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/344), squash `b0cf4143` sur `develop`, après validation humaine (`/merge 425 --i-tested`).
- Branche `feat/task-425-panne-imap-en-cours-de-lecture-503` supprimée (distante et locale). CI `develop` verte sur `b0cf4143`.
- Aucune branche staging (task lancée par `/start`, pas par `/forge`).
