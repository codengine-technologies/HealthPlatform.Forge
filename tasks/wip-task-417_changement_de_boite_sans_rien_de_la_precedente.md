# todo-task-417 — Changement de boîte : rien de la boîte précédente ne reste

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-412 (mêmes porteurs d'état et même purge)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`), constats m5, m7 et mineurs clients. Ils ont été
> détachés de task-412 le 2026-10-30, sur décision humaine, après vérification sur le code (mobile
> `cf3505f`, weda2 sur `feature/nova-mss-weda-integration`). `api-mail` porte le catalogue des scénarios
> e2e seulement.

## Objectif

En changeant de boîte, le médecin ne voit plus rien de la précédente : ni conversation IA, ni liste de
patients, ni accueil, ni réglages, ni identité d'expéditeur. Une action faite sur une autre boîte
(rattachement, suppression en attente) ne suspend jamais la boîte qu'il a ouverte.

## Constats vérifiés (2026-10-30)

À la bascule, seuls quatre porteurs d'état sont purgés (`mailbox-scoped-states.ts`) : messages,
patient sélectionné, documents et suppressions en attente. Le reste survit :

| Ce qui survit (mobile) | Cause |
|---|---|
| Conversation IA | `AiChatComponent` vit à la racine. `openFor` réutilise la conversation quand le dossier et les UID sont identiques, sans comparer la boîte : INBOX/27 dans B rouvre la conversation de INBOX/27 dans A |
| Liste de l'onglet Patients | `PatientSearchComponent` charge « patients du jour » une seule fois, dans son constructeur. Les pages d'onglet Ionic ne sont pas recréées |
| Réglages | `UserSettingsService.ensureLoaded()` garde sa promesse pour toujours. Les réglages de A sont relus dans B, et l'enregistrement automatique peut les écrire dans la base de B |
| Identité d'expéditeur | Rechargée au changement, mais une réponse tardive de A peut écraser celle de B : aucune garde de génération |
| Widgets de l'accueil | Rechargés à l'entrée de l'onglet, sans garde contre une réponse tardive |

Autres constats :
- **m7 (mobile, à vérifier sur weda2)** : l'intercepteur suspend la boîte ouverte sur **tout** refus
  d'accès, même pour une requête épinglée à une autre boîte (`MSS_MAILBOX_PIN`). C'est le cas de la
  confirmation de rattachement et des suppressions en attente.
- **Dossier « envoyés »** reconnu par la sous-chaîne `sent` : 1 endroit sur mobile
  (`mail-detail.component.ts`), 3 sur weda2 (`read-receipt.util.ts`, `mail-detail.component.ts`,
  `mail-header.component.ts`). Un dossier « Absent » ou « Consent » serait pris pour les envoyés.
- **weda2** : le flux de notifications ne se rouvre pas après un « Réessayer » réussi. Rapporté par
  l'audit, à confirmer en premier.

## Règles

1. **Tout ce qui appartient à la boîte est purgé à la bascule**, par le mécanisme existant
   (`MAILBOX_SCOPED_STATES` sur mobile, `MSS_RESETTABLE_STORES` sur weda2), et non par un nettoyage écran
   par écran :
   - la conversation IA : fermée et oubliée ;
   - la liste des patients : rechargée pour la nouvelle boîte ;
   - les réglages : promesse oubliée, relus pour la nouvelle boîte, **jamais réécrits** d'une boîte dans
     l'autre ;
   - l'identité d'expéditeur et les widgets : toute réponse arrivée après la bascule est ignorée, par une
     garde de génération.
2. L'état de connexion (« N messages prêts à partir ») est vérifié contre la génération de la boîte.
3. **Requête épinglée** (deux clients) : un refus d'accès sur une requête épinglée à une autre boîte ne
   suspend pas la boîte ouverte. Il est rendu à l'écran qui l'a demandée.
4. **Dossier « envoyés »** reconnu par `FolderType.Sent` sur les deux clients (accusé de lecture,
   annule-et-remplace), jamais par une sous-chaîne du chemin.
5. **weda2** : le flux de notifications se rouvre après un « Réessayer » réussi, si le constat est
   confirmé. Sinon, le `## Develop log` dit pourquoi il ne l'est pas.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-mobile` et `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque client
- [ ] Tests unitaires, chacun vu rouge sur le code d'avant :
  - conversation IA réinitialisée au changement de boîte, même dossier et même UID ;
  - onglet Patients rechargé au changement ;
  - réglages relus au changement, et aucun enregistrement d'une boîte dans l'autre ;
  - réponse tardive ignorée (identité d'expéditeur, widgets) ;
  - requête épinglée refusée sans suspension de la boîte ouverte (deux clients) ;
  - `FolderType.Sent` (deux clients), avec un dossier « Consent » non pris pour les envoyés ;
  - flux de notifications rouvert (weda2), si le constat est confirmé.
- [ ] Scénario **E2E-MAILBOX-007** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` (mobile requis,
      angular requis) : après un changement de boîte, l'assistant, l'onglet Patients et l'accueil ne
      montrent plus rien de la précédente. Implémenté dans chaque client, et prouvé rouge sur le code
      non corrigé.
- [ ] `data-testid` sur tout élément interactif ajouté
- [ ] Aucune donnée de santé en clair dans les logs ni dans le stockage de l'appareil

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). Mobile :
  `cd Client/Mobile && npm start`. weda2 : via le faux hôte.
- **Changement de boîte** :
  1. Dans la boîte A, ouvrir l'onglet Patients, puis l'assistant sur INBOX/1.
  2. Passer à la boîte B, puis rouvrir l'assistant sur INBOX/1.
  3. Attendu : une nouvelle conversation, l'onglet Patients et l'accueil de B.
- **Réglages** : changer un réglage dans A, passer à B. Attendu : les réglages de B. En revenant à A,
  le réglage de A n'a pas été écrit dans B.
- **Requête épinglée** : depuis la boîte A, rattacher une boîte dont l'opérateur simulé refuse l'accès.
  Attendu : l'erreur s'affiche dans l'écran de rattachement, et A reste ouverte, sans « accès suspendu ».
- **Dossier envoyés** : créer un dossier « Consent », y déplacer un message reçu qui demande un accusé
  de lecture. Attendu : la proposition d'accusé de lecture reste offerte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — cloisonnement des données entre boîtes côté client
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.8 (le client agit sur la
  BAL ouverte)
- **INS** : non applicable — affichage de fiches existantes seulement
- **Authentification PS** : inchangée (PSC)
- **Habilitations** : seules les données de la boîte ouverte s'affichent (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (changement de boîte déjà tracé côté serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — logique cliente. Aucune donnée persistée sur l'appareil.
- **AIPD / impact RGPD** : inchangé — corrige un affichage croisé entre boîtes

## Branches

> **Empilée sur task-412** : les branches partent de `fix/task-412-clients-deconnexion-et-changement-de` (et non de `develop`). task-417 réutilise
> la purge et l'évènement `closeMailboxOverlays$` de task-412, et ajoute au même catalogue. Merge :
> procédure des tasks empilées (squash de 412, puis `merge -s ours` de 417 sous double garde).

- `api-mail` (pushed) : fix/task-417-changement-de-boite-sans-rien-de-la — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-417-changement-de-boite-sans-rien-de-la
- `client-mobile` (pushed) : fix/task-417-changement-de-boite-sans-rien-de-la
- `client-angular` (code-only) : la forge écrit sur la branche checkoutée dans `Client/Angular/` (`feature/nova-mss-weda-integration`, qui porte déjà les specs non commités de task-412) — l'humain gère branche, commit, push et PR TFS

## Develop log

### client-mobile (`c9aacea`, `d53f1e8`), empilé sur task-412

| Constat | Correctif |
|---|---|
| Conversation IA (m5) | `AiChatComponent` suit `MailboxSessionService.generation()` : à chaque changement de boîte, elle se ferme et s'oublie |
| Onglet Patients (m5) | `PatientSearchComponent` recharge « patients du jour » à chaque génération |
| Widgets de l'accueil (m5) | `DashboardRefreshService` déclenche un rafraîchissement à chaque génération. L'opérateur `forCurrentMailbox()`, posé sur la requête des 5 widgets, ignore une réponse de la boîte quittée |
| Réglages (m5) | `UserSettingsService` devient un porteur d'état de boîte (`MAILBOX_SCOPED_STATES`) : cache oublié, relu, lecture tardive ignorée (`epoch`). Plus rien n'est enregistré d'une boîte dans l'autre |
| Identité d'expéditeur (m5) | `load()` ignore une réponse si la boîte a changé pendant la lecture |
| État de connexion | déjà gardé par la génération (`refreshConnectionStatus`) : aucun changement |
| Requête épinglée (m7) | intercepteur : un refus sur une requête épinglée à une AUTRE boîte est rendu à l'appelant, sans suspension ni sortie de la boîte ouverte |
| Dossier « envoyés » | `MailDetailComponent.isSentMail` : `FolderType.Sent` des dossiers chargés, jamais la sous-chaîne `sent` |

- Tests unitaires, vus rouges avec des bouchons (10 échecs attendus), puis **1399/1399** verts.
- Doubles mis à jour : les 5 specs de widgets ont reçu `forCurrentMailbox` (consigne « chercher ses
  doubles » de `conventions/angular.md`).
- Build vert. §Q : rien à simplifier.

### client-angular (code-only, non commité sur `feature/nova-mss-weda-integration`)

- **m7** : `mss-headers.interceptor.ts`. Un refus sur une requête épinglée à une autre boîte ne suspend
  plus la boîte ouverte. Test vu rouge, puis 5/5.
- **Dossier « envoyés »** : `isSentFolder(path, folders)` dans `read-receipt.util.ts`, par `FolderType.Sent`.
  Utilisé par `isReadReceiptPending`, `MailDetailComponent.canCancelAndReplace` et
  `MailHeaderComponent.isSentMail`.
  - `MailStateService` est injecté en optionnel dans l'en-tête, qui sert aussi au journal.
  - Mutation (sous-chaîne remise) : 3 rouges, puis 17/17.
- **Flux de notifications (constat confirmé)** :
  - Cause : le serveur ferme le flux en suspendant l'accès, et « Réessayer » (accès non vérifié) ne
    change ni le jeton ni la boîte. L'effet de reconnexion ne se relançait donc pas, et plus aucune
    alerte n'arrivait.
  - Correctif : `MssMailboxAccessSuspendedComponent.act()` rouvre le flux (`connect()`). Test vu rouge,
    puis 7/7.
- m5 sur weda2 : pas de constat. Les écrans se recréent à la navigation. E2E-MAILBOX-007 le garde.

Fichiers weda2 modifiés (non commités) :
- `apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts` et son spec ;
- `libs/mss/src/core/utils/read-receipt.util.ts` et son spec ;
- `libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts` ;
- `libs/mss/src/features/mail/components/mail-header/mail-header.component.ts` ;
- `libs/mss/src/features/mailbox-access-suspended/mss-mailbox-access-suspended.component.ts` et son spec ;
- `e2e/mss-e2e/specs/functional.e2e.ts` (E2E-MAILBOX-007).

### Parcours e2e (catalogue `8b8852bd`)

- **E2E-MAILBOX-007 v1** (mobile et angular requis).
  - Parcours : une fiche de la seule boîte praticien est recherchée dans l'onglet Patients, puis la
    boîte change. La fiche ne doit plus être proposée.
  - Mobile vert. **Vu rouge** sans le rechargement à la génération : `Expected 0, Received 1`.
  - weda2 : joué par la voie Angular de `/e2e`.
- **Écart assumé avec la DoD** : le scénario porte sur l'onglet Patients seul.
  - L'assistant et l'accueil ne s'observent pas de bout en bout de façon fiable. La fenêtre de
    l'assistant couvre le sélecteur de boîte, et l'accueil se recharge à l'entrée de l'onglet.
  - Leurs tests unitaires (vus rouges) les couvrent.
- Catalogue : `ScenarioCatalogTests` 17/17.

## Sonar log

**Sonar : skipped — aucun fichier analysé.** Sur api-mail, la task (empilée sur task-412) ne change que
le catalogue des scénarios e2e (`e2e/scenarios.yml`). Ce fichier est hors de l'analyse C#, donc aucun KPI
ne peut bouger. La référence reste l'analyse de task-416 : Quality Gate OK, 0 issue. Catalogue validé par
`ScenarioCatalogTests` (17/17).

## Lint log

`/lint-angular` en mode A : base `origin/next`, lint limité à `tag:scope:mss`, build et tests sur tout le
périmètre affecté.
- **Base** : 1 erreur (`prettier/prettier` dans `read-receipt.util.ts`, code de la task) et des warnings
  préexistants.
- **Itération 1** : `eslint --fix` sur ce fichier. Le lint passe à **0 erreur** (warnings préexistants).
- **Tests** : 12 projets, dont `mss-lib`, rouge au premier passage sur
  `mail-detail.read-receipt.spec.ts`. Ce spec simulait `MailStateService.folders` par une liste vide, et
  le test « dans Envoyés » attendait la reconnaissance par le nom.
  - Correction : le dossier y est donné avec son type `FolderType.Sent`.
  - `mss-lib` passe alors à **1408/1408**, et les 11 autres projets du périmètre étaient verts.
  - Récidive de la consigne « chercher ses doubles » : compteur porté à 3 dans `conventions/angular.md`.
- **Build** : `mss:build:production` et `prescription:build:production` rouges sur le **budget** de bundle
  initial (+1,02 Mo et +264 ko). Le rouge est préexistant : `prescription` ne dépend pas du code de la
  task, et une trentaine de lignes de logique n'expliquent pas ces tailles. La mémoire est mise à jour.
  Les autres cibles de build du périmètre sont vertes.

## Lint mobile log

- **client-mobile** (`/lint-mobile`) : `npm run lint` → **All files pass linting**. Aucune itération,
  aucun commit.

## E2E log

| Voie | Jouée ? | Résultat |
|---|---|---|
| mobile (`npm run e2e:headless`) | jouée (api-mail `8b8852bd`, mobile `d53f1e8`) | ✅ 57 verts, 0 flaky, parité verte |
| angular (`npm run e2e:mss`) | jouée **trois fois** (weda2 sur `feature/nova-mss-weda-integration`, non commité) | runs 1 et 2 : E2E-MAILBOX-007 rouge, **défaut du test**. Run 3 : ✅ **67 verts**, 1 flaky préexistant, parité verte |

**E2E-MAILBOX-007 sur weda2, défaut du test, corrigé.** Le geste de bascule avait été repris du parcours
embarqué (E2E-MAILBOX-001).
- Run 1 : le test attendait le témoin `mailbox-switcher-current`, qui n'existe qu'en mode embarqué.
- Run 2 : il attendait la liste de la seconde boîte, alors que weda2 autonome mène à l'accueil de la
  messagerie après la bascule. L'accueil montrait bien la seconde boîte (« 1 Total »).
- Correction : ouvrir la boîte de réception après la bascule, puis y lire le message de la seconde boîte.
  3/3 verts en `--repeat-each=3`, puis voie entière verte.
- Aucun défaut weda2 : l'écran Patients y est recréé par la navigation. Il n'y a donc aucune mutation
  d'une ligne pour le prouver rouge ; l'équivalent mobile l'est.

**Flaky préexistants** (registre de `conventions/e2e.md` mis à jour), tous sur des parcours que la task
ne touche pas :
- E2E-PATIENT-004 : 2ᵉ occurrence ;
- E2E-LIVE-001 : 2ᵉ occurrence ;
- E2E-AI-001 : **3ᵉ occurrence, task de stabilisation à ouvrir**.

Démontage vérifié : aucun port e2e à l'écoute.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « patients — la vue « Mails du patient » reste ouverte et ses pages viennent du serveur » (E2E-PATIENT-004)

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
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ⚠️ flaky | — |
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
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
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
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.


## Timings

*(généré par `tools/timing/report.sh --task task-417 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 10 s | — | — | — | — |
| /develop | ok | 15 min 16 s | 1 (7.8 s) | 5 (1 min 08 s) | — | client-mobile 1B/4T, api-mail 0B/1T |
| /sonar | skipped | 0.5 s | — | — | — | api-mail : catalogue e2e (YAML) seul, aucun fichier analysé par Sonar |
| /lint-angular | ok | 4 min 35 s | 1 (22 s) | 2 (1 min 56 s) | — | 1 itération(s), client-angular 1B/2T |
| /lint-mobile | ok | 16 s | — | — | — | — |
| /e2e | ok | 43 min 51 s | — | — | — | e2e ×7 (41 min 00 s) |
| **Total cycle** | | **1 h 04 min** | **2 (30 s)** | **7 (3 min 05 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×3 (32 s)
