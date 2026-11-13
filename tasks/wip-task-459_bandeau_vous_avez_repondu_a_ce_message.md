# todo-task-459.md — Bandeau « Vous avez répondu à ce message le… »

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 2
**Dependencies**: aucune
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Savoir, en ouvrant un message, qu'on y a déjà répondu
évite de répondre deux fois et de rouvrir Envoyés. En boîte partagée, c'est savoir qu'un collègue l'a fait.

> **Origine.** Demande explicite de l'humain du 2026-11-11 : « un bandeau qui s'affiche sur un mail dont la réponse a
> été faite : *Vous avez répondu à ce message le…* ».

## Ce qui est établi

- Les messages envoyés sont en base. Le dossier Envoyés est synchronisé, et l'archivage d'un envoi fait par la
  plateforme passe par `SentArchiveDispatcher` puis `ImapService.AppendToSentAsync`.
- `Mail.InReplyTo` et `Mail.References` sont stockés, avec l'index `IX_Mails_InReplyTo`.
- `MailRepository.GetThreadAsync` calcule déjà `HasReplies = Mails.Any(m => m.InReplyTo == messageId)`.
- `Mail.IsAnswered` (drapeau IMAP `\Answered`) existe. Il ne donne ni la date ni l'auteur, et les drapeaux ne sont
  relus que pour les nouveaux UID.
- L'envoi « pour le compte de la boîte » (E020 F006) pose l'en-tête `Sender` au nom du délégataire. La trace d'audit
  `MailReply` porte la personne réelle.
- Piège : un accusé de lecture ou un rapport de distribution entrant peut porter `In-Reply-To`. Il ne doit jamais
  compter comme une réponse.

## Objective

En ouvrant un message auquel la boîte a répondu, le lecteur voit un bandeau :
- **« Vous avez répondu à ce message le {date} à {heure} »**, si c'est lui ;
- **« {Prénom NOM} ({rôle}) a répondu à ce message le {date} à {heure} »**, si c'est une autre personne de la boîte ;
- **« Une réponse a été envoyée le {date} à {heure} »**, si la réponse est partie d'un autre logiciel et que l'auteur
  n'est pas connu.

Règles :
- **Lien « Voir la réponse »** : il ouvre le message envoyé.
- **Plusieurs réponses** : le bandeau montre la dernière et le nombre total (« … le 12/11 à 10 h 14 — 2 réponses »).
- **Ce qui compte comme réponse** : un message de la boîte, envoyé (dossier Envoyés), dont `In-Reply-To` ou
  `References` désigne ce message. Les accusés de lecture et les rapports de distribution sont exclus.
- **Dans la liste** : une icône « répondu » sur la ligne (weda2 et mobile), avec la même info au survol ou à l'appui
  long.
- **Drapeau IMAP** : une réponse envoyée par la plateforme pose `\Answered` sur le message d'origine, si ce n'est déjà
  fait. À vérifier, et à poser si c'est absent.
- **Transfert** : hors périmètre de cette task.

## Definition of Done

- [ ] Contrat : dernière réponse (date, auteur connu ou non, identifiant du message envoyé) et nombre de réponses dans
      `MailDto` ; paquet DTO publié.
- [ ] Auteur de la réponse établi par la trace `MailReply` (personne réelle) ou l'en-tête `Sender` ; jamais la boîte
      quand l'auteur réel est connu (règle 14).
- [ ] Tests unitaires : réponse par `In-Reply-To`, réponse par `References` seul, accusé de lecture exclu, rapport de
      distribution exclu, deux réponses, auteur inconnu.
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur `GET api/v1/Mail/folders/{f}/emails/{ids}` :
      - après une réponse envoyée par la plateforme (GreenMail et Dovecot), le message d'origine expose la date, la
        personne et le nombre de réponses, et porte `\Answered` côté IMAP ;
      - cas d'échec : un accusé de lecture entrant portant `In-Reply-To` ne crée **pas** de réponse.
      Vu rouge.
- [ ] **Deux personnes sur la même boîte** : le délégataire répond ; le titulaire lit « {délégataire} (délégataire) a
      répondu ».
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : les trois libellés, « Voir la réponse »,
      plusieurs réponses, icône dans la liste.
- [ ] **Scénario e2e** `E2E-DETAIL-006` v1, mobile et angular requis, vu rouge : répondre à un message, revenir sur le
      message d'origine, le bandeau « Vous avez répondu à ce message le … » est là, et « Voir la réponse » ouvre
      l'envoi.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les libellés ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend, weda2 et mobile sur la boîte de formation.
2. weda2 : répondre à un courrier. Revenir sur le courrier : « Vous avez répondu à ce message le … à … », avec « Voir
   la réponse » qui ouvre l'envoi. La ligne de la liste porte l'icône « répondu ».
3. Mobile, délégataire de la même boîte : ouvrir ce courrier : « {nom du titulaire} (titulaire) a répondu … ».
4. Répondre au même message depuis le webmail de l'opérateur, puis synchroniser : « Une réponse a été envoyée le … —
   2 réponses ».
5. Ouvrir un message dont seul un accusé de lecture est revenu : aucun bandeau.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes rattachées à la boîte sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable — en-têtes RFC 5322 (`In-Reply-To`, `References`) et RFC 3501 (`\Answered`)
- **Tracé PGSSI-S** : inchangé — l'envoi est déjà tracé (`MailReply`) au nom de la personne réelle
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé — l'auteur d'une réponse est déjà visible dans le journal de la boîte (E020)

## Branches
- `api-mail` (pushed) : feat/task-459-bandeau-vous-avez-repondu-a-ce-message — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-459-bandeau-vous-avez-repondu-a-ce-message
- `client-mobile` (pushed) : feat/task-459-bandeau-vous-avez-repondu-a-ce-message — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-459-bandeau-vous-avez-repondu-a-ce-message
- `dtos-mss` (pushed, créée par /develop) : feat/task-459-bandeau-vous-avez-repondu-a-ce-message — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-459-bandeau-vous-avez-repondu-a-ce-message
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

- Repos touched : dtos-mss, api-mail, client-mobile, client-angular (code-only)
- DTOs published : 597.0.0 → **605.0.0** (`MailReplySummaryDto`, `MailDto.Reply`, `MailDto.IsReport`) → **606.0.0**
  (`MailDto.Reply` en `JsonIgnore(WhenWritingNull)`, voir « Trou attrapé par l'e2e »). Consommateur .NET : api-mail
  (client-blazor non listé, non bumpé).
- Interop / SDK : no change
- Commits :
  - dtos-mss : `e8a5043` feat(dto) dernière réponse + rapport ; `8ed9c81` fix(dto) Reply absent du JSON quand nul
  - api-mail : `dbe0426a` bump 605 ; `ff60ead8` bump 606 ; `7009d9da` feat(mail) « Vous avez répondu… »
  - client-mobile : `0a5ceee` feat(mobile) bandeau + icône + E2E-DETAIL-006 ; `e40e841` refactor simplify pass
  - client-angular (code-only, **non commité** sur `feature/nova-mss-weda-integration`, à committer par l'humain) :
    `front/libs/mss/src/core/models/mail.model.ts`, `core/utils/reply-summary.util(.spec).ts`,
    `features/mail/components/reply-banner/*` (nouveau), `mail-detail/mail-detail.component.{ts,html}`,
    `mail-detail/mail-detail.reply-banner.spec.ts`, `mail-header/mail-header.component.{ts,html,scss}`,
    `mail-header/mail-header.reply.spec.ts`, `mail-compose/mail-compose.component(.spec).ts`,
    `services/mail-event.service.ts`, `services/mail-state.service(.spec).ts`,
    `front/e2e/mss-e2e/specs/functional.e2e.ts`, `front/e2e/mss-e2e/support/e2e-backend.ts`
    (`conventions/e2e.md`, test-angular-non-commite : le test E2E-DETAIL-006 Angular vit dans cet arbre).

### Conception

- **Auteur réel (règle 14)** : table `MailReplies` dans la base de la boîte, écrite par `MailReplyRecorder` au moment
  où la réponse part (point unique `OutgoingMailService` : envoi direct, brouillon et confirmation hors ligne), avec
  l'identité imputée comme la trace `MailReply` (compte, RPPS PSC sinon rattachement, prénom, nom, rôle). Ancrée aux
  `Message-ID`, jamais à la ligne `Mails` (consigne `etat-metier-hors-du-miroir-imap`). Migration
  `20261113120000_AddMailReplies` relue (règle 7c) : création de table + 2 index + colonne `Mails.IsReport` défaut
  false, aucune opération fantôme ; le modèle EF déclare le même schéma (suite d'intégration bâtie depuis le modèle,
  verte).
- **Ce qui compte comme réponse** (`MailReplySummaries`, domaine) : réponses enregistrées + copies du dossier Envoyés
  (classification SPECIAL-USE ou nom). Parent = `In-Reply-To`, sinon le **dernier** `References` (RFC 5322 § 3.6.4) :
  répondre au 3ᵉ message d'un fil n'est pas répondre au 1ᵉʳ. Exclus : message reçu, `multipart/report` (MDN, DSN —
  colonne `Mails.IsReport`, posée à la lecture IMAP depuis BODYSTRUCTURE), « annule et remplace ». Auteur :
  l'enregistrement, sinon l'en-tête `Sender` de la copie (nom seul), sinon inconnu.
- **« Vous » est calculé par le serveur** (`IsByCurrentPerson`, compte ou RPPS de la personne qui lit).
- **`\Answered`** : `FlagChangeKind.MarkAnswered` + `PendingActionTypes.MarkAnswered` (file des drapeaux, rejouable),
  sur les copies locales du message d'origine pas encore marquées. Limite : un original jamais vu par la base (ni
  affiché ni enrichi) ne reçoit pas le drapeau.
- **« Voir la réponse »** : l'UID rendu par l'`APPEND` (UIDPLUS) est noté sur l'enregistrement, sinon la copie
  synchronisée fait foi. Les clients relisent l'en-tête si l'emplacement manque encore.
- Lu par `GET folders/{f}/emails/{ids}` (en ligne et hors ligne), une lecture par page. `GetThreadAsync.HasReplies`
  exclut aussi les rapports.

### Trou attrapé par l'e2e (écrit avec la fonctionnalité, avant tout commit)

`E2E-DETAIL-006` mobile rouge au premier essai : la liste servie portait `reply`, mais l'icône manquait. La
notification SSE `EmailsEnriched` (partagée par toute la boîte) sérialisait `"reply": null`, et les clients
**fusionnent** le message reçu sur leur ligne (le détail mobile le **remplaçait**). Correctif :
`[JsonIgnore(WhenWritingNull)]` sur `MailDto.Reply` (DTO 606) + fusion `{ ...current, ...enriched }` dans
`mail-detail.page.ts`. Prévention : `conventions/csharp.md` § `champ-par-lecteur-hors-des-notifications`.

### Preuves (règle 1b, tests vus rouges)

- **Intégration bout en bout** (`ReplyBannerEndToEndTests`, pile HTTP réelle, Dovecot + GreenMail, base de la boîte) :
  - `TheHolderReplies_TheOriginalTellsWhenWhoAndHowMany_AndIsAnsweredOnTheServer` : date UTC, personne, nombre,
    `\Answered` relu sur Dovecot, emplacement « Voir la réponse » = la copie archivée ;
  - `TheDelegateReplies_TheHolderReadsTheDelegateAsTheAuthor` : deux personnes sur la même boîte ;
  - `AReadReceiptCarryingInReplyTo_IsNotAReply_WhetherReceivedOrArchived` : cas d'échec, MDN reçu ET rangé dans
    Envoyés (prémisse : les deux lignes en base avec `IsReport`) ;
  - `AReplyFromAnotherSoftware_IsCountedWithoutAuthor_AfterThePlatformReply` : 2 réponses, auteur inconnu ;
  - `AReplySentFromItsDraft_IsRecordedTheSameWay` : chemin jumeau du brouillon.
- **Mutations api-mail** (script, restauration depuis copie, recompilation) : M1 enregistreur non appelé → 3 rouges ;
  M2 rapport compté → rouge MDN ; M3 auteur ignoré → 2 rouges ; M4 `\Flagged` au lieu de `\Answered` → rouge
  titulaire ; M5 emplacement non noté → rouge titulaire ; M6 résumé non appliqué (en ligne) → 3 rouges ; M7 rapport
  non détecté → rouge MDN. Après la passe qualité, le filtre `IsReport` existe en SQL **et** dans la règle (défense en
  profondeur) : M2 seul ne rougit plus, M7 (détection) rougit toujours.
- `AnEnrichmentNotification_CarriesNoNullReply_AndKeepsARealOne` : rouge sur le contrat 605 (sans l'attribut), vert
  sur 606.
- **Unitaires** : `MailReplySummariesTests` (In-Reply-To, References seul, ancêtre écarté, MDN, DSN, reçu, annule et
  remplace, deux réponses, auteur inconnu, Sender, lecteur), `MailReplyRecorderTests`, `MailReplySummaryServiceTests`,
  `OutgoingMailServiceTests` (réponse, nouveau message, échec, annule et remplace), `OfflineMailDataProviderTests`,
  `MailFolderNamingRuleTests.IsSentName`.
- **Composants mobile** (Karma) : `reply-summary.util.spec`, `mail-detail.reply-banner.spec` (à travers le détail),
  `mail-header.reply.spec`, compose (relecture après envoi direct et brouillon), `mail-detail.page.spec` (fusion
  d'enrichissement, adoption de la relecture). Mutations Mm1–Mm9 toutes rouges sur les tests prévus.
- **Composants Angular** (Vitest) : mêmes axes, plus `MailStateService.refreshReply` ; mutations Ma1–Ma7 rouges.
- **E2E-DETAIL-006 v1** (catalogue + mobile + Angular), joué seul sur `--serve-only` : vert. Mutations E1/EA1 bandeau
  absent, E2/EA2 icône absente, E3/EA3 « Voir la réponse » sans effet : rouges sur l'assertion prévue ; témoins verts.
  Les voies complètes restent jouées par `/e2e`.

### Builds / tests

- dtos-mss : build vert.
- api-mail : build 0 avertissement ; suite complète verte (domain 249, infrastructure 749, application 4241, api
  1380, integration 1287 + 16 ignorés pré-existants). Flaky pré-existant vu une fois puis vert 3/3 seul :
  `ImapServiceTests.GetFolderNotSeenAsync_HappyPath_TagsTheImapActivityWithPerCommandDurationsAsync` (étiquette
  d'Activity, chemin non touché).
- client-mobile : `npm run build` vert ; 1440/1440.
- client-angular : `nx build weda2` vert ; `nx test mss-lib` 146 fichiers verts ; ESLint 0 erreur et stylelint
  0 erreur sur les fichiers touchés.

### Passe qualité (/simplify, 4 angles : reuse, simplification, efficacité, altitude)

- Appliqué :
  - marqueur « annule et remplace » unique (`MailCancellationService` lit celui du domaine) ;
  - noms du dossier des envois séparés (`SentNames`, plus de `Take(10)`), segment partagé, `FolderType.Sent` au lieu
    d'un `1` en dur ;
  - `MailReplySummaries` : un seul suivi pour les deux sources, `SentAt` en une expression ;
  - dépôt : normalisation une seule fois, plus de pré-lecture avant l'insertion, mise à jour projetée
    (`ExecuteUpdate`), `In-Reply-To` cherché seul (index), `References` seulement sans `In-Reply-To`, rapports filtrés
    en SQL, dossier des envois résolu dans la requête ;
  - clients : une seule relecture (`MailActionsService.refreshReply` mobile, `MailStateService.refreshReply`
    Angular) pour la rédaction et « Voir la réponse » — corrige une dérive : le bandeau mobile ne prévenait pas le
    détail ouvert ; appui long de l'icône sur le minuteur de la ligne (mobile) ; un seul repli « pas encore rangée ».
  - api-mail : cleanups appliqués **avant** le premier commit de la fonctionnalité (pas de commit séparé), re-validés
    par la suite complète. mobile : `e40e841`. Angular : non commité.
- Écarté, noté pour l'humain :
  - colonne `ParentMessageId` indexée à la synchronisation (la recherche par `References` reste un parcours des
    envois sans `In-Reply-To`) ;
  - réutiliser les lots de liens de fil quand `includeThreadCounts=true` ;
  - drapeau pour ne pas calculer le résumé sur le chemin de l'accusé de lecture ;
  - sortir la note d'emplacement d'`ImapService` (changer la signature d'`AppendToSentAsync` toucherait 20 fichiers
    de tests) ;
  - poser le résumé côté client sans relecture (le serveur reste la vérité : nombre, lecteur, emplacement) ;
  - retirer les gardes `InReplyTo` / `MessageId` redondantes avec l'appelé (gardées : elles évitent un appel et un
    test les éprouve).
- Contrôles mécaniques §Q 2b : 7 S125 réécrits avant le premier commit (`conventions/csharp.md`, Occurrences 28) ;
  xUnit1051 corrigé au build (Occurrences 5, contrôle mécanique ajouté à `agents/develop.md` §Q 2b).

### Prévention (règle d'or)

- `conventions/csharp.md` : nouvelle entrée `champ-par-lecteur-hors-des-notifications` ; xUnit1051 → 5 ; S125 → 28.
- `conventions/e2e.md` : `mutation-non-servie` → 7 (import laissé inutilisé par une mutation weda2).
- `agents/develop.md` §Q 2b : contrôle mécanique xUnit1051 (`Received…(…, default)`).

### Hors périmètre / restes

- Stitch : aucun écran créé ni réécrit (bandeau et icône ajoutés à des écrans existants) — non invoqué.
- Transfert : hors périmètre (task).
- Les lignes `Mails` existantes gardent `IsReport = false` jusqu'à leur prochaine synchronisation (pas de reprise,
  bases de test).

- DOD self-check : contrat ✓ ; auteur réel ✓ ; unitaires (6 cas) ✓ ; intégration bout en bout vue rouge ✓ ; deux
  personnes ✓ ; composants weda2 + mobile vus rouges ✓ ; E2E-DETAIL-006 v1 mobile + angular vu rouge ✓ ; data-testid,
  libellés FR, aucune donnée de santé dans les libellés ni les journaux ✓ ; builds et tests ✓.
- Green marked : client-mobile `e40e8410`, client-angular (arbre), api-mail `7009d9da` (suite finale)
- Next step : /review task-459 --code

### Reprise 1 après /review (revue anticipée, passage 1)

- **B1 — annulation après un envoi réussi** : `OutgoingMailService` engage l'archivage « Envoyés » **avant**
  l'enregistrement de la réponse, et l'enregistrement reçoit `CancellationToken.None` ; `MailReplyRecorder` est
  best-effort annulation comprise. Test : `OutgoingMailServiceTests.SendAsync_AClientThatAbortsRightAfterTheSend_StillGetsItsReplyArchived`
  (jeton annulé dans l'envoi SMTP, enregistreur réel sur un dépôt qui honore le jeton) — **rouge sur le code d'avant**
  (`OperationCanceledException` remontée, archivage absent). Défense double : la mutation d'une seule couche (jeton
  annulable seul, ou filtre de capture seul) reste verte ; les deux ensemble (= code d'avant) rougissent.
  Note : test d'application et non HTTP, l'harnais ne sait pas couper la requête entre l'envoi et l'enregistrement de
  façon déterministe.
- **B2 — règle 1b, chaque route que le diff change** (`ReplyBannerEndToEndTests`, pile réelle, 11/11 verts) :

  | Comportement | Test | Mutation → rouge |
  |---|---|---|
  | (a) réponse par `References` seul (branche SQL `byReferences`) | `AReplyCarryingOnlyReferences_IsCounted` (prémisse : copie sans `In-Reply-To` en base) | Ra branche morte → ce test |
  | (b) lecture hors ligne | `ReadOffline_TheOriginalStillTellsWhoReplied` | Rb résumé non appliqué hors ligne → ce test |
  | (c) Envoyés désigné par SPECIAL-USE seul | `AReplyFiledInASentFolderKnownOnlyBySpecialUse_IsCounted` (prémisse du négatif : non classé → pas de réponse) | Rc classification ignorée → ce test (+2) |
  | (d) annule et remplace jamais une réponse | `ACancelAndReplace_IsNeverAReplyToTheMessageItCancels` (route `…/cancel-and-replace`, sujet prérempli, prémisse : copie rattachée par `In-Reply-To`) | Rd1 enregistré → rouge ; Rd2 marqueur de copie ignoré → rouge |
  | (e) `GET thread/{messageId}` : `HasReplies` hors rapports | `TheThreadOfAMessageOnlyAcknowledgedByAReadReceipt_HasNoReplies` (prémisse : fil de 2 avec l'accusé) | Re filtre retiré → ce test |
  | (f) `pending-emails/{id}/send` enregistre la réponse | `AReplySetAsideWithoutTheCard_ThenConfirmed_IsRecorded` (+ `\Answered` sur Dovecot) | Rfg enregistreur non appelé → ce test |
  | (g) preuve du brouillon | `AReplySentFromItsDraft_IsRecordedTheSameWay` | Rfg → rouge (7 tests rouges en tout) |

- **S4 — mobile, bouton bloqué** : `opening` passe en `signal` (composant OnPush). Test
  `mail-detail.reply-banner.spec.ts` « rend « Voir la réponse » de nouveau actif… » : rendu juste après le clic
  (désactivé), puis après la fin (actif) — rouge sur le champ simple (fichiers du correctif mis de côté), vert avec
  le signal. Commit `b2a9a01`.
- **S7 — rejeu `MarkAnswered`** : `FlagPropagationServiceTests` (persisté sous son nom, `STORE +FLAGS (\Answered)`),
  `PendingActionServiceTests.ProcessPendingActions_AMarkAnsweredLeftInTheQueue_IsReplayedByDirectPropagation`,
  `PendingActionTypesTests`. Mutations S7a (`\Flagged` au lieu de `\Answered`) et S7b (cas de rejeu absent) → rouges.
- **S8** : remarque de la migration corrigée (aucune mise à jour ne recopie `IsReport` ; effet borné).
- **Relecture du correctif comme correctif** : l'ordre archivage → enregistrement ne change pas ce que lit le client
  (l'archivage est en file, l'enregistrement reste dans la requête : le bandeau est là au retour). Le sujet d'un
  remplacement saisi sans marqueur compterait comme réponse côté copie, mais jamais côté enregistrement (le chemin
  annule-et-remplace n'enregistre rien) : couvert par Rd1/Rd2 ; noté pour l'humain.
- **Prévention** : `conventions/csharp.md` § `apres-envoi-reussi-rien-d-annulable` (nouveau), S125 → 29 ;
  `conventions/angular.md` § `etat-asynchrone-onpush-en-signal` (nouveau).

### Reprise 2 après /review (revue anticipée, passage 2)

- **N1 — ordre enregistrement → archivage rétabli** (né du correctif B1 de la reprise 1) : l'archivage note
  l'emplacement de la copie sur la ligne `MailReplies` (`UPDATE`), la ligne doit donc exister avant la mise en file.
  `OutgoingMailService` enregistre la réponse d'abord (jeton `CancellationToken.None`, enregistreur qui ne lève jamais :
  B1 reste corrigé), puis met l'archivage en file. Test `OutgoingMailServiceTests.SendAsync_TheReplyIsRecordedBeforeItsArchiveIsQueued`
  (`Received.InOrder`) — **rouge sur l'ordre de la reprise 1**, vert après. `SendAsync_AClientThatAbortsRightAfterTheSend_StillGetsItsReplyArchived`
  reste vert. La course elle-même n'est pas reproductible en intégration (`DeterministicBackgroundTaskQueue` archive au
  drainage, après la requête) : l'ordre est figé par le test unitaire.
- **Relecture du correctif comme correctif** : un seul site changé (`SendAndArchiveAsync`), appelants inchangés
  (`sendmail`, brouillon, confirmation hors ligne, annule-et-remplace sans enregistrement) ; un enregistrement lent
  retarde l'archivage d'autant, jamais ne l'empêche. La consigne écrite à la reprise 1 (« l'archivage d'abord ») était
  fausse et aurait appris la course : corrigée.
- Suite complète api-mail verte (application 4248, intégration 1293 + 16 ignorés pré-existants). Commit `b87aa7cf`.
- **Prévention** : `conventions/csharp.md` § `apres-envoi-reussi-rien-d-annulable` réécrite (l'ordre suit les
  dépendances), Occurrences 2.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relu sur : api-mail `7009d9da`, dtos-mss `8ed9c81`, client-mobile `e40e841`, client-angular (arbre non commité sur
`feature/nova-mss-weda-integration`). Revue indépendante (sous-agent sans les conclusions de la forge) + verrou 4a.

**Ce qui tient** : modèle `MailReplies` ancré aux Message-ID, migration et modèle EF cohérents (7c) ; auteur réel pris de
l'identité de requête (règle 14), « vous » calculé par lecteur ; `JsonIgnore(WhenWritingNull)` + fusion côté clients ;
DI dans la racine de composition ; `ReplyBannerEndToEndTests` solide sur le chemin principal ; e2e jugés côté serveur ;
aucune donnée de santé dans libellés ni journaux. 4b : `E2E-DETAIL-006` v1 au catalogue, déclaré v1 dans les deux
clients.

**Verrou 4a (règle 1b) — comportement → test → preuve rouge**

| Comportement atteignable | Test d'intégration | Preuve rouge |
|---|---|---|
| `GET …/emails/{ids}` (en ligne) : nombre, date, auteur, « vous », emplacement | `TheHolderReplies…`, `TheDelegateReplies…`, `AReplyFromAnotherSoftware…` | M1, M3, M5, M6 |
| Rapports (MDN) exclus | `AReadReceiptCarryingInReplyTo…` | M7 |
| `POST sendmail` → `\Answered` sur Dovecot | `TheHolderReplies…` | M4 |
| `POST drafts/{id}/send` enregistre la réponse | `AReplySentFromItsDraft…` | **manquante** (test écrit après les mutations) |
| Réponse par `References` seul (branche SQL distincte) | — | — |
| `GET …/emails/{ids}` hors ligne | — (unitaire seul) | — |
| Dossier Envoyés reconnu par SPECIAL-USE seul | — | — |
| `POST …/cancel-and-replace` : jamais une réponse | — (unitaire seul) | — |
| `GET thread/{messageId}` : `HasReplies` exclut les rapports | — | — |
| `POST pending-emails/{id}/send` enregistre la réponse | — | — |

#### À corriger par la reprise

- **B1 ❌ Annulation après un envoi réussi** (`OutgoingMailService.SendAndArchiveAsync`, `MailReplyRecorder`) :
  l'enregistrement de la réponse s'intercale entre le succès SMTP et la mise en file de l'archivage, avec le jeton de
  la requête ; le recorder laisse passer `OperationCanceledException`. Un client qui se déconnecte à cet instant :
  pas de copie dans Envoyés, et sur `pending-emails/{id}/send` (`ReleasePendingEmailAsync`) ou l'envoi d'un brouillon,
  un message parti redevient envoyable (double envoi). Casse l'invariant task-272 / task-330. Correctif : archivage mis
  en file **avant** l'enregistrement, enregistrement non annulable par le client ; test qui annule le jeton après
  l'envoi et constate l'archivage engagé, vu rouge.
- **B2 ❌ Règle 1b** — un test d'intégration bout en bout, vu rouge, pour chacun :
  (a) réponse par `References` seul (branche `byReferences` sur PostgreSQL) ; (b) lecture hors ligne ;
  (c) dossier des envois reconnu par sa seule classification SPECIAL-USE (nom qui ne dit pas « Sent ») ;
  (d) annule et remplace : aucune réponse comptée ni enregistrée ; (e) `GET thread/{messageId}` : `HasReplies`
  n'est pas allumé par un accusé de lecture ; (f) `pending-emails/{id}/send` : la réponse confirmée est enregistrée ;
  (g) preuve rouge du test du brouillon (mutation M1 rejouée).
- **Mêmes passe, défauts réels (non bloquants)** :
  - S4 — mobile : « Voir la réponse » reste désactivé après l'avis « pas encore rangée » (`opening` champ simple sous
    `OnPush`, jamais re-vérifié) : signal, et test qui relit le bouton actif ;
  - S7 — rejeu `MarkAnswered` (`PendingActionService`) et correspondance `FlagPropagationService.Describe` non testés ;
  - S8 — remarque de la migration inexacte (« se corrigent à leur prochaine synchronisation » : aucune mise à jour ne
    recopie `IsReport`).

#### Arbitrage humain

- **A1 (S5)** — l'icône et le bandeau ne sont calculés que pour la liste d'un dossier (`GET …/emails/{ids}`) : ni la
  liste par étiquette, ni les résultats de recherche. Recommandation : accepter pour cette US (la DOD vise la liste du
  dossier), task de suite si souhaité.
- **A2 (S6)** — `\Answered` n'est posé que si le message d'origine est déjà en base (affiché ou enrichi) ; une réponse
  à un message jamais vu par la base ne pose pas le drapeau (le bandeau, lui, fonctionne). Recommandation : accepter
  (les clients enrichissent toute ligne affichée) ; repli IMAP `SEARCH HEADER Message-ID` en task de suite sinon.
- **A3 (S9)** — une réponse connue seulement par sa copie (autre logiciel, délégataire depuis un autre client) n'est
  jamais « Vous » : le lecteur peut lire son propre nom (« X a répondu »). Recommandation : accepter, le dire dans la PR.
- **A4 (S3)** — coût sur le chemin chaud : deux requêtes par page, y compris `includeThreadCounts=false` (task-266 les
  avait ramenées à zéro), et la branche `References` parcourt les envois. Recommandation : mesurer au banc ; colonne
  `ParentMessageId` indexée en task de suite.

### Passage 2 (revue anticipée, après reprise 1) — CHANGES REQUESTED

Relu sur : api-mail `6b88dfb4`, client-mobile `b2a9a01`, client-angular (arbre inchangé). Le diff de la reprise lu
**d'abord**, pour ce qu'il a cassé (revue indépendante).

**Constats du passage 1** : B1 ✓, B2 (a) ✓, (b) ✓, (c) ✓, (d) ✓, (e) ✓, (f) ✓, (g) ✓, S4 ✓, S7 ✓, S8 ✓ — chaque test
emprunte la route ou la branche nommée, sa prémisse est affirmée, et sa mutation le rougit.

#### À corriger par la reprise

- **N1 ❌ (né du correctif B1)** — `OutgoingMailService.SendAndArchiveAsync` met désormais l'archivage en file **avant**
  l'enregistrement de la réponse. Or l'archivage dépend de l'enregistrement : après l'`APPEND`,
  `ImapService.TryAppendToSentAsync` → `MailReplyRepository.RecordSentCopyAsync` est un `UPDATE … WHERE SentMessageId`
  (pas un upsert), seule voie par laquelle le serveur apprend `SentFolderPath` / `SentUid` avant la synchronisation
  d'Envoyés. En production la file de fond dépile aussitôt : si l'`APPEND` + `UPDATE` passent avant l'`INSERT` de la
  requête (pool Npgsql froid de la boîte, pool occupé, Dovecot local), l'emplacement est perdu — « Voir la réponse »
  répond « Réessayez dans un instant » jusqu'à la synchronisation, et `E2E-DETAIL-006` peut rougir par intermittence.
  Invisible aux tests : `DeterministicBackgroundTaskQueue` n'exécute l'archivage qu'au `DrainBackgroundQueueAsync`.
  L'ordre n'apportait rien à B1, déjà corrigé par le jeton non annulable et la capture totale de l'enregistreur.
  Correctif : rétablir enregistrement → archivage (en gardant `CancellationToken.None` et la capture totale), et un
  test qui fige l'ordre (`Received.InOrder`), vu rouge sur l'ordre actuel.

#### Arbitrage humain (en plus de A1–A4 du passage 1)

- **A5** — `DraftService` (pré-existant, hors task-459) : après un envoi réussi, la suppression du brouillon prend le
  jeton de la requête ; un client qui abandonne à cet instant garde le brouillon (même classe de risque que B1).
  Recommandation : task de suite, hors de cette US.
- Note pour la PR : B2 (c) pose la classification `MailFolders.FolderType` en base (le comportement changé est la
  requête qui la lit ; le listage SPECIAL-USE des dossiers est pré-existant).

### Passage 3 (revue anticipée, après reprise 2) — APPROVED

**Approved at** : api-mail `b87aa7cf`, dtos-mss `8ed9c81`, client-mobile `b2a9a01`, client-angular arbre non commité
sur `feature/nova-mss-weda-integration` (inchangé depuis le marqueur vert de `/develop`).

Revue indépendante du diff de la reprise 2 (lu d'abord) : N1 corrigé ✓ (l'`INSERT` est validé avant la mise en
file ; `Received.InOrder` rouge sur l'ordre de la reprise 1) ; B1 toujours corrigé ✓ (jeton non annulable +
capture totale de l'enregistreur : rien ne lève après le succès SMTP, la confirmation hors ligne ne se relâche plus).
Appelants vérifiés : `sendmail`, brouillon, `pending-emails/{id}/send`, annule-et-remplace (sans enregistrement).
Aucun bloquant.

**Suggestions (non bloquantes, pour la PR)** :
- aucun test ne fige `CancellationToken.None` sur l'enregistrement (B1 resterait sûr grâce à la capture, mais un
  abandon client perdrait l'auteur et `\Answered` de cette réponse) ;
- la mise en file de l'archivage attend désormais les écritures de l'enregistrement (au plus quelques secondes,
  bornées par les délais Npgsql) : prix de l'ordre qu'exige N1 ; si le processus meurt dans cette fenêtre, la copie
  « Envoyés » n'est pas faite (avant task-459, la mise en file suivait directement le SMTP).

**Arbitrages humains ouverts** : A1–A5 (passages 1 et 2), à trancher au merge.

## Timings

*(généré par `tools/timing/report.sh --task task-459 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 50 s | — | — | — | — |
| /develop | ok | 10 min 27 s | 18 (8 min 34 s) | 13 (50 min 53 s) | — | dtos-mss 2B/0T, api-mail 11B/6T, client-mobile 3B/4T, client-angular 2B/3T, reprise 2 |
| /review-code | ok | 3 min 31 s | — | — | — | — |
| **Total cycle** | | **14 min 49 s** | **18 (8 min 34 s)** | **13 (50 min 53 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×2 (31 s), restore ×2 (15 s)
