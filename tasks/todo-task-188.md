# todo-task-188.md — Plan de contrôle de la synchronisation : pause inopérante, état perdu, sync fantôme

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes sessions IMAP et
> concurrence).

## Objective

Rendre le pilotage de la synchronisation d'arrière-plan **effectif et cohérent** :
quand le praticien met en pause, la synchronisation s'arrête ; quand il consulte
l'état, l'état est vrai ; quand il relance, il ne crée pas une synchronisation
fantôme.

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
