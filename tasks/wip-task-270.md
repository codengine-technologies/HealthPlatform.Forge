# todo-task-270.md — La recherche de dossier ne repaie plus 5 allers-retours IMAP à chaque cache-miss

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

L'appel `folder` (`GET /mail/folders/{name}`) est le **premier poste du
dashboard** — 63 % de son temps serveur (3 899,7 s au palier 500 de la campagne
du 2026-08-23), et le dashboard est lui-même le deuxième poste global (23,1 %).
Vert au SLO, mais gros consommateur : le point aveugle que task-262 a
instrumenté précisément pour rendre cette US possible.

**Le seuil de reprise fixé par task-262 est franchi, et chiffré.** Le compteur
de sollicitations (première campagne où il couvre ce chemin) donne, sur la
fenêtre du tir (`mssante_mail_server_solicitations_total`, Prometheus) :

| Opération | Commandes IMAP | Occurrences |
|---|---|---|
| `GetFolderQuery` (recherche complète) | `resolve_folder` + `open_folder` + `status_folder` + `search_folder` + `close_folder` = **5 allers-retours** | 16 283 exécutions |
| `GetFolderStatus` (chemin `today`) | `resolve_folder` + `status_folder` = 2 allers-retours | 52 749 exécutions |

La route `folder` a été appelée ~43 200 fois (dashboard + inbox) : **~38 % des
appels partent en recherche complète à 5 allers-retours** (~500 ms sous 100 ms
de latence MSSanté), les autres sont servis par le cache. C'est exactement la
bimodalité de la route : p50 127 ms / p95 698 ms — et ce p95 est **plat de 100
à 500 médecins** (696 → 699 → 698) : un coût fixe par appel, pas un effet de
charge. Le remède est donc côté **contenu de l'appel**, pas côté capacité.

**Contenu attendu** (les deux remèdes nommés par task-262, à arbitrer sur
mesure par `/develop`) :

1. **Réduire le coût d'un cache-miss** : la séquence à 5 allers-retours
   contient un `STATUS` **et** un `SEARCH` sur un dossier qu'elle vient
   d'ouvrir — examiner ce que le `SEARCH` apporte que le `STATUS` (ou l'état
   du dossier ouvert) ne donne pas déjà, et supprimer les commandes redondantes.
   Toute réduction se **prouve par le compteur de sollicitations** (c'est
   l'instrument posé pour ça), jamais par la seule latence.
2. **Réduire la part de cache-miss** : la durée de fraîcheur du cache de
   dossier est un **arbitrage produit à énoncer** — un compteur de dossier
   plus frais coûte des allers-retours, un compteur périmé ment au médecin.
   La fraîcheur choisie doit être écrite (dans le code et la task), pas
   implicite.

**Gain attendu** : passer un cache-miss de 5 à 2-3 allers-retours ≈ −200 à
−300 ms sur ~16 000 appels/campagne ≈ **−3 000 à −4 900 s de temps serveur**
(le dashboard passerait sous ~15 % du temps serveur) ; p95 du dashboard
~700 → ~400-500 ms.

**Ce qui n'est PAS dans le périmètre** : la page d'en-têtes
(`GET …/emails/{ids}`, task-194/261) ; le chemin `today` à 2 allers-retours
(déjà minimal) ; toute modification du contrat de la route.

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] Le nombre d'allers-retours IMAP d'un cache-miss de `GetFolderQuery` est
      **réduit et prouvé par le compteur de sollicitations** (test
      d'intégration : compte exact des commandes enregistrées avant/après,
      dans l'ordre — même style que les tests de task-262)
- [ ] Ce que le médecin voit est inchangé : mêmes compteurs de dossier, même
      liste — >= 1 test d'intégration sur le vrai dépôt comparant la réponse
      avant/après
- [ ] Si la durée de fraîcheur du cache change : la valeur et sa justification
      sont écrites en commentaire au point de décision, et un test fixe le
      comportement (un dossier modifié côté IMAP est vu au plus tard après
      {fraîcheur})
- [ ] Aucune régression sur le chemin `GetFolderStatus` (`today`) — ses 2
      allers-retours restent 2, prouvé par le même compteur
- [ ] Unit tests pour toute nouvelle branche (>= 1 par branche)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
- Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 10 --api http://127.0.0.1:5052`
- Appeler `GET /api/v1/mail/folders/INBOX` deux fois (identité loadtest-1,
  session stable) : relever dans Prometheus
  `mssante_mail_server_solicitations_total{operation="GetFolderQuery"}` —
  le premier appel enregistre la séquence réduite, le second est un cache-hit
  (aucune commande)
- Vérifier que la réponse JSON (compteurs, uids) est identique à celle
  d'avant le correctif sur le même seed
- **Au banc (clôture de l'US, non bloquant pour le merge)** : tir journey
  distant iso-conditions 2026-08-23 — `dashboard,call:folder` p95 < 500 ms au
  palier 500 et part du dashboard < 18 % du temps serveur

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP interne au périmètre MSSanté existant
- **Tracé PGSSI-S** : inchangé — la consultation de dossier reste journalisée à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-270-folder-imap-roundtrips` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-270-folder-imap-roundtrips
- `dtos-mss` (pushed, auto-inclus) : `feat/task-270-folder-imap-roundtrips` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-270-folder-imap-roundtrips (aucun changement de contrat attendu — la task exclut toute modification du contrat de la route)

## Develop log

**Repos touchés** : `api-mail` uniquement. `dtos-mss` : branche créée par
`/start` (auto-inclusion), **aucun commit** — la task interdit toute
modification du contrat de la route, aucun DTO n'a bougé, donc pas de publish
NuGet ni de bump consommateur.

### Le défaut, tel que le compteur de task-262 le nommait

Un appel froid de `GET /mail/folders/{name}` enchaînait **deux séquences IMAP
indépendantes**, chacune sous son propre verrou de session, dont la seconde
**recommençait par `resolve` + `STATUS`** :

| # | Commande | Opération |
|---|---|---|
| 1 | `resolve_folder` | `GetFolderStatus` |
| 2 | `status_folder` | `GetFolderStatus` |
| 3 | `resolve_folder` | `GetFolderQuery` ← **doublon** |
| 4 | `status_folder` | `GetFolderQuery` ← **doublon** |
| 5 | `open_folder` | `GetFolderQuery` |
| 6 | `search_folder` | `GetFolderQuery` |
| 7 | `close_folder` | `GetFolderQuery` |

Le `SEARCH` n'est pas redondant — c'est la seule commande qui rend la liste
d'UIDs. Le `STATUS` l'est : celui de `GetFolderQuery` refaisait, quelques
millisecondes plus tard, la mesure que `GetFolderStatus` venait de prendre.

### Remède 1 — les deux séquences fusionnent (7 → 5)

`ReadFolderAsync` est désormais **le** passage IMAP d'une lecture de dossier :
`resolve` + `STATUS` une fois (le plancher, inchangé), puis
`SELECT` + `SEARCH` + `CLOSE` **seulement si** les compteurs frais démentent la
liste d'UIDs déjà en cache. Un verrou de session au lieu de deux.

L'opération `GetFolderQuery` passe donc de **5 commandes à 3** ; l'appel froid
complet de **7 à 5**.

### Remède 2 — « reçus aujourd'hui » ne jette plus une recherche encore valide

Dès que la fenêtre de `folder:status` (10 s) se refermait, l'entrée
`folder:query` — pourtant vivante 5 min — était **jetée** et la recherche
refaite à 5 allers-retours. Elle est maintenant confrontée à un `STATUS` frais
(2 allers-retours) : si `(Count, UidNext)` n'a pas bougé, le dossier n'a pas
bougé, donc l'ensemble des messages reçus dans la journée non plus.

### La fraîcheur retenue — arbitrage explicite

**Aucun TTL n'est modifié.** Ce qui change est la manière de démontrer la
fraîcheur, pas sa durée :

| Ce qui est rendu | Fraîcheur | Comment elle est démontrée |
|---|---|---|
| `Count`, `UnreadCount`, `UidNext` | **l'instant de l'appel** | `STATUS` de l'appel courant — jamais le cache |
| liste d'UIDs de `folder` (route `folder`) | jusqu'à 5 min (`folder:uids`) | confirmée par le `STATUS` frais — comportement **inchangé** |
| liste d'UIDs « reçus aujourd'hui » | jusqu'à 5 min (`folder:query`) | confirmée par le `STATUS` frais — **nouveau** (elle était jetée à 10 s) |
| liste d'UIDs « non lus » | **10 s** (`folder:status`) | **inchangé, volontairement strict** |

L'asymétrie est le point d'arbitrage, et elle est écrite en commentaire au point
de décision (`RevalidatableUids`) : « reçus aujourd'hui » est **entièrement**
décrit par l'invariant `(Count, UidNext)` — une arrivée fait avancer `UIDNEXT`,
une suppression fait bouger `Count`, rien d'autre ne modifie l'ensemble du jour.
**« Non lus » ne l'est pas** : marquer un message comme lu ne touche ni l'un ni
l'autre. Le re-valider promettrait une fraîcheur que l'invariant ne prouve pas
(retard possible jusqu'à 5 min sur le compteur de non-lus) — refusé.

### La preuve : le compteur, pas la latence

`tests/mss.mail.application.tests/Services/Imap/ImapServiceFolderStatusSolicitationTests.cs`
— nombre **et ordre** exacts des commandes enregistrées, même style que task-262 :

| Test | Chemin | Attendu |
|---|---|---|
| `ACacheMissOnTheFolderRoute_PaysTheStatusFloorThenTheSearch` | miss complet | **5** commandes (était 7), ordre épinglé |
| `AFolderRouteRevalidation_StillCostsExactlyTheTwoCommandsOfTheStatusFloor` | re-validation | **2** commandes — non-régression du chemin `GetFolderStatus` exigée par le DOD |
| `AFolderRouteMissWithAStaleUidCache_PaysTheFiveCommandsOnce` | UIDs périmés | 5, un seul `resolve`, un seul `STATUS` |
| `ABoundedSearchMiss_PaysFiveCommands_TheFloorPlusItsThreeAsync` | `emails/today` miss | 5 |
| `AFailedConnection_RecordsNothing_AbsenceStaysProvable` | connexion KO | 0 |

`ImapDashboardCachingTests.cs` — le comportement produit :

| Test | Ce qu'il fixe |
|---|---|
| `GetFolderTodayAsync_WhenTheStatusWindowExpired_RevalidatesInsteadOfSearchingAgainAsync` | statut périmé + dossier inchangé → **aucun `SEARCH`**, UIDs resservis |
| `GetFolderTodayAsync_WhenTheStatusWindowExpiredAndTheFolderMoved_SearchesAgainAsync` | `UIDNEXT` a bougé → recherche refaite (la borne de la re-validation) |
| `GetFolderNotSeenAsync_WhenTheStatusWindowExpired_TakesNoShortcutAsync` | « non lus » **jamais** re-validé — l'asymétrie voulue |
| `GetFolderAsync_ServesTheSameResponseBodyWhetherRevalidatedOrSearchedAsync` | corps de réponse **champ pour champ identique** entre chemin court et chemin long, sur un dossier imbriqué (`Id`, `Name`, `ParentFolder` discriminants) |

### Vérification

- `dotnet build HealthPlatform.Api.Mail.sln` → **0 erreur, 0 avertissement**
- `dotnet test HealthPlatform.Api.Mail.sln` → domain 136/136, infrastructure
  464/464, api 685/685, **integration 417/417** (16 skipped), application
  2185/2186
- L'unique rouge est le flaky **pré-existant** du rendu PDF
  (`Services.Export`, QuestPDF) : il change de nom d'un tir à l'autre
  (`BuildPdfWithoutAttachmentsOmitsAttachmentSection`, puis
  `RenderHeadingPreservesText`) et passe 3 fois sur 3 en isolation. Sans rapport
  avec ce chemin. Les 325 tests `Services.Imap` sont verts.

### DOD

- [x] Build 0 erreur / tests verts (hors flaky PDF pré-existant)
- [x] Allers-retours d'un cache-miss réduits **et prouvés par le compteur**
      (7 → 5 pour l'appel froid ; opération `GetFolderQuery` 5 → 3)
- [x] Réponse inchangée — parité champ pour champ testée sur dossier imbriqué
- [x] Fraîcheur : aucun TTL modifié ; l'arbitrage (et l'asymétrie today/unread)
      est écrit au point de décision et fixé par deux tests
- [x] `GetFolderStatus` reste à 2 allers-retours — test dédié
- [x] Tests unitaires sur chaque nouvelle branche (re-validation OK / démentie /
      refusée pour « non lus » / miss complet)
- [x] Aucune donnée de santé dans les journaux : les étiquettes du compteur
      restent des littéraux (`GetFolderStatus`, `GetFolderQuery`), les journaux
      ne portent que chemin de dossier et compteurs, comme avant

### Commit

- `api-mail` — [`6e1551b`](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/commit/6e1551b) sur `feat/task-270-folder-imap-roundtrips`
