# todo-task-353.md — Un message supprimé depuis un autre logiciel disparaît de la liste, et ne s'ouvre jamais sur un contenu vide

**Repos**: api-mail, client-angular, client-blazor, client-mobile
**Dependencies**: — (aucune ; task-352 touche le même composant de liste, même famille de défaut : la mettre en œuvre d'abord évite un conflit)
**Epic**: E009
**Priorité**: **2** — le praticien voit un message qui n'existe plus, l'ouvre, et lit un compte rendu **vide**. Il peut croire le document vide, ou perdu, au lieu de comprendre qu'il a été supprimé ou déplacé ailleurs. Le cas est courant dès que la boîte MSSanté est aussi ouverte dans un autre logiciel.

> **Origine.** Bug constaté par l'humain le 2026-10-04, journal Seq à l'appui :
> 1. Dans le client Angular, dossier `Demo/Biologie` ouvert, avec le message UID 10.
> 2. Dans un autre client de messagerie, sur la même boîte, on supprime ce message.
> 3. De retour dans Angular, le message est **toujours dans la liste**, et le rafraîchissement automatique (30 s) ne le retire pas. L'ouvrir affiche un **contenu vide** dans le détail.

## Ce qui est établi (Seq, 2026-10-04 07:56–07:58 UTC ; code de develop)

1. **Le serveur sait que le message a disparu.**
   - À chaque rafraîchissement de `GET /api/v1/mail/folders/Demo%2FBiologie` (200), le `SEARCH` IMAP rend **0 UID** (« Status Count=0, UidNext=11 »).
   - L'API répond donc que le dossier est vide.
   - Au passage : la liste d'UID en cache annonce encore 1 UID à chaque appel (« CACHE INVALIDATED (count 1 vs 0) »). Le résultat frais n'y est pas réécrit, et chaque rafraîchissement refait la lecture IMAP.
2. **Angular ne retire jamais un message disparu.**
   - Le rafraîchissement (`mss-mail.component.ts`, `interval(syncIntervalMs)` puis `getFolder`, vers la ligne 400) calcule les seuls UID **nouveaux** de la page.
   - S'il n'y en a pas, il s'arrête (`return EMPTY`). Un UID qui a quitté le serveur reste affiché indéfiniment.
3. **Blazor, même défaut.** `MailListComponent.RefreshEmailsCoreAsync` ne charge que les `newUids` ; les UID disparus restent à l'écran.
4. **Mobile** : pas de rafraîchissement périodique de la liste, seulement le flux temps réel et le « tirer pour rafraîchir ». Le message disparu reste jusqu'à un rechargement complet.
5. **L'ouverture d'un message disparu rend un contenu vide.**
   - `GET …/emails/10` puis `GET …/emails/content/10` répondent **200** en 17 à 24 ms, **sans aucun accès IMAP** dans la trace.
   - Le contenu est servi depuis la base locale ou le cache, où la ligne du message subsiste.
   - Le client affiche ce contenu vide, sans erreur.

## Objective

Un message qui n'existe plus sur le serveur de messagerie (supprimé ou déplacé depuis un autre logiciel) :
1. **disparaît de la liste** au rafraîchissement suivant, ou au « tirer pour rafraîchir » sur le mobile. Les compteurs du dossier suivent ;
2. **ne s'ouvre jamais sur un contenu vide** : l'ouvrir (avant que la liste ne se soit mise à jour) affiche « Ce message n'existe plus : il a été supprimé ou déplacé depuis un autre logiciel de messagerie. », puis le retire de la liste ;
3. s'il était **ouvert** dans le détail au moment où il disparaît, le détail se referme avec le même message.

Les trois clients se comportent de la même façon.

### Périmètre

1. **API** :
   - `GET …/folders/{dossier}/emails/content/{uid}`, et la lecture des en-têtes par UID, sur un message absent du serveur IMAP : un **404 `problem+json`** reconnaissable comme « message introuvable », jamais un 200 vide. Le `detail` ne contient ni sujet ni chemin de dossier ;
   - la ligne locale d'un message absent du serveur ne sert plus de contenu.
   - Le mécanisme (vérification à l'ouverture, purge des UID disparus à la lecture du dossier, cache) est laissé à `/develop`, sous la contrainte du coût : l'ouverture d'un message reste un chemin chaud (verrou `imap_session`).
2. **Angular et Blazor** : le rafraîchissement du dossier ouvert retire les messages dont l'UID n'est plus rendu par le serveur, ouverture d'un message introuvable comprise.
3. **Mobile** : le « tirer pour rafraîchir » et la réouverture du dossier retirent les messages disparus ; l'ouverture d'un message introuvable suit la même règle.
4. Les **étiquettes** (vues `tag:…`) suivent la même règle pour leurs messages, quand la vue est rafraîchie.

### Hors périmètre

- Notification temps réel d'une suppression faite ailleurs (IMAP IDLE / flux) : suivi.
- Un rafraîchissement périodique de la liste sur le mobile : non demandé. Le « tirer pour rafraîchir » suffit.
- Le cache de liste d'UID non réécrit après une lecture fraîche (« count 1 vs 0 » à chaque appel) : signalé ci-dessus. `/develop` le corrige si c'est la même cause, sinon suivi.

## Definition of Done

- [x] Build passes (0 errors) et tests pass (0 failures, hors flaky préexistants documentés) sur `api-mail`, `client-angular`, `client-blazor` et `client-mobile`
- [x] **Tests rouges d'abord** (log des runs rouges dans le task file), sur le code actuel
- [x] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{dossier}/emails/content/{uid}` (règle 1b), vu rouge (règle 1b) :
  - le message a été lu une fois par l'application, puis supprimé sur le serveur IMAP par un autre client ;
  - réponse : 404 `application/problem+json` reconnaissable comme « message introuvable », sans sujet ni chemin de dossier dans le `detail`, lu dans la réponse réelle ;
  - cas nominal : un message présent rend son contenu.
- [x] Test d'intégration de bout en bout pour la lecture des en-têtes par UID `GET …/emails/{uids}` : le message supprimé n'est pas rendu, les autres le sont. Vu rouge.
- [x] Test d'intégration pour `GET /api/v1/mail/folders/{dossier}` : après la suppression ailleurs, `uids` ne contient plus le message et le compte suit (non-régression du comportement déjà correct, à garder).
- [x] Tests de composant, par client (Angular vitest, Blazor bUnit, mobile Jasmine) :
  - le rafraîchissement qui ne rend plus un UID retire le message de la liste ;
  - l'ouverture d'un message « introuvable » affiche le message clair et le retire ;
  - un message ouvert qui disparaît referme le détail avec le message clair.
- [x] Libellé du message en dur en français sur Angular et mobile, via `Localizer` sur Blazor (FR et EN) ; `data-testid` sur le message
- [x] Scénario `E2E-MAIL-005` (v1) ajouté à `Api/Mail/e2e/scenarios.yml`, clients **mobile et angular requis**, et implémenté dans les deux suites :
  - un message est affiché dans la liste, puis supprimé **hors de l'application** ;
  - au rafraîchissement (Angular) ou au « tirer pour rafraîchir » (mobile), il n'est plus dans la liste ;
  - l'ouvrir avant la mise à jour affiche le message clair, jamais un contenu vide.
- [x] **Trou du filet** : `E2E-MAIL-005` prouvé rouge sur le bug non corrigé (Angular : le message reste, contenu vide), ligne ajoutée dans `conventions/e2e.md`
- [x] `/e2e` vert sur les deux voies, parité verte
- [x] Aucune donnée de santé dans les journaux (ni sujet, ni contenu, ni chemin de dossier)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, Dovecot) ; Angular, Blazor et mobile sur une boîte de test ; Thunderbird sur la même boîte.
2. **Disparition au rafraîchissement** :
   - ouvrir `Demo/Biologie` dans l'application, avec un message visible ;
   - le supprimer dans Thunderbird (et vider la corbeille de Thunderbird, ou le déplacer ailleurs) ;
   - attendre le rafraîchissement automatique (30 s) sur Angular et Blazor, ou tirer pour rafraîchir sur mobile.
   - **Attendu** : le message disparaît de la liste et le compteur du dossier baisse. Avant : il restait indéfiniment.
3. **Ouverture avant la mise à jour** : refaire la suppression dans Thunderbird puis, **immédiatement**, cliquer sur le message dans l'application.
   - **Attendu** : « Ce message n'existe plus… », puis le message quitte la liste. Avant : détail vide.
4. **Message ouvert** : ouvrir un message dans l'application, le supprimer dans Thunderbird, attendre le rafraîchissement.
   - **Attendu** : le détail se referme avec le même message clair.
5. **Non-régression** : un message déplacé **depuis l'application** apparaît bien dans le dossier cible ; un nouveau message reçu apparaît toujours au rafraîchissement.
6. Refaire 2 à 4 sur les trois clients.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie (les comptes rendus reçus sont le contenu le plus exposé)
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité de l'affichage de la messagerie existante. Effet de bord utile : un compte rendu n'apparaît plus « vide » à tort, ce qui évite une lecture clinique erronée.
- **INS** : non applicable — aucune donnée patient manipulée par la US
- **Authentification PS** : inchangée — PSC / e-CPS, session existante
- **Habilitations** : inchangées — la boîte du praticien connecté
- **Interop CI-SIS** : non applicable — opérations IMAP de lecture
- **Tracé PGSSI-S** : inchangé. La lecture d'un message introuvable n'est pas une consultation : aucune trace de lecture (`MailRead`) n'est émise pour un message absent du serveur. Avertissement technique sans sujet ni chemin.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé. Le retrait local d'un message supprimé côté serveur aligne la base sur le serveur, sans traitement nouveau.

## Branches

- `api-mail` (pushed) : fix/task-353-message-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-353-message-supprime-ailleurs
- `client-blazor` (pushed) : fix/task-353-message-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-353-message-supprime-ailleurs
- `client-mobile` (pushed) : fix/task-353-message-supprime-ailleurs — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-353-message-supprime-ailleurs
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (`feature/nova-rewriting-mss` au /start, task-352 commitée par l'humain) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : aucune branche à ce stade (branche paresseuse, créée par /develop si un contrat bouge)

## Develop log

**Ordre** : api-mail → client-blazor → client-mobile → client-angular (code-only). Aucun contrat `dtos-mss` touché.

### Conception (api-mail)

Avant la task, les trois chemins de lecture servaient la ligne locale d'un message disparu sans jamais consulter le serveur. Seule la synchronisation de fond purgeait les UID disparus, et elle ne vidait pas le cache par message.

1. **Purge à la relecture du dossier.** Quand `GET folder` relit vraiment IMAP (compte ou `UidNext` changés) :
   - les lignes locales des UID disparus sont supprimées et leurs caches par message vidés (`PurgeVanishedMailsAsync`, évictions en parallèle) ;
   - un dossier devenu vide est désormais mis en cache, ce qui supprime les « count 1 vs 0 » répétés.
2. **Garde à l'ouverture seulement** (`IsMessageGoneFromServerAsync`) :
   - le statut est relu sur le serveur (`bypassStatusCache`, un STATUS) ;
   - la liste d'UID en cache est réutilisée si rien n'a bougé, et la clé de statut partagée n'est pas touchée ;
   - un message disparu donne un 404 `problem+json` `code: MESSAGE_NOT_FOUND`, sans sujet ni chemin ;
   - le 404 du repli IMAP porte le même code.
3. **Règle commune** : un message est « disparu » si `uid < UidNext` **et** s'il est absent de la liste. Un message arrivé après l'état connu n'est jamais retiré.
4. **Page d'en-têtes : aucune garde, aucun coût ajouté.**
   - Une première version filtrait la page en lisant l'état du dossier.
   - La passe qualité l'a retirée : sur le chemin le plus chaud, elle coûtait un STATUS sous le verrou `imap_session` dès que le statut avait plus de 10 s.
   - Chaque client relit le dossier juste avant la page, et cette relecture purge déjà les lignes disparues. Le test d'intégration suit ce parcours.
5. **Outil e2e** :
   - `message --create|--delete` (IMAP hors de l'application, relu) ;
   - connexion praticien partagée (`E2eImap.ConnectPractitionerAsync`, `E2eImapTargets`).
   - Catalogue : **E2E-MAIL-005 v1**.

### Clients

- **Blazor** :
  - `MailService.GetEmailContentAsync` rend `NotFound(MESSAGE_NOT_FOUND)` (via `GetWithOutcomeAsync`) ;
  - `MailListComponent.OnMailsGoneAsync` est appelé au rafraîchissement et à l'ouverture. Il retire les messages de la liste ; si l'un était ouvert, il referme le détail et affiche la notification `MailGone` (FR et EN).
- **Mobile** :
  - le détail affiche `mail-gone-notice` (« Ce message n'existe plus… ») au lieu d'un contenu vide, et retire le message de la liste ;
  - le « tirer pour rafraîchir » repart des UID que le serveur rend encore (verrouillé par un test).
- **Angular** (code-only) :
  - `MailStateService.dropMailsGoneFromFolder` (rafraîchissement) et `dropMailsGoneFromServer` (ouverture, sur `isMessageNotFound`) ;
  - ils retirent le message de la liste, tiennent les compteurs du dossier (`forgetUidsInSelectedFolder`, extrait de `removeMailFromList`) et referment le détail ;
  - l'avis `mail-gone-notice` s'affiche dans la liste.

### Tests rouges d'abord (règle 1 et 1b)

| Comportement | Test | Preuve du rouge |
|---|---|---|
| Contenu d'un message supprimé ailleurs : 404 `problem+json`, `code: MESSAGE_NOT_FOUND`, `detail` sans sujet ni chemin, ligne locale purgée (vraie pile, Dovecot) | `FolderOperationsEndToEndTests.OpeningAMessageDeletedByAnotherClient_Is404ProblemJsonMessageNotFound_NeverAnEmptyContent` | rouge sur le code d'avant (200 avec le contenu périmé) |
| Clic **immédiat**, état du dossier en cache (cache avec mémoire pour le statut et les UID) | `OpeningAMessageRightAfterItsDeletion_IsStill404_EvenWithAWarmFolderCache` | mutation (relecture du statut neutralisée) : 200 périmé ; restauré |
| Message présent : contenu rendu | `OpeningAMessageStillOnTheServer_ReturnsItsContent` | garde du cas nominal |
| En-têtes par UID après relecture du dossier : le message disparu n'est pas rendu, l'autre l'est | `ReadingHeadersByUid_LeavesOutAMessageDeletedElsewhere_AndKeepsTheOthers` | rouge sur le code d'avant (`[1, 2]`) |
| Dossier relu : `uids` sans le message disparu, compte à jour, ligne locale purgée | `ReadingTheFolder_AfterADeletionElsewhere_NoLongerListsTheMessage` | rouge sur le code d'avant (ligne locale conservée) |
| Contrôleur : code posé, ni dossier ni sujet dans le message, cache non lu ; pas de garde hors ligne | `MailControllerTests.GetEmail_*` (3) | — (branches) |
| Blazor : rafraîchissement, message ouvert, ouverture, message arrivé entre-temps | `MailListMailGoneTests` (4) | 3 rouges avant le correctif ; le 4ᵉ est la garde « message arrivé » |
| Mobile : détail (3), « tirer pour rafraîchir » (1) | `mail-detail.page.spec.ts`, `inbox.page.spec.ts` | rouges à la compilation, puis mutation (`onMailGone` neutralisé) : FAILED ; restauré |
| Angular : état (3), rafraîchissement (3), détail (2), liste (1) | `mail-state.service.mail-gone.spec.ts`, `mss-mail.component.mail-gone.spec.ts`, `mail-detail.component.spec.ts`, `mail-list.component.spec.ts` | rouges avant le correctif ; détail : mutation rouge, restauré |
| **E2E-MAIL-005 mobile** | `functional.spec.ts` | vert, puis `onMailGone` neutralisé : **rouge** (« n'existe plus » absent) ; restauré, vert |
| **E2E-MAIL-005 Angular** (trou du filet) | `functional.e2e.ts` | vert, puis deux mutations : état neutralisé → **rouge** à l'ouverture ; réconciliation du rafraîchissement neutralisée → **rouge** sur « le rafraîchissement retire le message disparu » (attendu 0, reçu 1). Restauré, vert |

### Passe qualité §Q (4 relecteurs)

- **Appliqué** :
  - garde de la page d'en-têtes retirée (efficacité) ;
  - `bypassStatusCache` au lieu de la suppression de la clé partagée ;
  - `ExceptWith` sans seconde allocation ;
  - évictions de cache en parallèle, et garde « liste vide » dans la purge ;
  - méthode renommée `IsMessageGoneFromServerAsync` (un seul usage) ;
  - aide de cache de test unifiée (`KeepInCache<T>`) ;
  - outil e2e factorisé ;
  - Angular : réconciliation déplacée dans l'état, compteurs tenus, `isNotFoundWithCode`, code mort retiré du spec ;
  - mobile : `removeMailFromList` réutilisé, route lue une fois, `isNotFoundWithCode`, exécuteur e2e commun (JSDoc orphelin de `deleteFolderElsewhere` remis en place) ;
  - Blazor : `ApplyFilterAsync`, aide `Warned()`.
- **Écarté** :
  - une primitive de purge commune avec la synchro de fond et l'enrichissement (hors du diff) ;
  - les autres chemins qui servent encore une ligne disparue jusqu'à la prochaine relecture du dossier : vues par étiquette, fil, résumé IA, recherche, pièces jointes. L'ouverture du message reste protégée. → suivi ;
  - la lecture du cache de contenu en parallèle du STATUS ;
  - une anti-jointure SQL à la place de `GetExistingUidsAsync` (à mesurer au banc).
- **Re-validation** :
  - api-mail : domain 190, infrastructure 683, api 1 180, application 3 433, intégration 802 (+16) ;
  - Blazor : 423 (+2) ;
  - mobile : 1 004, build OK ;
  - Angular `libs/mss` : 582 ;
  - les deux suites e2e compilent.
- **Rouges isolés pendant `/develop`**, verts seuls et sans rapport avec la task :
  - `SeededThreadsAreCountableTests` (ordre d'exécution) ;
  - `StartSyncAsync_WhenLeaseRenewalFails` (timing sous charge).

### Commits

- api-mail : feature, ouverture à statut relu, passe qualité.
- Blazor : feature, passe qualité.
- Mobile : feature, passe qualité.

Un seul push par repo : api-mail `5a26c443`, Blazor `083671c`, mobile `7cc46c3`.

## Sonar log

**Analyse** : deux passes complètes sur `fix/task-353-message-supprime-ailleurs` (serveur 9.9.8), avec la couverture des cinq suites, vertes à chaque passe : domain 190, application 3 433, infrastructure 683, api 1 180, intégration 802 (+16 ignorés).

**Itération 1** (`242894c2`) : **CA1859** sur `ImapService.PurgeVanishedMailsAsync`, dont le paramètre était déclaré `IReadOnlyCollection<uint>` alors que ses deux appelants passent un `uint[]`. Le paramètre est désormais typé `uint[]`. C'est une récidive sur du code frais, introduite pendant la passe `/simplify` ; elle est consignée dans `conventions/csharp.md` (CA1859, 6ᵉ occurrence).

**Constat restant** : S107 sur `SemanticSearchService:395`, antérieur (task-329), hors du code de la task.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse précédente, 2026-10-04) | Final (task-353) | Δ |
|---|---|---|---|
| Quality Gate | OK | **OK** | = |
| New coverage | 97,5 % | 97,5 % (`ImapService` 98,4 %, `MailController` 94,1 %) | = |
| Coverage projet | 98,0 % | 97,9 % | −0,1 |
| Bugs / Vulnérabilités / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Code smells | 13 | 13 (14 à la première passe, CA1859 corrigé) | = |
| Duplication | 0,4 % (nouveau code 0,15 %) | 0,4 % (nouveau code 0,15 %) | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

- **Commande** : `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (`Client/Angular/front`, `feature/nova-rewriting-mss`, code-only).
- **Baseline** : 6 erreurs, toutes `prettier/prettier`, dans le code de la task (`mail-state.service.ts` : 4 ; `functional.e2e.ts` : 2). Aucune erreur `jsdoc/*` : les nouvelles méthodes ont été documentées à l'écriture, et le JSDoc déplacé dans `problem-details.utils.ts` a été rattrapé avant le lint.
- **Itération 1** :
  - `-- --fix` ramène les erreurs à **0** ;
  - il reste 43 avertissements : `max-lines` sur des fichiers déjà au-delà de 500 lignes, `require-example` préexistants, `complexity` ;
  - les `environment.ts` de l'humain ne sont pas touchés.
- **Build** : 10 projets sur 11 verts. Seul `mss:build:production` est rouge, comme avant la task (`environment.prod.ts` absent). **Tests** : 11 projets verts. La suite e2e compile.
- **Rappel code-only** : les fichiers Angular de la task ne sont pas commités. C'est à l'humain de les commiter et de les pousser sur TFS.

## Lint mobile log

- `npm run lint` : **All files pass linting** dès la baseline. 0 itération, aucun commit.
- Build et tests verts depuis la passe qualité de `/develop` (1 004/1 004), arbre inchangé depuis.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | `api-mail`, `client-mobile` touchés | ✅ verte | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 01 s |
| angular | `api-mail`, `client-angular` touchés | ✅ verte (3ᵉ passage) | 30 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 56 s |

- Backend : `api-mail` @ `242894c2`. Clients : `client-mobile` @ `7cc46c3` ; `client-angular` @ `feature/nova-rewriting-mss`, plus les modifications non commitées de la task. Les rapports sont copiés dans la même commande que leur voie (`agents/e2e.md`).
- Catalogue : **E2E-MAIL-005 v1** ajouté (mobile et angular requis). Il est vert sur les deux clients et a été prouvé rouge par mutation (Develop log).
- **Historique de la voie Angular** :
  1. **1er passage, rouge (défaut du test).** E2E-MAIL-005 attendait le message déposé hors de l'application par un unique `toBeVisible` de 30 s. Or l'état du dossier est en cache 10 s et la liste se rafraîchit toutes les 30 s : l'attente tombe pile à la limite. Le test rouvre désormais la boîte jusqu'à l'arrivée du message (90 s), comme E2E-COMPOSE-001. Consigne `depot-hors-application` créée dans `conventions/e2e.md`.
  2. **2e passage, rouge (incident de banc).** E2E-MAIL-005 est vert. E2E-COMPOSE-002 échoue aux deux essais :
     - 1er essai : le transfert est sans citation. C'est le défaut produit connu, task-350.
     - 2e essai : « Aucun contenu ». Le contenu a répondu 503 après une rafale de connexions IMAP coupées à l'authentification (10053/10054, Seq 12:20:29 UTC), qui a aussi fait échouer `enrich/sync`.
     - Ce chemin n'a pas pris la garde de task-353 : la garde passe par la session IMAP poolée sous verrou et n'ouvre aucune connexion, et ce message n'a reçu aucun 404 « disparu ».
     - L'incident est consigné au registre (E2E-COMPOSE-002).
  3. **3e passage : vert**, 30/30, 0 flaky.
- Porte `gate` sur les copies des rapports : **code 0**. Quarantaines : aucune. Divergences : aucune.
- Démontage complet : ports libres, aucun conteneur e2e résiduel.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

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
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
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
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/275 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/91 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/88 — label `awaiting-human-merge`
- `client-angular` : code-only. L'humain commite, pousse sur TFS et ouvre la PR. Fichiers modifiés, non commités, sur `feature/nova-rewriting-mss` :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/utils/problem-details.utils.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.mail-gone.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.mail-gone.spec.ts`
  - *(les deux `environment.ts` modifiés appartiennent à l'humain : hors task, à ne pas commiter avec elle)*

## Code Review Summary

**APPROVED** — 0 bloquant, 3 suggestions.

- **Validation `/review`** :
  - api-mail : domain 190, infrastructure 683, api 1 180, application 3 433, intégration 802 (+16 ignorés) ;
  - Blazor : 423 (+2 ignorés) ;
  - mobile : 1 004, build OK ;
  - Angular : 11 projets testés verts, lint `tag:scope:mss` à 0 erreur ; build 10/11, seul `mss:build:production` rouge (préexistant).
- **Règle 1b** : quatre tests d'intégration sur la vraie pile, chacun vu rouge (code d'avant ou mutation). Correspondance détaillée dans le Develop log.
- **E2E** : `## E2E log` vert ; E2E-MAIL-005 vert sur les deux clients, prouvé rouge par mutation.
- **Suggestions** :
  - fenêtre de concurrence purge / déplacement fait depuis l'application, bornée par le verrou de session, à vérifier au banc ;
  - autres lectures (étiquettes, fil, résumé IA, recherche, pièces jointes) servies jusqu'à la relecture suivante du dossier : suivi ;
  - primitive de purge commune avec la synchro de fond et l'enrichissement.

## Timings

*(généré par `tools/timing/report.sh --task task-353 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 43 min 41 s | 8 (55 s) | 14 (11 min 37 s) | — | api-mail 6B/5T, client-blazor 0B/3T, client-mobile 2B/4T, client-angular 0B/2T |
| /sonar | ok | 14 min 37 s | 3 (40 s) | 11 (11 min 17 s) | 4 (1 min 12 s) | 1 itération(s), api-mail 3B/11T |
| /lint-angular | ok | 3 min 04 s | 1 (21 s) | 1 (51 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 11 s | — | — | — | — |
| /e2e | ok | 24 min 35 s | — | — | — | e2e ×7 (19 min 56 s) |
| /review | ok | 6 min 15 s | 4 (31 s) | 4 (3 min 45 s) | — | api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 34 s | — | — | — | — |
| **Total cycle** | | **1 h 33 min** | **16 (2 min 28 s)** | **30 (27 min 33 s)** | **4 (1 min 12 s)** | |

Autres commandes mesurées : lint ×3 (55 s)
