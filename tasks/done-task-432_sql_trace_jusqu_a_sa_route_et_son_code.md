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
- [x] Parcours e2e verts (`/e2e`), aucun scénario ajouté : aucun parcours n'est modifié

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

## E2E log

Voies jouées le 2026-11-07 : `api-mail` à `29a5e1a9` (branche de la task), `client-mobile` à `develop`, `client-angular`
sur la branche du poste (code-only).

| Voie | Déclenchée par | Jouée / réutilisée | Résultat |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | jouée | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | jouée | ✅ 71 verts, 0 flaky, 0 rouge, parité verte |

Porte `gate` : code 0. Démontage vérifié : aucun conteneur e2e résiduel, aucun port du jeu e2e ouvert.

Aucun écran modifié : aucun scénario ajouté ni versionné (observabilité SQL et harnais de banc seulement).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Branches
- `api-mail` (pushed) : feat/task-432-sql-trace-jusqu-a-sa-route-et-son-code — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-432-sql-trace-jusqu-a-sa-route-et-son-code

## Timings

*(généré par `tools/timing/report.sh --task task-432 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 4 h 02 min | 4 (54 s) | 2 (10 min 51 s) | — | api-mail 4B/2T |
| /sonar | ok | 25 min 13 s | 3 (1 min 40 s) | 12 (16 min 23 s) | 4 (1 min 29 s) | 1 itération(s), api-mail 3B/12T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 19 min 22 s | — | — | — | e2e ×3 (18 min 49 s) |
| /review | ok | 7 min 42 s | 1 (16 s) | 1 (5 min 31 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 38 s | — | — | — | — |
| **Total cycle** | | **4 h 55 min** | **8 (2 min 51 s)** | **15 (32 min 46 s)** | **4 (1 min 29 s)** | |

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/351 — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 9 fichiers de production, 9 fichiers de tests, 5 fichiers de harnais. 0 point bloquant,
3 suggestions.

- Build : 0 erreur, 0 avertissement.
- Tests : domain 210, infrastructure 728, api 1 370, application 4 031, intégration 1 138 (+16 ignorés), 0 échec.
- `selftest.sh` du harnais : 431 tests verts.
- **Règle 1b** — comportement → test → preuve rouge :
  - commentaire de route et de site sur `GET …/medical-documents` →
    `ThePatientFolderPage_EveryCommandNamesItsRouteAndRepositoryMethod_WithoutAnyIdentifier` → M1, M2, M3 ;
  - commentaire gardé dans `pg_stat_statements` → `ThePractitionerDatabase_KeepsTheComment_InPgStatStatements`
    → M1, M2, M3 ;
  - écriture du bus sous `bus:AddNewMail` → `AMailConsumedFromTheBus_WritesUnderItsMessageName_AndTheRepositoryMethod`
    → M1, M4 ;
  - interrupteur à `false` → `SqlCallSiteCommentsSwitchIntegrationTests` → M5 ;
  - ordre du pipeline de production → `TheProductionPipeline_WiresTheMiddleware_TheSwitch_AndTheBusFilter` → M7.
- **E2E** : vert. Mobile 58, angular 71, parité verte.
- **Suggestions** :
  - l'INSERT d'`audit_traces` (3,2 % du temps SQL) reste sans commentaire, hors EF ;
  - le cache des sites est indexé par texte : des listes `IN` de longueurs variables consomment la borne ;
  - `UseCaseHttpHost` n'a pas l'ordre de production, qui est gardé par le test de source.
