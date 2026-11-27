# todo-task-497.md — Anneau de traitement : la liste et le détail

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: aucune (task-467 conseillée avant : tant qu'elle est ouverte, un anneau peut être neutre à tort)
**Epic**: E027
**EpicTitle**: Anneau de traitement : voir les boucles ouvertes

> **Origine.** Demande humaine du 2026-11-27 : « Chaque mail est représenté par un anneau incomplet. Chaque étape
> franchie remplit un segment. […] Le médecin ne gère plus des messages, il gère des attentes. »
>
> **Phase de conception validée le 2026-11-27** : `Docs/specs/anneau-de-traitement/specification.md`,
> `maquettes.html` (variante **D**) et `revue-design.md`. Décisions de l'humain, le même jour :
> - **variante D** : l'anneau dit l'avancement et la gravité ; le reste est écrit à droite ;
> - **« à traiter par »** : les initiales s'affichent **à l'intérieur de l'anneau**, et la pastille d'initiales
>   actuelle est supprimée, puisqu'elle existe dans l'anneau ;
> - « d'accord pour le reste » : les recommandations du § 13 de la spécification sont acceptées.
>
> Cette task est le lot 1. L'ancienneté est le lot 2 (task-498), le tableau de bord le lot 3 (task-499).

## Objectif

Dans la liste des messages et dans le détail, chaque message suivi porte un **anneau** : un segment par étape
franchie, le vide pour ce qui reste à faire, une coche quand la boucle est fermée. Le médecin, la secrétaire ou le
confrère voit d'un regard où en est chaque message, à qui il est confié et s'il porte une anomalie de biologie.

L'anneau **n'ajoute aucun état** : il dessine ce que la boîte sait déjà (lu, traité, attribution, acquittement).

### Ce qui est établi

Lecture du code au 2026-11-27 :

- **La ligne de liste porte déjà presque tout.** `MailDto` (`Dtos/MailDto.cs`) rend `IsRead`, `ArrivalDate`,
  `Handling` (`IsToHandle`, `IsHandled`, `By`, `At`, `Gesture`), `Assignment` (`Assignee`, `IsOpen`, `IsMine`,
  `AssigneeAccessRemoved`), `HasAbnormalBiology`, `PendingBiologyAcksCount`, `HasCriticalPendingBiologyAck`,
  `IsReport`, `IsAutomatic`, `Tags`.
- **Qui est « à traiter »** : `Domain/Rules/MailHandlingRule.cs` et son équivalent SQL `MailHandlingQueries.cs`.
  Jamais dans Envoyés, Brouillons, Corbeille ; un compte rendu de biologie à acquitter garde le message à traiter ;
  sinon l'état posé à la main ; sinon « suivi et non Pour info ».
- **« Lu » est partagé par la boîte** (`Mails.IsRead`, miroir du drapeau de la messagerie). Aucune date ni auteur de
  lecture n'est gardé sur le message.
- **L'acquittement est par document, en ajout seul** (`BiologyAcks`, `BiologyAckService`). Actions : Pris
  connaissance, Rappel patient, Convocation, Adressage confrère, Marquer comme résolu. L'état suit la dernière
  action. Il n'est réclamé que pour un compte rendu **avec anomalie** (l'API répond 400 sinon).
- **Il manque un champ** : la ligne ne dit pas quelle est la dernière action d'acquittement. Les agrégats de
  biologie sont calculés en une seule lecture pour toute la page (`MailRepository.EnrichManyWithBiologyAcksAsync`).
- **Mise à jour en direct** : « traité » et l'attribution poussent un évènement
  (`NotifyMailHandlingChangedAsync`, `NotifyMailAssignmentChangedAsync`). Un acquittement intermédiaire n'en pousse
  aucun ; seul « Résolu » le fait, par le « traité » qu'il déclenche.
- **Colonne de gauche de la ligne** : initiale de l'expéditeur dans un rond de 32 px sur weda2
  (`libs/mss/src/features/mail/components/mail-header/`), dans un carré de 40 px sur mobile
  (`src/app/features/mail/components/mail-header/`).
- **Pastilles existantes de la ligne** : initiales d'attribution (`.mail-assignee-chip`, task-457), « Traité »
  (`.mail-handled-chip`, weda2 seulement), badge d'acquittement (`mss-biology-ack-badge`, nombre de comptes rendus
  en attente).
- **Boutons d'acquittement** : weda2, dans le panneau latéral « Actions & dossier », section `ack`
  (`mss-biology-ack-panel`, un par compte rendu) ; mobile, dans l'onglet Biologie du message.
- **Personnes de la boîte** : `GET /api/v1/mail/mailbox/people`, déjà chargé par les deux clients
  (`MailAssignmentService.people`).
- **Réglages par personne** : `UserSettingsDto`, partagé par les deux clients (`POST /api/v1/Settings`).
- **api-mcp** lit `MailDto` par ses contrats locaux. Ajouter un champ n'est jamais un impact.
- **Aucun composant d'anneau n'existe** dans les deux clients.

### Règles

1. **Qui a un anneau.** Dans tout dossier sauf Envoyés, Brouillons et Corbeille :
   - message « à traiter » : anneau **ouvert** ;
   - message traité : anneau **fermé** ;
   - autre message (« Pour info », accusé, rapport, antérieur à la date de début du suivi) : **hors suivi**.

   Dans Envoyés, Brouillons et Corbeille, la ligne garde l'initiale d'aujourd'hui.
2. **Étapes.**
   - Courrier, message, biologie sans anomalie : **reçu → lu → traité** (3 segments).
   - Message portant au moins un compte rendu de biologie à acquitter : **reçu → pris connaissance → suite donnée →
     résolu** (4 segments). « Suite donnée » = Rappel patient, Convocation ou Adressage confrère. L'état suit la
     **dernière action**, comme aujourd'hui ; une action peut sauter une étape.
   - Plusieurs comptes rendus à acquitter dans un message : le **moins avancé** commande l'anneau de la liste.
3. **Dessin (variante D).**
   - L'anneau prend la place et la taille de l'initiale de l'expéditeur : 32 px sur weda2, 40 px sur mobile.
   - Étapes franchies : segments pleins. Étapes restantes : traits fins, contraste d'au moins 3:1 avec le fond.
   - Ni pointe, ni sens de rotation, ni balle, ni cernes.
   - Fermé : cercle fin et **coche**. Hors suivi : cercle fin en pointillé.
4. **Le centre de l'anneau.**
   - Message attribué (« à traiter par ») et anneau ouvert : les **initiales** de la personne attribuée. Sur fond
     plein si c'est la personne connectée ; barrées si son accès est retiré.
   - Sinon le centre est vide.
5. **La pastille d'initiales est supprimée** de la ligne, sur weda2 et sur mobile : l'anneau la porte. Le texte
   « À traiter par … — attribué par … le … » du détail reste. La pastille « Traité » de weda2 est supprimée : la
   coche la remplace.
6. **Gravité.** La couleur de l'anneau ne dit que la gravité clinique posée par le laboratoire :
   - neutre : pas de compte rendu à acquitter ;
   - ambre : un compte rendu avec anomalie à acquitter ;
   - rouge : un compte rendu avec valeur critique (LL, HH, AA) à acquitter.

   Le badge d'acquittement ⚠ n existant reste à droite, inchangé. Sur un message traité ou hors suivi qui porte une
   anomalie, un ⚠ atténué sans chiffre reste affiché : fermer la boucle n'efface pas l'anomalie.
7. **À droite de la ligne**, en toutes lettres :
   - **« Non affecté »** : anneau ouvert, aucune attribution, et la boîte a au moins deux personnes actives. Jamais
     dans une boîte à une seule personne ;
   - **« Attente patient »** : dernière action Rappel patient ou Convocation ;
   - **« Attente confrère »** : dernière action Adressage confrère.
8. **État en clair.** Chaque anneau a un libellé accessible, affiché au survol sur weda2 et à l'appui long sur
   mobile. Exemples : « Courrier. Étape 2 sur 3 : lu ; reste : traité. À traiter par Cyril DELEGUE. » ;
   « Biologie, valeur critique. Étape 1 sur 4 : reçu. Non affecté. » ; « Boucle fermée : traité. » ;
   « Pour info : aucune action attendue. ». Il ne cite jamais le patient, son INS ni une valeur.
9. **Détail.** Un bloc en tête du message :
   - un grand anneau et la liste des étapes. Chaque étape franchie donne sa date et son auteur quand la boîte les
     connaît : « Reçu » (date d'arrivée), « Traité par … le … — geste », chaque action d'acquittement (auteur, date).
     « Lu » s'affiche sans date ni auteur ;
   - pour un compte rendu à acquitter, **les boutons d'acquittement sont juste sous l'anneau**, rangés par étape :
     « Pris connaissance » ; « Rappel patient », « Convocation », « Adressage confrère » ; « Marquer comme résolu ».
     Ils quittent le panneau latéral de weda2 et l'onglet Biologie du mobile. La fenêtre de confirmation et la note
     ne changent pas ;
   - plusieurs comptes rendus à acquitter : un anneau et ses boutons par compte rendu ;
   - « Traité », « Remettre à traiter » et « À traiter par » restent où ils sont aujourd'hui.
10. **Chaque geste remplit son segment** par une transition brève. Aucune animation au chargement de la liste, ni
    quand le système demande de réduire les animations.
11. **En direct.** Un acquittement, y compris intermédiaire, met à jour l'anneau chez les autres personnes connectées
    à la boîte, comme « traité » et l'attribution le font déjà.
12. **Préférence de la personne** : « Affichage de la liste : Anneau de traitement (par défaut) / Icône classique ».
    En icône classique, la ligne est celle d'aujourd'hui, pastille d'initiales et pastille « Traité » comprises. Le
    bloc du détail ne dépend pas de ce réglage.
13. **Aucun état ne repose sur la seule couleur** : la forme (segments, coche, pointillé), les initiales et le texte
    suffisent en niveaux de gris.
14. **Performance.** La page de liste ne fait **aucun aller-retour de plus** vers la base. Aucune colonne « état
    d'anneau » n'est créée : l'anneau est dérivé des états existants.

### Hors périmètre

- L'ancienneté (compteur J+N, seuils) : task-498.
- Le tableau de bord : task-499.
- Les messages envoyés (état d'acheminement, attente de réponse) : non retenus dans ce lot (décision 9).
- Une étape « patient vu » : non retenue (décision 11).
- `client-blazor` : aucune des fonctions d'E024 n'y existe.

## Definition of Done

- [ ] Build passes : api-mail, dtos-mss, `nx build weda2`, client-mobile (0 erreur).
- [ ] Tests pass : api-mail, `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests unitaires (api-mail) de l'avancement d'acquittement d'un message : aucun compte rendu à acquitter ; un
      compte rendu sans action ; dernière action Pris connaissance ; Rappel patient ; Convocation ; Adressage
      confrère ; Résolu ; deux comptes rendus à des étapes différentes (le moins avancé commande) ; compte rendu
      antérieur au suivi (ne compte pas). Chacun vu rouge.
- [ ] Test d'intégration de bout en bout pour la page de liste (`GET api/v1/Mail/folders/{f}/emails/{ids}`) : un
      message portant un compte rendu avec anomalie rend, relu dans la réponse réelle, l'avancement « reçu » ; après
      `POST medical-documents/{id}/biology-ack` « Rappel patient », la même ligne rend « suite donnée » et l'action
      « Rappel patient » ; après « Marquer comme résolu », plus d'avancement en attente et `handling.isHandled` vrai.
      Cas d'échec : un compte rendu sans anomalie ne rend aucun avancement. Vu rouge (règle 1b).
- [ ] Même test sur la vue par tag (`GET api/v1/Mail/tags/emails`) et hors ligne (`OfflineMailDataProvider`) : le
      champ est rendu sur les trois chemins.
- [ ] Test d'intégration : la page de liste n'exécute pas une commande SQL de plus qu'avant la task (compté par le
      test, ou mesuré par `DbOperationScope` et consigné avant/après dans le `## Develop log`). Vu rouge par mutation.
- [ ] Test d'intégration en boîte partagée (règle 14) : le titulaire et un délégataire agissent sur la même boîte ;
      le délégataire acquitte « Pris connaissance », le titulaire relit la ligne et y lit l'avancement, et la trace
      porte le délégataire en auteur. Un évènement en direct est reçu par l'autre personne pour cet acquittement
      intermédiaire. Vu rouge.
- [ ] dtos-mss : champs ajoutés au contrat (ligne de liste, réglage de la personne) publiés, api-mail bumpé ;
      `python Tools/contracts/contract_impact.py check` sans impact non adapté.
- [ ] Composant anneau, weda2 et mobile, tests de composant vus rouges :
  - 1, 2 ou 3 segments sur 3 ; 1 à 4 sur 4 ; fermé (coche) ; hors suivi (pointillé) ;
  - initiales au centre pour un collègue, fond plein pour la personne connectée, barrées si l'accès est retiré,
    centre vide sans attribution ;
  - couleur neutre, ambre, rouge selon l'acquittement en attente ;
  - libellé accessible exact pour chaque cas de la règle 8, sans nom de patient.
- [ ] Tests de composant de la ligne, weda2 et mobile, vus rouges : la pastille d'initiales n'est plus rendue en mode
      anneau et revient en icône classique ; « Non affecté » seulement avec au moins deux personnes actives ;
      « Attente patient » et « Attente confrère » selon la dernière action ; ⚠ atténué sur un message traité porteur
      d'une anomalie ; dans Envoyés, la ligne garde l'initiale.
- [ ] Tests de composant du détail, weda2 et mobile, vus rouges : étapes datées et imputées ; boutons d'acquittement
      sous l'anneau, rangés par étape ; un anneau par compte rendu ; un clic remplit le segment ; plus de section
      d'acquittement dans le panneau latéral (weda2) ni dans l'onglet Biologie (mobile).
- [ ] Contraste des traits des étapes restantes mesuré à 3:1 au moins sur le fond de la ligne, dans les deux clients ;
      rendu vérifié en niveaux de gris.
- [ ] `data-testid` sur l'anneau de la ligne, l'anneau du détail, chaque étape et chaque pastille ; aucun texte en dur
      hors de la convention de chaque client.
- [ ] Mobile : références Stitch des écrans `mail-list` et `mail-detail` mises à jour (`/stitch-design`, best-effort).
- [ ] Scénario **E2E-RING-001** (version 1, `mobile: requis`, `angular: requis`) ajouté à
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : le test dépose, comme un autre logiciel, un
      courrier non lu d'un confrère, suivi et sans « Pour info ». Sa ligne porte un anneau à 1 segment sur 3. Le
      praticien l'ouvre : 2 sur 3, et le détail liste « Reçu » daté et « Lu ». Il le marque « Traité » : la ligne
      porte la coche, le détail dit « Traité par … », et le message relu du serveur est traité par le praticien.
- [ ] Scénario **E2E-RING-002** (version 1, `mobile: requis`, `angular: requis`) : sur un compte rendu de biologie
      avec anomalie à acquitter, la ligne porte un anneau coloré à 1 segment sur 4 et le badge ⚠. Depuis le détail,
      sous l'anneau, le praticien choisit « Rappel patient » : 3 segments sur 4, « Attente patient » sur la ligne, et
      l'acquittement relu du serveur porte son nom. Il choisit « Marquer comme résolu » : coche, ⚠ atténué, message
      traité relu du serveur.
- [ ] Scénario **E2E-RING-003** (version 1, `mobile: requis`, `angular: requis`) : en boîte partagée (titulaire et
      délégataire), un message à traiter non attribué affiche « Non affecté ». Le titulaire l'attribue à la
      délégataire : chez lui, l'anneau porte les initiales de la délégataire et la ligne n'a plus de pastille
      d'initiales ; chez elle, ses initiales sont sur fond plein.
- [ ] Scénario **E2E-SETTINGS-005** (version 1, `mobile: requis`, `angular: requis`) : le praticien choisit « Icône
      classique » ; la liste montre l'initiale de l'expéditeur et la pastille d'initiales ; après rechargement, le
      choix est retenu ; il revient à « Anneau de traitement ».
- [ ] **E2E-ASSIGN-001** passe en **version 3** dans les deux clients : « sa ligne porte la pastille « À traiter
      par » » devient « l'anneau de sa ligne porte ses initiales ». Tout autre scénario dont l'attendu ou
      l'implémentation lit la pastille d'initiales, la pastille « Traité » ou l'emplacement des boutons d'acquittement
      (E2E-ASSIGN-002/003, E2E-TRIAGE-\*, E2E-BIO-001/003/004/007) est relu : version montée si l'attendu change,
      implémentation adaptée sinon. Rejoués verts par `/e2e`.
- [ ] Aucune donnée de santé dans les journaux, les évènements en direct ni les libellés de l'anneau.

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`, ouvrir la messagerie.
- Mobile : `cd Client/Mobile && npm start`, ouvrir la boîte.
- Données : une boîte partagée avec un délégataire ; un courrier d'un confrère non lu ; un compte rendu de biologie
  avec une valeur critique, à acquitter ; un compte rendu de biologie sans anomalie ; un message reçu en copie.
- Référence visuelle : `Docs/specs/anneau-de-traitement/maquettes.html`, variante D.

1. weda2, Boîte de réception : chaque ligne suivie porte un anneau à la place de l'initiale. Le courrier non lu a
   1 segment sur 3 ; le message en copie a un cercle pointillé ; la biologie critique a un anneau rouge à 1 segment
   sur 4, le badge ⚠ et « Non affecté ».
2. Survoler un anneau : l'état est écrit en clair, sans nom de patient.
3. Ouvrir le courrier : 2 segments sur 3 ; le détail montre le grand anneau, « Reçu » daté, « Lu ».
4. « À traiter par » le délégataire : les initiales sont dans l'anneau, sans pastille d'initiales sur la ligne.
   Chez le délégataire, les mêmes initiales sont sur fond plein.
5. « Traité » : coche sur la ligne ; « Remettre à traiter » la rouvre.
6. Ouvrir la biologie critique : les boutons d'acquittement sont sous l'anneau, rangés par étape. « Rappel patient » :
   3 segments, « Attente patient » sur la ligne, et l'anneau se met à jour chez le délégataire sans rechargement.
7. « Marquer comme résolu » : coche, ⚠ atténué.
8. Paramètres : « Icône classique » rend la liste d'aujourd'hui ; revenir à « Anneau de traitement ».
9. Ouvrir Envoyés : pas d'anneau.
10. Refaire 1 à 8 sur le mobile (l'état en clair s'obtient par un appui long).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — présentation d'états déjà stockés, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable — aucun échange ni document nouveau.
- **INS** : non applicable — aucun patient identifié ni manipulé ; le libellé de l'anneau ne cite jamais le patient.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : inchangées. Titulaire, délégataire et membre voient les mêmes anneaux, qui appartiennent à la
  boîte ; un délégataire ou un membre sans verdict récent de l'opérateur ne voit rien (règle 14). « Initiales sur
  fond plein » dépend de la personne connectée, pas de la boîte.
- **Interop CI-SIS** : non applicable — l'anomalie reste celle posée par le laboratoire dans le CDA ou le HPRIM
  (code d'interprétation), jamais une comparaison aux bornes.
- **Tracé PGSSI-S** : aucun acte nouveau. Lire, traiter, attribuer et acquitter sont tracés comme aujourd'hui, au
  nom de la personne réelle (règle 14), famille `HealthDataAccess`, 3 653 jours. Afficher un anneau n'est pas un
  acte ; changer le réglage d'affichage est un réglage de la personne, non tracé.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun nouveau (codes d'interprétation HL7 déjà lus).
- **Hébergement HDS** : oui — les états lus sont ceux de la base de la boîte, environnement HDS existant ; aucune
  donnée de santé nouvelle.
- **AIPD / impact RGPD** : inchangée — même traitement, présentation différente.

## Branches

- `dtos-mss` (branche paresseuse) : créée par `/develop` au moment où il touche le contrat (ligne de liste, réglage de la personne)
- `api-mail` (pushed) : feat/task-497-anneau-de-traitement-liste-et-detail — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-497-anneau-de-traitement-liste-et-detail
- `client-mobile` (pushed) : feat/task-497-anneau-de-traitement-liste-et-detail — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-497-anneau-de-traitement-liste-et-detail
- `client-angular` (code-only) : branche checkout au /start : `feature/nova-mss-weda-integration` — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-497 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 46 s | — | — | — | — |
| **Total cycle** | | **46 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
