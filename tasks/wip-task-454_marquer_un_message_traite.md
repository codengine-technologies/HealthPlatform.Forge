# todo-task-454.md — Marquer un message traité

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 1
**Dependencies**: done-task-453 (ancrage des états de travail), done-task-466 (date de début du suivi), done-task-456 (tags système, dont « Pour info »)
**Epic**: E024

> **Mise à jour du 2026-11-12 (décision humaine)** : task-465 (mesure de charge) est **abandonnée** — traitement jugé trop lourd pour l'API. La dépendance et les indicateurs de tableau de bord qu'elle portait sont retirés. L'extraction des usages sera reprise plus tard par un **cron job hors de l'API**, sur la base d'un rapport journalier.

**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 7 de l'analyse (volume, peur de rater :
2/5). Pour un médecin, un message n'est pas « lu » ou « non lu » : il est **pris en charge** ou non.

> **Origine.** `Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`, manque A1. Décisions de l'humain du
> 2026-11-11 : traiter marque aussi le message comme lu, mais lire ne le traite pas ; l'état appartient à la boîte.
>
> **Reprise du 2026-11-12 (décisions de l'humain).** Un clic « Traité » sur chaque message, y compris sans importance,
> serait trop lourd, et un « tout marquer traité » viderait le signal. D'où :
> - n'entrent dans « À traiter » que les messages **suivis** (task-466 : arrivés après la date de début du suivi —
>   une première synchronisation ne réclame rien sur deux ans d'historique) et qui ne portent pas le tag système **« Pour info »** (task-456) ;
> - les **gestes naturels** (répondre, ranger, rattacher, acquitter) traitent le message ; le bouton sert au reste ;
> - le traitement groupé existe, mais **n'acquitte jamais de biologie** : la règle du 2026-11-11 « marquer traité fait
>   passer l'acquittement à « Résolu » » est **retirée** (risque de résoudre en masse des résultats jamais lus).

> **Décisions humaines du 2026-11-17, au `/develop`** (task-456 mergée entre-temps : vues par tag avec filtre
> Tous / Non lus retenu par personne, badge des non lus, un tag sans message n'est pas affiché) :
> - **Compteurs** : un **sélecteur en tête de la liste des dossiers** bascule tous les compteurs (dossiers et tags)
>   entre **« À traiter »** (par défaut) et **« Non lus »**. *Lecture de la forge* : ce choix est retenu dans les
>   réglages de la **personne** (`UserSetting`), comme le filtre de task-456.
> - **Filtres** : un **3e filtre « À traiter »** s'ajoute à Tous / Non lus, dans la Boîte de réception comme dans les
>   vues par tag, toujours retenu par personne. Il remplace la règle « les vues `tag:XXX` gardent les non traités au
>   lieu des non lus » : un message urgent lu mais non traité se retrouve par le filtre « À traiter ».
> - Les lignes « Ce qui est établi » sur les vues d'étiquettes (non lus seulement) et l'étape 5 du Manual Test Plan
>   (vue « Courriers et comptes rendus », retirée par task-456) sont périmées : la vue « Biologie » et la Boîte de
>   réception filtrée les remplacent.

## Ce qui est établi

Lecture du code au 2026-11-11 :

- **Aucun état « traité » n'existe.** `Mail` (`Domain/Entities/MailDb/Mail.cs`) porte `IsRead`, `IsImportant`,
  `IsAnswered`, `IsDraft`, `IsCancelled`. Aucun mot-clé IMAP personnalisé n'est utilisé.
- L'acquittement de biologie est le seul « traité » existant, par document et pour la biologie seulement :
  - entité `BiologyAck`, en ajout seul ;
  - actions `Acknowledged`, `PatientCalled`, `PatientSummoned`, `ReferredToColleague`, `MarkResolved` ;
  - état dérivé de la dernière action (`BiologyAckRepository.GetStateAsync`) ;
  - auteurs dénormalisés (`CreatedByRpps/FirstName/LastName/Role`).
- **Les compteurs ne peuvent pas venir des clients.** weda2 filtre sur la page chargée (`MailStateService`, pagination
  côté client sur `folder.uids`), le mobile sur le lot de 30. Seuls « Bio à acquitter »
  (`/biology-acks/pending-mail-uids/page`) et la vue patient ont des pages servies par le serveur.
- **Aucun évènement temps réel n'est poussé** pour un changement d'état. `ISseMailEventBroker` ne diffuse que
  `EmailsEnriched` et `TagsUpdated`. En boîte partagée, une personne ne voit pas ce que l'autre vient de faire.
- Les vues d'étiquettes IA (`GetTagFoldersAsync`, `CurrentInboxMailsAsync`) ne gardent que les **non lus**.
- Points d'accroche : `MailController` (`PUT emails/{id}/status/*`, `bulk/status/*`), `EmailFlagService`, panneau
  « Actions & dossier » de weda2 (`MailSidePanelComponent`), balayages du mobile (`ion-item-sliding` dans
  `M/features/mail/components/mail-list/mail-list.component.html`), toast d'annulation (suppression seulement).

## Objective

Le praticien, la secrétaire ou le délégataire voit ce qui **reste à traiter** dans la boîte, pas seulement ce qui n'est
pas lu. La plupart des messages sortent de « À traiter » **sans geste dédié**, par ce que la personne fait déjà
(répondre, ranger, rattacher, acquitter). Le bouton « Traité » ne sert qu'au reste. Chacun voit **qui** a traité et
**quand**.

Règles :
- **Entrent dans « À traiter »** les messages qui remplissent les deux conditions :
  - **suivis** au sens de task-466 (arrivés après la date de début du suivi de la boîte) ;
  - **sans** le tag système « Pour info » de task-456 (révisé le 2026-11-16 : la « nature » est devenue un jeu de tags).
  - N'y entrent **pas** : les messages tagués « Pour info » (copies, messages automatiques, accusés de lecture et de remise,
    notifications), ni l'historique antérieur au suivi.
- **Sortie implicite par les gestes naturels** — le message passe « traité », au nom de la personne qui a fait le
  geste :
  - répondre, répondre à tous ou transférer ;
  - le ranger hors de la Boîte de réception (archive, dossier) ;
  - rattacher un de ses documents à un dossier patient, ou l'importer dans le dossier Weda ;
  - acquitter « Résolu » **tous** ses comptes rendus de biologie signalés.
  - Le libellé dit le geste : « Traité par {Prénom NOM} ({rôle}) le … — répondu », « — rangé », « — rattaché »,
    « — résultats acquittés ».
- **Le bouton « Traité »** pour le reste : dans la ligne (au survol sur weda2), dans le panneau « Actions & dossier »,
  dans le détail mobile, et **en premier balayage sur le mobile**.
- **« Remettre à traiter »** sur **n'importe quel** message, y compris un message historique ou classé « Pour info » :
  il entre alors dans « À traiter », quelle que soit sa date ou ses tags.
- **Traité implique lu** ; lire ne traite pas.
- **La biologie n'est jamais résolue par « Traité »** (décision humaine du 2026-11-12, remplace celle du
  2026-11-11) :
  - marquer traité, seul ou en groupe, **n'écrit aucun acquittement** ;
  - un message porteur d'un compte rendu signalé **non acquitté** reste dans « À traiter » tant que ce compte rendu
    n'est pas résolu : le geste « Traité » sur lui est refusé avec l'avis « Ce compte rendu de biologie reste à
    acquitter » et un lien vers le panneau d'acquittement.
  - Remettre un message « à traiter » ne retire aucun acquittement.
- **Traitement groupé** (repris de task-456) :
  - sur une sélection, et sur la vue affichée : « Traiter les N messages affichés », avec confirmation du nombre et
    toast « N messages traités — Annuler » ;
  - les messages porteurs d'un résultat non acquitté sont **exclus** et restent à traiter ; l'avis le dit :
    « N comptes rendus de biologie restent à acquitter » ;
  - dans la vue **Biologie**, « Traiter les résultats sans anomalie » : les messages dont aucun résultat ne porte
    l'indicateur d'anomalie posé par le laboratoire (garde-fou de task-392 : jamais une comparaison aux bornes). Ils
    n'ont rien à acquitter ; aucun acquittement n'est écrit.
- **Annulation visible** : toast « Message traité — Annuler » pendant 6 s, sur le modèle de la suppression
  (`mail-pending-delete.service`), généralisé aux deux clients ; le traitement groupé s'annule en bloc.
- **L'état appartient à la boîte** (règle 14) : traité par une personne, il l'est pour toute l'équipe. Libellé
  « Traité par {Prénom NOM} ({rôle}) le {date} à {heure} ».
- **Reste à traiter** :
  - un compteur par dossier et **par vue de tag** (task-456), calculé par le serveur dans la base de la boîte ;
  - un filtre « À traiter » à côté de Tous / Non lus, servi en pages par le serveur ;
  - sur le tableau de bord, une tuile « À traiter », derrière le flag `dashboard_widget_to_handle` (weda2 et mobile).
- **Étiquettes IA** : les vues `tag:XXX` gardent les messages **non traités** au lieu des non lus. Un message urgent lu
  mais non traité y reste.
- **Temps réel** : un nouvel évènement d'état de message, publié par boîte et par dossier, met à jour la ligne et les
  compteurs chez toutes les personnes ouvertes sur la boîte.
- **Hors ligne** (titulaire, weda2) : le geste rejoint la file des gestes hors ligne (`PendingAction`), comme lu ou
  signalé.
- **Plateforme seulement** : l'état « traité » n'est pas visible d'un autre client IMAP. C'est assumé et dit dans
  l'aide. Un rangement fait depuis un autre client n'est pas un geste de la plateforme : il ne traite pas le message.
- **Ancrage** : l'état suit le modèle de task-453. Il survit à un déplacement hors plateforme.

### Hors périmètre

- Reporter un message : task-455. Attribuer à quelqu'un : task-457.
- La date de début du suivi et l'état « Antérieur au suivi » : task-466. Les tags système (dont « Pour info ») : task-456.
- Les dossiers Envoyés, Brouillons et Corbeille n'ont pas d'état « à traiter ».
- La règle « répondre = traité » ne vérifie pas que la réponse clôt l'échange : la relance sans réponse (task-462)
  couvre une réponse qui appelle une suite.

## Definition of Done

- [ ] Contrat : état de traitement exposé dans `MailDto` (traité oui ou non, par qui : RPPS, nom, rôle ; quand ;
      geste : bouton, réponse, rangement, rattachement, acquittement, groupe), compteur « à traiter » par dossier et
      par tag dans `FolderDto` ; paquet `HealthPlatform.Dtos.Mss` publié (`/publish-dtos`) et consommateurs à jour.
- [ ] Migration FluentMigrator de la table d'état dans la base de la boîte, ancrée selon l'ADR de task-453 ; audit de
      migration (règle 7c) ; modèle EF identique.
- [ ] Nouveaux actes d'audit `MailMarkedHandled` et `MailMarkedToHandle` en fin de `AuditActionType` (avec le geste),
      miroirs TypeScript, famille `HealthDataAccess`, contrôleurs marqués `[Audited]`.
- [ ] Tests unitaires de la règle d'entrée : message suivi sans le tag « Pour info » → à traiter ; tagué « Pour info » → non ;
      historique antérieur au suivi → non ; « Remettre à traiter » sur un historique ou un « Pour info » → à traiter.
- [ ] Tests unitaires des sorties : traité ⇒ lu ; lu ⇏ traité ; réponse, transfert, rangement, rattachement,
      acquittement « Résolu » de tous les comptes rendus ⇒ traité avec le bon geste ; « Traité » **n'écrit aucun
      acquittement** ; « Traité » refusé sur un message porteur d'un résultat non acquitté ; remettre à traiter ne
      retire aucun acquittement ; vue d'étiquette sur « non traité ».
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `PUT api/v1/Mail/emails/{id}/status/handled` (et
      `to-handle`) : `MailDto` relu par `GET …/emails/{ids}` avec l'état, l'auteur, l'heure et le geste ; `IsRead`
      vrai ; compteur « à traiter » du dossier et de ses tags diminué de 1. Cas d'échec : message inconnu → 404 en
      `ProblemDetails` ; message porteur d'un résultat non acquitté → 409 en `ProblemDetails`, aucun acquittement
      écrit. Vu rouge.
- [ ] **Test d'intégration du traitement groupé** (route groupée et « traiter la vue ») : sur un lot qui contient un
      message à résultat non acquitté, celui-ci reste à traiter, la réponse compte les messages exclus, et
      `LastBiologyAck` relu est **inchangé** ; « Traiter les résultats sans anomalie » ne traite que les messages sans
      indicateur d'anomalie. Vu rouge (avec la règle d'avant, qui résolvait la biologie).
- [ ] **Tests d'intégration des gestes naturels** : envoyer une réponse, ranger le message, rattacher son document à un
      patient, acquitter « Résolu » son dernier compte rendu : chaque geste, fait par la route existante, rend le
      message traité au nom de la personne, relu par `GET …/emails/{ids}`. Vus rouges.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire traite (bouton puis réponse) ; le titulaire
      relit le message traité « par » le délégataire ; la trace d'audit porte le délégataire (RPPS, nom, rôle), jamais
      la boîte.
- [ ] Test d'intégration de l'évènement temps réel : une personne traite, l'abonné de l'autre personne reçoit l'état.
- [ ] Tests de composant (weda2 et mobile), chacun vu rouge par mutation : geste Traité, remettre à traiter, annuler
      dans le toast, libellé « Traité par … — {geste} », refus avec l'avis biologie, traitement groupé et son avis
      « N comptes rendus de biologie restent à acquitter », filtre « À traiter », compteurs par tag, tuile
      « À traiter », balayage Traité en premier.
- [ ] **Scénarios e2e** ajoutés à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis, chacun vu rouge par mutation :
      - `E2E-TRIAGE-001` v1 : traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet ;
      - `E2E-TRIAGE-002` v1 : « Traiter les N messages affichés » laisse le compte rendu de biologie non acquitté à
        traiter, avec l'avis, et son acquittement est inchangé ;
      - `E2E-TRIAGE-006` v1 (repris de task-456) : « Traiter les résultats sans anomalie » laisse le résultat anormal
        à traiter ;
      - `E2E-TRIAGE-007` v1 : répondre à un message le fait sortir de « À traiter », libellé « — répondu » ;
      - `E2E-SHARED-003` v1 : le délégataire traite un message, le titulaire le voit traité « par » le délégataire.
- [ ] Les balayages existants (`swipe-read|flag|move|delete-*`, corbeille de task-142) restent verts ; tests adaptés à
      l'ordre nouveau.
- [ ] `data-testid` sur chaque élément interactif ajouté ; libellés selon les conventions du module ; aucune donnée de
      santé dans les libellés ni les logs.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, `Dtos`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`), weda2 (`cd Client/Angular/front && npm start`) et le
   mobile (`cd Client/Mobile && npm start`), sur une boîte où un délégataire est rattaché, la date de début du suivi
   posée (task-466).
2. weda2, titulaire : le compteur « À traiter » ne compte ni l'historique, ni les messages « Pour info ». Marquer un
   courrier « Traité » : il sort du filtre, le compteur baisse, le toast propose « Annuler ».
3. Répondre à un autre courrier : il sort de « À traiter », libellé « Traité par {vous} — répondu ». Ranger un
   troisième dans un dossier : « — rangé ».
4. Ouvrir un compte rendu de biologie à acquitter, cliquer « Traité » : refus, avis « Ce compte rendu de biologie reste
   à acquitter ». L'acquitter « Résolu » : le message sort de « À traiter », libellé « — résultats acquittés ».
5. Vue « Courriers et comptes rendus » : « Traiter les N messages affichés ». Vue « Biologie » : « Traiter les
   résultats sans anomalie » ; les résultats anormaux restent, l'avis donne leur nombre, leurs acquittements sont
   inchangés.
6. Mobile, délégataire sur la même boîte : balayer un message, choisir « Traité ». Sur weda2, sans recharger, le
   titulaire voit « Traité par {délégataire} (délégataire) le … ».
7. Sur un message ancien (avant la date de début du suivi), « Remettre à traiter » : il apparaît dans « À traiter ».
8. Ouvrir la vue d'étiquette « Urgent » : un message urgent lu mais non traité y figure toujours.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — organisation du travail ; prolonge le suivi des comptes rendus de biologie
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun identifiant patient manipulé
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : titulaire, membre et délégataire peuvent traiter, sous verdict récent de l'opérateur (règle 14) ;
  rien sans verdict ; traiter ne donne jamais le droit d'acquitter à la place de l'acquittement explicite
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `MailMarkedHandled` (avec le geste : bouton, réponse, rangement, rattachement, acquittement,
  groupe) et `MailMarkedToHandle`, au nom de la personne réelle (RPPS, nom PSC, rôle, boîte, instant, objet), famille
  `HealthDataAccess`, 3 653 jours ; aucun `BiologyMarkedResolved` n'est produit par « Traité »
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte, environnement HDS de production
- **AIPD / impact RGPD** : à mettre à jour — l'auteur du traitement est visible des autres personnes de la boîte
  (même finalité que le journal de la boîte, E020)

## Timings

*(généré par `tools/timing/report.sh --task task-454 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 30 s | — | — | — | — |
| /develop | ok | 30 min 40 s | 10 (1 min 25 s) | 23 (1 h 25 min) | — | dtos-mss 1B/0T, api-mail 3B/13T, client-mobile 5B/6T, client-angular 1B/4T, reprise 1 |
| /review-code | ok | 4 min 24 s | — | — | — | — |
| /sonar | ok | 37 min 25 s | 4 (1 min 35 s) | 11 (23 min 05 s) | 4 (1 min 32 s) | 2 itération(s), api-mail 4B/11T |
| /lint-angular | ok | 9 min 19 s | 1 (22 s) | 1 (1 min 49 s) | — | 3 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 34 s | — | — | — | — |
| **Total cycle** | | **1 h 22 min** | **15 (3 min 23 s)** | **35 (1 h 50 min)** | **4 (1 min 32 s)** | |

Autres commandes mesurées : lint ×8 (1 min 11 s), nuget-wait ×3 (59 s), restore ×1 (3.9 s)

## Branches
- `api-mail` (pushed) : feat/task-454-marquer-un-message-traite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-454-marquer-un-message-traite (depuis `develop` `fe801f26`, task-456 incluse)
- `client-mobile` (pushed) : feat/task-454-marquer-un-message-traite — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-454-marquer-un-message-traite (depuis `develop` `124578ab`)
- `dtos-mss` (branche paresseuse) : créée par `/develop` s'il touche un contrat
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, qui porte encore les fichiers non commités de task-486 et task-456) — l'humain gère branche, commit, push, PR TFS

## Develop log

### Plan (2026-11-17, avant le code)

Écrit avant le code, pour qu'il survive à un résumé de contexte. Il est appliqué dans cet ordre : dtos-mss, api-mail,
weda2, mobile, e2e.

**Règle « à traiter »** (domaine, `MailHandlingRule`). Un message est à traiter si :
1. son dossier n'est ni Envoyés, ni Brouillons, ni Corbeille ;
2. et l'une de ces conditions est vraie :
   - il porte un compte rendu de biologie **signalé, suivi et non résolu** : il est alors à traiter quel que soit
     son état ;
   - sinon, un état explicite **« remis à traiter »** existe ;
   - sinon, il n'a pas d'état « traité » et il est **suivi** (task-466) sans le tag système **« Pour info »**
     (task-456).

Un état explicite « traité » le sort, sauf en présence de la biologie en attente du premier cas.

**Données** (base de la boîte) : table `MailHandlingStates`, une ligne par message (état courant). L'historique est
le journal d'audit.
- Clé : le **Message-ID**, comme `MailReply` (task-459) et comme le prévoit l'ADR de task-453, ligne 113 : un état de
  message ancré sur le seul Message-ID. Pas de clé étrangère vers `Mails` : l'état survit au déplacement et à la purge
  par construction, sans relieur. Toutes les copies d'un même message partagent l'état.
- Un message **sans Message-ID** ne peut pas porter d'état : refus 409 `ProblemDetails`. C'est une limite assumée,
  rarissime en MSSanté.
- Colonnes : `MessageId` (unique), `State` (Handled 0 / ToHandle 1), `Gesture`, `ByRpps`, `ByFirstName`,
  `ByLastName`, `ByRole`, `At`.

**Gestes et routes** :
- Bouton : `PUT folders/{f}/emails/{uid}/status/handled`, corps facultatif `{ gesture }` (Button, ou WedaImport
  pour l'import dans le dossier Weda, fait côté client).
- `PUT …/status/to-handle` : remettre à traiter. Le toast « Annuler » s'en sert aussi.
- Groupé : `PUT folders/{f}/emails/bulk/status/handled` (UID) ; `PUT tags/emails/status/handled?tag=…&filter=…`
  (la vue par tag) ; `&withoutAnomaly=true` pour « Traiter les résultats sans anomalie ». Le résultat compte les
  messages traités et les messages **exclus** pour biologie en attente.
- Gestes naturels, posés côté serveur au nom de la personne :
  - réponse et réponse à tous (`MailReplyRecorder`) ;
  - transfert (nouveau champ `MailDto.ForwardedMessageId`, rempli par les clients) ;
  - rangement hors de la Boîte de réception (déplacements unitaires, groupés et `bulk-actions`) ;
  - rattachement d'un document à un patient ;
  - « Résolu » quand il ne reste aucun compte rendu signalé non résolu.
- **« Traité » n'écrit jamais d'acquittement.** Le refus est un 409 `ProblemDetails` quand un compte rendu suivi
  reste à acquitter.

**Contrat** (dtos-mss) :
- `MailDto.Handling` : `MailHandlingDto`, avec `IsToHandle`, `IsHandled`, `By` (`ActorDto`), `At`, `Gesture`.
- `MailDto.ForwardedMessageId`.
- `FolderDto.ToHandleCount`.
- Nouveaux types : `MailHandlingGesture`, `MailHandlingRequestDto`, `MailHandlingBulkResultDto`.
- `TagViewFilterType.ToHandle`, `InboxFilterType.ToHandle`.
- `UserSettingsDto.FolderCounter` (`FolderCounterMode` : ToHandle par défaut, ou Unread) : le sélecteur décidé par
  l'humain.
- `AuditActionType.MailMarkedHandled = 73` et `MailMarkedToHandle = 74`.

**Compteurs et pages** :
- `ToHandleCount`, calculé en SQL dans la base de la boîte pour chaque dossier IMAP et chaque dossier de tag (génération
  courante).
- Page des UID à traiter : `GET folders/{f}/emails/to-handle/page`, sur le modèle de
  `biology-acks/pending-mail-uids/page`.
- Filtre `to-handle` sur la vue par tag.

**Audit** : `[TracedInCode(MailMarkedHandled|MailMarkedToHandle)]`, le geste dans `ServerRequest`, au nom de la
personne réelle, famille `HealthDataAccess` par défaut.

**Temps réel** : nouvel évènement SSE `MailHandlingChanged` (dossier, UID, `MailHandlingDto`), publié par boîte et par
dossier.

**Hors ligne** : l'état n'existe qu'en base, il s'écrit donc aussi hors ligne. Pas de `PendingAction`, ce qui évite un
rejeu sans personne (règle 14).

### Implémentation (2026-11-17)

- **dtos-mss** : contrat publié (paquet `617.0.0`, commit `8584a008`) ; consommateurs .NET bumpés (api-mail `d9232f32`).
- **api-mail** : table `MailHandlingStates` (migration `20261117150000_AddMailHandlingStates`, `Down` = suppression de la
  table, aucune donnée existante touchée — règle 7c relue), règle `MailHandlingRule` (domaine), requêtes SQL
  `MailHandlingQueries` (compteurs, pages, filtre de vue), service `MailHandlingService`, contrôleur
  `MailHandlingController` (5 routes), gestes naturels branchés (réponse et transfert dans `OutgoingMailService`,
  rangement unitaire et groupé dans `MailController` et `BulkMailActionService`, rattachement dans
  `MedicalDocumentsController`, « Résolu » dans `BiologyAckService`), évènement SSE `MailHandlingChanged`, flag
  `dashboard_widget_to_handle` (fail-open, comme les autres widgets, semé par le banc).
- **weda2** (code-only) : modèles, API, `MailHandlingService` (geste, toast « Annuler » 6 s, avis biologie), filtre
  « À traiter » (boîte et vues par tag, servi en pages), sélecteur des compteurs en tête des dossiers, bouton de ligne,
  détail, sélection, « Traiter les N messages affichés » et « sans anomalie », tuile du tableau de bord derrière le flag,
  SSE.
- **client-mobile** : en cours (même découpage).

### Preuves rouges — api-mail (règle 1b), par mutation

Script `mutate.py` (scratchpad), build Release + test d'intégration ciblé par mutant, restauration vérifiée
(`RESTAURATION | build ok`, aucun `.mutbak` restant). Tests : `FolderOperationsEndToEndTests.Handling`
(UseCaseHttpHost, vraie pile HTTP, PostgreSQL et Dovecot du fixture) et `ReplyBannerEndToEndTests.ReplyingAndForwarding…`.

| Comportement (route) | Mutation | Test vu rouge |
|---|---|---|
| `PUT …/status/handled` écrit l'état | M1 état non écrit | `TheHandledButton_…` (Assert.Equal) |
| refus 409 sur biologie en attente | M2 refus retiré | `HandledIsRefused_…` (attendu 409, reçu 200) |
| groupé : exclusion biologie | M3 règle d'avant (sans exclusion) | `TheBulkHandling_…` |
| vue Biologie « sans anomalie » | M4 filtre ignoré | `HandlingTheBiologyViewWithoutAnomaly_…` |
| rangement hors Boîte de réception | M5 geste non posé | `TidyingAMessageOutOfTheInbox_…` |
| rattachement d'un document | M6 geste non posé | `AttachingADocumentToAPatient_…` |
| « Résolu » du dernier compte rendu | M7 geste non posé | `AttachingADocumentToAPatient_…` |
| réponse | M8 geste non posé | `ReplyingAndForwarding_…` |
| transfert (`ForwardedMessageId`) | M9 geste non posé | `ReplyingAndForwarding_…` |
| SQL « remis à traiter » (compteur, page, filtre) | M10 branche retirée | `TheToHandleCounterPageAndTagFilter_…` |
| compteurs posés sur `GET folders` | M11 non posés | `TheHandledButton_…` |
| imputation à la personne (règle 14) | M12 auteur = la boîte | `TheDelegateHandles_…` |
| évènement temps réel | M13 non publié | `TheDelegateHandles_…` (aucun appel reçu) |
| `PUT …/status/to-handle` | M14 écrit « traité » | `PuttingBackToHandle_…` |
| règle « Pour info » | M15 ignorée | `PuttingBackToHandle_…` (« Pour info » n'entre pas) |

Tests unitaires : `MailHandlingRuleTests` (12), `MailHandlingServiceTests` (11 : traité ⇒ lu, lu ⇏ traité, refus
biologie sans rien écrire, inconnu / sans Message-ID, remettre à traiter sans toucher à l'état lu, groupé exclut et
compte, rangement sans « lu », geste naturel qui n'échoue jamais, « Résolu » partiel, déplacements qui ne rangent pas).

### Preuves rouges — weda2 (tests de composant), par mutation

Script `mutate_w.py` (scratchpad), Vitest ciblé par mutant, sources restaurées (aucun `.mutbak`).

| Comportement | Mutation | Spec vue rouge |
|---|---|---|
| bouton de ligne Traité / Remettre à traiter | W1 toujours « Traité » | `mail-header.handled.spec` |
| libellé « Traité par … — geste » | W2 libellé vide | `mail-detail.handled.spec` |
| bouton Traité du détail | W3 remet à traiter | `mail-detail.handled.spec` |
| toast « Message traité » | W4 libellé ignoré | `mail-undo-toast.component.spec` |
| « Annuler » | W5 aucun appel serveur | `mail-handling.service.spec`, `mss-mail.component.handling.spec` |
| avis biologie → panneau d'acquittement | W6 panneau non demandé | `mss-mail.component.handling.spec` |
| « sans anomalie » | W7 = toute la vue | `mail-list.tag-view.spec` |
| confirmation du nombre | W8 sans confirmation | `mail-list.tag-view.spec` |
| filtre « À traiter » des vues par tag | W9 `to-handle` perdu | `mail-list.tag-view.spec`, `mail-state.service.handling.spec` |
| filtre « À traiter » servi par le serveur | W10 refiltré localement | idem |
| refus 409 reconnu | W11 | `mail-handling.service.spec`, `mss-mail.component.handling.spec` |
| avis du groupé | W12 muet | `mail-handling.service.spec` |
| sélecteur des compteurs | W13 Non lus = à traiter | `mail-state.service.handling.spec`, `mail-folder-list.tags.spec` |
| tuile « À traiter » | W14 sans filtre | `to-handle-kpi-tile.component.spec` |
| geste « répondu » | W15 perdu | `mail-handling.util.spec`, `mail-detail.handled.spec` |
| traité ⇒ lu | W16 | `mail-state.service.handling.spec` |

Correctif trouvé en écrivant l'e2e : « Annuler » rechargeait la liste avant la réponse du serveur (la ligne remise à
traiter pouvait ne pas revenir) ; le rechargement attend désormais les réponses.

`mss-lib` : 1764/1764 vert après adaptation des specs existantes (fourniture de `MailHandlingService`, flux
`handlingChanged$`, `requestedSidePanel`) ; « Traiter les N messages affichés » prend la classe `handle-btn` (ce n'est
pas un filtre, et le test task-456 « ni filtres locaux dans une vue par tag » le distinguait par `filter-btn`).

api-mcp : `mcp_impact.py check` → aucun impact.

### Passe qualité §Q — api-mail (/simplify, 4 relectures : réutilisation, simplification, efficacité, altitude)

**Appliqué** (non commité au moment de l'écriture, re-validé par la suite complète) :
- correspondance Message-ID factorisée (`WithState`) et chevrons retirés **du côté `Mails`** : l'index unique
  `UX_MailHandlingStates_MessageId` sert les deux formes (le `OR "<" + h.MessageId + ">"` l'empêchait) ; surcharges
  `string` de `StartsWith`/`EndsWith` (Npgsql ne traduit pas la surcharge `char` — vu en rejouant les tests) ;
- prédicat « Pour info » réutilisé (`ForInformation`) au lieu d'être réécrit ;
- surcharge morte `RecordGestureAsync(folderPath, uids, …)` retirée (aucun appelant) ;
- constante `INBOX` privée remplacée par `MailHandlingDefaults.InboxFolderPath` ; `Decode` du contrôleur remplacé par
  `MailController.DecodeFolderName` (rendu `internal`) ;
- « traité ⇒ lu » passe par `IEmailFlagService.UpdateEmailsReadStatusAsync` (chemin « lu » existant, sans trace
  `MailRead`), par dossier : une propagation IMAP en lot au lieu d'une par message ;
- les états relus pour la publication SSE servent aussi la réponse du geste (une lecture au lieu de deux) ;
- `Gesture = view.State?.Gesture` (l'écriture ne garde déjà le geste que d'un état traité) ; `IdSetAsync` réutilisé.

Preuves rouges rejouées après la passe : M1, M10 à M15 rouges (M13 réécrit : `if (false)` ne compile pas, CS0162).

**Écarté** (au-delà d'une passe qualité ; à juger en revue) :
- une seule requête « messages de la vue par tag » pour la page (`MailRepository.GetTagViewPageAsync`, task-456) et
  pour « Traiter les N messages affichés » (`MailHandlingRepository.GetTagViewUidsAsync`) : les deux copies filtrent
  la génération courante différemment (`CurrentGeneration` contre `CurrentInboxMailsAsync`), équivalentes en pratique ;
  refactor du code de task-456 ;
- le geste « rangé » posé une fois dans `ImapFolderService` (déplacements unitaire et groupé) plutôt que dans trois
  appelants ; le rattachement dans `PatientService` plutôt que dans le contrôleur (changerait le comportement des
  autres appelants) ; un évènement de domaine plutôt qu'une dépendance optionnelle dans huit producteurs ;
- requête « à traiter » en une passe au lieu de l'union de trois ensembles, compteurs dossiers et tags en un aller-retour
  (et mis en cache), vues d'une page en une projection : optimisations SQL à mesurer avant (règle d'or 5) ;
- index sur `Mails.MessageId` (ou colonne d'ancre normalisée) : migration, hors passe qualité ;
- un évènement SSE par lot plutôt que par message : change le contrat de l'évènement.

### Parcours e2e — voie mobile (`--serve-only`, scénarios seuls)

`conventions/e2e.md` relu **après** l'écriture des tests (étape 0 de 6b sautée, puis rattrapée) : deux consignes
appliquées en conséquence côté Angular (`depot-hors-application` : rouvrir la boîte jusqu'à l'arrivée du message ;
`catalogue-yaml-relu` : `yaml.safe_load` du catalogue, 94 scénarios). Les deux suites compilent (`tsc`).

Premier passage : 3/5 verts (TRIAGE-002, 006, 007). Deux défauts du test, corrigés :
- TRIAGE-001 : le menu des dossiers, ouvert pour lire le badge, n'était pas toujours refermé par Échap et couvrait la
  ligne au balayage suivant (`ion-menu.close()` sans effet non plus) ; refermé par le geste du médecin (« INBOX »),
  puis le filtre « À traiter » est reposé ;
- SHARED-003 : la trace d'audit porte l'auteur dans `actor.rpps` (objet `ActorDto`), pas `actorRpps`.
Second passage : 5/5 verts.

Preuves par mutation (client, `Date.now()` pour compiler ; nouveau bundle attendu dans `ngserve.log` ; `git checkout`
du fichier après chaque mutant, arbre propre à la fin) :

| Mutation | Scénario(s) rouge(s) | Assertion |
|---|---|---|
| E1 « Traité » n'appelle pas le serveur | TRIAGE-001, SHARED-003 | attente de `PUT …/status/handled` |
| E2 « Traiter la vue » n'appelle pas le serveur | TRIAGE-002 | attente de `PUT tags/emails/status/handled` |
| E3 « sans anomalie » envoyé à faux | TRIAGE-006 | attente de la requête `withoutAnomaly=true` |
| E4 réponse sans `In-Reply-To` | TRIAGE-007 | « relu du serveur, le message … est hors de « À traiter » » |
| E5 « Annuler » n'appelle pas le serveur | TRIAGE-001 | attente de `PUT …/status/to-handle` |

Témoin restauré : la voie mobile complète, rejouée par `/e2e` sur le code final.

### Parcours e2e — voie Angular (`--serve-only`, scénarios seuls)

Premier passage : 4/5 verts ; TRIAGE-001 cherchait le dossier « Boîte de réception », que weda2 affiche « INBOX »
(corrigé dans l'aide `expectInboxToHandleCounter`). Second passage : 5/5.

Preuves par mutation (weda2 code-only : sauvegarde et restauration octet pour octet ; journal du serveur de dev muet,
donc marqueur `String('MUTATION-Ax').length` qui survit à esbuild, vu servi dans les chunks avant de jouer, puis 15 s ;
restauration vérifiée et marqueur retiré du bundle après chaque mutant) :

| Mutation | Scénario(s) rouge(s) | Assertion |
|---|---|---|
| A1 « Traité » n'appelle pas le serveur | TRIAGE-001, SHARED-003 | attente de `PUT …/status/handled` |
| A2 « Traiter la vue » n'appelle pas le serveur | TRIAGE-002 | attente de `PUT tags/emails/status/handled` |
| A3 « sans anomalie » envoyé à faux | TRIAGE-006 | attente de la requête `withoutAnomaly=true` |
| A4 réponse sans `In-Reply-To` | TRIAGE-007 | « relu du serveur, le message … est hors de « À traiter » » |
| A5 « Annuler » n'appelle pas le serveur | TRIAGE-001 | attente de `PUT …/status/to-handle` |

Témoin restauré : 5/5 verts après la série.

> **À commiter sur TFS avant le merge de la PR api-mail** (conventions/e2e.md, `test-angular-non-commite`) :
> `front/e2e/mss-e2e/specs/functional.e2e.ts` et `front/e2e/mss-e2e/support/e2e-backend.ts` (scénarios
> E2E-TRIAGE-001, 002, 006, 007, E2E-SHARED-003 ; E2E-TAG-002 fixe les compteurs sur « Non lus »).

### Fin de /develop

- api-mail : `6ce18c8a` (feature) + `9eaf2062` (passe qualité), poussé ; suite complète verte deux fois (8093 puis
  8094 réussis, 0 échec) ; vert marqué.
- client-mobile : `38c487d`, `3bfae5d`, `86f269a` (passe qualité), `e07b0d6`, `bb5836f` (e2e), poussé ; 1580/1580 ;
  lint propre ; vert marqué.
- client-angular (code-only, non commité) : `nx test mss-lib` 1777/1777, `nx test weda2` 2683/2683, `nx build weda2`
  vert ; vert marqué sur l'arbre.
- dtos-mss : `8584a008`, paquet `617.0.0` publié.
- Flaky : `MailboxSwitcherComponent onAriaChanged`, 6e occurrence (conventions/angular.md).

## Sonar log

- Analyse de la branche `feat/task-454-marquer-un-message-traite` (SonarQube 9.9.8, `sonar.login`), deux passes :
  `e7b1a1ba` (code approuvé par la revue anticipée), puis `b7f20f06` (correctifs).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,7 %, 0 constat, 0 hotspot.
- Phase 1 — Issues fixées : 10 code smells (0 bug, 0 vulnérabilité, 0 hotspot), toutes dans les fichiers de la task :
  - CA1826 ×3 — `FirstOrDefault()` sur un `IReadOnlyList` (`MailHandlingService` ×2, `MailHandlingRepository`) →
    indexeur (`26459f40`) ;
  - CA1859 ×1 — `PublishAsync(IReadOnlyList<HandlingTarget>)`, relais privé → `List<HandlingTarget>` (`d90720f6`) ;
  - CA1866 ×2 — `StartsWith("<")` / `EndsWith(">")` dans `MailHandlingQueries.WithState`, expression traduite en SQL
    par EF Core : surcharge `string` gardée, CA1866 suspendue localement avec sa raison, comme CA1845 (`8b6aa219`) ;
  - CA1861 ×4 — `SequenceEqual(new[] { … })` dans des `Arg.Is` de `MailHandlingServiceTests` → champs
    `static readonly` (`9e48ef50`). Forme exacte de task-449 et task-459 : le contrôle mécanique de
    `agents/develop.md` §Q 2b l'aurait trouvée, il n'a pas été joué (récidive sur la lecture).
- Phase 1 — Tests ajoutés : 4 (`b7f20f06`), chacun vu rouge par mutation puis restauré :
  - intégration `InvalidHandlingRequests_AreRefusedIn400_AndHandleNothing` (vraie pile, problem+json) : geste
    `Bulk` sur la route du bouton, sélection vide, vue sans tag, annulation au-delà de 2 000 messages → 400 avec leur
    `detail`, compteurs et état inchangés. Quatre mutations, une par garde : chacune rouge (« Attendu 400, reçu 200 »,
    ou 404 pour la vue sans tag) ;
  - unitaires `MailHandlingServiceTests` : « remettre à traiter » un message inconnu → `NotFound` sans écriture ; le
    rangement dont les messages ne peuvent être relevés ne casse pas le déplacement ; un geste sur document dont l'état
    ne peut s'écrire ne casse pas le geste. Trois mutations (garde retirée, `catch` qui ne rattrape plus) : 3 rouges.
  - Couverture new code des fichiers de la task : `MailHandlingController` 77,3 → 92,0 %, `MailHandlingService`
    96,4 → 99,3 %, `MailHandlingRepository` 90,4 % (reste : retours anticipés sur entrée vide et reprise sur conflit
    23505, non couverts — sous la cible de 95 % pour ce fichier, la cible globale du new code est tenue).
- Phase 2 (legacy) : non jouée — 0 bug, 0 vulnérabilité, 0 code smell sur tout le projet, couverture 97,8 %.
- Build / tests (Release) : ✓ vert sur `b7f20f06` — suite complète 343 / 4 279 / 749 / 1 382 / 1 348 (+16 ignorés),
  0 FATAL, totaux conformes (+3 unitaires, +1 intégration). Passe de couverture de la ré-analyse : 1 rouge
  d'outillage, `ImapSessionSweepIntegrationTests.SmtpSend_WhileTheSweepRunsOnADeadImapLink_IsDeliveredExactlyOnceAsync`
  (`DockerContainerNotFoundException` : conteneur Testcontainers disparu, hors périmètre de la task), vert rejoué
  isolé (3/3). Vert marqué (`green.py mark --by sonar`, api-mail `b7f20f06`).
- `conventions/csharp.md` : CA1861 → 9, CA1859 → 18 ; entrées créées CA1826 et CA1866 (1).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,7 % | 96,7 % | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,8 % | 97,8 % | 0 |
| Duplication | 0,4 % | 0,3 % | −0,1 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

Baseline : dernière analyse du projet avant la task (2026-11-17, `3ee8c973`) ; new code = 30 derniers jours. Première
analyse de la branche (`e7b1a1ba`) : Quality Gate OK, mais 10 code smells new code, new_coverage 96,4 %, couverture
97,7 % — tous ramenés à la baseline par cette étape.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relecteur indépendant (code seul, pas les conclusions de la forge), sur dtos-mss `8584a00`, api-mail `9eaf2062`,
client-mobile `bb5836f`, weda2 (arbre, parties task-454). api-mcp : aucun impact (`mcp_impact.py check` → 0). Catalogue :
les cinq scénarios sont en v1 dans `scenarios.yml`, et les deux clients déclarent `scenario('E2E-…', 1)`.

Règle 1b, correspondance vérifiée : `PUT …/handled` (M1, M11), 409 et 404 (M2), `to-handle` (M14, M15), groupé (M3),
vue par tag et « sans anomalie » (M4), rangement unitaire (M5), rattachement et « Résolu » (M6, M7), réponse et
transfert (M8, M9), compteurs, page et filtre de vue (M10), délégataire et temps réel (M12, M13). **Manque** : le
rangement par `bulk/move` et `bulk-actions`.

#### À corriger par la reprise
- **B1 — le traitement groupé et « Annuler » touchent des états qu'ils ne devraient pas.** `HandleBulkAsync`
  (`MailHandlingService`) traite toute cible sans biologie en attente : messages déjà traités par une autre personne
  (l'auteur visible « répondu par Dr X » devient « groupé par moi »), historiques, « Pour info » ; la vue par tag sur
  « Tous » rend tous ses UID, sans borne. « Annuler » (weda2 et mobile) appelle `to-handle` sur chaque clé, ce qui pose
  un état explicite « à traiter » au lieu de rendre l'état d'avant (un « Pour info » ou un historique entre alors pour
  toujours dans « À traiter », y compris après un « Traité » unitaire). À faire : ne traiter que les messages
  **actuellement à traiter** (ce qui borne le lot), un « Annuler » qui **restaure l'état précédent**, un libellé N qui
  compte ce qui sera traité, et un test d'intégration sur un lot mêlé (traité par un autre, « Pour info », historique)
  puis l'annulation, vu rouge. La doc de `MailHandlingBulkResultDto.Handled` (« déjà traités exclus ») devient vraie.
- **B2 — règle 1b : le geste « rangé » des déplacements groupés n'est pas prouvé.** `bulk/move` (`MailController`)
  et `bulk-actions` (`BulkMailActionService`) : test d'intégration qui relit `Handling.Gesture == Move` et l'auteur par
  `GET …/emails/{ids}`, vu rouge.
- **B3 — preuves rouges des tests de composant mobiles absentes du Develop log** (DoD). Elles ont été faites
  (M1 à M28, V1 à V7, rapport de la fourche) mais pas consignées : les consigner.
- Même passe :
  - weda2 : « Traité » dans le panneau « Actions & dossier » (l'US le demande, absent) ;
  - `GetTargetOfDocumentAsync` sans filtre de génération courante (une ligne d'une génération périmée marquerait lu
    un autre UID) ;
  - DoD « le délégataire traite (bouton puis réponse) » : la réponse du délégataire n'est pas testée ;
  - catalogue E2E-TRIAGE-002 : le texte dit « il les sélectionne et choisit Traité », les deux clients jouent
    « Traiter les N messages affichés » sur une vue par tag : aligner le texte.

#### Arbitrage humain
- **Hors ligne** : l'US demande que le geste rejoigne la file `PendingAction` ; la forge l'écrit directement en base
  (l'état n'existe qu'en base, et un rejeu sans personne violerait la règle 14). À confirmer.
- **Geste naturel sur un message à biologie en attente** : l'état « traité — rangé » est écrit, le message reste à
  traiter (biologie), et le libellé « Traité par … » s'affiche alors qu'il est dans « À traiter ». Recommandation :
  compléter le libellé par « compte rendu de biologie à acquitter ».
- Coût des requêtes sur les chemins chauds (`GET emails/{ids}`, `GET folders`) : à mesurer sur une boîte de 6 à 11 000
  messages avant toute optimisation (règle d'or 5).


### Reprise 1 (2026-11-17) — revue anticipée, passage 1

**B1 — un traitement ne touche que l'à traiter, « Annuler » rend l'état d'avant.**
- Contrat : `MailHandlingBulkResultDto.PutBack` (dtos-mss `47e57b7`, paquet `618.0.0`, api-mail `91b8bb3f`).
- Serveur (`e7b1a1ba`) : `HandleBulkAsync` lit les états avant le geste et ne traite que les messages **à traiter** ;
  `PutBack` liste ceux qui avaient été remis à traiter ; la vue par tag est bornée à l'à traiter en SQL quel que soit son
  filtre ; nouvelle route `PUT emails/status/handled/undo` (corps = le résultat du traitement, ≤ 2 000 messages) qui efface
  l'état « traité » (la règle reprend la main) ou remet « à traiter » les messages de `PutBack`, tracée
  `MailMarkedToHandle` (« undo ») au nom de la personne.
- Clients : « Annuler » renvoie le résultat au serveur (un « Traité » unitaire construit le sien : `putBack` si le message
  portait un état « à traiter » explicite) ; « Traiter les N messages affichés » n'est proposé que dans une liste
  « À traiter » (boîte ou vue par tag) — le nombre annoncé est alors celui des messages traités ; « sans anomalie »
  reste dans la vue Biologie quel que soit le filtre.

**B2** — `BulkMovesOutOfTheInbox_HandleTheMessages_AsTidied` (`bulk/move` et `bulk-actions`) et la réponse du délégataire
(`TheDelegateReplies_…`, état « traité — répondu » au nom du délégataire).

**Même passe** : `GetTargetOfDocumentAsync` restreint à la génération courante (correctif défensif, sans test dédié : le
cas demande une génération périmée qui porte un document ; les tests de rattachement restent verts) ; « Marquer traité /
Remettre à traiter » dans le panneau « Actions & dossier » de weda2 ; texte du catalogue E2E-TRIAGE-002 aligné (vue de
l'essai, filtre « À traiter »).

Preuves rouges (api-mail) :

| Comportement | Preuve | Test rouge |
|---|---|---|
| groupé : seulement l'à traiter, auteur préservé | rouge sur le code d'avant ; R1 « tout est traité » | `TheBulkHandling_OnlyHandlesWhatIsToHandle_AndUndoRestoresTheStateBefore` |
| vue par tag bornée à l'à traiter | rouge sur le code d'avant (« Pour info » traités) | `HandlingATagView_LeavesWhatIsNotToHandle` ; R2 (borne SQL retirée) **survit** : le service filtre aussi, la borne SQL limite le lot sans changer la réponse |
| « Annuler » remet à traiter ce qui l'était | R3 | `TheBulkHandling_OnlyHandles…` |
| « Annuler » efface l'état « traité » | R4 | `TheBulkHandling_OnlyHandles…` |
| rangement par `bulk/move` | R5 | `BulkMovesOutOfTheInbox_…` |
| rangement par `bulk-actions` | R6 | `BulkMovesOutOfTheInbox_…` |
| réponse du délégataire | R7 | `TheDelegateReplies_TheHolderReadsTheDelegateAsTheAuthor` |

Suite complète api-mail : 8097 réussis, 0 échec. `mss-lib` : 1780/1780.

Preuves rouges weda2 (reprise) : W17 `putBack` perdu au « Traité » unitaire, W18 « Annuler » message par message, W19
« Traiter les N » hors « À traiter », W20 bouton du panneau qui remet à traiter, W21 `putBack` perdu au groupé — toutes
rouges sur la spec visée (`mail-handling.service.spec`, `mss-mail.component.handling.spec`, `mail-list.tag-view.spec`,
`mail-detail.handled.spec`), sources restaurées.

### Preuves rouges — client-mobile (B3 : faites par /develop, consignées ici)

Mobile `be84d34` : 1585/1585, lint propre. Reprise : R1 `wasPutBack` forcé à faux, R2 `putBack` perdu à la fusion, R3
liste non relue après « Annuler », R4 compteurs non relus, R5 « Traiter les N » hors « À traiter », R6 « sans
anomalie » seulement dans « À traiter », R7 mauvaise route d'annulation, R8 échec d'annulation muet — toutes rouges
(`mail-handling.service.spec`, `mail-list.handling.spec`, `mss-api.service.spec`).

Tours précédents (toutes rouges, puis restaurées) :

| Mutation | Spec |
|---|---|
| M1 « Traité » après « Lu » | `mail-list.handling.spec` (ordre des balayages) |
| M2 409 ignoré | `mail-handling.service.spec` (avis biologie) |
| M3 compteur par défaut « Non lus » | `user-settings.service.spec` |
| M4 libellé sans « répondu » | `mail-handling.util.spec` |
| M5 tuile sur `unreadCount` | `to-handle-tile.component.spec` |
| M6 transfert sans Message-ID | `mail-compose.component.spec` |
| M7 traité ⇏ lu | `mail-state.service.spec` |
| M8 « Annuler » sans réinsertion (code retiré par la reprise, couvert par R1-R4) | `mail-handling.service.spec` |
| M9 badge de dossier « Non lus » | `mail-folder-item.component.spec` |
| M10 page « À traiter » réordonnée | `mail-state.service.spec` |
| M11 évènement SSE mal nommé | `mail-events-stream.service.spec` |
| M12 service non rattaché à la boîte | `mailbox-scoped-states.spec` |
| M13 liste « À traiter » qui garde le traité | `mail-state.service.spec` |
| M14 fenêtre d'annulation 600 s (test d'abord lisant la constante : corrigé) | `mail-handling.service.spec` |
| M15 puce de tag « Non lus » | `inbox-tag-chips.component.spec` |
| M16 « À traiter » non servi par le serveur | `inbox.page.spec` |
| M17 avis : panneau d'acquittement non montré | `mail-handling-toast.component.spec` |
| M18 geste absent du corps | `mss-api.service.spec` |
| M19 exclus non comptés | `mail-handling.service.spec` |
| M20 balayage qui remet à traiter | `mail-list.handling.spec` |
| M21 sélecteur inversé | `mail-folder-list.component.spec` |
| M22 filtre de vue « À traiter » refusé | `inbox.page.spec` |
| M23 état serveur non appliqué au détail | `mail-detail.handling.spec` |
| M24 « Traité » offert dans la Corbeille | `mail-list.handling.spec` |
| M25 évènement temps réel d'un autre dossier appliqué | `inbox.page.spec` |
| M26 sélection non transmise | `inbox.page.spec` |
| M27 bouton sur un message envoyé | `mail-detail.handling.spec` |
| M28 « Traité » sans état posé | `mail-handling.service.spec` |
| V1 à V7 (traitement de la vue : total serveur, confirmation, « sans anomalie », relecture) | `mail-list.handling.spec`, `mail-handling.service.spec`, `mss-api.service.spec`, `inbox.page.spec` |

### Reprise 1 — parcours e2e

Tests ajustés : TRIAGE-001 attend `PUT emails/status/handled/undo` ; TRIAGE-002 joue « Traiter les 2 messages affichés »
dans la vue de l'essai filtrée « À traiter » (réglage remis à « Tous » en fin d'essai). Voie mobile (`--serve-only`) :
TRIAGE-001 et 002 verts ; E2 et E6 (« Annuler » sans appel à la route d'annulation) rouges sur l'attente visée ; témoin
restauré vert. Voie Angular : les 5 scénarios verts ; A2 et A5 (nouvelle route) rouges sur l'attente visée, marqueurs
servis puis retirés ; témoin restauré vert.

Fin de la reprise : api-mail `e7b1a1ba`, client-mobile `948047a`, dtos-mss `47e57b7` (`618.0.0`), poussés ; weda2 sur
l'arbre (code-only) ; verts marqués.

### Passage 2 (revue anticipée) — APPROVED

Relecteur indépendant, diff de la reprise lu d'abord (ce que le correctif aurait cassé) : rien de cassé. B1, B2, B3 et les
points « même passe » corrigés, avec leurs tests et leurs preuves rouges. api-mcp : aucun impact.

**Approved at** : dtos-mss `47e57b7`, api-mail `e7b1a1ba`, client-mobile `948047a`, client-angular (arbre weda2, code-only).

#### Suggestions (non bloquantes, à la PR)
- Née de la reprise — la doc de `IMailHandlingService.UndoHandledAsync` dit « un message traité depuis par une autre
  personne n'est pas touché » : faux, `ClearHandledAsync` efface tout état « traité » des Message-ID reçus. En boîte
  partagée, un délégataire qui répond pendant les 6 s du toast perdrait son état « répondu » si le titulaire annule.
  Correctif simple : restreindre l'effacement aux états posés par ce geste (auteur et heure), ou corriger la doc.
- Née de la reprise — bornes inégales : l'annulation refuse plus de 2 000 messages, les routes groupées n'ont pas de
  borne ; `"handled": null` dans le corps de l'annulation finirait en 500 (`ProblemDetails`).
- `GetTargetOfDocumentAsync` restreint à la génération courante sans test vu rouge (correctif défensif).
- L'annulation ne rend ni l'auteur ni l'heure d'un « remis à traiter » d'origine, ni l'état non lu.
- `UndoHandledAsync` sans test unitaire ; la trace « undo » (`MailMarkedToHandle`, RPPS de la personne) n'est pas relue
  par le test d'intégration.
- Après « Annuler », les clients ne réappliquent pas l'état localement : sans SSE, un détail déjà ouvert garde
  « Traité par … » jusqu'à son rechargement.

## Lint log

- Mode : affected (npx nx affected -t lint --base=origin/next --head=HEAD --projects=tag:scope:mss)
- Scope : tag:scope:mss (default — `mss`, `mss-lib`, `mss-e2e`) ; aucun override `**LintBase**` / `**LintProjects**`
- Pipeline fidelity : same commands as Client/Angular/azure-pipelines.yml (Stage 2 CI),
  with two intentional divergences :
  1. BASE_BRANCH default = origin/next (active TFS branch, not pipeline's origin/master fallback)
  2. Lint scoped to tag:scope:mss (the pipeline lints every affected project)
  Build/test stay un-scoped to catch downstream regressions.
- Arbre : branche `feature/nova-mss-weda-integration` @ `f0e9ee95` (code-only, rien de commité), `origin/next` rafraîchi
  (`738a5b63`). L'arbre porte aussi le WIP non commité de task-456 et task-486 : aucun fichier ajouté ni retiré de
  l'arbre par cette étape (même liste `git status` avant / après).
- Comptage : `npx eslint libs/mss apps/mss e2e/mss-e2e --format json` (le `--projects` ne restreint pas `nx affected`,
  13 cibles lint lancées, et `--output-file` en chemin Windows absolu échoue : contournement de task-367).
- Baseline : 107 errors / 100 warnings (98 `prettier/prettier`, 8 `jsdoc/require-jsdoc`, 1 `jsdoc/require-returns`)
- Final    : 0 errors / 99 warnings (75 `jsdoc/require-example`, 21 `max-lines`, 3 `complexity` — tous antérieurs, aucun
  sur une ligne ajoutée)
- Iterations : 3 / 5
- Build / tests : ✓ (build : seuls `mss:build:production` et `prescription:build:production` rouges, budget de bundle
  initial dépassé, rouge préexistant connu — `weda2`, `ins`, `dmp` verts ; tests : 12 projets, 11 956 tests, 0 échec,
  0 erreur)

| Iter | Errors before | Errors after | Warnings before | Warnings after | Build | Tests |
|------|---------------|--------------|-----------------|----------------|-------|-------|
| 1 — `eslint --fix --fix-type layout` (prettier seul) | 107 | 9 | 100 | 100 | ✓ ¹ | ✓ ¹ |
| 2 — JSDoc à la main (8 `require-jsdoc`, 1 `require-returns`) | 9 | 0 | 100 | 100 | ✓ ¹ | ✓ ¹ |
| 3 — `complexity` neuf de la task (avertissement) | 0 | 0 | 100 | 99 | ✓ | ✓ |

¹ Build + tests joués une fois, sur l'arbre final (après l'itération 3) : les itérations 1 et 2 ne changent que la
mise en forme et des commentaires.

**Itération 1** — auto-fix restreint au type `layout` : la règle `prettier/prettier` seule. Le fixer de
`jsdoc/require-jsdoc` aurait posé des squelettes vides (consigne de `conventions/angular.md`), et celui de
`require-example` aurait réécrit des JSDoc de fichiers hors task (`panel-splitter.component.ts`). 98 erreurs réglées, dans
8 fichiers suivis (`functional.e2e.ts`, `e2e-backend.ts`, `mail-events-stream.service.ts`, `mss-api.service.ts`,
`mail-detail.component.ts`, `mail-folder-item.component.ts`, `mail-list.component.ts`, `mail-state.service.ts`) et
3 nouveaux (`mail-handling.util.ts`, `mail-handling.service.ts`, `to-handle-kpi-tile.component.ts`). Fins de ligne
contrôlées après coup : chaque fichier est entièrement CRLF. Une partie des lignes reformatées de `mail-list` et de
`mail-state` (vue par étiquettes) appartient à task-456, seulement reformatée par le fixer.

**Itération 2** — JSDoc écrits à la main (description, `@param`, `@returns`, `@example` avec un appel) :
- `mail-detail.component.ts` : `markHandled` avait été inséré en ancrant sur la signature d'`openSidePanel`. Le JSDoc
  d'`openSidePanel` se trouvait au-dessus du bloc de `markHandled`, et `openSidePanel` n'avait plus de bloc. Le bloc est
  remis à sa place, et le diff redevient une pure insertion des trois méthodes de la task ;
- `mail-handling.service.ts` : `handleBulk`, `apply`, `showsToHandleList`, `refused`, `offerUndo`, `clearUndo` ;
- `to-handle-kpi-tile.component.ts` : `load` ;
- `mail-header.component.ts` : getter `canHandle`, `@returns` manquant.

**Itération 3** — `initializeFromPrefill` (`mail-compose.component.ts`) passait de 20 à 21 en complexité avec le
`if (prefill.forwardedMessageId)` de la task. C'est un avertissement neuf, signalé sur la signature et pas sur la ligne
ajoutée. Corrigé par l'extraction d'`applyPrefillThreading` (In-Reply-To, message transféré, message répondu,
References), sans changer l'ordre des affectations : pure refactorisation, la suite de la rédaction la couvre.

Résiduel : aucune erreur. Les 99 avertissements sont antérieurs à la task (`require-example` vides, `max-lines`, et
`complexity` sur `classify`, `replacePlaceholders` et `classifyDocument`).

Conventions (`conventions/angular.md`) : `jsdoc/require-jsdoc` → 15 occurrences, et `complexity` → 2 (la même
méthode qu'en task-399). Récidive sur la lecture : la passe qualité de /develop annonçait 4 erreurs prettier sur un
seul fichier, le lint en a trouvé 107 sur 11 fichiers. Le lint des fichiers touchés n'avait pas été rejoué après la
dernière modification (`agents/develop.md` §Q 2b).

Vert marqué : `green.py mark --task task-454 --repo client-angular --by lint-angular` (client-angular `f0e9ee95` + arbre modifié).

## Lint mobile log

- Repo : client-mobile (Client/Mobile/, Ionic/Angular CLI), branche `feat/task-454-marquer-un-message-traite` @ `948047a`
- Commands : npm run lint
- Baseline : 0 errors / 0 warnings (« All files pass linting »)
- Final    : 0 errors / 0 warnings
- Iterations : 0 / 5 — lint clean → no work, aucun commit
- Build / tests : non rejoués (baseline propre, aucun fichier modifié) ; le marqueur vert de `/develop` couvre ce code exact
  (`green.py check` : client-mobile `948047af` validé par /develop à 2026-11-17T16:41:48Z)
- Conventions : aucune règle corrigée à la main, `conventions/angular.md` inchangé
