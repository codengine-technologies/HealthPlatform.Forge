# todo-task-497.md — Anneau de traitement : la liste et le détail

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Reprises**: 3
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
   - **weda2 — décision humaine du 2026-11-27, après la validation finale** : « le bloc alourdit l'affichage du
     détail, il a plus sa place dans les actions & dossier de la barre latérale ». Sur weda2, le bloc (grand anneau,
     étapes, boutons d'acquittement rangés par étape, un anneau par compte rendu) **quitte la tête du message** et
     devient une section du panneau latéral « Actions & dossier », en premier. Panneau replié : l'icône de la section
     sur le rail porte la pastille « en attente » quand un compte rendu reste à acquitter, et un clic ouvre le panneau
     sur la section. Le mobile, qui n'a pas de panneau latéral, garde le bloc en tête du message.
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

## Develop log

- Repos touched : dtos-mss, api-mail, client-mobile, client-angular (code seul)
- DTOs published : 635.0.0 → **638.0.0** (`6f00908`, CI run 45964152282) — `MailDto.PendingBiologyAckStage` /
  `PendingBiologyAckLastAction`, `MailMedicalDocumentDto.BiologyAckHistory`, `MailBiologyAckProgressDto`,
  `UserSettingsDto.ListMarker` ; api-mail bumpé avec ses `packages.lock.json`
- Interop published : no interop change
- Commits :
  - dtos-mss : `6f00908` feat(dto): anneau de traitement
  - api-mail : `9fe4f8d9` chore(deps): bump 638.0.0 ; `bbb6d978` feat(mail): anneau de traitement
  - client-mobile : `888f7cc` feat(mobile) ; `9ec2ddb` refactor simplify pass ; `6f0e8f7` test(mobile) E2E-SETTINGS-005
- **contract_impact.py check** (après le code des trois dépôts) : `api-mcp : aucun impact` / `client-mobile : aucun
  impact` / `client-angular : aucun impact` (avertissements de lecture tolérante habituels). Un premier passage sortait
  en 2 : le modèle mobile s'appelait `MailBiologyAckSummaryDto`, renommé `MailBiologyAckProgressDto`.

### api-mail

- Règle pure `Domain/Rules/BiologyAckProgressRule.cs` : étape d'un compte rendu (aucune action → Reçu ; Pris
  connaissance ; rappel / convocation / adressage → Suite donnée ; Résolu ou antérieur au suivi → ne réclame rien). Le
  message suit le compte rendu le moins avancé, puis la dernière action la plus récente.
- `MailRepository.ApplyEnrichmentToMail` l'applique dans la lecture groupée existante : **32 commandes SQL avant et
  après** sur la page de liste (test `TheListPage_ServesTheStage_WithoutOneMoreSqlCommand`).
- Historique des acquittements servi par la lecture du contenu d'un message seulement (`GET …/emails/content/{uid}`),
  `null` sur les pages de liste et la vue par tag.
- Évènement `MailBiologyAckChanged` poussé après **tout** acquittement, intermédiaire compris, recalculé de la base.
  Best-effort : une panne du relais ne fait pas échouer l'acquittement, rien de clinique dans le journal. Il part aussi au
  rejeu de la file hors ligne : il ne porte ni auteur ni donnée de santé.
- Tests, tous vus rouges sur le code d'avant ou par mutation (mutations restaurées, recompilées) :

| Test | Prouve | Preuve rouge |
|---|---|---|
| `BiologyAckProgressRuleTests` (20) | les 9 cas de la DoD, départage, gravité | 9 mutations, chacune rouge sur son cas |
| `TheListRow_SaysTheAcknowledgementStage…` ×3 (dossier, tag, hors ligne) | Reçu → Suite donnée + Rappel patient → plus rien + `isHandled` | code d'avant : `Expected (1, Received, null) Actual (1, null, null)` |
| `TheListRow_CarriesTheStageAsAnInteger…` | entiers camelCase ; compte rendu sans anomalie → 400 et aucune étape | code d'avant : nombre attendu, null reçu |
| `TwoReportsInOneMessage…` | le moins avancé commande ; chaque évènement égale la ligne relue | publication retirée : `Expected 3 Actual 0` |
| `AnAcknowledgementOnAMessageOfAPastFolderGeneration…` | pas d'évènement pour une ligne périmée | filtre de génération retiré : rouge |
| `TheListPage_ServesTheStage_WithoutOneMoreSqlCommand` | 32 commandes avant et après | lecture d'historique ajoutée aux listes : rouge |
| `ReadingOneMessage_ServesTheAcknowledgementHistory…` | du plus ancien au plus récent, délégataire puis titulaire, null sur les listes | 4 mutations rouges |
| `TheDelegateAcknowledges_…` (règle 14) | le titulaire relit l'étape ; la trace nomme le délégataire ; un évènement est livré | charge retirée, évènement renommé, audit sauté : 3 rouges |
| `TheListMarker_…` | défaut Anneau, propre à la personne, `"listMarker":1` | enregistrement forcé à Anneau : rouge |
| `BiologyAckServiceLiveProgressTests`, cas du broker | chaque action et le rejeu publient ; panne tolérée | publication coupée : 6 rouges |

- Suite complète : domain 388, infrastructure 749, application 4 373, api 1 388, intégration 1 386 (+16 ignorés) —
  **0 échec, aucun plantage** ; build 0 erreur 0 avertissement.

### client-mobile

- `treatment-ring.util.ts` (règle pure), `mss-treatment-ring` (SVG), `mss-treatment-ring-steps` (bloc du détail).
- Ligne : anneau à la place de l'initiale, initiales au centre, pastille d'initiales retirée ; pastilles « Non affecté »,
  « Attente patient », « Attente confrère », ⚠ atténué.
- Détail : boutons d'acquittement sous l'anneau, rangés par étape, retirés de l'onglet Biologie. Réglage dans
  « Organisation ». Évènement en direct appliqué à la ligne et au détail ouvert.
- Contraste mesuré par le spec du composant : étapes restantes `--app-outline` 4,49 à 3,67:1 ; anomalie `--app-flag`
  ≥ 4,84:1.
- Unitaires : 120 mutations, 118 rouges sur l'assertion visée, 2 sans effet observable (U15, C13).
- Suite complète après la passe qualité : **1 906 / 1 906**. Build OK, ESLint 0 erreur sur les 46 fichiers touchés.

### client-angular (code seul) — fichiers à commiter sur TFS

Branche extraite : `feature/nova-mss-weda-integration`. Aucune opération git. 54 fichiers sous `Client/Angular/front/` :

- **nouveaux** : `libs/mss/src/core/utils/mail-ring.util.ts` (+spec), `core/utils/mail-ring-steps.util.ts` (+spec),
  `ui/mail-ring/` (composant `mss-mail-ring`), `features/mail/components/mail-ring-panel/` (bloc du détail),
  `features/mail/services/mail-biology-ack-live.service.ts` (+spec), specs `mail-header.ring`, `mail-detail.ring`,
  `mail-state.service.ring` ;
- **modifiés** : modèles `biology-ack`, `mail`, `mail-event`, `user-settings` ; `mail-events-stream.service` (+spec) ;
  `mail-header.component.{html,ts,scss}` ; `mail-detail.component.{html,ts,scss}` et ses 9 specs ;
  `biology-ack-panel.component.*` ; `mail-side-panel.component.{html,ts,spec}` (section d'acquittement retirée) ;
  `mss-mail.component.ts` (+ spec handling) ; `mail-state.service.ts` ; `mss-settings.component.{html,ts,spec}` ;
  e2e `functional.e2e.ts`, `support/weda.ts`, `support/e2e-backend.ts`.
- Unitaires : 83 mutations, toutes rouges sur le test visé. Suites après la passe qualité, lancées par PowerShell :
  `nx test mss-lib` **2 129 / 2 129**, `nx test weda2` **2 683 / 2 683** ; `nx build weda2` OK ; ESLint 0 erreur.

### Passe qualité (/simplify)

- Applied & committed : client-mobile : 3 fichiers (`9ec2ddb`) — type de dossier mis en cache par chemin (la liste
  parcourait l'arbre des dossiers à chaque ligne et à chaque rendu), tableau mort retiré, gardes redondantes.
- Applied (code-only, uncommitted) : client-angular : 3 fichiers — contexte de l'anneau calculé une fois par ligne au
  lieu de deux, enveloppe inutile retirée du bloc du détail.
- No change : api-mail.
- Skipped (contract) : dtos-mss.

### Parcours e2e

- Catalogue (api-mail) : ajoutés v1 `E2E-RING-001`, `E2E-RING-002`, `E2E-RING-003`, `E2E-SETTINGS-005` ; montés
  `E2E-ASSIGN-001` 2 → 3, `E2E-BIO-001` 2 → 3, `E2E-BIO-003` 1 → 2, `E2E-BIO-007` 1 → 2, `E2E-DETAIL-004` 1 → 2
  (angular seul). Adapté sans changer de version : `E2E-BIO-004` (les deux clients).
- **Mobile, joués contre le banc `--serve-only`** : RING-001/002/003, SETTINGS-005, ASSIGN-001, BIO-001/003/004/007.
  8 verts au premier passage ; SETTINGS-005 rouge sur le test lui-même (motif `/^\S$/` contre « C » entouré
  d'espaces), corrigé (`6f0e8f7`) puis vert.
- **Preuves par mutation mobiles** (ng serve recompile, scénario rejoué, source restaurée) :

| Mutation | Scénario | Rouge sur |
|---|---|---|
| M1 `isRead ? 2 : 1` → `1` | E2E-RING-001 | « courrier ouvert — 2 étape(s) franchie(s) » |
| M2 `withBiologyAck` neutralisé dans le détail | E2E-RING-002 | « compte rendu résolu, dans le détail — anneau fermé » |
| M3 `waitingOf` ne rend plus `patient` | E2E-RING-002 | « après « Rappel patient » — 3 étape(s) franchie(s) » |
| M4 `unassigned` forcé à faux | E2E-RING-003 | « la ligne écrit « Non affecté » » |
| M5 `mine` forcé à faux | E2E-RING-003 | « le message est à elle » |
| M6 `updateListMarker` sans effet | E2E-SETTINGS-005 | enregistrement du réglage |
| M7b initiales vides au centre | E2E-ASSIGN-001 | « l'anneau de sa ligne porte ses initiales » |

  Une première M7 ne compilait pas (TS18047) : ng serve gardait l'ancien bundle et le scénario restait vert. Refaite
  avec une mutation qui compile, contrôlée par le compteur de bundles du journal de ng serve.

- **weda2, joués contre le banc `--serve-only`** : RING-001/002/003, SETTINGS-005, ASSIGN-001, BIO-001/003/004/007,
  DETAIL-004. Premier passage : 9 verts, **DETAIL-004 rouge sur un vrai défaut** — à 1366×768, le bloc de l'anneau
  défilait en interne (plafond 50 %) et coupait le bouton « Marquer comme résolu » : deux zones de défilement dans la
  lecture, contre « un seul défilement » de l'attendu. Correctif : `biology-ack-panel` compacté (dernière action sur la
  ligne d'en-tête, « Choisir l'action » remplacé par les intitulés d'étape, boutons de 28 px, les trois groupes sur une
  rangée qui passe à la ligne), plafond de sécurité du bloc à 75 % ; mesuré 265 px sans défilement interne
  (`clientHeight = scrollHeight`), bouton entièrement visible. DETAIL-004 v2 affirme désormais le bouton dans la vue
  (`toBeInViewport({ ratio: 1 })`) ; l'assertion « au plus la moitié de la lecture », que l'attendu ne demande pas, est
  retirée ; le test retire d'abord l'étiquette « Lecture-e2e » d'un essai précédent (`removeTagFromInbox`).
- **Rejeu sur un seed neuf, après correctif** : **10 / 10 verts**.
- **Preuves par mutation weda2** (recompilation prouvée par un marqueur cherché dans le bundle servi, sources restaurées,
  sommes de contrôle identiques) :

| Mutation | Scénario | Rouge sur |
|---|---|---|
| util : `filled` forcé à 1 | E2E-RING-001 | « courrier ouvert, dans le détail : 2 segment(s) plein(s) sur 3 » |
| util : étape `+ 0` | E2E-RING-002 | « compte rendu à acquitter : 1 segment(s) plein(s) sur 4 » |
| ligne : mention d'attente coupée | E2E-RING-002 | « la ligne écrit « Attente patient » » |
| ligne : « Non affecté » coupé | E2E-RING-003 | « la ligne écrit « Non affecté » » |
| util : centre forcé vide | E2E-RING-003 | « chez le titulaire, l'anneau porte les initiales de la délégataire » |
| réglages : `triggerSave()` neutralisé | E2E-SETTINGS-005 | « « Icône classique » est enregistrée par le serveur » |
| util : `mine` forcé à faux | E2E-ASSIGN-001 | « ses initiales sont sur fond plein : le message est à elle » |
| détail : `[documents]="[]"` | E2E-BIO-001, BIO-003, BIO-007, DETAIL-004 | « l'acquittement est dans le bloc de l'anneau, en tête du message » |

- weda2 après le correctif du bloc : `nx build weda2` OK, `nx test mss-lib` **2 129 / 2 129**, `nx test weda2`
  **2 683 / 2 683** (PowerShell), ESLint 0 erreur, stylelint 0. La liste TFS reste de 54 fichiers.

### Points laissés ouverts (pour la revue et le HAG)

- Mobile : l'anneau remplace aussi l'avatar vert des messages de patient (la couleur disparaît de la ligne, le tag
  « Patient » reste).
- Mobile : après un acquittement, la ligne du message est relue du serveur (une requête de plus), en plus de l'évènement.
- Stitch : les écrans `mail-list` et `mail-detail` du projet `client-mobile` datent d'avant l'anneau. Ni `edit_screens`
  (interdit) ni génération lancée : la ligne de DoD « références Stitch mises à jour » reste à faire dans Stitch, d'après
  la variante D des maquettes.
- Hors ligne, le contenu d'un message ne porte pas ses documents (antérieur à la task) : pas d'historique d'acquittement
  hors ligne.
- Taille : PR mobile ≈ 52 fichiers, PR api-mail 16 fichiers, au-delà du repère d'environ 30 pour le mobile.

### Vert marqué

- api-mail `bbb6d978`, client-mobile (HEAD poussé), client-angular (arbre final) — `Tools/green/green.py`.
- Next step : `/review task-497 --code`.

### Reprise 1 après /review

| Point | Défaut | Correctif | Test | Preuve rouge |
|---|---|---|---|---|
| B1 (mobile) | `isHandled` testé avant `isToHandle` : anneau fermé sur un message à traiter | « à traiter » ou compte rendu en attente prime sur « traité » | `treatment-ring.util.spec` (2 cas) | rouges sur le code d'avant (`closed` au lieu de `open`), puis mutation |
| B2 (mobile) | le patch de `MailBiologyAckChanged` laissait la ligne « traitée » | `pendingBiologyAcksCount > 0` ouvre l'anneau quel que soit `handling` | `mail-list.ring.spec` + 2 cas util | rouges sur le code d'avant, puis mutation |
| B2 (web) | même défaut ; le détail ne relisait la ligne qu'après « Résolu » | même règle ; `applyBiologyAckProgress` remet `isToHandle` sans effacer qui a traité ; `refreshRing` après chaque acquittement | util, état, détail | rouges sur le code d'avant (`closed`, `refreshRing` 0 fois), 6 mutations |
| B3 (mobile) | la page renvoyait au détail sa copie périmée du message | la page relit seulement les documents ; le composant fusionne l'évènement sur son message courant | `mail-detail.page.spec`, `mail-detail.ring.spec` | mutations B3a à B3d |
| B4 (web) | parcours de l'arbre et vue neuve à chaque rendu de chaque ligne | `MailStateService.ringFolderTypes` (computed), `mailRingRowMemo` par ligne (`core/utils/mail-ring-row.util.ts`) | même instance tant que rien ne change ; transition qui survit au rafraîchissement | rouges sur le code d'avant, 11 mutations (1 équivalente survit : `filled` hors comparaison, le libellé porte l'étape) |
| S1 (web) | anneau à 4 segments sans comptes rendus : étapes du courrier | 4 étapes de la biologie | util et bloc du détail (4 tests) | rouges sur le code d'avant, 3 mutations |
| S2 (mobile) | « Antérieur au suivi » déduit des compteurs | `isTracked` lu du document (ajouté au modèle) | util et détail | mutations S2a à S2c |
| S3 (mobile) | sous-dossier d'Envoyés avec anneau | `ringFolderType`, type hérité du parent | util (6 cas), liste, détail | mutations S3a à S3c |
| S6 (mobile) | « Masquer » cachait les boutons d'acquittement | entrée `dismissible`, à `false` dans le bloc de l'anneau | détail, panneau | mutations S6a, S6b |

- Relecture « qu'est-ce que ça casse » :
  - web : la première version de B2 ouvrait l'anneau quand `handling` est inconnu (ligne non synchronisée) et aurait
    affiché « Non affecté » sans le savoir — garde remise, test et mutation rouge ; un double de `refreshRing` qui
    répondait toujours « traité » rendu neutre ;
  - mobile : `withBiologyAck` aurait passé « suivi » un compte rendu antérieur au suivi acquitté localement — corrigé
    (`isTracked` à `false`), test.
- Défaut voisin laissé ouvert (antérieur à la task, hors liste de la revue) : la page de détail mobile remplace encore le
  message du détail par sa copie sur `mailUpdated$` (réponse partie) et `emailsEnriched$` ; le traitement, l'attribution
  et l'avancement d'acquittement reçus depuis l'ouverture s'y perdent jusqu'au rechargement.
- Prévention (règle d'or) : `conventions/angular.md`, entrées `drapeaux-serveur-combinables` et
  `page-hote-ne-renvoie-pas-sa-copie`.
- Validations :
  - mobile : commit `06fb9b5`, poussé ; suite complète **1 933 / 1 933**, build OK, ESLint 0 erreur, CRLF OK ;
  - web : 2 fichiers nouveaux (`core/utils/mail-ring-row.util.ts` + spec, liste TFS : **56 fichiers**), 9 modifiés ;
    `nx test mss-lib` **2 160 / 2 160**, `nx test weda2` **2 683 / 2 683**, `nx build weda2` OK, ESLint 0 erreur ;
  - api-mail, dtos-mss : non touchés.
- e2e : aucun scénario existant ne change. Le cas B2 en direct (« Résolu », puis une action d'un autre poste) n'a pas de
  parcours ; une étape de E2E-RING-002 (v2) le couvrirait — décision de catalogue laissée à la revue.
- Vert marqué : client-mobile `06fb9b5`, client-angular (arbre final).
- Next step : `/review task-497 --code`.

### Reprise 2 après décision humaine (HAG, 2026-11-27)

Décision : sur weda2, le bloc de l'anneau quitte la tête du message pour la section « Traitement » du panneau
« Actions & dossier », en premier (Objectif, règle 9). Le mobile ne change pas.

| Point | Changement | Test | Preuve rouge |
|---|---|---|---|
| H1 — section | `SidePanelSectionKey` `ring` (« Traitement », icône `check-circle`), première section du panneau ; `mss-mail-ring-panel` projeté dans `[mssPanelSection=ring]`, retiré de `.mail-detail-reading` | `mail-side-panel.component.spec` (section en premier, rail), `mail-detail.side-panel.spec` (section en premier, bloc hors lecture), `mail-detail.ring.spec` (rendu réel ciblé dans la section) | M1 (section jamais poussée) : 5 rouges ; M6 (bloc dans la lecture) : 14 rouges ; M7 (section introuvable) : 4 rouges |
| H1 — présence | `hasRingSection` : un compte rendu signalé, ou l'anneau du message (`mailRingView`, même règle que les unités du bloc) ; aucune section dans Envoyés / Brouillons / Corbeille sans compte rendu, ni tant que l'état de traitement est inconnu | `mail-detail.side-panel.spec` (Envoyés ; courrier dont l'état arrive) | M3 (Envoyés reçoit une section) : 2 rouges |
| H1 — signal | pastille du rail (`pending`) et puce « Acquittement à traiter » (rétablies) tant qu'un compte rendu reste à acquitter ; la puce ouvre la section | `mail-detail.side-panel.spec` (pastille, puce, compte rendu résolu) | M2 (pastille jamais posée) : 1 rouge ; M8 (puce absente) : 2 rouges |
| H1 — avis | l'avis « Ce compte rendu de biologie reste à acquitter » ouvre le message sur la section (`requestedSidePanel = 'ring'`, rétabli) | `mss-mail.component.handling.spec`, `mail-detail.side-panel.spec` (panneau en rail redéplié) | M4 (l'avis ne demande rien) : 1 rouge ; M5 (le détail ignore la demande) : 1 rouge |
| H1 — largeur | bloc à la largeur du panneau (320 px) : anneau 56 px à côté des étapes, sans défilement propre (le corps du panneau défile) | `mail-ring-panel.component.spec` (taille de l'anneau) | — (mise en page, jugée par E2E-DETAIL-004 : « Marquer comme résolu » à l'écran) |

- Mutations : `scratchpad/r2/mutate.py`, huit mutations, chacune rouge sur l'assertion prévue, fichiers restaurés.
- Parcours e2e (weda2) : E2E-DETAIL-004 v2 réécrit (icône « Traitement » et sa pastille au rail, puce, bloc absent de la
  lecture, contenu en haut, la puce ouvre la section avec « Marquer comme résolu » à l'écran) ; aide `expectAckUnderRing`
  ouvre la section « Traitement » et y cherche l'acquittement (BIO-001, BIO-003, BIO-007, RING-002) ; RING-001 ouvre la
  section avant de lire le grand anneau. Catalogue : textes de BIO-001 v3, BIO-003 v2, BIO-007 v2 et DETAIL-004 v2 corrigés
  pour weda2, **sans montée de version** (versions nées dans cette task, absentes de `develop` ; voie mobile inchangée).
  Rejoués seuls sur le banc (`--serve-only` + `--grep`) : DETAIL-004, BIO-001, BIO-003, BIO-007, RING-001, RING-002
  **6 / 6 verts**. Mutation e2e : bloc remis dans la lecture (`data-mutx`, recompilation prouvée dans le bundle servi
  puis son absence après restauration) → DETAIL-004 et BIO-001 rouges sur « l'acquittement est dans la section
  « Traitement » du panneau ». Les voies complètes restent à `/e2e`.
- Validations : `nx test mss-lib` **2 164 / 2 164**, `nx test weda2` **2 683 / 2 683**, `nx build weda2` OK, ESLint 0 erreur
  sur les fichiers touchés, stylelint OK, `tsc` e2e OK.
- Prévention (règle d'or) : le défaut vient d'une revue de design qui jugeait le bloc seul, sans la lecture assemblée ;
  consigne `bloc-en-tete-de-lecture` ajoutée dans `conventions/angular.md`.
- Fichiers weda2 à commiter sur TFS (en plus des 56) : aucun nouveau fichier ; modifiés : `mail-side-panel.component.{ts,html,spec.ts}`,
  `mail-detail.component.{ts,html,scss}` et ses specs, `mail-ring-panel.component.{ts,scss,spec.ts}`,
  `mail-state.service.ts`, `mss-mail.component.ts`, `mss-mail.component.handling.spec.ts`, `e2e/mss-e2e/support/weda.ts`,
  `e2e/mss-e2e/specs/functional.e2e.ts`.

### Reprise 3 après /review (passage 4)

| Point | Défaut | Correctif | Test | Preuve rouge |
|---|---|---|---|---|
| B5 | l'avis « reste à acquitter » consommait sa demande dans le tour qui change de message ; le `resetKey` du nouveau message repliait ensuite le panneau en lecture étroite | la demande désigne son message (`RequestedSidePanel` : section, dossier, uid) ; consommée seulement quand ce message est affiché **et** son contenu servi (ou en échec) | `mail-detail.side-panel.spec` : autre message en lecture étroite (demande + sélection dans le même tour, rail disparu) ; demande pour un autre message sans effet ; `mss-mail.component.handling.spec` (la demande porte le message) | rouges sur le code d'avant (rail toujours là) ; mutations B5a (sans attendre le contenu), B5b (sans vérifier le message), B5c (l'avis ne désigne aucun message) : chacune 1 rouge |
| S7 | pastille du rail absente avant le chargement du contenu | `isBiologyAckPending` : la ligne (`pendingBiologyAcksCount`) tant que le contenu n'est pas chargé, les comptes rendus ensuite | `mail-detail.side-panel.spec` (avant / après chargement) | rouge sur le code d'avant ; mutation S7 : 1 rouge |
| S8 | commentaires périmés du panneau d'acquittement | `biology-ack-panel.component.{html,scss}` décrivent la section « Traitement » (320 px) | — | — |
| S9 | anneau fermé lu sans être vu (RING-001, étape 3) | visibilité de l'anneau dans la section avant ses attributs | e2e RING-001 | même garde que l'étape 2, rejouée par `/e2e` |

- Relecture « qu'est-ce que ça casse » : `requestedSidePanel` n'a que deux usages (l'avis, le détail) ; une demande jamais
  consommée (message quitté avant son chargement) reste attachée à ce seul message et ouvre sa section à la prochaine
  visite, sans effet sur les autres. Test : `afterEach` du spec rend l'horloge réelle avant `verify`, et le test S7 n'affirme
  qu'après avoir servi la requête : un rouge n'entraîne plus les tests suivants en cascade (constaté sous mutation).
- Validations : `nx test mss-lib` **2 167 / 2 167**, `nx test weda2` **2 683 / 2 683**, `nx build weda2` OK, ESLint 0 erreur,
  Prettier OK, `tsc` e2e OK. api-mail, dtos-mss, client-mobile : non touchés.
- Prévention : `conventions/angular.md`, entrée `demande-d-ouverture-liee-a-son-objet`.

## Sonar log

> **Après les reprises 2 et 3 (2026-11-27)** : non rejoué. Depuis `bbb6d978`, seul `e2e/scenarios.yml` a changé dans
> api-mail (`git diff --name-only bbb6d978..HEAD -- '*.cs'` vide) : aucun fichier analysé par Sonar. Les KPIs ci-dessous
> restent ceux du code C# de la PR. Skip mesuré, dans l'esprit de la décision humaine du 2026-11-19 (task-485).

Analysé à api-mail `bbb6d978` (2026-11-27, SonarQube 9.9.8, projet `healthplatform-api-mail`, période de nouveau code :
30 jours depuis le 2026-10-28). Une analyse complète : begin → build Release → cinq suites avec couverture OpenCover → end.

- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,1 % (lignes 98,3 %, branches 90,6 %)
- Phase 1 — Issues fixées : 0 (0 bug / 0 vulnérabilité / 0 code smell / 0 hotspot : aucune issue ouverte sur le nouveau
  code, ni sur le projet entier)
- Phase 1 — Tests ajoutés : 0 (cible de couverture du nouveau code atteinte)
- Phase 2 (legacy) : itérations 0 / 5 — non jouée : toutes les cibles projet sont déjà tenues (0 bug, 0 vulnérabilité,
  maintenabilité A, couverture 97,6 % ≥ 95 %), arrêt anticipé du Step 1
- Phase 2 — Issues fixées : 0
- Phase 2 — Issues restantes : 0
- Aucun commit : HEAD inchangé (`bbb6d978`), le marqueur vert de `/develop` tient
- Build / tests : ✓ green — domain 388, application 4 373, infrastructure 749, api 1 388, integration 1 386 (+ 16 skipped),
  0 échec, aucun FATAL
- Couverture résiduelle du code de la task (non bloquante, sous le seuil de signalement) : 2 conditions de
  `BiologyAckProgressRule.Leader.Leads` (comparaison d'instants nullables, l. 99) et 1 de
  `MailRepository.ToBiologyAckDto` (`MedicalDocumentId ?? Guid.Empty`, l. 5492). Les 4 lignes non couvertes de
  `SseMailEventBroker` (l. 111-121) appartiennent à task-456 et task-457, pas à cette task.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 95,9 % | 96,1 % | +0,2 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,6 % | 97,6 % | 0 pt |
| Duplication | 0,3 % | 0,3 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : affected (`npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss`),
  branche Angular `feature/nova-mss-weda-integration`, `origin/next` rafraîchi (`c49efacd..16c31ba9`).
- Scope : `tag:scope:mss` (défaut, aucun champ `**LintBase**` / `**LintProjects**`).
- Pipeline fidelity : mêmes commandes que `Client/Angular/azure-pipelines.yml` (Stage 2 CI), avec les deux
  divergences voulues (base `origin/next`, lint filtré `tag:scope:mss`).
- Baseline : **0 erreur** / 139 warnings sur les 13 projets que lance la commande (`--projects` ne restreint toujours
  pas `nx affected` sur ce workspace, défaut déjà constaté sur task-367) ; dans `tag:scope:mss` : 0 erreur /
  100 warnings (`mss-lib` 49, `mss-e2e` 51, `mss` 0).
- Fichiers de la task (51 `.ts`/`.html` de l'arbre de travail, `npx eslint --format json`) : **0 erreur /
  41 warnings, tous préexistants** — aucun sur une ligne ajoutée par la task (`git diff -U0 HEAD`), aucun dans les
  fichiers neufs. Détail : `max-lines` sur 7 fichiers déjà au-delà de 500 lignes à HEAD (`mail-detail.component.ts`,
  `mail-header.component.ts`, `mss-mail.component.ts`, `mail-state.service.ts`, `mss-settings.component.ts`,
  `functional.e2e.ts`, `e2e-backend.ts`) ; `jsdoc/require-example` (34) sur des fonctions existantes.
- Final : identique à la baseline (0 erreur). Aucun `--fix` lancé : le critère d'arrêt de l'étape (0 erreur) est
  atteint d'emblée, et l'auto-fixer aurait réécrit des warnings préexistants dans 13 projets, hors de la tranche de
  la task (règle 6 ; le seul warning corrigible dans ses fichiers insère un `@example` vide).
- Iterations : 0 / 5. Fichiers modifiés par `/lint-angular` : **aucun** — build et suites non rejoués, vert non
  re-marqué (l'arbre est celui qu'a laissé la reprise 1).
- `conventions/angular.md` : rien à consigner (aucune correction manuelle).

| Iter | Errors before | Errors after | Build | Tests |
|------|---------------|--------------|-------|-------|
| — (baseline) | 0 | 0 | n/a (aucun fichier touché) | n/a |

## Lint mobile log

- Branche : `feat/task-497-anneau-de-traitement-liste-et-detail` (HEAD `06fb9b5`).
- Baseline `npm run lint` : **All files pass linting** — 0 erreur, 0 avertissement.
- Itérations : 0 sur 5. Aucune correction, aucun commit. Build et suite non rejoués (rien de modifié) : le vert de
  `/develop` (reprise 1, 1 933 / 1 933) tient sur ce code.
- Conventions : rien à consigner.

## E2E log

| Voie | Déclencheur | Jouée | Résultat | Durée |
|---|---|---|---|---|
| mobile (`npm run e2e:headless`) | api-mail, client-mobile, dtos-mss touchés | oui (code 06fb9b5) | **84 verts**, 0 flaky, 0 rouge, parité verte | 14 min |
| angular (`npm run e2e:mss`) | api-mail, client-angular, dtos-mss touchés | oui (arbre de travail final) | **107 verts**, 0 flaky, 0 rouge, parité verte | ~15 min |

- Démontage vérifié : ports 5052 / 8100 / 4200 / 3993 / 3465 / 3143 / 47399 libres, aucun conteneur e2e résiduel.
- Écrans modifiés sans spec e2e modifié : aucun (les deux suites portent les parcours RING, SETTINGS-005 et les
  versions montées).
- Porte (`mss.mail.e2e.dll gate`, catalogue de la branche api-mail) : code 0.

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
| E2E-BIO-001 | 3 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 2 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-BIO-004 | 1 | headless | Un compte rendu acquitté puis déplacé depuis un autre client garde son acquittement | ✅ | ✅ |
| E2E-BIO-007 | 2 | headless | Un compte rendu arrivé avant la date de début du suivi ne réclame rien, et s'acquitte quand même | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 2 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-DETAIL-006 | 1 | headless | Après une réponse, le message d'origine dit « Vous avez répondu à ce message le… » | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-012 | 1 | headless | Traiter tous les résultats d'une recherche | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-015 | 1 | headless | Le détail surligne ce qui a été cherché | ✅ | — |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
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
| E2E-SHARED-004 | 1 | headless | Dans la conversation, un message écrit par un délégataire pour le compte de son expéditeur le dit | ✅ | ✅ |
| E2E-SHARED-005 | 1 | headless | Dans la fiche patient, l'aperçu d'un message écrit par un délégataire le dit sous « De » | ✅ | — |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |
| E2E-TAG-001 | 1 | headless | Choisir un tag de la boîte dans la liste, créer un tag de plusieurs mots | ✅ | ✅ |
| E2E-TAG-002 | 2 | headless | Les tags système classent la Boîte de réception : Biologie, Patient, Pour info | ✅ | ✅ |
| E2E-TAG-003 | 1 | headless | Combiner deux tags et retrouver le filtre « Non lus » | ✅ | ✅ |
| E2E-TAG-004 | 1 | headless | Une combinaison de tags où rien n'est à traiter s'ouvre sur « Tous », le réglage reste « À traiter » | ✅ | ✅ |
| E2E-TRIAGE-001 | 2 | headless | Traiter un message le retire de « À traiter », le compteur baisse, « Annuler » le remet | ✅ | ✅ |
| E2E-TRIAGE-002 | 1 | headless | Traiter les messages affichés laisse le compte rendu de biologie à acquitter | ✅ | ✅ |
| E2E-TRIAGE-006 | 1 | headless | Dans la vue « Biologie », « Traiter les résultats sans anomalie » laisse le résultat anormal à traiter | ✅ | ✅ |
| E2E-TRIAGE-007 | 1 | headless | Répondre à un message le fait sortir de « À traiter », libellé « — répondu » | ✅ | ✅ |
| E2E-TRIAGE-008 | 1 | headless | « Traité » sur un message d'un fil traite aussi ses précédents, jamais le plus récent ; « Annuler » les remet | ✅ | ✅ |
| E2E-SHARED-003 | 1 | headless | Le délégataire traite un message, le titulaire le voit traité « par » le délégataire | ✅ | ✅ |
| E2E-ASSIGN-001 | 3 | headless | Le titulaire attribue un message à la secrétaire délégataire, qui le trouve dans « Pour moi » | ✅ | ✅ |
| E2E-ASSIGN-002 | 1 | headless | Traiter un message attribué le retire de « Pour moi », et le détail dit « traité par » | ✅ | ✅ |
| E2E-ASSIGN-003 | 1 | headless | La puce « Pour moi » porte son compteur, n'apparaît pas à zéro et reste affichée quand on traite le dernier | ✅ | ✅ |
| E2E-CONV-001 | 1 | headless | Lire un fil en vue chat et y répondre en une ligne, à tous les participants | ✅ | ✅ |
| E2E-CONV-002 | 1 | headless | Joindre un fichier depuis la vue chat | ✅ | ✅ |
| E2E-CONV-003 | 1 | headless | La vue chat s'ouvre d'elle-même sur un fil engagé, et n'existe qu'en mode Conversation | ✅ | ✅ |
| E2E-RING-001 | 1 | headless | L'anneau d'un courrier se remplit de « reçu » à « lu » puis se ferme à « traité » | ✅ | ✅ |
| E2E-RING-002 | 1 | headless | L'anneau d'un compte rendu de biologie à acquitter suit ses acquittements, jusqu'à « résolu » | ✅ | ✅ |
| E2E-RING-003 | 1 | headless | En boîte partagée, « Non affecté » puis les initiales de la personne attribuée dans l'anneau | ✅ | ✅ |
| E2E-SETTINGS-005 | 1 | headless | Choisir « Icône classique » pour la liste, le retrouver après rechargement, revenir à l'anneau | ✅ | ✅ |

**Divergences temporaires ouvertes** (9) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-012 [mobile] — la sélection de tous les résultats arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relu à : dtos-mss `6f00908`, api-mail `bbb6d978`, client-mobile `6f0e8f7`, client-angular arbre de travail (54 fichiers).
Deux relecteurs indépendants (backend + contrat ; deux clients), sans le `## Develop log`.

**4a — verrou intégration (règle 1b)** : chaque comportement atteignable par un endpoint a son test d'intégration sur la
vraie pile, lu dans la réponse réelle, vu rouge (tableau du `## Develop log`, api-mail) : étape et dernière action sur les
trois chemins de liste (dossier, tag, hors ligne), cas d'échec sans anomalie, deux comptes rendus, page sans commande SQL
de plus, historique sur la lecture d'un message seulement, évènement en direct en boîte partagée avec l'auteur réel dans
la trace, réglage `listMarker` par personne. ✅

**4c — consommateurs du contrat** : `api-mcp : aucun impact` / `client-mobile : aucun impact` / `client-angular : aucun
impact` (avertissements de lecture tolérante habituels). ✅

**4b — clause DoD du parcours** : RING-001/002/003 et SETTINGS-005 v1, ASSIGN-001 v3, BIO-001 v3, BIO-003 v2,
BIO-007 v2, DETAIL-004 v2 (angular) au catalogue, aux versions déclarées par les tests des deux clients. ✅

**Backend (dtos-mss, api-mail)** : APPROVED. Suggestions non bloquantes : une seule collecte pour la ligne et
l'évènement (codes critiques copiés deux fois), test de composition du relais sur le vrai conteneur, `ThenBy(Id)` sur
l'historique, message d'échec du test SQL qui dit de remesurer la référence.

**Clients** : CHANGES REQUESTED.

#### À corriger par la reprise

- **B1 — mobile — `core/utils/treatment-ring.util.ts` (≈ l. 150)** : `isHandled` est testé avant `isToHandle`. Une ligne
  servie `{ isToHandle: true, isHandled: true }` — compte rendu analysé après un « Traité », ou action intermédiaire
  posée après « Résolu » — donne un anneau **fermé**, même après rechargement, contre la règle 1 (« à traiter » = anneau
  ouvert) et contre `MailHandlingRule` du serveur. Correctif : « à traiter » (ou un compte rendu en attente) prime sur
  « traité ». Test unitaire du cas `{ isToHandle: true, isHandled: true }`, vu rouge.
- **B2 — mobile et web — mise à jour en direct** : après « Résolu », une action intermédiaire ne publie que
  `MailBiologyAckChanged` ; le patch de ligne (`biologyAckPatch` / `applyBiologyAckSummary` mobile,
  `applyBiologyAckProgress` web) ne touche que les champs de biologie, la ligne garde `isHandled` et l'anneau reste
  fermé chez les autres personnes jusqu'au rechargement. Correctif : un compte rendu en attente (`pending > 0`, hors
  Envoyés / Brouillons / Corbeille) ouvre l'anneau quel que soit `handling`, ou le patch pose `isToHandle = true`.
  Côté web, le détail ne relit la ligne qu'après « Résolu » (le mobile après chaque acte) : aligner. Un test unitaire
  par client, vu rouge.
- **B3 — mobile — `mail-detail/mail-detail.page.ts` (abonnement `biologyAckChanged$`)** : la page fusionne le patch dans
  **sa** copie du message, jamais mise à jour par `handling.applied$`, `assignments.applied$` ni la lecture ; elle
  renvoie au composant un message périmé (ancien traitement, ancien « À traiter par », non lu). Correctif : la page
  rafraîchit le contenu, la fusion des agrégats se fait dans le composant sur son message courant. Test vu rouge.
- **B4 — web — `mail-header.component.ts`, getter `ringRow`** : à chaque rendu de chaque ligne, parcours de tout
  l'arbre des dossiers et allocation d'une vue neuve ; l'entrée de `mss-mail-ring` change à chaque rendu (segments
  recalculés, transition d'un segment gagné coupée), et `folders()` change à chaque acquittement. Correctif : table
  chemin → type calculée une fois (comme le `computed` du mobile), vue mémorisée par message. Test vu rouge (la
  transition survit à un rafraîchissement de la liste, ou la vue est la même instance tant que le message ne change pas).
- **S1 → à corriger — web — `mail-ring-panel` / `mailRingSteps`** : un anneau de message à 4 segments sans comptes rendus
  chargés liste les étapes Reçu / Lu / Traité ; le mobile liste les 4 étapes de la biologie. Aligner, test vu rouge.
- **S2 → à corriger — mobile — `reportRing`** : « Antérieur au suivi » est déduit de `!!last && pendingBiologyAcksCount
  === 0` et s'affiche à tort sur une ligne périmée. Lire `isTracked` du document (déjà servi par le contrat), comme le
  web (`isBiologyAckClaimed`). Test vu rouge.
- **S3 → à corriger — mobile — `canHandleFolder`** : un sous-dossier d'Envoyés reçoit un anneau ; le web hérite du type
  du parent (`ringFolderType`). Aligner (règle 1 : « Dans Envoyés, Brouillons et Corbeille, la ligne garde l'initiale »).
  Test vu rouge.
- **S6 → à corriger — mobile — `biology-ack-panel`** : le bouton « Masquer » peut cacher les boutons d'acquittement
  désormais en tête du message. Le retirer de ce contexte ; test vu rouge.

#### Arbitrage humain

- **A1 — règle 8, exemple 2** : l'exemple « Biologie, valeur critique. Étape 1 sur 4 : reçu. Non affecté. » omet
  « reste : … », que les deux clients ajoutent à tous les libellés (comme les maquettes). Recommandation de la forge :
  garder « reste : … » partout, plus utile au lecteur d'écran.
- **A2 — règles SCSS de weda2** : `mail-ring.component.scss` porte des couleurs littérales (contraste mesuré sur ces
  valeurs), contraire à `front/CLAUDE.md`. Recommandation : passer aux jetons `--ds-*` équivalents si leur contraste
  reste ≥ 3:1, sinon acter l'exception en commentaire.
- **A3 — cohérence d'affichage entre clients** : un compte rendu résolu montre un anneau fermé sur mobile, ses seules
  étapes sur web ; la coche est animée sur mobile, pas sur web. Recommandation : anneau fermé sur les deux, sans
  animation de la coche.

Suggestions sans suite dans cette reprise : collecte unique backend, test de composition du relais, `ThenBy(Id)`,
message du test SQL ; scénario e2e en direct à deux personnes avec une action après « Résolu » (il aurait attrapé B2 ;
les tests unitaires de B2 en tiennent lieu dans cette reprise).

### Passage 2 (revue anticipée) — APPROVED

**Approved at** : dtos-mss `6f00908`, api-mail `bbb6d978`, client-mobile `06fb9b5`, client-angular arbre de travail
(56 fichiers, après la reprise 1).

- Backend : inchangé depuis le passage 1, APPROVED. `contract_impact.py check` : aucun impact pour les trois consommateurs.
- Clients : relecteur indépendant, diff de la reprise lu en premier. Rien de cassé : même règle d'ouverture et même
  ordre que `MailHandlingRule` dans les deux clients (Envoyés / Brouillons / Corbeille et sous-dossiers filtrés d'abord,
  `handling` inconnu n'ouvre rien) ; mémoire de ligne web sans risque de vue périmée (aucun message modifié en place) ;
  une seule relecture par acquittement, résiliée avec le composant.
- B1, B2, B3, B4, S1, S2, S3, S6 : corrigés, tests qui échoueraient au retour du code d'avant.

#### Suggestions non bloquantes (recopiées dans la PR)

- **N1 — mobile — `mail-detail.page.ts` (`mailUpdated$`, `emailsEnriched$`)** : la page renvoie encore sa copie du
  message au composant (défaut antérieur à la task, contraire à la consigne `page-hote-ne-renvoie-pas-sa-copie`) ; ne
  fusionner que `reply` / `isAnswered` et les champs d'enrichissement, dans le composant.
- **N2 — web — `mail-state.service.ts` (`refreshRing`)** : la relecture après un acquittement peut écraser `isRead` et
  `assignment` par une réponse partie avant un geste plus récent, et pose `handling` sans passer par
  `MailHandlingService.apply` (une ligne résolue ne sort pas d'une vue filtrée « À traiter » sans flux) ; n'adopter que
  l'avancement d'acquittement et passer `handling` par le service, comme le mobile.
- **N3 — cohérence** : le web pose `isToHandle` sur la ligne, le mobile s'en remet à la règle ; même affichage.

### Passage 3 — décision humaine au HAG (2026-11-27)

Après la validation finale, l'humain a demandé de déplacer le bloc de l'anneau du détail weda2 vers le panneau latéral
(Objectif, règle 9, dernier point). Ce changement de comportement repasse par `/develop --reprise` avant le merge.

#### À corriger par la reprise

- **H1 — weda2 — le bloc de l'anneau va dans « Actions & dossier »** :
  - `mail-detail.component.html` : `mss-mail-ring-panel` quitte la zone de lecture et est projeté dans
    `mss-mail-side-panel`, dans une nouvelle section placée **en premier** (avant le doublon et le patient) ; libellé et
    icône de section cohérents avec les autres (`meta`), section absente quand le message n'a pas d'anneau ;
  - rail du panneau replié : icône de la section, pastille « en attente » (`pending`) quand un compte rendu reste à
    acquitter, clic qui ouvre le panneau sur la section ;
  - le bloc tient dans la largeur du panneau (anneau réduit si besoin, étapes et boutons empilés), sans défilement
    interne qui masque « Marquer comme résolu » ; mode superposé (écran étroit) compris ;
  - comportement inchangé : acquittement, confirmation et note, transition du segment, mise à jour en direct,
    relecture de la ligne (`refreshRing`) ;
  - tests unitaires vus rouges (section présente / absente, pastille du rail, bloc absent de la zone de lecture) ;
  - parcours e2e weda2 qui cherchent le bloc ou les boutons en tête du message (E2E-BIO-001, BIO-003, BIO-007,
    DETAIL-004, RING-002) : les cibler dans le panneau latéral, scénarios rouges rejoués d'abord (`--serve-only` +
    `--grep`) ; textes du catalogue qui disent « ont quitté le panneau latéral de weda2 » corrigés pour weda2, version
    montée seulement si l'assertion du client change, sans toucher la voie mobile ;
  - mobile : inchangé.

### Passage 4 (revue anticipée, après la reprise 2) — CHANGES REQUESTED

Relu à : api-mail `3ad2b65b` (catalogue seul depuis `bbb6d978`), client-angular arbre de travail ; dtos-mss et
client-mobile inchangés. Relecteur indépendant, diff de la reprise lu en premier.

- **4a** : aucun comportement atteignable par un endpoint ne change (api-mail : texte du catalogue seul). ✅
- **4c** : `api-mcp : aucun impact` / `client-mobile : aucun impact` / `client-angular : aucun impact`. ✅
- **4b (DoD)** : BIO-001 v3, BIO-003 v2, BIO-007 v2, DETAIL-004 v2 corrigés pour weda2, versions égales à celles
  déclarées par les tests ; voie mobile inchangée. ✅
- Vérifié et tenu : plus aucune référence à `ack` ; présence de la section = unités du bloc (ni section vide, ni bloc
  hors section) ; contenu projeté une fois et monté quand le panneau est masqué ; largeur 320 px ; « Marquer comme
  résolu » à l'écran en superposé ; acquittement, relecture de la ligne et évènement en direct inchangés.
- Le dernier rapport e2e rouge de `out/test-results` est celui de la mutation volontaire (`data-mutx`), après un
  passage 6 / 6 vert : pas un défaut.

#### À corriger par la reprise

- **B5 — weda2 — l'avis « reste à acquitter » n'ouvre plus le panneau en lecture étroite** (`mail-detail.component.ts`,
  effet task-454 ; `mss-mail.component.ts` `openPendingAck` ; `mail-side-panel.component.ts` effet `resetKey`) : la
  section `ring` existe dès la sélection (anneau du message), alors que l'ancienne section `ack` attendait le contenu.
  L'effet consomme la demande et déplie le panneau, puis le nouveau `resetKey` du message le replie
  (`expanded = !narrow`) : panneau en rail, demande perdue. Reproduit par le relecteur avec le vrai panneau
  (`scratchpad/reviewer-r2/race.spec.ts`). Le test unitaire posait la demande sur le message déjà affiché (vert qui
  ment). Correctif : la demande survit au changement de message (consommée une fois la section affichée pour le
  message demandé). Test : lecture étroite, demande et changement de message dans le même tour, rail disparu ; vu rouge.
- **S7 — weda2 — pastille du rail absente avant le chargement du contenu** (`sidePanelSections`) : tant que le contenu
  n'est pas chargé (ou s'il échoue), `pending` est faux alors que la ligne porte `pendingBiologyAcksCount > 0`.
  Retomber sur la ligne tant que le contenu n'est pas là. Test vu rouge.
- **S8 — weda2 — commentaires périmés** : `biology-ack-panel.component.html` (« a quitté Actions & dossier »),
  `biology-ack-panel.component.scss` (en-tête, `&__groups`) décrivent l'ancien emplacement.
- **S9 — e2e weda2 — anneau fermé lu sans être vu** (`functional.e2e.ts`, RING-001 étape 3) : après
  `openSidePanelSection(page, 'ring')`, affirmer la visibilité de l'anneau avant ses attributs.

#### Arbitrage humain

- Couleurs littérales `#475569` de `mail-ring-panel.component.scss` : relève de l'arbitrage A2 déjà ouvert (jetons `--ds-*`).

### Passage 5 (revue anticipée, après la reprise 3) — APPROVED

**Approved at** : dtos-mss `6f00908`, api-mail `3ad2b65b`, client-mobile `06fb9b5`, client-angular arbre de travail
(après la reprise 3).

- Relecteur indépendant, diff de la reprise 3 lu en premier : rien de cassé. `requestedSidePanel` n'a qu'un écrivain
  (`openPendingAck`) et un lecteur (le détail). B5 corrigé : la demande n'est consommée qu'une fois son message affiché et
  son contenu servi ou en échec, après la remise à zéro du panneau ; le test joue le vrai enchaînement. S7, S8, S9 corrigés.
- 4a / 4b / 4c : inchangés depuis le passage 4 (✅).

#### Suggestions non bloquantes (recopiées dans la PR)

- **N4 — weda2 — demande en suspens** : si le médecin quitte le message de l'avis avant son chargement, la demande reste
  attachée à ce message et ouvre sa section « Traitement » à la visite suivante. Correctif possible : la vider dès qu'un
  autre message est affiché.
- **N5 — weda2 — ordre d'effets implicite** : le correctif B5 suppose que l'effet de chargement (qui remet
  `contentLoadFailed` à faux) est déclaré avant celui de la demande ; un échec lié à la clé du message rendrait l'ordre
  indifférent.
- **N6 — e2e weda2 — `openSidePanelSection`** (antérieure à la task) ne regarde le rail qu'une fois.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/75 — `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/382 — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/136 — `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. 56 fichiers non commités sur
  `feature/nova-mss-weda-integration` : la liste est dans le `## Develop log` (« client-angular (code seul) — fichiers à
  commiter sur TFS »), plus `libs/mss/src/core/utils/mail-ring-row.util.ts` et son spec (reprise 1).
- Ordre de merge (règle 11, même US) : dtos-mss, puis api-mail, puis client-mobile ; weda2 avec eux.

### Validation finale

- Build + tests : vert réutilisé — api-mail `bbb6d978` (/develop), client-mobile `06fb9b5` (/develop, reprise 1),
  client-angular arbre final (/develop, reprise 1) ; dtos-mss : build rejoué, 0 erreur (pas de projet de test).
- Diff depuis l'approbation (passage 2) : aucun — /sonar, /lint-angular et /lint-mobile n'ont rien modifié.
- DoD : tous les points vérifiés, sauf « références Stitch mises à jour » (best-effort, laissé à l'humain : les écrans
  `mail-list` et `mail-detail` existent mais datent d'avant l'anneau).
- `## E2E log` : **E2E : vert** (mobile 84, angular 107, parité verte).
- Branches à jour de `develop` (0 commit de retard), aucun merge nécessaire.

## Timings

*(généré par `tools/timing/report.sh --task task-497 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 46 s | — | — | — | — |
| /develop | ok | — | 9 (1 min 52 s) | 28 (25 min 44 s) | — | dtos-mss 1B/0T, api-mail 4B/12T, client-mobile 0B/2T, client-angular 4B/14T, reprise 3 (B5, S7, S8, S9); no start marker |
| /review-code | ok | 1 min 50 s | — | — | — | — |
| /sonar | skipped | 9.2 s | 1 (1 min 03 s) | 5 (10 min 39 s) | 2 (1 min 07 s) | api-mail 1B/5T, aucun fichier analysé par Sonar depuis bbb6d978 (scenarios.yml seul) |
| /lint-angular | ok | 2 min 25 s | — | — | — | — |
| /lint-mobile | ok | 16 s | — | — | — | 0 erreur |
| /e2e | ok | 30 min 19 s | — | — | — | e2e ×5 (59 min 15 s), mobile 84 + angular 107 verts, parité verte |
| /review | ok | 1 min 36 s | 1 (2.7 s) | — | — | dtos-mss 1B/0T, PRs dtos #75, api-mail #382, mobile #136 |
| /tech-writer | ok | 3 min 58 s | — | — | — | — |
| **Total cycle** | | **41 min 22 s** | **11 (2 min 58 s)** | **33 (36 min 23 s)** | **2 (1 min 07 s)** | |

Autres commandes mesurées : lint ×3 (40 s), nuget-wait ×1 (15 s), restore ×1 (4.2 s)
