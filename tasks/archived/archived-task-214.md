# todo-task-214.md — Dix-neuf acquisitions du verrou de session sur vingt ne sont pas mesurées : la table qui juge task-213 ne peut afficher qu'un seul appelant

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-211 (mergée) — a posé les histogrammes de verrou ;
task-213 (mergée, `42f21ed`) — a posé l'étiquette `operation` ; le correctif de
buckets `1be290d` — sans lui les histogrammes sont illisibles
**Priorité**: **1** — **bloquant**. La contre-épreuve de task-213 et la campagne
de confirmation groupée (task-205, 202, 206, 211, 201) produiraient toutes une
table aveugle tant que ce défaut tient.

> **Ce n'est pas une demande d'instrumentation supplémentaire.** C'est la
> réparation d'une mesure qui existe, qui est publiée dans les rapports de tir,
> et qui a **déjà produit une conclusion fausse** dans un `.md` livré.

## Objective

Qu'aucune acquisition du sémaphore de session IMAP n'échappe aux histogrammes
`mssante_lock_wait_duration_seconds` / `mssante_lock_hold_duration_seconds` —
de sorte que la table « `imap_session`, par opération » du rapport de tir nomme
réellement les opérations qui attendent et celles qui détiennent, au lieu de
n'en montrer qu'une par construction.

**US backend-only (justification)** : télémétrie interne d'`ImapLockScope` /
`MailClientSessionManager`. Aucun contrat, aucun écran, aucun changement de
comportement fonctionnel attendu.

## Le défaut, établi par lecture du code

`MailClientSessionManager` expose **deux** API pour le **même** sémaphore
(`session.ImapLock`) :

| API | Sites d'appel | Émet `mssante_lock_*` ? |
|---|---|---|
| `AcquireLockWithIdAsync` / `ReleaseLockWithId` | **1** — `ProcessEmailUidAsync` (`ImapService.cs:1763`) | **oui** — `MailClientSessionManager.cs:223, 236, 265` |
| `AcquireLockAsync` → `ImapLockScope.AcquireAsync` / `DisposeAsync` | **~20**, dont `AppendToSentAsync` (`ImapService.cs:2803`), `AppendToDraftsAsync`, les six méthodes d'`ImapFolderService`, `EmailFlagService` | **non** — `ImapLockScope.cs` ne référence pas `MailProcessingMetrics` |

Conséquence directe : la table par opération **ne peut afficher que
`ProcessEmailUid`**, sur n'importe quel tir, passé ou futur. Ce n'est pas une
décomposition du verrou — c'est le seul appelant instrumenté.

## Ce que ce défaut a déjà fait dire de faux

Le rapport de vérification de task-213
(`reports/2026-08-01/report-mixed-mssante-60vu-164903.md`) écrit :

> ⓘ Aucune acquisition `AppendToSent` sur la fenêtre — le tir n'a pas archivé
> d'envoi, la ligne qui juge task-213 est donc absente.

**L'archivage a tourné.** Trois éléments du même rapport l'établissent :

- GreenMail (puits SMTP) à **0,38 cœur de moyenne**, 1,33 en pointe — pas un
  conteneur au repos ;
- 13 973 opérations `send`, **0,38 % d'erreurs**, checks à 99,6 % — les envois
  aboutissent, donc `sendResult.Value` est non nul, donc `AppendToSentAsync` est
  appelée (`MailController.cs:1013`) ;
- **sessions Dovecot à 5 002** contre ~2 500 avant task-213 — c'est très
  exactement la seconde connexion ouverte par la voie d'écriture, celle
  qu'ouvre `ConnectInternalAsync(writeLane)` **sous** le verrou en cause.

C'est donc « non mesuré » qui a été lu « non exercé » — le travers nommé la
veille par `d4643e9` (« un verrou NON EXERCÉ n'est pas un verrou NON MESURÉ »),
d'un cran au-dessus.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la mesure existante est juste sur son périmètre.** Les
  lignes `imap_session` de task-211 (« attente p95 1,075 s / détention 6,345 s »)
  et la prémisse chiffrée de task-213 décrivent **`ProcessEmailUid` seul**, pas
  le verrou. Le sens de lecture posé par task-211 — « une attente élevée désigne
  la contention, une détention élevée désigne ce qui se fait dessous » — reste
  valable ; ce sont les chiffres qui ne couvraient qu'un appelant.
- **Ne pas présumer que le correctif est « ajouter deux appels dans
  `ImapLockScope` ».** C'est la réparation minimale ; elle laisse la porte
  ouverte à la récidive, puisque `LockImapClientAsync` reste publique sur
  `IMailClientSessionManager` et appelable directement. Voir « Contenu attendu ».
- **Ne pas présumer un double comptage inoffensif.** Si l'instrumentation
  descend dans `LockImapClientAsync` / `UnLockImapClient`, les appels
  `RecordLockWait` / `RecordLockHold` existants de `AcquireLockWithIdAsync` et
  `ReleaseLockWithId` **doivent disparaître** — sinon `ProcessEmailUid` est
  compté deux fois et devient artificiellement le poids lourd de la table, ce
  qui est exactement l'erreur qu'on répare.
- **Ne pas présumer que le verdict de task-213 tombe.** Le « NON » sur les
  chemins de lecture (`read_list` +82 %, `folders_warm` +63 %) est mesuré côté
  client k6 et **reste acquis**. Ce qui manque est le bénéfice côté verrou.
- **Ne pas présumer qu'il faut un interrupteur de la voie d'écriture.** La
  contre-épreuve se joue sur une branche jetable où `ImapService.WriteLane`
  retombe sur `userContextInfo`, avec la configuration de banc **inchangée**
  (Dovecot `service imap` à 8000, `imap-login` en high-performance). Un
  interrupteur en production pour les besoins d'une expérience de banc serait un
  coût permanent pour un usage unique.

## Contenu attendu

1. **Aucune acquisition du sémaphore n'échappe à la mesure.** Deux voies
   possibles, à trancher **par écrit dans le code** :
   - instrumenter `ImapLockScope.AcquireAsync` / `DisposeAsync` (minimal, laisse
     `AcquireLockWithIdAsync` en place, deux points d'émission à garder
     cohérents) ;
   - **ou** descendre la mesure dans `LockImapClientAsync` / `UnLockImapClient`
     — le sémaphore lui-même —, ce qui rend l'échappement structurellement
     impossible, au prix d'y faire descendre l'étiquette `operation` et de
     **retirer** les émissions redondantes du chemin `WithId`.
2. **Garde anti-récidive**, dans l'esprit de l'analyseur de task-205 : un test
   qui échoue si un chemin d'acquisition du sémaphore n'émet pas les
   histogrammes — pas une convention écrite dans un commentaire. Il doit être
   **constaté RED** sur le binaire actuel.
3. **La voie de task-213 est lisible.** Il doit être possible, sur un rapport de
   tir, de répondre à « combien d'acquisitions sur la voie d'écriture, et
   combien attendent ? ». Étiquette de voie (lecture / écriture) ou toute autre
   forme, cardinalité bornée, **jamais** un identifiant de session en étiquette.
4. **`report.py`** : la table par opération dit désormais quelque chose de vrai.
   La distinction en trois états posée par `d4643e9` (aucune série / série à 0
   acquisition / série renseignée) est **conservée** ; la phrase qui conclut
   « le tir n'a pas archivé d'envoi » ne doit plus pouvoir être imprimée quand
   la cause est l'absence d'instrumentation. Un test de rapport le prouve.
5. **Trace dans `docs/loadtest.md`** : comment lire la table par opération, et
   la règle apprise — une table dont la source ne couvre qu'un appelant se lit
   comme un verdict alors qu'elle est un échantillon.

## Hors scope

- Toute modification de la **portée** des verrous (c'est task-211 et task-213,
  déjà tranchées) et de la voie d'écriture elle-même.
- Le sort de la voie d'écriture au vu du « NON » sur les lectures — il se décide
  **après** la contre-épreuve, pas ici.
- Les verrous `distributed_fetch` et `in_process_fetch` : déjà instrumentés
  (`ImapService.cs:1570, 1596, 1624, 1632`), non touchés.
- La campagne de confirmation groupée (task-205, 202, 206, 211, 201) : elle
  s'exécute après, sur le binaire instrumenté.

## Definition of Done

- [ ] Build passes (0 erreur) — Tests pass (0 échec)
- [ ] La voie retenue (scope ou sémaphore) est **écrite dans le code** avec
      l'argument qui l'a fait préférer à l'autre, l'autre écartée par écrit
- [ ] Test : une acquisition passant par `ImapLockScope` produit une observation
      d'attente **et** une de détention, étiquetées par la famille d'opération
- [ ] Test : `AppendToSent` est mesurable — une acquisition sur la voie
      d'écriture apparaît sous son étiquette d'opération
- [ ] **Garde** : un chemin d'acquisition non instrumenté fait échouer un test
      (constaté RED sur le binaire actuel, preuve dans le `## Develop log`)
- [ ] Aucun double comptage : `ProcessEmailUid` produit **une** observation
      d'attente par acquisition (test dédié)
- [ ] Aucune étiquette ne porte d'email, d'INS, de nom de pièce jointe ni
      d'identifiant de session (contrainte PGSSI-S + cardinalité, task-211)
- [ ] `report.py` : test prouvant que « le tir n'a pas archivé d'envoi » n'est
      pas imprimable au motif d'une instrumentation absente
- [ ] Tests **constatés RED avant le correctif** (preuve dans le `## Develop log`)
- [ ] `CrossTenantOwnershipTests` verte (aucune clé de verrou touchée)

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Un tir 500 praticiens produit une table par opération comportant **au
      moins deux opérations distinctes**, dont `AppendToSent`
- [ ] Le nombre d'acquisitions sur la voie d'écriture est cohérent avec le
      nombre d'envois du tir (même ordre de grandeur)

## Manual Test Plan

**Lancer le banc** (skill `loadtest-skill`, profil `loadtest`) :

```powershell
cd Api/Mail/src/AppHost
$env:MSS_LOADTEST = "1"
dotnet run
```

**Seeder** puis **tirer** un `mixed` court, 500 praticiens :

```bash
cd Api/Mail/tests/loadtest-k6
./reset-state.sh
USERS=500 VUS=60 DURATION=2m ./run.sh mixed
python report.py <run-id>
```

**Écran / artefact à ouvrir** : le rapport généré,
`tests/loadtest-k6/reports/{date}/report-mixed-*.md`, section
**« Verrou de session `imap_session`, par opération »**.

**Ce qu'il faut voir** :
- **au moins deux lignes**, dont `AppendToSent` — et non la seule ligne
  `ProcessEmailUid` d'aujourd'hui ;
- pour `AppendToSent`, un taux d'acquisitions du même ordre que le débit
  d'envois du tir (table « Débit demandé vs délivré », ligne `send`) ;
- aucune cellule `—` sur une opération dont le taux est non nul (ce serait la
  contradiction des deux signes que `d4643e9` a corrigée).

**Ce qui invaliderait le test** : une table où `AppendToSent` reste absent alors
que la ligne `send` du tir affiche un débit non nul. Vérifier dans ce cas, avant
toute conclusion, que le binaire déployé porte bien le correctif — le piège de
task-213 est de conclure sur l'application ce qui relève du banc.

**Données de test** : 100 % synthétiques (boîtes `loadtest-*`, corpus de pièces
jointes de test). Aucune donnée de santé, aucun INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — observabilité technique interne, aucune
  exigence de référencement créée ni modifiée.
- **Exigences DSR honorées** : aucune nouvelle. L'US ne modifie aucun
  comportement fonctionnel — elle mesure ce qui existe.
- **INS** : non manipulée.
- **Authentification PS** : inchangée — PSC / e-CPS, eIDAS substantiel.
- **Habilitations** : les clés de verrou ne changent pas
  (`{email}_{ClientSessionId}`). `CrossTenantOwnershipTests` reste la garde.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun nouvel évènement métier. Métriques techniques
  uniquement — durées et issues de verrou —, sans donnée de santé ni identifiant
  patient. ⚠️ Point de vigilance repris de task-211 et task-213 : toute
  étiquette ajoutée doit être un **ensemble fini connu à la compilation**.
  `LockOperationFamily` tronque au premier `:` précisément parce que
  `GetAttachment` concatène le **nom de la pièce jointe**, qui en messagerie de
  santé nomme couramment le patient et l'examen.
- **Consentement patient** : non applicable.
- **Hébergement HDS** : non — banc de charge, données 100 % synthétiques.
- **AIPD / impact RGPD** : inchangé.

## Branches
- `api-mail` (pushed) : fix/task-214-instrument-session-lock-scope — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-214-instrument-session-lock-scope
- `dtos-mss` (pushed, auto-inclus) : fix/task-214-instrument-session-lock-scope — aucun contrat attendu (US backend-only)

> Pré-flight `/start` : `api-mail`, `client-blazor`, `dtos-mss`, `sdk`, `host`,
> `interop-cda` sur `develop`. `client-mobile` non cloné sur ce poste — hors
> périmètre de cette task.

## Develop log

### La voie retenue (DOD 2)

**Instrumenter `ImapLockScope`** — là où les deux chronomètres existent déjà —
**et retirer l'API concurrente**. L'arbitrage complet, avec l'option écartée,
est écrit en tête de `ImapLockScope.cs`.

L'option écartée était de descendre la mesure dans `LockImapClientAsync` /
`UnLockImapClient`, c'est-à-dire dans le sémaphore lui-même, ce qui rendrait
l'échappement structurellement impossible. Deux raisons de ne pas le faire :
ces méthodes ignorent le libellé d'opération et la durée de détention (il
faudrait pousser l'un et reconstituer l'autre depuis l'état de session —
rebâtir dans le gestionnaire ce que le scope tient déjà), et elles sont
appelées **directement** par les tests de concurrence pour tenir le verrou sans
scope : la mesure compterait alors des acquisitions qui n'en sont pas.

Ce qui supprime la divergence n'est donc pas l'endroit de la mesure mais le
**retrait de la seconde API** — `AcquireLockWithIdAsync` / `ReleaseLockWithId`,
109 lignes, un seul site d'appel (`ProcessEmailUidAsync`) ramené sur le scope
commun. Sur le modèle de task-205, où le retrait de la surcharge synchrone
était le correctif.

**Détail C# qui rendait ce retrait non évident** : `ProcessEmailUidAsync` est un
`IAsyncEnumerable` et l'ancienne API avait probablement été choisie pour cela.
`yield return` **est** licite sous un `await using` — celui-ci se réduit à un
`try`/`finally`, et seul un `try` porteur d'un `catch` interdit le yield
(CS1626). Le bloc explicite disparaît donc sans changer la sémantique de
libération : dans un itérateur, le `finally` s'exécutait déjà à la disposition
de l'énumérateur, exactement comme le scope.

### Tests constatés RED avant le correctif (DOD 9)

`dotnet build tests/mss.mail.application.tests` avant implémentation :

```
SessionLockInstrumentationTests.cs(119,35): error CS0117: 'MailProcessingMetrics'
  does not contain a definition for 'LockLaneRead'
SessionLockInstrumentationTests.cs(122,35): … 'LockLaneWrite'
SessionLockInstrumentationTests.cs(195,44): … 'LockOutcomeCancelled'
```

Et côté garde de surface, `SessionLockAcquisitionSurfaceTests` exigeait
l'absence de `AcquireLockWithIdAsync` / `ReleaseLockWithId` d'une interface qui
les portait encore.

Côté Python, `test_a_missing_archive_line_is_reported_as_undecidable_not_as_a_verdict`
**change de verdict — c'est le correctif** : il exigeait auparavant la phrase
« le tir n'a pas archivé d'envoi », celle qui a été imprimée à tort le
2026-08-01.

### Correction apportée à un document d'exploitation

`loadtest-skill` affirmait encore « les boîtes du banc n'ont pas de dossier
`Sent` ; l'envoi réussit, l'archivage échoue (non fatal) », en table de lecture
des exceptions **et** en réserve de baseline. C'était vrai jusqu'à `118c3f4`
(2026-08-01, 14 h 32), qui déclare `Sent` / `Drafts` / `Trash` dans la conf
Dovecot du banc. Deux conséquences écrites à la place : toute
`FolderNotFoundException` est désormais une **régression**, et les baselines
`send` d'avant cette date ne sont **plus comparables** (elles mesuraient un
envoi dont l'archivage échouait, donc plus court).

C'est accessoirement la troisième pièce qui établit que le tir de vérification
de task-213, lancé à 16 h 49, **archivait réellement**.

### Suite complète

`dotnet test HealthPlatform.Api.Mail.sln` : **3 331 réussis, 0 échec, 16 ignorés**
(domain 102, infrastructure 393, api 624, application 1 921, integration 291).
Python : **110 tests** verts (`tests/loadtest-k6`).

### Passe `/forge-simplify`

Deux points, commit séparé (`191bbfc`) :

- `ImapLockScope` recalculait la famille d'opération et la voie **à la
  libération** alors qu'elles avaient déjà été dérivées **à l'acquisition**. Le
  coût est négligeable ; le risque ne l'est pas — deux dérivations indépendantes
  des mêmes étiquettes peuvent diverger, et une détention publiée sous une autre
  voie que son attente serait indétectable dans le rapport. Portées par deux
  champs, calculées une fois.
- `report.py` interrogeait deux fois la même série de taux par voie. Calculée
  une fois, passée aux deux consommateurs.

Aucun changement de comportement, tests re-passés verts après la passe.

## Sonar log

Analyse du 2026-08-02 (`healthplatform-api-mail`, SonarQube 9.9.8 sur
`127.0.0.1:9000`). Suite complète jouée en Release avec couverture OpenCover :
**3 331 réussis, 0 échec, 16 ignorés**.

| KPI | Projet | Code neuf |
|---|---|---|
| Quality Gate | **OK** | — |
| Bugs | 0 | 0 |
| Vulnérabilités | 0 | 0 |
| Hotspots sécurité | 3 | **0** |
| Code smells | 32 | 7 → **6** après correction |
| Couverture | 86,8 % | **87,5 %** |
| Duplication | 0,6 % | 0,21 % |
| Fiabilité / Sécurité / Maintenabilité | **A / A / A** | — |

**Un seul des 7 findings de code neuf est attribuable à task-214** :
`csharpsquid:S107` sur le constructeur d'`ImapLockScope`, passé à 8 paramètres
par la passe `/simplify` — corrigé en groupant les deux étiquettes dans
`LockTags(Family, Lane)`, ce qui **dit** ce que deux champs juxtaposés
laissaient au lecteur (elles doivent être identiques des deux côtés). Les 6
autres sont dans des fichiers que la task ne touche pas : `BackgroundSyncService`
(S107), `OcspValidationService` (S3604, S1168), `MailClientSession` (S3604 ×2),
`VCardSerializer` (S1643).

> ✅ **La réserve de task-212 / task-213 « KPIs projet inexploitables » est
> levée** : l'analyse rend des mesures cohérentes. Le point à retenir est
> l'authentification — `sonar.login` et non `sonar.token` sur SonarQube 9.9
> (diagnostic déjà posé par task-205).

### Deux pièges d'outillage rencontrés

- **`sonar-skill` pointait `:9001`**, le serveur écoute sur `:9000` (c'est ce
  que dit `.env`). Corrigé dans le skill.
- **Git Bash mange les arguments `/k:` et `/d:`** du scanner (conversion de
  chemins MSYS) : sans `MSYS_NO_PATHCONV=1` et `MSYS2_ARG_CONV_EXCL='*'`, le
  préprocesseur échoue sur « A required argument is missing: /key ». Même
  famille que le piège k6 déjà consigné.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/142 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche sans commit (US backend-only)

## Code Review Summary

**APPROVED** — 12 fichiers, 0 blocage.

- `ImapLockScope` — ✅ les trois issues d'attente couvertes (acquired / timeout /
  cancelled) ; étiquettes dérivées **une fois** à l'acquisition et réutilisées à
  la libération, pour qu'attente et détention ne puissent pas diverger.
- `MailClientSessionManager` / `IMailClientSessionManager` — ✅ retrait net,
  aucun appelant de production orphelin. Deux `using System.Diagnostics` devenus
  morts, trouvés **en relecture du diff** et non par le compilateur (un using
  inutile n'est pas un warning).
- `ImapService.ProcessEmailUidAsync` — ✅ sémantique de libération inchangée : le
  `finally` d'un itérateur s'exécutait déjà à la disposition de l'énumérateur,
  exactement comme le scope.
- `UserContextInfo.IsWriteLane` — ✅ dérivé du suffixe et non d'un champ propre,
  pour que `ForWriteLane` reste un `MemberwiseClone`.
- `report.py` — ✅ écrit qu'il ne sait pas plutôt que de deviner, et nomme le
  contrôle qui tranche.

**PGSSI-S** : aucune étiquette ne porte d'email, d'INS, de nom de pièce jointe ni
d'identifiant de session (`TheOperationTagCarriesTheFamilyOnlyNotItsArguments`).
`CrossTenantOwnershipTests` verte — aucune clé de verrou touchée.

### Observation hors périmètre

Après merge de `develop` (PR #129, secrets AppHost sortis du code source), les
tests d'intégration passent de **16 à 103 ignorés** (291 → 204 exécutés). Sans
rapport avec cette task ; à regarder si ces 87 tests doivent être reconfigurés
plutôt que sautés.

## Merged
- `api-mail` : **b7fd92b** — squash de la PR #142, mergée le 2026-08-02
- `dtos-mss` : aucune PR (branche sans commit) ; ref distant supprimé

Refs distants supprimés sur les deux repos ; **branches locales conservées**.

> **Suite immédiate** : `todo-task-215.md` — contre-épreuve de la voie
> d'écriture de task-213, désormais exécutable sur un binaire instrumenté.
> Protocole à trois tirs, dont un **témoin** avec la voie d'écriture
> neutralisée : la comparaison publiée le 2026-08-01 confond « coût de la voie
> d'écriture » et « effet du passage de Dovecot à 8 000 sessions », sa baseline
> ayant été tirée avant ce changement de conf.
