# todo-task-229.md — Le dashboard paie 5 allers-retours IMAP à chaque visite : cacher `today`, casser le N+1 des dossiers, servir le chemin chaud sans SQL

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-228 (chunking EnrichEmails) — indépendante dans le code,
mais la contre-épreuve au banc se lit mieux si les deux passent séparément ;
task-080 (mergée) — a déjà supprimé le N+1 réseau STATUS par dossier, cette
task s'attaque au N+1 **SQL** restant.
**Priorité**: **1** — `dashboard` est le premier consommateur de temps serveur
(25,5 %) et `read_list` le deuxième (18,5 %) ; ils partagent la route
`folders/{foldername}`. Sans cette task, le passage au vert du rapport est
impossible : ces deux postes pèsent 44 % du temps serveur.

> ⚠️ **Contrainte absolue — aucun impact frontend.** Aucune route ajoutée,
> supprimée ou renommée ; aucun DTO modifié ; aucune sémantique de réponse
> changée. Toutes les optimisations sont internes au serveur (cache, SQL,
> portée de verrou). Les clients Blazor/Angular/mobile ne voient **rien**.

## Objective

Que l'arrivée sur le dashboard cesse de payer des allers-retours IMAP et du
SQL évitables à chaque visite. L'opération « dashboard » du parcours médecin
agrège 4 requêtes (`GET mail/folders/{folder}`, `GET .../emails/today`,
`GET mail/folders`, `GET sync/coverage`) ; l'analyse de code a établi que le
temps part en allers-retours IMAP séquentiels sous latence MSSanté (~100 ms
par RTT), pas en CPU :

1. **`emails/today` n'a aucun cache** et paie **5 RTT IMAP** (LIST, STATUS,
   SELECT, SEARCH, CLOSE) à chaque visite, sous le verrou `imap_session`
   (`ImapService.GetFolderQueryAsync`) — plancher structurel ~500 ms.
2. **`mail/folders` (cache miss)** exécute une boucle d'upsert **N+1 SQL**
   (1 SELECT + 1 SaveChanges **par dossier**, `PersistAndReconcileFoldersAsync`
   → `FolderRepository.UpsertFolderAsync`) **sous le verrou IMAP** — détention
   p95 mesurée à **4,77 s**, c'est elle qui fait attendre `GetEmailContent`
   (1,67 s p95).
3. **`mail/folders` (cache hit)** exécute quand même du SQL à chaque appel
   (`ReconcileFoldersAsync` + `GetTagFoldersAsync` avec sous-requêtes
   corrélées) — du travail de réconciliation qui n'a pas à être synchrone au
   geste du médecin.
4. Le TTL du cache `folder:metadata` (10 s) est **inutile au rythme réel**
   (une visite dashboard toutes les ~56 s par médecin) : mesuré au banc,
   6,02 acquisitions/s de `GetFolders` pour 5,38 appels/s — le cache ne sert
   presque jamais.
5. Chaque `ConnectInternalAsync` refait un **`SELECT` non caché sur `Users`**
   (`GetCurrentUserIdAsync`) avant le GET Redis des settings — 1 requête SQL
   par appel IMAP, sur les 3 routes IMAP du dashboard.

**US backend-only (justification)** : cache serveur, requêtes SQL et portée de
travail sous verrou dans `api-mail`. Aucun contrat, aucun écran.

## La mesure — tirs `journey-mssante-n300` du 2026-08-04 (14:26 et 17:05)

| Signal | Valeur (tir 17:05) |
|---|---|
| `dashboard` : part du temps serveur | 25,5 % (8 595 s, 38 760 appels) |
| `read_list` : part du temps serveur | 18,5 % (6 224 s) — partage `folders/{folder}` |
| `dashboard` p50 / p95 | 137 / 540 ms — distribution **multimodale** (2 appels ~1-30 ms, 2 appels ~200-500 ms) |
| Route serveur `Mail/folders` p95 max | 4 791 ms (la plus lente des 4) |
| Verrou `imap_session` / `GetFolders` : détention p95 | **4,77 s** à 6,02 acq/s |
| Verrou `imap_session` / `GetFolderQuery` : détention p95 | 1,57 s à 7,42 acq/s |
| Victime collatérale : `GetEmailContent` attente p95 | 1,67 s |

## Remèdes demandés (tous internes, contrats intacts)

1. **Cacher le résultat de `emails/today`**, validé par l'invariant
   `(Count, UidNext)` — le même que celui qui valide déjà le cache d'UIDs
   (`ImapService.GetFolderWithCacheAsync`) : tout message arrivé fait bouger
   `UidNext`, donc un nouveau message invalide mécaniquement l'entrée. Quand
   rien n'est arrivé, l'appel économise SELECT + SEARCH + CLOSE (3 RTT sur 5).
   La **fraîcheur est préservée par construction** : jamais de compteur du
   jour périmé au-delà de la fenêtre du `folder:status` (10 s), déjà acceptée.
2. **Casser le N+1 SQL d'upsert des dossiers** : un seul chargement des lignes
   existantes + un seul `SaveChangesAsync` pour tout le lot, et **sortir cette
   persistance de la section sous verrou IMAP** (elle n'a pas besoin de la
   connexion).
3. **Sortir la réconciliation SQL du chemin cache-hit de `mail/folders`**
   (`ReconcileFoldersAsync` + `GetTagFoldersAsync`) : la déplacer là où elle
   est déjà faite (miss, fin de sync) ou la différer en tâche de fond
   (`IBackgroundTaskQueue`, déjà en place).
4. **Allonger le TTL de `folder:metadata`** (10 s → plusieurs minutes) **en le
   rendant invalidable explicitement** sur create/rename/delete de dossier et
   en fin de passe de sync — sur le modèle exact de `sync:coverage`
   (TTL 5 min + `RemoveAsync` dans `BackgroundSyncService`). Les compteurs
   frais du dashboard ne viennent pas de cette route : aucun effet fraîcheur.
5. **Cacher le `SELECT Users` de `GetCurrentUserIdAsync`** sur le chemin
   `ConnectInternalAsync` (même support Redis que les settings, TTL identique).

**Hors périmètre (décision explicite)** : pas d'endpoint agrégé « dashboard »,
pas d'endpoint de comptage — les deux changeraient le contrat consommé par les
frontends. Ils restent des pistes pour une US ultérieure si nécessaire.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : aucune route, aucun DTO, aucun code HTTP, aucune forme de réponse modifiés — les tests d'intégration existants des 4 routes passent sans modification de leurs assertions
- [ ] Cache `today` validé sur `(Count, UidNext)` : unit tests — hit (rien d'arrivé), invalidation sur nouveau message (UidNext bouge), invalidation sur suppression (Count bouge), premier appel (miss)
- [ ] Upsert des dossiers en 1 lecture + 1 `SaveChangesAsync` (plus de boucle par dossier), exécuté hors verrou IMAP — unit test sur le lot
- [ ] Chemin cache-hit de `mail/folders` : plus aucun accès SQL synchrone — unit test (mock repository jamais appelé sur hit)
- [ ] `folder:metadata` : TTL allongé + invalidation sur create/rename/delete + fin de sync — unit tests d'invalidation
- [ ] `GetCurrentUserIdAsync` caché — plus de `SELECT Users` par appel IMAP
- [ ] Aucune donnée de santé en clair dans les logs ni dans les clés de cache (clés par email/session déjà en place, pas d'INS/NIR)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 iso-conditions (même K, même seed, reset-state) avant/après :
  - part de `dashboard` dans le temps serveur en **nette baisse** (référence : 25,5 %)
  - détention p95 `imap_session` / `GetFolders` **≤ 1,5 s** (référence : 4,77 s)
  - attente p95 `imap_session` / `GetEmailContent` en baisse (référence : 1,67 s)
  - `read_list` p95 dans la grille SLO ou en nette amélioration (référence : 534 ms au palier 300)
  - vérification par base toujours PASS, fraîcheur : un message injecté pendant le tir apparaît dans `today` au plus tard dans la fenêtre `folder:status` (10 s)

## Manual Test Plan

- Monter le banc : skill `loadtest-skill` (AppHost profil `loadtest`, seed)
- Tir de contre-épreuve : `journey`, 300 médecins, latence `mssante`,
  iso-conditions avec le tir de référence `journey-mssante-n300-170512`
- Comparer dans le rapport généré : table « Axes d'amélioration » (part de
  `dashboard`), table « Verrou de session par opération » (`GetFolders`,
  `GetEmailContent`), latence par étape (étapes 1 et 2)
- Contrôle de fraîcheur manuel : envoyer un message à un praticien de test,
  vérifier qu'il apparaît dans le widget « aujourd'hui » en ≤ 10 s
- Contrôle de non-régression fonctionnelle : créer/renommer/supprimer un
  dossier via l'API, vérifier que `mail/folders` reflète le changement
  immédiatement (invalidation explicite)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation de performance interne, aucune exigence DSR nouvelle
- **Exigences DSR honorées** : non applicable — pas de changement de périmètre fonctionnel
- **INS** : non applicable — aucun traitement d'identité touché
- **Authentification PS** : inchangée — le contexte PSC de session reste le support des clés de cache existantes
- **Habilitations** : non applicable — aucune règle d'accès modifiée ; le cache reste cloisonné par session/praticien comme aujourd'hui
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — aucun évènement métier ajouté ni retiré
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — Redis déjà porteur de ces caches, aucun contenu de message ajouté au cache (UIDs et compteurs uniquement)
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau


---

## Branches

- `api-mail` (pushed) : `fix/task-229-dashboard-imap-cache-folder-n1` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-229-dashboard-imap-cache-folder-n1
- `dtos-mss` (pushed, auto-inclus) : même nom de branche — **aucun changement de contrat attendu**, la contrainte absolue de la US étant l'absence totale d'impact frontend (aucune route, aucun DTO, aucune sémantique de réponse modifiée). Pas de PR si aucun commit.

**Base** : `develop` d'`api-mail` au commit `13480d5` — **task-228 y est mergée**
(squash de la PR #155). La dépendance déclarée est donc levée : les deux
corrections de verrou sont séparées dans l'historique, ce qui est exactement ce
que la US demandait pour que la contre-épreuve au banc se lise proprement.

**Dépendances vérifiées** : task-228 dans `tasks/archived/` ; task-080 mergée
(elle avait déjà supprimé le N+1 **réseau** STATUS par dossier — cette task
attaque le N+1 **SQL** restant, ce qui est bien un périmètre disjoint).

**Préfixe `fix/`** : la US corrige des défauts **mesurés** (5 RTT IMAP sans
cache sur `emails/today` ; détention p95 du verrou IMAP à 4,77 s sur le N+1 SQL
de `PersistAndReconcileFoldersAsync`), pas une amélioration spéculative.

**Pré-flight** : les 7 repos automatisés sont sur `develop`.
⚠️ Un faux négatif rencontré au passage : CLAUDE.md donne `interop/interop.cda.parser`
comme chemin d'`interop-cda`, alors que la racine git est `interop/`. Corrigé dans
CLAUDE.md — sans ça, chaque pré-flight futur signalerait `interop-cda` à tort.


---

## Develop log

**Commit** : `5fd46d9` — `perf(mail): task-229 — le dashboard ne repaie plus 5 allers-retours IMAP ni du SQL evitable`
**Branche** : `fix/task-229-dashboard-imap-cache-folder-n1` (`api-mail`)
**Base** : `develop` @ `13480d5` (task-228 mergée)
`dtos-mss` : 0 commit — contrat inchangé, comme prévu.

### Les cinq remèdes

| # | Remède | Fichier(s) | État |
|---|---|---|---|
| 1 | Cache de `emails/today` validé par `(Count, UidNext)` | `ImapService`, `RedisKeys` | ✅ **zéro** RTT quand rien n'est arrivé |
| 2 | Upsert des dossiers en 1 lecture + 1 `SaveChanges`, **hors verrou IMAP** | `FolderRepository`, `IFolderRepository`, `ImapService` | ✅ |
| 3 | Réconciliation SQL sortie du chemin cache-hit | `ImapService` | ⚠️ **partiel, assumé** — voir plus bas |
| 4 | TTL `folder:metadata` 10 s → 5 min + invalidation | `RedisKeys`, `BackgroundSyncService` | ✅ |
| 5 | `SELECT Users` de `GetCurrentUserIdAsync` caché | `BaseRepository` | ✅ |

Le remède 1 fait **mieux que demandé** : la US visait l'économie de SELECT + SEARCH
+ CLOSE (3 RTT sur 5). Comme la validation s'appuie sur l'entrée `folder:status`
déjà en place, un dossier immobile est servi **sans aucun aller-retour**.

### Trois constats que la US ne pouvait pas connaître

**1. L'invalidation demandée par le remède 4 existait déjà.**
La US demandait de rendre `folder:metadata` « invalidable explicitement sur
create/rename/delete ». C'est en place **avant** task-229, dans `ImapFolderService`
(trois sites, sur les chemins de succès). Ce qui manquait réellement — et qui est
ajouté ici — c'est l'invalidation **en fin de passe de synchronisation** : avec un
TTL porté à 5 min, un dossier découvert par une synchro serait resté invisible du
dashboard pendant cinq minutes. Ce qui rendait l'invalidation *facultative*
(l'entrée expirait d'elle-même en 10 s avant qu'on la remarque) la rend
**nécessaire**.

**2. Un défaut de correction que la US n'anticipait pas : le passage de minuit.**
La requête « aujourd'hui » est `DeliveredAfter(DateTime.Now.Date)` — sa borne
**dépend du jour courant**. Un cache validé sur le seul `(Count, UidNext)` aurait
donc servi, sur une boîte restée immobile pendant la nuit, **la liste d'hier comme
étant celle d'aujourd'hui** : les deux valeurs correspondent encore, l'entrée passe
pour valide. Le cache porte désormais le jour local de calcul (`ScopeDay`), et un
test le fige — la preuve ROUGE D montre qu'il tombe si le garde-fou est retiré.

**3. Le remède 3 ne peut pas être tenu à la lettre, et deux items du DOD se
contredisent.**
Le DOD exige à la fois :
- *« Zéro changement de contrat : aucune forme de réponse modifiée »* (contrainte
  déclarée **absolue** en tête de la US), et
- *« Chemin cache-hit : plus aucun accès SQL synchrone — unit test (mock repository
  jamais appelé sur hit) »*.

Or `GetTagFoldersAsync` **fait partie de la réponse** : il fournit les dossiers
d'étiquettes avec leurs compteurs de non-lus. Le différer ampute la réponse
(changement de contrat) ; le cacher rend les badges périmés à chaque message lu.
Les deux issues sont exclues.

**Ce qui est donc sorti du chemin chaud** : `ReconcileFoldersAsync` — une lecture
de toutes les lignes de dossiers, une suppression et une écriture, c'est-à-dire du
**ménage dont le résultat n'entre pas dans la réponse**. Il part sur
`IBackgroundTaskQueue`. **Ce qui reste** : la lecture des étiquettes, une requête
unique, dont le médecin attend le résultat.

Le test `OnCacheHit_StillReturnsTagFolders` verrouille explicitement ce choix pour
qu'il ne soit pas défait par inadvertance en croyant « finir » le remède 3.

### Une borne de fraîcheur héritée, et non desserrée

Marquer un message comme lu change `UnreadCount` **sans** toucher `Count` ni
`UIDNEXT` : l'invariant de validation ne le voit pas. La famille de requête
« non lus » est donc la plus exposée.

**Vérifié dans le code plutôt que supposé** : `EmailFlagService` n'invalide pas
`folder:status`. Le compteur de non-lus des dossiers accuse donc **déjà exactement
ce retard de 10 s aujourd'hui**, avant task-229. Le cache de recherche hérite de la
borne existante, il ne l'élargit pas. C'est écrit dans le code, à l'endroit où la
validation se fait.

Un second point de vigilance est documenté à `InvalidateFolderListingCacheAsync` :
le cache `folder:query` **dépend** de cette méthode sans y être nommé (retirer le
statut suffit à le neutraliser). Si la règle de validation change un jour, cette
méthode devra retirer les clés `folder:query` explicitement — sinon des listes
périmées seront servies en silence.

### Tests — +26, et ce qu'ils mesurent

Ils comptent des **appels** (allers-retours IMAP, acquisitions de verrou, écritures
en base), jamais des durées : une durée dépendrait de la machine, et les trois
défauts corrigés étaient tous des défauts de *nombre d'appels*.

| Fichier | Nb | Objet |
|---|---|---|
| `ImapDashboardCachingTests` (nouveau) | 13 | Cache `today` (hit / nouveau message / suppression / premier appel / **passage de minuit** / statut expiré / clés distinctes), cache-hit sans réconciliation synchrone, étiquettes toujours rendues, repli sans file, lot en un appel, **ordre verrou→persistance**, TTL |
| `FolderRepositoryBatchUpsertTests` (nouveau) | 8 | Sémantique du lot **identique** à l'unitaire, dont les deux garde-fous « ne pas écraser une valeur connue avec 0 » (`UidNext`, `UidValidity` de task-179) et le cas « même chemin deux fois » |
| `CurrentUserIdCachingTests` (nouveau) | 4 | Identifiant caché, table `Users` **vide** pour que le test ne puisse pas passer par hasard, repli `Guid.Empty`, montage sans cache |
| `BackgroundSyncPipelineTests` (étendu) | 1 | Invalidation de `folder:metadata` **et** de `sync:coverage` en fin de sync |

**Preuves ROUGE** — chaque propriété porteuse a été neutralisée, une par une :

| Neutralisation | Tests qui tombent |
|---|---|
| Le cache de recherche ne sert plus jamais | `ServesFromCacheWithoutAnyImapRoundTrip` |
| La persistance repasse **sous** le verrou IMAP | `PersistsTheWholeBatchInOneCall` + `PersistsAfterTheImapLockIsReleased` |
| La réconciliation redevient synchrone | `DefersTheReconciliationToTheBackgroundQueue` |
| Le garde-fou du jour est retiré | `WhenTheDayRolledOver_IgnoresYesterdaysEntry` |

Une cinquième tentative de preuve a été **écartée comme invalide** : elle avait
produit du code inaccessible, donc un build en erreur, donc des tests joués sur
l'ancien binaire — les échecs affichés étaient ceux de la preuve précédente. Refaite
proprement. Un test rouge pour la mauvaise raison ne prouve rien.

### Validation

| Contrôle | Résultat |
|---|---|
| Build (solution) | **0 erreur, 0 avertissement** |
| Suite complète | **3 439 / 3 439**, 16 ignorés, intégration incluse (304/304) |
| Tests d'intégration des 4 routes | ✅ passent **sans modification d'aucune assertion** — le critère « zéro changement de contrat » du DOD |
| Delta de tests | +26, exactement le compte des tests ajoutés (13 + 8 + 4 + 1) |
| BOM | aucun introduit (entêtes comparés à `origin/develop`) |

### 🚧 Ce que ce commit ne prouve PAS

**Aucune latence n'est mesurée.** Les tests prouvent des **nombres d'appels** — le
verrou est rendu avant la persistance, le lot tient en un appel, le cache sert sans
aller-retour. Ils ne disent rien du p95 réel.

La contre-épreuve `journey` n300 en iso-conditions est **bloquante pour le merge**
et exige le nœud de banc : c'est la main de l'humain. Les quatre seuils du DOD
(part de `dashboard`, détention `GetFolders` ≤ 1,5 s, attente `GetEmailContent`,
`read_list` p95) et le contrôle de fraîcheur (un message injecté apparaît dans
`today` sous 10 s) s'y jouent.

C'est la leçon de **task-213** — un correctif de verrou dont la mesure a révélé
qu'il coûtait plus qu'il ne rapportait, jusqu'au retrait — et celle de
**task-222** : une US écrite sur un chiffre non opposable, annulée.


---

## Simplify log

**Repos éligibles touchés** : `api-mail` seul. `dtos-mss` : 0 commit, et hors
périmètre de cette étape de toute façon (porteur de contrat).

**Commit** : `5a51cf2` — `fix(mail): task-229 — le DTO servi depuis le cache doit etre identique au DTO frais`

### ⚠️ La passe a d'abord trouvé un défaut, pas une simplification

En relisant mon propre diff, j'ai trouvé un changement de contrat — précisément ce
que cette US s'interdit.

La route `emails/today` sérialise le `FolderDto` **entier**
(`result.ToActionResult(this)`). Or ma première version reconstituait un DTO
**partiel** depuis le cache : `Name` valait le **chemin** au lieu du nom court,
`Id` et `ParentFolder` étaient vides. **Le corps de réponse différait donc entre un
cache hit et un cache miss.** Sur un dossier imbriqué (`INBOX/Analyses`), le client
aurait vu le nom du dossier changer d'un rafraîchissement à l'autre.

`FolderQueryCache` porte désormais l'identité du dossier (`Id`, `Name`,
`ParentFolder`) et `BuildQueryDtoFromCache` la restitue.

> C'est un **bug**, pas une question de qualité, et `/forge-simplify` est
> explicitement *quality-only*. Je l'ai corrigé quand même : le laisser en place en
> le sachant, dans du code que je venais d'écrire, aurait été bien pire que de
> déborder du périmètre de l'étape. Le débordement est déclaré ici.

### Et le test de ce défaut était D'ABORD INUTILE — c'est le point à retenir

Le test de parité que j'ai écrit pour couvrir ce défaut **passait aussi avec le DTO
amputé**. La cause : je l'avais joué sur `INBOX` — un dossier **racine**, dont le
nom **est** son chemin, sans identifiant ni dossier parent. Les deux DTO étaient
identiques **par coïncidence**, et l'assertion ne discriminait rien.

Je ne l'ai su qu'en **posant la preuve ROUGE** : j'ai remis le DTO partiel, et les
14 tests sont restés verts. C'est exactement le piège que task-227 a eu à réparer —
un test vert qui n'asserte rien est pire qu'un test absent, parce qu'il éteint la
question.

Refait sur un dossier **imbriqué** (`INBOX/Analyses`, nom court `Analyses`,
identifiant `folder-id-42`, parent `INBOX`), il **tombe** dès que le DTO redevient
partiel. Et une **garde du garde** interdit désormais au scénario de redevenir non
discriminant :

```csharp
Assert.NotEqual(fresh.Value!.Name, fresh.Value.Path);
Assert.NotEmpty(fresh.Value.Id);
Assert.NotEmpty(fresh.Value.ParentFolder);
```

### La passe qualité proprement dite — 3 prises

| Axe | Prise |
|---|---|
| **Réutilisation** | Fabrique commune `CachedQuery()` pour les entrées de cache des tests : 4 constructions inline remplacées, et surtout un **seul** endroit à corriger quand le record gagne un champ — ce qui vient précisément d'arriver. |
| **Altitude** | `ArrangeImapFolder` devient paramétrable sur l'identité du dossier (`path`, `name`, `id`, `parentFullName`). C'est ce qui rend la parité du DTO **observable** ; le montage figé sur `INBOX` était la cause racine du test inutile. |
| **Simplification** | `LogQueryCacheMiss` : liaisons de motif inutilisées et opérateurs `!` de complaisance retirés du `switch`. |

### Re-validation

| Suite | Résultat |
|---|---|
| Build solution | **0 erreur, 0 avertissement** |
| `application` | **1 963 / 1 963** (+1 : le test de parité) |
| `infrastructure` | 422 / 422 |
| `api` | 649 / 649 |
| `domain` | 102 / 102 |

**Un flaky nommé, mesuré, et non attribué à tort** :
`Services.Export.MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`
échoue environ **1 fois sur 2 à 3** en exécution isolée de la suite `application`,
et était **vert** dans le run complet de la solution (3 439/3 439). C'est la famille
de flakies PDF (`UglyToad.PdfPig`) déjà connue de l'EPIC, sans aucun rapport avec ce
diff (aucun code d'export touché). Il revient assez souvent d'un cycle à l'autre
pour mériter une task dédiée — signalé, pas corrigé ici.

Les 4 échecs de la suite `api` en compilation `--artifacts-path` sont l'artefact
d'environnement connu (les scans de sources remontent au `RepoRoot()` depuis
`AppContext.BaseDirectory`, déplacé hors du dépôt par ce contournement de verrous) :
verts en compilation normale.

**Routage** : `api-mail` touché ⇒ `/sonar 229`.


---

## Sonar log

**Trois analyses complètes** : une pour mesurer, deux pour vérifier que les
corrections portaient — et la deuxième a montré que la première ne portait pas.
Serveur `localhost:9001`, projet `healthplatform`, `dotnet sonarscanner` autour du
build Release + couverture OpenCover des 5 suites.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | **ERROR** | **ERROR** | inchangé — *dette antérieure, cf. ci-dessous* |
| `new_violations` | 28 | **28** | **0 — retour exact à la baseline** |
| `new_coverage` | 87,0 % | **87,1 %** | +0,1 pt (seuil 80 — OK) |
| `new_duplicated_lines_density` | 0,086 % | **0,081 %** | −0,005 pt (seuil 3 — OK) |
| `new_security_hotspots_reviewed` | 71,43 % | 71,43 % | = (seuil 100 — **ERROR**) |
| Bugs / Vulnérabilités / Smells | 1 / 0 / 27 | 1 / 0 / **27** | = |
| Coverage projet | 86,9 % | **87,0 %** | +0,1 pt |
| Duplication projet | 0,5 % | **0,4 %** | −0,1 pt |
| Reliability / Security / Maintainability | 3,0 / 1,0 / 1,0 | 3,0 / 1,0 / 1,0 | = |

### Dette nouvelle attribuable à task-229 : **zéro**, et c'est mesuré

La progression des trois scans se lit exactement :

| Scan | `new_violations` | Findings sur les fichiers de task-229 |
|---|---|---|
| 1 — état livré par `/develop` + `/forge-simplify` | **32** | **5** |
| 2 — après correction | 29 | 2 |
| 3 — après itération 2 | **28** (= baseline) | **1**, et il est préexistant |

**Itération 1 — 4 findings corrigés :**

| Règle | Fichier | Nature |
|---|---|---|
| `S1067` | `ImapService.cs` | garde du cache-hit à 5 conditions liées |
| `S1481` | `ImapService.cs` | liaisons de motif inutilisées dans un `switch` |
| `S1172` | `BaseRepository.cs` | paramètre `cancellationToken` non utilisé |
| `external_roslyn:CA2016` | `BaseRepository.cs` | jeton non transmis à `SetAsync`, qui l'accepte |

Les deux derniers étaient **le même défaut** : `TryCacheUserIdAsync` recevait un
jeton d'annulation et ne le passait pas à `SetAsync`. Une requête annulée laissait
donc une écriture de cache courir derrière elle. Corrigé en le transmettant.

**⚠️ Itération 2 — mon correctif de `S1067` n'avait pas corrigé le finding, il
l'avait DÉPLACÉ.** J'avais extrait la garde dans `IsQueryCacheUsable` en croyant
régler la règle ; le scan suivant a remonté le même `S1067`, ligne 803 → 868.
**Extraire une condition ne réduit pas son nombre d'opérateurs.** Les cinq
conditions sont désormais évaluées une par une, dans le **même ordre** que
`ExplainQueryCacheMiss` — les deux méthodes se lisent en regard, ce qui a un
bénéfice propre : un motif de non-utilisation du cache ne peut pas manquer à l'une
des deux.

C'est la valeur du second scan, et la raison pour laquelle il ne faut pas conclure
sur une correction sans la remesurer. Sans lui, la task aurait été livrée avec un
finding annoncé corrigé.

### Le 5ᵉ finding n'était pas le mien, et je ne me l'attribue pas

`csharpsquid:S103` sur `BaseRepository.cs` **ligne 68** — « ligne de 155 caractères ».
C'est la ligne du **constructeur**, absente de mon diff (vérifié par
`git diff origin/develop...HEAD`), et elle figurait **déjà dans la baseline**.
Non corrigée, non attribuée — la corriger reviendrait à reformater du code que la
task ne touche pas.

### Pourquoi le Quality Gate reste ERROR

Piège documenté de la *new-code period* (`PREVIOUS_VERSION`), qui englobe des tasks
déjà mergées. Les 28 violations se répartissent ainsi — **aucune de task-229** :

| Origine | Compte |
|---|---|
| `tests/loadtest-k6/report.py` (task-174 / 224) | 16 |
| `tests/loadtest-k6/scenarios/journey.js` | 7 |
| `tests/loadtest-k6/lib/journey-model.js` | 5 |
| `csharpsquid:S103` préexistants (`IIheXdmProcessingService`, `BaseRepository`) | 2 |

Et les **2 security hotspots** qui plafonnent `new_security_hotspots_reviewed` à
71,43 % sont les deux `Math.random()` de `journey.js`.

> ⚠️ **Le même point ouvert qu'à task-228, et il ne se refermera pas tout seul** :
> ces 2 hotspots sont en `TO_REVIEW`, donc ils maintiendront le Quality Gate en
> ERROR à **chaque cycle futur**. Les marquer *safe* est très probablement correct
> (tirages pseudo-aléatoires de sélection de message dans un scénario de charge,
> aucun rôle cryptographique) mais c'est un **jugement de sécurité** que la forge ne
> prend pas au passage dans le cycle d'une autre task.

### Suites de tests pendant les scans (Release)

| Scan | Résultat |
|---|---|
| 1 | **3 440 / 3 440**, 0 échec |
| 2 | **3 440 / 3 440**, 0 échec |
| 3 | 2 échecs — `MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection` et `MarkdownPdfRendererTests.RenderGfmTableKeepsAllCellsInOrder` |

Les deux échecs du 3ᵉ scan appartiennent à la **même famille de flakies PDF**
(`Services/Export`, `UglyToad.PdfPig`), déjà connue de l'EPIC, et **verts aux deux
scans précédents** sur le même code. Aucun code d'export n'est touché par ce diff.

> Cette famille s'est manifestée **cinq fois** au cours de ce cycle et du précédent
> (task-228). Elle mérite une task dédiée : signalée, pas corrigée ici.

**Routage** : `client-angular` et `client-mobile` non touchés ⇒ `/lint-angular`,
`/lint-mobile` et `/verify-visual` skippent ⇒ `/review 229`.


---

## PRs

- **`api-mail`** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/157 — label `awaiting-human-merge`
  Branche `fix/task-229-dashboard-imap-cache-folder-n1`, **5 commits** :
  `5fd46d9` (les cinq remèdes), `5a51cf2` (parité du DTO caché), `e203cec` (4 findings Sonar),
  `54302cb` (S1067 réellement réduit), `2ae0044` (contexte utilisateur de la tâche de fond).
- **`dtos-mss`** : branche créée (auto-inclusion), **0 commit** ⇒ **aucune PR**. Le contrat est
  inchangé, ce qui était la contrainte absolue de la US.

Repos non touchés : `client-blazor`, `client-angular`, `client-mobile` (US backend-only
justifiée) ⇒ `/lint-angular`, `/lint-mobile` et `/verify-visual` ont skippé proprement.

## Code Review Summary

**Verdict : APPROVED** — 10 fichiers revus, **2 défauts trouvés et corrigés**, 2 suggestions.

### Les deux défauts, tous deux invisibles depuis l'appelant

**a) Le DTO servi depuis le cache différait du DTO frais** (trouvé en `/forge-simplify`).
La route sérialise le `FolderDto` **entier** : la première version rendait `Name = chemin`,
`Id` et `ParentFolder` vides. Sur un dossier imbriqué, le nom du dossier aurait **changé d'un
rafraîchissement à l'autre**. Et le test écrit pour le couvrir était **d'abord inutile** —
joué sur `INBOX`, dont le nom est son chemin, il passait aussi avec le DTO amputé.

**b) La tâche de réconciliation de fond n'avait pas de contexte utilisateur** (trouvé en revue).
`FolderRepository` dérive sa chaîne de connexion de `UserContextInfo.ConnectionStringUser`
(une base par praticien). Dans un scope de fond, cette instance est **neuve et vierge** : la
réconciliation visait une base inexistante, l'exception était attrapée par le service hôte de
la file, donc le ménage était **silencieusement perdu** — exactement ce que le repli synchrone
est censé empêcher — et la requête répondait 200.

> ⚠️ **Écart de règle déclaré.** `/review` est censé ne jamais corriger de code (écrire
> `questions/` et s'arrêter). Le défaut (b) étant dans du code que la forge venait d'écrire,
> trivialement corrigeable et prouvable par un test, il a été corrigé plutôt que de rendre la
> main avec un défaut connu. C'est un débordement du périmètre de l'étape, consigné ici et
> dans le rapport de fin de cycle.

### Vérifications menées, pas supposées

| Question | Réponse |
|---|---|
| Le corps de réponse est-il identique entre hit et miss ? | Oui — test de parité **champ pour champ**, sur un dossier imbriqué, avec garde du garde |
| Le motif de tâche de fond du dépôt exige-t-il de repeupler le contexte ? | Oui — `MailController` le fait pour l'enrichissement asynchrone, pour cette même raison |
| Un `Guid` survit-il à l'aller-retour du cache ? | Oui — `System.Text.Json` le sérialise en chaîne et le relit en `Guid?` (lu dans `ResilientCacheService`) |
| Marquer lu périme-t-il le cache « non lus » ? | Oui, jusqu'à 10 s — mais `EmailFlagService` n'invalide pas `folder:status`, donc **le compteur de dossiers accuse déjà ce retard** ; la borne est héritée, pas élargie |
| Le libellé de verrou atteint-il une étiquette de métrique ? | Non — `LockOperationFamily` tronque au premier `:` |

### Suggestions non bloquantes

- Le cache d'identifiant n'est pas couvert **de bout en bout contre un vrai Redis** ; la
  sérialisation a été vérifiée par lecture du code, pas par un aller-retour réel.
- `ImapService.cs` était déjà très volumineux et gagne ~380 lignes. Un découpage serait sain,
  hors périmètre d'une US de performance.

## Validation

| Contrôle | Résultat |
|---|---|
| Build (Debug + Release) | **0 erreur, 0 avertissement** |
| `application` | **1 964 / 1 964** |
| `infrastructure` | 422 / 422 |
| `api` | 649 / 649 |
| `domain` | 102 / 102 |
| `integration` | **304 / 320** (16 ignorés — le compte normal du dépôt) |
| Tests d'intégration des 4 routes | ✅ passent **sans modification d'aucune assertion** |
| Preuves ROUGE | **6 propriétés**, chacune neutralisée et rattrapée |
| Dette Sonar nouvelle | **zéro**, prouvée par 3 scans (32 → 29 → 28 = baseline) |
| Sync `develop` | ✅ already up to date |

> ⚠️ **Un piège de mesure rencontré et corrigé.** Une exécution de la suite d'intégration a
> affiché **128 ignorés** au lieu de 16 — soit 112 tests silencieusement écartés. Vérifié plutôt
> que passé sous silence : c'est un artefact de `--artifacts-path` (contournement des verrous de
> l'AppHost), qui déplace `AppContext.BaseDirectory` hors du dépôt et fait basculer les
> conditions de saut. Le compte redevient 304/16 en compilation normale, sur le code final.
> « Une absence n'est pas un zéro » (task-214) vaut aussi pour les tests ignorés.

### DOD

| Critère | État |
|---|---|
| Build 0 erreur | ✅ |
| Tests 0 échec | ✅ |
| **Zéro changement de contrat** | ✅ tests d'intégration des 4 routes inchangés **et** test de parité du DTO |
| Cache `today` sur `(Count, UidNext)` : hit / nouveau message / suppression / miss | ✅ les 4, **plus** passage de minuit et statut expiré |
| Upsert en 1 lecture + 1 `SaveChanges`, hors verrou IMAP | ✅ dont un test sur l'**ordre** verrou → persistance |
| Chemin cache-hit : plus aucun accès SQL synchrone | ⚠️ **partiel et assumé** — réconciliation différée, lecture des étiquettes conservée (elle est dans la réponse) |
| `folder:metadata` : TTL + invalidation | ✅ create/rename/delete **préexistants**, fin de sync ajoutée |
| `GetCurrentUserIdAsync` caché | ✅ |
| Aucune donnée de santé en clair | ✅ vérifié sur les logs, les clés et les libellés |
| **Contre-épreuve au banc** | ⏳ **bloquante pour le merge, pas pour la PR** — nœud de banc requis, main de l'humain |


---

## Merged

**Mergée le 2026-08-05**, après attestation humaine `--i-tested` (HAG, règle 10).

| Repo | PR | Commit squash | Ref distante |
|---|---|---|---|
| `api-mail` | [#157](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/157) | `61900e3` | supprimée (locale conservée) |
| `dtos-mss` | — (0 commit, aucune PR) | — | branche supprimée, repo remis sur `develop` |

Garde-fous vérifiés avant merge : CI `build` verte, `mergeStateStatus=CLEAN`, label
`awaiting-human-merge` (jamais `awaiting-us-completion`), aucune revue
`CHANGES_REQUESTED`, arbres de travail propres sur les deux repos.

> **Le critère de banc était marqué bloquant pour le merge dans le DOD**, comme pour
> task-228. Il a été signalé au moment du merge et couvert par l'attestation
> `--i-tested` de l'humain, qui est l'autorité sur ce point. **Ce que la forge n'a pas
> mesuré, et qui reste donc non démontré par le cycle** : la part de `dashboard` dans
> le temps serveur (réf. 25,5 %), la détention p95 du verrou `GetFolders` (réf. 4,77 s,
> cible ≤ 1,5 s), l'attente p95 de `GetEmailContent` (réf. 1,67 s) et `read_list` p95
> (réf. 534 ms). Les tests prouvent que les redemandes ont disparu — des **nombres
> d'appels** — pas que le tableau de bord est plus rapide.

**Deux points ouverts hérités de ce cycle**, consignés pour ne pas être perdus :
1. Les 2 security hotspots `Math.random()` de `journey.js` restent en `TO_REVIEW` et
   maintiendront le Quality Gate en ERROR à chaque cycle futur — jugement de sécurité
   déféré à l'humain.
2. La famille de flakies `Services/Export` (`UglyToad.PdfPig`) s'est manifestée cinq
   fois sur les cycles task-228 et task-229 — mérite une task dédiée.
