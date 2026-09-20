# todo-task-325.md — Les traitements IA de la messagerie tournent en local : fournisseur réellement commutable, Ollama sur GPU dans l'AppHost, zéro appel OpenAI au banc et en développement

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E017
**EpicTitle**: Traitements IA en local — fournisseur commutable et souveraineté des données
**Single frontend**: true
**Priorité**: **2** — chaque campagne du banc de charge paie OpenAI pour des mails synthétiques. Sur les **15 jours de rétention Prometheus** (2026-09-05 → 2026-09-20), `api-mail` a émis **1 270 758 requêtes HTTP 200** vers `api.openai.com` et en a reçu **15 536 en 429**, pour **348 460 taggings** et **342 358 embeddings** de pipeline réussis (5 501 en erreur), plus la recherche sémantique et l'assistant. Aucun de ces appels ne porte de valeur médicale : ce sont des tirs. Le poste de banc dispose d'un GPU RTX 5070 Ti 16 Go, de 191 Go de RAM et de Docker 29, inutilisés pour l'IA.

> **Origine.** Analyse du 2026-09-20 (session forge, à la demande du responsable
> produit) du câblage IA de `api-mail` : tout passe par Semantic Kernel dans
> `Api/Mail/src/Api/Extensions/SemanticKernelExtensions.cs`. Cinq familles
> d'appels : pipeline par mail reçu (`AddNewMailConsumer` — embedding vers
> pgvector + auto-tagging JSON, pilotés par les flags `ai_pipeline`,
> `ai_embedding`, `ai_auto_tagging`), recherche sémantique (embedding de la
> requête), assistant conversationnel (`AiConversationService`, streaming +
> function calling sur les 5 outils d'`EmailActionsPlugin`), aide à la rédaction
> (`AiTextService`), résumé (`EmailSummaryService`). Modèles : `gpt-4o-mini`
> pour tout le chat, `text-embedding-3-small` (1536 dimensions).
>
> Chiffres Prometheus (`127.0.0.1:9090`, `increase(...[90d])` bornée par la
> rétention de 15 j) : durée moyenne d'une étape de pipeline **2,0 s** (tagging)
> et **2,6 s** (embedding), **0,89 s** par requête HTTP vers OpenAI. Les
> **tokens ne sont pas mesurés** : le coût en euros ne peut être qu'estimé
> (ordre de grandeur, à ~1 500 tokens par appel : ~1,9 milliard de tokens sur
> 15 jours, soit une centaine à quelques centaines d'euros par quinzaine de
> banc aux tarifs `gpt-4o-mini` / `text-embedding-3-small`). Cette US **rend le
> coût mesurable** avant de le supprimer.

## Ce qui est établi, et pourquoi la branche Ollama existante n'a jamais tourné

**Établi (lecture du code, 2026-09-20)** :
- Une branche Ollama existe : `OllamaOptions` (port 7869, `mistral`, `nomic-embed-text`), connecteur `Microsoft.SemanticKernel.Connectors.Ollama` 1.77.0-alpha référencé, `AddSemanticKernelWithOllama` écrit. Elle est **inatteignable** pour quatre raisons :
  1. L'AppHost injecte `AiProvider__Provider = "OpenIA"` (`Api/Mail/src/AppHost/AppHost.cs` ~l. 444, commentaire `// Ollama:OpenIA`). La faute de frappe retombe dans le `default` du `switch`, donc **silencieusement sur OpenAI**. Toute valeur inconnue fait de même.
  2. **Aucun conteneur Ollama** n'est déclaré, ni dans l'AppHost, ni dans `docker-compose.yml`, ni dans `devtools/docker-compose.yml`.
  3. L'option `OpenAi:Endpoint` (`https://api.openai.com/v1` dans `appsettings.json`) **n'est jamais passée au connecteur** : impossible de viser un serveur compatible OpenAI local (Ollama `/v1`, vLLM, LiteLLM) sans toucher au code. C'est une option morte.
  4. La branche Ollama n'a **ni HttpClient poolé ni timeout**, contrairement à la branche OpenAI depuis task-073 (`SocketsHttpHandler`, `PooledConnectionLifetime` 5 min, `TimeoutSeconds`).
- `AiConversationService` construit des `OpenAIPromptExecutionSettings` (~l. 173) pour porter `FunctionChoiceBehavior.Auto()` : un réglage **spécifique au connecteur OpenAI** sur un chemin censé être commutable.
- `FlexibleEmbeddingService`, `OpenAiEmbeddingProviderService`, `OllamaEmbeddingProviderService` et `IEmbeddingProviderService` ne sont **enregistrés nulle part** (constat déjà fait par task-073 pour `FlexibleEmbeddingService`). Ils prétendent gérer la dimension des vecteurs (1536 / 768) ; c'est du code mort. La colonne pgvector est déclarée `vector` **sans dimension fixe** et **aucun index HNSW / IVFFlat** n'existe : changer de modèle d'embedding ne demande pas de migration, mais un vecteur de requête d'une autre dimension que le corpus fait **échouer la requête SQL** au lieu de rendre un résultat vide.
- Mémoires de la forge convergentes : un **seul circuit** pour chat et embeddings, le `429 insufficient_quota` non transitoire est retenté et rouvre le circuit (`openai-circuit-partage-chat-embeddings`) ; au banc, la recherche est rouge à 67 % **à cause d'OpenAI**, pas de la base (`loadtest-page-en-tetes-charge-les-blobs`). Le fournisseur externe est aujourd'hui **le facteur limitant du banc sur la recherche**.

**Le poste** : GPU NVIDIA RTX 5070 Ti (16 303 Mio), Ryzen 9 7900X 12 cœurs, 191 Go de RAM, Docker 29.6.2. Le passthrough GPU fonctionne sous Docker Desktop (WSL2) avec `--gpus=all`. Aspire 13.5.3 ; le paquet communautaire `CommunityToolkit.Aspire.Hosting.Ollama` existe en **13.5.0** (support GPU et téléchargement des modèles au démarrage).

## Objective

Que les cinq familles de traitements IA d'`api-mail` puissent tourner **intégralement sur le poste**, sans clé ni appel OpenAI, par simple choix de fournisseur, et que ce soit le **mode par défaut** du développement et du banc de charge. OpenAI reste disponible sur **opt-in explicite** (la clé n'est plus exigée au démarrage quand le fournisseur est local).

Ce que cette US change : la facture OpenAI du banc tombe à zéro, la recherche sémantique cesse d'être rouge pour une cause externe, et **aucun contenu de mail ne quitte le poste** pour être résumé, étiqueté ou vectorisé. Ce qu'elle **ne change pas** : les contrats (aucun DTO), les frontends, la logique métier des prompts, les flags Flagsmith qui pilotent le pipeline.

### Périmètre

1. **Sélecteur de fournisseur fiable** : la valeur d'`AiProvider:Provider` est validée au démarrage — `OpenAI` ou `Ollama`, insensible à la casse ; toute autre valeur (dont `OpenIA`) **fait échouer le démarrage** avec un message clair, jamais un repli silencieux. L'AppHost injecte la valeur correcte, et la clé `OpenAi__ApiKey` n'est plus `Require` (obligatoire) que si le fournisseur retenu est OpenAI.
2. **Endpoint OpenAI honoré** : `OpenAi:Endpoint` est réellement passé aux deux connecteurs (chat + embeddings). Conséquence : n'importe quel serveur **compatible OpenAI** (Ollama `/v1`, vLLM, LiteLLM, LocalAI) est utilisable **sans changement de code**, ce qui prépare un éventuel passage à vLLM pour le débit du banc (hors périmètre ici).
3. **Ollama dans l'AppHost, sur GPU** : ressource Aspire (paquet communautaire ci-dessus, ou conteneur `ollama/ollama` équivalent si le paquet pose problème avec Aspire 13.5.3) avec **GPU exposé**, **volume persistant** pour les modèles (pas de re-téléchargement à chaque démarrage), modèles tirés automatiquement au premier lancement, `api-mail` en `WaitFor` sur la ressource. L'`Ollama:Endpoint` est injecté depuis la référence Aspire (fin du `localhost:7869` codé en dur, et attention au piège `localhost → ::1` documenté dans l'AppHost pour Postgres et Seq).
4. **Parité de la branche Ollama** : HttpClient nommé et poolé + `TimeoutSeconds`, comme la branche OpenAI. `AiConversationService` utilise des `PromptExecutionSettings` **neutres** (le `FunctionChoiceBehavior` vit sur la classe de base) pour que le function calling passe par les deux fournisseurs.
5. **Modèles par défaut, avec leurs exigences** : le modèle de chat doit **tenir dans 16 Go de VRAM**, être **bon en français**, supporter les **outils** (function calling) en streaming et produire du **JSON exploitable** par `ParseTagsFromResponse`. Suggestion de départ : `qwen2.5:14b` (ou `qwen3:14b`), `mistral-nemo` en alternative. Le modèle d'embedding doit être **multilingue** : `bge-m3` (1024 dimensions) plutôt que `nomic-embed-text`, faible en français clinique. Ces valeurs sont des **défauts de configuration**, changeables sans code. Les défauts actuels (`mistral`, `nomic-embed-text`) sont remplacés.
6. **Cohérence corpus / requête d'embedding** : au démarrage, `api-mail` journalise le fournisseur, les modèles et la dimension d'embedding actifs. Une recherche dont le vecteur de requête n'a **pas la dimension du corpus** rend une erreur métier explicite (`ProblemDetails`, règle 12, message sans donnée de santé) au lieu d'une erreur SQL en 500. La **réindexation** d'un corpus existant après changement de modèle est **hors périmètre** (voir ci-dessous) : au banc, `reset-state` repart d'une base vierge.
7. **Le coût devient mesurable** : un compteur `mssante_ai_tokens_total{provider, model, kind=prompt|completion|embedding}` alimenté par l'`usage` renvoyé par les fournisseurs quand il est disponible, et les métriques `mssante_ai_pipeline_*` existantes **étiquetées `provider`**. Un panneau « IA — fournisseur, appels, tokens » ajouté au tableau de bord Grafana `mssante-mail-processing.json`. C'est ce qui permettra d'écrire, chiffres à l'appui, ce que la campagne suivante n'a pas payé.
8. **Code mort retiré** : `FlexibleEmbeddingService`, `IEmbeddingProviderService` et ses deux implémentations sont **supprimés** (ou enregistrés et utilisés, mais pas les deux : la dimension ne doit être déclarée qu'à un seul endroit, celui du § 6). Leurs tests suivent.
9. **Documentation d'exploitation** : une page `Api/Mail/docs/` (ou section du README de l'AppHost) qui dit comment choisir le fournisseur, quels modèles sont tirés, où vit le volume, comment revenir à OpenAI, et ce qu'implique un changement de modèle d'embedding. Le skill `loadtest-skill` est mis à jour pour que le banc parte **en local par défaut**.

### Décisions prises par le PO, à contredire si besoin

- **Défaut = local**, en développement comme au banc. OpenAI sur opt-in explicite. Motif : le coût est payé sur des données synthétiques, et le local est aussi la voie **HDS-compatible** pour de la donnée réelle. Si l'humain préfère garder OpenAI par défaut en développement pour la qualité de l'assistant, une seule variable d'environnement suffit.
- **Qualité non certifiée par cette US.** Un modèle 14B en Q4 étiquette et résume moins bien que `gpt-4o-mini`, et suit moins strictement le format JSON. Cette US exige que le pipeline **fonctionne** (JSON parsé, embeddings stockés, assistant qui appelle un outil) ; la **mesure d'écart de qualité** (précision du tagging sur un jeu de mails de référence, avant/après) est une US séparée de la même EPIC.

### Hors périmètre, explicitement

- **vLLM / TEI / LiteLLM** : débit et routage. Le § 2 les rend possibles sans code ; les monter est une autre US.
- **Réindexation** d'un corpus d'embeddings existant après changement de modèle (batch de re-vectorisation des mails déjà stockés).
- **Banc de qualité** tagging / résumé / assistant, modèle local vs `gpt-4o-mini`.
- Tout changement des prompts, des flags Flagsmith, de `Dtos/`, des frontends.
- Le circuit partagé chat / embeddings et le traitement du `429 insufficient_quota` (mémoire `openai-circuit-partage-chat-embeddings`) : à instruire si OpenAI reste utilisé quelque part ; sans objet en local.

### Mesure — après, sur la campagne suivante

Sur la prochaine campagne `terrain` (celle de task-323 ou toute autre), lancée en fournisseur local : **0 requête** vers `api.openai.com` dans `http_client_request_duration_seconds_count` ; `mssante_ai_pipeline_total{status="success"}` en proportion **≥** à la campagne du 19/09 (tagging et embedding) ; recherche sémantique **sans erreur attribuée au fournisseur** ; `mssante_ai_tokens_total` non nul avec `provider="Ollama"` ; utilisation GPU visible (`nvidia-smi`) pendant le tir. Les durées de pipeline (2,0 s / 2,6 s aujourd'hui) sont **relevées, pas exigées** : un 14B local sur un seul GPU peut être plus lent sous 1 000 praticiens ; c'est la donnée d'entrée de la US vLLM.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Preuve du ROUGE d'abord** : un test montre que `AiProvider:Provider = "OpenIA"` (et toute valeur inconnue) sélectionne aujourd'hui OpenAI en silence ; après correctif, le démarrage échoue avec un message explicite — ≥ 1 test par cas (`OpenAI`, `ollama` en minuscules, valeur inconnue, vide)
- [ ] `OpenAi:Endpoint` est transmis aux connecteurs chat et embeddings — test unitaire sur la construction du Kernel (endpoint factice observé sur le HttpClient / la requête)
- [ ] La clé OpenAI n'est **pas exigée** quand le fournisseur est Ollama — test ; elle reste exigée quand le fournisseur est OpenAI — test
- [ ] Branche Ollama : HttpClient nommé et poolé avec `TimeoutSeconds` — test de configuration
- [ ] `AiConversationService` n'a plus de dépendance de type au connecteur OpenAI (`OpenAIPromptExecutionSettings` remplacé par le type de base) — vérifié par `grep` dans la PR et par les tests existants du service, verts
- [ ] Ressource Ollama déclarée dans l'AppHost avec GPU, volume persistant, modèles tirés au démarrage, `api-mail` en `WaitFor` et `Ollama__Endpoint` injecté depuis la référence — démarrage de l'AppHost observé, `ollama list` dans le conteneur montre les deux modèles
- [ ] Parcours bout en bout en local, **sans clé OpenAI dans l'environnement** : un mail injecté par le seed est étiqueté (tags persistés) et vectorisé (ligne pgvector), une recherche sémantique rend des résultats, l'assistant répond en streaming et déclenche au moins un outil d'`EmailActionsPlugin`, l'aide à la rédaction améliore un texte — consigné dans le task file avec les identifiants Seq
- [ ] Recherche avec un vecteur de dimension différente du corpus → `ProblemDetails` métier (4xx), jamais 500 SQL — test unitaire ou d'intégration
- [ ] Compteur `mssante_ai_tokens_total{provider,model,kind}` et étiquette `provider` sur `mssante_ai_pipeline_*` — tests sur `MailProcessingMetrics` ; panneau Grafana ajouté au tableau `mssante-mail-processing.json`
- [ ] `FlexibleEmbeddingService`, `IEmbeddingProviderService` et implémentations supprimés (ou enregistrés et utilisés — un seul lieu déclare la dimension), tests associés ajustés, build vert
- [ ] Documentation d'exploitation écrite (choix du fournisseur, modèles, volume, retour à OpenAI, changement de modèle d'embedding) ; `loadtest-skill` mis à jour pour le défaut local
- [ ] Aucune donnée de santé ni contenu de mail dans les nouveaux logs et métriques (les étiquettes sont `provider`, `model`, `kind` — jamais de texte de prompt)
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché, prompts inchangés
- [ ] Le body de la PR cite les chiffres Prometheus du 2026-09-20 (1 270 758 requêtes / 15 536 en 429 sur 15 j) et l'objectif « 0 requête `api.openai.com` à la campagne suivante »

## Manual Test Plan

- **Prérequis** : Docker Desktop avec intégration GPU active (`docker run --rm --gpus=all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi` affiche la RTX 5070 Ti). Retirer ou vider `OpenAi__ApiKey` de l'environnement / des secrets du poste pour la durée du test.
- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`. Dans le tableau de bord Aspire, la ressource Ollama passe en « Running » ; au premier lancement, les journaux montrent le téléchargement des deux modèles (plusieurs minutes, une seule fois grâce au volume). `api-mail` démarre **après** et journalise `AiProvider=Ollama`, les modèles et la dimension d'embedding.
- **Pipeline** : seeder une boîte (`loadtest-skill`, quelques mails suffisent), vérifier dans Seq (`seq-local`) les événements `[SuggestTagsAsync]` puis les tags persistés, et dans Postgres (`mcp postgresql`) une ligne d'embedding pour le mail. `nvidia-smi` montre le processus Ollama avec de la VRAM occupée.
- **Recherche** : dans `client-blazor`, recherche sémantique sur un terme présent dans le mail seedé → résultats rendus, aucune erreur.
- **Assistant** : ouvrir l'assistant sur la boîte, demander « propose une réponse à ce mail » → réponse en streaming, puis « appelle le patient » → l'action `call_patient` est capturée (log `[AiConversationService] Action captured from filter`).
- **Aide à la rédaction** : améliorer un texte depuis le composeur → texte réécrit.
- **Fournisseur invalide** : mettre `AiProvider__Provider=OpenIA` → `api-mail` refuse de démarrer avec un message explicite dans les journaux Aspire.
- **Retour à OpenAI** : `AiProvider__Provider=OpenAI` + clé → démarrage normal ; sans clé → échec explicite.
- **Grafana** (`localhost:3000`, tableau mail processing) : le panneau IA montre `provider=Ollama`, des tokens comptés, zéro série `api.openai.com` sur la fenêtre du test.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — infrastructure des traitements IA, aucune exigence fonctionnelle nouvelle
- **Exigences DSR honorées** : non applicable — les fonctions IA (résumé, tags, recherche, assistant) sont hors référentiel Ségur ; aucun changement de leur périmètre fonctionnel
- **INS** : non applicable — aucun trait d'identité manipulé par l'US ; les contenus de mails traités par l'IA peuvent contenir des traits patient, et c'est précisément ce qui **cesse de quitter le poste**
- **Authentification PS** : inchangée (PSC / e-CPS) — l'US ne touche pas au chemin d'authentification
- **Habilitations** : inchangées — les traitements IA restent exécutés dans le contexte du praticien connecté
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : nouveaux événements techniques au démarrage (fournisseur, modèles, dimension) et compteurs de tokens par fournisseur ; aucun contenu de prompt ni de mail dans les journaux ou les étiquettes de métriques. Conservation : celle de Seq / Prometheus existante
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — **amélioration** : en fournisseur local, les contenus de mails (potentiellement DSCP) ne sont plus transmis à un sous-traitant hors périmètre HDS pour résumé, étiquetage ou vectorisation ; les modèles et leurs données transitoires vivent dans un volume Docker du poste (environnement de développement et de banc, données synthétiques)
- **AIPD / impact RGPD** : **à mettre à jour** — le registre des sous-traitants doit refléter qu'OpenAI n'est plus destinataire par défaut des contenus de mails en développement et au banc ; l'usage en production, s'il existe, reste à qualifier (fournisseur, localisation, clauses) dans une US de la même EPIC
