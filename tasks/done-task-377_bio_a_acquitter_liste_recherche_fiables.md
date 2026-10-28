# todo-task-377.md — Liste, recherche et puce « Bio à acquitter » montrent ce qu'elles annoncent, et disent quand elles ne peuvent pas

**Repos**: client-angular, api-mail, client-mobile
**Dependencies**: task-375 (identité `(folderPath, uid)` et flux de chargement de la liste)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — des résultats de biologie à acquitter sont masqués alors que le compteur dit qu'ils existent ; une panne fait disparaître la tuile au lieu de la signaler ; la vue « Mails du patient » s'interrompt d'elle-même au bout de 30 s.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-31, ANG-32, ANG-33, ANG-35, ANG-37**).

## Ce qui est établi

- **ANG-31** — `inbox-biology-ack-chip.component.ts:73-125`, `mail-state.service.ts:280-300` : la puce filtre seulement la page chargée, garde les UID d'INBOX dans les autres dossiers, et peut laisser l'INBOX filtrée sans aucun signe visible après un retour de lecture.
- **ANG-32** — `isSearchActive` n'est jamais remis à zéro : pagination disparue (50 premiers messages seulement), recherche effacée qui revient, résultats d'une ancienne recherche affichés en dernier, nouveaux messages ajoutés aux résultats.
- **ANG-33** — `mss-mail.component.ts:815-864` : la vue « Mails du patient » est un dossier virtuel `__patient__/{id}` ; le rafraîchissement le demande à api-mail (404 `FOLDER_NOT_FOUND`) et renvoie à INBOX avec un faux « dossier supprimé depuis un autre logiciel » ; une seule page ; le handle du patient part dans l'URL, les journaux serveur et le SSE.
- **ANG-35** — sans volet de lecture (réglage par défaut), « Version précédente » d'un CDA versionné ne fait rien, et le bouton « IA » détourne la prochaine lecture vers une conversation construite sur d'autres messages.
- **ANG-37** — une erreur masque la tuile « biologie en attente » (le tableau de bord ressemble à « rien en attente ») ; un échec des réglages bloque la messagerie sur un spinner.

## Objective

Que la liste, la recherche, la vue patient et les indicateurs de biologie montrent **exactement** ce qu'ils annoncent — tous les résultats à acquitter, tous les mails du patient, les seuls résultats de la recherche affichée — et qu'une panne soit **signalée** comme telle, jamais confondue avec « rien à signaler ».

### Périmètre

1. **Puce « Bio à acquitter »** servie par le serveur comme une source paginée (comme la recherche), rechargée au changement de dossier, état actif tenu par l'état de la liste.
2. **Recherche** remise à zéro au changement de dossier ; « effacer » annule la requête en vol ; pas d'ajout de nouveaux messages pendant une recherche.
3. **Vue « Mails du patient »** avec sa propre source (hors rafraîchissement de dossier, SSE et puce), paginée côté serveur ; le handle du patient n'apparaît jamais dans un chemin d'URL.
4. **Sans volet de lecture** : « Version précédente » et l'assistant IA fonctionnent (abonnement porté par l'écran mail, `folderPath` respecté) ; l'IA se ferme au changement de dossier.
5. **États « indisponible »** explicites (tuile, puce, écran) avec réessai.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Test d'intégration de bout en bout pour la liste paginée des mails à biologie non acquittée (route existante ou ajoutée) : 60 mails en attente sur deux pages, la page 2 contient les 10 derniers (lus dans la réponse réelle), vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la liste paginée des mails d'un patient, désigné par son handle dans le corps ou la requête et non dans le chemin : la page 2 existe et le handle n'apparaît pas dans le chemin journalisé, vu rouge (règle 1b) — si la route est créée ou modifiée
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] puce active sur la page 3 : les résultats en attente de toutes les pages sont accessibles
  - [ ] changement de dossier pendant une recherche : recherche et pagination remises à zéro
  - [ ] vue patient ouverte 60 s : ni retour à INBOX ni message « dossier supprimé »
  - [ ] sans volet de lecture : « Version précédente » ouvre la version précédente
  - [ ] erreur du résumé de biologie : la tuile affiche « indisponible » et un réessai
- [ ] Scénario E2E-BIO-002 « La puce Bio à acquitter montre tous les résultats en attente, sur toutes les pages » ajouté (angular `requis` ; mobile : `non-applicable` si la puce n'existe pas sur mobile, à confirmer)
- [ ] Scénario E2E-PATIENT-001 versionné : la vue « Mails du patient » reste ouverte et paginée
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] Aucun handle patient, INS ni contenu dans les URL et journaux ajoutés

## Manual Test Plan

1. Boîte avec plus de 50 mails dont des biologies non acquittées réparties sur plusieurs pages : activer la puce → toutes apparaissent, sur toutes les pages.
2. Rechercher « échographie », changer de dossier → la recherche est effacée, la pagination revient.
3. Ouvrir « Mails du patient » depuis le tableau de bord, attendre 2 min → la vue reste ouverte ; parcourir plusieurs pages.
4. Couper api-mail : la tuile « biologie en attente » affiche « indisponible », pas une absence.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie / médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable — rétablit l'exhaustivité de l'affichage des résultats à acquitter
- **INS** : non applicable ; le handle patient sort des URL (cohérent avec task-184)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : résultats de biologie (CDA, LOINC) — affichage seulement
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (biologie)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-377-bio-a-acquitter-liste-recherche-fiables — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-377-bio-a-acquitter-liste-recherche-fiables
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS
- `client-mobile` (pushed, ajouté le 2026-10-28 sur décision humaine — option A de `questions/task-377.md`) : feat/task-377-bio-a-acquitter-liste-recherche-fiables — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-377-bio-a-acquitter-liste-recherche-fiables

> **Restauré le 2026-10-28 à 22:41** : ces sections avaient disparu de l'arbre lors de la synchronisation du plan de contrôle avec `origin/develop` (22:31–22:37, hors de la session de la task). Reconstituées depuis les copies de session ; voir `questions/task-377.md`.

## Develop log

- Repos touchés : `api-mail` (poussé), `client-angular` (code-only, non commité sur `feature/nova-mss-weda-integration`).
- DTOs publiés : aucun changement de contrat NuGet (`PagedResultDto<T>` générique existant ; requête `PatientMailsPageRequest` locale au contrôleur, comme `CorrectTextRequest`). Interop : aucun.
- Commits api-mail :
  - `2e15e8f4` feat(api): la puce bio et la vue patient servies par pages (task-377)
  - `023a0e70` test(e2e): E2E-BIO-002 et E2E-PATIENT-004 au catalogue (task-377)
  - `22805ea7` refactor(api): simplify pass (/simplify) — task-377
- Routes ajoutées :
  - `GET /api/v1/biology-acks/pending-mail-uids/page?folderPath&lastAction&page&pageSize` → `PagedResultDto<uint>`, du plus récent au plus ancien (ANG-31).
  - `POST /api/v1/patients/mails` `{ patientId, page, pageSize }` → `PagedResultDto<MailDto>`, handle dans le corps, trace sans identifiant (ANG-33).
  - `PageQuery.EnsureValid` : page ≥ 1, taille 1..200, sinon 400 problem+json.
- Angular (`libs/mss`) :
  - `MailStateService` : sources de la liste dans l'état (`biologyAckFilterActive`, `searchUids`/`searchRequest`, `patientViewId`, `serverPagedTotal`, `listUnavailable`), numéro de chargement (une réponse ancienne est ignorée), `loadServerPage$()` pour la puce et la vue patient ; la recherche est paginée sur ses propres résultats.
  - `mss-mail` : recherche, vue patient et assistant IA remis à zéro au changement de dossier ; puce éteinte en quittant un dossier (gardée à l'entrée depuis le tableau de bord) ; vue patient hors rafraîchissement, en-tête `__patient__` sans handle ; `requestSelectByUid$` (« Version précédente ») servi par l'écran mail ; réglages et dossiers en panne → message + « Réessayer » ; sans volet de lecture, l'assistant IA s'affiche avant la lecture.
  - `mail-list` : un seul chargement vit à la fois (abandon du précédent), bandeau « liste indisponible » + réessai, puce et recherche absentes de la vue patient, flux temps réel coupé en vue patient, chargement repris quand la liste monte pendant un chargement.
  - Puce : état actif reçu de la liste, recompte au changement de dossier, panne → « indisponible, réessayer ». Tuile KPI : panne → « indisponible » + « Réessayer » (le test qui figeait la tuile masquée est remplacé).
  - Barre de recherche : « effacer » abandonne la requête en vol ; la requête est retenue dans l'état, relue par une liste recréée, vidée quand la liste oublie la recherche.
  - Assistant IA : lit `aiChatFolderPath` (le dossier des messages choisis).
  - `mss-api.service` : `getBiologyAckPendingMailUidsPage`, `getPatientMailsPage` ; `getMailsByPatientIdPaged` (handle dans le chemin) retiré, plus aucun appelant.
  - Banc e2e : `OtherDevice.patientId/userSettings/saveUserSettings` ; `spaNavigate` attend désormais un chemin à requête (comparaison sur la partie chemin).
- Fichiers Angular modifiés (non commités, l'humain commite et pousse sur TFS) : `core/services/mss-api.service.ts`, `features/dashboard/components/biology-ack-pending-kpi-tile/*` (ts, html, scss, spec), `features/mail/components/ai-chat-panel/ai-chat-panel.component.ts`, `features/mail/components/inbox-biology-ack-chip/*` (ts, html, scss, spec), `features/mail/components/mail-list/*` (ts, html, scss, spec, **nouveau** `mail-list.list-sources.spec.ts`), `features/mail/components/mail-search/mail-search.component.ts` + spec, `features/mail/mss-mail.component.*` (ts, html, scss, **nouveau** `mss-mail.component.list-sources.spec.ts`), `features/mail/services/mail-state.service.ts` ; `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`, `e2e/mss-e2e/support/weda.ts`. **E2E-BIO-002 et E2E-PATIENT-004 sont `angular: requis` : `functional.e2e.ts` est à commiter sur TFS avant le merge de la PR api-mail.**
- Build / tests locaux :
  - api-mail : build vert ; suite complète 6 962 tests, 1 rouge **flaky préexistant** `AnnuaireQuotaSharedRedisIntegrationTests.TwoInstances_SimultaneousSearches_NeverGetMoreThanTheBudgetPerSecondTogether` (task-386, budget par seconde : 51 au lieu de 48 sous la charge de la suite complète), vert 3/3 rejoué seul. Après la passe qualité : intégration task-377 9/9, `mss.mail.api.tests` 1 288/1 288 (catalogue compris).
  - client-angular : `nx build weda2` vert ; `nx test mss-lib` 120 fichiers, 1 324 tests verts ; après formatage, specs mail + dashboard 627/627 ; `tsc` de la suite e2e vert ; ESLint sans aucun message sur les lignes de la task.
- Règle 1b, tests d'intégration (`UseCases/MailListSourcesEndToEndTests`, vraie pile, base du praticien) :
  - `SixtyPendingMails_AreServedOnTwoPages_TheSecondHoldingTheTenOldest` : 60 en attente, page 2 = les 10 plus anciens, lus dans la réponse. Rouge avant (404, route absente), puis mutation « `Skip` retiré » → rouge (`Collections differ`).
  - `ThePatientMails_HaveASecondPage_AndTheHandleIsNeverInThePath` : 30 mails, page 2 de 10, pages disjointes, handle absent de l'URL. Rouge avant (405), puis mutation « page forcée à 0 » → rouge (`Expected: 10, Actual: 20`).
  - En plus : résultat résolu sorti des pages, filtre par dernier geste, 400 hors bornes (×3), 404 handle inconnu, 400 handle vide.
- Tests unitaires et de composant, preuve par mutation (`Date.now() < 0`, marqueur compté, restauration par copie puis `touch`) :
  - M1 puce active page 3 (`showsServerPages` ignore la puce) → rouge ; M2 changement de dossier pendant une recherche (`clearSearch` neutralisé) → rouge ; M3 vue patient 60 s (garde du rafraîchissement neutralisée) → rouge ; M4 « Version précédente » sans volet (sélection neutralisée) → rouge ; M5 tuile en panne (`unavailable` jamais posé) → rouge ; M6 « effacer » annule la recherche en vol (abandon neutralisé) → rouge.
- Parcours e2e Angular, banc `--serve-only` (compteur de bundles + 15 s, témoins restaurés verts) :
  - ME1 E2E-BIO-002, puce qui ne demande plus les pages au serveur → rouge (la page des résultats en attente n'est jamais demandée) ;
  - ME2 E2E-PATIENT-004, vue patient de nouveau rafraîchie comme un dossier → rouge sur « la vue reste ouverte après le rafraîchissement ».
- Catalogue : **E2E-BIO-002** v1 (angular et **mobile requis** : la puce et le même défaut existent sur le mobile), **E2E-PATIENT-004** v1 (angular requis, mobile non-applicable : écran absent). **Écart à la DoD** : E2E-PATIENT-001 n'est pas monté en version, le mobile n'ayant pas de vue « Mails du patient ».
- Trou du filet : ligne task-377 ajoutée à `conventions/e2e.md`.
- Passe qualité (/simplify) :
  - Appliquée et commitée : api-mail, 1 fichier (`22805ea7` : paramètres de page par défaut, comme la route voisine).
  - client-angular : rien au-delà du formatage Prettier des lignes de la task.
  - Contrôles §Q 2b (S125, xUnit1045, S4457, xUnit2032) : vides.
- DOD self-check : build et tests ✓ (weda2, api-mail ; 1 flaky préexistant hors task) ; intégration bio paginée ✓ ; intégration patient ✓ ; 5 tests unitaires DoD ✓ ; E2E-BIO-002 ✓ (mobile requis sans test : bloquera `/e2e`) ; E2E-PATIENT-001 versionné ✗ (remplacé par E2E-PATIENT-004, à arbitrer) ; trou du filet ✓ ; aucun handle ni INS dans les URL et journaux ajoutés ✓.
- **Arbitrage humain requis** : `questions/task-377.md` (mobile d'E2E-BIO-002, et E2E-PATIENT-004 au lieu d'E2E-PATIENT-001 v2).
- Next step : `/sonar task-377`

### Relance du 2026-10-28 — `client-mobile` (décision humaine, option A)

- Branche `feat/task-377-bio-a-acquitter-liste-recherche-fiables` créée depuis `origin/develop` et poussée ; commit `855053a` fix(mail): la puce « Bio à acquitter » liste tous les résultats en attente (task-377).
- Correctif (`inbox.page`, `MailStateService`, `inbox-biology-ack-chip`) : activée, la puce ne filtre plus les seuls messages chargés. La liste se **pagine sur les résultats en attente** du dossier, lot par lot, avec le mécanisme de pagination existant du mobile (UID triés, 30 par lot, `GET …/emails/{uids}`). Éteinte, elle revient au dossier. La route paginée d'api-mail n'est pas nécessaire au mobile, qui connaît déjà tous les UID en attente.
  - Numéro de pagination (`pagingSeq`) : un lot parti pour une pagination remplacée (puce basculée, autre dossier) est ignoré à son retour.
  - La puce s'éteint en quittant un dossier, et l'activation depuis le tableau de bord ne joue qu'une fois (elle se rejouait à chaque changement de dossier).
- Tests (Jasmine) : 3 tests de page au travers du parent (`inbox.page.spec.ts`, dossier de 70 messages, résultat en attente hors du premier lot) et 2 tests de puce. Preuve par mutation (`Date.now() < 0`, marqueur compté, restauration par copie puis `touch`) :
  - M1 puce = filtre local (ancien comportement) → 3 rouges ;
  - M2 garde de pagination neutralisée → rouge « ignores a folder batch that answers after the chip was switched on » ;
  - M3 puce non éteinte au changement de dossier → 2 rouges ;
  - M4 auto-activation rejouée → rouge « auto-activates only once ».
- Parcours e2e **E2E-BIO-002 (mobile)** dans `e2e/specs/functional.spec.ts` (+ `OtherDevice.pendingBiologyUids()`). Le banc tient en un seul lot (13 messages) : le test lit les résultats en attente côté serveur, vérifie le compte de la puce, que le clic fait demander au serveur exactement ces messages (méthode et chemin exacts), et que la liste en montre autant. Banc `--serve-only` : témoin vert ; **ME1** (puce = filtre local) → rouge sur `waitForResponse` (les résultats en attente ne sont jamais demandés), bundles 1 → 2, aucun `[ERROR]`, +15 s ; témoin restauré vert (bundles 3). Démontage complet, aucun conteneur résiduel.
- Build et tests : `npm run build` vert ; `npm test` 1 307/1 307 au second passage. Au premier, 3 rouges **hors task** dans `HtmlEditorComponent` (lecture de la sélection du texte et de la signature), verts 7/7 deux fois rejoués seuls puis dans la suite complète : instables sous charge (le banc e2e venait d'être démonté), non consignés jusqu'ici.
- Passe qualité (/simplify) : diff relu, aucun nettoyage appliqué.
- Next step : `/lint-mobile task-377`, puis `/e2e task-377`.

## Sonar log

- Serveur SonarQube 9.9.8 (`sonar.login`), conteneurs `sonarqube_db` puis `sonarqube` redémarrés (arrêtés depuis 48 min), port 9000 mesuré.
- Analyse de `feat/task-377-bio-a-acquitter-liste-recherche-fiables` (`22805ea7`) : build Release vert, 5 passes de tests avec couverture vertes (195 + 3 748 + 695 + 1 288 + 1 020, 16 ignorés comme en baseline).
- Phase 1 (code neuf) : ✓ Quality Gate OK, new_coverage = 96,8 % ; 0 issue, 0 hotspot à revoir sur le code neuf. Fichiers de la task : `PageQuery.cs`, `BiologyAcksController.cs`, `PatientsController.cs` couverts à 100 %.
- Phase 1 — issues corrigées : 0 ; tests ajoutés : 0.
- Phase 2 (legacy) : sans objet, 0 bug, 0 vulnérabilité, 0 code smell (arrêt anticipé, aucune itération).
- Conventions : aucune règle corrigée à la main, `conventions/csharp.md` inchangé.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,8 % | 96,8 % | 0 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : chaîné. Contournement task-367 : `npx nx run-many -t lint --projects=mss-lib`, puis `npx eslint -f json` sur les 21 fichiers `.ts`/`.html` de la task (suite e2e comprise), messages attribués par `git diff -U0 HEAD` (fichiers non suivis comptés en entier).
- Base : `origin/next` rafraîchie ; scope lint `tag:scope:mss`.
- Baseline = final : **0 erreur** ; `mss-lib` 41 warnings, **aucun** sur une ligne de la task (fichiers de la task : 57 warnings, tous antérieurs : JSDoc `@example` vides, `max-lines`, `consistent-type-imports`).
- Itérations : 0 (le formatage Prettier des lignes de la task a été fait par `/develop`, sur les fichiers propres en HEAD seulement).
- Build / tests : verts depuis `/develop` (`nx build weda2`, `nx test mss-lib` 1 324, specs mail + dashboard 627 après formatage) ; rien modifié par cette étape.
- Conventions : aucune règle corrigée à la main, `conventions/angular.md` inchangé.
- Code-only : aucune opération git sur `client-angular` (seul `git fetch origin next`).

## Lint mobile log

- Mode : chaîné, branche `feat/task-377-bio-a-acquitter-liste-recherche-fiables` (`855053a`), arbre propre.
- Baseline = final (`ng lint`, 333 fichiers) : **0 erreur, 0 warning**, rien d'auto-corrigeable.
- Itérations : 0. Build et tests verts depuis `/develop` (`npm run build`, `npm test` 1 307/1 307) ; rien modifié par cette étape, aucun commit.
- Conventions : aucune règle corrigée à la main, `conventions/angular.md` inchangé.

## E2E log

Rejeu après la décision A, sur les branches de la task fusionnées avec `origin/develop` (règle 4 : task-402 mergée dans `develop` pendant le cycle, et code Angular de task-402 et task-377 commité par l'humain sur `feature/nova-mss-weda-integration`).

| Voie | Jouée / réutilisée | Code | Résultat | HEAD couverts |
|---|---|---|---|---|
| mobile | jouée (`npm run e2e:headless`) | 0 | suite verte : 50 verts, 0 flaky, 0 rouge ; parité de la colonne verte (E2E-BIO-002 compris) | api-mail `5e6f34e8`, client-mobile `cfbce70` |
| angular | jouée (`npm run e2e:mss`) | 0 | suite verte : 60 verts, 0 flaky, 0 rouge (E2E-BIO-002 et E2E-PATIENT-004 compris) ; parité de la colonne verte | api-mail `5e6f34e8`, client-angular `fcab4f67` + correctif du test E2E-BIO-002 (2 fichiers e2e non commités) |

- Porte : `mss.mail.e2e gate`, catalogue de la branche de la task (`5e6f34e8`), rapports exécutés des deux voies : **code 0**.
- Démontage : ports 5052, 8100, 4200, 3993, 3465, 3143 libres ; aucun conteneur e2e résiduel.
- Passages écartés, et pourquoi :
  - mobile n° 1 (vert, 48) : non retenu, une autre session a basculé api-mail et mobile sur `develop` puis les a remis sur la branche en pleine voie (22:46, `/merge` de task-402) : une partie du build a vu `develop` (`packages.lock.json` réécrit en DTO 551). Rejoué vert (48) sur les bons HEAD, puis rejoué de nouveau après la fusion de `develop`.
  - angular n° 1 (rouge, 6) : l'arbre Angular portait déjà le code de task-402 (E2E-MAILBOX-003/004, E2E-WEDA-001 v2) contre le backend et le catalogue de la branche task-377 d'avant fusion : rouges et parité de task-402, pas de task-377.
  - mobile après fusion, n° 1 : code 2 deux fois (outillage), restauration NuGet en 401 sur le DTO 551.0.0 hors cache ; levé par `dotnet restore` avec `GH_TOKEN` (cf. mémoire), puis vert.
  - angular après fusion, n° 1 (vert, 59 + 1 flaky) : **E2E-BIO-002 (Angular), test de cette task, instable** : `response.json()` sur la réponse interceptée, corps déjà libéré par le navigateur (même signature au passage précédent). Test corrigé (total relu par `OtherDevice.pendingBiologyTotal()`), voie rejouée : 60 verts, 0 flaky. Convention `corps-de-reponse-libere` ajoutée, ligne au registre des flaky.
- Écrans modifiés sans spec e2e modifié : aucun.
- À signaler : la divergence E2E-MAILBOX-002 [angular] (task-395) est marquée « **à retirer** » par la porte (décision humaine).

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
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
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
| E2E-MAILBOX-003 | 1 | headless | Rattacher ses boîtes depuis « Mes boîtes » — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## E2E log — premier passage (avant la décision A)

| Voie | Jouée / réutilisée | Code | Résultat | HEAD couverts |
|---|---|---|---|---|
| mobile | jouée (`npm run e2e:headless`) | 1 | suite verte : 47 verts, 0 flaky, 0 rouge ; parité de la colonne rouge (`MissingRequired` E2E-BIO-002) | api-mail `22805ea7`, client-mobile `3db7d1b9` |
| angular | jouée (`npm run e2e:mss`) | 0 | suite verte : 58 verts, 0 flaky, 0 rouge (dont E2E-BIO-002 et E2E-PATIENT-004) ; parité de la colonne verte | api-mail `22805ea7`, client-angular `056d1aa8` + arbre de la task |

- Porte : `mss.mail.e2e gate`, catalogue de la branche de la task, rapports exécutés des deux voies : **code 1**.
- Démontage : ports 5052, 8100, 4200, 3993, 3465, 3143 libres ; aucun conteneur e2e créé par le run. Deux conteneurs e2e **arrêtés depuis le 2026-10-14** (`e2e-greenmail-gcgjbrzp`, `e2e-dovecot-kgrndjwd`) préexistent, hors de ce run, non touchés.
- Écrans modifiés sans spec e2e modifié : aucun (les specs Angular sont modifiées).
- Motif du blocage : **parité**, pas une régression. Arbitrage humain : `questions/task-377.md`.
- À signaler : la divergence E2E-MAILBOX-002 [angular] (task-395) est marquée « **à retirer** » par la porte, le client étant revenu à la version du catalogue.

**E2E : ROUGE** — 1 motif(s) de blocage.

**Bloquant** (1) :

- [mobile] parité MissingRequired : E2E-BIO-002 (« La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages ») est requis pour mobile mais absent de sa suite, ou non joué.

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
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ⛔ non joué |
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

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : ROUGE** — 1 écart(s) :

- `MissingRequired` [mobile] E2E-BIO-002 (« La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages ») est requis pour mobile mais absent de sa suite, ou non joué.


## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/322 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/112 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Code de la task commité par l'humain sur `feature/nova-mss-weda-integration` (« Task 377 », `d87a30ce`, merge `fcab4f67`). Reste non commité (stabilisation du test E2E-BIO-002, `/e2e`) :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 4 suggestions.

Validation (`/review`, branches fusionnées avec `origin/develop`, qui porte task-402) :

| Repo | Build | Tests |
|---|---|---|
| api-mail `5e6f34e8` | ✓ | ✓ 7 017 (16 ignorés, comme en baseline), 0 échec, aucun crash |
| client-mobile `cfbce70` | ✓ `npm run build` | ✓ 1 322/1 322 |
| client-angular `fcab4f67` + 2 fichiers e2e | ✓ `nx build weda2` | ✓ `nx test mss-lib` 1 339/1 339 (121 fichiers) |

### Règle 1b — comportement → test d'intégration → preuve du rouge

| Comportement atteignable par un endpoint | Test d'intégration (`UseCases/MailListSourcesEndToEndTests`) | Rouge |
|---|---|---|
| `GET biology-acks/pending-mail-uids/page` : pages des résultats en attente, du plus récent au plus ancien, total | `SixtyPendingMails_AreServedOnTwoPages_TheSecondHoldingTheTenOldest` | 404 avant la route ; mutation « `Skip` retiré » → `Collections differ` |
| Un résultat acquitté quitte les pages | `AResolvedResult_LeavesThePendingPages` | 404 avant la route |
| Filtre par dernier geste | `ThePendingPages_FilteredByLastAction_KeepOnlyTheMatchingResults` | 404 avant la route |
| Page hors bornes → 400 problem+json | `AnInvalidPage_Is400ProblemJson` (×3) | 404 avant la route |
| `POST patients/mails` : pages des mails du patient, handle dans le corps | `ThePatientMails_HaveASecondPage_AndTheHandleIsNeverInThePath` | 405 avant la route ; mutation « page forcée à 0 » → `Expected: 10, Actual: 20` |
| Handle inconnu → 404, handle vide → 400 | `AnUnknownPatientHandle_Is404ProblemJson`, `AMissingPatientHandle_Is400ProblemJson` | 405 avant la route |

### Par fichier

- api-mail `PageQuery.cs` — ✅ bornes partagées, 400 par `ValidationException` (règle 12).
- api-mail `BiologyAcksController.cs` — ✅ extraction de `LoadPendingMailUidsAsync` sans changement de la route existante. ⚠️ `(page - 1) * pageSize` déborde pour un `page` démesuré (renvoie alors la 1ʳᵉ page au lieu d'une page vide, sans risque) ; la liste en attente est chargée en entier puis découpée en mémoire (bornée par les résultats en attente d'un dossier).
- api-mail `PatientsController.cs` — ✅ handle dans le corps, trace sans identifiant, `EnsurePatientExistsAsync` avant lecture (404).
- client-mobile `mail-state.service.ts`, `inbox.page.ts`, `inbox-biology-ack-chip` — ✅ pagination sur les résultats en attente, garde par numéro de pagination, puce éteinte au changement de dossier, auto-activation à un coup. ⚠️ la puce qui recompte pendant qu'elle est active relance la pagination (liste rechargée), acceptable.
- client-angular (commit TFS « Task 377 ») — ✅ sources de la liste dans l'état, numéro de chargement, états « indisponible » avec réessai. ⚠️ l'URL de navigation weda2 garde `?patient={handle}` (antérieure, task-035/task-184, jamais envoyée au serveur) : hors du critère « URL ajoutées », à traiter à part si souhaité.

### DoD

- [x] Build et tests verts : weda2, api-mail (et client-mobile)
- [x] Intégration, liste paginée des résultats en attente : 60 sur deux pages, page 2 = 10 plus anciens, vu rouge
- [x] Intégration, mails d'un patient par handle dans le corps : page 2, handle absent du chemin, vu rouge
- [x] Tests unitaires et de composant rouges d'abord : puce page 3, changement de dossier pendant une recherche, vue patient 60 s, « Version précédente » sans volet, tuile « indisponible » (Angular M1–M6 ; mobile M1–M4)
- [x] Scénario E2E-BIO-002 ajouté — angular **et mobile requis** (la puce existe sur mobile, avec le même défaut ; corrigé sur décision humaine, option A)
- [~] Scénario E2E-PATIENT-001 versionné → **remplacé par E2E-PATIENT-004** (angular requis, mobile non-applicable : le mobile n'a pas cet écran). Écart signalé, sans objection de l'humain : **à confirmer au HAG**
- [x] Trou du filet : ligne task-377 dans `conventions/e2e.md`
- [x] Aucun handle patient, INS ni contenu dans les URL et journaux ajoutés

## Timings

*(généré par `tools/timing/report.sh --task task-377 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /develop | ok | 18 min 05 s | 1 (8.0 s) | 2 (30 s) | — | client-mobile 1B/2T, relance mobile (option A) : 855053a pousse ; entrees du matin perdues lors de la synchro du plan de controle |
| /lint-mobile | ok | 1 min 09 s | — | — | — | 0 erreur, 0 warning |
| /e2e | ok | 56 min 25 s | — | — | — | e2e ×9 (51 min 32 s), mobile 50, angular 60, porte verte apres fusion develop ; BIO-002 angular stabilise |
| /review | ok | 8 min 08 s | 3 (36 s) | 3 (5 min 24 s) | — | api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T, APPROVED, PR api-mail #322, mobile #112 |
| /tech-writer | ok | 44 s | — | — | — | E009 v1.118 |
| **Total cycle** | | **1 h 24 min** | **4 (44 s)** | **5 (5 min 54 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (45 s), restore ×1 (3.2 s)
