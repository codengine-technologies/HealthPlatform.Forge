# todo-task-352.md — Ouvrir un dossier supprimé depuis un autre logiciel : un message clair et un retour à la boîte de réception, plus jamais un chargement sans fin

**Repos**: api-mail, client-angular, client-blazor, client-mobile
**Dependencies**: — (aucune ; task-339, PR #272, touche la même zone côté serveur, sans dépendance fonctionnelle)
**Epic**: E009
**Priorité**: **2** — sur Angular, le praticien reste bloqué devant un chargement sans fin. Il doit changer de dossier pour sortir de l'impasse, sans savoir que le dossier n'existe plus. Le cas est courant : une boîte MSSanté est souvent ouverte aussi dans un autre logiciel (LPS, webmail de l'opérateur).

> **Origine.** Bug constaté par l'humain le 2026-10-04, journal Seq à l'appui :
> 1. Dans le client Angular, la vue e-mail et la liste des dossiers sont chargées, avec le dossier `Demo/Demo2` visible.
> 2. Dans un autre client de messagerie, sur la même boîte, on supprime `Demo2`.
> 3. De retour dans Angular, un clic sur `Demo2` laisse un **spinner sans fin** dans la liste des e-mails.

## Ce qui est établi (Seq, 2026-10-04 07:43:46 UTC ; code de develop)

1. **Serveur** :
   - `GET /api/v1/mail/folders/Demo%2FDemo2` : le serveur IMAP répond `NO Mailbox doesn't exist` au `STATUS`.
   - L'API se répare d'elle-même (« IMAP folder … no longer exists - cleaning up local state » : ligne dossier et mails locaux retirés, liste des dossiers en cache invalidée).
   - Elle rend ensuite **404 avec un corps vide** (`Size=0`, `result.ToActionResult(this)` dans `MailController.GetFolderAsync`). Ce n'est pas du `problem+json` (règle 12), et rien ne permet à un client de distinguer « dossier disparu » d'un autre 404.
2. **Angular** (`libs/mss/src/features/mail/mss-mail.component.ts`) :
   - au changement de dossier, `isLoading.set(true)` puis `getFolder(...).subscribe(next)` **sans gestionnaire d'erreur**. Le 404 laisse le chargement allumé indéfiniment, n'affiche aucun message, et `Demo2` reste dans la liste des dossiers ;
   - le rafraîchissement périodique du dossier ouvert (`getFolder` vers la ligne 401) ne traite pas davantage le cas.
3. **Mobile** (`src/app/inbox/inbox.page.ts`) : l'erreur est attrapée et le chargement s'arrête, mais le message affiché est le texte technique brut (« Http failure response … 404 »), et le dossier fantôme reste dans la liste.
4. **Blazor** (`Application/Services/FolderService.GetFolderAsync`) : l'erreur devient un « Failed to get folder » générique, et le dossier fantôme reste dans la liste.

## Objective

Quand le praticien ouvre un dossier qui n'existe plus sur le serveur de messagerie (supprimé ou renommé depuis un autre logiciel), ou quand le dossier ouvert disparaît pendant la consultation, les **trois clients** :
1. arrêtent le chargement ;
2. affichent un message clair : « Ce dossier n'existe plus : il a été supprimé ou renommé depuis un autre logiciel de messagerie. » ;
3. rafraîchissent la liste des dossiers, où le dossier disparu n'apparaît plus ;
4. ramènent le praticien sur la **Boîte de réception**.

### Périmètre

1. **API** : `GET /api/v1/mail/folders/{dossier}` sur un dossier absent du serveur rend un **404 `problem+json`** que les clients peuvent reconnaître comme « dossier introuvable » (titre ou type stable, sans le chemin du dossier dans le `detail`). Le nettoyage local existant (ligne dossier, mails, cache de la liste) est conservé.
2. **Angular** :
   - ouverture d'un dossier disparu : comportement de l'objectif ;
   - dossier ouvert qui disparaît, constaté au rafraîchissement suivant : même comportement, et le message éventuellement ouvert est refermé avec le dossier ;
   - toute autre erreur de chargement arrête aussi le chargement, avec un message générique, et ne laisse jamais de spinner sans fin.
3. **Mobile** : même comportement, à l'ouverture et au rafraîchissement du dossier ouvert ; plus de message technique brut.
4. **Blazor** : même comportement, à l'ouverture et au rafraîchissement du dossier ouvert.
5. Les **étiquettes** (vues `tag:…`) et le dossier virtuel **Brouillons** ne sont pas concernés : ce ne sont pas des dossiers IMAP.

### Hors périmètre

- Détecter la suppression **avant** le clic (notification temps réel de la structure des dossiers) : suivi.
- Retrouver automatiquement le nouveau nom d'un dossier renommé ailleurs.
- Les autres routes d'un dossier disparu (lecture d'un message, déplacement vers lui) : leur comportement d'erreur actuel n'est pas modifié, sauf s'il laisse un chargement sans fin dans le même parcours (alors corrigé ici).

## Definition of Done

- [x] Build passes (0 errors) et tests pass (0 failures, hors flaky préexistants documentés) sur `api-mail`, `client-angular`, `client-blazor` et `client-mobile` (commandes de la table des repos)
- [x] **Tests rouges d'abord** (log des runs rouges dans le task file), sur le code actuel
- [x] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{dossier}` (règle 1b) :
  - un dossier supprimé sur le serveur IMAP après avoir été listé rend un 404 `application/problem+json`, reconnaissable comme « dossier introuvable », sans le chemin du dossier dans le `detail`, lu dans la réponse réelle ;
  - le nettoyage local a eu lieu : la liste des dossiers suivante ne contient plus le dossier ;
  - cas nominal : un dossier existant rend 200 ;
  - test vu rouge (règle 1b).
- [x] Tests de composant, par client (Angular vitest, Blazor bUnit, mobile Jasmine) :
  - ouverture d'un dossier qui répond « dossier introuvable » : chargement arrêté, message clair affiché, liste des dossiers rechargée, Boîte de réception sélectionnée ;
  - même chose quand le rafraîchissement du dossier ouvert répond « dossier introuvable » ;
  - toute autre erreur à l'ouverture : chargement arrêté, message générique, aucune redirection.
- [x] Libellé du message en dur en français sur Angular et mobile (convention actuelle), via `Localizer` sur Blazor (FR et EN) ; `data-testid` sur le message
- [x] Scénario `E2E-FOLDER-003` (v1) ajouté à `Api/Mail/e2e/scenarios.yml`, clients **mobile et angular requis**, et implémenté dans les deux suites :
  - le dossier est créé, listé, puis supprimé **hors de l'application** ;
  - son ouverture affiche le message, le dossier n'est plus dans la liste et la Boîte de réception est affichée.
- [x] **Trou du filet** : `E2E-FOLDER-003` prouvé rouge sur le bug non corrigé (Angular : spinner sans fin), ligne ajoutée dans `conventions/e2e.md`
- [x] `/e2e` vert sur les deux voies, parité verte
- [x] Aucune donnée de santé dans les journaux, ni le nom du dossier dans le `detail` de l'erreur : un nom de dossier peut nommer un patient

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, Dovecot) ; Angular, Blazor et mobile sur une boîte de test ; un client IMAP tiers (Thunderbird) sur la même boîte.
2. **Ouverture d'un dossier disparu** :
   - dans l'application, ouvrir la vue e-mail : la liste des dossiers montre `Demo/Demo2` ;
   - dans Thunderbird, supprimer `Demo2` ;
   - revenir dans l'application et cliquer sur `Demo2`.
   - **Attendu** : le chargement s'arrête aussitôt, le message « Ce dossier n'existe plus… » s'affiche, `Demo2` disparaît de la liste et la Boîte de réception s'affiche. Avant : spinner sans fin sur Angular, message technique sur mobile et Blazor.
3. **Dossier ouvert qui disparaît** :
   - ouvrir `Demo3` dans l'application (avec un message ouvert) ;
   - le supprimer dans Thunderbird ;
   - attendre le rafraîchissement, ou le provoquer.
   - **Attendu** : même message, `Demo3` disparaît de la liste, retour à la Boîte de réception.
4. **Non-régression** : ouvrir un dossier existant, une étiquette (« BIO ») et les Brouillons : aucun message, aucun changement.
5. Refaire 2 et 3 sur les trois clients.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — robustesse de l'interface de messagerie existante, aucune exigence nouvelle
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : inchangée — PSC / e-CPS, session existante
- **Habilitations** : inchangées — la boîte du praticien connecté
- **Interop CI-SIS** : non applicable — opérations IMAP de structure de boîte
- **Tracé PGSSI-S** : inchangé. L'échec d'ouverture est journalisé en avertissement technique, sans chemin de dossier ni contenu de message (un nom de dossier peut nommer un patient). Le message d'erreur rendu au client ne porte pas le chemin.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau ; le nettoyage local des mails d'un dossier disparu existe déjà

## Branches

- `api-mail` (pushed) : fix/task-352-dossier-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-352-dossier-supprime-ailleurs
- `client-blazor` (pushed) : fix/task-352-dossier-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-352-dossier-supprime-ailleurs
- `client-mobile` (pushed) : fix/task-352-dossier-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-352-dossier-supprime-ailleurs
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (`feature/nova-rewriting-mss` au /start) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : aucune branche à ce stade (branche paresseuse, créée par /develop si un contrat bouge)

## Develop log

**Ordre** : api-mail → client-blazor → client-mobile → client-angular (code-only). Aucun contrat
`dtos-mss` touché : pas de branche, pas de publication NuGet.

### Ce qui a été fait
- **api-mail** : `GET /api/v1/mail/folders/{dossier}` sur un dossier absent du serveur lève
  `NotFoundException(message, MailNotFoundCodes.FolderNotFound)`. `NotFoundException` devient
  `IErrorCoded`, et le `GlobalExceptionHandler` existant pose `code: FOLDER_NOT_FOUND` dans le
  ProblemDetails. Le `detail` est une phrase fixe, sans le chemin. Le nettoyage local existant
  (suppression du dossier en base, invalidation du cache) est conservé tel quel.
  Outil e2e : sous-commande `folder --delete <chemin>`, qui supprime un dossier par IMAP hors de
  l'application et relit la suppression. Catalogue : **E2E-FOLDER-003 v1** (mobile et angular requis).
- **client-blazor** : `HttpRequestService.GetWithOutcomeAsync` (valeur, statut, `code`), sur le
  modèle de `PostOutcome`. `FolderService.GetFolderAsync` rend `Result.NotFound` sur
  `FOLDER_NOT_FOUND`. `MailListComponent` relit le dossier à l'ouverture, et rafraîchit sur
  `NotFound` : il referme le message ouvert, relit le menu (nouvel événement
  `RefreshFolderList`), ouvre la boîte de réception et affiche la notification `FolderGone`.
  Toute autre panne : `FolderLoadError`, sans redirection. Libellés FR et EN.
- **client-mobile** : `inbox.page.ts`. Sur `FOLDER_NOT_FOUND`, la page relit les dossiers, ouvre
  la boîte de réception (`findInbox`, partagé avec `loadFolders`) et affiche l'avis
  `mail-folder-error`. Toute autre panne affiche un message générique au lieu du message
  technique brut.
- **client-angular** (code-only, non commité) : signal `folderLoadError` (`MailStateService`),
  `isFolderNotFound` dans `problem-details.utils.ts`, gestionnaire d'erreur sur `folderChanged$`
  (le chargement s'arrêtait jamais : spinner sans fin), `onFolderGone` aussi sur le
  rafraîchissement du dossier ouvert, et bandeau `mail-folder-error` dans `mail-list`.

### Tests rouges d'abord (règle 1 et 1b)

| Comportement | Test | Preuve du rouge |
|---|---|---|
| 404 problem+json `code: FOLDER_NOT_FOUND`, `detail` sans le nom, dossier retiré de la liste suivante (vraie pile : HTTP, DI, handler, Postgres, Dovecot) | `FolderOperationsEndToEndTests.OpeningAFolderDeletedByAnotherClient_Is404ProblemJsonFolderNotFound_AndItLeavesTheFolderList` | rouge sur le code d'avant : `code` absent du ProblemDetails |
| Dossier existant : 200 | `FolderOperationsEndToEndTests.OpeningAnExistingFolder_StillReturnsIt` | garde du cas nominal (vert avant et après) |
| Contrôleur : code posé, nom absent du message | `MailControllerTests.GetFolder_NotFound_ThrowsFolderNotFound_ForTheProblemDetailsCode` | rouge avant le correctif |
| Blazor : ouverture, rafraîchissement, panne générique | `MailListFolderGoneTests` (3) | rouges avant le correctif (NRE dans `GetMails` : la liste périmée se chargeait) |
| Mobile : idem | `inbox.page.spec.ts` (3 nouveaux) | mutation (branche neutralisée) : 3 FAILED, restauré |
| Angular : idem | `mss-mail.component.folder-gone.spec.ts` (4), `mail-list.component.spec.ts` (+3) | rouges avant le correctif |
| **E2E-FOLDER-003 mobile** | `functional.spec.ts` | vert sur le code corrigé, puis mutation `if (Date.now() < 0 && isFolderNotFound(err))` dans `inbox.page.ts` : **rouge** sur « le praticien est prévenu que le dossier n'existe plus » (`mail-folder-error` absent), restauré par copie, vert à nouveau |
| **E2E-FOLDER-003 Angular** (trou du filet) | `functional.e2e.ts` | vert sur le code corrigé ; bug d'origine réinjecté (`onFolderLoadFailed` neutralisé par `if (Date.now() > 0) { return }`, nouveau bundle attendu dans `weda2.log`) : **rouge** sur « le praticien est prévenu que le dossier n'existe plus ». La capture montre le bug signalé : dossier fantôme toujours au menu, liste en chargement sans fin. Restauré par copie, nouveau bundle, vert à nouveau |

Sessions `--serve-only` arrêtées par `out/STOP` : ports libres, aucun conteneur e2e résiduel.

### Passe qualité §Q (`/simplify`, 4 relecteurs)
- **Appliqué** :
  - api-mail : constructeur `NotFoundException(message, errorCode)`, comme `UnavailableException`,
    et `ImapHelper.CollectAllPaths` réutilisé par le test d'intégration ;
  - Blazor : `MailNotFoundCodes` dans son propre fichier, et un seul arrêt du chargement ;
  - mobile : `findInbox` partagé ;
  - Angular : `isFolderNotFound` déplacé dans `problem-details.utils.ts` (sur `isProblemDetails`),
    et suppression de l'attribut `data-folder-error` (non lu) et de l'alias `folderLoadError`.
- **Corrigé en chemin** : apostrophe dans une chaîne entre apostrophes simples, dans les deux
  specs e2e (erreur de syntaxe, voie entière en panne). Prévention : `conventions/e2e.md`,
  « suite-e2e-non-compilee ».
- **Écarté** :
  - lancer `JoinFolderAsync` en parallèle du GET de validation (Blazor) : gain faible, et un
    redémarrage du flux gâché dans le cas d'un dossier disparu ;
  - premier rafraîchissement redondant au démarrage (Blazor) : comportement préexistant, hors
    du diff ;
  - `GetOutcome` réécrit sur `PostOutcome` : optionnel ;
  - Angular `onFolderGone` via `refreshFolders` : effets de bord à évaluer, hors §Q ;
  - `E2eFolder.FindAsync` via `GetFolderAsync` : mineur.
- **Re-validation** :
  - api-mail : build 0 erreur, et tests ciblés verts (infra 29, api 246, application 48,
    intégration 17) ;
  - Blazor : 412 verts, 2 ignorés ;
  - mobile : 994/994, build OK ;
  - Angular `libs/mss` : 564/564 ;
  - suites e2e : `tsc` vert sur les deux.

### Validation complète
- api-mail, toutes suites (avant §Q) : domain 190, infrastructure 683, application 3384,
  api 1170, intégration 792 (16 ignorés) — 0 échec.
- Push unique par repo : api-mail `7cd63aab`, Blazor `ea1dd0b`, mobile `b082712`.

## Sonar log

**Analyse** : une passe complète sur `fix/task-352-dossier-supprime-ailleurs` (serveur 9.9.8,
`sonar.login`), avec la couverture des cinq suites, toutes vertes : domain 190, application
3 384, infrastructure 683, api 1 170, intégration 792 (+16 ignorés).

**Constats du nouveau code** : 2.
- **S3925** sur `NotFoundException` : la classe n'est pas scellée et reçoit une propriété
  `ErrorCode`. Le triplet de constructeurs est présent ; seul reste le constructeur
  `ISerializable`, obsolète sur .NET 8+ (SYSLIB0051). L'issue est marquée **FALSE-POSITIVE**,
  avec un commentaire, comme les exceptions voisines. Récidive consignée dans
  `conventions/csharp.md` (S3925, 4ᵉ occurrence).
- **S107** sur `SemanticSearchService:395` : antérieur (task-329), hors du code de la task.

Aucune modification de code : **0 itération**.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-10-03) | Final (task-352) | Δ |
|---|---|---|---|
| Quality Gate | OK | **OK** | = |
| New coverage | 97,5 % | 97,5 % (`NotFoundException` 100 %) | = |
| Coverage projet | 98,0 % | 98,0 % | = |
| Bugs / Vulnérabilités / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Code smells | 13 | 13 (14 à l'analyse, S3925 marqué faux positif) | = |
| Duplication | 0,4 % (nouveau code 0,15 %) | 0,4 % (nouveau code 0,15 %) | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

- **Commande** : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss`
  (`Client/Angular/front`, branche `feature/nova-rewriting-mss`, code-only).
- **Baseline** : 14 erreurs, toutes `prettier/prettier` et toutes auto-réparables. Elles sont dans
  les fichiers de la task : `mss-mail.component.ts`, abonnement `folderChanged$` (10), et
  `e2e/mss-e2e/support/e2e-backend.ts`, `deleteFolderElsewhere` (4). 41 avertissements
  préexistants (`max-lines`, `complexity`, `jsdoc/require-example`).
- **Itération 1** : `-- --fix`, **0 erreur**. Seuls ces deux fichiers ont été modifiés. Les
  `environment.ts` de l'humain n'ont pas été touchés. Les correctifs de l'auto-fixer ne
  comptent pas dans `conventions/angular.md`.
- **Build** (`nx affected -t build`) : 10 projets sur 11 verts, `weda2` compris. Seul
  `mss:build:production` est rouge, à cause du rouge **préexistant** connu
  (`environment.prod.ts` absent sur `feature/nova-rewriting-mss`), qui n'est pas une régression.
- **Tests** (`nx affected -t test --skipNxCache`) : 11 projets verts. La suite e2e compile
  (`tsc`).
- Rappel code-only : les fichiers Angular de la task restent **non commités**. L'humain les
  commite et les pousse sur TFS.

## Lint mobile log

- `npm run lint` (`Client/Mobile`, branche `fix/task-352-dossier-supprime-ailleurs`) :
  **All files pass linting** dès la baseline.
- 0 itération, aucun commit. Build et tests verts depuis la passe qualité de `/develop`
  (994/994), arbre inchangé depuis : pas de re-validation.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | `api-mail`, `client-mobile` touchés | ✅ verte | 28 verts, 0 flaky, 0 rouge, 0 quarantaine | 4 min 39 s (rejouée : 4 min 33 s, voir ci-dessous) |
| angular | `api-mail`, `client-angular` touchés | ✅ verte | 27 verts, 1 flaky, 0 rouge, 0 quarantaine | 4 min 06 s |

- Backend joué : `api-mail` @ `fix/task-352-dossier-supprime-ailleurs`. Clients : `client-mobile` @ `fix/task-352-dossier-supprime-ailleurs`, et `client-angular` @ `feature/nova-rewriting-mss` avec les modifications non commitées de la task. Checkout de l'humain, sans opération git.
- Catalogue : `Api/Mail/e2e/scenarios.yml` de la branche, avec **E2E-FOLDER-003 v1** ajouté (mobile et angular requis). Il est vert sur les deux clients, et a été prouvé rouge par mutation dans `/develop` (voir Develop log).
- Porte `gate` sur les copies des deux rapports : **code 0**. Quarantaines : aucune. Divergences ouvertes : aucune.
- Flaky : **E2E-AI-001** (angular). Premier essai : `response.json: Protocol error (Network.getResponseBody)`. Le test ne touche pas au code de la task. Au registre, 2ᵉ occurrence.
- **Voie mobile rejouée** : la voie Angular, qui monte son backend par l'orchestrateur mobile, a vidé `Client/Mobile/e2e/headless/out` avant que le rapport mobile soit copié. La première porte est tombée en « Could not find file » (code 1, outillage). Le rejeu est vert à l'identique (28/28). Prévention : avertissement et commande unique « voie + copie » dans `agents/e2e.md`, Step 1.
- Parcours touchés sans spec e2e modifié : aucun. L'écran de liste des dossiers est couvert par E2E-FOLDER-003 dans les deux suites.
- Démontage : complet. Ports libres, aucun conteneur e2e résiduel.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « assistant — résumé initial puis deux questions de suite, conversation relue du serveur » (E2E-AI-001)

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ⚠️ flaky | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/274 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/90 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/87 — label `awaiting-human-merge`
- `client-angular` : code-only. L'humain gère le commit, le push sur TFS et l'ouverture de la PR. Fichiers modifiés, non commités, sur `feature/nova-rewriting-mss` :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.folder-gone.spec.ts` (nouveau)
  - *(les deux `environment.ts` modifiés sont ceux de l'humain : hors task, à ne pas commiter avec elle)*

## Code Review Summary

**APPROVED** — 0 bloquant, 2 suggestions.

- Validation `/review` :
  - api-mail : build OK, domain 190, infrastructure 683, api 1 170, application 3 384, intégration 792 (+16 ignorés) ;
  - Blazor : build OK, 412 (+2 ignorés) ;
  - mobile : build OK, 994/994 ;
  - Angular : 11 projets testés verts ; build 10/11, seul `mss:build:production` rouge (préexistant, `environment.prod.ts` absent).
- **Règle 1b** : 404 `problem+json` `code: FOLDER_NOT_FOUND`, `detail` sans le nom, dossier retiré de la liste. Prouvé par `FolderOperationsEndToEndTests.OpeningAFolderDeletedByAnotherClient_…` (vraie pile), rouge sur le code d'avant ; cas nominal gardé par `OpeningAnExistingFolder_StillReturnsIt`.
- **E2E** : `## E2E log` vert. E2E-FOLDER-003 est vert sur les deux clients et prouvé rouge par mutation (Develop log).
- **Points vérifiés** :
  - Blazor : `GetAsync` et `GetQuietlyAsync` gardent leur comportement (corps en tampon, 404 jamais notifié par toast) ;
  - Blazor : Brouillons virtuels et étiquettes exclus de la relecture ;
  - les sous-dossiers vivent dans `FoldersViewModel`, donc remplacer le DTO ne casse pas le menu.
- **Suggestions** :
  - mobile et Angular : le `getFolders` de repli n'a pas de gestion d'erreur ;
  - Blazor : `JoinFolderAsync` pourrait partir en parallèle de la relecture.

## Timings

*(généré par `tools/timing/report.sh --task task-352 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| /develop | ok | 41 min 00 s | 8 (1 min 16 s) | 8 (5 min 06 s) | — | api-mail 5B/3T, client-blazor 0B/2T, client-mobile 3B/2T, client-angular 0B/1T |
| /sonar | ok | 7 min 25 s | 1 (19 s) | 5 (5 min 11 s) | 2 (37 s) | api-mail 1B/5T |
| /lint-angular | ok | 3 min 37 s | 1 (21 s) | 1 (52 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 22 s | — | — | — | — |
| /e2e | ok | 14 min 45 s | — | — | — | e2e ×5 (13 min 18 s) |
| /review | ok | 5 min 58 s | 4 (31 s) | 4 (3 min 44 s) | — | api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 40 s | — | — | — | — |
| **Total cycle** | | **1 h 14 min** | **14 (2 min 29 s)** | **18 (14 min 54 s)** | **2 (37 s)** | |

Autres commandes mesurées : lint ×3 (1 min 03 s)
