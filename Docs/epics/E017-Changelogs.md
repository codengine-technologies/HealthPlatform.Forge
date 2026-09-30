# E017 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E017-traitements-ia-en-local-fournisseur.md](E017-traitements-ia-en-local-fournisseur.md).
> **Dernière mise à jour** : 2026-09-30 (v1.0)

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
| Exploitation | `docs/ia-fournisseurs.md` | Choisir, basculer, mesurer |

---

## Annexe B — Inventaire fonctionnel daté

*À compléter au premier `--refresh`.*

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | RGs |
|------|--------------|-----|
| task-325 | Fournisseur IA par capacité, chat local sur Ollama, embeddings OpenAI, colonne `EmbeddingModel`, comptage des tokens | RG-E017-01, RG-E017-02, RG-E017-03 |
