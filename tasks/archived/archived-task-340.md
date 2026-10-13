# todo-task-340.md — L'accusé de lecture fonctionne de bout en bout : demandé selon la norme, proposé à la réception, envoyé ou refusé une seule fois, enregistré et tracé

**Repos**: dtos-mss, api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: task-334 (la détection de la demande d'accusé sur les mails synchronisés en fond) — **mergée** (archivée)
**Epic**: E009
**Single frontend**: false
**Priorité**: **3** — l'accusé de lecture demandé par le praticien est ignoré par les clients courants ; à la réception, le mobile et weda2 ne le proposent jamais, et quand Blazor le propose, l'accusé échoue dès que l'expéditeur porte un nom d'affichage, n'est jamais enregistré (rien n'empêche un second envoi) et le journal d'audit l'enregistre en échec.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-32**, **AUD-43**).
>
> **Exigence humaine (2026-10-12).** Cette task doit **impérativement** être validée par des tests
> d'intégration couvrant **tout** le périmètre (un test au moins par point, sur la vraie pile) **et**
> par des tests e2e dédiés, sur mobile et sur weda2.
>
> **Décision humaine (2026-10-12).** Le **refus** de l'accusé par le praticien est une réponse à part
> entière : il est **tracé** au journal d'audit et **enregistré**. Le refus est **définitif** : la
> proposition ne revient plus, sur aucun client ni aucun poste, et l'accusé ne peut plus être envoyé
> ensuite.

## Ce qui est établi (re-vérifié sur develop @ `a87cde0`)

1. **Envoi non enregistré (AUD-32)** — `MailRepository.cs:2756-2770` (`MarkReadReceiptSentAsync`),
   `MailDataContext.cs:104-140` (aucun `HasColumnType` sur `ReadReceiptSentAt`, alors que `SentDate` et
   `AiTaggingPendingSince` l'ont), `MdnService.cs:56-100` : la valeur écrite par `NormalizeUtc` est de
   `Kind = Unspecified` ; faute de `HasColumnType`, EF type le paramètre en `timestamptz` et Npgsql le
   refuse avant même d'atteindre la base — le mécanisme que le contexte documente lui-même pour
   `SuppressionRequestedAt` (`MailDataContext.cs:232-239`). La colonne de production est déjà
   `timestamp without time zone` (FluentMigrator `AsDateTime`, `20240101_SetupMigration.cs:177`) : le
   défaut est dans le **modèle EF**, pas dans le schéma. Aucun interrupteur
   `Npgsql.EnableLegacyTimestampBehavior` ne le masque. Conséquences :
   - `ReadReceiptSentAt` jamais persisté → la garde 409 de l'endpoint (`MailController.cs:1036-1040`)
     ne se déclenche jamais, et Blazor (`MailListComponent.razor:1081`) repropose l'accusé dès que le
     mail repasse non lu ou est ouvert depuis un autre poste ;
   - l'exception survient **après** `SendAsync` : audit `ReadReceiptSend Success=false` pour un accusé
     réellement parti, et erreur rendue au client ;
   - le test unitaire `MailRepositoryTests.cs:819` passe car il tourne sur le fournisseur InMemory ;
   - la note de `MailRepositoryStatusCoverageTests.cs:148-153` attribue l'échec au seul harnais
     `EnsureCreated` et affirme l'écriture « correcte en prod » — c'est faux : le type du paramètre vient
     du modèle EF, pas de la colonne, la production échoue de la même façon.
2. **Demande non standard (AUD-43 a)** — `SmtpService.cs:389-392` : la demande d'**accusé de lecture**
   n'émet que `Return-Receipt-To`, jamais `Disposition-Notification-To` (RFC 8098) — les clients courants
   (Outlook / Thunderbird) ne proposent donc pas l'accusé de lecture. `Return-Receipt-To` relève de
   l'**accusé de réception** (demande DSN, MSS/va1.15 — RG-E009-042), pas de l'accusé de lecture. Deux
   tests d'intégration figent l'état actuel : `EmailCompositionUseCaseTests.cs:487-551` (task-197, qui
   consigne l'écart comme « décision produit » en attente) et `SendPathsEndToEndTests.cs:75`.
3. **Adresse inexploitable (AUD-43 b)** — `EmailAddressHelper.cs:51-62`, `MdnService.cs:111` : la valeur
   brute `"Dr X" <x@y.fr>` est passée comme **adresse** à `new MailboxAddress(string.Empty, …)` → échec
   d'analyse ou `RCPT TO` invalide ; seul le cas d'une adresse nue fonctionne. Le défaut est propre à
   l'accusé de lecture : l'envoi classique construit ses destinataires à partir du nom et de l'adresse
   séparés (`SmtpService.cs:302-311`, `DraftMimeBuilder.cs:21-30`) et émet correctement
   `"Dr X" <x@y.fr>`.
4. **Format** — le MDN envoyé (`MdnService.cs:104-140`) est un mail texte/HTML simple, pas un
   `multipart/report; report-type=disposition-notification` : aucun client ne le reconnaît comme accusé.
5. **Adresse en clair dans les journaux** — `MdnService.cs:41-42` et `:59` journalisent l'adresse de
   retour (`{To}`) en Information.
6. **Trace d'audit de la réponse du praticien — incomplète et en partie fausse.** La chaîne d'écriture
   fonctionne : `AuditService.Trace` (file `Channel`, débordement Redis, jamais de perte — task-292) →
   `AuditBackgroundService` (aucun filtre par type d'action) → journal mutualisé, sous le tenant de la boîte
   posé par `UserContextEnricherMiddleware` (`:597-599`), que la route `sendreadreceipt` traverse comme les
   autres ; relue sans filtre par `PostgresAuditReader`, libellée « Accusé de lecture » dans weda2
   (`audit.model.ts:92`) et Blazor (`AuditActionLabels.cs:41`). Mais dans `MdnService` :
   - **échec de connexion SMTP → aucune trace** (`MdnService.cs:47-51` rend `Result.Error` sans tracer)
     — un flux de transmission tenté n'est pas tracé (SC.MSS/CONF.17, SC.MSS/UX.37), et le client reçoit
     une erreur générique là où l'envoi classique rend `503` typé (task-330, `SmtpService.cs:93-101`) ;
   - **succès tracé après l'enregistrement** (`:61-75`) : l'échec d'AUD-32 le transforme en trace
     d'échec — un accusé parti est journalisé comme non parti ;
   - **auteur faux** : `FromAddress = originalMail.From?.Address` (`:70`, `:95`) désigne l'expéditeur
     d'origine, pas le praticien qui émet l'accusé ; `ToAddresses` porte la valeur brute de l'en-tête
     (`"Dr X" <x@y.fr>`) au lieu de l'adresse ;
   - **refus du PS non tracé** : « Non » dans Blazor (`MailListComponent.razor:1084-1101`) n'appelle pas
     l'API, et le mobile n'offre aucun bouton de refus (le bandeau ne peut qu'être ignoré). Rien n'est
     tracé ni enregistré : la proposition revient à chaque passage du mail en non lu. Le dernier membre
     d'`AuditActionType` est `MailServerAuthRetry = 40` (`Dtos/AuditActionType.cs`) ; aucun type ne
     désigne un refus d'accusé, et `MailDto` ne porte aucun état « refusé ».
   - Le seul scénario existant (`tests/Features/Mss/AuditJournal.feature:128-131`) n'est pas exécutable
     (règle 1) : aucun test ne relit la trace `ReadReceiptSend` en base.
7. **Proposition à la réception absente des clients du filet e2e.**
   - **client-mobile** : le bandeau existe (`mail-detail.component.ts:648-660`, task-105) mais il est
     conditionné à `mail.requestReadReceipt === true`, que l'API ne renseigne que pour les brouillons
     (`DraftService.cs:407, 439`) : il ne s'affiche **jamais** pour un mail reçu. Le modèle mobile
     (`mail.model.ts:176`) ne porte ni `readReceiptTo` ni `readReceiptSentAt`, et « déjà envoyé » n'est
     retenu que dans la session (`readReceiptSent`).
   - **client-angular (weda2)** : seule la case « Accusé de lecture » de la rédaction existe
     (`mail-compose.component.html:318-321`) ; aucun écran de lecture ne propose l'accusé, et
     `MssApiService.sendReadReceipt` n'a aucun appelant.
   - **client-blazor** : la proposition fonctionne (`ReadReceiptTo` présent et `ReadReceiptSentAt` vide)
     — c'est la référence de comportement.
   - `MailDto` porte déjà `ReadReceiptTo` et `ReadReceiptSentAt` (`Dtos/MailDto.cs:56-57`).
   - Aucun scénario du catalogue e2e (`Api/Mail/e2e/scenarios.yml`) ne couvre l'accusé de lecture.

## Objective

Qu'une demande d'accusé de lecture soit **comprise par les clients de messagerie courants** ; qu'un mail
reçu qui en demande un se le voie **proposer** sur mobile et sur weda2 ; que l'accusé soit renvoyé **une
seule fois** à l'adresse correcte au format normalisé, ou **refusé** une fois pour toutes ; que chaque
réponse du praticien — envoi ou refus — soit enregistrée et tracée avec son vrai résultat.

### Périmètre

**api-mail**

1. `ReadReceiptSentAt` mappé `timestamp without time zone` dans `MailDataContext` (convention du
   contexte, aligné sur la colonne FluentMigrator). L'écriture à l'insertion (`MailRepository.cs:225`)
   passe aussi par `NormalizeUtc`, sans quoi une valeur `Kind = Utc` serait refusée à son tour. Les trois
   propriétés `DateTime` de `Mail` sont alors toutes mappées explicitement.
2. Émission de `Disposition-Notification-To` lorsque l'**accusé de lecture** est demandé — le correctif
   AUD-43 a ne s'applique qu'à l'accusé de lecture.
3. Destinataire de l'**accusé de lecture** : l'en-tête reçu est analysé par `InternetAddressList.Parse`,
   la première `MailboxAddress` est retenue telle quelle (nom d'affichage compris). Valeur invalide →
   `400` ProblemDetails, aucun envoi, `ReadReceiptSentAt` reste vide, événement journalisé. Le correctif
   AUD-43 b ne s'applique qu'à l'accusé de lecture (construction du MDN) : l'envoi classique conserve
   `"Dr X" <x@y.fr>` sans aucun changement, et la valeur brute de l'en-tête reçu n'est pas réécrite.
4. MDN au format RFC 8098 : `multipart/report; report-type=disposition-notification`, une partie lisible
   (texte actuel conservé) et une partie `message/disposition-notification` portant au minimum
   `Final-Recipient` (boîte du praticien), `Original-Message-ID` (si le mail d'origine en a un) et
   `Disposition: manual-action/MDN-sent-manually; displayed` (l'envoi suit toujours l'action du PS). Le
   MDN ne demande lui-même aucun accusé.
5. Une fois le MDN parti, un échec d'enregistrement de `ReadReceiptSentAt` n'est plus rapporté comme
   un échec d'envoi : réponse `200`, trace `ReadReceiptSend` en succès (elle reflète le résultat SMTP),
   échec d'enregistrement journalisé à part (Error, sans adresse).
5 bis. **Toute réponse du praticien qui atteint le service d'accusé produit exactement une trace
   `ReadReceiptSend`** (constat 6), avec le contenu exigé par SC.MSS/CONF.18 :
   - succès : tracé **dès l'acceptation SMTP**, avant l'enregistrement de `ReadReceiptSentAt` ;
   - échec de connexion SMTP : trace d'échec, et `503` typé comme l'envoi classique (task-330) ;
   - échec d'envoi SMTP : trace d'échec (inchangé) ;
   - adresse d'accusé invalide : trace d'échec (motif « adresse d'accusé invalide »), `400` ;
   - contenu : `FromAddress` = boîte du praticien (auteur de l'accusé), `ToAddresses` = adresse analysée
     (sans nom d'affichage), `MailMessageId` = identifiant du message d'origine, `ServerRequest` = commande
     émise, `DurationMs` renseigné comme pour l'envoi classique.
   - Non tracés, car aucune décision n'est prise : `409` (accusé déjà envoyé ou refusé), `400` sans
     demande d'accusé, `404`, fenêtre de proposition fermée sans choix (Échap, clic hors de la fenêtre).
5 ter. **Refus de l'accusé** (décision du 2026-10-12) :
   - nouvel endpoint `POST folders/{foldername}/emails/{emailid}/declinereadreceipt`, symétrique de
     `sendreadreceipt` : `200` ; `400` sans demande d'accusé ; `404` mail inconnu ; `409` si l'accusé est
     déjà envoyé **ou** déjà refusé. Aucun message n'est émis (pas de MDN « denied »).
   - enregistrement : colonne `Mails.ReadReceiptDeclinedAt` (`timestamp without time zone`, nullable,
     migration FluentMigrator avec `Up` / `Down`, sur le modèle de `20261005130000_AddAiTaggingPending`),
     mappée explicitement dans `MailDataContext`, écrite via `NormalizeUtc`, lue par les chemins qui
     lisent `ReadReceiptSentAt` (`MailRepository.cs:225, 1173-1174, 2501-2502`).
   - `sendreadreceipt` refuse désormais aussi un mail dont l'accusé est refusé (`409`, aucun MDN).
   - trace `ReadReceiptDeclined` à chaque refus enregistré : `Success = true`, `UserId` et `FromAddress` =
     praticien, `ToAddresses` = adresse du demandeur (analysée ; vide si l'en-tête est invalide — le refus
     reste possible), `MailMessageId` = message d'origine, `ServerRequest` = `DECLINE MDN` (action locale,
     aucun échange serveur). Échec d'enregistrement → `5xx`, trace `Success = false`.
6. Les journaux de `MdnService` ne portent plus l'adresse de retour (constat 5) ; la trace d'audit, qui
   la porte par destination, est inchangée.
7. Tests existants mis à jour : la note de `MailRepositoryStatusCoverageTests.cs:148-153` remplacée par
   un vrai test ; `EmailCompositionUseCaseTests.cs:487-551` et `SendPathsEndToEndTests.cs:75` assertent
   `Disposition-Notification-To` (le commentaire task-197 est soldé) ; `MdnServiceTests` adaptés au
   nouveau format.

**dtos-mss**

7 bis. `AuditActionType.ReadReceiptDeclined = 41` (ordinal explicite, commentaire de la task, comme
   task-354) et `MailDto.ReadReceiptDeclinedAt` (`DateTime?`). Package publié (`/publish-dtos`),
   consommateurs bumpés : api-mail et client-blazor. `AuditActionTypeContractTests` étendu (41).

**client-mobile**

8. Le modèle du mail reçu porte `readReceiptTo`, `readReceiptSentAt` et `readReceiptDeclinedAt`. Le
   bandeau de `mail-detail` s'affiche quand `readReceiptTo` est renseigné et que l'accusé n'est ni envoyé
   ni refusé (mail reçu, ni brouillon ni envoyé) — il ne dépend plus de `requestReadReceipt`, qui reste le
   champ de la rédaction. Il offre **deux** actions : « Envoyer l'accusé » et « Ne pas envoyer » (appel de
   `declinereadreceipt`). Après une réponse réussie, l'état est mis à jour localement et le bandeau
   disparaît ; au rechargement, c'est la valeur serveur qui décide. Réponse `409` (déjà envoyé ou refusé,
   par exemple depuis un autre poste) → bandeau retiré avec un message d'information, pas une erreur.
   Aucune réponse sans action du PS (inchangé).

**client-angular (weda2)**

9. Même comportement dans la lecture d'un mail de weda2 (`mail-detail`) : proposition « L'expéditeur a
   demandé un accusé de lecture » avec « Envoyer l'accusé » et « Ne pas envoyer », mêmes conditions
   d'affichage, même traitement du succès, du `409` et des erreurs (ProblemDetails), aucune réponse sans
   action du PS. Le modèle `mail.model.ts` porte les trois champs ; `MssApiService` gagne
   `declineReadReceipt`. Miroir TS d'`AuditActionType` : `ReadReceiptDeclined = 41` (valeur explicite,
   `audit.model.spec.ts`) et libellé « Accusé de lecture refusé ». Libellés FR, `data-testid` sur la
   proposition, les deux boutons et les messages.

**client-blazor**

9 bis. La proposition (`MailListComponent.razor:1081`) ne s'affiche plus si l'accusé est refusé
   (`ReadReceiptDeclinedAt`). Un « Non » **explicite** appelle `declinereadreceipt` (nouvelle méthode
   `DeclineReadReceiptAsync` du `MailService`) ; fermer la fenêtre sans choisir n'appelle rien.
   `AuditActionLabels` : « Accusé de lecture refusé ».

**Filet e2e**

10. Trois scénarios au catalogue `Api/Mail/e2e/scenarios.yml`, écrits **avant** les tests
    (règle 1c), et deux données de seed :
    - donnée **`mail-demande-accuse-lecture`** : un message non lu de « Confrère E2E », portant
      `Disposition-Notification-To: "Dr Praticien E2E" <{adresse du praticien e2e}>` — adresse **avec nom
      d'affichage** (cas AUD-43 b), pointant vers la boîte du praticien pour que l'accusé, relayé par le
      puits, soit observable dans l'application. `E2eSeedMessage` / `E2eSeedPlan` étendus, liste
      `donnees` mise à jour (`ScenarioCatalogTests`) ;
    - donnée **`mail-accuse-a-refuser`** : un second message non lu, même forme, objet distinct ;
    - **E2E-RECEIPT-001**, **E2E-RECEIPT-002** et **E2E-RECEIPT-003**, v1 (voir la Definition of Done).

### Hors périmètre

- La détection de la demande sur les mails synchronisés en fond (task-334, mergée).
- client-blazor : hors du filet e2e (aucune voie) ; couvert par ses tests de composant et le plan de test
  manuel.
- L'envoi d'un MDN de refus (`Disposition: …; denied`) : la RFC 8098 le permet sans l'exiger ; le refus
  reste silencieux pour l'expéditeur.
- L'accusé de réception (`Return-Receipt-To`, demande DSN, MSS/va1.15) : son émission n'est ni retirée,
  ni remplacée, ni modifiée par cette task.
- L'adressage de l'envoi classique (`From` / `To` / `Cc` / `Bcc`, brouillons) : inchangé.
- Le mot-clé IMAP `$MDNSent` (RFC 3503), qui partagerait l'information « accusé envoyé » avec les autres
  clients de la boîte : non posé, la garde reste `ReadReceiptSentAt` en base.
- L'enveloppe SMTP nulle (`MAIL FROM:<>`) recommandée pour les MDN : non visée, la soumission MSSanté
  reste authentifiée au nom de la boîte du praticien.

## Definition of Done

### Build et tests

- [ ] api-mail : build 0 erreur — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; suite complète 0 échec (hors flaky pré-existants documentés)
- [ ] client-mobile : `npm run build` ✓ ; `npm test -- --watch=false --browsers=ChromeHeadless` 0 échec
- [ ] client-angular : `npm run build` (weda2) ✓ ; `npm test` 0 échec
- [ ] client-blazor : build 0 erreur ; tests 0 échec
- [ ] dtos-mss : package publié, consommateurs api-mail et client-blazor bumpés
- [ ] Migrations : `ReadReceiptSentAt` n'en demande aucune (colonne déjà `timestamp without time zone`, seul le modèle EF change — prouvé par I1) ; **une** migration FluentMigrator ajoute `ReadReceiptDeclinedAt`, relue (règle 7c : aucune opération fantôme), `Up` puis `Down` joués sur Postgres (I10)

### Tests d'intégration — couverture complète du périmètre (règle 1b)

Pile réelle : routage HTTP, DI, ProblemDetails, services, **PostgreSQL** du fixture, **GreenMail** comme
messagerie (fournisseur externe). Chaque test lit le comportement dans la **réponse réelle** et dans
l'**effet réel** (base, message relu dans le puits). Chacun est **vu rouge** sur le code actuel ou par
mutation, preuve consignée dans le `## Develop log`.

- [ ] **I1 — Enregistrement (périmètre 1)** : sur le **schéma de production** (`MigrateUp` FluentMigrator, comme `SetupMigrationGuardTests` — pas `EnsureCreated`), `MarkReadReceiptSentAsync` → exception sur le code actuel ; après correctif, valeur persistée et relue. Insertion d'un mail portant un `ReadReceiptSentAt` de `Kind = Utc` → acceptée.
- [ ] **I2 — Demande à l'envoi (périmètre 2)** : envoi par l'endpoint avec demande d'accusé de lecture → message relu dans le puits avec `Disposition-Notification-To` = adresse de l'expéditeur ; `Return-Receipt-To` présent, inchangé. Sans demande → aucun des deux en-têtes.
- [ ] **I3 — Non-régression de l'envoi classique (périmètre 3)** : envoi par l'endpoint vers `{ Name = "Dr X", Address = "x@y.fr" }` → en-tête `To` relu dans le puits `"Dr X" <x@y.fr>`.
- [ ] **I4 — Contrat de lecture (périmètres 8-9 bis)** : mail reçu portant `Disposition-Notification-To: "Dr X" <x@y.fr>` → `readReceiptTo` renseigné, `readReceiptSentAt` et `readReceiptDeclinedAt` vides dans la réponse réelle de la liste **et** du détail ; après envoi, `readReceiptSentAt` renseigné dans les deux ; après refus (autre mail), `readReceiptDeclinedAt` renseigné dans les deux.
- [ ] **I5 — Envoi de l'accusé, bout en bout (périmètres 3, 4)** sur `POST folders/{folder}/emails/{uid}/sendreadreceipt` :
  - nominal → `200` ; MDN relu dans le puits, `RCPT TO` `x@y.fr`, en-tête `To` `"Dr X" <x@y.fr>` ; `Content-Type` `multipart/report; report-type=disposition-notification` ; partie `message/disposition-notification` avec `Final-Recipient`, `Original-Message-ID`, `Disposition: manual-action/MDN-sent-manually; displayed` ; le MDN ne porte ni `Disposition-Notification-To` ni `Return-Receipt-To` ; `ReadReceiptSentAt` renseigné en base ;
  - second appel → `409` ProblemDetails, **aucun second MDN** dans le puits ;
  - mail dont l'accusé est refusé → `409`, aucun MDN ;
  - en-tête invalide → `400` ProblemDetails, aucun MDN dans le puits, `ReadReceiptSentAt` vide ;
  - mail sans demande → `400`, aucun MDN.
- [ ] **I6 — Audit (périmètres 5, 5 bis)** : la trace est relue **dans le journal en base, par l'API d'audit** (vrai `AuditService` → `AuditBackgroundService` → Postgres → `PostgresAuditReader`, sans `NoOpAuditService` ni `Audit:Disabled`), sous le **tenant de la boîte** du praticien :
  - I5 nominal → exactement **une** trace `ReadReceiptSend`, `Success = true`, `UserId` = praticien, `FromAddress` = boîte du praticien, `ToAddresses` = `x@y.fr`, `MailMessageId` = message d'origine, `ServerRequest` renseigné ;
  - serveur SMTP injoignable → `503` ProblemDetails, une trace `Success = false` ;
  - en-tête invalide → `400`, une trace `Success = false` au motif « adresse d'accusé invalide » ;
  - second appel (`409`) → aucune trace supplémentaire ;
  - vu rouge : sur le code actuel, le cas nominal produit une trace `Success = false` (AUD-32) et l'échec de connexion n'en produit aucune.
- [ ] **I7 — Échec d'enregistrement après envoi (périmètre 5)** : écriture de `ReadReceiptSentAt` refusée **par la base** (trigger de test qui lève sur cette mise à jour — la couche modifiée n'est pas simulée) → `200`, MDN relu dans le puits, **une seule** trace `ReadReceiptSend`, en succès, relue dans le journal, erreur d'enregistrement journalisée.
- [ ] **I8 — Journaux (périmètre 6)** : journaux capturés pendant I5 et I7 → ni l'adresse de retour, ni le sujet, ni le contenu du mail.
- [ ] **I10 — Refus de l'accusé (périmètre 5 ter)** sur `POST folders/{folder}/emails/{uid}/declinereadreceipt`, sur le schéma de production (`MigrateUp`, migration comprise) :
  - nominal → `200` ; `ReadReceiptDeclinedAt` renseigné en base ; **aucun message** dans le puits ; exactement **une** trace `ReadReceiptDeclined`, `Success = true`, `UserId` / `FromAddress` = praticien, `ToAddresses` = `x@y.fr`, `MailMessageId` = message d'origine, relue par l'API d'audit sous le tenant de la boîte ;
  - second refus → `409`, aucune trace supplémentaire ; refus après envoi → `409` ; envoi après refus → `409`, aucun MDN ;
  - en-tête invalide → refus accepté (`200`), trace avec `ToAddresses` vide ; sans demande → `400`, aucune trace ;
  - migration : `Down` retire la colonne, `Up` la remet, le mapping EF lit et écrit sans erreur ;
  - vu rouge : la route n'existe pas sur le code actuel (`404`).
- [ ] **I9 — Mail synchronisé en fond** : mail portant `Disposition-Notification-To` ingéré par la synchro de fond, puis accusé envoyé par l'endpoint → MDN relu dans le puits, `ReadReceiptSentAt` renseigné (chaîne task-334 + 340).
- [ ] Tests existants mis à jour (périmètre 7) et note erronée retirée.

### Tests unitaires et de composants

- [ ] api-mail : `MdnService` (construction du MDN, adresse invalide, échec d'enregistrement après envoi), `EmailAddressHelper` / analyse de l'en-tête (adresse nue, avec nom, plusieurs adresses → première, invalide, vide), `SmtpService.SetMessageHeaders` (avec et sans demande).
- [ ] api-mail : contrôleur et service du refus (nominal, `409` envoyé / refusé, `400`, `404`, échec d'enregistrement → trace d'échec).
- [ ] client-mobile : test de composant `mail-detail` — bandeau affiché (`readReceiptTo` présent, ni envoyé ni refusé) ; masqué si déjà envoyé, si déjà refusé, si brouillon, si dossier Envoyés, si pas de demande ; « Envoyer » → `sendReadReceipt` puis bandeau masqué ; « Ne pas envoyer » → `declineReadReceipt` puis bandeau masqué ; `409` → bandeau masqué + information ; autre erreur → message ProblemDetails, bandeau conservé ; test de service `declineReadReceipt` (POST sur la bonne route).
- [ ] client-angular : mêmes cas sur le composant de lecture weda2 ; `audit.model.spec.ts` : `ReadReceiptDeclined = 41`.
- [ ] client-blazor : « Oui » → envoi ; « Non » → refus appelé ; fenêtre fermée sans choix → aucun appel ; mail refusé → aucune proposition.
- [ ] `data-testid` sur la proposition, les deux boutons et les messages (mobile et Angular).

### Tests e2e dédiés (règle 1c, `/e2e`)

- [ ] Données `mail-demande-accuse-lecture` et `mail-accuse-a-refuser` ajoutées au seed et déclarées dans `donnees` ; `ScenarioCatalogTests` vert.
- [ ] Scénario **E2E-RECEIPT-001** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` (`mobile: requis`, `angular: requis`, `mode: headless`, `origine: task-340`) et implémenté dans les deux suites. Titre : « Demander un accusé de lecture à l'envoi ». Attendu : le praticien écrit à « Robert E2E », coche « Accusé de lecture » et envoie ; le message arrive dans la boîte de réception ; **relu côté serveur** (API), il porte la demande (`readReceiptTo` = adresse du praticien) ; l'application propose l'accusé à son ouverture.
- [ ] Scénario **E2E-RECEIPT-002** v1 ajouté (`mobile: requis`, `angular: requis`, `mode: headless`, `seed: [mail-demande-accuse-lecture]`, `origine: task-340`) et implémenté dans les deux suites. Titre : « Envoyer l'accusé de lecture d'un message reçu, une seule fois ». Attendu : à l'ouverture du message, l'application propose l'accusé ; le praticien l'envoie, une confirmation s'affiche, la proposition disparaît ; **relu côté serveur**, `readReceiptSentAt` est renseigné et le journal d'audit porte une trace « Accusé de lecture » en succès (API d'audit) ; l'accusé (« Lu : {objet} ») arrive dans la boîte de réception ; après rechargement de l'application, le message rouvert ne propose plus l'accusé.
- [ ] Scénario **E2E-RECEIPT-003** v1 ajouté (`mobile: requis`, `angular: requis`, `mode: headless`, `seed: [mail-accuse-a-refuser]`, `origine: task-340`) et implémenté dans les deux suites. Titre : « Refuser l'accusé de lecture d'un message reçu ». Attendu : à l'ouverture du message, l'application propose l'accusé ; le praticien choisit « Ne pas envoyer », la proposition disparaît ; **relu côté serveur**, `readReceiptDeclinedAt` est renseigné, `readReceiptSentAt` reste vide et le journal d'audit porte une trace « Accusé de lecture refusé » ; aucun accusé n'arrive dans la boîte ; après rechargement, le message rouvert ne propose plus l'accusé.
- [ ] Le jugement porte sur ce que le serveur a enregistré, pas seulement sur l'écran (`conventions/e2e.md`, `etat-optimiste`). Les données de E2E-RECEIPT-002 et 003 sont consommées par leur parcours : chaque suite part d'un backend remis à zéro, ou dispose de sa propre donnée — choix de `/develop`, consigné.
- [ ] Trou du filet : les trois scénarios **prouvés rouges** sur le code non corrigé (mobile : bandeau jamais affiché ; weda2 : aucune proposition ; E2E-RECEIPT-003 : aucun refus possible), puis verts. La relecture serveur de E2E-RECEIPT-001 ne distingue pas `Disposition-Notification-To` de `Return-Receipt-To` (l'API lit les deux) : l'en-tête émis est prouvé par I2, pas par l'e2e — preuve consignée (`preuve-par-mutation`), ligne ajoutée dans `conventions/e2e.md`.
- [ ] `/e2e` vert sur les voies mobile et Angular, porte `gate` comprise ; `## E2E log` rempli.

### Hygiène

- [ ] Aucune adresse ni contenu en clair dans les journaux de `MdnService` (constat 5 corrigé)
- [ ] Aucun envoi ni refus d'accusé sans action explicite du PS, sur aucun client

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, GreenMail) ; client mobile, weda2, et Blazor en non-régression.
2. Envoyer un message avec « Accusé de lecture » coché vers une boîte de test lue dans Thunderbird → Thunderbird propose l'accusé. Avant : aucune proposition.
3. **Mobile** : recevoir un mail de test demandant un accusé avec un nom d'affichage (`"Dr Test" <test@…>`), l'ouvrir → le bandeau propose l'accusé ; l'envoyer → confirmation, bandeau retiré ; l'accusé arrive chez l'expéditeur au format accusé (reconnu comme tel par Thunderbird). Avant : aucun bandeau.
4. **Mobile** : fermer et relancer l'application, rouvrir le mail → aucune proposition. Avant : sans objet (aucun bandeau).
5. **weda2** : mêmes étapes 3 et 4 sur un second mail de test. Avant : aucune proposition.
6. **Blazor** : sur un troisième mail, accepter l'accusé, marquer le mail non lu, recharger, le rouvrir → aucune nouvelle proposition, aucun second accusé. Avant : nouvelle proposition, second accusé.
7. Envoyer l'accusé d'un mail depuis Blazor puis l'ouvrir sur mobile → pas de proposition (ou information « déjà envoyé » si l'écran était déjà ouvert).
8. Écran d'audit (weda2 ou Blazor) → chaque envoi d'accusé apparaît une fois, « Accusé de lecture », en succès, émis par la boîte du praticien vers l'adresse de l'expéditeur. Avant : en échec, avec l'expéditeur d'origine comme émetteur.
9. Couper le serveur SMTP du banc, tenter un accusé → message « messagerie indisponible » ; l'écran d'audit montre la tentative en échec. Avant : erreur générique, aucune trace.
10. **Refus** — sur mobile, weda2 et Blazor (un mail chacun) : choisir « Ne pas envoyer » / « Non » → la proposition disparaît, aucun accusé n'arrive chez l'expéditeur ; recharger, rouvrir → plus de proposition ; ouvrir le même mail sur un autre client → plus de proposition. Écran d'audit → une ligne « Accusé de lecture refusé » par mail. Avant : aucune trace, proposition à chaque passage en non lu (Blazor), aucun refus possible (mobile, weda2).
11. **Blazor** : fermer la fenêtre de proposition sans choisir → aucune trace, la proposition reviendra.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : accusé de lecture MSSanté (fonctionnalité existante rendue conforme à la RFC 8098 et proposée sur tous les clients)
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée pour l'envoi
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — norme de messagerie (RFC 8098)
- **Tracé PGSSI-S** : `ReadReceiptSend` tracé avec son vrai résultat ; refus tracé (`ReadReceiptDeclined`) — SC.MSS/CONF.17, CONF.18, UX.37
- **Consentement patient** : non applicable — l'accusé n'est jamais envoyé ni refusé sans action du PS
- **Référentiels métier** : RFC 8098 (Message Disposition Notification)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-340-accuse-de-lecture — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-340-accuse-de-lecture
- `client-blazor` (pushed) : fix/task-340-accuse-de-lecture — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-340-accuse-de-lecture
- `client-mobile` (pushed) : fix/task-340-accuse-de-lecture — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-340-accuse-de-lecture
- `dtos-mss` (paresseuse) : aucune branche créée par `/start` — `/develop` la crée depuis `origin/develop` (fix/task-340-accuse-de-lecture) au moment où il touche le contrat (`AuditActionType.ReadReceiptDeclined`, `MailDto.ReadReceiptDeclinedAt`)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (instantané au `/start` : `feature/nova-rewriting-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-340 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 32 s | — | — | — | — |
| /develop | ok | 3 min 11 s | 20 (2 min 11 s) | 17 (9 min 24 s) | — | dtos-mss 1B/0T, api-mail 15B/13T, client-blazor 2B/2T, client-angular 1B/1T, client-mobile 1B/1T |
| /sonar | skipped | 6.4 s | 3 (42 s) | 11 (9 min 10 s) | 4 (1 min 12 s) | api-mail 3B/11T, api-mail inchangé depuis l'analyse b41550d0 |
| /lint-angular | ok | 10 s | — | — | — | — |
| /lint-mobile | ok | 9.0 s | — | — | — | — |
| /e2e | ok | 12 min 07 s | — | — | — | e2e ×6 (24 min 13 s) |
| /review | ok | 5 min 46 s | 5 (42 s) | 4 (3 min 57 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 30 s | — | — | — | — |
| **Total cycle** | | **23 min 33 s** | **28 (3 min 36 s)** | **32 (22 min 31 s)** | **4 (1 min 12 s)** | |

Autres commandes mesurées : lint ×5 (26 s), nuget-wait ×1 (44 s), restore ×4 (13 s)

## Develop log

- **Repos touchés** : `dtos-mss` (branche créée ici, contrat), `api-mail`, `client-blazor`, `client-mobile`, `client-angular` (code-only, non commité).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss` → **527.0.0** (`AuditActionType.ReadReceiptDeclined = 41`, `MailDto.ReadReceiptDeclinedAt`). Consommateurs bumpés : api-mail (lock files compris, 524 → 527), client-blazor (517 → 527). Miroirs : `AuditActionTypeContractTests` (41, 43 membres), `AuditRetentionPolicy` (ReadReceiptSend et ReadReceiptDeclined → accès aux données de santé, test ajouté), Angular `audit.model.ts` (+ spec), Blazor `AuditActionLabels` — **qui reçoit aussi 39 et 40** (task-354 n'avait pas bumpé Blazor : le contrat 527 les y fait entrer, le test « chaque action a un libellé » l'exige).
- **Restore NuGet** : les jetons du flux GitHub configurés (dépôt et profil) répondent 401. Restore fait avec le jeton de la CLI `gh` (portée `write:packages`) passé par `NuGetPackageSourceCredentials_*` à la seule commande, aucun fichier de configuration modifié. **À renouveler par l'humain** : jetons de `Api/Mail/nuget.config` et de `%APPDATA%\NuGet\NuGet.Config`.
- **Interop / SDK** : aucun changement.
- **Commits** :
  - dtos-mss : `29073f5` feat(dto) — contrat du refus
  - api-mail : `b06837bd` bump 527 ; `d63f504b` fix(mail) production ; `2121a316` test(mail) ; `63c24e1e` style S125 ; `5206f18b` test(e2e) catalogue + seed ; `1b69a58c` refactor (passe qualité)
  - client-blazor : `238a7be` bump 527 ; `84961a4` feat(mss) ; `5106fa6` refactor (passe qualité)
  - client-mobile : `60aa545` fix(mobile) ; `ecc8dc5` test e2e ; `91a358a` test e2e (filtre des traces)
  - client-angular (non commité, branche `feature/nova-rewriting-mss-weda-integration`) : `core/models/{audit.model.ts, audit.model.spec.ts, mail.model.ts}`, `core/services/mss-api.service.ts`, `core/utils/read-receipt.util.ts` (+ spec, nouveaux), `features/mail/components/mail-detail/{.ts,.html,.scss}`, `mail-detail.read-receipt.spec.ts` (nouveau), `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts` — **à commiter sur TFS avant le merge de la PR api-mail** (tests des scénarios requis E2E-RECEIPT-001/002/003).
- **Build / tests locaux** :
  - api-mail : build 0 erreur ; domain 190 ✓, infrastructure 683 ✓, application 3 617 ✓, api 1 199 ✓, intégration 860 ✓ + 16 ignorés préexistants. **3 rouges préexistants hors task** : `FilterTodayEmailsShouldReturnOnlyToday…`, `GetFolderTodayAsync_Inbox_…`, `GetFolderNotSeenTodayAsync_Inbox_…` — fenêtre 00:00–02:00 heure de Paris (date locale différente de la date UTC de Dovecot), déjà consignée par task-339 et task-343 ; suites jouées à 00:0x et 00:5x.
  - client-blazor : build 0 erreur ; 437 ✓, 2 ignorés préexistants.
  - client-mobile : build ✓ ; 1 027 ✓ sur trois passages consécutifs. Un premier passage, juste après le build, a compté 3 échecs que la sortie filtrée n'a pas nommés ; non reproduits ensuite (consigné, non attribué).
  - client-angular : `npm run build` (weda2) ✓ ; `npm test` 11 projets ✓ (mss-lib 771 ✓) ; lint ciblé 0 erreur (avertissements tous antérieurs) ; Prettier : `--write` seulement sur les fichiers propres en HEAD, diff sans suppression parasite ; HTML (non propre en HEAD) formaté à la main sur les seuls ajouts.
- **Tests d'intégration (règle 1b)** — `ReadReceiptEndToEndTests` (11, UseCases : HTTP réel, base praticien provisionnée par `MigrateUp`, GreenMail, journal Postgres relu par `GET /api/v1/audit/traces`), `ReadReceiptMigrationTests` (3, schéma de production `MigrateUp` / `MigrateDown`), `MailRepositoryStatusCoverageTests` (3 tests remplaçant la note erronée de task-082), plus `EmailCompositionUseCaseTests` et `SendPathsEndToEndTests` mis à jour :
  - I1 `MarkReadReceiptSentAsync_PersistsTheTimestamp_AndItIsReadBack`, `AddNewMail_WithUtcReadReceiptDates_…`, `TheEfModel_WritesAndReadsBothDates_OnTheProductionSchema` ; I2 `AMessageSentWithAReadReceiptRequest_CarriesDispositionNotificationTo_AndKeepsReturnReceiptTo` ; I3 `ARegularSend_ToARecipientWithADisplayName_KeepsTheDisplayName` ; I4/I5/I6/I8 `AReceiptRequestedWithADisplayName_IsSentOnce_InRfc8098_ToTheParsedAddress_RecordedAndTraced` ; I5/I6 `AnUnusableReceiptAddress_Is400_…`, `AMailThatRequestsNoReceipt_Is400_…`, `AMailServerThatCannotBeReached_Is503_…` ; I7/I8 `WhenTheDatabaseRefusesTheRecordAfterTheSend_…` (trigger Postgres de test, la couche modifiée n'est pas simulée) ; I10 `DecliningAReceipt_RecordsItForGood_…`, `DecliningAfterTheReceiptWasSent_Is409_…`, `DecliningAReceiptWithAnUnusableAddress_…`, `TheDeclinedColumn_GoesDownAndComesBack_…`, `BothReadReceiptColumns_AreTimestampsWithoutTimeZone` ; I9 `AMailSyncedInTheBackground_CanHaveItsReceiptSent_AndRecorded`.
  - Journal (I6) : les traces émises par le vrai `AuditService` sont lues dans le canal de la fixture (qui n'héberge pas son consommateur), confiées à un vrai `AuditBackgroundService` → `PostgresAuditSink` → journal Postgres dédié, relues par le vrai `AuditController` / `PostgresAuditReader` sous le tenant de la boîte. Panne SMTP : seul le résolveur de serveur désigne un port fermé ; fabrique SMTP et `MdnService` réels.
  - Journaux (I8) : capture globale `ReadReceiptLogCapture` (convention `asynclocal-hors-requete-de-test`), prouvée non vide avant l'absence.
- **Preuves par mutation (api-mail, 11 mutations, `git checkout` après chacune, dépôt propre à la fin)** — chacune rouge sur les tests visés :
  - M1 sans `HasColumnType` sur ReadReceiptSentAt (AUD-32) → 7 rouges : les 3 tests de dépôt, `TheEfModel_…OnTheProductionSchema`, I5, I9, `DecliningAfterTheReceiptWasSent_…` ;
  - M2 sans Disposition-Notification-To (AUD-43 a) → I2, `EmailCompositionUseCaseTests.SendEmailWithReadReceiptRequest…`, `SendPathsEndToEndTests.ADraftWithAPdf…` ;
  - M3 valeur brute passée comme adresse (AUD-43 b) → I5 ; M4 MDN réduit à sa partie lisible → I5 ;
  - M5 enregistrement refusé rendu en échec → I7 ; M6 échec de connexion non tracé → I6 (503) ; M7 auteur = expéditeur d'origine → I5 et I10 ;
  - M8 refus non définitif → I10 ; M9 adresse journalisée → I5 et I7 (I8) ; M10 `ReadReceiptDeclinedAt` absent de la lecture → I10 ; M11 refus sans condition → test de dépôt.
  - Blazor : `IsPending` sans le refus → `ReadReceiptResponderTests` rouge. Angular : règle sans le refus → 3 specs rouges. Mobile : idem → 2 specs rouges.
- **Défaut trouvé en route et corrigé** : `MarkReadReceiptDeclinedAsync` (ExecuteUpdate) laissait une copie suivie périmée dans le contexte — consigne `executeupdate-copie-suivie-perimee` appliquée (`ReloadAsync` des copies suivies), test de dépôt rouge avant, vert après.
- **Défaut préexistant relevé, hors périmètre — task à ouvrir** : `PostgresAuditReader.ApplyFilters` **ignore `ActionType` et `Search`** de `AuditTraceFilterDto` : le filtre par type d'action de l'écran d'audit (weda2, Blazor) est sans effet, et aucun test ne le couvre. Les parcours e2e lisent donc les traces par `MailUid` (appliqué) et filtrent `actionTypeName` eux-mêmes.
- **Parcours e2e (Step 6b)** : catalogue E2E-RECEIPT-001/002/003 v1 (mobile et Angular requis) écrit avant les tests ; données `mail-demande-accuse-lecture` et `mail-accuse-a-refuser` (lues, `Disposition-Notification-To: "Dr Praticien E2E" <praticien@…>`) ; `E2eSeedPlanTests` +3, `ScenarioCatalogTests` ✓. Joués en `--serve-only` contre le backend e2e, `--grep E2E-RECEIPT`, `--retries 0` :
  - mobile : MR-a (bug d'origine, bandeau sur `requestReadReceipt`) → 3 rouges sur « l'accusé est proposé » ; MR-b (refus no-op) → RECEIPT-003 rouge sur l'appel jamais émis ; vert : **3 passed** ;
  - weda2 : MA-a (aucune proposition) → 3 rouges sur « l'accusé est proposé » ; MA-b (refus no-op) → RECEIPT-003 rouge sur l'appel jamais émis ; vert : **3 passed** ;
  - chaque mutation : marqueur `MUTATION` = 1, nouveau bundle servi sans erreur, 15 s de rechargement (convention `mutation-non-servie`). Trou du filet consigné dans `conventions/e2e.md` ; `preuve-par-mutation` → 5 occurrences.
  - Premier passage mobile (avant correction du helper) : RECEIPT-002 et 003 rouges à cause du filtre `ActionType` ignoré par le serveur (le décompte comptait aussi `MailRead` / `MailReceive`) — helper corrigé, puis seed neuf.
- **Stitch** : non invoqué — aucun écran mobile créé ni refait (bouton ajouté au bandeau existant de task-105).
- **Passe qualité (/simplify)** :
  - Applied & committed : api-mail : 1 fichier (`1b69a58c`, chargement du mail commun aux deux actions d'accusé) ; client-blazor : 1 fichier (`5106fa6`, appel d'accusé commun à l'envoi et au refus) ;
  - No change : client-mobile, client-angular ;
  - Skipped (contract) : dtos-mss.
- **Contrôles mécaniques §Q 2b** : 5 commentaires « … ; » (S125) réécrits avant le push, `conventions/csharp.md` S125 → 15 occurrences.
- **DOD self-check** : build/tests ✓ (hors 3 rouges horaires préexistants) ; I1 à I10 présents et vus rouges ; tests unitaires et de composants ✓ (api-mail, mobile, Angular, Blazor) ; `data-testid` ✓ ; e2e : catalogue, seed, 3 scénarios × 2 clients, prouvés rouges puis verts — le passage complet par `/e2e` et la porte `gate` reste à faire par l'étape `/e2e` ; aucune adresse dans les journaux de `MdnService` (I8) ; aucun envoi ni refus sans geste du PS.
- **Next step** : `/sonar task-340`

## Sonar log

- Mode A (chaîné), serveur SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`, période de code neuf : 30 jours (depuis le 2026-09-11).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,1 % (cible 95 %).
- Phase 1 — Issues fixées : 1 code smell (CA1859, helper de test `DeleteFolderAsync` de task-340, `b41550d0`). 0 bug, 0 vulnérabilité, 0 hotspot.
- Phase 1 — Constat restant, **hors code de la task** : S107 sur `SemanticSearchService.cs:395` (créé le 2026-10-02 par task-329), déjà dans la baseline et laissé pour le même motif par les tasks 351 à 355 et 367.
- Phase 1 — Tests ajoutés : 0 (couverture du code neuf déjà au-dessus de la cible).
- Phase 2 (legacy) : non jouée — baseline saine (A/A/A, 0 bug, 0 vulnérabilité, couverture 97,9 %) ; best-effort.
- Build / tests : ✓ (Release, 2 analyses complètes) ; mêmes 3 rouges horaires préexistants (`…Today…`, fenêtre 00:00–02:00, cf. Develop log).
- `conventions/csharp.md` : CA1859 → 8 occurrences.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,3 % | 97,1 % | −0,2 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 |
| Coverage (projet) | 97,9 % | 97,9 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- client-angular (code-only, branche `feature/nova-rewriting-mss-weda-integration`) : lint ciblé sur les 11 fichiers .ts/.html de la task (contournement consigné par task-367 : `nx affected` ne se restreint pas à `tag:scope:mss` et couvre toute la branche Nova de l'humain — aucun `--fix` global).
- Baseline : **0 erreur** ; 29 avertissements sur ces fichiers, **0 sur les lignes ajoutées par la task** (attribution par `git diff -U0 HEAD`) — les 2 seules notices attribuées sont « fichier ignoré » pour deux `.spec.ts` exclus par la configuration ESLint.
- `nx run-many -t lint --projects=mss,mss-lib,mss-e2e` : 0 erreur (avertissements tous antérieurs).
- Itérations : 0 (rien à corriger) ; aucun fichier modifié, build et tests de `/develop` toujours valables (weda2 build ✓, `npm test` 11 projets ✓).
- Git : aucune opération (code-only).

## Lint mobile log

- Branche `fix/task-340-accuse-de-lecture`, arbre propre.
- Baseline `npm run lint` : **All files pass linting** (0 erreur, 0 avertissement).
- Fichiers e2e (hors cible `ng lint`) : `ESLINT_USE_FLAT_CONFIG=false npx eslint e2e/specs/functional.spec.ts e2e/support/e2e-backend.ts` propre pendant `/develop`.
- Itérations : 0 ; aucun commit (rien à corriger).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ❌ rouge | 33 verts, 0 flaky, 1 rouge (E2E-AI-001, rouge aux deux essais), 0 quarantaine | 6 min 30 s |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 37 verts, 1 flaky (E2E-COMPOSE-001), 0 rouge, 1 quarantaine (E2E-COMPOSE-002, posée par l'humain) | 5 min 58 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-340-accuse-de-lecture` (E2E-RECEIPT-001/002/003 v1, mobile et Angular requis)
- Quarantaines : E2E-COMPOSE-002 (angular), correction : task-350
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (`mail-detail` mobile et weda2 : specs e2e modifiés)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- Verdict : **ROUGE** — motif « régression » probable, introduite par la task : voir `questions/task-340.md`. Chaîne arrêtée avant `/review`.

**E2E : ROUGE** — 1 motif(s) de blocage.

**Bloquant** (1) :

- [mobile] rouge : « assistant — résumé initial puis deux questions de suite, conversation relue du serveur » (E2E-AI-001)

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « rédaction — envoyer, recevoir, lire, supprimer » (E2E-COMPOSE-001)

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
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ⚠️ flaky | ✅ |
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
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ❌ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

### Reprise de /develop après /e2e rouge (questions/task-340.md)

- Cause confirmée : E2E-RECEIPT-001 laissait son message et E2E-RECEIPT-002 l'accusé « Lu: … » en tête de boîte ; l'appui long d'E2E-AI-001 (mobile) tombait sous la barre d'onglets.
- Correctif (tests e2e seulement) : `removeFromInbox` (suppression puis départ relu au serveur, en `finally` pour RECEIPT-001), mobile `e2ff73f` (poussé) et weda2 (non commité, même fichier `e2e/mss-e2e/specs/functional.e2e.ts`).
- Preuve : seed neuf, `--grep "E2E-RECEIPT|E2E-AI-001"` dans l'ordre de la suite → **4 passed** (E2E-AI-001 vert derrière les parcours RECEIPT) ; sans le nettoyage, E2E-AI-001 était rouge aux deux essais de la voie complète.
- Type-check et lint des deux suites e2e : propres. Aucun changement d'api-mail, de dtos-mss ni de client-blazor dans cette reprise.

- Seconde passe (reprise après /e2e) : api-mail inchangé depuis l'analyse précédente (HEAD `b41550d0`, arbre propre), Quality Gate toujours OK — pas de nouvelle analyse, KPIs ci-dessus valables.
- Seconde passe (reprise après /e2e, `functional.e2e.ts` modifié) : 0 erreur, 0 constat sur les lignes de la task ; itérations 0.
- Seconde passe (reprise après /e2e) : `npm run lint` → All files pass linting ; e2e (`functional.spec.ts`, `e2e-backend.ts`) propres ; itérations 0, aucun commit.

## E2E log — seconde passe (après correctif, fait foi)

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ✅ verte | 34 verts, 0 flaky, 0 rouge, 0 quarantaine | 6 min 11 s |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 38 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, posée par l'humain) | 5 min 19 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-340-accuse-de-lecture`
- Quarantaines : E2E-COMPOSE-002 (angular), correction : task-350
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- Première passe (rouge, E2E-AI-001 mobile) : cause et correctif au `## Develop log` (« Reprise de /develop »).

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
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- dtos-mss : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/45 [awaiting-human-merge]
- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/290 [awaiting-human-merge]
- client-blazor : https://github.com/codengine-technologies/HealthPlatform.Client/pull/94 [awaiting-human-merge]
- client-mobile : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/91 [awaiting-human-merge]
- client-angular : code-only — humain gère commit/push TFS et ouverture PR, **avant le merge de la PR api-mail** (tests des scénarios requis E2E-RECEIPT-001/002/003). Branche `feature/nova-rewriting-mss-weda-integration`, fichiers :
  - front/e2e/mss-e2e/specs/functional.e2e.ts
  - front/e2e/mss-e2e/support/e2e-backend.ts
  - front/libs/mss/src/core/models/audit.model.spec.ts
  - front/libs/mss/src/core/models/audit.model.ts
  - front/libs/mss/src/core/models/mail.model.ts
  - front/libs/mss/src/core/services/mss-api.service.ts
  - front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html
  - front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.scss
  - front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts
  - front/libs/mss/src/core/utils/read-receipt.util.spec.ts (nouveau)
  - front/libs/mss/src/core/utils/read-receipt.util.ts (nouveau)
  - front/libs/mss/src/features/mail/components/mail-detail/mail-detail.read-receipt.spec.ts (nouveau)
  - front/libs/design-system/src/tokens/variables/component/_form-control.scss (ajouté après la revue : `--ds-toggle-width-sm` référençait `--ds-spacing-7`, absent de l'échelle — tout interrupteur `size="small"` faisait 0px, dont « Accusé de lecture » de la rédaction)

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 3 suggestions.

- **api-mail** — `MdnService` : une trace `ReadReceiptSend` par tentative (succès dès l'acceptation SMTP, échec de connexion → 503 tracé, adresse invalide → 400 tracé), auteur = praticien, plus d'adresse dans les journaux, MDN RFC 8098 (`multipart/report`) ✅. `MailDataContext` : `ReadReceiptSentAt` / `ReadReceiptDeclinedAt` en `timestamp without time zone` (AUD-32) ✅. `SmtpService` : `Disposition-Notification-To` ajouté, `Return-Receipt-To` inchangé ✅. `EmailAddressHelper.ParseReadReceiptAddress` : utilisé pour le seul MDN, l'envoi classique garde son adressage ✅. `MarkReadReceiptDeclinedAsync` : écriture conditionnelle atomique + relecture des copies suivies ✅. Migration `AddReadReceiptDeclinedAt` : nullable, sans défaut, `Down` symétrique, jouée `Up`/`Down`/`Up` en test ✅. Contrôleur : `declinereadreceipt` symétrique de `sendreadreceipt`, chargement commun ✅.
- **dtos-mss** — `AuditActionType.ReadReceiptDeclined = 41` (ordinal explicite), `MailDto.ReadReceiptDeclinedAt` ✅. Miroirs : contrat figé (api-mail), rétention, Angular, Blazor ✅.
- **client-blazor** — `ReadReceiptResponder` (Oui / Non / fenêtre fermée) testé hors de la fenêtre Radzen ; libellés 39, 40 et 41 ✅.
- **client-mobile** — le bandeau suit `readReceiptTo` / `readReceiptSentAt` / `readReceiptDeclinedAt` (il dépendait de `requestReadReceipt`, jamais renseigné pour un mail reçu), « Ne pas envoyer », 409 traité en information ✅.

**Règle 1b — comportement → test d'intégration → preuve rouge** (détail au Develop log) :

| Comportement | Test d'intégration (pile réelle) | Preuve rouge |
|---|---|---|
| Enregistrement de l'envoi (AUD-32) | `MarkReadReceiptSentAsync_PersistsTheTimestamp_AndItIsReadBack`, `TheEfModel_WritesAndReadsBothDates_OnTheProductionSchema`, I5 | M1 |
| Demande RFC 8098 à l'envoi (AUD-43 a) | `AMessageSentWithAReadReceiptRequest_CarriesDispositionNotificationTo_AndKeepsReturnReceiptTo` | M2 |
| Adresse analysée, nom conservé (AUD-43 b) ; MDN RFC 8098 ; 409 au second envoi | `AReceiptRequestedWithADisplayName_IsSentOnce_InRfc8098_ToTheParsedAddress_RecordedAndTraced` | M3, M4 |
| Adressage classique intact | `ARegularSend_ToARecipientWithADisplayName_KeepsTheDisplayName` | — (non-régression) |
| Trace : succès, 503, 400, auteur | I5, `AMailServerThatCannotBeReached_Is503_…`, `AnUnusableReceiptAddress_Is400_…` | M6, M7 |
| Enregistrement refusé après envoi | `WhenTheDatabaseRefusesTheRecordAfterTheSend_…` (trigger Postgres) | M5 |
| Aucune adresse dans les journaux | I5, I7 (capture globale prouvée non vide) | M9 |
| Refus définitif, tracé, sans message | `DecliningAReceipt_RecordsItForGood_…`, `DecliningAfterTheReceiptWasSent_Is409_…`, `DecliningAReceiptWithAnUnusableAddress_…` | M8, M10, M11 |
| Mail synchronisé en fond | `AMailSyncedInTheBackground_CanHaveItsReceiptSent_AndRecorded` | M1 |

**Suggestions (non bloquantes)** :
1. Un en-tête d'accusé fait uniquement d'espaces passe la garde `IsNullOrEmpty` du contrôleur et finit en 500 (comportement antérieur, inchangé) : une garde `IsNullOrWhiteSpace` le rendrait en 400.
2. Défaut préexistant relevé : `PostgresAuditReader.ApplyFilters` ignore `ActionType` et `Search` — le filtre par type d'action de l'écran d'audit est sans effet. Task à ouvrir.
3. Filet e2e mobile : `gestureBox` fait défiler une ligne sous la barre d'onglets Ionic ; un parcours qui laisse des messages décale les suivants (cause du rouge E2E-AI-001 de la 1re passe, corrigé ici par le nettoyage des parcours).

Validation /review : build + tests verts sur les 5 repos — api-mail (domain 190, infrastructure 683, application 3 617, api 1 199, intégration 863 + 16 ignorés, les 3 tests « du jour » verts hors fenêtre horaire), client-blazor 437, client-mobile 1 027, client-angular (weda2 build, npm test 11 projets), dtos-mss build. Branches à jour avec `origin/develop` (aucun commit en retard), aucun changement non commité sur les repos poussables.

## Merged

- **Date** : 2026-10-13, `/merge task-340 --i-tested` (validation humaine attestée).
- dtos-mss : squash `49dab080` (PR #45) — CI develop : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/38388747608
- api-mail : squash `87e972a5` (PR #290) — CI develop : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38388766325
- client-blazor : squash `97de370b` (PR #94) — CI develop : https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/38388785697
- client-mobile : squash `f992de71` (PR #91) — CI develop : https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/38388805248
- Branches `fix/task-340-accuse-de-lecture` supprimées (distante et locale) sur les quatre dépôts ; label `awaiting-human-merge` retiré.
- client-angular : managed manually by the human (TFS).
