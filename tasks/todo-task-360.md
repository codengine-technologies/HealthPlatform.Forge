# todo-task-360.md — Intégration Weda : classer en un clic un document reçu dans le dossier patient Weda

**Repos**: api-mail, client-angular
**Dependencies**: done-task-357 (panneau « Dossier Weda »), done-task-359 (mots-clés IMAP)
**Epic**: E019
**Single frontend**: true — seul weda2 (client-angular) est embarqué dans Weda. Blazor et mobile
n'ont pas d'hôte Weda (raison fonctionnelle).
**Priorité**: **1** — c'est la valeur centrale de l'intégration : RG-E009-034, « visualiser et
classer en 1 clic dans le dossier patient ». Sans elle, le praticien en mode exclusif ne peut plus
classer ses courriers.

> **Origine.** Amendement 2 de l'ADR-007 du dépôt Weda (2026-10-09), décision A6 :
> - weda2 demande le classement par le pont, **avec des identifiants seulement** ;
> - le serveur Weda lit les pièces dans api-mail, puis crée l'événement et le document dans un
>   **dossier existant** ;
> - en v1, aucune identité n'est créée ni modifiée ;
> - le mot-clé IMAP `WedaClasse` mémorise le classement ;
> - **pas de corbeille** après classement.
>
> L'ADR client (`Client/Angular/docs/ADR-2026-10-09-integration-weda-mode-embarque.md`,
> amendement 2) retire le classement par octets prévu par task-356.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **client-angular** :
  - le pont v1 (`EmbeddedHostService.request()`), `WedaIntegrationService`, et
    `MSS_PATIENT_RECORD_GATEWAY` avec `WedaPatientRecordGateway` (task-356) ;
  - le panneau `mss-weda-patient-panel` dans `mail-detail` : patient Weda trouvé par INS vérifiée,
    candidats par traits, « Ouvrir le dossier » (task-357) ;
  - **types et méthodes obsolètes** depuis l'amendement 2, à retirer : `getFilingStatus`,
    `IWedaFilingEntry`, `IWedaFilingPart` (et son `content: ArrayBuffer`), le transfert
    d'`ArrayBuffer` de `fileDocuments`, `MAX_FILING_STATUS_MESSAGE_IDS`, et les types de demande
    `get-filing-status` et `file-documents`.
- **api-mail** :
  - `GET /mail/folders/{f}/emails/{uid}/download/attachment/{fileName}` sert une pièce jointe (cache
    en base, sinon IMAP), tracée (task-186) ;
  - les mots-clés `Weda` et `WedaClasse` sont exposés sur le mail (`isHandledByWeda`,
    `isFiledInWeda`) et peuvent être posés par l'API d'intégration (task-359).
- **Weda** (hors forge) : `MSSanteImportService.ImportAttachmentInPatient` montre comment créer
  l'événement et le document d'une pièce reçue (destination 1, 2 ou 3, classification, commentaire,
  date d'envoi). Il dépend toutefois de `T_MessageMSSante`, qui ne contient pas les messages
  d'api-mail.

## Objective

1. **api-mail** :
   - **`GET api/v1/integration/mails/{mailId}/attachments/{attachmentId}`** sert le contenu d'une
     pièce jointe au logiciel hôte. Les règles sont celles de la route de téléchargement
     existante : cache, sinon IMAP ; occurrences ; **traçabilité** dans le journal d'audit. La
     route est fermée si `weda_integration` est inactif ;
   - les identifiants de pièce (`attachmentId`) sont exposés là où weda2 en a besoin, s'ils ne le
     sont pas déjà dans le contenu du mail.
2. **client-angular** :
   - **« Classer dans Weda »**, bouton du panneau « Dossier Weda », rendu seulement si
     `MSS_PATIENT_RECORD_GATEWAY.available()`. Il ouvre une fenêtre de classement :
     - **le patient** : celui trouvé par INS, sinon un candidat choisi explicitement. **Aucune
       création de patient** depuis cette fenêtre (garde-fou métier) ;
     - **les pièces à classer** : cases à cocher, toutes cochées par défaut, sauf l'enveloppe
       IHE_XDM ;
     - **la destination** (Consultation, Examen, Courrier), **la classification**, **un
       commentaire** et **un post-it** facultatif. Ces listes viennent de `get-filing-context`
       (task-357).
   - « Classer » envoie la demande **`file-message`** :
     `{ mailId, attachmentIds, patientId, destination, classificationId?, comment?, postIt? }`.
     **Aucun fichier n'est téléchargé ni transféré par weda2.**
   - Badges :
     - **« Classé dans Weda »** sur le mail si `isFiledInWeda`. Un second classement demande une
       confirmation explicite : « Ce message a déjà été classé dans Weda. Classer à nouveau ? » ;
     - pour un **CR de biologie**, l'information « Intégré dans Weda (bannette HPRIM) » si
       `isHandledByWeda`, sinon « En attente d'intégration par Weda ». **Pas de bouton
       « Classer »** pour un CR de biologie seul.
   - **Nettoyage** des types et méthodes obsolètes listés plus haut, et alignement des modèles sur
     le contrat amendé de l'ADR-007.
   - **Faux hôte de test** : une page de test qui embarque weda2 dans une iframe et répond au pont
     v1 avec des données fixes (`host-capabilities`, `resolve-patient`, `get-filing-context`,
     `file-message`). Il rend le parcours testable sans Weda, en e2e et en manuel.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

- **Gestionnaire du pont `file-message`** dans `Default.aspx`, qui appelle **`POST /api/mss/filing`**,
  côté serveur Weda :
  1. vérifie que le patient appartient au cabinet de la session ;
  2. lit chaque pièce par la route d'intégration ;
  3. crée l'événement (la date d'envoi du message) et le document (destination, classification,
     commentaire), et pose le post-it ;
  4. puis `POST …/keywords {WedaClasse}`.
- **Code Weda seulement** : la logique « événement + document » est extraite de
  `MSSanteImportService` sans dépendre de `T_MessageMSSante`. **Aucun changement de schéma.**

## Definition of Done

- [ ] Build passes (0 errors) sur api-mail et client-angular ; Tests pass (0 failures, hors flaky
  préexistants documentés)
- [ ] **api-mail** — test d'intégration de bout en bout pour
  `GET /api/v1/integration/mails/{mailId}/attachments/{attachmentId}` :
  - [ ] les octets rendus sont ceux de la pièce `mail-avec-pj` du seed ;
  - [ ] la lecture apparaît dans le journal d'audit ;
  - [ ] cas d'échec : `404` `ProblemDetails` pour une pièce inconnue, et `403` si
    `weda_integration` est inactif ;
  - [ ] vu rouge (règle 1b)
- [ ] **Angular** — tests de composant, rouges d'abord :
  - [ ] le bouton et la fenêtre ne sont rendus que si `available()` ;
  - [ ] la demande `file-message` porte exactement les identifiants choisis, et **aucun
    `ArrayBuffer`** ;
  - [ ] le patient candidat doit être choisi explicitement, et aucun patient n'est présélectionné
    s'il n'y a pas de résultat par INS ;
  - [ ] le badge « Classé dans Weda » s'affiche, et la confirmation est demandée avant un second
    classement ;
  - [ ] pour un CR de biologie seul : pas de bouton « Classer », et l'information d'intégration
    s'affiche selon `isHandledByWeda` ;
  - [ ] les erreurs du pont (`forbidden`, `not-found`, `timeout`…) donnent un message clair, sans
    détail technique
- [ ] **Angular** — les types et méthodes obsolètes sont retirés. Une recherche de
  `getFilingStatus`, `IWedaFilingEntry` et `IWedaFilingPart` ne donne plus rien, et c'est consigné
  dans la revue.
- [ ] Scénario **E2E-WEDA-001**, version 1, ajouté dans `Api/Mail/e2e/scenarios.yml` :
  - titre : « Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis classer le
    document » ;
  - **il couvre aussi le parcours de task-357** (report décidé par le PO le 2026-10-10,
    `questions/answered/task-357.md`). L'attendu inclut :
    - le panneau « Dossier Weda » sous le message, avec le dossier trouvé par INS ou les
      correspondances « à vérifier » ;
    - « Ouvrir le dossier », qui envoie la demande d'ouverture à l'hôte ;
    - puis le classement ;
  - clients : `angular: requis`, `mobile: non-applicable — l'application mobile n'est pas
    embarquée dans Weda` ;
  - seed : `cr-bio-a-acquitter` (INS de test : dossier trouvé par INS), `cda-sans-ins-a-rattacher`
    (pas d'INS : candidats par traits), `mail-avec-pj` ;
  - implémenté dans client-angular avec le faux hôte de test. Le profil e2e d'api-mail active
    `weda_integration`, ce qui ajoute une ligne au profil e2e (`E2eProfile`).
- [ ] `data-testid` sur le bouton, la fenêtre, chaque case de pièce, les listes, et les boutons
  Classer et Annuler ; libellés FR en dur
- [ ] Aucune donnée de santé dans les logs : ni INS, ni nom de patient, ni contenu de pièce
- [ ] Partie Weda faite et validée (règle 11) : voir Manual Test Plan

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost`. weda2 :
   `cd Client/Angular/front && .\serve-weda2.ps1`. Weda en `https://localhost:44300`, cabinet de
   test en `weda_integration`.
2. Dans Échanges (nouvelle expérience), ouvrir un courrier avec une pièce PDF dont le patient est
   connu de Weda par INS. Le panneau affiche « Dossier Weda : … » et le bouton
   **Classer dans Weda**.
3. Classer en « Courrier », avec une classification et un commentaire. Le document apparaît dans
   le dossier du patient (Weda), à la date du message, avec la bonne destination et la bonne
   classification. Le badge « Classé dans Weda » s'affiche dans weda2.
4. Le message porte le mot-clé `WedaClasse` dans un client IMAP de test. Il est resté dans l'INBOX,
   et n'est pas parti à la corbeille.
5. **Second classement** : recliquer sur Classer. La confirmation « déjà classé » s'affiche ;
   annuler ne crée rien.
6. **Candidat par traits** : sur un document sans INS, choisir un candidat, puis classer. Le
   document est dans le dossier de ce candidat. Aucun patient n'a été créé.
7. **CR de biologie** : pas de bouton Classer. « Intégré dans Weda (bannette HPRIM) » s'affiche
   une fois task-359 passée.
8. **Faux hôte** : ouvrir la page du faux hôte de test. Le parcours fonctionne sans Weda.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : RG-E009-034 (MSS/va1.28), « visualiser et classer en 1 clic dans le
  dossier patient » : passe de 🟡 partiel à couvert pour les documents non structurés et les pièces
  jointes.
- **INS** : le classement vise un **dossier existant**. Il est trouvé par **INS vérifiée**, ou
  choisi explicitement par le praticien parmi les candidats par traits, ce qui est **une
  proposition et non un rapprochement automatique** (identito-vigilance). **Aucune identité n'est
  créée ni modifiée en v1, donc aucun appel INSi.** La création d'un patient depuis le CDA est hors
  périmètre (garde-fou « pas de création patient depuis rattachement »).
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel. Session du praticien, réutilisée
  par le serveur Weda pour lire les pièces.
- **Habilitations** : le patient doit appartenir au cabinet de la session, ce que Weda vérifie
  côté serveur. La boîte est celle du praticien (`Client-Email`).
- **Interop CI-SIS** : les pièces sont classées telles que reçues. Pas de transformation de CDA.
- **Tracé PGSSI-S** :
  - la lecture des pièces par le logiciel hôte est journalisée dans le journal d'audit d'api-mail ;
  - le classement est tracé dans Weda, comme un classement de l'ancien écran (document créé,
    auteur, date) ;
  - le mot-clé `WedaClasse` est journalisé techniquement.
- **Consentement patient** : non applicable — classement d'un document reçu dans le dossier tenu
  par le professionnel destinataire
- **Référentiels métier** : aucun (classifications propres au cabinet)
- **Hébergement HDS** : oui — les pièces transitent entre api-mail et Weda, deux services hébergés,
  en HTTPS. Elles sont stockées dans Weda comme aujourd'hui.
- **AIPD / impact RGPD** : inchangé — même finalité que le classement de l'ancien écran
