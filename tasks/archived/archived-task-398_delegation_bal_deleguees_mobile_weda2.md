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
8. **La BAL principale et les BAL déléguées se distinguent au premier coup d'œil**, dans les deux
   clients. C'est une exigence primordiale de la task :
   - les BAL déléguées sont **toujours placées sous tous les dossiers de la BAL principale** ;
   - elles sont **repliées** à chaque arrivée ;
   - elles portent une **couleur propre**, différente de celle de la BAL principale.
9. **weda2 : panneau des dossiers plus large et redimensionnable.** Un séparateur se tire à la
   souris pour agrandir ou réduire le panneau, et une largeur minimale l'empêche d'être écrasé.

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
- **Section « Boîtes déléguées »**, dans les deux clients :
  - une entrée par délégant, libellée par son **adresse**, repliable ;
  - le **cumul** des non lus affiché sur l'entrée repliée ;
  - en dessous, Réception, Envoyés, Brouillons, Spam et Corbeille, avec les icônes et libellés
    système, puis les sous-dossiers du délégant.
- **Position : toujours en dernier** (décision 8). La section se place après **tous** les dossiers
  de la BAL principale, sous-dossiers compris, quel que soit l'ordre renvoyé par l'API.
  - L'ordre est appliqué par le client, et tient après un rafraîchissement de la liste, la création,
    le renommage ou la suppression d'un dossier personnel, et le retour en ligne.
  - Les délégants sont triés par adresse, pour un ordre stable.
- **Repliée par défaut** (décision 8). Chaque entrée déléguée est repliée au chargement de la
  messagerie et après une reconnexion.
  - L'utilisateur la déplie d'un clic ; cet état est tenu **en mémoire** pour la session, et
    n'est **jamais persisté**. Une clé de stockage porterait l'adresse du délégant (règle 14).
  - Ouvrir un dossier délégué par un autre chemin, comme un lien ou un retour arrière, déplie son
    entrée.
- **Couleur propre** (décision 8). Toutes les BAL déléguées partagent une **couleur d'accent**
  distincte de la BAL principale.
  - Elle s'applique à l'en-tête de la section, à l'entrée du délégant, aux icônes et au filet
    latéral de ses dossiers, ainsi qu'au bandeau « (délégation) » et au titre de liste. On garde
    ainsi le repère une fois dans la boîte.
  - La couleur est un **jeton de thème** propre à chaque client : variable CSS dans weda2, variable
    Ionic sur mobile. Elle n'est jamais codée en dur dans les composants, et le même rendu vaut en
    thème clair et sombre.
  - La couleur n'est **jamais le seul repère**. Le libellé de section, l'adresse et le bandeau
    portent la même information, et le contraste texte / fond respecte WCAG AA.
  - La sélection d'un dossier délégué reste lisible : elle ne doit pas se confondre avec la couleur
    de délégation.
- **Tout le code client qui cherche ou met à jour un dossier parcourt l'arborescence.** Il cesse de
  ne regarder que la racine. Côté mobile, cela concerne :
  - `mail-state.service.ts:137, 360` (compteurs) ;
  - `mail-detail.component.ts:345, 398` (corbeille, restauration) ;
  - `mail-list.component.ts:198`.
- **Le rôle du contrat remplace les détections par nom**, aux quatre endroits :
  - mobile `mail-detail.component.ts:747` ;
  - weda2 `read-receipt.util.ts:18`, `mail-detail.component.ts:1136` (garde d'« Annuler et
    remplacer »), `mail-header.component.ts:450`.

### Panneau des dossiers redimensionnable (weda2)

Aujourd'hui, `.mail-folder-panel` est fixé à `width: 240px; min-width: 200px`
(`libs/mss/src/features/mail/mss-mail.component.scss:63-65`). C'est trop étroit, et l'adresse
d'un délégant ne tient pas.

- **Largeur par défaut : 300 px.**
- **Largeur minimale : 240 px.** Aucun geste ne descend en dessous, ni le glisser, ni le clavier,
  ni une valeur enregistrée.
- **Largeur maximale : 480 px**, réduite si besoin pour que la liste des messages garde son
  `min-width` de 300 px.
- **Séparateur** entre le panneau des dossiers et la liste :
  - il se tire à la souris (événements pointeur), avec un curseur `col-resize` et une poignée
    visible au survol ;
  - la largeur suit la souris pendant le glisser, bornée au minimum et au maximum ;
  - un **double-clic** rend la largeur par défaut ;
  - accessible au clavier : `role="separator"`, `aria-orientation="vertical"`,
    `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, focusable. Les flèches gauche et droite
    changent la largeur de 16 px, Début et Fin vont au minimum et au maximum ;
  - `data-testid="mail-folder-splitter"`.
- **Mémorisation** : la largeur choisie est gardée dans `localStorage`, car elle ne contient aucune
  donnée de BAL. La règle 14 ne s'y oppose donc pas.
  - Chaque lecture et chaque écriture sont protégées par un `try/catch`.
  - Une valeur absente, illisible ou hors bornes rend la largeur par défaut, ou est ramenée dans les
    bornes.
- **Redimensionnement de la fenêtre** : la largeur est ramenée dans les bornes.
- **Libellés longs** : une adresse ou un nom de dossier qui ne tient pas est tronqué par une
  ellipse, avec l'intitulé complet en infobulle.
- Le séparateur est écrit dans le module MSS, sans nouvelle dépendance. `@angular/cdk` est déjà
  présent si besoin.

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
      - **section toujours après tous les dossiers de la BAL principale**, y compris quand l'API
        renvoie les dossiers délégués en tête, et après la création d'un dossier personnel ;
      - **entrées déléguées repliées au chargement**, dépliées au clic, sans aucune écriture
        dans un stockage du navigateur ou de l'appareil ;
      - **classe ou jeton de couleur de délégation** posé sur la section, les dossiers délégués,
        le bandeau et le titre de liste, et absent des dossiers de la BAL principale ;
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
- [ ] Tests de composant weda2 du **séparateur** :
      - largeur par défaut de 300 px ;
      - glisser vers la droite et vers la gauche ;
      - butée au minimum de 240 px et au maximum ;
      - flèches, Début, Fin et attributs ARIA ;
      - double-clic qui rend la largeur par défaut ;
      - largeur relue depuis `localStorage`, et valeur absente, illisible, hors bornes, ou
        stockage qui lève une exception.
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
      - **E2E-DELEG-001** : voir la BAL déléguée dans sa section, **repliée et placée sous le
        dernier dossier de la BAL principale**, la déplier, ouvrir un compte rendu, lire le
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
   - Elle est **sous le dernier dossier de Cyril**. Créer un dossier personnel : la section reste
     en dessous.
   - Sa **couleur** la distingue de la boîte de Cyril. Le repère se retrouve dans le bandeau et
     dans le titre de la liste, et reste lisible en thème sombre.
   - Recharger la page (weda2) ou relancer l'app (mobile) : la boîte est de nouveau **repliée**.
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
11. **Panneau des dossiers** (weda2) :
    - il s'ouvre à 300 px, et l'adresse de Virginie se lit, ou porte une ellipse et une infobulle ;
    - tirer le séparateur à droite : le panneau s'élargit, sans réduire la liste sous 300 px ;
    - tirer à gauche jusqu'au bout : il s'arrête à 240 px ;
    - recharger : la largeur choisie est conservée ; double-cliquer sur le séparateur : retour à
      300 px ;
    - au clavier, en tabulant jusqu'au séparateur, les flèches changent la largeur.

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

## Branches
- `api-mail` (pushed) : feat/task-398-delegation-bal-deleguees-mobile-weda2 — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-398-delegation-bal-deleguees-mobile-weda2
- `client-mobile` (pushed) : feat/task-398-delegation-bal-deleguees-mobile-weda2 — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-398-delegation-bal-deleguees-mobile-weda2
- `dtos-mss` (lazy) : aucune branche au /start — créée par /develop depuis `origin/develop` au premier contrat touché (CLAUDE.md, « Repo à branche PARESSEUSE »)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (`feature/nova-mss-weda-integration` au /start, 2026-10-25) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-398 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 34 s | — | — | — | — |
| /develop | skipped | 1 min 38 s | 12 (2 min 00 s) | 26 (12 min 50 s) | — | dtos-mss 1B/0T, api-mail 4B/16T, client-mobile 3B/8T, client-angular 4B/2T, aucun changement : requalification API renvoyée à une task de suivi |
| /sonar | ok | 7 min 58 s | 4 (1 min 23 s) | 17 (19 min 50 s) | 6 (2 min 01 s) | 1 itération(s), api-mail 4B/17T, re-analyse après tranche 9 : QG OK, 0 issue |
| /lint-angular | ok | 0.4 s | — | — | — | eslint des fichiers de la tranche 9 : 0 erreur, 0 warning de la task (vérifié en /develop) |
| /lint-mobile | ok | 6.9 s | — | — | — | lint propre après tranche 9 |
| /e2e | ok | 9 min 30 s | — | — | — | e2e ×10 (1 h 12 min), rejeu après tranche 9 : 2 voies vertes, porte 0, 2 flaky |
| /review | ok | 6 min 29 s | 3 (10 s) | 2 (49 s) | — | client-mobile 1B/1T, client-angular 1B/1T, dtos-mss 1B/0T, 2e passe APPROVED, 3 PR ouvertes |
| /tech-writer | ok | 1 min 04 s | — | — | — | — |
| **Total cycle** | | **27 min 24 s** | **19 (3 min 34 s)** | **45 (33 min 30 s)** | **6 (2 min 01 s)** | |

Autres commandes mesurées : lint ×5 (43 s), nuget-wait ×1 (18 s), restore ×2 (1 min 17 s)

## Develop log

> Journal de progression (mis à jour à chaque tranche commitée — point de reprise en cas de compaction).

**Plan des tranches** :

| # | Tranche | Dépôt | État |
|---|---|---|---|
| 1 | Contrat : `FolderRole` + `Owner` / `Role` sur `FolderDto`, publication NuGet, bump api-mail | dtos-mss, api-mail | ✅ dtos `4e642d5a` → **536.0.0** (run 536) ; bump api-mail `a54fd93b` |
| 2 | API : propriétaire et rôle posés sur toute la liste des dossiers (propre, déléguée, étiquettes, Brouillons virtuel) + unitaires + test d'intégration vu rouge | api-mail | ✅ `e28c7de4` — 18 unitaires, 1 bout en bout rouge (propriétaire vide) puis par mutation |
| 3 | Banc e2e : fragment de délégation monté par l'AppHost e2e, `delegation --grant/--revoke`, `--mailbox` sur `message` et `folder`, seed `bal-deleguee`, `E2eReset`, scénarios E2E-DELEG-001..004 au catalogue | api-mail | ✅ `18ec2d34` — 111 tests e2e de l'outillage verts ; seed réel joué par `/e2e` |
| 4 | Mobile : section « Boîtes déléguées », arborescence, gestes masqués, corbeille, sélecteur, purge déconnexion / hors ligne, révocation + unitaires | client-mobile | ✅ `a0b1532` — 1 326 tests verts (dont 38 nouveaux), 5 mutations unitaires rouges |
| 5 | Mobile : scénarios e2e E2E-DELEG-001..004 | client-mobile | ✅ `9997542` — 4 verts sur le banc réel, 4 mutations rouges sur l'assertion visée |
| 6 | weda2 : section, couleur, gestes masqués (dont panneau Weda / import), Restaurer / Supprimer définitivement, glisser-déposer, séparateur redimensionnable + unitaires | client-angular | ✅ non commité (code-only, branche `feature/nova-mss-weda-integration`) — `mss-lib` 1 326 tests verts, build `weda2` vert |
| 7 | weda2 : scénarios e2e E2E-DELEG-001..004 | client-angular | ✅ non commité (code-only) — 4 verts sur le banc réel, rejoués deux fois ; 4 mutations rouges sur l'assertion visée, témoins verts |
| 8 | Passe qualité §Q, contrôle outillé « aucun stockage », DoD | tous | ✅ api-mail `bf97c7d3`, mobile `4f93c41` + `c40d504`, weda2 non commité ; poussés : api-mail (`47a94d4f..bf97c7d3`), mobile (`6d890c2..c40d504`) |

| 9 | Retours de `/review` (CHANGES REQUESTED, 3 revues) : révocation sur liste périmée, détail, hors ligne, session expirée, IA, seeds, test du cache | tous sauf dtos | ✅ api-mail `a120684f`, mobile `c44b22d`, weda2 non commité ; poussés |

**Suite complète api-mail avant le push** : 6 986 tests verts, dont domaine 264, infrastructure 701, api 1 346, application 3 673 et intégration 1 002. Trois tests rouges, tous de la famille « du jour » : `FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync` et les deux `GetFolder*TodayAsync` d'`ImapFolderServiceIntegrationTests`. La suite a tourné entre 00:00 et 02:00, fenêtre connue où le `SINCE` en UTC ne trouve pas le message du jour local. Ils ne touchent pas la task et sont à rejouer de jour.

**Écart assumé, à valider au HAG — enrichissement et SSE sur `shared/`.** La task interdit aux
clients `enrichEmailsSync` et le flux SSE sur un dossier délégué (§ « Appels que les clients ne
font plus », DoD « aucun appel d'enrichissement, de SSE… »). Ce texte a été écrit le 2026-10-25 à
13:13 ; la **décision 14 de la task-397** (même jour, 17:13, « après essai ») l'a rendu caduc : les
en-têtes délégués porteurs d'un CDA sont `Pending` jusqu'à `enrich/sync`, qui décode en mémoire et
émet `EmailsEnriched` par SSE (diffusion, rien d'écrit). Sans ces deux appels, ces en-têtes
resteraient `Pending` indéfiniment. La forge suit donc la décision 14 : **enrichissement et SSE
conservés** sur les dossiers délégués (rien n'est persisté côté serveur, prouvé par task-397) ;
la **recherche** reste coupée, et les **notifications système** de nouveau message restent
écartées pour `shared/`.

**Constats et preuves (au fil des tranches)**

- **Tranche 2 — test d'intégration** `DelegationEndToEndTests.TheFolderList_GivesEveryFolderItsOwnerAndRole_WithoutChangingTypes_NorTheVirtualDrafts` (vraie pile HTTP, Dovecot en délégation, base du délégataire) : rôles et propriétaire de `shared/<A>`, `Sent`, `Drafts`, `Trash`, `Junk`, `Demo`, `Demo/Biologie2026` ; type `Custom` inchangé ; BAL propre à propriétaire vide ; un seul « Brouillons » (le virtuel, juste après Envoyés) ; aucune ligne de la base du délégataire ne porte `shared/` ni `Biologie2026`.
  - Rouge avant branchement : `Expected "loadtest-4023@loadtest.local", Actual ""`.
  - Mutation M1 (rôle délégué forcé à `Personal`) : rouge `Expected Inbox, Actual Personal` ; restauré par copie + `touch`, vert.
- **Tranche 3 — banc** : `!include_try /etc/dovecot/fragments/*.conf` vérifié sur l'image `dovecot/dovecot:2.3.21` (`doveconf -n`) : sans fragment, configuration inchangée et sans erreur ; avec `delegation.conf` monté, `acl`, `imap_acl` et l'espace `shared` actifs.
- **Tranche 5 — révocation sur le banc réel** : après `--revoke`, l'API rend d'abord `FOLDER_NOT_FOUND` (et non `DELEGATION_WITHDRAWN`) sur un sous-dossier délégué, parce que la session IMAP mutualisée garde un instant l'ancienne vue. Le client relit alors la liste des dossiers (`getFolders(true)`) : racine déléguée absente + dossier délégué introuvable ⇒ « Cette boîte ne vous est plus déléguée ». Même traitement sur weda2 (`onDelegatedFolderGone`).
- **Tranche 7 — weda2** : le premier passage était rouge sur les quatre parcours, le titre de liste affichant « propriétaire — propriétaire ». La réponse de `GET /folders/{path}` ne porte pas le rôle et remplaçait le dossier cliqué. Correctif : `selectedFolder` garde `owner` et `role` du dossier cliqué.
- **Parcours rejouables (mobile et weda2)** : les témoins des mutations étaient rouges au deuxième passage. DELEG-001 avait lu le compte rendu, et la mutation NA2, qui refuse la restauration, avait laissé le courrier dans la corbeille déléguée. Chaque parcours pose désormais son état de départ par l'API (`resetDelegatedMailbox` : courrier remis dans la réception s'il est resté à la corbeille, compte rendu remis non lu), et DELEG-001 rend le compte rendu non lu à la fin.
- **Mutations e2e weda2** (mutant → assertion rouge ; témoin restauré → vert) :
  | # | Mutation | Parcours | Assertion rouge |
  |---|---|---|---|
  | NA1 | `isDelegationExpanded` toujours vrai | DELEG-001 | « repliée à l'arrivée » (`aria-expanded` `true`) |
  | NA2 | restauration vers `INBOX` propre | DELEG-002 | « la restauration est acceptée par le serveur » |
  | NA3 | gestes Weda non gardés | DELEG-003 | « pas de « Dossier Weda » » |
  | NA4 | révocation mappée sur `FOLDER_NOT_FOUND` | DELEG-004 | « Cette boîte ne vous est plus déléguée » (reçu : « Ce dossier n'existe plus… ») |

### Passe qualité §Q (`/simplify`, 4 relectures : réutilisation, simplification, efficacité, altitude)

| Dépôt | Appliqué | Re-validation |
|---|---|---|
| api-mail | `DelegationImap` (banc d'intégration, task-397) délègue à `E2eDelegation.GrantAsync` / `RevokeAsync` / `AllFoldersAsync` : un seul protocole SETACL/DELETEACL et un seul jeu de droits (`E2eSeedPlan.DelegateRights`) ; `E2eOptions.Switches` privé ; `--mailbox` lu par `Last()` au lieu d'un vide reconverti en `null` | build vert ; 21 tests de délégation, 111 de l'outillage e2e, puis suite complète avant push |
| client-mobile | `folderOwner()` remplace cinq copies ; `isDelegationWithdrawn` rejoint `http-error.util` (`isNotFoundWithCode`) ; `updateFolder` en un seul parcours ; `resetForMailboxSwitch` s'appuie sur `leaveDelegatedMailbox`, double purge retirée de `onFolderGone`, `openInbox()` factorise trois ouvertures ; une table rôle → icône ; e2e : `mailsIn()` partagé | build vert, 1 326 tests verts — `c40d504` |
| client-angular | `folderOwner()` ; `isDelegationWithdrawn` rejoint `problem-details.utils` ; `state.leaveDelegatedMailbox()` remplace deux purges recopiées ; repli mort retiré de `onFolderGone` ; `sidePanelSections` sans branche recopiée ; e2e : `mailsIn()` partagé (`moveBackIfIn` : 2 requêtes au lieu de 4) | `mss-lib` 121 fichiers de test verts, build `weda2` vert, ESLint 0 erreur — non commité (code-only) |

**Écartés, avec la raison :**
- **`GET /folders/{path}` annoté par `FolderOwnership`** (altitude) : essayé, test d'intégration vu rouge puis vert sur le dossier délégué. Mais cette route ne lit pas le SPECIAL-USE : un dossier **propre** y sort en `Custom`, donc en rôle `Personal`. Les clients auraient gardé leur recollage pour la boîte propre. Retiré : la compensation côté client reste nécessaire tant que le fournisseur n'expose pas le type sur un dossier seul.
- **Requalification de la révocation côté API** (altitude) : dans la fenêtre où la session IMAP mutualisée sert encore l'ancienne vue, l'API rend `FOLDER_NOT_FOUND`, et les clients requalifient en relisant la liste. Faire ce travail dans `DelegatedMailboxPolicyFilter` changerait le comportement de l'API sur toutes les routes déléguées : c'est hors d'une passe qualité. **Suite proposée** : une task dédiée. Limite connue d'ici là : sur le détail d'un message, un 404 dans cette fenêtre affiche « message supprimé » au lieu de « plus déléguée ».
- **Politique unique des gestes** (`mailCapabilities(mail)`, altitude) : facultatif, à faire si une autre fonction s'ajoute.
- **Triple borne du séparateur** (simplification) : défense de l'entrée `max` d'un composant réutilisable, couverte par ses tests ; conservée.
- **`ResizeObserver`** au lieu de `window:resize` (efficacité) : coût mesuré négligeable.

### Contrôle outillé « aucun stockage » (règle 14 côté client)

- **Tests** : espions sur les écritures de stockage, qui doivent rester à zéro appel pendant les gestes délégués.
  - Mobile : `localStorage.setItem` et `sessionStorage.setItem` dans `mail-folder-list.delegation.spec.ts` (déplier, replier, cumul des non-lus) ; `localStorage.setItem` dans `mail-state.delegation.spec.ts`.
  - weda2 : `Storage.prototype.setItem` dans `mail-folder-list.delegation.spec.ts` et `mss-mail.component.delegation.spec.ts` (ouvrir un dossier délégué).
- **Code ajouté** : un balayage du diff de production (`setItem`, `Preferences.set`, `indexedDB`, `caches.open`) ne trouve qu'une écriture, la largeur du panneau des dossiers de weda2 (`mss.mail.folderPanelWidth`). C'est un nombre de pixels, sans aucune donnée de BAL.
- **Déconnexion mobile** : `MAILBOX_SCOPED_STATES` purge l'état des BAL, `DocumentContentService` compris ; c'est couvert par le test de `logout.service`.

### DoD — auto-contrôle

| Critère | État |
|---|---|
| Contrat `Owner` / `Role`, NuGet 536.0.0, consommateurs .NET, types TS des deux clients | ✅ |
| Intégration : liste des dossiers (propriétaire, rôles, types, Brouillons virtuel), vue rouge | ✅ tranche 2 |
| « Rien de persisté » sur la route modifiée | ✅ dans le même test (aucune ligne `shared/` ni `Biologie2026` dans la base du délégataire) |
| Tests de composants mobile et weda2 (section, repli, couleur, bandeau, menus, gestes masqués, Restaurer/Supprimer définitivement, sélecteur, glisser-déposer, mode liste, appels, nom d'export) | ✅ tranches 4 et 6 ; l'enrichissement et le SSE restent actifs (écart ci-dessus) |
| Séparateur weda2 (8 tests) | ✅ |
| Unitaires mobile : arborescence, purge à la déconnexion, hors ligne | ✅ |
| Contrôle outillé « aucun stockage » | ✅ ci-dessus |
| Banc e2e (fragment, `delegation`, `--mailbox`, seed `bal-deleguee`, `E2eReset`) | ✅ tranche 3 |
| E2E-DELEG-001..004 au catalogue, dans les deux clients | ✅ tranches 5 et 7, mutations rouges |
| Build et tests verts sur les quatre dépôts ; `/e2e` vert | build et tests ✅ ; `/e2e` : étape suivante |

### Tranche 9 — retours de `/review` (2026-10-26)

`/review` a été rendue par trois relectures indépendantes, une par dépôt, avec un verdict **CHANGES REQUESTED** et un même défaut bloquant sur les deux clients.

**Le défaut bloquant : la révocation dépendait d'une liste relue, que le serveur peut servir périmée.** Pendant la fenêtre où la session IMAP mutualisée d'api-mail garde l'ancienne vue, `getFolders(true)` porte encore la BAL retirée. Trois effets :
- l'entrée reste dans la section après l'avis « plus déléguée » : c'était la cause du flaky E2E-DELEG-004 mobile ;
- l'avis générique « dossier supprimé » peut s'afficher ;
- une réception déléguée introuvable se rouvre en boucle, à deux requêtes par tour.

**Correctif (mobile et weda2)** :
- `withdrawDelegation(owner)` retire la BAL de la liste en mémoire ;
- `setFolders` la tient absente des listes suivantes et lève le retrait dès qu'une liste arrive sans elle, ce qui laisse une nouvelle délégation se revoir ;
- le refus `DELEGATION_WITHDRAWN` s'applique sans relecture ;
- une réception déléguée elle-même introuvable vaut retrait.

Ce mécanisme ne garde rien sur le disque (règle 14) : un ensemble d'adresses en mémoire, vidé au changement de boîte.

**Preuves rouges avant le correctif** :
- mobile : 9 assertions rouges, dont « Expected 4 to be 1 » (la boucle) et l'avis générique au lieu de « plus déléguée » ;
- weda2 : 6 tests rouges, dont « expected 4 to be 1 ».

Tous ces tests sont verts après le correctif.

**Corrections associées** :
- **Mobile** :
  - la page de détail applique le retrait vu pendant la lecture (chargement et rafraîchissement du contenu) et quitte un message délégué au passage hors ligne ;
  - une session expirée purge la boîte comme une déconnexion (`MailboxSessionService.clear()`) ;
  - les Envoyés sont reconnus par leur chemin en lien profond ;
  - la recherche ne porte jamais sur une BAL déléguée, quel que soit le chemin d'arrivée.
- **weda2** :
  - le détail remonte `DELEGATION_WITHDRAWN` (`MailEventService.delegationWithdrawn$`) au lieu de « contenu indisponible » ;
  - l'assistant IA se referme à l'entrée dans une BAL déléguée ;
  - les entrées dépliées se replient à toute coupure ;
  - tests ajoutés : notification `shared/` écartée, chemin masqué dans la console.
- **api-mail** :
  - le test d'intégration relit le propriétaire et le rôle aussi sur la liste **servie par le cache**, et il a été vu rouge par mutation (annotation limitée au `refresh` : `Expected "loadtest-4023@…", Actual ""`) ;
  - `--revoke` ne prend plus qu'un refus `NO` pour un retrait relu ;
  - seeds complets de E2E-DELEG-001..004 ;
  - documentation : seule la liste porte `Owner` et `Role` ; la relecture IMAP du banc ; `--mailbox`.

**Prévention** :
- `conventions/e2e.md` : entrée `retrait-sur-liste-perimee`, et ligne du registre des flaky requalifiée en défaut produit corrigé.

**Écartés ou renvoyés** :
- **Requalification de la révocation côté API — limite connue, task de suivi à rédiger par l'humain (`/po`).** Les clients traitent désormais le refus explicite et une réception déléguée introuvable. Il reste le cas d'un **sous-dossier** dans la fenêtre bornée de task-397 (décision 9). Au rejeu `/e2e` après la tranche 9, ce sous-dossier a répondu `FOLDER_NOT_FOUND` pendant 180 s, alors que la liste et la racine étaient encore servies. Le client ne peut alors pas distinguer « sous-dossier supprimé par la délégante » de « délégation retirée » : il affiche « Ce dossier n'existe plus ». C'est contraire à § Révocation, et c'est la cause du flaky E2E-DELEG-004, 2ᵉ occurrence. Seule l'API peut trancher : sur un 404 délégué, revérifier la racine sur une session IMAP **renouvelée**. Or le gestionnaire de sessions n'offre aucune invalidation, et ce chemin est sensible sous charge. Un test d'intégration « révocation pendant la consultation » a été écrit puis retiré : sur le banc d'intégration, la session répond encore 200 dans la fenêtre, ce que la décision 9 accepte. Il exigeait donc plus que la spécification ;
- **politique unique des gestes** (`mailCapabilities`) : facultative ;
- **DoD « aucun appel d'enrichissement ni de SSE »** : remplacée par la décision humaine 14 de la task-397 (« après essai »), plus récente que ce texte. L'écart est annoncé en tête des PR.

**Validation** :
- mobile : 1 333 tests verts, lint propre, build vert ;
- weda2 : `mss-lib` 121 fichiers de test verts, build `weda2` vert, aucun warning sur une ligne de la task ;
- api-mail : build vert ; 21 tests de délégation et 111 tests de l'outillage e2e et du catalogue, verts.

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-folder-list | Menu latéral : Dossiers IMAP (label `mail-folder-list`) | 8dfbb9fc7b7c49318ce15b77a660ac3b | reused | [capture](https://lh3.googleusercontent.com/aida/AEtjO1Wz_Db_zIKRl3SAkV6nqgNX5ck1waTpQKA0NOkCkN5FZUDXwTfqLb3tAKLX3fPsmWuSM00_l1CDjHD1Tanq4BTRnGtCVoBQtdVG_GbLjqlwuavraisrunhxU27WTAFs_v63BSCVDH6VPvTIYgC7EqXZWZ8Nfr7dy3tw7682-fLv_XxHyJPTUaKxSFBF8kSjP6omwdISyV7Hg8Xz0F9Wcd3EoTu0ISWEqEMjFGDlFrXAvChJq6KTYF50gt0) |
  | mail-detail | E-mail : Compte-rendu patient Martin (label `mail-detail`) | 39b4cedfd18d47778ad4b23ab20f5d72 | reused | [capture](https://lh3.googleusercontent.com/aida/AEtjO1UExtCC3meeJkOwl6t1tYvRBJr7kE7mEn7pxQXyK1VWFQUxHs8o9acaTx4AOix7tN7g4A5BHYJpNLZYjhTB2eoK0-rJsEEqlljeUqiirh0rJ3YuormlunWz-JveB48GnJWzepKQ5t420npTmC0vZdCJ8UO8fl62SeAm7JW7Ot776DFZrtq0Kn14EnpgKAeDa0wzUC3o6P5ps-MrqPj-RbUBKwaiviwAYGFezBoOEfibJ6KICzisvOmqo_4c) |
- La section « Boîtes déléguées » et le bandeau « (délégation) » sont des **ajouts** à deux écrans existants : ils se codent dans le langage visuel de ces références (pilules de dossier, en-tête de section, jetons du socle) avec un accent de délégation propre. Aucune régénération Stitch n'a été lancée (risque de doublon par timeout, `edit_screens` régénère tout l'écran) : rafraîchir les deux écrans dans l'UI Stitch reste à l'humain s'il souhaite la référence à jour.
- ⚠ Rename / labelliser in Stitch UI : none
- ⚠ Doublons suspectés à nettoyer dans l'UI : none
- Stitch reachable : ✓
- **Tranche 4 — mobile** : `core/utils/delegated-mailbox.util.ts` (BAL d'un chemin, réception et corbeille de SA boîte, cibles de « Déplacer vers… », refus « délégation retirée »), `MailStateService` (compteurs sur toute l'arborescence, entrées dépliées en mémoire, mode liste forcé), volet des dossiers (section en dernier, repliée, cumul, couleur `--app-delegation` #5b2a86 — contraste 9,9:1 sur blanc), détail (bandeau, gestes masqués, corps en lecture seule), page hôte (titre, recherche coupée, notification écartée, hors ligne, retrait), déconnexion (`MailboxSessionService.clear()` purge `MailStateService` et `DocumentContentService`).
  - Mutations unitaires, toutes rouges puis restaurées : entrée toujours dépliée (3 tests) ; `isDelegated` neutralisé dans le détail (2 tests) ; refus « délégation retirée » ignoré à l'ouverture d'un dossier (1 test).
  - Un test existant reposait sur la détection « sent » par le nom (`mail-detail.component.spec`, accusé de lecture) : il reçoit désormais la liste des dossiers où les Envoyés portent leur rôle.
  - Le mobile n'a pas de thème sombre (`color-scheme: light`, `variables.scss`) : « même rendu en clair et sombre » est sans objet côté mobile.
- **Tranche 5 — e2e mobile**, banc réel (`e2e:headless --serve-only`, seed de délégation relu par l'API) : E2E-DELEG-001 (3,6 s), 002 (12,4 s), 003 (6,5 s), 004 (7,5 à 34,6 s selon la fenêtre de révocation).
  - **Défaut trouvé par le banc** : après le retrait, l'API répond `FOLDER_NOT_FOUND` sur un sous-dossier délégué (la racine reste servie un temps par la session IMAP poolée). Le mobile affichait « Ce dossier n'existe plus », que la task écarte pour ce cas. Correctif : un dossier délégué introuvable dont la BAL a quitté la liste relue (`getFolders(true)`) vaut retrait ; s'il reste déléguée, retour à la réception déléguée. 2 tests unitaires.
  - Preuves par mutation (harnais : marqueur compté, nouveau bundle attendu, témoin restauré rejoué vert) : M1 entrée dépliée d'office → 001 rouge « repliée à l'arrivée » ; M2 suppression déléguée jamais envoyée → 002 rouge « le courrier est dans la corbeille de la délégante » ; M3b Répondre non masqué → 003 rouge « detail-action-reply masqué » (M3, `isDelegated` neutralisé, tombait sur le bandeau : remplacée) ; M4 avis générique → 004 rouge « plus déléguée » (premier essai rouge sur un clic expiré : relance rendue tolérante, puis rouge sur l'assertion visée).
- **Tranche 6 — weda2** (code-only, rien de commité) : `core/utils/delegated-mailbox.util.ts` (miroir du mobile, plus `effectiveFolderType` pour le glisser-déposer), `core/utils/folder-panel-width.util.ts` et `mss-mail-folder-splitter` (300 px par défaut, 240 au minimum, plafond 480 réduit pour garder 300 px à la liste, pointeur, clavier ±16 / Début / Fin, double-clic, ARIA, `localStorage` protégé), section « Boîtes déléguées » (en dernier, repliée, cumul, jetons `--mss-delegation-*` clair / sombre sur `:host` de `mss-mail`), détail (bandeau, gestes masqués, panneau Weda et import **non instantiés** — `viewChild` remplace la référence de gabarit `#wedaImport`), Restaurer / Supprimer définitivement (nouveaux, propre et délégué), export `email-{uid}` pour un message délégué, « Déplacer vers… » et glisser-déposer par BAL et par rôle, refus « délégation retirée », racine disparue, hors ligne, notification et journal console du flux SSE sans chemin délégué, accusé et « Annuler et remplacer » par rôle.
  - Tests ajoutés : util (7), séparateur (8), panneau des dossiers (7), détail (8), liste (4), `mss-mail` (7), glisser-déposer (2), accusé de lecture (1) ; un test existant adapté (Envoyés par le rôle).
  - Mutations, rouges puis restaurées : `isDelegated` neutralisé dans le détail → 3 tests rouges (bandeau, gestes masqués, Weda non instancié) ; butée minimale retirée du séparateur → 3 tests rouges.
  - Lint : 0 erreur ; avertissements préexistants (`max-lines`, `@example` vides de méthodes antérieures). Prettier appliqué aux fichiers neufs et aux fichiers propres en HEAD seulement (consigne `prettier-fichier-existant`).

## Sonar log

Analyse complète `healthplatform-api-mail` (SonarQube 9.9.8 local, `sonar.login`), sur la branche `feat/task-398-…`.

- **1ʳᵉ analyse** (`bf97c7d3`) : Quality Gate OK, **1 issue** sur le nouveau code. C'est `CA1859` sur `E2eOptions.Switches`, introduite par la passe `/simplify` : le champ, devenu `private`, devait reprendre son type concret `HashSet<string>`. Corrigée par `44532f60`, et le compteur de la convention est porté à 11.
- **2ᵉ analyse** (`44532f60`) : **QG OK, 0 issue** sur le nouveau code, aucun hotspot à revoir.
- **3ᵉ analyse, après la tranche 9** (`a120684f`) : **QG OK, 0 issue** sur le nouveau code, new coverage 95,1 %. La suite complète est **entièrement verte** (6 989 tests, intégration 1 005/1 005 + 16 sautés) : les trois tests « du jour » passent hors de la fenêtre de minuit.
- Phase 1 (new code) : ✓ — 1 issue corrigée, aucun test à ajouter (new coverage 95,1 %).
- Phase 2 (legacy) : rien à faire, 0 bug / 0 vulnérabilité / 0 smell sur le projet.
- Build / tests : ✓ verts, sauf les trois tests « du jour » de l'intégration. Ceux-ci sont rouges entre 00:00 et 02:00 (heure locale contre `SINCE` en UTC), sans lien avec la task (voir `## Develop log`).

### KPIs qualité (baseline → final)

| Métrique | Baseline (`9d2e5a71`, develop) | Final (`a120684f`) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 95,1 % | 95,1 % | = |
| New bugs / vulnérabilités / smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Bugs / Vulnérabilités / Smells (projet) | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,6 % | 97,5 % | −0,1 pt |
| Duplication | 0,3 % | 0,3 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

- Conventions : `CA1859` → Occurrences 11 (`conventions/csharp.md`), avec une variante nouvelle : restreindre la visibilité d'un membre, c'est aussi revenir à son type concret.

## Lint log

- Mode : chaîné. Contournement task-367 : `npx nx run-many -t lint --projects=mss-lib`, puis `npx eslint -f json` sur les 34 fichiers `.ts` de la task. Les messages sont attribués à la task par `git diff -U0 HEAD`, et les fichiers non suivis comptent en entier.
- Base : `origin/next` (rafraîchie) ; scope `tag:scope:mss` (`mss-lib` touché ; `e2e/mss-e2e` contrôlé à part).
- Baseline `mss-lib` : **0 erreur** / 43 warnings, tous antérieurs : aucun sur une ligne écrite par la task.
- `e2e/mss-e2e` (specs et support) : 0 erreur ; 31 warnings antérieurs (`jsdoc/require-example`, `max-lines`, `consistent-type-imports`), aucun dans les blocs de la task.
- Fichiers de spec de la task : ignorés par la configuration ESLint du dépôt (motif d'exclusion), comme les autres specs.
- Itérations : 0 / 5 — lint propre, rien à corriger ; auto-fix non lancé (rien de corrigible).
- Build / tests : ✓ verts (`mss-lib` 121 fichiers de test, build `weda2`) depuis la passe §Q, aucun changement depuis.
- Conventions : aucune règle corrigée à la main → rien à reporter dans `conventions/angular.md`.
- Git : aucune opération (code-only) ; les changements restent non commités sur `feature/nova-mss-weda-integration`.

## Lint mobile log

- Branche : `feat/task-398-delegation-bal-deleguees-mobile-weda2`, arbre propre (`c40d504`).
- Baseline `ng lint` : **All files pass linting** — 0 erreur, 0 warning.
- Itérations : 0 / 5 — rien à corriger, aucun commit.
- Build / tests : ✓ verts depuis la passe §Q (`npm run build`, 1 326 tests Karma), aucun changement depuis.
- Conventions : rien à reporter dans `conventions/angular.md`.

## E2E log

> ⚠️ **Flaky récurrent → task de stabilisation à ouvrir** : E2E-INBOX-001 [angular], 3ᵉ occurrence (task-343, task-397, task-398), `page.waitForURL` en dépassement au 1er essai.
> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 [angular], posée le 2026-10-09 (17 jours), correction due par **task-350**.
> ⚠️ **Divergence à retirer** : E2E-MAILBOX-002 [angular] (task-395) — le client weda2 est revenu à la version du catalogue ; décision de l'humain.

Rejeu après la tranche 9 (retours de `/review`). Le premier passage, avant la tranche 9, était vert lui aussi ; il est remplacé par celui-ci.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail + client-mobile touchés (`a120684f` / `c44b22d`) | ✅ verte (jouée) | 49 verts, 1 flaky, 0 rouge, 0 quarantaine | 11 min 0 s |
| angular | api-mail + client-angular touchés (weda2 non commité) | ✅ verte (jouée) | 58 verts, 1 flaky, 0 rouge, 1 quarantaine (verte) | 8 min 49 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`a120684f`)
- Porte : **code 0**, rendue par ce run (`gate --out` régénéré)
- Quarantaines : E2E-COMPOSE-002 [angular] — task-350 (verte à ce run)
- Divergences ouvertes : E2E-MAILBOX-002 [angular] — task-395, **à retirer**
- Flaky :
  - **E2E-DELEG-004 [mobile]** : 2ᵉ occurrence, cause établie. Dans la fenêtre bornée de révocation (task-397, décision 9), le sous-dossier délégué répond `FOLDER_NOT_FOUND` alors que la liste et la racine sont encore servies. Le client ne peut pas distinguer ce cas d'un dossier supprimé. Seule une requalification côté API le peut : task de suivi à rédiger (voir `## Develop log`, tranche 9). La 1ʳᵉ occurrence était un défaut client, corrigé par la tranche 9.
  - **E2E-INBOX-001 [angular]** : 3ᵉ occurrence, sans lien avec la task ; une task de stabilisation est à ouvrir.
- Parcours touchés sans spec e2e modifié : aucun (les deux suites portent E2E-DELEG-001..004)
- Démontage : complet — ports 5052, 8100, 4200, 3993, 3465, 3143 libres ; aucun conteneur e2e en marche. Deux conteneurs arrêtés depuis le 2026-10-14 (`e2e-greenmail-gcgjbrzp`, `e2e-dovecot-kgrndjwd`) ne viennent pas de ce run ; ils sont laissés en place.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (2) :

- [mobile] « BAL déléguée — la délégation retirée pendant la consultation ramène à sa propre réception » (E2E-DELEG-004)
- [angular] « inbox — filtres Non lus / Lus / Tous et recherche » (E2E-INBOX-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ⚠️ flaky | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
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
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
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
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-DELEG-001 | 1 | headless | Voir la BAL déléguée dans sa section, repliée sous la BAL principale, et lire un compte rendu | ✅ | ✅ |
| E2E-DELEG-002 | 1 | headless | Supprimer un message délégué vers la corbeille de la délégante, puis le restaurer | ✅ | ✅ |
| E2E-DELEG-003 | 1 | headless | Dans une BAL déléguée, seuls les gestes de gestion sont proposés | ✅ | ✅ |
| E2E-DELEG-004 | 1 | headless | La délégation retirée pendant la consultation ramène à sa propre réception | ✅ | ⚠️ flaky |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

Ouvertes le 2026-10-26, label `awaiting-human-merge` (HAG, règle 10) :
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/48
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/314
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/107
- `client-angular` (code-only) : l'humain gère le commit et le push TFS, et ouvre la PR. Les modifications sont non commitées sur `feature/nova-mss-weda-integration`, validées par build `weda2` vert, `nx test` des 12 projets vert, lint propre et voie e2e Angular verte. **Le catalogue exige `angular: requis` pour E2E-DELEG-001..004 : la PR TFS doit accompagner le merge d'api-mail.** Fichiers :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/e2e/mss-e2e/support/session.ts`
  - `front/libs/mss/src/core/components/notification-dispatcher/notification-dispatcher.component.spec.ts`
  - `front/libs/mss/src/core/components/notification-dispatcher/notification-dispatcher.component.ts`
  - `front/libs/mss/src/core/models/folder.model.ts`
  - `front/libs/mss/src/core/services/mail-events-stream.service.spec.ts`
  - `front/libs/mss/src/core/services/mail-events-stream.service.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.ts`
  - `front/libs/mss/src/core/utils/read-receipt.util.spec.ts`
  - `front/libs/mss/src/core/utils/read-receipt.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.read-receipt.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.html`
  - `front/libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.html`
  - `front/libs/mss/src/features/mail/mss-mail.component.scss`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-drag.service.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-drag.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-event.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/core/utils/delegated-mailbox.util.spec.ts`
  - `front/libs/mss/src/core/utils/delegated-mailbox.util.ts`
  - `front/libs/mss/src/core/utils/folder-panel-width.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.delegation.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.delegation.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-splitter/mail-folder-splitter.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-folder-splitter/mail-folder-splitter.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-folder-splitter/mail-folder-splitter.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.delegation.spec.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.delegation.spec.ts`

## Code Review Summary

- **1ʳᵉ passe — CHANGES REQUESTED** (2026-10-26, trois relectures indépendantes : backend et contrat, mobile, weda2). Le bloquant commun : la révocation dépendait d'une liste relue que le serveur peut servir périmée. Corrigé par la tranche 9 (voir `## Develop log`).
- **2ᵉ passe — APPROVED** (2026-10-26), sur le diff de la tranche 9. Points 1 à 4 vérifiés ✅. Il n'y a plus d'écriture de liste serveur qui contourne `setFolders`.
- **Suggestions non bloquantes**, reportées dans les PR :
  - mobile : `leaveIfDelegated` peut remplacer la navigation `/login?expired=1` à l'expiration de session pendant la lecture d'un message délégué ;
  - api-mail : le README e2e ne liste pas encore `delegation` ni `--mailbox` ;
  - plusieurs pods : réapparition possible de la BAL dans la fenêtre bornée.
- **Règle 1b** :

  | Comportement | Test d'intégration | Preuve rouge |
  |---|---|---|
  | `GET /mail/folders` : `Owner` / `Role` des dossiers délégués, `Type` inchangé | `TheFolderList_GivesEveryFolderItsOwnerAndRole_…` | avant branchement + mutation M1 |
  | Même chose sur la liste servie par le cache | même test, 2ᵉ lecture | mutation « annotation limitée au `refresh` » |
  | BAL propre : `Owner` vide, rôle du type ; Brouillons virtuel unique | même test | même rouge |
  | Règle 14 sur la route modifiée | même test (`RowsContainingAsync`) | garde task-397 |
- **E2E double verrou** : `## E2E log` vert (porte 0), DoD des scénarios E2E-DELEG-001..004 remplie : catalogue `v1`, implémentés et prouvés rouges sur les deux clients.
- **DoD** : tous les critères sont remplis, sauf un, remplacé. « Aucun appel d'enrichissement ni de SSE » cède devant la décision humaine 14 de task-397, plus récente. L'écart est annoncé en tête des PR, à valider au HAG.

## Merged

Mergé le 2026-10-26 par `/merge task-398 --i-tested`, sur attestation de test manuel de l'humain (HAG, règle 10). Squash, dans l'ordre topologique :

| Dépôt | PR | Commit squash sur `develop` | CI `develop` |
|---|---|---|---|
| `dtos-mss` | #48 | `ed31ab9c` | ✅ https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/40279987244 |
| `api-mail` | #314 | `84988dda` | ✅ https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/40280003174 |
| `client-mobile` | #107 | `95944249` | ✅ https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/40280018739 |

- Branches `feat/task-398-delegation-bal-deleguees-mobile-weda2` supprimées (distantes et locales) ; clones revenus sur `develop`. Label `awaiting-human-merge` retiré.
- `client-angular` : géré manuellement par l'humain (TFS).
- Staging : aucune branche `forge/staging-*` (cycle lancé par `/start`, hors `/forge`).
