# todo-task-448.md — Recherche : sélectionner tous les résultats et actions groupées

**Repos**: api-mail, dtos-mss, client-angular
**Dependencies**: done-task-445 (mode résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Le médecin trie sa boîte à partir d'une recherche :
« tous les messages de ce laboratoire, marqués lus et archivés » en un geste.

> **Origine.** Analyse du 2026-11-10 (case « tout sélectionner » d'Outlook, « sélectionner les N conversations
> correspondant à cette recherche » de Gmail). Décision de l'humain du 2026-11-10 : actions groupées limitées à
> marquer lu ou non lu, étoile, déplacer, supprimer (mise à la corbeille). **Hors lot, par sécurité clinique** :
> l'acquittement de biologie en masse (acquitter atteste que le médecin a pris connaissance de **chaque** résultat) et
> le rattachement en masse à un patient (risque d'identito-vigilance).

## Ce qui est établi

- weda2 a un mode sélection dans la liste (`mail-list.component`) avec « Tout », Lu, Non lu, Favori, Déplacer : il ne
  porte que sur les messages **chargés** à l'écran.
- La règle 14 impose que chaque acte sur un message soit imputé à la personne réelle.

## Objective

Dans le mode « Résultats de recherche », le médecin sélectionne tous les résultats, y compris ceux qui ne sont pas
encore chargés, et leur applique une action groupée.

Règles :
- **Case « Tout sélectionner »** dans l'en-tête des résultats : elle sélectionne les résultats chargés, puis propose
  « Sélectionner les N résultats de la recherche » (N = total rendu par le serveur).
- **Actions** : Marquer comme lu, Marquer comme non lu, Ajouter ou retirer l'étoile, Déplacer vers un dossier,
  Supprimer (mise à la Corbeille). La suppression définitive n'est pas proposée.
- **Confirmation explicite** quand l'action porte sur plus de messages qu'il n'en est chargé, ou sur plus de 50
  messages : « Déplacer 342 messages vers Archives ? ».
- **Périmètre figé** : l'action porte exactement sur les résultats comptés au moment de la confirmation ; un message
  arrivé depuis n'est pas concerné.
- **Plafond** : 2 000 messages par action ; au-delà, le médecin est invité à affiner sa recherche.
- **Progression et compte rendu** : une barre de progression au-delà de 100 messages ; à la fin, « 340 messages
  déplacés, 2 en échec », avec la possibilité de réessayer les échecs. Une action partielle n'est jamais présentée comme
  complète.
- Après l'action, la recherche est relancée (un message déplacé hors portée ou à la Corbeille disparaît des résultats).
- **Règle 14** : chaque message touché est tracé **individuellement**, au nom de la personne qui a agi (RPPS, nom PSC,
  rôle), avec l'action et l'objet. Un délégataire ou un membre agit comme le titulaire, et la trace le dit.

### Hors périmètre

- Acquittement de biologie en masse, rattachement en masse à un patient, suppression définitive : exclus par décision
  de l'humain.
- Le mobile : task-451.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`, weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`
- [ ] Tests unitaires du service d'action groupée : chaque action, plafond, échecs partiels, périmètre figé (≥ 1 test par
      branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b)** sur la route d'action groupée, lus dans la réponse réelle et en
      base, chacun vu rouge par mutation :
      - 120 résultats (plus d'une page) déplacés vers « Archives » : les 120 sont dans « Archives », aucun autre message
        n'a bougé ; la réponse compte 120 succès ;
      - marquer lu : les 120 portent le drapeau lu ;
      - un message supprimé entre la confirmation et l'exécution : 119 succès, 1 échec nommé, aucune erreur globale ;
      - **périmètre figé** : un message correspondant arrivé après la confirmation n'est pas déplacé ;
      - **cas d'échec** : 2 001 messages → 400 en `ProblemDetails`, rien n'est modifié ; boîte sans verdict de
        l'opérateur → refus, rien n'est modifié
- [ ] **Test d'intégration règle 14** : deux personnes rattachées à la même boîte (titulaire et délégataire) ; le
      délégataire déplace 3 résultats ; la trace porte **3 entrées au nom du délégataire** (RPPS, nom, rôle
      « délégataire »), aucune au nom du titulaire ni de la boîte
- [ ] Contrat `dtos-mss` publié (rétrocompatible) et consommateurs .NET mis à jour ; types TypeScript de weda2 alignés
- [ ] Tests de composant weda2 : « Tout sélectionner » puis « Sélectionner les N résultats », confirmation, progression,
      compte rendu partiel, relance de la recherche ; chacun vu rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-012` v1 : « Traiter tous les résultats d'une recherche » — attendu : après
      « Sélectionner les N résultats » et confirmation, les N messages sont marqués lus, y compris ceux qui n'étaient pas
      chargés. Clients : angular requis, mobile requis avec **divergence temporaire** (raison : « la sélection de tous
      les résultats arrive sur le mobile avec la refonte mobile », tache : task-451). Implémenté dans weda2, vu rouge
      par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté
- [ ] Évènements PGSSI-S journalisés : une trace par message et par action, au nom de la personne réelle
- [ ] Aucune donnée de santé en clair dans les logs (objets, expéditeurs, termes)
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : une action groupée trace chaque objet touché
      au nom de son auteur, et rend le détail de ses échecs

## Manual Test Plan

1. Lancer le backend sur le corpus fictif : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de référence. Lancer
   weda2 : `cd Client/Angular/front && npm start`.
2. Rechercher l'expéditeur d'un laboratoire du corpus (plus de 50 messages).
3. Cocher « Tout sélectionner », puis « Sélectionner les N résultats de la recherche ».
4. Cliquer « Marquer comme lu » : une confirmation annonce N messages. Confirmer : progression, puis « N messages
   marqués comme lus ».
5. « Fermer la recherche », ouvrir la Boîte de réception : les messages du laboratoire, y compris les plus anciens, sont
   lus.
6. Rechercher à nouveau, tout sélectionner, « Déplacer » vers « Archives » : ils disparaissent des résultats en portée
   « Dossier courant » et apparaissent dans « Archives ».
7. Se connecter avec la carte du délégataire, déplacer 3 résultats ; ouvrir le journal de la boîte : 3 entrées au nom du
   délégataire.
8. Vérifier qu'aucune action « Acquitter » ni « Rattacher à un patient » n'est proposée en sélection.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la messagerie
- **Exigences DSR honorées** : non applicable — l'imputabilité des actes suit la PGSSI-S (référentiel d'imputabilité)
  et la règle 14 de la plateforme
- **INS** : non applicable — aucun rattachement patient en masse (exclu)
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : verdict de l'opérateur MSSanté requis (règle 14) ; titulaire, délégataire et membre disposent des
  mêmes actions groupées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : une trace par message et par action (lecture marquée, étoile, déplacement, mise à la Corbeille),
  au nom de la personne réelle (RPPS, nom PSC, rôle), avec la boîte, l'instant, l'action et l'objet ; 3 653 jours ;
  visibles de toute personne rattachée à la boîte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte et serveur IMAP de l'opérateur, inchangés
- **AIPD / impact RGPD** : inchangé — mêmes actions qu'à l'unité

## Branches

- `api-mail` (pushed) : feat/task-448-recherche-selectionner-tous-les — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-448-recherche-selectionner-tous-les
- `dtos-mss` (paresseuse) : créée par `/develop` au premier changement de contrat (même nom).
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

**Ordre** : dtos-mss → api-mail → client-angular (code-only, `feature/nova-mss-weda-integration`, aucun commit).

### dtos-mss (branche paresseuse `feat/task-448-recherche-selectionner-tous-les`, publié **592.0.0**)

- `MailKeyDto`, `BulkMailActionType` (MarkRead, MarkUnread, Flag, Unflag, Move, Trash), `BulkMailActionRequestDto`
  (`MaxItems = 2000`, validation : liste vide, plafond, déplacement sans destination), `BulkMailActionResultDto` /
  `BulkMailActionFailureDto` (`not_found`, `already_in_trash`, `failed`), `SearchKeysResponseDto`. Rétrocompatible
  (types nouveaux seulement). Consommateur .NET : api-mail bumpé (`753124f9`).

### api-mail

- `POST /api/v1/search/keys` (`SearchController.ListKeysAsync`) : la recherche affichée, rejouée sans explication
  (`SemanticSearchOptions.Explain = false` : ni patients trouvés ni extraits), 2 000 clés au plus, dans l'ordre de la
  recherche ; `IsOverLimit` quand la recherche est tronquée (`SearchResultHelper.ToKeys`).
- `POST /api/v1/mail/bulk-actions` (`BulkMailActionsController` → `BulkMailActionService`) : périmètre = la liste reçue,
  regroupée par dossier ; message absent de la base du dossier → `not_found` ; Corbeille depuis la Corbeille ou dossier
  de type inconnu → refus nommé ; chaque message passe par le **service du geste unitaire** (lu, non lu, étoile, sans
  étoile : `IEmailFlagService` ; déplacer : `BulkMoveEmailsAsync` ; Corbeille : `DeleteEmailsAsync`), qui trace un acte
  par message au nom de la personne de la requête (règle 14). Plafond vérifié dans le contrat **et** dans le service.
- Verrou de l'opérateur : la route passe par la sélection de boîte comme toutes les routes de données.

**Tests** (règle 1b, vrais contrôleurs, vraie base PostgreSQL, Dovecot) :

| Comportement | Test | Preuve rouge |
|---|---|---|
| 120 résultats déplacés vers Archives, aucun autre ; arrivé après la confirmation non déplacé | `FolderOperationsEndToEndTests.MovingThe120ConfirmedResults_…` | B1 (déplacement non fait), B2 (périmètre relu à l'exécution : 122 au lieu de 120) |
| Marquer lu : les 120 lus en base, aucun autre | `MarkingThe120ConfirmedResultsRead_…` | B3 (lu ↔ non lu) |
| Message supprimé entre-temps : 119 + 1 `not_found` nommé | `AResultDeletedBetweenTheConfirmationAndTheAction_…` | B4 (absent non nommé : 120 au lieu de 119) |
| 2 001 messages → 400 `problem+json`, rien modifié | `MoreThan2000Messages_Is400ProblemJson_…` | rouge sur le code d'avant (route absente → 404) ; plafond du service prouvé en unitaire |
| Règle 14 : délégataire déplace 3 → 3 `MailMove` au nom du délégataire (RPPS, nom, rôle), aucun autre | `TheDelegateMovesThreeResults_…` | B5 (déplacement sans trace par message) |
| Délégataire refusé par l'opérateur → 403, rien touché ; le titulaire agit | `MailboxAccessLockIntegrationTests.Delegate_RefusedAtRenewal_Gets403_OnABulkAction_…` | rouge sur le code d'avant (route absente) |
| Clés de 120 résultats au-delà de la première page, dans l'ordre de la recherche, dossier filtré | `SearchKeysEndpointIntegrationTests.Keys_Of120Results_…` | K1 (clés plafonnées à la page) |
| 2 001 résultats → 2 000 clés, `IsOverLimit` | `Keys_OfMoreResultsThanAnActionCovers_…` | K2 (troncature ignorée) |
| Requête vide → 400 `problem+json` | `Keys_OfAnEmptyQuery_Is400ProblemJson` | rouge sur le code d'avant (route absente) |

- Unitaires : `BulkMailActionServiceTests` (16, puis 20 après `/sonar` : chaque action par son geste unitaire, déplacement par dossier, même
  dossier, Corbeille, refus depuis la Corbeille, dossier inconnu, `not_found`, refus partiel, refus serveur
  déplacement / Corbeille, doublons, plafond, plafond exact) ; `SearchResultHelperTests.ToKeys_*` (4).
- **Simplification issue d'une mutation survivante** : K2 initial (« un résultat de plus que le plafond ») a survécu :
  la recherche dit déjà qu'elle est tronquée. `MaxResults = MaxItems` (le `+ 1` était redondant), et la mutation qui
  ignore la troncature est rouge.
- Build : 0 erreur, 0 avertissement.
- Suite complète `HealthPlatform.Api.Mail.sln` (`97eeb727`) : domain 210, application 4 213, infrastructure 743, api 1 376,
  integration 1 256 (+16 ignorés) ✅, **sauf 3 rouges « du jour »** (`GetFolderTodayAsync…`, `GetFolderNotSeenTodayAsync…`,
  `FilterTodayEmails…`) : suite jouée à 00:1x, fenêtre minuit connue (Dovecot compare `SINCE` en UTC, mémoire
  `integration-tests-du-jour-fenetre-minuit`), sans lien avec la task. Rejoués après 01:00 (voir `## Sonar log`).

### client-angular (weda2, code-only)

- `core/models/bulk-mail-action.model.ts` (types du contrat), `MssApiService.searchKeys` / `executeBulkMailAction`.
- `MailSearchBulkService` (+ `mail-search-bulk-labels.ts`) : « Tout sélectionner » coche les résultats chargés puis
  compte ceux de la recherche (`/search/keys`) s'il en reste à charger ; « Sélectionner les N résultats de la
  recherche » ; plafond 2 000 (« affinez la recherche ») ; confirmation au-delà de ce qui est chargé ou de 50 ;
  périmètre figé à la demande ; envoi par morceaux de 100 ; progression au-delà de 100 ; compte rendu
  (« 340 messages déplacés vers Archives, 2 en échec »), un morceau refusé en bloc nomme ses messages ; « Réessayer
  les échecs » (refus du serveur seulement) ; recherche relancée, compteurs des dossiers relus.
- `MailSearchBulkComponent` dans l'en-tête des résultats ; la barre de sélection de la liste passe par le service en mode
  recherche (lu, non lu, favori, **sans étoile** — nouveau, aussi en mode dossier —, déplacer, supprimer = Corbeille).
  Ni acquittement ni rattachement en sélection.
- Tests de composant `mail-list.search-bulk.spec.ts` (15, à travers la liste) : mutations F1–F12 toutes rouges
  (décompte, choix, confirmation, périmètre figé, morceaux, progression, refus en bloc, nouvel essai, relance,
  compte rendu partiel, liste qui ignore la recherche, Corbeille).
- E2E `E2E-SEARCH-012` v1 (catalogue : angular requis, mobile en divergence task-451) : pages de 4, N résultats
  sélectionnés, confirmation « Marquer N messages comme lus ? », chacun lu côté serveur ; état des seeds rétabli.
  Mutations servies E1 (le client envoie « non lu » en annonçant « lu » → rouge sur la lecture serveur), E2 (choix
  sans effet → rouge), marqueurs vérifiés dans le bundle puis retirés.
- `nx test mss-lib` 1 625 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅.

### Passe qualité (§Q)

- weda2 : `allLoadedSelected` calculé une fois dans le service, relu par le composant (doublon retiré) ; libellés sortis
  du service (fichier < 500 lignes). api-mail : `MaxResults + 1` redondant retiré (ci-dessus). Pas de commit séparé.

### Prévention (règle d'or)

- `conventions/csharp.md` § `action-groupee-tracee-par-objet`.
- Défaut **antérieur** relevé, hors périmètre : les routes `…/emails/bulk/status/read|unread|flagged|unflagged` ne
  tracent pas message par message (règle 14). Task de suivi recommandée.

### Reprise après `/review` (2026-11-12) — B1, B2, S5, S6, S8

S1 et S4 restent en arbitrage humain (`questions/task-448.md`), hors de cette reprise.

- **B1** — « marquer non lu » trace désormais un `MailFlagChange` par message (`EmailFlagService.UpdateEmailUnReadStatusAsync`,
  comme l'étoile), au nom de la personne. Défaut antérieur du geste unitaire : la route unitaire en profite aussi.
- **S5** — une Corbeille refusée parce que la liste des dossiers n'a jamais enregistré le type du dossier rend
  `folder_type_unknown` (dtos-mss : documentation du code, publié **593**, api-mail bumpé). Le client ne le propose pas
  au nouvel essai (déjà le cas : seul `failed` est retenté ; type TS complété).
- **S6** — la confirmation en attente porte la recherche pour laquelle elle a été demandée ; une nouvelle recherche
  l'efface (`MailSearchBulkService.pending` calculé), et « Confirmer » n'agit plus sur l'ancien périmètre.
- **S8** — commentaire de `SearchResultHelper.ToKeys` corrigé (plus de « un résultat de plus »).

**Tests d'intégration** (règle 1b, vraie pile, `FolderOperationsEndToEndTests.BulkActions`) :

| Comportement | Test | Preuve rouge |
|---|---|---|
| Délégataire : 3 résultats mis à la Corbeille, présents dans `Trash`, 3 `MailDelete` à son nom (le type des dossiers est bien enregistré par la liste) | `TheDelegateTrashesThreeResults_…` | C2 (Corbeille non faite), C3 (Corbeille sans trace) |
| Corbeille → Corbeille : `already_in_trash`, messages **toujours sur le serveur** | `TrashingResultsAlreadyInTheTrash_…` | C1 (garde retirée : les 2 messages détruits) |
| Dossier jamais listé : `folder_type_unknown`, message resté | `TrashingFromAFolderTheListingNeverRecorded_…` | rouge sur le code d'avant (`failed`) |
| Étoile / sans étoile / non lu : état en base + 1 `MailFlagChange` par message au nom du délégataire (`[Theory]`) | `TheDelegateChangesTheStateOfThreeResults_…` | non lu : rouge sur le code d'avant (0 trace) et C6 ; C4 (étoile inversée), C5 (sans étoile inversée) |
| Résultats de deux dossiers mis à la Corbeille d'une action | `TrashingResultsFromTwoFolders_…` | C2, C7 (un seul dossier : 2 + 2 `not_found`) |

- Unitaires : `EmailFlagServiceTests.UpdateEmailUnReadStatusAsync_EmitsMailFlagChangeAudit_…` ;
  `BulkMailActionServiceTests` (raison `folder_type_unknown`).
- weda2 : `mail-list.search-bulk.spec.ts` + 2 tests (nouvelle recherche efface la question ; type inconnu non retenté),
  mutations F13 et F14 rouges. `nx test mss-lib` 1 627 ✅, `nx test weda2` 2 683 ✅, `nx build weda2` ✅.
- Passe qualité (§Q) : diff minimal, aucun cleanup.
- **Prévention** : `conventions/csharp.md` § `action-groupee-tracee-par-objet` complété — réutiliser un geste unitaire
  ne prouve pas qu'il trace (journal lu pour **chaque** action exposée) ; un refus non rejouable a sa propre raison.

## Sonar log

- Mode A (chaîné), branche `feat/task-448-recherche-selectionner-tous-les`, serveur 9.9.8 (`sonar.login`).
- Analyse 1 (`97eeb727`) : `ANALYSIS SUCCESSFUL`. **1 issue nouveau code** : S3218 (`FolderOutcome.Failed` masquait la
  constante `Failed`) → propriétés renommées `Touched` / `Failures`. Trous de couverture de la task comblés : quatre
  branches du service (dossier vidé entre-temps, action inconnue, déplacement refusé par résultat, Corbeille refusée)
  et les branches `ModelState` invalide des deux contrôleurs (`BulkMailActionsControllerTests`,
  `SearchControllerTests.ListKeys_*`).
- **Défaut de test trouvé par la suite instrumentée** : `TheDelegateMovesThreeResults…` rouge en suite complète, vert seul.
  Cause : canal d'audit de la fixture borné (1 000) et sans consommateur, rempli par les tests à 120 messages. Reproduit
  sur la seule collection `UseCases`, corrigé (`ForgetTraces()`), collection verte. Prévention :
  `conventions/csharp.md` § `canal-d-audit-borne-de-la-fixture` + mémoire.
- Analyse 2 (`93c8435b`) : `ANALYSIS SUCCESSFUL`, 5 passes OpenCover vertes (integration 1 255, dont les 3 tests « du
  jour » rejoués après 01:00 : verts). 4 tests PgBouncer ignorés (fixture PgBouncer indisponible, ignorés par
  conception), sans lien avec la task.
- Itérations : 2 (Phase 1). Phase 2 (legacy) : rien à traiter (0 smell).
- **Reprise après revue** — analyse 3 (`4350bc8a` + lock files) : `ANALYSIS SUCCESSFUL`, 5 passes OpenCover vertes
  (integration 1 266, 16 ignorés), Quality Gate **OK**, **0 issue nouveau code**, couverture nouveau code 96,3 %. Rien à
  corriger (1 itération). KPIs inchangés ci-dessous.

### KPIs qualité (baseline → final)

| KPI | Baseline | Final |
|---|---|---|
| Quality Gate | OK | **OK** |
| Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 |
| Code Smells | 0 | 0 |
| Coverage | 97,8 % | 97,8 % |
| Duplication | 0,4 % | 0,4 % |
| Reliability / Security / Maintainability | A / A / A | A / A / A |
| New code — issues | — | 0 (1 corrigée) |
| New code — coverage | — | 96,3 % |

## Lint log

- client-angular (code-only, `feature/nova-mss-weda-integration`, aucun git) : `npx nx run-many -t lint
  --projects=mss-lib,mss-e2e` (contournement task-367).
- **0 erreur** ; avertissements 52 (`mss-lib`) + 48 (`mss-e2e`), identiques à la base de task-446 : aucun introduit.
- Itérations : 0. Build et tests déjà verts sur l'arbre final (fin de `/develop`, après la passe qualité).
- **Reprise après revue** : relancé sur l'arbre repris — **0 erreur**, 52 + 48 avertissements (inchangés). Itérations : 0.

## Lint mobile log

- skipped — `client-mobile` absent des `**Repos**`.

## E2E log

| Voie | Jouée / réutilisée | Résultat | Dépôts couverts |
|---|---|---|---|
| mobile | jouée (reprise après revue) | 60 verts, 0 flaky, 0 rouge, parité verte | api-mail `4350bc8a` + lock files, client-mobile `develop` |
| angular | jouée (reprise après revue) | 81 verts (dont E2E-SEARCH-012), 0 flaky, 0 rouge, parité verte | api-mail `4350bc8a` + lock files, dtos 593, client-angular (arbre non commité), Client/Mobile/e2e |

Porte : catalogue de la branche de la task (`Api/Mail/e2e/scenarios.yml`, E2E-SEARCH-012 v1). Démontage vérifié : ports
libres, aucun conteneur e2e résiduel.

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
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

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

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/363 (label `awaiting-human-merge`)
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/62 (label `awaiting-human-merge`)
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-mss-weda-integration`. Fichiers modifiés :
  - modifiés : `front/e2e/mss-e2e/specs/functional.e2e.ts`, `front/e2e/mss-e2e/support/e2e-backend.ts`, `front/libs/mss/src/core/services/mss-api.service.ts`, `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.{html,ts,spec.ts}`, `mail-list.gestures.spec.ts`, `mail-list.list-sources.spec.ts`, `mail-list.search-mode.spec.ts`, `mail-search-results/mail-search-results.component.{html,ts}`, `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - nouveaux : `core/models/bulk-mail-action.model.ts`, `mail-list.search-bulk.spec.ts`, `components/mail-search-bulk/*` (html, scss, ts), `services/mail-search-bulk.service.ts`, `services/mail-search-bulk-labels.ts`

## Code Review Summary

**APPROVED** (passage 2, après reprise de `/develop`, 2026-11-12) — 0 bloquant.

Les deux bloquants du passage 1 sont corrigés et prouvés sur la vraie pile :

| Comportement | Test d'intégration | Preuve rouge |
|---|---|---|
| 120 résultats déplacés vers Archives, périmètre figé | `MovingThe120ConfirmedResults_…` | B1, B2 (mutations) |
| Marquer lu : les 120 lus en base | `MarkingThe120ConfirmedResultsRead_…` | B3 |
| Message supprimé entre-temps : 119 + `not_found` | `AResultDeletedBetweenTheConfirmationAndTheAction_…` | B4 |
| 2 001 messages → 400 `problem+json` | `MoreThan2000Messages_Is400ProblemJson_…` | route absente avant |
| Délégataire : 3 déplacements à son nom | `TheDelegateMovesThreeResults_…` | B5 |
| Délégataire refusé par l'opérateur → 403 | `MailboxAccessLockIntegrationTests.Delegate_RefusedAtRenewal_Gets403_OnABulkAction_…` | route absente avant |
| Clés de 120 résultats / plafond / requête vide | `SearchKeysEndpointIntegrationTests.*` | K1, K2, route absente avant |
| **Corbeille** par le délégataire : dans `Trash`, 3 `MailDelete` à son nom | `TheDelegateTrashesThreeResults_…` | C2, C3 |
| **Corbeille → Corbeille** : `already_in_trash`, messages toujours sur le serveur | `TrashingResultsAlreadyInTheTrash_…` | C1 (garde retirée : messages détruits) |
| Dossier au type jamais enregistré : `folder_type_unknown` | `TrashingFromAFolderTheListingNeverRecorded_…` | rouge sur le code d'avant |
| **Étoile / sans étoile / non lu** : état en base + 1 trace par message au nom du délégataire | `TheDelegateChangesTheStateOfThreeResults_…` (`[Theory]`) | non lu : 0 trace avant (B1), C4, C5, C6 |
| Résultats de **deux dossiers** | `TrashingResultsFromTwoFolders_…` | C2, C7 |

- `EmailFlagService` : « marquer non lu » trace un `MailFlagChange` par message (défaut antérieur, corrigé aussi pour la route unitaire). ✅
- `BulkMailActionService` : raison `folder_type_unknown`, non proposée au nouvel essai. ✅
- weda2 `MailSearchBulkService` : la question en attente est liée à la recherche, une nouvelle recherche l'efface. ✅ (F13, F14 rouges)

**Suggestions non bloquantes**
- S2/S3 : comptes rendus optimistes dans des cas limites (déplacement vers le dossier même compté comme succès, message déjà effacé compté comme mis à la Corbeille, morceaux restants abandonnés si le médecin quitte la vue).
- S7 : ~4 allers-retours SQL par message pour les drapeaux (bornés par morceaux de 100) — acceptable en v1.
- S9 : `TraceFlagChange` écrit « OK flags updated » alors que la propagation est différée (antérieur, aussi pour l'étoile) ; « marquer lu » écrit déjà « queued for background propagation ».
- Défaut antérieur hors périmètre : les routes `…/emails/bulk/status/read|unread|flagged|unflagged` ne tracent pas message par message → task de suivi.

> 🧑‍⚖️ **Arbitrage humain ouvert (à trancher au HAG, `questions/task-448.md`)**
> - **S1** — une remise en « lu » groupée trace `MailRead`, qui atteste un **accès** au message : 2 000 résultats marqués lus = 2 000 attestations d'accès. Recommandation forge : `MailFlagChange`.
> - **S4** — « tous les résultats » inclut les résultats **proches par le sens** : une Corbeille groupée peut toucher des messages sans les mots cherchés. Recommandation forge : limiter l'action aux résultats exacts en v1.

Validation (passage 2) : api-mail build 0 erreur / 0 avertissement, domain 210, infrastructure 743, api 1 380, application 4 218, integration 1 266 (16 ignorés), 0 échec ; dtos-mss build vert ; weda2 `mss-lib` 1 627, `weda2` 2 683, `nx build weda2` vert ; `/e2e` vert (mobile 60, angular 81, parité verte) ; Sonar QG OK, 0 issue nouveau code.

### Passage 1 (historique)

**CHANGES REQUESTED** (revue indépendante, passage 1, 2026-11-12) — 2 bloquants, détail dans `questions/task-448.md`.

- Validation : api-mail build 0 erreur et suite verte (`93c8435b`, analyse Sonar) ; weda2 `mss-lib` 1 625, `weda2` 2 683,
  build vert ; `/e2e` vert (mobile 60, angular 81, parité verte).
- B1 : « Marquer non lu » ne trace rien (`EmailFlagService.UpdateEmailUnReadStatusAsync`), défaut antérieur multiplié
  par l'action groupée (règle 14).
- B2 : Corbeille et refus « Corbeille depuis la Corbeille », étoile, sans étoile, non lu, plusieurs dossiers : pas de
  test d'intégration sur la vraie pile (règle 1b).
- À corriger dans la reprise : S5 (raison non réessayable), S6 (confirmation effacée au changement de recherche),
  S8 (commentaire de `ToKeys`).
- Arbitrage humain : S1 (lu groupé tracé comme accès), S4 (résultats proches par le sens inclus dans « tous »).

## Timings

*(généré par `tools/timing/report.sh --task task-448 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 7.8 s | — | — | — | — |
| /develop | ok | 15 min 37 s | 12 (1 min 58 s) | 13 (16 min 26 s) | — | dtos-mss 1B/0T, api-mail 8B/9T, client-angular 3B/4T, reprise après revue : B1 B2 S5 S6 S8 |
| /sonar | ok | 8 min 26 s | 3 (1 min 14 s) | 16 (1 h 23 min) | 6 (2 min 07 s) | 1 itération(s), api-mail 3B/16T, reprise : QG OK, 0 issue |
| /lint-angular | ok | 19 s | — | — | — | reprise : 0 erreur |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 19 min 32 s | — | — | — | e2e ×10 (1 h 15 min), reprise : mobile 60, angular 81, parité verte |
| /review | ok | 7 min 57 s | 5 (35 s) | 5 (13 min 43 s) | — | api-mail 2B/2T, client-angular 2B/3T, dtos-mss 1B/0T, APPROVED (passage 2), PRs api-mail #363, dtos-mss #62 |
| /tech-writer | ok | 37 s | — | — | — | — |
| **Total cycle** | | **52 min 41 s** | **20 (3 min 48 s)** | **34 (1 h 53 min)** | **6 (2 min 07 s)** | |

Autres commandes mesurées : lint ×2 (19 s), nuget-wait ×2 (47 s), restore ×2 (26 s)

## Merged

Mergée le 2026-11-12 par `/merge task-448 --i-tested` (validation humaine, HAG).

Avant le merge, la PR `api-mail` #363 était en conflit avec `develop` (task-453, #364, mergée entre-temps) :
chaque task avait publié son paquet DTO (593 pour task-448, 591 pour task-453), aucun ne portant les contrats de
l'autre. Resynchronisation : branche DTO de task-448 fusionnée avec `develop` et republiée en **597.0.0**,
`api-mail` fusionnée avec `develop` sur 597, lock files régénérés, constante `Archives` déclarée deux fois dans
la classe partielle `FolderOperationsEndToEndTests` dédoublonnée. Build vert, 7 867 tests verts (0 échec).

| Repo | PR | Commit squash | CI `develop` |
|---|---|---|---|
| `dtos-mss` | #62 | `ca6f3ff` | ✅ [run 599](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/43193359761) |
| `api-mail` | #363 | `7c054c3e` | ✅ [run 948](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/43193383654) |
| `client-angular` | — | — | géré manuellement par l'humain |
