# todo-task-188.md — Plan de contrôle de la synchronisation : pause inopérante, état perdu, sync fantôme

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes sessions IMAP et
> concurrence).

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | 1. Pause inopérante (DI `Scoped`) | `DependencyInjection.cs:37` | **`:48-49`** — `AddScoped<IBackgroundSyncService>` **et** `AddScoped<ISyncPauser>(sp => sp.GetRequiredService<IBackgroundSyncService>())`, inchangé | inchangé |
> | État de pause en champ d'instance | `BackgroundSyncService.cs:29` | **`:32`** (`private volatile bool _isPaused`), lu par `WaitWhilePausedAsync` **`:469`** de la **même** instance | inchangé |
> | Résolution dans un autre scope | `BackgroundSyncManager.cs:146` | **`:163`** — `scopedProvider.GetRequiredService<IBackgroundSyncService>()` | inchangé |
> | Appel de pause qui ne met rien en pause | `ImapService.cs:1197` | **`:2176`** (`syncPauser?.PauseSync()`), reprise **`:2186`** | inchangé |
> | 2. TTL d'état à 15 min | `RedisSyncStateStore.cs:29` | **`:28`** (`StateTtl`), posé en `SET NX` **`:105`**, rafraîchi **`:140`** — seul appelant `BackgroundSyncNotifier.cs:30` | inchangé |
> | Écrasement du runtime vivant | `:101-117` | **`:134`** (`_localRuntime[userEmail] = runtime`) | inchangé |
> | 3. Gardes muets avant démarrage | `:236-252`, `:364-379` | **`:274`, `:298`, `:419`, `:427`, `:446`** — cinq sites `runtime.SyncService is not null` sans branche `else` | inchangé, **plus étendu** |
>
> Le nombre de sites gardés par `SyncService is not null` est passé de deux à
> **cinq**. La forme du défaut n'a pas changé ; sa surface a grandi.

## Objective

Rendre le pilotage de la synchronisation d'arrière-plan **effectif et cohérent** :
quand le praticien met en pause, la synchronisation s'arrête ; quand il consulte
l'état, l'état est vrai ; quand il relance, il ne crée pas une synchronisation
fantôme.
En cas de logout la synchronisation doit se terminer imédiatement.

Trois défauts indépendants concourent au même symptôme — des boutons qui semblent
morts et une synchronisation incontrôlable :

1. **La pause de la synchronisation par le premier plan ne fait rien** —
   `ISyncPauser` est enregistré en *scoped*, donc l'appel de pause construit une
   **instance neuve** dont l'état `_isPaused` n'est lu par personne, tandis que la
   synchronisation réellement en cours possède la sienne.
2. **L'état Redis expire pendant une synchronisation longue**, car son TTL n'est
   rafraîchi que par une notification de progression — qu'une synchronisation sans
   UID manquant n'émet jamais.
3. **Pause et reprise sont ignorées** si elles arrivent avant que le travail mis en
   file n'ait démarré.

**US backend-only (justification)** : orchestration côté serveur. Le contrat HTTP
est inchangé, mais le comportement observé par les frontends change (les boutons
fonctionnent).

### Preuve (état actuel du code)

**1. Pause inopérante** — `src/Api/DependencyInjection.cs:37` :
```csharp
services.AddScoped<IBackgroundSyncService, BackgroundSyncService>();
services.AddScoped<ISyncPauser>(sp => sp.GetRequiredService<IBackgroundSyncService>());
```
L'état de pause est un champ d'instance
(`private volatile bool _isPaused`, `BackgroundSyncService.cs:29`), lu uniquement par
`WaitWhilePausedAsync` de **la même** instance. Or la synchronisation en cours a été
résolue dans un **autre** scope : `BackgroundSyncManager.cs:146` fait
`scopedProvider.GetRequiredService<IBackgroundSyncService>()` sur un scope créé par
la file de travaux. L'appel `syncPauser?.PauseSync()` de
`src/Application/Services/Implementation/ImapService.cs:1197` journalise donc
« Sync paused » et **ne met rien en pause**.

Conséquences observables : une **seconde** connexion IMAP concurrente à la même
boîte pendant chaque consultation (certains serveurs plafonnent les connexions par
boîte et refusent alors la connexion de premier plan), les deux chemins insérant
les mêmes UID — la course que `ImapService.cs:1529` avale en « Failed to save
header for UID={UID}, may already exist » — et des logs « Sync paused » alors que
la synchronisation continue visiblement.

**2. TTL de l'état Redis** —
`src/Application/Services/Implementation/RedisSyncStateStore.cs:29` : TTL de
15 minutes, posé en `SET NX`. Le **seul** appel de rafraîchissement est
`src/Api/Hubs/BackgroundSyncNotifier.cs:22`, atteint uniquement depuis
`ProcessMissingUidsBatchesAsync` et seulement si l'étranglement l'autorise
(`BackgroundSyncService.cs:355-358`). Une synchronisation **sans UID manquant**
n'entre jamais dans cette méthode : le parcours des dossiers
(`BackgroundSyncService.cs:232-246`) peut largement dépasser 15 minutes sans un seul
rafraîchissement. Le second garde-fou, le verrou distribué, expire à **30** minutes
— les deux se désynchronisent.

Scénario : passé la minute 15, la clé expire. Le praticien relance ; l'état dit
« inactif », le démarrage réussit et `_localRuntime[userEmail] = runtime`
**écrase** le runtime vivant (`BackgroundSyncManager.cs:101-117`), orphelinant son
jeton d'annulation. Le nouveau travail échoue à prendre le verrou distribué, et son
`finally` (`:169-170`) **efface l'état de la synchronisation encore en cours**.
Dès lors l'état affiche « inactif », l'arrêt répond « aucune synchronisation
active » et ne fait rien, et chaque relance est un coup dans le vide pendant
30 minutes — tandis que la synchronisation orpheline continue de solliciter IMAP et
la base.

**3. Pause/reprise avant démarrage** —
`src/Application/Services/Implementation/BackgroundSyncManager.cs:122-150` :
`runtime.SyncService` n'est affecté qu'au moment où la file dépile le travail. Les
deux branches de pause (`:236-252` locale, `:364-379` commande distante) sont
gardées par `runtime.SyncService is not null` et, sinon, **ne font rien** — ni
report, ni erreur. `StopSyncAsync` y échappe car il annule directement le jeton.

### Contenu attendu

1. **Pause effective** : l'ordre de pause doit atteindre l'instance qui exécute
   réellement la synchronisation (état partagé correctement porté, ou signal passant
   par le même canal que l'arrêt — qui, lui, fonctionne). Corriger l'enregistrement
   DI en conséquence.
2. **Durée de vie de l'état alignée sur la réalité** : le TTL doit être rafraîchi
   par le fait que la synchronisation **vit**, indépendamment de toute progression
   métier (battement de cœur), et les deux garde-fous (état et verrou distribué)
   doivent être cohérents entre eux.
3. **Pas d'écrasement de runtime** : un démarrage ne doit jamais remplacer un
   runtime vivant ; et un travail qui échoue à prendre le verrou ne doit **jamais**
   effacer l'état d'une synchronisation qui tourne.
4. **Pause/reprise avant démarrage** : l'ordre doit être mémorisé et appliqué au
   démarrage effectif, ou refusé explicitement — jamais ignoré en silence.
5. **Vérité de l'état** : l'état exposé (`/sync/status`) doit refléter la réalité ;
   arrêt et relance doivent être fiables à tout instant.

### Hors scope

- Le cycle de vie des sessions IMAP → task-187.
- La performance de la synchronisation elle-même.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : l'ordre de pause émis depuis une requête atteint l'instance
      qui exécute la synchronisation (ce test doit échouer sur le code actuel — le
      vérifier explicitement)
- [ ] Test unitaire : une synchronisation en pause **cesse effectivement** de
      solliciter IMAP, et reprend sur ordre de reprise
- [ ] Test unitaire : une synchronisation longue **sans progression métier**
      conserve son état (TTL rafraîchi par battement de cœur)
- [ ] Test unitaire : un démarrage alors qu'une synchronisation tourne n'écrase pas
      le runtime vivant et n'orpheline aucun jeton d'annulation
- [ ] Test unitaire : un travail qui échoue à prendre le verrou distribué n'efface
      **pas** l'état de la synchronisation en cours
- [ ] Test unitaire : pause reçue **avant** le démarrage effectif ⇒ appliquée au
      démarrage (ou refusée explicitement), jamais ignorée
- [ ] Test unitaire : l'état exposé est cohérent à tout instant (en cours, en
      pause, arrêtée) ; l'arrêt fonctionne dans chacun de ces états
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Pause effective** : lancer une synchronisation complète sur une boîte fournie,
   puis cliquer sur pause. **Attendu** : le trafic IMAP s'arrête (visible dans les
   logs et les métriques de sessions actives) et la progression se fige. Avant
   correctif, la ligne « Sync paused » apparaît mais la synchronisation continue.
3. Reprendre → la synchronisation repart où elle en était.
4. **Concurrence premier plan / arrière-plan** : pendant une synchronisation,
   naviguer dans les dossiers. **Attendu** : pas de seconde connexion IMAP
   concurrente à la même boîte, pas de « may already exist » en rafale.
5. **Synchronisation longue sans nouveaux messages** : lancer une synchronisation
   sur une boîte **déjà synchronisée** et volumineuse, et laisser passer 15 minutes.
   **Attendu** : `/sync/status` continue d'indiquer « en cours ». Avant correctif,
   l'état repasse à « inactif ».
6. **Sync fantôme** : dans cette situation, presser à nouveau « lancer », puis
   « arrêter ». **Attendu** : l'arrêt arrête réellement. Avant correctif, l'arrêt
   répond « aucune synchronisation active » et la synchronisation orpheline continue
   pendant 30 minutes.
7. **Pause immédiate** : lancer une synchronisation puis cliquer pause **aussitôt**
   (avant démarrage effectif) → la pause est bien prise en compte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — maîtrise par le praticien
  des traitements en cours sur sa boîte MSSanté
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — les ordres de pilotage restent portés par
  l'identité du praticien propriétaire de la boîte
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : journaliser démarrage, pause, reprise et arrêt de
  synchronisation avec leur **effet réel** (une trace « pause » qui ne met rien en
  pause est une trace mensongère — c'est l'objet même du correctif)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement ni de divulgation.

## Branches

- `api-mail` (pushed) : `fix/task-188-sync-control-plane` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-188-sync-control-plane

Aucun autre repo : la task est backend-only (`**Repos**: api-mail`, justification
« orchestration côté serveur, contrat HTTP inchangé »). `dtos-mss` n'est pas
auto-inclus (branche paresseuse depuis le 2026-09-16) — aucun contrat n'est
attendu en changement ici.

## Timings

*(généré par `tools/timing/report.sh --task task-188 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 53 s | — | — | — | — |
| /develop | ok | 47 min 48 s | 10 (3 min 08 s) | 9 (8 min 17 s) | — | api-mail 10B/9T |
| **Total cycle** | | **48 min 41 s** | **10 (3 min 08 s)** | **9 (8 min 17 s)** | **0 (0.0 s)** | |

## Develop log

- **Repos touchés** : `api-mail` (backend-only, conformément à `**Repos**:`)
- **DTOs publiés** : aucun changement de contrat — `SyncStatusDto`/`SyncProgressDto`
  inchangés, donc aucune branche sur `dtos-mss`, aucun paquet NuGet republié.
- **Interop publié** : aucun changement.

### Vérification RED explicite (DOD, item 1)

La DOD exigeait que le test de l'ordre de pause **échoue sur le code actuel**, et
que ce soit vérifié. Deux tests ont été écrits et lancés **avant** toute
modification du code de production :

| Test | Résultat sur `develop` |
|---|---|
| `CaptiveDependencyTests.Le_port_de_pause_du_premier_plan_n_est_pas_le_worker_de_synchronisation` | **RED** — `IBackgroundSyncService` satisfaisait `ISyncPauser`, ce qui rendait l'alias DI naturel et invisible |
| `SyncControlPlaneTests.Une_pause_recue_avant_le_demarrage_est_appliquee_au_demarrage` | **RED** — `Expected to receive exactly 1 call matching: PauseSync() — Actually received no matching calls` |

### Ce qui a été corrigé

| Défaut | Correctif |
|---|---|
| 1. Pause inopérante | `ISyncPauser` n'est plus un alias de `IBackgroundSyncService` (le lien d'héritage entre les deux est rompu). Nouvelle implémentation unique `SyncPauser`, scopée, qui délègue au `IBackgroundSyncManager` — seul détenteur du runtime vivant. |
| 1 bis. Régression évitée en chemin | Une **cession au premier plan** est comptée séparément de la **pause du praticien** : elle ne publie pas l'état « en pause » et, en se rendant, n'annule pas une pause explicite. Sans cette distinction, une simple navigation dans les dossiers aurait relancé une synchronisation que le praticien venait de suspendre. |
| 2. TTL d'état | Battement de cœur porté par le worker (`RunLeaseHeartbeatAsync`), qui renouvelle **l'état partagé ET le verrou distribué**. Les deux garde-fous partagent désormais une seule durée (`BackgroundSyncOptions.SyncLeaseTtl`, 15 min) au lieu de 15 et 30 min. Le `RefreshAsync` opportuniste de `BackgroundSyncNotifier` est retiré : une garantie, un propriétaire. |
| 2 bis. Écrasement de runtime | Réservation locale par `TryAdd` **avant** le créneau distribué. Le retrait est borné à l'instance concernée (`ReleaseRuntime`, retrait par paire clé/valeur). |
| 2 ter. Effacement de l'état d'autrui | `IBackgroundSyncService.StartSyncAsync` rend un `SyncRunOutcome` : un travail qui n'a pas pris le verrou n'efface rien. |
| 3. Pause/reprise avant démarrage | L'ordre est mémorisé sur le runtime et appliqué à l'attachement du worker (`ApplyPauseState`). Les deux branches — locale et commande distante — passent par le même chemin ; elles divergeaient. |
| 3 bis. Défaut découvert par le test | `BackgroundSyncService.StartSyncAsync` remettait `_isPaused = false` au démarrage, ce qui **annulait une ligne plus loin** l'ordre que le correctif venait d'appliquer. Retiré. Trouvé par `StartSyncAsync_WhilePaused_StopsCallingImapAndResumesOnOrder`, pas par relecture. |
| 5. Vérité de l'état | `GetStatusAsync` ne sert plus l'`Idle` du worker tant qu'il n'est pas entré dans sa boucle : c'était vrai de lui, faux de la boîte, et c'est cette réponse qui invitait à relancer — geste par lequel naissait la synchronisation fantôme. |

### Choix de conception à connaître

**La cession au premier plan est délibérément locale à l'instance** (pas de
diffusion sur le bus inter-instances), alors que la pause du praticien, elle,
traverse. La porter sur le bus exposerait à une **reprise perdue** — instance
émettrice disparue avant son `finally` — qui laisserait la synchronisation
suspendue indéfiniment : pire que le défaut réparé ici. Le partage d'une boîte
entre instances relève du cycle de vie des sessions IMAP, hors scope
(task-187). L'asymétrie est documentée sur `IBackgroundSyncManager.HoldForForeground`.

### Build / tests

- `dotnet build HealthPlatform.Api.Mail.sln` : **0 erreur**
- `dotnet test HealthPlatform.Api.Mail.sln` : **4 492 réussis, 0 échec**, 16 ignorés
- **Flaky pré-existant rencontré une fois** :
  `mss.mail.integration.tests.Repository.SeededThreadsAreCountableTests.AThreadedCorpusProducesCountableThreads`
  — vert sur deux passes complètes antérieures et vert en isolation au
  re-lancement. Sans rapport avec le plan de contrôle (semis de corpus en base).

### Tests ajoutés (12)

- `SyncControlPlaneTests` (9) : ordre de pause d'une requête atteignant le worker ;
  cession n'annulant pas la pause du praticien ; reprise après la **dernière**
  cession rendue ; pas d'écrasement de runtime vivant ; pas d'effacement de l'état
  d'autrui ; libération du créneau par une synchronisation qui a tourné ; pause
  avant démarrage ; cohérence de l'état en file / en cours / en pause avec arrêt
  fonctionnel dans chacun ; arrêt avant démarrage effectif.
- `BackgroundSyncServiceTests` (+4) : bail renouvelé sans progression métier ;
  battement qui s'arrête avec la synchronisation ; verrou pris pour la durée
  configurée ; pause qui cesse effectivement de solliciter IMAP et reprend.
- `CaptiveDependencyTests` (+1) : garde de composition sur la séparation des deux
  ports.

- **Conventions** : `conventions/csharp.md` relu avant d'écrire ; aucune règle
  apprise enfreinte, aucune nouvelle entrée à créer à ce stade.
- **Prochaine étape** : `/sonar task-188`

### Passe qualité (`/simplify`) — appliquée

Quatre relectures (reuse / simplification / efficacité / altitude). Appliqué :

- **Reuse** : clé du verrou remontée dans `RedisKeys.Lock.BackgroundSync` (littéral
  inchangé — le renommer ferait cesser de s'exclure deux instances de versions
  différentes pendant un déploiement) ; un seul script Lua « comparer le détenteur,
  puis agir » pour `ReleaseAsync` et `TryRenewAsync` ; `TestWait.UntilAsync` remplace
  la 6ᵉ copie d'une boucle d'attente (dont une identique dans le même assembly, migrée) ;
  `DeferredBackgroundTaskQueue` rejoint `EagerBackgroundTaskQueue`.
- **Simplification** : `AdjustForegroundHolds(email, delta)` fusionne deux méthodes
  jumelles ; une seule section critique par ordre (`ApplyPauseStateLocked` appelée
  sous le verrou du mutateur) ; fabrique `CreateService` dans les tests du worker ;
  `SyncLockKey`, `LocalSyncRuntime.Email` et un `<returns>` recopié retirés.
- **Efficacité** : `TryRemove(KeyValuePair)` au lieu d'un cast `ICollection` ;
  `RedisValue` construit depuis un `long` sans chaîne intermédiaire.
- **Doc corrigée** : le garde-fou sur un intervalle de battement nul était présenté
  comme « réservé aux tests ». C'en est un de **configuration** — `PeriodicTimer`
  lève sur une telle valeur — et il passe en `Warning`.

**Écarté délibérément, et pourquoi** :

| Finding | Décision |
|---|---|
| **Supprimer le verrou distribué du worker** : `TryStartAsync` est déjà un `SET NX` + TTL et porte l'instance propriétaire, donc strictement meilleur mutex. Ferait disparaître `SyncRunOutcome`, `TryRenewAsync` et son script. | **Écarté ici.** Restructure le modèle de concurrence — hors d'une passe qualité, qui ne doit pas changer le comportement — et **contredit la DOD**, qui exige explicitement un test « un travail qui échoue à prendre le verrou distribué n'efface pas l'état ». À arbitrer par le PO : c'est la meilleure observation des quatre relectures et elle mérite sa propre US. |
| Faire porter le bail par le gestionnaire (`await using var lease = …`) plutôt que par le worker | Même raison — dissout dans la précédente. |
| `GetStatusAsync` : ne prendre du worker que la progression | Écarté : change le comportement observable et l'attente d'un test **existant** (`GetStatusAsync_WhenServiceReturnsStatus_ReturnsServiceStatus`), qu'on ne réécrit pas pour arranger un refactor. |
| Supprimer `PauseApplied` au profit de `worker.IsPaused` | Écarté : rendrait l'assertion « un seul `PauseSync()` pour deux cessions » dépendante du comportement d'un substitut. Le champ reste, sa doc passe de 4 lignes à 1. |
| Fusionner `PauseSyncAsync`/`ResumeSyncAsync`/branches distantes en une méthode paramétrée | Écarté : duplication de forme **préexistante**, et les quatre diffèrent par leur garde d'état. |

- **Re-validation après la passe** : build 0 erreur, **4 493 tests verts, 0 échec**.
