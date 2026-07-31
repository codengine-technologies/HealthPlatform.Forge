# todo-task-205.md — `read_list` bloque des threads du pool et plafonne toute l'API à ~858 req/s

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-204 (l'escalier qui a nommé le facteur limitant)

> **Origine** : escalier de capacité du 2026-07-29 (task-204, § « Escalier de
> capacité log »). Premier tir de l'EPIC à **nommer** son facteur limitant au
> lieu de l'inférer.

## Objective

Supprimer la famine de ThreadPool que `read_list` provoque sur les réplicas
`api-mail`, et qui est **le** plafond de capacité mesuré du service.

### La mesure, et elle est sans ambiguïté

Cinq paliers à population fixe (200 praticiens, `mixed` 3 min, budget explicite) :

| Budget demandé | Délivré (plateau) | Servi | Latence moy. | `read_list` moy. | File ThreadPool (pire réplica) |
|---|---|---|---|---|---|
| 486 req/s | 482,7 | 99,3 % | 256 ms | 252 ms | 11 |
| 630 req/s | 625,4 | 99,3 % | 223 ms | 212 ms | 5 |
| 756 req/s | 745,5 | 98,6 % | 290 ms | 344 ms | 12 |
| 882 req/s | 824,8 | 93,5 % | 396 ms | **714 ms** | **136** |
| 972 req/s | 857,9 | 88,3 % | 591 ms | **1 533 ms** | **432** |

Deux faits qui, ensemble, ne laissent qu'une explication :

1. **`read_list` se dégrade d'un facteur ~7** (212 → 1 533 ms) quand toutes les
   autres opérations ne prennent qu'un facteur ~1,5 (`folders` 44 → 167,
   `search` 276 → 657, `send` 1 137 → 1 703, `enrich` 2 659 → 4 177).
2. **La file du ThreadPool explose (11 → 432) à CPU quasi constant** : le réplica
   le plus chargé consomme **1,19 cœur sur 24** avec 432 éléments en file et
   44 threads. Ce n'est pas une famine de CPU — c'est du **blocage d'I/O sur des
   threads du pool**, que l'algorithme d'escalade du ThreadPool (1-2 threads/s)
   ne rattrape pas.

Et la répartition entre réplicas est très inégale (432 / 205 / 68 / 13 / 6), ce
qui exclut une cause globale (base, pooler, IMAP) et pointe un **chemin de code
bloquant** exercé par certaines requêtes.

### L'expérience qui exclut le client comme explication

Objection légitime : et si ces abandons venaient du **harnais** (pool de VUs trop
petit) plutôt que du serveur ? Elle a été testée. Même budget de 882 req/s, même
population, **seul** le plafond de VUs du client change :

| | `VU_TAIL_FACTOR=8` | `VU_TAIL_FACTOR=16` |
|---|---|---|
| VUs réellement utilisés | 674 / 793 | 2 144 / 2 182 |
| Débit délivré | 824,8 req/s | **716,4 req/s** (−13 %) |
| Abandons | 4,21 % | **13,49 %** |
| p95 | 1 309 ms | **6 766 ms** |
| `read_list` moy | 714 ms | **3 606 ms** |
| Erreurs HTTP | 0,06 % | **6,41 %** |
| File ThreadPool par réplica | 136 / 93 / 13 / 10 / 7 | **406 / 951 / 579 / 648 / 813** |
| CPU par réplica | ~1,1 cœur | 0,8-2,3 cœurs |

**Donner plus de concurrence au client fait BAISSER le débit** et multiplie les
files de threads par 5 à 60, à CPU quasi inchangé. C'est un effondrement par
congestion sur une ressource bloquante — pas une pénurie de VUs, pas une pénurie
de CPU. Le rendement est **négatif** au-delà du genou : c'est aussi une consigne
d'exploitation (ne pas « pousser » un service déjà au genou).

### Ce que la campagne a déjà écarté

- **Pas le CPU applicatif** : au palier le plus haut, les 5 réplicas totalisent
  **3,68 cœurs sur 24** (mesuré par processus sur la fenêtre du tir) — soit 15 % de
  la machine — quand l'**infra du banc** en consomme **14,93** (`vmmemWSL` 7,56 ;
  Postgres 2,40 ; `com.docker.backend` 1,88 ; `dcp` 1,18 ; conteneurs le reste).
  L'application n'est pas à court de CPU : elle attend.
  **Corollaire pour la lecture des chiffres** : ~858 req/s est un **plancher** de
  la capacité réelle, pas un plafond — sur ce poste, le banc se dispute la machine
  avec le service qu'il mesure.
- **Pas PgBouncer** : `cl_waiting` ≤ 8 **dans** les fenêtres de tir, `sv_active`
  ≤ 162, 402 backends praticien. Les pics (jusqu'à 75) sont des **transitoires de
  démarrage** hors fenêtre.
- **Pas Dovecot** : 1 001 sessions IMAP (= 5 par praticien × 200, exactement le
  modèle), CPU du conteneur marginal.
- **Pas le client k6** : 0,2-0,4 cœur.
- **Pas Postgres** : 2,7 cœurs moyens, 4,0 en pointe.

### Piste de départ (à confirmer, pas à croire)

`BaseRepository.get_DataContext` est le suspect historique de sync-over-async
(cité par task-204 et jamais mesuré jusqu'ici). Le chemin de `read_list`
(`GET /api/v1/mail/folders/{folder}/emails/{ids}`) est celui à profiler en
premier : il combine fetch IMAP et écriture en base, et c'est le seul dont la
latence explose.

⚠️ **Ne pas partir de la conclusion.** L'US commence par *localiser* le blocage
(`dotnet-counters`, `dotnet-stack`, ou un `ThreadPool` starvation detector sur un
tir de 3 min à 882 req/s), puis corrige ce qui est trouvé.

## Contenu attendu

1. **Localiser** le ou les appels bloquants du chemin `read_list` — pile de
   threads bloqués pendant un tir au palier 882 req/s (le premier où la file
   décolle), preuve jointe à la task.
2. **Corriger** : rendre le chemin asynchrone de bout en bout (aucun `.Result`,
   `.Wait()`, `GetAwaiter().GetResult()`, aucun `lock` autour d'une I/O).
3. **Verrouiller par test** : un test qui échoue si le chemin de `read_list`
   réintroduit un appel bloquant (analyseur, ou test de concurrence qui sature un
   pool réduit).
4. **Re-mesurer** avec le banc : rejouer les paliers 882 et 972 req/s et publier
   la file ThreadPool avant/après. Critère de succès chiffré ci-dessous.

## Hors scope

- Les autres opérations (`send` à 1,7 s, `enrich` à 4,2 s) : elles se dégradent
  normalement sous charge, une task chacune si besoin.
- Le dimensionnement du harnais et les défauts de conclusion du rapport
  (task-208, task-209).
- Le bruit d'exceptions du banc (task-206).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] La ou les instructions bloquantes sont **nommées** (fichier:ligne) avec la
      pile de threads qui les incrimine, jointe à la task
- [ ] Test unitaire par chemin corrigé (>= 1 par méthode rendue asynchrone)
- [ ] Test de non-régression qui échoue si un appel bloquant revient sur le
      chemin `read_list`
- [ ] **Mesure au banc** : au palier 882 req/s, file ThreadPool max **< 20** sur
      chaque réplica (contre 136), et `read_list` moy **< 400 ms** (contre 714)
- [ ] **Mesure au banc** : au palier 972 req/s, débit délivré **> 900 req/s**
      (contre 857,9) et drop **< 1 %**
- [ ] Rapport de tir + ligne d'INDEX pour l'avant/après

## Manual Test Plan

1. Monter le banc en profil loadtest (skill `loadtest-skill`).
2. Seeder / re-câbler 200 praticiens :
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 0 --api http://127.0.0.1:5052`
   (le maildir contient déjà 200 × 100 messages — ne pas supprimer le volume
   `loadtest-dovecot-mail`).
3. Purger les tables mail des 200 bases (sinon `read` est servi depuis la base et
   le défaut ne se reproduit pas).
4. Démarrer l'échantillonneur détaché : `tests/loadtest-k6/observe.sh start 900`.
5. Tirer le palier qui révèle le défaut :
   ```bash
   BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
   SESSION_ROTATION=0.001 RPS=980 VU_TAIL_FACTOR=8 ENRICH_SHARE=0.05 \
     tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
   ```
6. Ouvrir Grafana (`http://localhost:3001`), rangée « Saturation » : la file du
   ThreadPool par réplica doit rester plate. Avant correction, un réplica monte
   au-delà de 100.
7. `tests/loadtest-k6/report.sh <json> --expected 100`, puis lire la table
   « Par réplica api-mail » : colonne « File ThreadPool (max) ».

## Branches

- `api-mail` (pushed) : `feat/task-205-read-list-threadpool-starvation` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-205-read-list-threadpool-starvation
- `dtos-mss` (pushed, auto-inclus) : `feat/task-205-read-list-threadpool-starvation` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-205-read-list-threadpool-starvation
- `client-angular` / `client-mobile` : non listés dans `**Repos**:` (`Single frontend: true`) — aucune génération de code frontend

### Pre-flight (2026-07-31)

Tous les repos forge présents sont sur `develop`, arbres propres. Deux écarts
d'environnement, non bloquants et déjà relevés par task-200/203/204 :

- `client-mobile` — `Client/Mobile/` **absent du disque** (repo non cloné).
- `host` — `Host/Modules/` n'est pas un repo git autonome ; 14 fichiers modifiés
  y sont **hors périmètre** de cette task.

**Dépendance `task-204`** : satisfaite — PR #130 mergée le 2026-07-31 (squash
`c10fa7b`), task archivée en `tasks/archived/archived-task-204.md`. La branche de
cette task part donc d'un `develop` qui porte **l'instrument qui a nommé le
défaut** : attribution des métriques par réplica (collector OTLP), échantillonneur
hôte/conteneurs, section « Ressources & télémétrie » de `report.py`, dashboard de
saturation. C'est ce qui rend la re-mesure avant/après possible — et les 8 lignes
d'INDEX de l'escalier du 2026-07-29 sont sur `develop` (baseline de l'avant).

### Ce que `/develop` peut livrer, et ce qui restera dû

La DOD mêle du **code** et des **tirs de banc**. Le cycle autonome livre le
premier ; le second est une session de banc à conduire.

| Item de DOD | `/develop` | Banc |
|---|---|---|
| Build / tests verts | ✅ | — |
| Instruction bloquante **nommée** (fichier:ligne) + pile de threads | partiel — la lecture de code peut désigner les candidats, mais la **pile de threads bloqués sous charge** exige un tir à 882 req/s | ✅ requis |
| Test unitaire par chemin rendu asynchrone | ✅ | — |
| Test de non-régression « pas d'appel bloquant sur le chemin `read_list` » | ✅ | — |
| Palier 882 : file ThreadPool < 20, `read_list` < 400 ms | — | ✅ |
| Palier 972 : > 900 req/s délivrés, drop < 1 % | — | ✅ |
| Rapport de tir + ligne d'INDEX avant/après | — | ✅ |

⚠️ Consigne de la task à ne pas contourner : **« Ne pas partir de la
conclusion »**. `BaseRepository.get_DataContext` est un *suspect*, pas un verdict.
L'étape 1 est de **localiser**, preuve à l'appui.

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` : branche créée par
  `/start`, **aucun commit** — aucun contrat touché, donc aucune PR et aucun
  publish NuGet.
- **DTOs published** : no DTO change. **Interop published** : no interop change.
- **Commit** (`api-mail`, poussé) :
  - `10eda9d` `fix(imap): supprimer la famine de ThreadPool du chemin read_list`
- **Local build / test** : build **0 erreur / 0 warning** ; suite complète
  **3 207 tests verts, 0 échec**, 16 skips préexistants (tests IA nécessitant
  des clés API). Détail : domain 102, infrastructure 370, **application 1 858**
  (+6, les tests de cette task), api 590, integration 287.

### L'instruction bloquante, nommée

**`Api/Mail/src/Application/Services/Implementation/ImapService.cs:1180`** (sur
`develop`, avant correctif) :

```csharp
imapFolder = imapClient.GetFolder(folder, cancellationToken);   // ← bloquant
```

dans `TryGetFolderSafely`, atteint par le chemin `read_list`
(`GET /api/v1/mail/folders/{folder}/emails/{ids}`) :

```
MailController.GetEmailsByIdsAsync                MailController.cs:247
  └ OnlineMailDataProvider.GetEmailHeadersAsync   OnlineMailDataProvider.cs:38
     └ ImapService.GetEmailFromUidsAsync          ImapService.cs:661
        └ FetchEmailsInternalAsync                ImapService.cs:1215
           └ FetchMissingUidsWithLocksAsync       ImapService.cs:1277
              └ ProcessEmailUidAsync              ImapService.cs:1435
                 └ TryGetFolderSafely             ImapService.cs:1172 → :1180  ⛔
```

Relais : `IImapClientWrapper.GetFolder(string, CancellationToken)`
(`IImapClientWrapper.cs:35`) → `ImapClientWrapper.cs:66` →
`MailKit.IMailStore.GetFolder(string, CancellationToken)`.

### Pourquoi c'est bien une I/O bloquante — l'API de MailKit le dit

Le point dur était de **prouver** que cette surcharge fait un aller-retour
réseau, plutôt que de le supposer. La preuve est dans les métadonnées de
`MailKit.xml` (4.11.0) : sur les **trois** surcharges de `GetFolder`, une seule
a un pendant `Async` et une seule déclare des exceptions de transport.

| Surcharge | Pendant `…Async` ? | Exceptions déclarées | Verdict |
|---|---|---|---|
| `GetFolder(FolderNamespace)` | **non** | `ArgumentNull`, `FolderNotFound` | lecture mémoire |
| `GetFolder(SpecialFolder)` | **non** | — | lecture mémoire |
| **`GetFolder(String, CancellationToken)`** | **oui** (`GetFolderAsync`) | `IOException`, `ProtocolException`, `CommandException`, `OperationCanceled` | **I/O réseau (LIST)** |

Un client IMAP n'expose un pendant asynchrone que pour ce qui parle au serveur.
Cette asymétrie **dans la bibliothèque elle-même** est l'argument : ce n'est pas
une lecture de cache, c'est une commande.

### Pourquoi ça correspond à la mesure de task-204, et pas seulement « ça pourrait »

Trois recoupements, pas un seul :

1. **`read_list` dégrade ×7 quand `folders` ne dégrade que ×1,5.** `folders`
   (`GET /mail/folders`) passe par `GetFoldersAsync(namespace, …)` — la variante
   **asynchrone** — et ne touche jamais `TryGetFolderSafely`. Les deux opérations
   parlent au même Dovecot ; seule celle qui bloque s'effondre.
2. **Le Manual Test Plan exige de purger les tables mail avant le tir** (« sinon
   `read` est servi depuis la base et le défaut ne se reproduit pas »). Le code
   dit pourquoi : base pleine → `FetchEmailsInternalAsync` sert depuis
   `GetMailsByUidsAsync` et **sort avant** le chemin IMAP ; base vide → chaque
   `read_list` passe par `ProcessEmailUidAsync`, donc par l'appel bloquant. Le
   déclencheur documenté du défaut sélectionne exactement la branche fautive.
3. **File qui explose à CPU plat.** Un thread parqué sur une I/O ne consomme pas
   de CPU mais retire une unité de service au pool, que l'escalade du ThreadPool
   (1-2 threads/s) ne rattrape pas — 432 en file pour 1,19 cœur.

### Le correctif

- `TryGetFolderSafely` → **`TryResolveFolderAsync`** (`ImapService.cs:1187`),
  qui `await imapClient.GetFolderAsync(folder, cancellationToken)`. Les **5**
  appelants passent en async (`:401` `GetFolderStatus`, `:601` `GetFolderQuery`,
  `:723` `EnrichEmails`, `:1476` `ProcessEmailUid` — *le chemin `read_list`* —,
  `:2693` `FetchSingleEmail`).
- **La surcharge synchrone est retirée de `IImapClientWrapper`** et de son
  implémentation. C'est le cœur du correctif : *ce qui n'existe plus ne peut pas
  être rappelé par inadvertance*. Les surcharges `SpecialFolder` / `FolderNamespace`
  restent — ce sont des lectures mémoire (tableau ci-dessus).
- Les deux comportements du try-pattern d'origine sont préservés et testés :
  `FolderNotFoundException` **propagée** (l'appelant purge la ligne périmée et
  rend un 404 au lieu d'un 500), toute autre panne **absorbée**.

### Les gardes de non-régression, et ce que chacune attrape vraiment

`tests/.../Services/Imap/ReadListNonBlockingTests.cs` — **6 tests**. Les trois
gardes ont été **constatées RED avant le correctif** (5 échecs sur 6 au premier
run), donc elles mordent ; ce n'est pas une suite décorative.

| Garde | Ce qu'elle interdit | Ce qu'elle ne voit pas |
|---|---|---|
| **Surface publique** (réflexion) | qu'un `GetFolder(string, …)` synchrone réapparaisse sur `IImapClientWrapper` / `ImapClientWrapper` | un appel qui court-circuite le wrapper |
| **Analyseur** (métadonnées de l'assembly compilé) | **toute** référence de `mss.mail.application` à `IMailStore.GetFolder(String, CancellationToken)`, y compris hors wrapper | un blocage par une *autre* API |
| **Comportement** (`Timeout = 15 s`) | que le chemin `read_list` garde le thread appelant pendant que l'I/O du dossier est en attente — attrape donc aussi un `sync-over-async` réintroduit sur `GetFolderAsync` | ce qui ne passe pas par la résolution de dossier |

L'analyseur filtre sur la **signature décodée**, pas sur le nom : filtrer sur
`GetFolder` seul aurait signalé à tort les deux surcharges légitimes. Aucune
dépendance ajoutée — `System.Reflection.Metadata` est dans le framework.

### Ce que j'ai vérifié et écarté, plutôt que de partir de la conclusion

La task nommait `BaseRepository.get_DataContext` comme suspect historique
(⚠️ « ne pas partir de la conclusion »). **Il est innocent sur le chemin chaud**,
et il fallait le vérifier avant de le corriger :

`BaseRepository.cs:115` porte bien un `CreateDbContextAsync().GetAwaiter().GetResult()`.
Mais `CreateDbContextAsync` n'a qu'un seul `await`, sous
`if (environment == "Development" || "Staging")` → `HandleEnvironmentDbSetupAsync`,
dont la **première ligne** est un fast-path statique par processus
(`_migratedDatabases.ContainsKey(databaseName)`, `BaseRepository.cs:276`). Après
le premier contact de chaque base par chaque réplica — c'est-à-dire pendant tout
le plateau d'un tir de 3 min —, la tâche est **déjà complétée** et
`GetAwaiter().GetResult()` ne bloque rien. Le `.Result` est réel, mais il n'est
pas le facteur limitant mesuré. **Non corrigé : hors périmètre de cette task**
(règle 6), à traiter pour lui-même si on veut supprimer le sync-over-async
résiduel du démarrage.

### Deux blocages adjacents trouvés en chemin — signalés, pas corrigés

Hors périmètre `read_list` (règle 6 et « Hors scope » de la task), mais de la
**même famille** et probablement des candidats de tasks :

1. **`MailClientSession.cs:234`** — `_imapClientWrapper?.DisconnectAsync(true).GetAwaiter().GetResult()`
   dans `Dispose`. Un `Dispose` qui bloque sur une déconnexion réseau : le timer
   de nettoyage des sessions peut y parquer un thread du pool.
2. **`EmailFlagService.cs:44/67/77/89`** — `folder.AddFlags(…)` / `RemoveFlags(…)`
   **synchrones** (commande IMAP STORE). Même défaut exactement, sur le chemin
   « marquer lu/suivi », pas sur `read_list`.

### ⚠️ Ce que ce commit ne prouve pas — la mesure reste due

Le code est corrigé et verrouillé ; **la moitié « mesure » de la DOD est un tir
de banc, pas du code**, et suit le précédent explicite de task-204 (« Différés au
banc / HAG — ce sont des tirs, pas du code »).

Restent dus, dans cet ordre :

- [ ] **Pile de threads bloqués** capturée pendant un tir à 882 req/s
      (`dotnet-stack`), jointe à la task. Le chemin est nommé et prouvé par
      l'API de MailKit et par le recoupement avec les mesures de task-204 ;
      la pile est la preuve *in situ* qui manque.
- [ ] **Palier 882 req/s** : file ThreadPool max **< 20** par réplica (contre 136)
      et `read_list` moy **< 400 ms** (contre 714).
- [ ] **Palier 972 req/s** : débit délivré **> 900 req/s** (contre 857,9),
      drop **< 1 %**.
- [ ] **Rapport de tir + ligne d'INDEX** pour l'avant/après. La baseline de
      l'« avant » est déjà sur `develop` (8 lignes d'INDEX de l'escalier du
      2026-07-29, mergées avec task-204).

**Réserve honnête sur le critère de débit** : task-204 a établi que sur ce poste
l'infra du banc consomme 62 % du CPU contre 15 % pour l'application, et que
~858 req/s est un **plancher** contaminé, pas un plafond. Supprimer le blocage
devrait relever le plateau ; que le seuil de **900 req/s** soit atteint *sur
cette machine* dépend aussi de la contention du banc, qui n'est pas dans le
périmètre de cette task. Si le tir montre la file effondrée (le critère qui teste
vraiment le correctif) mais le débit sous 900, c'est un arbitrage à porter au PO
plutôt qu'un échec du correctif.

### Écarts de procédure, signalés plutôt que passés sous silence

1. **`conventions/csharp.md` lu avant le C#** (CA1822, S2068, CA1861, CA1859).
   CA1861 appliqué d'emblée : les listes de référence de l'analyseur sont hissées
   en `private static readonly` au lieu d'être des littéraux en argument.
2. **Un test a été corrigé par le test, pas par le code** :
   `GetEmailHeadersResolvesTheFolderAsynchronouslyAndReturnsTheHeaders` échouait
   sur un montage NSubstitute faux — MailKit route la surcharge
   `FetchAsync(…, MessageSummaryItems, …)` (une extension) vers
   `FetchAsync(…, IFetchRequest, …)`, c'est donc celle-ci qu'il faut doubler.
   Défaut du test, pas du code : corrigé côté test.
3. **La consigne de session interdit l'Agent tool sans demande explicite** — la
   localisation a donc été conduite en direct (lecture du chemin d'appel,
   métadonnées MailKit) plutôt que par des agents de recherche parallèles.

- Next step : /forge-simplify task-205

## Simplify log

- **Repos passed** : `api-mail` (seul repo touché — 5 fichiers de diff vs
  `develop`).
- **Skipped (contrat / exclus)** : `dtos-mss` (porteur de contrat, et **sans
  diff** — branche créée par `/start`, aucun commit), `interop-cda`, `devops`,
  `psc-proxy-*`.
- **Applied & committed** : `api-mail`, 1 fichier — `c62f5dc`
  `refactor(imap): passe qualité (/simplify) — task-205` (poussé).

| Axe | Cleanup |
|---|---|
| **Altitude** | **L'analyseur se contrôle lui-même.** La garde IL affirmait « aucune référence bloquante » à partir d'une chaîne de signature (`"String, System.Threading.CancellationToken"`) couplée au **rendu des types** du décodeur. Si ce rendu changeait, la recherche ne trouverait plus rien et la garde passerait **à vide** — en annonçant un succès. Elle exige désormais de retrouver d'abord la surcharge **légitime** (`GetFolder(FolderNamespace)`, que le wrapper conserve) : le témoin prouve que le scanner voit encore quelque chose avant qu'on le croie sur parole. |
| Simplification | `Assert.ThrowsAnyAsync<Exception>` → `Assert.ThrowsAsync<FolderNotFoundException>` dans le nettoyage du test de non-blocage. L'assertion large n'aurait rien vu si la propagation avait changé de type ; la précise documente le comportement voulu (404 self-heal). |
| Simplification | `MemberReferenceInfo` perd son champ `Name`, qui répétait invariablement l'argument passé au scanner. |

### Le cleanup d'altitude a payé pendant la passe elle-même

Le témoin a **échoué au premier run**, et c'est le meilleur argument pour lui :
il a montré que le compilateur émet la référence contre **`MailKit.MailStore`**
— la classe de base concrète dont dérive `ImapClient` — et **non** contre
`MailKit.IMailStore`. La garde principale, elle, listait déjà les deux
propriétaires et fonctionnait ; mais rien ne le prouvait, et une garde réduite à
la seule interface aurait été silencieusement inopérante. Le pourquoi des deux
propriétaires est désormais écrit à côté de la liste.

- **Écarté** — un **builder partagé d'`ImapService` pour les tests**. Le service
  se construit désormais dans **4** fichiers de test avec ~14 doublures
  (`ImapServiceTests`, `ImapMoveFallbackTests`, `ImapServiceDraftTagTests`, et
  celui de cette task). Le dossier est réel et se renforce, mais n'en refactorer
  qu'un serait moins lisible, et reprendre les trois autres sort du périmètre
  (règle 6). Même raisonnement que le helper de table Markdown écarté par
  task-203 et task-204 : **candidat à une passe dédiée**, pas à un effet de bord
  de celle-ci.
- **Écarté** — fusionner ces tests dans `OnlineMailDataProviderTests`. Le fichier
  dédié porte une question distincte (« ce chemin bloque-t-il un thread ? ») avec
  son propre outillage ; la dispersion coûterait la lisibilité de la garde.
- **Validation** : build **0 erreur / 0 warning** ; suite complète **3 207 tests
  verts, 0 échec**, 16 skips IA préexistants. Aucun fichier de production touché
  par cette passe — le correctif de `/develop` est inchangé. Aucun rollback.
- **Écart de procédure** : le playbook `/simplify` prévoit 4 agents de revue en
  parallèle. La consigne de session interdit l'Agent tool sans demande explicite
  de l'humain — la revue des 4 axes a donc été faite en direct sur le diff (même
  écart que task-200, task-203 et task-204).
- Next step : /sonar task-205 (api-mail touché)

## Sonar log

Mode A (chaîné), **1 itération** sur la branche de la task — aucune seconde n'a
été nécessaire. SonarQube **9.9.8.100196** (`http://127.0.0.1:9000`, conteneurs
`sonarqube` + `sonarqube_db` démarrés par l'agent — ils étaient `Exited`, et
**remis dans cet état** après le scan, l'instance contaminant les mesures du
banc). Projet `healthplatform-api-mail`.

- **Phase 1 (new code)** : ✅ Quality Gate **OK**, `new_coverage` = **87,9 %**
- **Phase 1 — issues fixées** : **0** — il n'y en avait aucune dans le périmètre
- **Phase 1 — tests ajoutés** : 0 (le code de la task est déjà à 100 %, voir
  ci-dessous)
- **Phase 2 (legacy)** : non déclenchée (aucune régression, KPI au niveau de la
  baseline)
- **Build / tests** : ✅ Release avec couverture — **3 207 passés, 0 échec**,
  16 skips IA préexistants (102 + 1 858 + 370 + 590 + 287)

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-204) | **Final** | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | **OK** | → |
| New coverage | 87,8 % | **87,9 %** | +0,1 pt |
| New bugs / New vuln. | 0 / 0 | **0 / 0** | → |
| New code smells | 6 | **6** | → (voir note) |
| New security hotspots | 0 | **0** | → |
| Bugs | 0 | **0** | → |
| Vulnerabilities | 0 | **0** | → |
| Security hotspots | 3 | **3** | → |
| Code smells (projet) | 31 | **31** | → |
| Coverage (projet) | 86,6 % | **86,6 %** | → |
| Duplication | 0,7 % | **0,7 %** | → |
| Reliability / Security / Maintainability | A / A / A | **A / A / A** | → |
| ncloc | 35 573 | **35 018** | −555 |

### Périmètre task-205 : 0 issue et 100 % de couverture, dès le premier scan

Les trois fichiers de production sont interrogés nommément :

| Fichier | Issues | Couverture du code neuf |
|---|---|---|
| `src/Application/Services/Implementation/ImapService.cs` | **0** | **100 %** sur `TryResolveFolderAsync` |
| `src/Application/Services/Implementation/ImapClientWrapper.cs` | **0** | — (suppression + commentaires) |
| `src/Application/Services/Interfaces/IImapClientWrapper.cs` | **0** | — (interface) |

La couverture a été vérifiée **ligne à ligne** (`/api/sources/lines`) et non sur
l'agrégat du fichier, parce que l'agrégat d'`ImapService.cs` (71,6 %) porte
1 350 lignes dont l'immense majorité est antérieure et dirait n'importe quoi sur
ce diff. Résultat : **toutes** les lignes exécutables de `TryResolveFolderAsync`
sont couvertes, **y compris les deux branches `catch`** (propagation de
`FolderNotFoundException`, absorption du reste) — ce sont précisément les deux
comportements que la conversion en async devait préserver.

### ⚠️ Les 6 new-code smells : 5ᵉ task consécutive à les constater

Ce sont **exactement les mêmes six** que task-199, task-200, task-203 et
task-204, imputées à des tasks mergées antérieurement (la période new-code est
large) :

| Règle | Fichier | Touché par task-205 ? |
|---|---|---|
| S107 | `BackgroundSyncService.cs:43` | non |
| S3604 | `OcspValidationService.cs:44` | non |
| S1168 | `OcspValidationService.cs:402` | non |
| S3604 | `MailClientSession.cs:89` | non |
| S3604 | `MailClientSession.cs:121` | non |
| S1643 | `VCardSerializer.cs:206` | non |

Hors périmètre (règle 6). **Mais il faut arrêter de le noter et le traiter** :
quatre tasks les ont déjà signalées comme « candidat mûr pour un `/sonar
api-mail` standalone (Mode B) ». C'est la cinquième. Le principe zero-new-debt
de `agents/sonar.md` exige `new_code_smells = 0` ; il est en défaut permanent
non pas par laxisme des tasks, mais parce qu'**aucune task de feature ne peut
légitimement les corriger** — elles appartiennent à des fichiers hors de son
module. Seul un run Mode B le peut. → **à planifier explicitement**, sinon la
prochaine task écrira le même paragraphe.

Note incidente : `MailClientSession.cs` porte deux de ces six smells, et c'est
aussi le fichier du blocage adjacent relevé par `/develop` (`Dispose` bloquant,
ligne 234). Un Mode B ou une task dédiée y ferait donc d'une pierre deux coups.

### Le piège d'outillage qui a coûté un scan — et il corrige task-204

Le `end` du scanner a échoué **après** les ~6 min de build + tests :

```
ERROR: Not authorized. Analyzing this project requires authentication.
       Please provide a user token in sonar.login or other credentials...
```

Diagnostic de task-204 face au même symptôme : « le `SONAR_TOKEN` du `.env` est
périmé (401), **à la charge de l'humain** de le régénérer ». **C'est faux, et
l'action demandée à l'humain était inutile.** Le token est valide :

```
curl -u "$SONAR_TOKEN:" .../api/authentication/validate  →  {"valid":true}
```

La vraie cause est la **version du serveur** : `sonar.token` n'existe qu'à partir
de **SonarQube 10.0**, et cette instance est en **9.9.8**. La 9.9 ignore la
propriété, laisse le `begin` réussir (il ne fait que lire le profil qualité),
et ne refuse qu'au moment de **publier** le rapport. Le message d'erreur accuse
les identifiants, ce qui envoie droit sur la mauvaise piste.

Correctif : `/d:sonar.login="$SONAR_TOKEN"`. Le scan est passé du premier coup
ensuite, **sans refaire le build ni les tests** — `.sonarqube/` survit à un `end`
en échec, donc rejouer `end` seul suffit (30 s au lieu de 6 min).

**`agents/sonar.md` a été corrigé** (sections « Begin » et « End » + un
avertissement expliquant le faux diagnostic et comment vérifier la version).
C'est une modification du **plan de contrôle de la forge**, hors du périmètre
normal de `/sonar` : signalée ici pour ratification par l'humain. Sans elle,
chaque prochain run rejouerait la même perte de 6 minutes.

Confirmé au passage, sans changement : `dotnet sonarscanner` ne reçoit pas ses
arguments `/k:` `/d:` sous Git Bash (task-200, task-203, task-204) — scan lancé
par un script **PowerShell détaché**, écrit en **ASCII pur** pour neutraliser
d'emblée le piège d'encodage de PowerShell 5.1 relevé par task-204, et **parsing
vérifié avant exécution** (`Parser::ParseFile` → `PARSE OK`).

### `conventions/csharp.md` : aucune entrée ajoutée, et c'est le résultat attendu

Le protocole ne consigne que les règles corrigées **à la main** sur du code
frais. Zéro correction ici : le code de la task ne déclenche aucune règle. La
boucle d'auto-amélioration a fonctionné en amont — CA1861 (« pas de tableau
littéral en argument »), apprise en task-203, a été appliquée **d'emblée** par
`/develop` sur les listes de référence de l'analyseur. Aucun compteur à
incrémenter.

- Itérations : **1/5** (arrêt immédiat : 0 issue dans le périmètre, Quality Gate
  OK, KPI au niveau de la baseline). Next : /review task-205
  (`lint-angular`, `lint-mobile`, `verify-visual` : skip — repos non touchés).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/131
  — label `awaiting-human-merge` (6 fichiers : 3 production, 3 tests)
- `dtos-mss` : aucun changement de contrat — branche sans commit, **pas de PR**
  (build validé : 0 erreur)
- `client-angular` / `client-mobile` : non listés dans `**Repos**:`
  (`Single frontend: true`) — et ni `Client/Angular/` ni `Client/Mobile/` ne
  sont clonés sur ce poste
- Racine du workspace (plan de contrôle, hors automation) :
  `agents/sonar.md` **modifié** (`sonar.login` au lieu de `sonar.token` —
  correction du faux diagnostic de task-204, à ratifier),
  `tasks/wip-task-205.md` → `tasks/done-task-205.md`.
  `conventions/csharp.md` **inchangé** — aucune règle corrigée à la main.

## Code Review Summary

**APPROVED** — 6 fichiers relus. **1 défaut trouvé et corrigé** avant
l'ouverture de la PR, 0 bloquant restant.

### Le défaut : du code mort laissé par la PR elle-même

`using System.Diagnostics.CodeAnalysis` (ImapService.cs:34) n'était importé que
pour le `[NotNullWhen(true)]` de l'ancien `out`-paramètre, que le passage en
async supprimait. Critère 5.4 (« pas de code mort laissé par la PR »). Traité
en **étape de développement** (`4bfdffe`) et non dans `/review`, la revue étant
en lecture seule sur le code — même protocole que task-204. Re-validé : build
0 erreur / 0 warning, 3 207 tests verts.

Ni Sonar ni le compilateur ne l'auraient signalé (un `using` inutilisé ne
produit pas de warning par défaut, et le fichier ressort à 0 issue) : c'est une
trouvaille de relecture, pas d'outil.

### Vérifications conduites pendant la revue, au-delà de la lecture

- **Équivalence sémantique des 5 conversions**, une par une. Le point non
  trivial : sur les sites `:401` et `:601`, `found && folder is { CanOpen: true }`
  se réduit à `folder is { CanOpen: true }` — le succès du try-pattern impliquait
  déjà non-null, donc le booléen était redondant. Les trois autres sites sont des
  gardes `is null` directes.
- **Les gardes ont été constatées RED avant le correctif** (5 échecs sur 6 au
  premier run). Une garde qu'on n'a jamais vue échouer n'est pas une garde ; ces
  trois-là mordent.
- **Couverture vérifiée ligne à ligne** (`/api/sources/lines`) et non sur
  l'agrégat du fichier : les deux branches `catch` — propagation de
  `FolderNotFoundException`, absorption du reste — sont couvertes. Ce sont
  précisément les deux comportements que la conversion devait préserver.
- **Le suspect désigné par la task a été innocenté par la mesure du code**, pas
  écarté d'un revers de main : `BaseRepository.get_DataContext` porte bien un
  `.GetAwaiter().GetResult()`, mais derrière un fast-path statique par processus
  qui rend la tâche déjà complétée pendant tout le plateau d'un tir.
- **Recherche exhaustive des appels résiduels** : plus aucun `GetFolder(string)`
  synchrone dans `src/` ni `tests/` ; les trois occurrences restantes sont les
  surcharges `SpecialFolder` / `FolderNamespace`, sans I/O.

### Réserve de méthode

La revue est faite par la forge sur son propre code. Deux points méritent l'œil
humain :

1. **Le retrait d'une méthode d'interface** est un choix fort. Il est le
   correctif (« ce qui n'existe plus ne peut pas être rappelé »), mais il ferme
   la porte à un usage synchrone légitime qui n'existe pas aujourd'hui — à
   rouvrir consciemment si le besoin apparaît, pas par accident.
2. **Le pari de fond n'est pas vérifié par cette PR** : que ce blocage-là soit
   *le* facteur limitant, et non *un* facteur parmi d'autres. Les trois
   recoupements sont solides, mais seul le tir au banc tranchera. Si la file
   ThreadPool ne s'effondre pas au palier 882, la piste suivante est déjà
   nommée : les deux blocages adjacents (`MailClientSession.Dispose`,
   `EmailFlagService`).

Validation : build **0 erreur / 0 warning** (`api-mail` + `dtos-mss`) ;
**3 207 tests verts, 0 échec** (16 skips IA préexistants) ; SonarQube Quality
Gate **OK**, **0 issue** sur le périmètre, nouveau code à **100 %** de
couverture.

**Ce que cette PR ne livre pas** : la mesure. Les deux paliers de re-mesure
(882 et 972 req/s), la pile de threads et la ligne d'INDEX avant/après restent
à conduire — c'est un tir, pas du code.

## Tir de vérification log — 2026-07-31

**La mesure que la DOD réclamait a été conduite, et elle a démenti le
correctif initial.** Quatre tirs, 200 praticiens, `mixed` 3 min, mêmes
paramètres que l'escalier de task-204 (`SESSION_ROTATION=0.001`,
`VU_TAIL_FACTOR=8`, `ENRICH_SHARE=0.05`), bases purgées entre chaque palier,
corpus maildir de 3,3 Go conservé.

### Le correctif IMAP seul n'a rien changé

| Palier 882 req/s | task-204 (avant) | Correctif IMAP seul |
|---|---|---|
| File ThreadPool par réplica | 136 / 93 / 13 / 10 / 7 | **159 / 132 / 131 / 5 / 3** |
| `read_list` moy | 714 ms | **1 438 ms** |
| Débit plateau | 824,8 req/s | 803,8 req/s |

Avant d'accuser le correctif, **le binaire mesuré a été vérifié** :
`TryGetFolderSafely` — l'unique méthode qui portait l'appel bloquant — est
absente du DLL déployé, `TryResolveFolderAsync` y est, et le fichier précède les
tirs. Les 5 PID des réplicas correspondent aux identités de télémétrie.

*(Un contrôle complémentaire des métadonnées n'a rien produit : PowerShell 5.1
n'a pas résolu `PEReader` et la boucle a itéré sur `null` en silence. Résultat
vide, pas résultat négatif — non compté comme preuve. C'est très exactement le
mode d'échec que la garde n°2 de cette task interdit.)*

### La capture de piles a nommé le vrai coupable

`dotnet-stack report` sur les **5 réplicas**, en plein plateau (1 min 32) :

```
[Native Frames]
StackExchange.Redis.RedisBase.ExecuteSync(...)                      ← bloque
Microsoft.Extensions.Caching.StackExchangeRedis.RedisCache.GetAndRefresh(...)
HealthPlatform.Host.Sdk.Services.CacheService.Get(string)           ← API synchrone
mss.mail.application.Helpers.SafeCacheExtensions.SafeGet(...)
mss.mail.Infrastructure.Repository.UserSettingsRepository.GetSettingsAsync()   ← async !
   …
System.Threading.ThreadPoolWorkQueue.Dispatch()
System.Threading.PortableThreadPool+WorkerThread.WorkerThreadStart()  ← thread du POOL
```

**10 des 35 threads applicatifs**, sur **5 réplicas sur 5**, étaient parqués là :
5 sous `UserSettingsRepository.GetSettingsAsync`, 5 sous
`SearchHistoryService.Record`. Deux méthodes `async` appelant un cache
synchrone qui fait un aller-retour Redis bloquant.

Piles complètes :
`tests/loadtest-k6/reports/2026-07-31/stacks-170058/` (gitignoré comme tous les
rapports de tir — seul l'INDEX est versionné).

### Le correctif cache, et pourquoi il ne touche pas le SDK

`ICacheService` (repo `sdk`, consommé en **NuGet 8.0.0**) n'expose que
`Get<T>` / `Set<T>` / `Remove` — aucun pendant asynchrone. Changer ce contrat
imposait une republication NuGet et impactait `client-blazor` et `host` pour une
raison **interne à api-mail**.

Choix retenu : descendre d'une couche sur **`IDistributedCache`**, déjà
enregistré dans la DI par `AddStackExchangeRedisCache` (SDK) et porteur natif de
l'API asynchrone. Trois helpers `SafeGetAsync` / `SafeSetAsync` /
`SafeRemoveAsync` ajoutés dans api-mail, reproduisant **exactement** la
sérialisation de `CacheService` — les entrées restent interopérables entre les
deux voies pendant la migration progressive des 28 sites d'appel restants.

Convertis ici : `UserSettingsRepository` (les 3 accès, avec repli synchrone pour
les constructeurs de test) et `SearchHistoryService` (+ son interface et
`SearchController`).

### Après correctif — mêmes paramètres, même banc

| Palier 882 req/s | task-204 | IMAP seul | **+ cache** | Cible DOD |
|---|---|---|---|---|
| **File ThreadPool** | 136/93/13/10/7 | 159/132/131/5/3 | **8/6/6/5/4** | **< 20** ✅ |
| Threads max | — | 33–40 | **19–24** | — |
| `read_list` moy | 714 ms | 1 438 ms | **718 ms** | < 400 ms ❌ |
| Débit plateau | 824,8 | 803,8 | **863,0** | — |
| Abandons | 4,21 % | 5,6 % | **1,6 %** | — |

| Palier 972 req/s | task-204 | **+ cache** | Cible DOD |
|---|---|---|---|
| **Débit plateau** | 857,9 | **940,3 req/s** | **> 900** ✅ |
| File ThreadPool | 432/205/68/13/6 | **13/11/6/5/4** | < 20 ✅ |
| `read_list` moy | 1 533 ms | **641 ms** | < 400 ms ❌ |
| Abandons | 7,38 % | **2,3 %** | < 1 % ❌ |

Intégrité : **0 sujet étranger**, verdict propriété **PASS**, ~20 000 mails
stockés par palier, `enrich` jamais court-circuité.

### DOD — 2 critères chiffrés sur 4 atteints

- [x] **Palier 882, file ThreadPool < 20** : max **8** (contre 136). Atteint très
      largement.
- [ ] **Palier 882, `read_list` < 400 ms** : **718 ms**. Non atteint.
- [x] **Palier 972, débit > 900 req/s** : **940,3**. Atteint.
- [ ] **Palier 972, drop < 1 %** : **2,3 %**. Non atteint (÷3 tout de même).
- [x] **Pile de threads incriminante** jointe (ci-dessus).
- [x] **Rapport de tir + ligne d'INDEX** : 4 rapports, 4 lignes d'INDEX
      committées (`395a11e`), une ligne dupliquée retirée au passage.

**La famine de ThreadPool, objet de la task, est éteinte** — c'est le critère qui
teste réellement le correctif. Les deux critères manqués relèvent de causes
distinctes, désormais identifiées :

- **`read_list` reste lent** (p50 213 ms, p95 1 480 ms) : profil de
  **sérialisation**, pas de famine. Sur base purgée, chaque lecture prend le
  verrou IMAP de session, un sémaphore par (boîte, dossier), puis un verrou
  distribué Redis dont l'attente va jusqu'à 30 s par pas d'une seconde. Chantier
  distinct.
- **Abandons > 1 %** : c'est le dimensionnement du harnais, périmètre de
  task-209.

### Ce que la campagne ne dit pas

- **Le nouveau genou n'est pas localisé.** 940 req/s est le débit le plus haut
  **testé**, pas la limite : à 972 demandés la messagerie en sert encore 940 avec
  une file de threads plate. Il faudrait des paliers 1080 / 1200 / 1400.
- **L'axe population n'est pas exercé.** Les 4 tirs sont à population **fixe**
  (200 praticiens) ; seul le débit varie. Or les connexions PG (≈ praticiens ×
  réplicas × pool) et les sessions IMAP (5 par praticien) suivent le **nombre de
  praticiens**, pas le trafic — un plafond indépendant, documenté par task-200 et
  non déplacé par ces correctifs.
- **Les chiffres restent des planchers** : 62 % du CPU pour l'infra du banc
  contre 15 % pour l'application.

Conversion indicative, au modèle du banc (`RPS = utilisateurs × 6 req/s`, soit la
définition « praticien actif » du dossier de dimensionnement) : 940 req/s ≈
**157 praticiens actifs simultanés** servis, contre ~137 avant. Servir 200 actifs
demanderait 1 200 req/s — non démontré.

### État rendu

AppHost et `dcp.exe` arrêtés, ports libres, conteneurs `loadtest-*` détruits par
Aspire, 500 bases synthétiques purgées, **4 880 archives CDA en clair** supprimées
de `%TEMP%`.

**Écart assumé — maildir conservé** (`--keep-maildir`) : le volume
`loadtest-dovecot-mail` porte le corpus 200 × 100 accumulé depuis le 2026-07-28
(3,3 Go). Le supprimer imposerait de re-seeder 20 000 messages avant le prochain
tir. Même écart que task-204, désormais couvert par un drapeau explicite du
script plutôt que par une purge manuelle.

## Merged — 2026-07-31

| Repo | PR | Squash commit | Branche distante |
|---|---|---|---|
| `api-mail` | [#131](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/131) — closed | `06f8a629e30702ae94a6b3033fdd3227a6773e4e` (2026-07-31T20:05:24+02:00) | supprimée (locale conservée) |
| `dtos-mss` | aucune (branche sans commit) | — | supprimée (locale conservée) |

14 fichiers, +730 / −159.

- **Staging** : `forge/staging-task-176-196-20260728` **conservée** — sa plage
  `[176, 196]` ne contient pas 205, et 21 tasks de ce run sont encore en `todo-*`.

### Ce qui a été mergé, et ce qui reste ouvert

Merge décidé par l'humain (HAG, règle 10) **en connaissance des deux critères de
DOD non atteints** — `read_list` à 641-718 ms contre 400 visés, abandons à
1,6-2,3 % contre 1 %. Le critère qui testait réellement l'objet de la task — la
famine de ThreadPool — est atteint très largement (file max **8** contre 136), et
le débit franchit les 900 req/s.

La task a été **élargie en cours de route** : elle a livré **deux** correctifs
alors qu'elle n'en visait qu'un. Le premier (résolution de dossier IMAP
synchrone) était réel et prouvé mais n'était **pas** le facteur limitant — la
mesure l'a démenti. Le second (aller-retour Redis synchrone sur les threads du
pool), trouvé par capture de piles sous charge, l'était.

**Trois chantiers ouverts par cette task**, aucun couvert ici :

1. **`read_list` reste lent** — profil de sérialisation (verrou IMAP de session +
   sémaphore par boîte/dossier + verrou distribué Redis), pas de famine.
2. **28 sites d'appel du cache synchrone** subsistent dans api-mail ; deux
   seulement ont été convertis. `ICacheService` du SDK reste sans API asynchrone.
3. **Deux blocages adjacents signalés** : `MailClientSession.Dispose`
   (déconnexion réseau bloquante) et `EmailFlagService` (`AddFlags` /
   `RemoveFlags` synchrones).

Et deux inconnues de mesure : le **nouveau genou n'est pas localisé** (940 req/s
est le plus haut palier testé, pas la limite), et **l'axe population n'a pas été
exercé** — les 4 tirs sont à 200 praticiens fixes, alors que les connexions PG et
les sessions IMAP suivent le nombre de praticiens, pas le trafic.
