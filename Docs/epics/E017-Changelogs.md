# E017 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E017-traitements-ia-en-local-fournisseur.md](E017-traitements-ia-en-local-fournisseur.md).
> **Dernière mise à jour** : 2026-10-08 (v1.1)

---

## Historique détaillé des changelogs

### v1.0 — Un fournisseur IA par capacité, chat sur Ollama GPU, embeddings sur OpenAI — task-325

- **Task** : task-325, statut `done`. PR `api-mail` #265, label `awaiting-human-merge`, branche `feat/task-325-ia-locale-ollama`. Aucun contrat : pas de branche `dtos-mss`, pas de NuGet, aucun frontend.
- **Motif** : sur 15 jours de rétention Prometheus (2026-09-05 → 2026-09-20), 1 270 758 requêtes HTTP 200 vers `api.openai.com` et 15 536 en 429. Le chat `gpt-4o-mini` pèse environ neuf dixièmes de la facture estimée. Les tokens n'étaient pas mesurés.
- **Sélection** : `AiProvider:Chat` et `AiProvider:Embedding` (`OpenAI` | `Ollama`, casse ignorée), validés au démarrage par `AiProviderSelection.FromConfiguration`.
  - Une valeur inconnue (`OpenIA`), une valeur absente, une valeur numérique (`1`) ou l'ancienne clé `AiProvider:Provider` lèvent `InvalidOperationException`. Rouge prouvé d'abord : `OpenIA` sélectionnait OpenAI en silence.
  - `OpenAi:ApiKey` n'est exigée que si une capacité passe par OpenAI, côté API (`EnsureProvidersAreReachable`) comme côté AppHost (`WithOpenAiKeyIfRequired`).
- **Défauts** : AppHost hybride (Chat=Ollama, Embedding=OpenAI) ; `appsettings.json` tout-OpenAI.
  - Ce second défaut vient de la revue : les configmaps Prod et Staging ne posent aucun `AiProvider__*`, et le chat serait parti vers `127.0.0.1:11434`.
  - Décision humaine. Garde : `EmbeddingOptionsConsistencyTests`, prouvé rouge.
- **Kernel** : `AiKernelFactory.Build` compose un `IChatCompletionService` et un `IEmbeddingGenerator` via les extensions Semantic Kernel 1.80.1 (connecteur Ollama 1.77.0-alpha).
  - Décorateurs `MeteredChatCompletionService` et `MeteredEmbeddingGenerator` → `mssante_ai_tokens_total{provider,model,kind}`. Seuls les tokens déclarés par le fournisseur sont comptés, via `AiTokenUsageReader`.
  - `OpenAi:Endpoint` est transmis (un seul `OpenAIClient`, retries du SDK à 0).
  - Deux clients nommés poolés : `SemanticKernelOpenAI` et `SemanticKernelOllama`.
  - `AiConversationService` passe sur des `PromptExecutionSettings` neutres.
- **Métriques** : `RecordAiPipelineExecuted` et `RecordAiPipelineDuration` portent `provider`. Le pipeline complet vaut `mixed` quand les deux fournisseurs diffèrent.
- **Colonne `EmbeddingModel`** (varchar 128) sur `MailContents` et `MailMedicalDocuments`, migration FluentMigrator `20260930180000_AddEmbeddingModelColumns`.
  - Rétro-remplissage à `openai:text-embedding-3-small` des seules lignes vectorisées.
  - Audit 7c : fichier lu, pas d'opération fantôme, schéma prouvé par `AddEmbeddingModelColumnsMigrationTests`.
- **Recherche** : `SemanticSearchRepository` lit les vecteurs par deux racines filtrées sur le modèle actif, `EmbeddedContents` et `EmbeddedDocuments`.
  - `RunVectorQueryAsync` traduit SQLSTATE 22000 « different vector dimensions » en `ConflictException` → 409 `ProblemDetails`.
  - `SemanticSearchService` relance ce conflit sur les recherches hybride et par patient.
  - Mutations prouvées : retirer le filtre, ou retirer le mappage, fait passer au rouge.
- **AppHost** : conteneur `mss-mail-ollama` (`ollama/ollama`, port 11434, volume `mss-mail-ollama-models`, `--gpus=all` sauf `MSS_OLLAMA_GPU=none`, `OLLAMA_KEEP_ALIVE=24h`).
  - Conteneur de tirage `mss-mail-ollama-pull` des seuls modèles utilisés (`AiProviderProfile.ModelsToPull`), attendu par l'API (`WaitForCompletion`).
  - Nom de modèle validé avant la commande shell.
  - Profil e2e : les deux capacités sont servies par le faux fournisseur, sans conteneur ni clé.
- **Code mort retiré** : `FlexibleEmbeddingService`, `IEmbeddingProviderService`, `BaseEmbeddingProviderService`, `OllamaEmbeddingProviderService`, `OpenAiEmbeddingProviderService`, et leurs tests.
- **Passe qualité `/simplify`** (`4380ee62`) : prédicat du modèle recopié 13 fois ramené à deux racines ; `ServiceOf<T>` pour les 4 connecteurs ; `ChatModelOf` ; la borne d'embedding lit le fournisseur comme la sélection. Deux écarts au DOD corrigés à part (`efdbb2bd`) : 409 sur la recherche par patient, tirage de `bge-m3`.
- **Sonar** (9.9.8, new code sur 30 jours) : Quality Gate OK, new_coverage 97,6 %.
  - 3 code smells corrigés : S3267 (récidive, écrite par la passe qualité), S3604 ×2 (code de task-342).
  - Code smells du projet : 10 → 8.
- **Tests** : 0 échec. domain 190, infrastructure 677, api 1148, application 3272, integration 673 (16 ignorés, cas d'usage IA réels).
- **E2E** : voies mobile et Angular vertes (24/24 chacune), parité verte, E2E-AI-001 et E2E-LIVE-001 verts avec le profil e2e sur Ollama.
- **Leçons capturées** :
  - `TrackedSourceScan` voit maintenant les fichiers non ajoutés (`64a7b876`) : deux captures de mesures non sérialisées étaient passées.
  - `conventions/csharp.md` : `collection-postgresql-partagee`, `defaut-de-dev-dans-appsettings`, S3267 et S3604 incrémentés.
  - `conventions/e2e.md` : `garde-de-port-ipv4-seul`.
  - §Q de `agents/develop.md` : relire les conventions avant d'appliquer les nettoyages.
- **Limites reportées (suggestions de revue)** :
  - `ollama pull` à chaque démarrage bloque l'API hors ligne ;
  - backfill `openai:` sur d'éventuelles bases e2e persistantes ;
  - `AiDiagnosticsController` sans filtre de modèle ;
  - `ActiveEmbeddingModel.Dimension` jamais vérifiée ;
  - `Arg.Any<string>()` sur l'identifiant de modèle dans `AddNewMailConsumerTests` et `EmbeddingReindexServiceTests` ;
  - comptage des tokens en streaming non prouvé contre le connecteur Ollama réel ;
  - 73 fichiers, au-delà de la règle 5.
- **À la HAG** : démarrage GPU et `ollama list`, parcours bout en bout avec identifiants Seq, recherche identique, assistant et rédaction, Grafana.

---

### v1.1 — Ollama traite plusieurs étiquetages à la fois ; gabarit réordonné écarté par la garde qualité — task-355

- **Task** : task-355, statut `done`. PR `api-mail` #282, label `awaiting-human-merge`, branche
  `feat/task-355-ollama-parallele-gabarit-prefixe`. Aucun contrat, aucun frontend.
- **Motif** : campagne terrain 1000 hybride du 2026-10-07/08. Ollama (`qwen2.5:14b`, RTX 5070 Ti)
  à `OLLAMA_NUM_PARALLEL=1` étiquette 40 à 45 mails/min pour ~44 arrivées/min. Attente moyenne
  61 s, 42 timeouts à 180 s sur 3 h, file `add-new-mail-queue` à 94 000 après chauffe.
- **Livré** :
  - `AiProviderProfile.OllamaNumParallel` : défaut 4, surcharge `MSS_OLLAMA_NUM_PARALLEL`.
    `NumberStyles.None`, bornes 1..8 ; sinon `InvalidOperationException` actionnable.
  - `AppHost.cs` : `OLLAMA_NUM_PARALLEL` sur `mss-mail-ollama`.
  - `docs/ia-fournisseurs.md`.
- **Conteneur persistant** : Aspire le **recrée** quand la valeur change. Constaté 2 → 4 :
  `Created` changé deux fois, `docker logs` affiche `OLLAMA_NUM_PARALLEL:2` puis `:4`.
- **Débit** (micro-banc `Docs/audits/ollama-bench-20261008/`, 50 demandes simultanées, gabarit
  actuel) :
  - P=1 : 40,8/min, 11,2 Go ;
  - P=2 : 45,6/min, 12,2 Go ;
  - **P=4 : 45,6/min, 13,6 Go** ;
  - P=6 : 49,2/min, 15,2 Go.
  - Le goulet est le calcul du prompt (~2 550 tokens).
- **Écarté — gabarit d'étiquetage réordonné** (grille constante avant type et expéditeur, pour le
  cache de préfixe) :
  - Ce qu'il apportait : 79,3/min à P=4, calcul du prompt 0,71 → 0,37 s, et une grille de
    1 171 tokens `o200k` éligible au cache de prompt OpenAI.
  - **Garde qualité échouée** (`guard.py`, 200 contenus cliniques de `JEUX_TESTS_FULL` :
    125 CDA distincts, 8 suites de documents longs, 67 extraits) :
    - ancien contre nouveau : 89,5 à 94 % de concordance ;
    - bruit du modèle (même gabarit rejoué) : 92,5 à 96 % ;
    - température 0 : 13 descentes, 0 montée, deux fois ;
    - « Urgent » : ~21 → ~15.
  - **Arbitrage A** du responsable produit : parallélisme seul. Le commit du gabarit (`75e214c3`)
    est retiré par `c456a028`, et `EmailTaggingService.cs` est identique à `develop`.
- **Tests** : 0 échec. domain 190, infrastructure 683, application 3 552, api 1 183, integration
  830 (16 ignorés).
  - 10 cas nouveaux dans `AiProviderProfileTests` : mutations « variable ignorée » (8 rouges) et
    « bornes retirées » (seuls `0` et `9`).
  - `OllamaServerEnvironmentWiringTests` : lecture de la source de l'AppHost, mutation prouvée.
  - `TaggingPromptPrefixTests` : vu rouge sur l'ancien ordre, puis retiré avec le gabarit.
- **Passe qualité `/simplify`** (`8e76759e`) :
  - propriété `OllamaServerEnvironment` retirée ;
  - `MemoryExtensions.CommonPrefixLength` au lieu d'une boucle ;
  - écartés : un `BuildKernel` de test partagé, et l'ordre « constante d'abord » dans
    `AiPromptHelper` (résumé), hors périmètre.
- **Sonar** (9.9.8, new code sur 30 jours) : Quality Gate OK, new_coverage 97,6 → 97,5 %.
  - 0 constat sur le code de la task, puisque `src/AppHost/**` est exclu de l'analyse.
  - Reste un S107 sur `SemanticSearchService.cs:395` (task-329), hors task.
  - Code smells du projet : 13 → 13.
- **E2E** : voies mobile (31/31) et Angular (30 verts, 1 flaky) vertes, parité verte. Le flaky
  est E2E-COMPOSE-002 Angular, 4e occurrence : bug produit connu, task-350 en `todo`.
- **Leçons capturées** :
  - mémoire de session `garde-concordance-llm-bruit-du-modele` : juger une garde de prompt contre
    le bruit du modèle rejoué, et sur le sens des écarts ;
  - `questions/task-355.md` : seuil de 95 % au niveau du bruit, à revoir dans `/po` ;
  - `conventions/e2e.md` : registre des flaky, E2E-COMPOSE-002 incrémenté.
- **Limites reportées (suggestions de revue)** :
  - P=2 donne le même débit que P=4 avec le gabarit actuel, pour 1,4 Go de moins ;
  - dans `docs/ia-fournisseurs.md`, le paragraphe « `127.0.0.1:11434` » se retrouve sous le
    sous-titre « Pourquoi le gabarit… » ;
  - la réserve de l'IA locale au terrain 1000 reste quasi nulle (45,6/min pour ~44/min).
- **À la HAG** : `docker logs` affiche `OLLAMA_NUM_PARALLEL:4`, puis `:2` avec la surcharge ;
  refus de démarrer avec `0` et `abc` ; micro-banc à ~45/min ; étiquettes visibles inchangées.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Emplacement | Rôle |
|--------|-------------|------|
| Sélection des fournisseurs | `src/Application/Configuration/AiProviderSelection.cs`, `AiProviderKind.cs`, `ActiveEmbeddingModel.cs` | Validation au démarrage, modèle actif |
| Composition du kernel | `src/Api/Extensions/SemanticKernelExtensions.cs`, `src/Api/Extensions/Ai/AiKernelFactory.cs` | Connecteurs, clients HTTP nommés |
| Comptage des tokens | `src/Api/Extensions/Ai/MeteredChatCompletionService.cs`, `MeteredEmbeddingGenerator.cs` | `mssante_ai_tokens_total` |
| Journal de démarrage | `src/Api/Extensions/Ai/AiProviderStartupReport.cs` | `[AiProvider] Chat=…, Embedding=…` |
| Filtre de modèle | `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs` | Racines filtrées, 409 sur dimension |
| Migration | `src/Infrastructure/Migrations/MailDb/20260930180000_AddEmbeddingModelColumns.cs` | Colonne `EmbeddingModel` |
| AppHost | `src/AppHost/AiProviderProfile.cs`, `AiResourceExtensions.cs`, `AppHost.cs` | Conteneurs Ollama, variables |
| Exploitation | `docs/ia-fournisseurs.md` | Choisir, basculer, mesurer, régler le parallélisme Ollama |
| Garde qualité de gabarit | `Docs/audits/ollama-bench-20261008/guard.py` (plan de contrôle) | Concordance ancien/nouveau gabarit d'étiquetage, bruit du modèle, température 0 |

---

## Annexe B — Inventaire fonctionnel daté

*À compléter au premier `--refresh`.*

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | RGs |
|------|--------------|-----|
| task-325 | Fournisseur IA par capacité, chat local sur Ollama, embeddings OpenAI, colonne `EmbeddingModel`, comptage des tokens | RG-E017-01, RG-E017-02, RG-E017-03 |
| task-355 | `OLLAMA_NUM_PARALLEL` (défaut 4, surcharge validée 1..8) ; gabarit réordonné mesuré puis écarté par la garde qualité (arbitrage A) | — |
