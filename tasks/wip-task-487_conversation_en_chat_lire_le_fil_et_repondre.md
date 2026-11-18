# todo-task-487.md — Conversation en chat : lire le fil et répondre

**Repos**: api-mail, dtos-mss, client-mobile, client-angular
**Reprises**: 2
**Dependencies**: none
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-17. Un échange entre confrères se lit aujourd'hui message
par message, avec l'historique recopié dans chaque réponse. Le médecin veut le lire comme une messagerie
instantanée et répondre en une ligne, sans ouvrir la rédaction.

> **Maquette** (Claude Design, Weda Design System) : https://claude.ai/artifact/Kr2n5sEFfrbeWkcU7c1yyC
> — écran mobile interactif, planche « États d'un message » (9 états), écran weda2. Pour le mobile, `/stitch-design`
> la reprend : Stitch reste la référence de design de `client-mobile`.

> ⚠️ **Taille.** US large : contrat de conversation, réponse composée par le serveur, découpage de la citation, état
> des accusés, deux clients. La PR `api-mail` risque de dépasser ~30 fichiers (règle 5). Si c'est le cas, `/develop` le
> signale dans le `## Develop log` ; la règle 11 interdit de livrer une partie de l'US.

## Décisions humaines (2026-11-17)

1. **Une seule US** pour le mobile et weda2.
2. **Envoi** : sur weda2, Entrée envoie et Maj+Entrée va à la ligne. Sur mobile, Entrée va à la ligne et la flèche
   envoie.
3. **Aucun délai d'annulation** : le message part dès l'appui.
4. **Destinataires par défaut** : tous les participants du fil (répondre à tous), toujours affichés au-dessus de la
   saisie.
5. **Ouvrir une conversation marque tous ses messages comme lus**, et chaque lecture est tracée au nom de la personne
   réelle (règle 14).
6. **Joindre un document dès cette US** : un fichier, ou un document du dossier patient.
7. **L'état « distribué » et « lu » sous les bulles entre dans cette US.**
8. **Une réponse du chat ne demande jamais d'accusé de lecture.** « lu » n'apparaît que si le correspondant en envoie
   un de lui-même.

## Ce qui est établi

- **Le fil existe** : `GET api/v1/mail/thread/{messageId}` (`MailController.cs:1937`) rend tout le fil, trié par date,
  dossier Envoyés compris (task-268, `MailRepository.GetThreadAsync`, `MailRepository.cs:4397`). Les accusés ne
  comptent pas comme réponses (task-459). Mais chaque élément (`MailThreadItemDto`) ne porte que uid, dossier,
  Message-ID, objet, expéditeur, date et lu : **ni corps, ni pièces jointes, ni sens, ni auteur réel, ni état**.
- **Le mode Conversation** (task-108 sur mobile, weda2 à parité) regroupe la liste par fil et déplie des lignes
  d'en-têtes. Il n'affiche aucun corps.
- **La réponse sait rester dans le fil** côté client : la rédaction mobile pose `In-Reply-To` et `References`, cite
  l'historique (`buildQuote`) et ajoute la signature (`mail-compose.component.ts:474-515`).
- **L'auteur réel d'une réponse est connu** : trace `MailReply` (personne réelle) ou en-tête `Sender` (task-459,
  `MailReplyRecorder`, `MailReplySummaries`). Réutilisable pour la bulle.
- **Les accusés reçus sont seulement marqués** `IsReport` (`Mail.cs:139`). La plateforme sait **émettre** un accusé de
  lecture (`MdnService`, RFC 8098), mais **rien ne lit les accusés reçus** pour en déduire qu'un message envoyé a été
  distribué ou lu. Vérifié le 2026-11-17 : `grep -rln "Original-Message-ID\|delivery-status\|disposition-notification"
  Api/Mail/src` ne rend que des sites d'émission (`MdnService`) ou de construction de `References`
  (`MailCancellationService`), aucun site de lecture.
- **Hors ligne sans carte** : un envoi sans e-CPS est « prêt à partir » et attend la confirmation par la carte
  (task-320). **Erreurs** : code et référence affichés (task-421).
- **api-mcp n'est pas touché** : `python Tools/contracts/mcp_impact.py surface` montre qu'il lit `MailDto`, les dossiers,
  les boîtes et la recherche, jamais le fil. L'US ajoute des routes et ne retire rien.

## Objective

Le médecin ouvre un échange en **vue chat** : chaque message est une bulle, les siens à droite, ceux des autres à
gauche, du plus ancien au plus récent. Il répond dans une zone de saisie en bas de la vue, et sa réponse part comme un
vrai email, sans passer par la rédaction.

### Lire

- **Entrées** : toucher une conversation en mode Conversation ouvre la vue chat ; dans un message ouvert, « Voir en
  conversation ». Depuis le chat, « Vue email » ramène à l'affichage habituel.
- **En-tête** : nom et rattachement du correspondant (ou « {N} participants »), objet du fil, chip du patient quand le
  fil est rattaché.
- **Bulles** : le texte **nouveau** de chaque message, sans l'historique cité ni la signature. Séparateur par jour
  (« 13 novembre », « Aujourd'hui »), heure sous chaque bulle. Les bulles reçues portent le nom de l'expéditeur quand
  le fil a plus de deux participants.
- **Texte cité replié** : un bouton « Texte cité et signature » sous la bulle déplie le reste du message.
  **Au moindre doute du découpage, la bulle montre tout le message.** Masquer à tort une information médicale est
  le risque principal de cette US.
- **Message long ou mis en forme** : au-delà de 12 lignes, ou si le message contient un tableau, la bulle est coupée
  et « Lire le message complet » ouvre la vue email.
- **Pièces jointes** : une carte par pièce dans la bulle (nom, type CDA / HPRIM / fichier, patient rattaché). La carte
  ouvre la pièce, comme dans la vue email.
- **Boîte partagée** : une bulle envoyée par une autre personne de la boîte porte son nom et son rôle, et un bleu plus
  clair que les vôtres. Jamais le nom de la boîte ni du titulaire quand l'auteur réel est connu (règle 14). Auteur
  inconnu (réponse partie d'un autre logiciel) : le nom de la boîte.
- **Accusés** : ils ne deviennent jamais des bulles. Ils changent l'état écrit sous le message envoyé : « envoyé »,
  « distribué » (rapport de distribution reçu), « lu à {heure} » (accusé de lecture reçu). Un rapport d'échec de
  distribution donne « non distribué » en erreur. Le mot porte l'état, l'icône l'accompagne seulement.
- **Ordre et volume** : les 30 messages les plus récents d'abord ; les précédents se chargent en remontant.
- **Pas de temps réel** : à l'arrivée d'un message du fil (notification existante ou synchronisation), une pastille
  « {N} nouveau(x) message(s) » propose de descendre. La vue ne saute jamais sous les yeux du lecteur.
- **Lecture** : ouvrir la conversation marque comme lus tous ses messages reçus non lus, avec la trace de lecture
  habituelle, au nom de la personne réelle.

### Répondre

- **Destinataires** : tous les participants du fil, sauf la boîte elle-même. Ils sont écrits au-dessus de la saisie
  (« À : Dr Moreau, Dr Lefèvre »). Si la liste a changé depuis le dernier message de la boîte dans ce fil, un
  avertissement le dit au-dessus de la saisie : « Les destinataires ont changé depuis votre dernier message. »
- **Envoi** : weda2 — Entrée envoie, Maj+Entrée va à la ligne, le bouton « Envoyer » envoie aussi. Mobile — Entrée va à
  la ligne, la flèche envoie. Aucun délai d'annulation. Aucun envoi pendant une saisie IME en cours. Un second appui
  pendant l'envoi ne crée pas de second message.
- **Ce qui part est un vrai email**, composé par le serveur : objet « RE: {objet du fil} », `In-Reply-To` et
  `References` du dernier message du fil, historique cité, signature par défaut de la personne. **Aucune demande
  d'accusé de lecture.** Le correspondant qui n'a pas de vue chat reçoit une réponse ordinaire.
- **Joindre** : un fichier, ou un document du dossier patient, par le parcours de pièce jointe existant de chaque
  client. La pièce apparaît dans la bulle envoyée.
- **États de la bulle envoyée** (planche « États d'un message » de la maquette) :
  - « envoi… » pendant l'envoi ;
  - « envoyé », puis « distribué » ou « lu » à mesure que les accusés arrivent ;
  - **hors ligne sans carte** : « prêt à partir » et « Confirmer avec ma carte » (task-320) ;
  - **échec** : la bulle reste dans le fil, en erreur, avec le code et la référence (task-421), et « Réessayer ».
- **Délégataire** : il répond « de la part du » délégant comme dans la rédaction (task-399). La bulle porte son nom.

### Hors périmètre

- Transférer depuis le chat (le transfert reste dans la vue email).
- Modifier ou supprimer un message envoyé.
- Indicateur « en train d'écrire », présence, temps réel.
- Réactions, mentions.
- Mise en forme riche dans la saisie (gras, listes). Le texte saisi part en texte simple.

## Definition of Done

- [ ] Build passes on every listed repo (0 errors).
- [ ] Tests pass on every listed repo (0 failures).
- [ ] **Contrat de conversation** : `GET api/v1/mail/conversation/{messageId}`, paginé depuis les plus récents. Par
      message : sens (reçu / envoyé), expéditeur, auteur réel et rôle quand il est connu, texte nouveau, texte complet
      ou son accès, indicateur « découpage sûr », pièces jointes résumées, état (envoyé / distribué / non distribué /
      lu + heure). Pour le fil : participants, objet, patient rattaché. DTO dans `dtos-mss`, paquet publié, miroirs
      TypeScript sur les deux clients.
- [ ] **Réponse composée par le serveur** : une route de réponse reçoit le texte, les destinataires et les pièces
      jointes ; le serveur pose l'objet « RE: », `In-Reply-To`, `References`, l'historique cité et la signature par
      défaut, sans `Disposition-Notification-To`. Erreurs en `ProblemDetails` (règle 12).
- [ ] **Découpage de la citation** côté serveur, ne repliant que le texte retrouvé dans le message parent du fil ;
      sinon « découpage sûr » = faux et la bulle montre tout. Tests unitaires sur un corpus de messages réels
      **anonymisés**, versionné dans le dépôt : réponses Mailiz, Outlook (en-têtes « De : … Envoyé : »), Thunderbird
      (« Le … a écrit : »), Apple Mail, réponses en `>`, envois de la plateforme, et au moins un message où le texte
      « cité » ne figure pas dans le parent (doit rester visible).
- [ ] **Accusés reçus rattachés au message envoyé** : rapport de distribution (`multipart/report;
      report-type=delivery-status`, succès et échec) et accusé de lecture (`disposition-notification`), reliés par
      `Original-Message-ID` (ou `In-Reply-To` à défaut). Un accusé reçu ne devient jamais une bulle. Si l'état est
      stocké : migration FluentMigrator relue (règle 7c, points 1 à 4 ; aucune suppression de données).
- [ ] **Lecture à l'ouverture** : tous les messages reçus non lus du fil passent lus, chacun tracé au nom de la
      personne réelle (famille `HealthDataAccess`).
- [ ] Tests unitaires : sens et auteur réel d'une bulle, pagination, composition de la réponse (objet, en-têtes,
      citation, signature, pas d'accusé demandé), destinataires = tous les participants moins la boîte, détection du
      changement de destinataires, rattachement des trois sortes d'accusés, accusé inconnu ignoré.
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `GET api/v1/mail/conversation/{messageId}` : un fil de
      trois messages (deux reçus, un envoyé) déposé dans GreenMail ; la réponse réelle porte les trois messages dans
      l'ordre, le sens de chacun, le texte nouveau **sans** l'historique cité du message de réponse, la pièce jointe du
      premier ; un message dont la citation n'est pas retrouvée dans le parent revient avec « découpage sûr » = faux et
      son texte complet. Cas d'échec : identifiant inconnu → 404 en `ProblemDetails`. Vu rouge.
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour la route de réponse : le message reçu par GreenMail porte
      « RE: », `In-Reply-To` et `References` du dernier message du fil, l'historique cité, la signature, tous les
      participants en destinataires, **aucun** `Disposition-Notification-To`, et la pièce jointe. Relu ensuite par la
      route de conversation, il apparaît comme bulle envoyée. Cas d'échec : texte vide → 400 en `ProblemDetails`.
      Vu rouge.
- [ ] **Test d'intégration de bout en bout (règle 1b)**, accusés : après l'envoi, un rapport de distribution puis un
      accusé de lecture déposés dans GreenMail font passer l'état lu dans la réponse de conversation de « envoyé » à
      « distribué » puis « lu » avec l'heure ; un rapport d'échec donne « non distribué ». Aucun des trois n'est une
      bulle. Vu rouge.
- [ ] **Test d'intégration de bout en bout (règle 1b), deux personnes sur la même boîte** : le délégataire répond depuis
      la route de réponse ; le titulaire relit la conversation, la bulle envoyée porte le nom PSC et le rôle du
      délégataire ; la trace de l'envoi porte le délégataire ; l'ouverture de la conversation par le titulaire trace
      la lecture des messages au nom du titulaire. Vu rouge.
- [ ] **weda2 (`client-angular`)** : vue chat (en-tête, bulles, séparateurs de jour, texte cité replié, message long,
      pièces jointes, auteur réel, états, pastille « nouveau message », chargement des précédents), saisie avec
      destinataires visibles et avertissement de changement, Entrée envoie et Maj+Entrée va à la ligne, pas d'envoi
      pendant une saisie IME, pas de double envoi, joindre un fichier ou un document du dossier, « Voir en
      conversation » et « Vue email ». Tests de composant : rendu des bulles et des états, touches Entrée / Maj+Entrée
      / IME, double appui.
- [ ] **Mobile (`client-mobile`)** : même vue, écran conçu avec `/stitch-design` ; Entrée va à la ligne, la flèche
      envoie. Tests de composant équivalents.
- [ ] **L'avertissement « Les destinataires ont changé depuis votre dernier message »** s'affiche quand la liste a
      changé, sur les deux clients (test de composant + scénario e2e).
- [ ] Libellés en français sans chaîne en dur hors i18n là où le client a un i18n ; `data-testid` sur chaque élément
      interactif (saisie, envoi, joindre, bulle, « Texte cité et signature », « Lire le message complet », « Vue
      email », « Voir en conversation », pastille, « Réessayer », « Confirmer avec ma carte »).
- [ ] Scénario **E2E-CONV-001** ajouté dans `Api/Mail/e2e/scenarios.yml` (version 1, mobile : requis, angular :
      requis) et implémenté dans les deux clients : ouvrir un fil en vue chat, lire les bulles, répondre ; la réponse
      relue du serveur est dans le fil, adressée à tous les participants.
- [ ] Scénario **E2E-CONV-002** ajouté (version 1, mobile : requis, angular : requis) et implémenté dans les deux
      clients : joindre un document depuis le chat ; la pièce est dans la bulle envoyée et dans le message relu du
      serveur.
- [ ] Aucune donnée de santé en clair dans les logs : ni corps, ni texte saisi, ni nom de patient, ni contenu de pièce
      jointe.

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run` (ou l'AppHost). weda2 : `cd Client/Angular && npm start`. Mobile :
   `cd Client/Mobile && npm start`.
2. Préparer un fil avec un confrère : un message reçu avec un compte rendu CDA, une réponse de vous, deux messages
   reçus ensuite, dont un dont le logiciel cite l'historique (Outlook ou Thunderbird).
3. weda2, mode Conversation : ouvrir le fil. Les bulles sont dans l'ordre, les vôtres à droite. Le message qui citait
   l'historique ne montre que son texte nouveau ; « Texte cité et signature » déplie le reste. La carte du CDA ouvre
   le document.
4. Revenir à la liste : les messages du fil sont lus.
5. Taper « Merci, je préviens le patient. », puis Maj+Entrée et une seconde ligne, puis Entrée. La bulle passe à
   « envoi… » puis « envoyé ». Dans la boîte du confrère : objet « RE: … », historique cité, signature, pas de demande
   d'accusé de lecture.
6. Depuis la boîte du confrère, renvoyer un accusé de lecture : la bulle passe à « lu à {heure} », et aucune bulle ne
   s'ajoute.
7. Mobile, même fil : Entrée va à la ligne, la flèche envoie. Joindre un document du dossier patient : il apparaît dans
   la bulle.
8. Ajouter un participant en copie depuis la boîte du confrère, puis rouvrir le chat : l'avertissement de changement de
   destinataires s'affiche, et « À : » liste tous les participants.
9. Boîte partagée : la secrétaire déléguée répond depuis son mobile ; le médecin voit la bulle avec « Cyril DELEGUE
   (délégataire) ».
10. Couper le réseau du backend vers la messagerie, puis envoyer : la bulle reste en erreur avec le code et la
    référence ; « Réessayer » l'envoie une fois le réseau revenu.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — ergonomie de lecture et de réponse, sans exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — la réponse reste un message MSSanté ordinaire, déjà conforme
- **INS** : non applicable — la vue affiche le patient déjà rattaché au fil (chip), elle ne rattache ni ne qualifie
  aucune identité
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; hors ligne sans carte, l'envoi attend la
  confirmation par la carte (task-320)
- **Habilitations** : personnes rattachées à la boîte sous verdict récent de l'opérateur (règle 14) ; le délégataire
  répond de la part du délégant (task-399)
- **Interop CI-SIS** : non applicable pour le contenu. Transport : en-têtes RFC 5322 (`In-Reply-To`, `References`),
  rapports RFC 3464 (distribution) et RFC 8098 (lecture) lus en réception. Les CDA joints restent traités par
  `interop-cda`, inchangé
- **Tracé PGSSI-S** : envoi (trace `MailReply` existante) et lecture de chaque message à l'ouverture, au nom de la
  personne réelle avec son rôle ; famille `HealthDataAccess`, conservation 3 653 jours (règle 14)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte ; l'éventuel état des accusés y est stocké
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle sur le patient ; l'état distribué / lu porte sur des
  messages déjà conservés

## Branches
- `api-mail` (pushed) : feat/task-487-conversation-en-chat-lire-le-fil-et — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-487-conversation-en-chat-lire-le-fil-et (depuis `develop` `a148b7e3`, task-454 incluse)
- `client-mobile` (pushed) : feat/task-487-conversation-en-chat-lire-le-fil-et — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-487-conversation-en-chat-lire-le-fil-et (depuis `develop` `14ec5c0`)
- `dtos-mss` (branche paresseuse) : créée par `/develop` au moment où il touche le contrat
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, arbre propre) — l'humain gère branche, commit, push, PR TFS

## Stitch design log

- Écran `conversation-chat` (projet Stitch `client-mobile`, 10088502293310567548) : `generate_screen_from_text` appelé une
  fois, délai dépassé ; l'écran n'apparaît ni dans `get_project` ni dans `list_screens`, et il n'a pas été régénéré
  (consigne : un délai dépassé est un succès probable, jamais de doublon). À vérifier dans l'interface Stitch.
- L'écran Ionic suit les règles du projet (bulles envoyées pleines en couleur primaire à droite, reçues sur fond neutre à
  gauche) et la maquette Claude Design citée en tête de la task.
## Develop log

- Repos touched : `dtos-mss` (branche paresseuse créée par /develop), `api-mail`, `client-mobile`, `client-angular` (code-only).
- DTOs published : `HealthPlatform.Dtos.Mss` 618.0.0 → **621.0.0** (`MailConversationDto`, `ConversationMessageDto`,
  `ConversationAttachmentDto`, `ConversationReplyRequestDto`, `ConversationReplyResultDto`, enums `ConversationDirection`,
  `ConversationDeliveryState`, `ConversationAttachmentKind`). Consommateur bumpé : api-mail. `client-blazor` n'est pas dans
  les `**Repos**` (il reste en 533.0.0, comme avant cette task) : non touché.
- Interop published : no interop change.
- api-mcp : aucun impact (`mcp_impact.py check` = 0).
- Commits :
  - dtos-mss : `1e4c449` feat(dto): contrat de conversation en chat.
  - api-mail : `223e9ea4` bump DTO 621 ; `066be005` feat(conversation) ; `4973c9e6` refactor simplify pass.
  - client-mobile : `3af2264` feat(mobile) ; `0ed943f` refactor simplify pass ; `ab03b32` test(mobile) E2E-CONV-001 (sélecteur).
  - client-angular : non commité sur `feature/nova-mss-weda-integration` (liste en fin de log).

### Serveur (api-mail)

- **Routes** (`ConversationController`) :
  - `GET api/v1/Mail/conversation/{messageId}?page&pageSize` — `[TracedInCode(MailRead)]`. La page 1 est l'ouverture : les
    messages reçus non lus du fil passent lus par `IEmailFlagService.UpdateEmailReadStatusAsync`, un `MailRead` par message
    au nom de la personne réelle. La route rend le patient du fil : jamais `TraceExempt` (convention
    `route-identite-patient-jamais-exemptee`).
  - `POST api/v1/Mail/conversation/{messageId}/reply` — `[TracedInCode(MailReply)]` (SmtpService trace `MailReply` pour une
    réponse). Hors ligne : 202, réponse « prête à partir » dans la file `SendMail` (task-320).
- **Règles** (Domain, sans base) : `ConversationQuoteSplitter` (ne replie que le texte retrouvé dans le parent, sinon
  `IsSplitSafe = false` et texte complet ; signature repliée seulement sur le séparateur normalisé « -- »),
  `ConversationDeliveryStates` (échec > lu > distribué > envoyé), `ConversationParticipants` (tous moins la boîte,
  changement depuis le dernier envoi de la boîte).
- **Application** : `ConversationText` (HTML → texte : `blockquote` en « > », commentaires de signature en « -- »,
  lignes de tableau relevées), `DeliveryReportParser` (RFC 8098 `displayed`, RFC 3464 `failed`/`delivered`/`relayed`/
  `expanded`, `Original-Message-ID`, en-têtes renvoyés, repli `In-Reply-To`), `ConversationReplyComposer` (RE:,
  `In-Reply-To`/`References` du dernier message, texte échappé, signature par défaut avant l'historique cité, aucun
  `RequestReadReceipt`), `ConversationService`, `SignatureMarkers` (constantes partagées avec `SmtpService`).
- **Accusés reçus** : lus à l'ouverture (page 1, en ligne), au plus 20 par ouverture, par `IMailExportService.BuildEmlAsync`
  (verrou de session, dossier refermé, message disparu = `NotFound` relu plus tard). Résultat stocké sur la ligne du
  rapport : migration `20261117221900_AddMailReportLinks` (`Mails.ReportKind` smallint null, `Mails.ReportOriginalMessageId`
  varchar(512) null, index `IX_Mails_ReportOriginalMessageId`). Règle 7c relue : deux colonnes ajoutées nullables, un index,
  aucune suppression ni modification de données, `Down` symétrique ; FluentMigrator (pas de Designer) ; le modèle EF
  déclare colonnes et index sous les mêmes noms (`MailDataContext`).
- **Fil** : le parcours du fil (`ThreadMessageIds`) est extrait de `MailRepository` et partagé ; un `Message-ID` ou un
  `In-Reply-To` stocké avec ses chevrons se lit dans les deux sens.
- **Copie d'Envoyés pas encore synchronisée** : une réponse partie de la plateforme et archivée (emplacement noté par
  task-459) est analysée à la lecture de la conversation : la bulle envoyée revient sans attendre la synchronisation.
- **Corpus** (`tests/mss.mail.application.tests/Conversation/Corpus`, ressources incorporées) : Thunderbird, Outlook (« De :
  … Envoyé : »), Apple Mail, Mailiz, Gmail, réponse en « > », envoi de la plateforme, et une citation absente du parent
  (reste visible). Messages et noms anonymisés (domaine `corpus.test`, patiente fictive).

#### Règle 1b — comportement → test d'intégration → preuve rouge

Tests : `tests/mss.mail.integration.tests/UseCases/ConversationEndToEndTests.cs` (vraie pile HTTP, PostgreSQL de la boîte,
Dovecot, GreenMail ; seuls la porte de la carte et le résumé IA sont simulés). 29 mutations (script
`mutate.py`, build + test ciblé, restauration par copie), **29/29 rouges sur l'assertion prévue**, rejouées après la passe
qualité (29/29) :

| Comportement | Test | Mutation vue rouge |
|---|---|---|
| Fil dans l'ordre, sens de chaque bulle | `TheConversation_ReadsTheThreadInOrder_…` | M2 sens inversé |
| Texte nouveau sans l'historique cité, replié | idem | M4 texte nouveau = complet ; M21 rien de replié ; M28 parent ignoré |
| Pièce jointe du premier message | idem | M3 pièces jointes perdues |
| Destinataires = tous moins la boîte, changement signalé | idem | M5 boîte parmi les participants ; M22 changement muet |
| Citation absente du parent → découpage non sûr, texte complet | `AQuoteNotFoundInTheParent_…` | M1 citation non vérifiée |
| Message inconnu → 404 ProblemDetails | `AnUnknownMessage_Is404_…` | M6 500 au lieu de 404 |
| Réponse : RE:, In-Reply-To, References, citation, signature, tous les participants, aucun DNT, pièce jointe | `TheReply_IsARealEmail_…` (lu dans GreenMail) | M7, M8, M9, M10, M11, M23, M24, M25, M26 |
| Réponse relue comme bulle envoyée sans synchronisation d'Envoyés | idem | M29 copie archivée non analysée |
| Texte vide → 400 ProblemDetails | `AnEmptyText_Is400_…` | M12 texte blanc accepté |
| Accusés : envoyé → distribué → lu (heure) ; échec → non distribué ; jamais une bulle | `ReceivedReports_ChangeTheState…` | M13, M14, M15, M16, M20, M27 |
| Délégataire : bulle à son nom et rôle, trace `MailReply` à son nom ; ouverture par le titulaire tracée `MailRead` au nom du titulaire | `TheDelegateReplies_…` | M17 auteur ignoré ; M18 lecture sur les envoyés ; M19 « écrit par moi » toujours vrai |

Tests unitaires : `ConversationRulesTests` (15, domaine), `ConversationCorpusTests` (9), `ConversationHelpersTests`
(texte, accusés, composition), `ConversationServiceTests` (sens, auteur réel, pagination, lecture à l'ouverture page 1
seulement, accusés lus en ligne seulement à l'ouverture, accusé disparu, destinataires, réponse vide, hors ligne, échec).

### client-mobile

- Écran `/conversation/:messageId` (`src/app/conversation/`), sélecteur de documents du dossier patient
  (`patient-document-picker`, pièce par référence comme un transfert : le serveur la relit par `OutgoingMailService`),
  utilitaires `core/utils/conversation.util.ts`, modèles `core/models/conversation.model.ts`, appels `getConversation` /
  `replyToConversation`, entrées « mode Conversation » et « Voir en conversation ».
- Tests unitaires : 1585 → **1638**, verts deux fois de suite ; lint propre ; build OK.
- Preuves rouges unitaires (agent) : garde IME, double appui, repli de la citation, pas de « Réessayer » sur une
  distribution incertaine, libellé « non distribué ».
- E2E (voie servie `--serve-only`, `playwright --grep E2E-CONV`) : **2/2 verts**. Mutations (`mutate_e2e_mobile.py`,
  recompilation attendue dans `ngserve.log`) : E1 réponse au seul premier destinataire → rouge « le message parti est
  adressé aux deux confrères » ; E2 bouton « Texte cité » sans effet → rouge « déplie le reste » ; E3 avertissement
  absent → rouge ; E4 pièce jointe perdue → rouge « la bulle envoyée relue du serveur porte la pièce jointe ». Code
  restauré, 2/2 verts.
- Le test E2E-CONV-001 écrit par l'agent était faux deux fois, vu à sa première exécution : un `has:` absolu évalué dans
  une rangée (jamais trouvé), et un ordre de bulles supposé alors que l'outil e2e date la réponse du confrère une minute
  plus tard (task-375). Corrigé (`ab03b32`).

### client-angular (weda2, code-only)

- Vue chat dans l'écran mail (`features/mail/components/mail-conversation/` : conteneur, `chat-bubble`, `chat-composer`),
  modèles et utilitaires `core/models/conversation.model.ts`, `core/utils/conversation.util.ts`, entrées « mode
  Conversation » (bouton `open-conversation` par fil) et « Voir en conversation ».
- Tests : mss-lib 1780 → **1832**, weda2 **2683** ; build weda2 OK (dépassements de budget déjà présents : 2,38 Mo,
  `mss-contacts.component.scss`) ; ESLint 0 erreur (avertissement `max-lines` sur `mail-conversation.component.ts`) ;
  stylelint et prettier propres.
- Preuves rouges unitaires (agent) : garde IME, Maj+Entrée, garde d'envoi en vol, texte nouveau affiché malgré un
  découpage douteux, rang des pièces homonymes.
- E2E (voie servie `--serve-only`) : **2/2 verts**. Mutations (`mutate_e2e_angular.py`, fenêtre de recompilation de 60 s) : A1 réponse au seul premier destinataire → rouge « la réponse part au second confrère » ; A2 bouton « Texte cité » sans effet → rouge ; A3 avertissement absent → rouge « les destinataires ont changé » ; A4 pièce jointe perdue → rouge « la bulle envoyée relue du serveur porte la pièce jointe ». Code restauré, 2/2 verts.
- **Non fait** : joindre un « document du dossier patient » depuis la saisie weda2. weda2 n'a pas de parcours existant
  pour cela (il arrive par l'intention d'envoi de l'hôte Weda, task-367) ; seul « joindre un fichier » existe. À
  trancher : arbitrage humain.

### Passe qualité (/simplify)

- Applied & committed : api-mail (`4973c9e6` — `BuildEmlAsync` réutilisé au lieu d'une copie dans `IImapService`, accusés
  lus seulement à l'ouverture, texte des seules bulles de la page, `GetThreadAsync` découpé (S138), filtre IHE_XDM sans
  casse, `SignatureMarkers` partagés, `HasFolded` dérivé, normalisation des fins de ligne partagée, garde « Sender = boîte »
  retirée (l'ingestion l'écarte déjà)), client-mobile (`0ed943f` — utilitaires réutilisés, limite de pièce jointe lue dans
  les réglages, plus de tri client des pages, polling borné et coupé à la destruction, pas de GET thread pour un message
  sans rapport, défilement infini au lieu de `ionScroll`).
- Applied (code-only, uncommitted) : client-angular (rang des homonymes, `sendErrorMessage` et `readFileAsBase64`
  partagés avec la rédaction, limite de pièce jointe unique, clé de jour corrigée (mois décalé), téléchargement d'une
  pièce non prévisualisable, plus de tri client des pages, rechargements sérialisés, notification débouncée).
- Skipped (contract) : dtos-mss.

### DOD self-check

- Build / tests : verts sur api-mail (358 + 749 + 4316 + 1382 + 1355), mobile (1638), weda2 (1832 + 2683).
- Contrat de conversation, réponse composée, découpage + corpus, accusés rattachés + migration, lecture à l'ouverture,
  tests unitaires, 4 tests d'intégration de bout en bout vus rouges : présents (table ci-dessus).
- weda2 et mobile : vues, saisie, touches, IME, double envoi, testids, avertissement de destinataires (tests de composant
  et E2E-CONV-001) : présents. **Écart** : joindre un document du dossier patient depuis le chat weda2 (ci-dessus).
- E2E-CONV-001 et E2E-CONV-002 au catalogue (v1, mobile et angular requis) et implémentés dans les deux clients.
- Aucune donnée de santé dans les journaux : le service ne journalise ni texte, ni corps, ni nom ; le contrôleur journalise
  la page et le nombre de messages.
- Green marked : api-mail (`4973c9e6`), client-mobile (`0ed943f`) ; client-angular marqué sur l'arbre final.

### Amélioration continue (préventions)

- `conventions/csharp.md` : `lecture-imap-ponctuelle-par-le-chemin-existant` (un dossier IMAP laissé ouvert cachait les
  messages arrivés ensuite) et `fichier-de-test-texte-et-autocrlf` (corpus extrait en CRLF sous Windows).
- Mémoire de session : récidive ×3 du piège « barre oblique inverse en heredoc » (deux fichiers cassés, réparés avant
  commit) ; réflexe noté : script écrit avec Write dès qu'il y a une barre oblique inverse.
- `conventions/e2e.md` : à alimenter par /review si la revue le juge (un `has:` absolu dans un `filter` ne trouve rien).

- Next step : /review task-487 --code

### Reprise 1 après /review

Chaque correctif écrit test d'abord, vu rouge sur le code d'avant, puis vert.

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **B1** historique fait d'en-têtes seuls jugé sûr | `ConversationQuoteSplitter` : un contenu vide après les marques n'est plus une preuve (`content.Length > 0 &&`) | `ConversationRulesTests.Split_AHeaderOnlyQuote_IsNotSafe_AndEveryLineStays` ; intégration `UnverifiedTextIsNeverFolded_HeaderOnlyQuote_AndPostScriptAfterTheSignature` | rouge avant correctif (unitaire) ; mutation M30 rouge (`Assert.False() Failure`) |
| **B2** texte après la signature replié | la signature ne se replie que si son début et sa fin sont connus (`SignatureRange`, lue par `ConversationText` : marques `<!-- signature -->`…`<!-- /signature -->`, conteneurs `moz-signature` / `gmail_signature`) ; le texte écrit après elle reste ; un simple « -- » en texte brut ne replie rien | `Split_TextAfterAPlainSignature_StaysVisible`, `Split_TextAfterTheSignatureEnd_StaysVisible_AndTheQuoteStillFolds`, `Split_ASignatureWithAKnownEndFolds_ButAPlainDelimiterFoldsNothing` ; intégration (même test que B1) | rouge avant correctif (unitaire) ; mutation M31 rouge (`Sub-string not found`) |
| **B3** brouillons dans le fil | `ConversationRepository.GetThreadAsync` exclut `IsDraft` et le dossier des brouillons | `AReplyDraftSavedByAnotherSoftware_IsNotABubble_NorTheLastMessage` (brouillon déposé dans Drafts, `\Draft`) | rouge avant correctif (le brouillon était la 4e bulle) ; mutation M32 rouge |
| **B4** mobile : bulle « prêt à partir » jamais résolue | rechargement de la page 1 et retour sur la page retirent les bulles locales en attente | `B4 — a reply ready to go (202) leaves the thread on re-entry…`, `B4 — a page 1 reload drops a local « prêt à partir » bubble` | rouges sur ab03b32 (`Expected $[0] = 'prêt à partir' to equal 'envoyé'`, bouton « Confirmer avec ma carte » encore là) |
| mobile : rechargements de confirmation qui défilent | plus de `scrollToEnd` sur ces rechargements | `the confirmation reloads after a send never scroll the view…` | rouge (`Expected 2 to be 1`) |
| mobile : garde `isSplitSafe` | texte complet, pas de bouton, si le découpage n'est pas sûr | `shows the whole message, without « Texte cité et signature »…` | rouge |
| mobile : erreur réseau technique | `problemMessage(error, …)` | `says a network failure in plain words…` | rouge (l'URL s'affichait) |
| les deux clients : destinataires périmés quand la pastille annonce des messages | l'envoi relit d'abord la page 1 | mobile `when the pill announces new messages, sending first reloads page 1…` ; weda2 `quand la pastille annonce des messages, l'envoi relit d'abord le fil…` | rouges (anciens destinataires envoyés) |
| weda2 : téléchargement en échec sans gestion | message à l'écran (code et référence), rien en console | `le téléchargement d'une pièce en échec se dit à l'écran…` | rouge (« Unhandled Error ») |
| weda2 : « Voir en conversation » sans garde | `canOpenConversation` (Message-ID, ni brouillon ni accusé) | `mail-detail.conversation.spec.ts` (4 cas) | rouges |
| weda2 : envoi sans destinataire, « 1 participants » | `canSend` exige un destinataire ; titre au singulier, sujet sans participant | `n'envoie pas sans destinataire`, `sans participant connu…` | rouges |
| weda2 : pièce demandée introuvable gardée | la demande est effacée dès que le message demandé s'affiche | `une pièce demandée introuvable dans le message n'est pas gardée…` | rouge |

| serveur : lecture des accusés pendant une panne, accusé disparu en tête de file | `NotFound` → lu « inconnu » ; autre échec → arrêt de la lecture (une tentative par ouverture) | unitaires `Get_TheMailServerDown_StopsReadingReportsAtTheFirstFailure`, `Get_AReportGoneFromTheServer_…` ; intégration `AFarPageIsEmpty_AndAReportGoneFromTheServerNeverBreaksTheOpening` (accusé expurgé du serveur) | unitaires rouges avant correctif ; mutation M34 rouge (`Assert.Empty() Failure`) |
| serveur : page lointaine en 500 | calcul de la page en `long`, bornée au fil | unitaire `Get_APageFarBeyondTheThread_IsEmpty` ; intégration (même test, `page=1000000000&pageSize=200`) | unitaire rouge ; mutation M33 rouge (« Attendu 200, reçu 500 ») — survivante d'abord avec une page qui ne débordait pas, test corrigé |

Non repris (suggestion) : `ReadAt` retombe encore sur la date d'en-tête quand la date d'arrivée manque.

Suite complète api-mail de la reprise : domaine, infrastructure, application, api verts ; intégration 1353/1373, 4 rouges
hors de la task — trois tests « du jour » joués entre 0 h et 2 h (fenêtre connue : filtre SINCE en UTC) et
`ImapSessionSweepIntegrationTests.ConnectAsync_WhileTheSweepRunsDuringTheConnection_OpensTheSessionAsync`, bloqué une heure,
bloqué de nouveau en isolé (ni le service de connexion ni `ImapService` ne diffèrent de `develop`). Vert api-mail **non
marqué** : la validation finale rejoue la suite complète.

Relecture du correctif comme correctif : `Split` a un seul appelant de production (le service) ; le filtre des brouillons
ne touche ni la lecture des copies d'Envoyés ni l'analyse des messages manquants ; la règle « pas de repli sur un « -- »
brut » change le corpus Thunderbird (aucune signature) et la plateforme (marques présentes) sans écart.

Tests : domaine 18 (Conversation), application 112 (Conversation), intégration 9/9 (`ConversationEndToEndTests`) ; mobile
1644/1644 deux fois ; weda2 mss-lib 1842/1842, weda2 2683/2683.

### Reprise 2 après /review (règle 13 relevée le 2026-11-18)

| Constat | Correctif | Test | Preuve rouge |
|---|---|---|---|
| **R1 (récidive de B2)** PS masqué quand la réponse et le parent cité sont signés, ou sans marque de fin | `ConversationText` : chaque signature de la réponse (marques de la plateforme, `moz-signature`, `gmail_signature`) reçoit un numéro, **hors citation** ; seule la **première signature fermée** est retenue ; une marque d'ouverture sans fermeture ne donne aucune signature. `ConversationQuoteSplitter` : la signature doit se terminer avant l'historique (`range.End <= bodyEnd`) | corpus `signed-both` (réponse Thunderbird signée + PS + parent signé par la plateforme) ; `Text_AnUnclosedSignatureMarker_HasNoKnownSignature` ; `Text_ASignatureInsideTheQuote_IsNotTheReplySignature` ; intégration `UnverifiedTextIsNeverFolded_…` étendu (même forme, lue dans la réponse réelle) | les trois tests unitaires et le corpus rouges avant correctif ; mutation M37 (les trois gardes retirées) rouge (`Sub-string not found`). M35 (une seule garde retirée) survit : les gardes se recouvrent, c'est voulu |
| `HasRichContent` aveugle à un tableau écrit après la signature | `ConversationSplit.Shows(line)` : une ligne est montrée si elle est avant l'historique et hors signature | `Get_ATableAfterTheSignature_MakesTheBubbleRich` ; intégration (tableau dans le PS du cas `signed-both`) | rouge avant correctif (`Assert.True() Failure`) ; mutation M36 rouge |
| `ReadAt` sur la date d'en-tête étiquetée UTC (liste du passage 1) | la date d'arrivée UTC seulement | — (la date d'arrivée est toujours écrite par l'ingestion : le repli était mort) | non applicable |
| **R2 (weda2)** réponse partie vers un fil quitté | `send` capture le fil, ses destinataires et `loadSeq` ; la relecture d'avant envoi n'écrit et n'envoie rien si le fil a changé ; `transmit(reply, target)` n'envoie qu'à sa cible | `ouvrir un autre fil pendant la relecture d'avant envoi : rien ne part, rien n'est écrit dans le nouveau fil` | rouge (`replyToConversation` appelé) ; mutation du filtre `loadSeq` rouge |
| weda2 : `downloadError` survit au changement de fil | `reset()` l'efface | `l'échec de téléchargement d'un fil ne s'affiche pas dans le fil suivant` | rouge |
| **R3 (mobile)** « prêt à partir » retiré sans confirmation | la bulle n'est retirée que lorsque l'envoi en attente qui lui correspond (objet « RE: … » + texte saisi, lu par `pending-emails`) a disparu ; non identifiable → gardée ; « envoyé » gardé jusqu'à la bulle du serveur de même Message-ID | `R3 — a page 1 reload keeps an unconfirmed « prêt à partir » bubble…` (remplace le test qui affirmait le défaut), `R3 — coming back from /pending-emails without confirming…`, `R3 — a reply that pending-emails does not reliably identify is kept`, `R3 — a sent reply stays until the server bubble…` | rouges sur 7f0ae07 ; mutations rouges |
| mobile : garde R2 | `send` capture l'identifiant et les destinataires ; rien ne part si la route a changé | `R2 — when the route changes during the pre-send reload, nothing is posted` | rouge |

Tests : api-mail domaine 361, infrastructure 749, application 4322, api 1382, intégration 1357/1373 (16 ignorés),
**0 échec** — suite jouée en excluant seulement `ImapSessionSweepIntegrationTests.ConnectAsync_WhileTheSweepRunsDuringTheConnection_OpensTheSessionAsync`,
qui bloque une heure (code non modifié par la task : `ImapService` et le service de connexion identiques à `develop`) ;
vert api-mail non marqué pour cette raison. Mobile 1648/1648 deux fois ; weda2 mss-lib 1844/1844, weda2 2683/2683.
Commits : api-mail `7f80eaf8`, client-mobile `3921a69`.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Revue par deux relecteurs indépendants (serveur : api-mail + dtos-mss ; clients : client-mobile + weda2), sur le code,
sans le Develop log.

- **4a (règle 1b)** : chaque comportement atteignable par une route a son test d'intégration de bout en bout
  (`ConversationEndToEndTests`, vraie pile HTTP, PostgreSQL, Dovecot, GreenMail), lu dans la réponse réelle, vu rouge
  par mutation (29/29, table du Develop log). Les trois bloquants serveur ci-dessous n'ont pas de test : la reprise les
  ajoute, vus rouges.
- **4c** : api-mcp : aucun impact (`mcp_impact.py check` = 0).
- **4b (clause DoD)** : E2E-CONV-001 et E2E-CONV-002 au catalogue en version 1, mobile et angular requis ; les deux
  clients les déclarent en version 1 (`scenario('E2E-CONV-00x', 1)`).

#### À corriger par la reprise

- **B1 (serveur)** — `ConversationQuoteSplitter` : un historique fait seulement de lignes d'en-tête (« De : … / Date : … /
  Objet : … ») laisse un contenu vide après `SkipMarks`, et le repli est déclaré sûr sans rien comparer au parent. Un
  message « Je vous adresse Mme X. / De : cardiologie / Date : 20/11 14h / Objet : douleur thoracique, ECG anormal » ne
  montre que la première ligne, `IsSplitSafe = true`. Un contenu vide n'est pas une preuve : non sûr. Test unitaire et
  corpus.
- **B2 (serveur)** — la signature repliée n'a pas de fin : tout ce qui suit le dernier « -- » jusqu'à la citation (ou la
  fin) est replié sans contrôle. Un PS écrit après la signature HTML de la plateforme (`<!-- /signature -->`, posé par
  la rédaction mobile) ou sous une signature « -- » de Thunderbird est masqué, `IsSplitSafe = true`. Le repli s'arrête à
  la marque de fin ; du texte après une signature « -- » sans marque de fin rend le découpage non sûr. Tests unitaires.
- **B3 (serveur)** — `ConversationRepository.GetThreadAsync` ne filtre pas les brouillons : un brouillon de réponse
  enregistré par un autre logiciel dans Drafts (`\Draft`, `In-Reply-To` dans le fil) devient une bulle « envoyé », le
  dernier message du fil (la réponse s'y rattache et le cite) et la base de « destinataires changés ». Exclure `IsDraft`
  et le dossier des brouillons. Test d'intégration vu rouge.
- **B4 (mobile)** — une réponse « prête à partir » (202) reste une bulle locale `queued` sans `messageId` : rien ne la
  retire. Après confirmation par la carte et retour sur la page, elle dit toujours « prêt à partir » et la bulle du
  serveur « envoyé » apparaît à côté, même texte. Retirer les bulles locales en attente au rechargement de la page 1 et au
  retour sur la page. Test de composant.
- Défauts réels corrigés dans la même passe :
  - serveur : la lecture des accusés à l'ouverture s'arrête au premier échec qui n'est pas « message introuvable »
    (messagerie en panne : une tentative, pas vingt) ; un accusé introuvable sur le serveur est marqué lu « inconnu »
    (sinon vingt accusés disparus bloquent les suivants à chaque ouverture) ; la pagination borne `end` au nombre de
    messages (une page énorme rendait un 500 au lieu d'une page vide) ; `ReadAt` ne retombe plus sur la date d'en-tête
    en heure locale étiquetée UTC.
  - weda2 : le téléchargement d'une pièce depuis une carte a un gestionnaire d'erreur (message à l'écran, rien dans la
    console : l'URL porte le nom du fichier) ; « Voir en conversation » est masqué sans `Message-ID`, sur un brouillon et
    sur un accusé (comme mobile) ; `canSend` exige au moins un destinataire ; titre « 1 participant » au singulier, sans
    « 1 participants » sur une liste vide ; la demande d'ouverture de pièce est effacée si le détail ne la trouve pas.
  - mobile : les rechargements de confirmation après un envoi ne font plus défiler la vue (« la vue ne saute jamais ») ;
    garde côté client sur `isSplitSafe` (texte complet, pas de bouton de repli), comme weda2 ; message d'erreur réseau
    par `problemMessage` (jamais l'URL technique).
  - les deux clients : quand la pastille annonce des messages nouveaux, l'envoi relit d'abord la page 1 (sans défiler)
    et part avec les destinataires à jour.

#### Arbitrage humain (non bloquant, va dans la PR)

- **Joindre un document du dossier patient depuis le chat weda2** (décision 6) : l'US le limite au « parcours de pièce
  jointe existant de chaque client ». La rédaction weda2 n'en a pas (un document du dossier arrive par l'intention
  d'envoi de l'hôte Weda, task-367) ; le chat weda2 offre donc « joindre un fichier ». Le mobile offre les deux.
  Recommandation : accepter pour cette US, ouvrir une task pour un sélecteur de documents du dossier dans weda2.
- **Entrée weda2 en mode Conversation** : un bouton « ouvrir en conversation » sur chaque fil ; un clic sur la ligne
  ouvre toujours le message (les parcours existants, dont E2E-MAIL-006, en dépendent). Le mobile ouvre le chat au toucher
  du fil. Recommandation : garder le bouton dans weda2.
- **« Les destinataires ont changé »** compare tous les participants du fil aux destinataires du dernier message de la
  boîte : une personne retirée volontairement par le médecin réapparaît (répondre à tous) et l'avertissement s'affiche.
  À trancher : « nouveaux participants depuis votre dernier message » seulement ?
- **Coupe à 12 lignes** : comptée en lignes du texte, pas en lignes affichées (un long paragraphe sans retour n'est pas
  coupé). À trancher.
- **Corpus « réel anonymisé »** : les huit cas sont construits sur les formes réelles des logiciels (attributions,
  blocs d'en-têtes, blockquote, signature de la plateforme), pas copiés de vrais messages. À confirmer, ou fournir des
  messages réels anonymisés à ajouter.
- **Accusés reçus avant task-459** : leurs lignes gardent `IsReport = false` (pas de reprise de données à task-459) ; un
  ancien « Lu : … » apparaît donc comme une bulle reçue sur une boîte existante. Une reprise de données est une
  écriture en masse sur les bases des boîtes : à décider.

#### Suggestions retenues pour plus tard (non bloquantes)

- Lire les accusés reçus à la synchronisation plutôt qu'à l'ouverture ; ne charger les corps que pour la page.
- Pagination par curseur (`before=`) plutôt que par numéro de page depuis le plus récent.
- Idempotence serveur de `POST …/reply` (un « Réessayer » après un délai dépassé où le SMTP avait accepté).
- Signature des signatures weda2 (Tiptap) non repliée : affichée, sans risque.

### Passage 2 (revue anticipée, après la reprise 1) — CHANGES REQUESTED, chaîne arrêtée

Relecteur indépendant, diff de la reprise lu d'abord. api-mcp : aucun impact.

État des constats du passage 1 : B1 corrigé ; **B2 non corrigé en général** (R1) ; B3 corrigé ; B4 corrigé mais
sur-corrigé (R3) ; accusés (panne, disparu), page lointaine, weda2 (téléchargement, garde, `canSend`, titre, pièce
demandée), mobile (défilement, garde `isSplitSafe`, message réseau) corrigés ; pastille avant envoi corrigée sur mobile,
corrigée sur weda2 mais source de R2 ; `ReadAt` non corrigé (passé en suggestion par la reprise, à tort : il était dans la
liste « À corriger »).

#### Bloquants

- **R1 (serveur, retour de B2)** — `ConversationText.Build` forme une seule `SignatureRange` de la première à la dernière
  ligne de signature de **tout** le message, citation comprise (marques de la plateforme, `moz-signature`,
  `gmail_signature` dans le `blockquote`). Quand la réponse et le parent cité sont tous deux signés — la forme la plus
  courante, puisque `ConversationReplyComposer` cite le HTML du parent avec ses marques — la plage dépasse le début de
  l'historique, `after` est vide, et tout ce qui suit la signature de la réponse (un PS) est replié avec
  `IsSafe = true`. Une marque `<!-- signature -->` sans fermeture marque aussi tout le reste du message. Le test
  d'intégration citait un parent sans signature.
- **R2 (weda2)** — la relecture de la page 1 avant l'envoi (`send` → `loadRecent$(…).subscribe({ complete: transmit })`)
  échappe au `switchMap` sur la conversation ouverte et ne vérifie pas `loadSeq`. Si le médecin ouvre un autre fil
  pendant cette relecture, l'ancienne page s'écrit dans la nouvelle vue, puis la réponse part avec le `messageId` du fil
  B et les destinataires du fil A : l'historique cité (B) va aux correspondants de A. « Vue email » dans la même fenêtre
  perd la réponse en silence. (Même schéma sur mobile, `send` → `post`, moins exposé : suggestion.)
- **R3 (mobile)** — toute relecture de la page 1 retire les bulles « prêt à partir » (`queued`), y compris quand la
  réponse n'a pas été confirmée : retour de `/pending-emails` sans confirmer, toucher de la pastille, relecture avant
  envoi. La réponse n'est pas partie et le chat ne le dit plus (DoD : « prêt à partir » + « Confirmer avec ma carte »).
  Le test `B4 — a page 1 reload drops a local « prêt à partir » bubble` affirme ce défaut.

#### Pourquoi la chaîne s'arrête

R1 est le bloquant B2 du passage 1, revenu après la reprise : la règle 13 (« un bloquant qui revient après une reprise
arrête la chaîne ») s'applique, même si la reprise 2 reste permise par le plafond. Question écrite :
`questions/task-487.md`.

#### Suggestions (non bloquantes)

- `HasRichContent` ne compte que les lignes avant la signature : un tableau dans un PS n'est pas coupé.
- `MailExportService` rend `NotFound` pour une `ImapCommandException` (refus temporaire possible) : l'accusé serait marqué
  « inconnu » à tort ; une exception de `OpenAsync` fait encore tomber la requête.
- weda2 : `downloadError` survit à `reset()` (l'erreur d'un fil s'affiche dans le suivant).
- mobile : relecture et pastille retirent aussi les bulles « envoyé » pas encore relues du serveur (elles réapparaissent).

#### À corriger par la reprise (passage 2, après relèvement de la règle 13 le 2026-11-18)

La chaîne avait été arrêtée par l'ancienne règle de récidive ; l'humain a relevé la règle 13 (5 reprises, un bloquant
toléré une fois en récidive) et demandé la reprise 2.

- **R1 (récidive de B2)** — signature : ne retenir que la **première** suite de lignes de signature, **hors citation**
  (profondeur de citation 0), et seulement si elle **se termine avant l'historique** ; une marque d'ouverture sans
  fermeture ne replie rien. Corpus : un cas où la réponse **et** le parent cité sont signés (marques de la plateforme et
  `moz-signature`), avec un PS entre la signature et la citation. Test d'intégration vu rouge sur la même forme.
- **R2 (weda2)** — l'envoi capture le fil ouvert, ses destinataires et le numéro de chargement ; la relecture d'avant
  envoi n'écrit rien et n'envoie rien si le fil a changé (ou si la vue email a été ouverte). Même garde sur mobile
  (`send` → `post` : identifiant du fil revérifié).
- **R3 (mobile)** — une bulle « prêt à partir » n'est retirée qu'une fois l'envoi en attente parti ou abandonné (liste
  `pending-emails`), jamais par une simple relecture de la page 1 ; les bulles « envoyé » restent jusqu'à ce que la bulle
  du serveur les relaie. Corriger le test qui affirmait le défaut.
- **`ReadAt`** (liste du passage 1, oublié) — l'instant de lecture vient de la date d'arrivée (UTC) seulement.
- Défauts réels du passage 2 corrigés dans la même passe : `HasRichContent` compte les lignes du corps hors signature
  (un tableau dans un PS coupe la bulle) ; weda2 : `downloadError` remis à zéro au changement de fil.

### Passage 3 (revue anticipée, après la reprise 2) — APPROVED

Relecteur indépendant, diff de la reprise 2 lu d'abord. api-mcp : aucun impact.

**approved at** : dtos-mss `1e4c449` ; api-mail `7f80eaf8` ; client-mobile `3921a69` ; client-angular : arbre de travail
de `feature/nova-mss-weda-integration` au 2026-11-18 (code-only).

- R1 (récidive de B2) : **corrigé** — signature numérotée hors citation, seule la première fermée retenue, fin avant
  l'historique ; cas tracés (marque ouverte puis parent signé, fin dans la citation, en-têtes Outlook, conteneurs
  imbriqués, deux ouvertures) : rien de non vérifié n'est replié.
- R2 (weda2) : **corrigé**. R3 (mobile) : **corrigé**. `ReadAt`, `HasRichContent`, `downloadError`, garde R2 mobile :
  **corrigés**.
- Règle 1b : rien de nouveau n'est atteignable par une route sans test d'intégration vu rouge (table du Develop log,
  M30-M37). Règle 14 : imputation inchangée.

#### Arbitrage humain (ajout du passage 3)

- **Réponse abandonnée sans le dire** : si le médecin change de fil (ou ouvre « Vue email ») pendant la relecture qui
  précède l'envoi, rien ne part (correctif R2), mais la saisie et la bulle « envoi… » disparaissent sans message. Choix
  produit : envoyer quand même au fil d'origine (destinataires relus, sans rien écrire dans la vue), ou le dire et rendre
  le brouillon. Recommandation : le dire et rendre le brouillon.

#### Suggestions (non bloquantes)

- mobile : l'identification d'une réponse en attente compare le texte à tout le corps, citation comprise, liste du plus
  ancien au plus récent ; préférer « commence par le texte saisi » et une date de création postérieure à l'envoi.
- mobile : `loadFirstPage` revérifie `seq` après l'attente de `pending-emails` (changement de route dans la même page).
- mobile : la réconciliation après un 202 sort du `try` de `post` (une exception marquerait « erreur » une réponse déjà
  en file, et « Réessayer » la doublerait).
- weda2 : garde `seq` sur l'erreur de téléchargement (erreur tardive affichée dans le fil suivant).
- mobile : après confirmation, la réponse disparaît le temps que la copie d'Envoyés arrive (inchangé, pas une
  régression).

## Sonar log

Projet `healthplatform-api-mail` (SonarQube 9.9.8), branche `feat/task-487-conversation-en-chat-lire-le-fil-et`.
2 analyses (build Release + 5 suites avec couverture OpenCover + scan).

| Itération | Constat new code | Correctif | Commit |
|---|---|---|---|
| 1 | 2 × S3604 (MINOR) — `ConversationService.Texts` : `_read = []` et `_indexes = bubbles.Select(…)` initialisés en champ d'une classe privée à constructeur primaire | constructeur explicite, aucun changement de comportement (refactor pur, suites inchangées) | api-mail `34451a35` |
| 2 | 0 | — | — |

### KPIs qualité (baseline → final)

| Indicateur | Baseline (avant task) | Final |
|---|---|---|
| Quality Gate | OK | **OK** |
| Bugs | 0 | 0 |
| Vulnérabilités | 0 | 0 |
| Code smells | 0 | 0 (2 pendant l'itération 1, corrigés) |
| Security hotspots | 0 | 0 |
| Couverture | 97,8 % | 97,7 % |
| Couverture du new code | — | 96,2 % (seuil ≥ 95 %) |
| Duplication | 0,3 % | 0,3 % (new code 0,04 %) |
| Fiabilité / Sécurité / Maintenabilité | A / A / A | A / A / A |

Suites jouées par l'analyse : domaine 361, application 4322, infrastructure 749, api 1382, intégration 1357/1373
(16 ignorés), **0 échec** — en excluant seulement
`ImapSessionSweepIntegrationTests.ConnectAsync_WhileTheSweepRunsDuringTheConnection_OpensTheSessionAsync` (bloque une
heure, code identique à `develop`). Vert api-mail **non marqué** pour cette raison : `/review` rejouera.
Convention : `conventions/csharp.md` S3604 → Occurrences 6 (récidive sur du code frais).

## Lint log

- Mode : A (chaîné), scope `tag:scope:mss` (défaut — `mss`, `mss-lib`, `mss-e2e`), base `origin/next` ; aucun override
  `**LintBase**` / `**LintProjects**`.
- Arbre : branche `feature/nova-mss-weda-integration` (code-only, rien de commité) ; même `git status` avant / après
  l'étape (44 fichiers `.ts`/`.html` de la task).
- Comptage : `npx eslint libs/mss apps/mss e2e/mss-e2e --format json` (contournement de task-367 : `--projects` ne
  restreint pas `nx affected`, `--output-file` en chemin Windows absolu échoue) ; attribution à la task par
  `git diff -U0 HEAD` + fichiers non suivis.
- Baseline : **0 error** / 100 warnings (75 `jsdoc/require-example`, 22 `max-lines`, 3 `complexity`).
- Warning né de la task : **1** — `max-lines` sur `mail-conversation.component.ts` (fichier neuf, 790 lignes, seuil
  500). **Accepté** (best-effort, avertissement) : découper le conteneur du chat après l'approbation de la revue
  rouvrirait une revue pour un gain de lisibilité seul ; à reprendre si le composant grossit. Les 99 autres sont
  antérieurs (aucun sur une ligne ajoutée).
- Final : 0 error / 100 warnings. Itérations : 0 / 5 (rien à corriger, aucun fichier modifié).
- Build / tests : non rejoués — arbre inchangé, vert de `/develop` toujours valide (`green.py check` : `5fbc7e28`).

## Lint mobile log

- Branche `feat/task-487-conversation-en-chat-lire-le-fil-et` @ `3921a69`, arbre propre.
- Baseline : `npm run lint` (ng lint) → **All files pass linting** : 0 error / 0 warning.
- Itérations : 0 / 5, aucun commit. Build / tests non rejoués : vert de `/develop` valide sur ce code exact
  (`green.py check` : `3921a69e`).

## Timings

*(généré par `tools/timing/report.sh --task task-487 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 29 s | — | — | — | — |
| /develop | ok | 14 min 37 s | 10 (1 min 27 s) | 42 (1 h 35 min) | — | dtos-mss 1B/0T, api-mail 9B/42T, reprise 2 |
| /review-code | ok | 8 min 26 s | — | — | — | — |
| /sonar | ok | 23 min 47 s | 2 (1 min 45 s) | 10 (16 min 11 s) | 4 (1 min 35 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 1 min 27 s | — | — | — | — |
| /lint-mobile | ok | 18 s | — | — | — | — |
| **Total cycle** | | **49 min 07 s** | **12 (3 min 12 s)** | **52 (1 h 52 min)** | **4 (1 min 35 s)** | |

Autres commandes mesurées : lint ×4 (24 s), nuget-wait ×1 (19 s)
