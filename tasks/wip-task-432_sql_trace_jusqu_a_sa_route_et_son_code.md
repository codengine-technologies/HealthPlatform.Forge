# todo-task-432.md — Chaque requête SQL porte sa route et la méthode qui l'émet

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Étage 1 de l'amélioration « le banc comme outil d'exploration » (2026-11-06). Une ligne de
`pg_stat_statements` ne dit pas quel code l'a émise. Remonter d'une requête coûteuse à sa cause demande aujourd'hui de
chercher les noms de tables et de colonnes dans le code, ce qui est lent et parfois ambigu. Utile aussi en
exploitation : la même information sert à lire `pg_stat_statements` en production.

> **Origine.** Exploration du 2026-11-06 (task-429, task-430) : chaque candidat a demandé une recherche dans le code
> pour retrouver son site d'émission.

## Ce qui est établi

- **Un intercepteur de commandes existe** : `DbCommandPhaseInterceptor` (`src/Infrastructure/Telemetry/DbOperationPhaseInterceptors.cs`,
  task-243). Il voit chaque commande avant son exécution, mais ne mesure que les opérations encadrées par un
  `DbOperationScope`.
- **Postgres ignore les commentaires pour regrouper les requêtes** (`queryid`), mais **garde le texte** de la première
  exécution vue, par base. Un commentaire en tête du SQL apparaît donc dans `pg_stat_statements` sans démultiplier les
  formes.
- **Limite connue** : si deux méthodes émettent exactement le même SQL dans une même base, seul le commentaire de la
  première est gardé. C'est rare avec des requêtes EF Core écrites site par site.
- **EF Core 10** propose `TagWith` et `TagWithCallSite`, mais requête par requête, sur des centaines de sites.

## Objective

Chaque commande SQL émise par api-mail commence par un commentaire qui nomme la **route** et la **méthode** qui l'a
émise : `/* route=GET /api/v1/Patients/{patientId}/medical-documents site=PatientRepository.LoadMailsWithAttachmentsAsync */`.

Règles :
- **La route est le gabarit, jamais le chemin réel** : `{patientId}`, pas l'identifiant. Elle vient de l'activité HTTP
  en cours (`http.route`). Hors requête HTTP (consommateur du bus, tâche de fond), le commentaire nomme l'opération
  (consommateur, tâche) : `route=bus:AddNewMail`.
- **La méthode** est la première méthode des dépôts (`*Repository`, `PostgresTenantRegistryClient`) dans la pile
  d'appel. Elle est **calculée une seule fois par texte SQL distinct**, puis mise en cache (par processus, taille
  bornée). Le coût par commande est une recherche dans un dictionnaire.
- **Aucune donnée dans le commentaire** : ni identifiant, ni paramètre, ni valeur. Uniquement des noms de route et de
  méthode du code. Le texte SQL peut finir dans les journaux de Postgres : rien de ce qui y est ajouté ne doit être une
  donnée de santé ou une donnée personnelle.
- **Désactivable** par configuration (`Database:SqlCallSiteComments`), **activé par défaut**.
- **Comportement inchangé** : mêmes résultats, même nombre de requêtes. Le surcoût est mesuré au banc.
- **`report.py`** extrait `route` et `site` du texte de chaque forme et les affiche dans le top des requêtes, et dans les
  signaux de task-431 si elle est mergée.

### Hors périmètre

- Instrumenter le temps SQL par route dans Prometheus : `pg_stat_statements` et le commentaire suffisent pour
  l'exploration.
- Les requêtes émises par Npgsql lui-même (chargement des types) : sans site applicatif, elles restent sans commentaire.

## Definition of Done

- [x] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [x] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [x] **Test d'intégration de bout en bout (règle 1b)** : un appel à
      `GET /api/v1/Patients/{patientId}/medical-documents?page=1&pageSize=20` sur la vraie pile et la vraie base du
      fixture :
      - la réponse est inchangée ;
      - le SQL relevé par intercepteur commence par
        `/* route=GET /api/v1/Patients/{patientId}/medical-documents site=PatientRepository.` ;
      - le commentaire ne contient pas l'identifiant du patient ;
      - **vu rouge** sans l'intercepteur.
- [x] **Test d'intégration, la base garde le commentaire** : après l'appel, `pg_stat_statements` de la base du fixture
      (si l'extension est chargée par le fixture ; sinon, `pg_stat_activity` pendant l'appel, ou les journaux du
      conteneur) contient le commentaire. Le moyen retenu est justifié dans le `Develop log`
- [x] **Test d'intégration, acte système** : une écriture faite par le consommateur du bus porte `route=bus:…` et son
      site
- [x] **Désactivation** : `Database:SqlCallSiteComments=false` ne produit aucun commentaire (test d'intégration)
- [x] Tests unitaires : la résolution du site (premier dépôt de la pile), le cache par texte (une seule résolution pour
      deux exécutions), la borne du cache
- [x] **Surcoût mesuré au banc**, tir court contre contrôle `develop` dans la même session :
      - aucune étape ralentie de plus de 5 % au p50 ;
      - CPU d'api-mail relevé ;
      - rapport régénéré : le top des requêtes affiche `route` et `site`.
- [x] `report.py` affiche `route` et `site` par forme : test sur une fixture de `pg_stat_statements` qui porte le
      commentaire
- [x] Aucune donnée de santé en clair dans les logs, ni dans le texte SQL : contrôle mécanique dans le test
      d'intégration, aucune valeur d'identifiant dans le commentaire
- [ ] Parcours e2e verts (`/e2e`), aucun scénario ajouté : aucun parcours n'est modifié

## Manual Test Plan

- [ ] `cd Api/Mail && dotnet run --project src/AppHost`, ouvrir la messagerie et le dossier d'un patient.
- [ ] Sur la base de la boîte :
      `SELECT left(query, 160) FROM pg_stat_statements WHERE query LIKE '/* route=%' LIMIT 20;` : chaque requête porte
      sa route et sa méthode, sans aucun identifiant.
- [ ] Relancer avec `Database__SqlCallSiteComments=false` : les nouvelles formes n'ont plus de commentaire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — observabilité interne
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — garde-fou explicite : aucun identifiant, ni INS, ni NIR, ni patient, dans le commentaire
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. Le commentaire n'est pas une trace d'acte et n'en remplace aucune. Il ne porte aucune
  identité (ni RPPS, ni nom), pour que les journaux de Postgres n'en contiennent pas
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — pas de donnée nouvelle. Le texte SQL reste dans Postgres, sur l'environnement HDS
- **AIPD / impact RGPD** : inchangée — aucune donnée personnelle ajoutée au texte SQL

## Develop log

**Commits api-mail** : `44b2f220` (feature + passe qualité), `f8a9684e` (middleware avant l'authentification, trouvé
au banc).

### Conception

- **Le commentaire** : `/* route=<gabarit> site=<Dépôt.Méthode> */ ` en tête de chaque commande EF Core. Postgres
  l'ignore pour le `queryid` mais garde le texte vu en premier, par base.
- **`route`** : un `AsyncLocal` (`SqlCallSite`, Application) ouvert par trois portes.
  - Le middleware `SqlCallSiteMiddleware` écrit le gabarit de route, sans les contraintes, et ne recopie que la
    version d'API numérique. La méthode HTTP est prise dans une liste fermée, sinon `OTHER`.
  - Le filtre MassTransit `SqlCallSiteFilter<T>` écrit `bus:AddNewMail`.
  - Par défaut, la valeur est `background`.
- **`site`** : `SqlCallSiteResolver` lit la pile et prend la première trame d'un `*Repository` (hors
  `BaseRepository`) ou de `PostgresTenantRegistryClient`. Les noms générés par le compilateur sont démêlés.
  - La résolution est mise en cache par texte SQL (borne de 4096).
  - Un texte non résolu 32 fois devient `?`, ce qui borne le coût de la pile.
- **Point de pose : `CommandInitialized`, pas `ReaderExecuting`.** EF initialise la commande *avant* d'ouvrir la
  connexion. Quand l'ouverture rend la main (`await` qui cède), la trame du dépôt a disparu de la pile au moment
  de l'exécution. Le test du bus en INSERT/UPDATE sortait `site=?` tant que le commentaire était posé à
  l'exécution.
- **Interrupteur** : `Database:SqlCallSiteComments` (vrai par défaut), lu au démarrage par
  `SqlCallSiteComments.Configure`.
- **Branchement** : `BaseRepository.CreateDbContextAsync`, le client du registre, le filtre de consommation du bus,
  `app.UseSqlCallSite()` après `UseExceptionHandler` et **avant `UseAuthentication`** (voir le banc).
- **Harnais** :
  - `pg-statements.sh` agrège les formes sur le texte **sans** commentaire (le md5 est inchangé, vérifié sur un
    `postgres:16` jetable à deux bases) et ajoute la colonne `call_sites`.
  - `report_postgres.py` retire le commentaire avant les détecteurs et ajoute une colonne « Émise par » au top 20
    et aux signaux de défaut.

### Preuve que la base garde le commentaire : `pg_stat_statements`

`UseCaseFixture` charge désormais `shared_preload_libraries=pg_stat_statements`. Le test
`ThePractitionerDatabase_KeepsTheComment_InPgStatStatements` remet les compteurs à zéro, appelle la route sur la
vraie pile, puis lit `pg_stat_statements` de la base du praticien via `SqlProbe` (`Pooling=false`). C'est le moyen
le plus direct : le même texte que lit `pg-statements.sh` au banc. `pg_stat_activity` n'aurait vu que l'instant de
l'appel, et les journaux du conteneur dépendent de `log_statement`.

### Preuves rouges (règle 1b), par mutation

| Mutation | Tests rouges |
|---|---|
| M1 — intercepteur non branché dans `BaseRepository` | 4 : interrupteur actif, HTTP, `pg_stat_statements`, bus |
| M2 — le middleware ouvre `background` | HTTP, `pg_stat_statements` |
| M3 — chemin réel (`…/{patientId}` valué) dans la route | HTTP, `pg_stat_statements` (identifiant détecté) |
| M4 — filtre du bus sans opération | `AMailConsumedFromTheBus_WritesUnderItsMessageName_AndTheRepositoryMethod` |
| M5 — interrupteur ignoré | test « désactivé » |
| M6 — pose à l'exécution seulement | resté vert : non déterministe (dépend d'un `await` qui cède), le défaut a été vu au banc d'intégration avant le correctif |
| M7 — middleware placé après `UseAuthentication` | `TheProductionPipeline_WiresTheMiddleware_TheSwitch_AndTheBusFilter` |
| R1 — commentaire laissé dans le texte (rapport) | 3 tests de `report_postgres` |
| R2 — colonne « Émise par » non rendue | 1 test de `report_postgres` |

### Suite complète

| Projet | Résultat |
|---|---|
| domain | 210 verts |
| infrastructure | 728 verts |
| api | 1370 verts |
| application | 4031 verts |
| integration | 1138 verts, 16 ignorés |
| loadtest-k6 (Python) | `CallSiteTests` (5) verts |

Le premier passage complet a sorti **28 échecs `53300 too many clients`** dans la collection UseCases. Les
nouvelles sondes ouvrent un pool par base, ce qui fait une 4ᵉ récidive. Corrigé par `max_connections=400` sur
`UseCaseFixture` et `Pooling=false` sur la sonde. La mémoire de session est corrigée : elle prêtait cette valeur à
`PostgreSqlFixture`.

### Passe qualité (`/simplify`, §Q)

- **Appliqué** :
  - dédoublonnage de la CTE d'export ;
  - retrait des surcharges `*Executing` ;
  - chemin rapide sans allocation pour le nettoyage du commentaire ;
  - compteur `Interlocked` au lieu de `.Count` ;
  - allocations du middleware réduites ;
  - `Enabled` en propriété ;
  - réutilisation de `SqlProbe` ;
  - note sur `HttpErrorReporting.RouteOf`.
- **Écarté** :
  - correspondance du site par espace de noms (s'écarte du contrat de la task) ;
  - cache de premier niveau par référence ;
  - `struct` jetable.

### Banc : surcoût, tir court 1400 → 1996 avec IA simulée, A/B/A, même session (2026-11-07)

| Tir | Code | Requêtes | Rapport |
|---|---|---|---|
| A | `develop` 18f9c9fb | 764 008 | `report-journey-courte-1400-1996-20261107-controle432-170442.md` |
| B | branche 44b2f220 | 758 288 | `…-task432-175431.md` |
| B' | branche finale f8a9684e | 763 043 | `…-task432b-184604.md` |
| A2 | `develop` 18f9c9fb | 695 244 | `…-controle432b-193520.md` : **VOID** |

- **A2 est inutilisable.** Côté SMTP du banc, l'obtention de session a pris 8,6 s et la transmission 8,1 s par
  envoi. L'envoi est passé à un p50 de 20,4 s au palier 1996, ce qui a bridé les VU (−9 % de requêtes) et allégé
  toutes les autres étapes. C'est un incident d'environnement sur le code `develop`, sans lien avec la task. Il
  n'y a donc qu'un seul contrôle valable.
- **Bruit mesuré** entre B et B', deux tirs d'un code quasi identique : jusqu'à ±2,5 % au p50. Une milliseconde
  vaut 2 à 3 % sur les étapes de 35 à 50 ms.

**Verdict, code final (B') contre contrôle (A) : aucune étape ralentie de plus de 5 % au p50. ✅**
Pire écart : **+4,1 %**, sur l'inbox au palier 1996 (49 → 51 ms). Les autres étapes vont de −0,6 % à +3,1 %.
Le +5,3 % de B (inbox au palier 1400, 38 → 40 ms) ne se reproduit pas sur B' (38 → 39). C'est de la granularité.

| Étape | p50 1400 A → B' | p50 1996 A → B' |
|---|---|---|
| Arrivée dashboard | 58 → 59 | 63 → 64 |
| Inbox | 38 → 39 | 49 → 51 |
| Message enrichi | 32 → 33 | 45 → 46 |
| Message froid | 444 → 444 | 453 → 454 |
| Recherche | 324 → 322 | 347 → 348 |
| Envoi | 493 → 496 | 484 → 498 |
| PJ | 35 → 36 | 50 → 51 |
| Marquer lu | 33 → 33 | 51 → 52 |
| Recherche patient | 55 → 55 | 56 → 56 |
| Page dossier patient | 56 → 56 | 59 → 59 |
| Fiche patient complète | 257 → 262 | 336 → 340 |

- **CPU** :
  - hôte, en moyenne : 61,7 % (A), 60,5 % (B), 60,5 % (B') ;
  - api-mail, pointe par processus : 2,2 à 3,1 cœurs (A), 2,6 à 3,2 (B), 2,0 à 3,9 (B').

  Ce sont des pointes transitoires, pas une consommation soutenue, et leur somme ne se compare pas d'un tir à
  l'autre (4 ou 5 processus selon les redémarrages).
- **Rapport régénéré** : la colonne « Émise par » apparaît au top 20 et aux signaux.

**Couverture du commentaire au banc**, en part du temps SQL du tir :

| | B (middleware après l'authentification) | B' (final) |
|---|---|---|
| Route + site | 64 formes, 86,8 % | **71 formes, 93,2 %** |
| `background` seul | 9 formes, 7,3 %, dont `GetMailboxAsync` du registre à 6,5 % | 4 formes, 0,6 % : `PendingActionRepository`, vrai acte de fond |
| Site `?` seul | 23 formes, 0,1 % | 23 formes, 0,1 % |
| Sans commentaire | 36 formes, 5,8 % | 35 formes, 6,1 % |

Le banc B a trouvé le défaut de placement : l'authentification et l'enrichisseur de contexte lisent le registre
*avant* le middleware. D'où `f8a9684e` et la mutation M7.

### Limites connues, assumées

- **SQL brut hors EF, sans commentaire (6,1 %)** :
  - l'INSERT d'`audit_traces` (3,2 %, 138 250 appels), avec son `BEGIN` et son `SET LOCAL ROLE mss_audit_writer` ;
  - le chargement des types de Npgsql (2,0 %) ;
  - le `FOR KEY SHARE` des clés étrangères, émis par Postgres lui-même.

  L'audit passe par Npgsql sans `DbContext`. Le commenter demanderait une pose à la main dans l'écrivain d'audit :
  c'est une piste, hors du périmètre de la task.
- **Site `?`** : 23 formes, 0,1 % du temps. Ce sont des commandes dont aucune trame de dépôt ne reste dans la pile.
  La borne de 32 échecs plafonne leur coût.

## Sonar log

Deux analyses complètes de la branche, avec couverture OpenCover sur les 5 projets de tests, toutes vertes. Une
seule itération de correction.

- **Analyse 1** (`f8a9684e` + index du banc) : Quality Gate OK, mais **13 issues de code neuf**, toutes des règles
  déjà consignées dans `conventions/csharp.md`. Ce sont donc des **récidives sur du code frais**.
  - S3604 ×2 : `SqlCallSiteResolver`, initialiseurs de champ sous constructeur primaire chaîné.
  - CA1822 ×9 : doublures de test nommées par réflexion.
  - CA1859 ×2 : helpers de test qui rendent un type plus large que ce qu'ils calculent.
  - SYSLIB1045 ×1 : `Regex.IsMatch` dans une assertion du test du bus.
- **Correctifs** (`29a5e1a9`) :
  - constructeurs classiques pour le résolveur ;
  - doublures en classes `static`, avec `Method(typeof(X), …)` ;
  - types concrets pour les helpers ;
  - `[GeneratedRegex]` pour le test du bus.
- **Re-validation** : build propre, puis suite complète verte dans l'analyse 2 (domain 210, application 4031,
  infrastructure 728, api 1370, integration 1138 + 16 ignorés).
- **Analyse 2** (`29a5e1a9`) : **0 issue de code neuf**.

### KPIs qualité (baseline → final)

| Métrique | Baseline (`develop`, 13:53 UTC) | Final (branche, 19:12 UTC) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New violations | 0 | 0 (13 à l'analyse 1) | = |
| New coverage | 96,1 % | 95,9 % | −0,2 |
| Bugs / Vulnérabilités / Smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,9 % | 97,8 % | −0,1 |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

**Couverture des fichiers neufs** :

| Fichier | Couverture | Ligne(s) non couverte(s) |
|---|---|---|
| `SqlCallSite` | 100 % | — |
| `SqlCallSiteComments` | 96,1 % | — |
| `SqlCallSiteResolver` | 96,1 % | 1 |
| `SqlCallSiteMiddleware` | 89,2 % | 2 |
| `SqlCallSiteFilter` | 83,3 % | 1 (`Probe`) |

**Prévention** : les compteurs de CA1822, CA1859, S3604 et SYSLIB1045 sont incrémentés dans
`conventions/csharp.md`, avec la variante de task-432. Ces récidives signalent un défaut de lecture des consignes
pendant `/develop`, pas un défaut du code (règle d'or, point 3).

## Branches
- `api-mail` (pushed) : feat/task-432-sql-trace-jusqu-a-sa-route-et-son-code — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-432-sql-trace-jusqu-a-sa-route-et-son-code

## Timings

*(généré par `tools/timing/report.sh --task task-432 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 4 h 02 min | 4 (54 s) | 2 (10 min 51 s) | — | api-mail 4B/2T |
| /sonar | ok | 25 min 13 s | 3 (1 min 40 s) | 12 (16 min 23 s) | 4 (1 min 29 s) | 1 itération(s), api-mail 3B/12T |
| **Total cycle** | | **4 h 27 min** | **7 (2 min 35 s)** | **14 (27 min 14 s)** | **4 (1 min 29 s)** | |
