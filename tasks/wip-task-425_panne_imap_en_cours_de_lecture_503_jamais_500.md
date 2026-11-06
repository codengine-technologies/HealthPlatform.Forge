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
| **Total cycle** | | **55 min 40 s** | **5 (1 min 16 s)** | **9 (19 min 00 s)** | **2 (42 s)** | |
