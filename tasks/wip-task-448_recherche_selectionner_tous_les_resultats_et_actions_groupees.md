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

## Lint mobile log

- skipped — `client-mobile` absent des `**Repos**`.

## Timings

*(généré par `tools/timing/report.sh --task task-448 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 7.8 s | — | — | — | — |
| /develop | ok | — | 8 (1 min 07 s) | 9 (8 min 47 s) | — | dtos-mss 1B/0T, api-mail 5B/6T, client-angular 2B/3T, no start marker |
| /sonar | ok | 1 h 28 min | 2 (54 s) | 11 (1 h 16 min) | 4 (1 min 24 s) | 2 itération(s), api-mail 2B/11T |
| /lint-angular | en cours | — | — | — | — | — |
| **Total cycle** | | **1 h 28 min** | **10 (2 min 01 s)** | **20 (1 h 25 min)** | **4 (1 min 24 s)** | |

Autres commandes mesurées : lint ×1 (9.7 s), nuget-wait ×1 (24 s), restore ×1 (23 s)
