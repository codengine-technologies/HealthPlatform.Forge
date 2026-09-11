# todo-task-301.md — Dovecot et GreenMail sont démarrés deux fois par exécution : un harnais serveur unique au niveau assembly, et le coût d'entrée d'une suite tombe à zéro

**Repos**: api-mail
**Dependencies**: done-task-300
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — c'est le **débloqueur** de l'EPIC. Les trois US
suivantes (`297`, `298`, `299`) ajoutent chacune des suites à serveur réel ;
tant que chaque nouvelle collection paie son propre démarrage de conteneurs,
leur coût est prohibitif et elles seront rognées.

> **Origine** : audit de l'exploitation des tests d'intégration api-mail du
> 2026-09-11.

## Objective

Que le serveur IMAP (Dovecot) et le puits SMTP (GreenMail) soient démarrés
**une seule fois par exécution de l'assembly de test**, et qu'une nouvelle
suite à serveur réel puisse s'y brancher en trois lignes — sans re-déclarer un
conteneur, sans re-semer un corpus, sans re-payer un démarrage.

### Ce qui a été mesuré (2026-09-11)

| Grandeur | Valeur mesurée |
|---|---|
| Images déclarées par `ImapServicesFixture` | `dovecot:2.3.21`, `greenmail:2.1.3`, `pgvector:pg16`, `redis:7-alpine` |
| Images déclarées par `UseCaseFixture` | **les mêmes quatre**, re-démarrées |
| Démarrages de conteneur par exécution complète | **8** |
| Coût des collections | `ImapServices` 8,2 s (36 tests) / `UseCases` 44,3 s (55 tests) / smoke de banc 17,5 s (6 tests, **1 conteneur par test**) |
| `APPEND` IMAPS par exécution complète | **~675** (≈ 15 boîtes × 45 messages du corpus) |
| Parallélisme configuré | **aucun** — `xunit.runner.json` : `parallelizeTestCollections: false`, `maxParallelThreads: 1` |
| `AssemblyFixture` (xUnit v3, déjà en place en 4.0.0) | utilisé **nulle part** |

**Mécanique.** Un `ICollectionFixture` vit le temps de **sa** collection. Deux
collections qui veulent un serveur de messagerie déclarent donc deux fois les
mêmes conteneurs, et les démarrent l'un après l'autre puisque le runner est
strictement séquentiel. xUnit v3 — la version déjà utilisée par le projet —
offre `AssemblyFixture`, dont la durée de vie couvre l'assembly entier : c'est
exactement la portée que veut un serveur de messagerie partagé.

**Ce que cela change vraiment.** Le gain de durée est secondaire. Le vrai
effet est que le **coût d'entrée d'une nouvelle suite à serveur réel tombe à
zéro** : aujourd'hui, ouvrir une 3ᵉ collection coûte ~10 s de démarrage plus
un corpus à semer, ce qui condamne toute suite de moins d'une dizaine de
tests. Après, le coût marginal est celui **déjà mesuré** à l'intérieur d'une
collection existante : **0,11 à 0,25 s par test**.

### Contenu attendu

1. **`MailServerFixture` au niveau assembly.** Un `[assembly: AssemblyFixture]`
   porte Dovecot + GreenMail et expose ce que `MailServerTestHarness` sait
   déjà produire (hôte, ports mappés, `DomainSettings`). Les conteneurs
   Postgres et Redis **restent par collection** : ce sont eux qui portent
   l'isolation des bases praticien, et les partager mélangerait les états.
2. **`ImapServicesFixture` et `UseCaseFixture` deviennent consommateurs.**
   Ils ne déclarent plus ni Dovecot ni GreenMail et reçoivent le harnais par
   injection. Aucun test existant ne change de comportement observable.
3. **Table centrale d'allocation des utilisateurs virtuels.** Les indices sont
   aujourd'hui en dur, dispersés dans chaque suite (`2`–`5` pour
   `ImapServices`, `10`–`16`, `40`–`42`, `112` pour `UseCases`) et disjoints
   **par chance**. Avec un Dovecot partagé, une collision devient un
   croisement silencieux de boîtes entre deux suites. Une constante unique
   déclare l'attribution, et un test de garde vérifie qu'aucun indice n'est
   déclaré deux fois.
4. **Registre de boîtes semées partagé et mémoïsé** au niveau du harnais :
   une boîte semée une fois est réutilisée par toute suite qui demande le même
   indice, y compris à travers les collections. Les suites qui **mutent** leur
   boîte (drapeaux, déplacement, envoi) gardent un indice exclusif — invariant
   déjà posé par le harnais actuel, désormais vérifié par la table.
5. **Contrat d'extension publié**, en tête de `MailServerFixture` : ce qu'une
   nouvelle suite doit écrire pour obtenir un serveur réel et une boîte semée.
   C'est le livrable que consomment `297`, `298` et `299`.
6. **Parallélisme des collections activé** : `parallelizeTestCollections: true`
   et `maxParallelThreads: 4`. Le harnais est conçu pour cela (un utilisateur
   virtuel et une base praticien par suite, `mail_max_userip_connections = 100`
   côté Dovecot). À activer **dans cette US et pas avant** : la quarantaine de
   `task-300` doit déjà être en place, sinon le parallélisme sera accusé des
   flakies préexistants.
7. **Mesure avant / après** avec `Tools/timing/measure.sh --kind test`,
   consignée dans le task file. Sans elle, l'optimisation reste un pari —
   c'est la raison d'être de l'instrumentation de la forge.

### Hors périmètre (explicite)

- **Le corpus pré-semé** (volume Maildir monté au lieu de ~675 `APPEND`). Il ne
  devient rentable qu'une fois les suites de `298` et `299` écrites ; il fera
  sa propre task si la mesure le justifie alors.
- Les `*BenchSmokeTests`, qui démarrent volontairement un conteneur jetable
  **par test** : c'est leur objet (ils éprouvent la configuration de banc
  montée depuis `src/AppHost/`), ils ne rejoignent pas le harnais partagé.
- Toute nouvelle capacité serveur (quota, dossiers spéciaux) — objet de
  `todo-task-302`.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures) hors quarantaine déclarée
- [ ] Un `AssemblyFixture` porte Dovecot et GreenMail ; `grep` sur les images
      `dovecot/` et `greenmail/` ne remonte plus qu'**une** déclaration hors
      `*BenchSmokeTests`
- [ ] Démarrages de conteneur par exécution complète : **de 8 à 6**, constaté
      par observation de `docker ps` ou par les journaux Testcontainers
- [ ] Les 97 tests `Server=real` restent verts, **et le nombre reste 97**
      (aucune suite perdue par un `[Collection]` mal recâblé)
- [ ] Table centrale d'attribution des indices d'utilisateur virtuel + test de
      garde qui échoue si un indice est déclaré deux fois
- [ ] Contrat d'extension écrit en tête de `MailServerFixture` : une nouvelle
      suite obtient serveur + boîte semée sans déclarer de conteneur
- [ ] `xunit.runner.json` : `parallelizeTestCollections: true`,
      `maxParallelThreads: 4`
- [ ] **3 exécutions consécutives vertes** de `Server=real` après activation du
      parallélisme, consignées dans le task file (c'est la seule preuve que
      l'isolation tient)
- [ ] Mesure avant / après consignée : durée totale et durée par collection,
      via `Tools/timing/measure.sh --kind test`
- [ ] Aucune donnée de santé dans le corpus ni les journaux

## Manual Test Plan

- **Avant** : `cd Api/Mail && dotnet test tests/mss.mail.integration.tests --no-build --filter "Server=real"`,
  noter la durée (références mesurées : 74 s à froid, 51 s images tirées) et compter les conteneurs
  `dovecot` / `greenmail` vus par `docker ps` pendant l'exécution
  (référence : 2 de chaque, successivement).
- **Après** : même commande. **Ce que l'humain doit voir** : `réussite : 97,
  échec : 0`, durée attendue ~25 à 40 s, et **un seul** conteneur `dovecot` et
  **un seul** `greenmail` vivants pendant toute l'exécution.
- **Contre-épreuve d'isolation** : relancer la commande **trois fois de suite**
  sans nettoyer. Les trois passes doivent être vertes. Un rouge intermittent
  ici signe une collision d'utilisateur virtuel ou de base praticien — ne pas
  le mettre en quarantaine, c'est un défaut de cette US.
- **Contre-épreuve du test de garde** : dupliquer volontairement un indice
  d'utilisateur virtuel dans la table centrale, constater que le test de garde
  échoue avec un message nommant l'indice, puis revenir en arrière.
- **Données de test** : 100 % synthétiques.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de vérification interne
- **Exigences DSR honorées** : non applicable — la US porte sur la durée de vie
  des conteneurs de test, pas sur une exigence de référencement
- **INS** : non applicable — corpus synthétique, aucun INS/NIR/NIA
- **Authentification PS** : inchangée. L'authentification IMAP du harnais reste
  la `passdb static` du serveur de test, jamais un secret réel
- **Habilitations** : inchangées — RPPS fictifs (`99700000042` et le RPPS
  distinct du harnais des use cases) conservés
- **Interop CI-SIS** : non applicable directement ; les archives IHE-XDM du
  corpus restent les échantillons CDA synthétiques déjà versionnés
- **Tracé PGSSI-S** : aucun évènement métier nouveau
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — conteneurs locaux, données synthétiques
- **AIPD / impact RGPD** : inchangée

## Branches

- `api-mail` (pushed) : `feat/task-301-harnais-serveur-assembly` — base `origin/develop` @ 5855604, puis **merge de `feat/task-300`** (voir Develop log)
- `dtos-mss` (pushed, auto-inclus) : même nom de branche, aucun changement de contrat

## Develop log

### Ce qui a ete fait

1. **`MailServerFixture`, fixture d'assembly** (`[assembly: AssemblyFixture(...)]`,
   xUnit v3 deja en place en 4.0.0) : Dovecot et GreenMail demarres **une fois
   pour tout l'assembly**, avec le registre de boites semees. Postgres et Redis
   **restent par collection** — ce sont eux qui portent l'isolation des bases
   praticien ; les partager melangerait les etats au lieu de les separer.
2. **`ImapServicesFixture` et `UseCaseFixture` deviennent consommateurs** : ils
   recoivent le harnais par constructeur et deleguent `Dovecot`, `GreenMail` et
   `GetSeededMailboxAsync`. Aucun site d'appel de test n'a change.
3. **Table `VirtualUsers`** : les 15 indices d'utilisateur virtuel, jusque-la en
   dur et disperses, reunis avec le nom de leur reservataire.
4. **Test de garde `VirtualUserAllocationTests`** (3 tests) : echoue si un
   indice est reserve deux fois, si le compte d'attributions derive, ou si un
   indice est nul/negatif.
5. **Contrat d'extension** ecrit en tete de `MailServerFixture` : trois gestes
   pour brancher une nouvelle suite a serveur reel, sans declarer de conteneur.

### Mesure avant / apres

| Grandeur | Avant | Apres |
|---|---|---|
| Declarations `DovecotFixture.StartAsync()` dans le code | **2** | **1** |
| Declarations `GreenMailFixture.StartAsync()` | **2** | **1** |
| Demarrages de conteneur longue duree par execution | **8** | **6** |
| Population `Server=real` | 97 verts / 51 s | **97 verts / 49-50 s** |
| Projet d'integration complet | 487 tests / ~90 s | **490 tests / 82-91 s** |

**Le gain n'est pas la duree** — les conteneurs demarraient deja de front, donc
la mesure ne bouge quasiment pas, et le task file l'annoncait. Le gain est que
le **cout d'entree d'une nouvelle suite a serveur reel tombe a zero** : c'est ce
qui rend abordables task-302, task-303 et task-304.

### Le parallelisme a ete active, mesure, puis RETIRE — et c'est un resultat

`parallelizeTestCollections: true` + `maxParallelThreads: 4` :

- **duree 90 s -> 27 s (x3,3)** ;
- **3 echecs**, tous d'extraction CDA, tous « collection vide » :
  `CdaParsingIntegrationTests.ParseCardiologyPrescriptionReturnsDocumentWithMetadata`,
  `CdaParsingIntegrationTests.ParseImagingReportReturnsDocumentWithMetadata`,
  `CdaDocumentExtractionNonRegressionTests(folder: "CR-BIO_2021.01_Microbiologie_V2")`.

**La cause n'est pas dans les tests.** `IheXdmScratch`
(`src/Application/Helpers/IheXdmScratch.cs:32`) expose **un repertoire de
travail unique par machine** — `Path.Combine(Path.GetTempPath(), "mss-ihe-xdm")` —
et son `Sweep()` de demarrage (ligne 112) supprime **tous** les fichiers qu'il y
trouve, sans filtre d'age ni marqueur de proprietaire. Deux collections en
parallele : le balayage de l'une efface les archives **en vol** de l'autre.

Decision : **revenir au sequentiel** plutot que mettre ces 3 tests en
quarantaine. Les quarantiner aurait force le gain de duree en masquant un defaut
qui **porte aussi en production** — api-mail tourne en 5 replicas, et un
redemarrage de l'un balaie le repertoire partage des autres. Detail et
implication production : `questions/task-301.md`.

**Ce meme mecanisme explique tres probablement l'echec CI #1 de task-300**
(`CdaDocumentExtractionNonRegressionTests(folder: "CR Imagerie")`, « collection
vide » sur Linux, vert sur Windows) : meme symptome, meme famille, meme
repertoire partage.

### Dependance de branche

`task-301` a d'abord ete branchee sur `origin/develop`, qui **ne contient pas
task-300** (PR #230 ouverte, non mergee — HAG). Les traits `Server=real`
n'existaient donc pas et le filtre ne selectionnait **aucun** test. `feat/task-300`
a ete **merge** dans `feat/task-301` (regle 4 : merge, jamais rebase). La PR de
task-301 porte donc les commits de task-300 tant que celle-ci n'est pas mergee.

### Validation

**3 executions consecutives du projet d'integration, sequentiel** : 490 tests,
**0 echec** a chaque passe (1 m 31 / 1 m 25 / 1 m 22), 16 ignores
(`Assert.SkipUnless` Ollama / Windows-only).

### Passe qualite `/simplify` (SQ)

Aucun cleanup applique. Le diff est une extraction de responsabilite deja
factorisee (`MailServerTestHarness` existait) ; les deux fixtures consommatrices
ont perdu une trentaine de lignes de duplication, ce qui **etait** l'objet de la
task et non un cleanup opportuniste. Pas de re-validation supplementaire.

## Sonar log

**Skip propre** — `git diff --name-only origin/develop...HEAD` sur api-mail ne
rend aucun `src/**/*.cs` : le diff est entierement dans
`tests/mss.mail.integration.tests/`. Aucune issue Sonar attribuable.

| KPI | Baseline | Final | Quality Gate |
|---|---|---|---|
| — | non mesure (skip) | non mesure (skip) | non evalue |

> Le defaut decouvert par cette task porte pourtant sur du code de production
> (`src/Application/Helpers/IheXdmScratch.cs`) — mais il est **constate**, pas
> **modifie** : voir `questions/task-301.md`.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/231 — label `awaiting-human-merge`
  - ⚠️ contient les commits de task-300 (PR #230) : voir « Dependance de branche » du Develop log
- `dtos-mss` : **aucune PR** — 0 commit

## Code Review Summary

**APPROVED** — 5 fichiers revus, 0 blocage.

| Fichier | Verdict |
|---|---|
| `Fixtures/MailServerFixture.cs` | OK — portee correcte (serveurs partages, bases par collection), contrat d'extension explicite, message d'erreur nommant la cause si le fixture d'assembly est retire |
| `Fixtures/VirtualUserAllocationTests.cs` | OK — garde le seul invariant que le partage rend critique ; hors `Server=real` (lecture de table) |
| `Fixtures/ImapServicesFixture.cs` | OK — delegation, aucun site d'appel modifie ; `Dispose` ne libere plus les serveurs |
| `UseCases/UseCaseFixture.cs` | OK — idem |
| `xunit.runner.json` | OK — sequentiel conserve, avec la mesure et la cause ecrites dans le fichier |

**Validation** : solution complete **4 373 tests, 0 echec** ; projet d'integration
**3 executions consecutives vertes**. `develop` n'avait pas bouge.

## Timings

*(généré par `tools/timing/report.sh --task task-301 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /develop | ok | 19 min 19 s | — | — | — | — |
| /sonar | skipped | 2.8 s | — | — | — | hors périmètre (api-mail tests seuls) |
| /lint-angular | skipped | 2.4 s | — | — | — | hors périmètre (api-mail tests seuls) |
| /lint-mobile | skipped | 2.2 s | — | — | — | hors périmètre (api-mail tests seuls) |
| /verify-visual | skipped | 2.0 s | — | — | — | hors périmètre (api-mail tests seuls) |
| /review | ok | 3 min 21 s | — | 1 (0.9 s) | — | api-mail 0B/1T |
| /tech-writer | ok | 42 s | — | — | — | — |
| **Total cycle** | | **23 min 33 s** | **0 (0.0 s)** | **1 (0.9 s)** | **0 (0.0 s)** | |
