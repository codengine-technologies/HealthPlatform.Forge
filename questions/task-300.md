# questions/task-300.md — Le gate a marché du premier coup et a révélé deux défauts Linux-only : arbitrage demandé

**Task** : task-300 (EPIC E016) — `done-*`, PR api-mail [#230](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/230) ouverte, label `awaiting-human-merge`
**Statut** : livrable **fonctionnel et prouvé**. La CI de la PR est **rouge**, sur deux défauts **pré-existants** que le gate vient de rendre visibles.
**Date** : 2026-09-11

---

## Ce qui s'est passé

Le gate CI rétabli par task-300 s'est exécuté pour la première fois sur une PR
vers `develop` (run `34594564320`) :

| Étape CI | Résultat |
|---|---|
| `Build` | ✅ succès |
| `Test (hors serveur réel)` | ❌ **2 échecs** |
| `Test (serveur réel — Dovecot/GreenMail)` | ⏭️ non atteinte (la précédente a échoué) |

**Le livrable fonctionne** : l'étape `Test` s'exécute, alors qu'elle était
sautée sur ce chemin depuis toujours. Et elle a trouvé quelque chose dès le
premier contact.

**Ces deux défauts ne sont pas des régressions de task-300** : la task ne
touche aucun code de production, et aucun des deux tests n'est parmi les
16 classes modifiées. Ils sont **verts sur Windows** (4 exécutions complètes
consécutives, 4 370 tests, 0 échec) et **rouges sur `ubuntu-latest`**. Ils
étaient invisibles parce que la CI ne les avait jamais exécutés.

## Défaut 1 — extraction CDA vide pour un seul dossier du corpus

```
Failed CdaDocumentExtractionNonRegressionTests
       .A_mono_document_archive_yields_exactly_one_clinical_document(folder: "CR Imagerie")
  Assert.Single() Failure: The collection was empty
  tests/mss.mail.integration.tests/Services/CdaDocumentExtractionNonRegressionTests.cs:73
```

- Les deux autres jeux de données de la même `[Theory]`
  (`CR-BIO_2021.01_Microbiologie_V2`, `DLU-FLUDT_2021.01`) **passent**.
- **Ce n'est pas un problème de nom de dossier** : `CR Imagerie` existe avec
  cette casse exacte sur le disque **et** dans l'index git (vérifié).
- L'extraction rend donc **zéro document clinique** sur Linux là où elle en
  rend un sur Windows. Comme le nom de fichier de l'archive est ce qui
  déclenche la pipeline CDA, un écart de comportement de l'extraction selon
  la plateforme mérite d'être compris et pas contourné — c'est du contenu
  clinique.

## Défaut 2 — contamination de dimensions entre suites partageant Postgres

```
Failed AiDiagnosticsControllerIntegrationTests.DebugVectorSearchAsync_WithSeededEmbedding_ComputesCosineDistances
  Npgsql.PostgresException : 22000: different vector dimensions 3 and 1536
```

Le fichier de test porte **déjà** le commentaire de la correction précédente :

> *« A 3-dim toy vector here made pgvector throw "different vector dimensions
> 1536 and 3" as soon as those 1536-dim rows coexisted. Use a deterministic
> 1536-dim vector so every row shares the same dimension. »*

L'erreur revient **dans l'autre sens** (`3 and 1536`) : ce n'est donc plus ce
test qui sème un vecteur à 3 dimensions, c'en est **un autre**, partageant le
conteneur Postgres de la collection `PostgreSql`. L'ordre d'exécution diffère
sur Linux, et la contamination devient visible.

C'est un **défaut d'isolation entre suites partageant un conteneur** — la
classe de problème que `todo-task-301` traite (harnais partagé, table
d'attribution, isolation vérifiée par un test de garde).

## L'arbitrage demandé

Le registre `Api/Mail/tests/quarantine.md` existe et son mécanisme est
**vérifié** (97 → 96 avec un test étiqueté). Mais son contrat exige qu'une
entrée **nomme la task qui la corrigera** — et la forge ne crée pas de task
d'elle-même (règle de `/forge` : pas de chasse au backlog, pas de task de
suivi auto-créée).

Trois conduites possibles :

| Option | Effet | Quand la choisir |
|---|---|---|
| **A — deux tasks de correction, puis quarantaine** | Tu crées `/po` deux US (une par défaut), je pose les traits `[Trait("Quarantine", "task-NNN")]` et les deux lignes du registre. La CI de #230 passe au vert, le gate est armé, les défauts sont tracés et datés. | **Recommandé.** C'est le mécanisme prévu, et il force la reprise des deux défauts au lieu de les enterrer. |
| **B — corriger les deux maintenant, dans task-300** | La PR grossit et sort de son périmètre (elle ne devait toucher aucun code de production). Le défaut 2 recoupe `task-301`. | Si tu veux une PR verte sans dette ouverte, et que le coût de diagnostic est jugé faible. |
| **C — merger #230 avec la CI rouge** | Le gate serait armé mais son premier signal ignoré. | **Déconseillé** : cela viderait de son sens la US qui vient d'être écrite. |

**Ma recommandation : A.** Le défaut 2 a de bonnes chances d'être **résolu
mécaniquement par `task-301`** (isolation des suites), donc sa task de
correction peut être `task-301` elle-même. Seul le défaut 1 appelle une US
dédiée.

## Ce qui n'est pas en question

- La PR #230 reste ouverte et correcte. Aucun rollback n'est proposé.
- Le reste du run `/forge` (task-301 à 304) continue : ces deux défauts
  n'appartiennent pas à leur périmètre, et task-301 pourrait en résoudre un.
