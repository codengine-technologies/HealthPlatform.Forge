# todo-task-398.md — Délégation de BAL : les BAL déléguées, visibles et utilisables dans le mobile et weda2

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-397 (lecture directe, garde de la règle 14, refus de l'API, banc de délégation)
**Epic**: E009
**Priorité**: **2** — après la task-397, la BAL déléguée est sûre côté serveur. Mais dans les
clients, elle apparaît comme un dossier racine nommé par une adresse, et plusieurs gestes
l'exploitent encore. Le pire : le panneau Weda de weda2 envoie **automatiquement** l'identité des
patients du délégant au dossier Weda du délégataire.

> **Analyse** : [Docs/audits/delegation-bal-mailiz-analyse-20261025.md](../Docs/audits/delegation-bal-mailiz-analyse-20261025.md).
> **Revue du code** : [Docs/audits/delegation-bal-revue-code-20261025.md](../Docs/audits/delegation-bal-revue-code-20261025.md),
> §3.8 (clients), §3.10 (bancs).
> **Règle 14** (CLAUDE.md) : rien d'une BAL déléguée n'est persisté chez le délégataire, y compris
> sur l'appareil ou dans le navigateur.

## Décisions actées (humain, 2026-10-25)

1. **Mobile et weda2**, avec la parité e2e.
2. **Libellé : l'adresse du délégant, seule.**
3. **Jamais de déplacement entre BAL.** Les sélecteurs et le glisser-déposer ne proposent que la BAL
   courante ; l'API le refuse (task-397).
4. **Répondre, Répondre à tous et Transférer sont masqués** sur un message délégué jusqu'à la
   task-399.
5. **Gestion seule** : pas de « à intégrer », pas d'acquittement, pas d'IA, pas d'import Weda.
6. **Impression, export PDF / EML et téléchargement de pièces jointes : permis**, comme geste
   explicite. **Aucun nom de fichier ne contient l'objet** du message.
7. **Révocation : fenêtre bornée** (task-397). Le client affiche le refus « délégation retirée ».

## Objective

Le délégataire voit les BAL qu'on lui délègue dans une section à part, avec des dossiers
reconnaissables. Il les parcourt et les gère en sachant toujours dans quelle BAL il se trouve.
Aucun geste ne fait sortir un message de la BAL du délégant, aucun geste ne l'exploite, et rien
n'est conservé sur son appareil.

## Règles

### Contrat et arborescence

- **Contrat** : un dossier porte son **propriétaire** (adresse du délégant, vide pour la propre
  BAL) et son **rôle** (réception, envoyés, brouillons, spam, corbeille, dossier personnel), posés
  par l'API (task-397, règle A).
  - Le type actuel des dossiers personnels ne change pas, pour que les logiques « première
    réception », « premiers Envoyés » et le dossier virtuel « Brouillons » ne basculent pas sur
    un dossier délégué. Le contrôle porte sur `MailController.cs:215-247`.
- **Section « Boîtes déléguées »**, sous les dossiers personnels, dans les deux clients :
  - une entrée par délégant, libellée par son **adresse**, repliable et repliée par défaut ;
  - le **cumul** des non lus affiché sur l'entrée repliée ;
  - en dessous, Réception, Envoyés, Brouillons, Spam et Corbeille, avec les icônes et libellés
    système, puis les sous-dossiers du délégant.
- **Tout le code client qui cherche ou met à jour un dossier parcourt l'arborescence.** Il cesse de
  ne regarder que la racine. Côté mobile, cela concerne :
  - `mail-state.service.ts:137, 360` (compteurs) ;
  - `mail-detail.component.ts:345, 398` (corbeille, restauration) ;
  - `mail-list.component.ts:198`.
- **Le rôle du contrat remplace les détections par nom**, aux quatre endroits :
  - mobile `mail-detail.component.ts:747` ;
  - weda2 `read-receipt.util.ts:18`, `mail-detail.component.ts:1136` (garde d'« Annuler et
    remplacer »), `mail-header.component.ts:450`.

### Contexte et gestes

- **Contexte visible** :
  - le titre de la liste indique `<adresse> — <dossier>` ;
  - le détail d'un message délégué porte le bandeau « Boîte de `<adresse>` (délégation) ».
- **Gestes sur les dossiers délégués** :
  - les dossiers système n'ont ni Renommer ni Supprimer ;
  - **Nouveau sous-dossier** reste proposé sur la réception déléguée, et c'est le seul moyen d'en
    créer à sa racine ;
  - après la suppression d'un sous-dossier délégué, on revient à la **réception déléguée**, et non
    à sa propre réception (weda2 `mail-folder-list.component.ts:220`).
- **Gestes sur un message délégué** :
  - permis : lire, marquer lu ou non lu, déplacer **dans la même BAL**, supprimer vers la corbeille
    du délégant ; imprimer, exporter, télécharger une pièce jointe, sans objet dans le nom de
    fichier (weda2 `mail-detail.component.ts:1494`) ;
  - **masqués** :
    - Répondre, Répondre à tous, Transférer, jusqu'à la task-399 ;
    - la proposition d'accusé de lecture ;
    - l'invitation « à intégrer » et le panneau de rattachement manuel ;
    - l'acquittement de biologie ;
    - les bandeaux de doublon, de version et de suppression ;
    - Synthèse IA, « Poser une question à l'IA », conversation IA ;
    - l'éditeur d'étiquettes ;
    - « Annuler et remplacer » (weda2) ;
    - dans weda2, le **panneau « Dossier Weda »** et **« Importer dans Weda »**, qui ne sont même
      pas instanciés : aucun appel `resolvePatient` ni `fileDocuments`
      (`weda-patient-panel.component.ts:133`, `weda-import.component.ts`) ;
  - le contenu, le document décodé, la bannière patient et la biologie restent affichés, en lecture.
- **Gestes de liste dans une BAL déléguée** :
  - « Analyser avec l'IA » en lot : masqué ;
  - puce « bio à acquitter » : non appelée ;
  - **mode liste forcé**, sans fils de conversation : un fil pourrait ouvrir la copie du délégataire
    d'un même `Message-ID`.
- **Corbeille déléguée** :
  - **Restaurer**, vers la réception du délégant ;
  - **Supprimer définitivement**.

  Dans weda2, ce sont des **interfaces nouvelles** : il n'en existe aucune aujourd'hui, même pour
  la propre corbeille.
- **Déplacer vers…** : tous les niveaux de dossiers de la **BAL courante**. Ce correctif vaut aussi
  pour la propre BAL.
  - Le dossier virtuel « Brouillons » n'est plus proposé comme destination ; il l'est aujourd'hui
    sur mobile.
- **Glisser-déposer** (weda2, `mail-drop-rules.util.ts`) : même BAL **et** règles de rôle. Par
  exemple, les Envoyés délégués ne vont que vers la Corbeille déléguée.

### Appels que les clients ne font plus pour un dossier délégué

- Pas d'**enrichissement** (`enrichEmailsSync` : mobile `inbox.page.ts:503`, weda2
  `mail-list.component.ts:265, 281`, `mss-mail.component.ts:528`).
- Pas de **flux SSE** par dossier (`?folder=shared/…` : mobile `inbox.page.ts:427`, weda2
  `mail-events-stream.service.ts`).
- Pas de **recherche** : un message dit qu'elle n'est pas disponible.
- Aucun **journal console** du chemin (weda2 `mail-events-stream.service.ts:168`).
- Toute **notification** reçue pour un dossier `shared/` est écartée (weda2
  `notification-dispatcher.component.ts:121`).

### Règle 14 côté client

- Aucune donnée d'une BAL déléguée dans un stockage du navigateur ou de l'appareil (local,
  session, IndexedDB, préférences, fichiers), hors fichiers que l'utilisateur choisit d'enregistrer
  (décision 6).
- **Déconnexion** : purge de tous les états liés à la BAL. Côté mobile, la déconnexion n'appelle
  pas aujourd'hui la purge de `MailboxSessionService`, et laisse en mémoire `MailStateService` et
  `DocumentContentService` (HTML des CDA décodés) (`logout.service.ts:58-66`).
- **Passage hors ligne** dans une BAL déléguée : purge de son état et retour à la propre réception.
  Hors ligne, la section n'apparaît pas.
- **Dossier d'ouverture** : jamais proposé sous `shared/`. Une valeur `shared/…` déjà enregistrée
  est ignorée à la lecture.

### Révocation

- Le refus de `type` « délégation retirée » (task-397, règle H) affiche « Cette boîte ne vous est
  plus déléguée » et ramène à la propre réception.
- Une racine déléguée disparue de la liste, ou passée en `\Noselect`, a le même effet.
- Les messages génériques « dossier supprimé » et « message introuvable » ne s'appliquent pas à ce
  cas.

## Definition of Done

- [ ] `dtos-mss` : propriétaire et rôle dans le contrat de dossier. Paquet publié, consommateurs .NET
      mis à jour, types TypeScript des deux clients alignés.
- [ ] Test d'intégration : la liste des dossiers renvoie, pour `shared/<A>`, le propriétaire A et
      les bons rôles. Les dossiers personnels gardent leur type et propriétaire vide. Le dossier
      virtuel « Brouillons » reste unique et à sa place. Lu dans la réponse réelle, vu rouge
      (règle 1b).
- [ ] Test d'intégration « rien de persisté » (règle 14) rejoué sur toute route nouvelle ou
      modifiée.
- [ ] Tests de composants, sur mobile et weda2 :
      - section, libellés système, cumul des non lus ;
      - bandeau et titre ;
      - menus des dossiers système ; Nouveau sous-dossier sur la réception déléguée ;
      - **chaque geste masqué** de la liste ci-dessus, panneau Weda et import compris, sans appel
        `resolvePatient` ;
      - Restaurer et Supprimer définitivement ;
      - sélecteur limité à la BAL courante, tous niveaux, sans « Brouillons » virtuel ;
      - glisser-déposer par BAL et par rôle ;
      - mode liste forcé ;
      - aucun appel d'enrichissement, de SSE ni de recherche sur `shared/` ;
      - nom de fichier d'export sans objet.
- [ ] Tests unitaires mobile : recherches et mises à jour de dossiers sur l'arborescence ;
      déconnexion qui purge tous les états liés à la BAL, `DocumentContentService` compris ; passage
      hors ligne.
- [ ] Contrôle outillé : aucun accès à un stockage du navigateur ou de l'appareil avec une donnée de
      BAL déléguée, dans les deux clients, consigné dans le `## Develop log`.
- [ ] **Banc e2e** :
      - le fragment Dovecot de délégation de task-397 est monté par le banc e2e ;
      - la sous-commande `delegation --grant / --revoke` (`SETACL` / `DELETEACL` en IMAP) est
        ajoutée à `tests/mss.mail.e2e` ;
      - `message` et `folder` acceptent une option `--mailbox` pour la délégante ;
      - une donnée de seed « bal-deleguee » est déclarée au plan de seed, et contrôlée par
        `ScenarioCatalogTests` ;
      - `E2eReset` couvre la BAL de la délégante et ses ACL.
- [ ] Scénarios ajoutés dans `Api/Mail/e2e/scenarios.yml`, et implémentés sur mobile et angular :
      - **E2E-DELEG-001** : voir la BAL déléguée dans sa section, ouvrir un compte rendu, lire le
        document décodé ;
      - **E2E-DELEG-002** : supprimer un message délégué → il est dans la corbeille de la BAL
        déléguée ; le restaurer ;
      - **E2E-DELEG-003** :
        - les dossiers système délégués n'ont ni Renommer ni Supprimer ;
        - un message délégué n'a ni Répondre, ni Transférer, ni IA, ni étiquettes ;
        - dans weda2, ni « Dossier Weda » ni « Importer dans Weda » ;
        - « Déplacer vers… » ne propose que la BAL déléguée ;
      - **E2E-DELEG-004** : la délégation est retirée pendant la consultation (`--revoke`) →
        message « délégation retirée », puis retour à la propre réception.
- [ ] Build et tests verts sur les quatre dépôts ; `/e2e` vert, avec parité verte.

## Manual Test Plan

Comptes de formation : Cyril, délégataire de Virginie. Lancer l'AppHost, puis le mobile
(`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.

1. **Section.** La section « Boîtes déléguées » contient la boîte de
   `virginie.medecinrpps0062267@medecin.formation.mssante.fr`, repliée, avec son cumul de non lus.
   La déplier : Réception, Envoyés, Brouillons, Spam, Corbeille, puis `Demo`.
2. **Message délégué.**
   - Ouvrir un message de la Réception déléguée : bandeau « (délégation) ».
   - Aucun de ces gestes : Répondre, Transférer, Synthèse IA, IA, étiquettes, Annuler et
     remplacer.
   - weda2 : ni « Dossier Weda » ni « Importer dans Weda » ; le dossier Weda de Cyril n'a reçu
     aucune recherche de patient.
3. **Lecture et export.** Un compte rendu de biologie est décodé, sans « à intégrer » ni
   acquittement. Exporter en PDF : le fichier ne porte pas l'objet dans son nom.
4. **Déplacer vers…** : seuls les dossiers de la boîte de Virginie, sous-dossiers compris. Le
   glisser vers sa propre réception est refusé.
5. **Corbeille.** Supprimer un message : il est dans la Corbeille de la boîte de Virginie.
   Restaurer : il revient dans sa Réception. Supprimer définitivement depuis la Corbeille : il
   disparaît.
6. **Dossiers.** Menu des Envoyés de Virginie : ni Renommer ni Supprimer. Créer un sous-dossier
   sous sa Réception, puis le supprimer : retour à la Réception déléguée.
7. **Appels.** Dans la boîte déléguée, la recherche indique qu'elle n'est pas disponible, et aucune
   notification n'arrive. Dans Seq, aucune requête d'enrichissement ni flux SSE sur `shared/…`.
8. **Hors ligne.** Couper le réseau en étant dans la boîte déléguée : retour à la propre réception,
   section absente.
9. **Déconnexion** (mobile) : se reconnecter avec un autre compte ; aucun contenu de la boîte
   déléguée n'apparaît.
10. **Révocation.** Virginie retire la délégation dans le webmail Mailiz pendant que Cyril est dans
    sa boîte. Au plus 5 minutes après : « Cette boîte ne vous est plus déléguée », puis retour à la
    propre réception.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable. Le mode opératoire Mailiz est suivi, et le choix de la
  BAL est rendu visible.
- **INS** : non applicable. Lecture seule, et **aucune** recherche de patient envoyée au dossier Weda
  pour un message délégué.
- **Authentification PS** : inchangée — PSC / e-CPS du délégataire
- **Habilitations** : droits tenus par les ACL Mailiz. L'interface retire les gestes réservés au
  délégant ou reportés à la task-399, ainsi que toute exploitation : IA, étiquettes, Weda,
  rattachement.
- **Interop CI-SIS** : non applicable — affichage des documents décodés par task-397
- **Tracé PGSSI-S** : inchangé — audit réduit de task-397, imputabilité en task-400
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — rien d'une BAL déléguée n'est stocké, ni sur l'appareil ni dans
  le navigateur
- **AIPD / impact RGPD** : couvert par la mise à jour ouverte par task-397. Y ajouter les exports à
  l'initiative de l'utilisateur.

## Notes de cadrage

- **Constats et lignes** : revue, §3.8 et §3.10.
- **Hors périmètre** :
  - envoi « de la part de », brouillons délégués, accusés de lecture : task-399 ;
  - traçabilité : task-400 ;
  - gestion des délégations : webmail Mailiz seul.
