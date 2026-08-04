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
