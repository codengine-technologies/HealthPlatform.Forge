# todo-task-487.md — Conversation en chat : lire le fil et répondre

**Repos**: api-mail, dtos-mss, client-mobile, client-angular
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
