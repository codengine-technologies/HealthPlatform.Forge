# todo-task-454.md — Marquer un message traité

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-453 (ancrage des états de travail), done-task-466 (date de début du suivi), done-task-456 (nature des messages), done-task-465 (mesure de référence relevée avant)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 7 de l'analyse (volume, peur de rater :
2/5). Pour un médecin, un message n'est pas « lu » ou « non lu » : il est **pris en charge** ou non.

> **Origine.** `Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`, manque A1. Décisions de l'humain du
> 2026-11-11 : traiter marque aussi le message comme lu, mais lire ne le traite pas ; l'état appartient à la boîte.
>
> **Reprise du 2026-11-12 (décisions de l'humain).** Un clic « Traité » sur chaque message, y compris sans importance,
> serait trop lourd, et un « tout marquer traité » viderait le signal. D'où :
> - n'entrent dans « À traiter » que les messages **suivis** (task-466 : arrivés après la date de début du suivi —
>   une première synchronisation ne réclame rien sur deux ans d'historique) et d'une **nature à traiter** (task-456) ;
> - les **gestes naturels** (répondre, ranger, rattacher, acquitter) traitent le message ; le bouton sert au reste ;
> - le traitement groupé existe, mais **n'acquitte jamais de biologie** : la règle du 2026-11-11 « marquer traité fait
>   passer l'acquittement à « Résolu » » est **retirée** (risque de résoudre en masse des résultats jamais lus).

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
  - d'une **nature à traiter** au sens de task-456 : Biologie, Patients, Courriers et comptes rendus.
  - N'y entrent **pas** : la nature « Pour info » (copies, messages automatiques, accusés de lecture et de remise,
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
  il entre alors dans « À traiter », quelle que soit sa date ou sa nature.
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
  - un compteur par dossier et **par vue de nature** (task-456), calculé par le serveur dans la base de la boîte ;
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
- La date de début du suivi et l'état « Antérieur au suivi » : task-466. La classification par nature : task-456.
- Les dossiers Envoyés, Brouillons et Corbeille n'ont pas d'état « à traiter ».
- La règle « répondre = traité » ne vérifie pas que la réponse clôt l'échange : la relance sans réponse (task-462)
  couvre une réponse qui appelle une suite.

## Definition of Done

- [ ] Contrat : état de traitement exposé dans `MailDto` (traité oui ou non, par qui : RPPS, nom, rôle ; quand ;
      geste : bouton, réponse, rangement, rattachement, acquittement, groupe), compteur « à traiter » par dossier et
      par nature dans `FolderDto` ; paquet `HealthPlatform.Dtos.Mss` publié (`/publish-dtos`) et consommateurs à jour.
- [ ] Migration FluentMigrator de la table d'état dans la base de la boîte, ancrée selon l'ADR de task-453 ; audit de
      migration (règle 7c) ; modèle EF identique.
- [ ] Nouveaux actes d'audit `MailMarkedHandled` et `MailMarkedToHandle` en fin de `AuditActionType` (avec le geste),
      miroirs TypeScript, famille `HealthDataAccess`, contrôleurs marqués `[Audited]`.
- [ ] Tests unitaires de la règle d'entrée : message suivi d'une nature à traiter → à traiter ; « Pour info » → non ;
      historique antérieur au suivi → non ; « Remettre à traiter » sur un historique ou un « Pour info » → à traiter.
- [ ] Tests unitaires des sorties : traité ⇒ lu ; lu ⇏ traité ; réponse, transfert, rangement, rattachement,
      acquittement « Résolu » de tous les comptes rendus ⇒ traité avec le bon geste ; « Traité » **n'écrit aucun
      acquittement** ; « Traité » refusé sur un message porteur d'un résultat non acquitté ; remettre à traiter ne
      retire aucun acquittement ; vue d'étiquette sur « non traité ».
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `PUT api/v1/Mail/emails/{id}/status/handled` (et
      `to-handle`) : `MailDto` relu par `GET …/emails/{ids}` avec l'état, l'auteur, l'heure et le geste ; `IsRead`
      vrai ; compteur « à traiter » du dossier et de la nature diminué de 1. Cas d'échec : message inconnu → 404 en
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
      « N comptes rendus de biologie restent à acquitter », filtre « À traiter », compteurs par nature, tuile
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
- [ ] Mesure de charge (task-465) : indicateurs « délai jusqu'au traitement » (p50, p95), « part traitée par un
      délégataire ou un membre » et **« part traitée par geste »** (bouton, geste naturel, **groupe**) ajoutés au
      tableau de bord, avec leur test unitaire. Une part « groupe » dominante signale un modèle encore trop lourd.
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
| /start | skipped | 23 s | — | — | — | refus : dépendances task-466, task-456, task-465 encore en todo |
| **Total cycle** | | **23 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
