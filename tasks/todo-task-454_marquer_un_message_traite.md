# todo-task-454.md — Marquer un message traité

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-453 (ancrage des états de travail), done-task-465 (mesure de référence relevée avant)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 7 de l'analyse (volume, peur de rater :
2/5). Pour un médecin, un message n'est pas « lu » ou « non lu » : il est **pris en charge** ou non.

> **Origine.** `Docs/analyse-fonctionnelle-manques-messagerie-2026-11.md`, manque A1. Décisions de l'humain du
> 2026-11-11 : traiter marque aussi le message comme lu, mais lire ne le traite pas ; l'état appartient à la boîte ;
> **marquer traité fait passer l'acquittement de biologie à « Résolu », avec un libellé qui dit qui a traité**.

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

Le praticien, la secrétaire ou le délégataire marque un message **« Traité »** d'un geste, et peut le remettre « À
traiter ». La boîte affiche ce qui **reste à traiter**, pas seulement ce qui n'est pas lu. Chacun voit **qui** a traité
et **quand**.

Règles :
- **Le geste** : « Traité » dans la ligne (au survol sur weda2), dans le panneau « Actions & dossier », dans le détail
  mobile, en action groupée sur une sélection, et **en premier balayage sur le mobile**. « Remettre à traiter » sur un
  message traité.
- **Traité implique lu** : traiter marque aussi le message comme lu. Lire ne traite pas.
- **Annulation visible** : toast « Message traité — Annuler » pendant 6 s, sur le modèle de la suppression
  (`mail-pending-delete.service`), généralisé aux deux clients.
- **L'état appartient à la boîte** (règle 14) : traité par une personne, il l'est pour toute l'équipe. Le libellé dit
  **« Traité par {Prénom NOM} ({rôle}) le {date} à {heure} »** (« Traité par Cyril DELEGUE (délégataire) le 12/11 à
  10 h 12 »).
- **Biologie** : marquer traité un message qui porte un compte rendu de biologie non résolu **ajoute à chacun de ses
  documents une action `MarkResolved`** au nom de la personne, avec la note « Marqué traité ». L'historique
  d'acquittement affiche alors « Résolu — message marqué traité par {Prénom NOM} ({rôle}) le … ».
  - Réciproquement, un message dont **tous** les documents de biologie sont « Résolus » par l'acquittement est traité
    d'office, au nom de l'auteur du dernier acquittement.
  - Remettre un message « à traiter » **ne retire aucun acquittement** : ils restent en ajout seul.
- **Reste à traiter** :
  - un compteur par dossier, calculé par le serveur dans la base de la boîte ;
  - un filtre « À traiter » à côté de Tous / Non lus, servi en pages par le serveur ;
  - sur le tableau de bord, une tuile « À traiter », derrière le flag `dashboard_widget_to_handle` (weda2 et mobile).
- **Étiquettes IA** : les vues `tag:XXX` gardent les messages **non traités** au lieu des non lus. Un message urgent lu
  mais non traité y reste.
- **Temps réel** : un nouvel évènement d'état de message, publié par boîte et par dossier, met à jour la ligne et les
  compteurs chez toutes les personnes ouvertes sur la boîte.
- **Hors ligne** (titulaire, weda2) : le geste rejoint la file des gestes hors ligne (`PendingAction`), comme lu ou
  signalé.
- **Plateforme seulement** : l'état « traité » n'est pas visible d'un autre client IMAP. C'est assumé et dit dans
  l'aide.
- **Ancrage** : l'état suit le modèle de task-453. Il survit à un déplacement hors plateforme.

### Hors périmètre

- Reporter un message : task-455. Vues par nature : task-456. Attribuer à quelqu'un : task-457.
- Les dossiers Envoyés, Brouillons et Corbeille n'ont pas d'état « à traiter ».

## Definition of Done

- [ ] Contrat : état de traitement exposé dans `MailDto` (traité oui ou non, par qui : RPPS, nom, rôle ; quand),
      compteur « à traiter » par dossier dans `FolderDto` ; paquet `HealthPlatform.Dtos.Mss` publié (`/publish-dtos`)
      et consommateurs à jour.
- [ ] Migration FluentMigrator de la table d'état dans la base de la boîte, ancrée selon l'ADR de task-453 ; audit de
      migration (règle 7c) ; modèle EF identique.
- [ ] Nouveaux actes d'audit `MailMarkedHandled` et `MailMarkedToHandle` en fin de `AuditActionType`, miroirs
      TypeScript, famille `HealthDataAccess`, contrôleurs marqués `[Audited]`.
- [ ] Tests unitaires : traité ⇒ lu ; lu ⇏ traité ; traité ⇒ `MarkResolved` sur chaque document non résolu ; tous
      résolus ⇒ traité ; remettre à traiter ne retire aucun acquittement ; vue d'étiquette sur « non traité ».
- [ ] **Test d'intégration de bout en bout (règle 1b)** pour `PUT api/v1/Mail/emails/{id}/status/handled` (et
      `to-handle`, et la version groupée) : `MailDto` relu par `GET …/emails/{ids}` avec l'état, l'auteur et l'heure ;
      `IsRead` vrai ; compteur « à traiter » du dossier diminué de 1. Cas d'échec : message inconnu → 404 en
      `ProblemDetails`. Vu rouge.
- [ ] **Test d'intégration biologie** : traiter un message porteur d'un compte rendu « À traiter » ; `LastBiologyAck`
      relu = `MarkResolved`, note « Marqué traité », auteur = la personne qui a traité. Vu rouge.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire traite ; le titulaire relit le message traité
      « par » le délégataire ; la trace d'audit porte le délégataire (RPPS, nom, rôle), jamais la boîte.
- [ ] Test d'intégration de l'évènement temps réel : une personne traite, l'abonné de l'autre personne reçoit l'état.
- [ ] Tests de composant (weda2 et mobile), chacun vu rouge par mutation : geste Traité, remettre à traiter, annuler
      dans le toast, libellé « Traité par … », filtre « À traiter », tuile « À traiter », balayage Traité en premier.
- [ ] **Scénarios e2e** ajoutés à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis, chacun vu rouge par mutation :
      - `E2E-TRIAGE-001` v1 : traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet ;
      - `E2E-TRIAGE-002` v1 : traiter le compte rendu de biologie à acquitter le fait passer « Résolu », avec « marqué
        traité par » et le nom ;
      - `E2E-SHARED-003` v1 : le délégataire traite un message, le titulaire le voit traité « par » le délégataire.
- [ ] Les balayages existants (`swipe-read|flag|move|delete-*`, corbeille de task-142) restent verts ; tests adaptés à
      l'ordre nouveau.
- [ ] Mesure de charge (task-465) : indicateurs « délai jusqu'au traitement » (p50, p95) et « part traitée par un
      délégataire ou un membre » ajoutés au tableau de bord, avec leur test unitaire.
- [ ] `data-testid` sur chaque élément interactif ajouté ; libellés selon les conventions du module ; aucune donnée de
      santé dans les libellés ni les logs.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, `Dtos`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`), weda2 (`cd Client/Angular/front && npm start`) et le
   mobile (`cd Client/Mobile && npm start`), sur une boîte où un délégataire est rattaché.
2. weda2, titulaire : noter le compteur « À traiter » de la Boîte de réception. Marquer un message « Traité » : il
   sort du filtre « À traiter », le compteur baisse, le toast propose « Annuler ».
3. Ouvrir un compte rendu de biologie à acquitter, cliquer « Traité » : l'acquittement affiche « Résolu — message
   marqué traité par {votre nom} ».
4. Mobile, délégataire sur la même boîte : balayer un message, choisir « Traité ». Sur weda2, sans recharger, le
   titulaire voit « Traité par {délégataire} (délégataire) le … ».
5. Remettre ce message « À traiter » : il revient, l'historique d'acquittement est intact.
6. Ouvrir la vue d'étiquette « Urgent » : un message urgent lu mais non traité y figure toujours.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — organisation du travail ; prolonge le suivi des comptes rendus de biologie
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun identifiant patient manipulé
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : titulaire, membre et délégataire peuvent traiter, sous verdict récent de l'opérateur (règle 14) ;
  rien sans verdict
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `MailMarkedHandled`, `MailMarkedToHandle`, et `BiologyMarkedResolved` (note « Marqué traité »),
  au nom de la personne réelle (RPPS, nom PSC, rôle, boîte, instant, objet), famille `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte, environnement HDS de production
- **AIPD / impact RGPD** : à mettre à jour — l'auteur du traitement est visible des autres personnes de la boîte
  (même finalité que le journal de la boîte, E020)
