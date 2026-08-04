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
