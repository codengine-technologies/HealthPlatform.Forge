# todo-task-325.md — Traitements IA hybrides : le chat (tags, résumé, assistant, rédaction) tourne en local sur Ollama GPU dans l'AppHost, les embeddings restent sur OpenAI ; fournisseur choisi par capacité, jamais de repli silencieux

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
> banc). Aux tarifs publics, le **chat `gpt-4o-mini` pèse environ neuf dixièmes
> de cette facture**, les embeddings `text-embedding-3-small` un dixième.
> Cette US **rend le coût mesurable** et supprime la part dominante.
>
> **Amendée le 2026-09-20 (même session), en mode hybride.** La première
> rédaction basculait aussi les embeddings en local. Or deux modèles
> d'embedding produisent deux espaces vectoriels sans correspondance, même à
> dimension égale : les bases praticien du banc, hydratées par la chauffe,
> portent des vecteurs OpenAI en 1536 dimensions dans `MailContents` et
> `MailMedicalDocuments`. Un modèle local en 1024 dimensions ferait échouer
> chaque recherche en erreur SQL de dimensions ; un modèle local en 1536
> rendrait des résultats silencieusement faux. Décision : **les embeddings
> restent sur OpenAI**, le corpus reste valide, et la bascule des embeddings
> attend une US de re-vectorisation (task-326, à rédiger) que cette US prépare
> par une **colonne modèle par ligne**.

## Revue du constat (2026-09-27)

**Toujours d'actualité, constat intact** sur `origin/develop` d'api-mail (`dff07dce`). Depuis la
rédaction, seuls deux commits ont touché les fichiers concernés, et aucun ne change le câblage IA :
task-171 (#248, jeton PSC, ajouts dans `AppHost.cs` sans rapport avec l'IA) et le nettoyage Sonar
(#249, renommages cosmétiques dans des tests d'embedding et de tagging). Chaque point vérifié :

- `AppHost.cs:444` porte toujours `.WithEnvironment("AiProvider__Provider", "OpenIA")`.
- Toujours aucun conteneur Ollama ; `OpenAi:Endpoint` toujours ignoré par `SemanticKernelExtensions`
  (seul l'`Ollama:Endpoint` est lu).
- `AiConversationService.cs:173` construit toujours des `OpenAIPromptExecutionSettings`.
- `FlexibleEmbeddingService`, `IEmbeddingProviderService`, `BaseEmbeddingProviderService` toujours
  présents et non enregistrés (seul un commentaire task-073 les cite dans `SemanticKernelExtensions`).
  Ajouter `BaseEmbeddingProviderService` à la liste du §10.
- Toujours aucune colonne `EmbeddingModel` en base, aucun compteur de tokens.
- `OllamaOptions` : toujours `nomic-embed-text` (et `mistral`) par défaut.

**Deux compléments, non vus à la rédaction** :

- **Une brique de re-vectorisation existe déjà.** `EmbeddingReindexService` (task-196, 2026-08-08),
  exposé par `MailMaintenanceController` (`POST embeddings/reindex/{documentId}`,
  `POST embeddings/reindex-missing`), sait inventorier et re-vectoriser les **documents médicaux**
  **sans vecteur**, sans session IMAP. Il ne connaît ni le modèle ni `MailContents`. Hors périmètre
  ici, mais c'est la base naturelle de task-326. **Point d'attention pour le §7** : une fois la
  recherche filtrée sur le modèle actif, un document vectorisé par un autre modèle est invisible à la
  recherche **sans** figurer dans l'inventaire des « non indexés ». Cette US ne doit pas l'aggraver
  (défaut : un seul modèle en base), et task-326 devra étendre l'inventaire à « non indexé **pour le
  modèle actif** ».
- **Versions Aspire à vérifier pour le §4.** Le paquet `Aspire.Hosting.AppHost` est en 13.5.3, mais
  le SDK du projet AppHost est déclaré `Aspire.AppHost.Sdk` **9.3.1**
  (`mss.mail.AppHost.csproj`). Avant d'ajouter `CommunityToolkit.Aspire.Hosting.Ollama` 13.5.0,
  vérifier que ce décalage ne gêne pas le paquet communautaire ; sinon, prendre la voie de repli
  déjà prévue (conteneur `ollama/ollama` déclaré à la main).

## Ce qui est établi, et pourquoi la branche Ollama existante n'a jamais tourné

**Établi (lecture du code, 2026-09-20)** :
- Une branche Ollama existe : `OllamaOptions` (port 7869, `mistral`, `nomic-embed-text`), connecteur `Microsoft.SemanticKernel.Connectors.Ollama` 1.77.0-alpha référencé, `AddSemanticKernelWithOllama` écrit. Elle est **inatteignable** pour quatre raisons :
  1. L'AppHost injecte `AiProvider__Provider = "OpenIA"` (`Api/Mail/src/AppHost/AppHost.cs` ~l. 444, commentaire `// Ollama:OpenIA`). La faute de frappe retombe dans le `default` du `switch`, donc **silencieusement sur OpenAI**. Toute valeur inconnue fait de même.
  2. **Aucun conteneur Ollama** n'est déclaré, ni dans l'AppHost, ni dans `docker-compose.yml`, ni dans `devtools/docker-compose.yml`.
  3. L'option `OpenAi:Endpoint` (`https://api.openai.com/v1` dans `appsettings.json`) **n'est jamais passée au connecteur** : impossible de viser un serveur compatible OpenAI local (Ollama `/v1`, vLLM, LiteLLM) sans toucher au code. C'est une option morte.
  4. La branche Ollama n'a **ni HttpClient poolé ni timeout**, contrairement à la branche OpenAI depuis task-073 (`SocketsHttpHandler`, `PooledConnectionLifetime` 5 min, `TimeoutSeconds`).
- Le sélecteur est **tout ou rien** : un seul `AiProvider:Provider` construit un kernel entièrement OpenAI ou entièrement Ollama. Pourtant le `Kernel` de Semantic Kernel est un conteneur de services où **chat et embeddings sont enregistrés séparément** : les consommateurs demandent `IChatCompletionService` d'un côté, `IEmbeddingGenerator<string, Embedding<float>>` de l'autre, sans connaître le fournisseur. Rien n'impose le même fournisseur aux deux — c'est ce que l'hybride exploite.
- `AiConversationService` construit des `OpenAIPromptExecutionSettings` (~l. 173) pour porter `FunctionChoiceBehavior.Auto()` : un réglage **spécifique au connecteur OpenAI** sur un chemin censé être commutable. La propriété existe sur le type de base `PromptExecutionSettings`.
- `FlexibleEmbeddingService`, `OpenAiEmbeddingProviderService`, `OllamaEmbeddingProviderService` et `IEmbeddingProviderService` ne sont **enregistrés nulle part** (constat déjà fait par task-073 pour `FlexibleEmbeddingService`). Ils prétendent gérer la dimension des vecteurs (1536 / 768) ; c'est du code mort. La colonne pgvector est déclarée `vector` **sans dimension fixe**, **aucun index HNSW / IVFFlat** n'existe, et **aucune colonne ne dit quel modèle a produit un vecteur** : les tables ne savent pas ce qu'elles contiennent.
- Mémoires de la forge convergentes : un **seul circuit** pour chat et embeddings, le `429 insufficient_quota` non transitoire est retenté et rouvre le circuit (`openai-circuit-partage-chat-embeddings`) ; au banc, la recherche est rouge à 67 % **à cause d'OpenAI**, pas de la base (`loadtest-page-en-tetes-charge-les-blobs`).

**Le poste** : GPU NVIDIA RTX 5070 Ti (16 303 Mio), Ryzen 9 7900X 12 cœurs, 191 Go de RAM, Docker 29.6.2. Le passthrough GPU fonctionne sous Docker Desktop (WSL2) avec `--gpus=all`. Aspire 13.5.3 ; le paquet communautaire `CommunityToolkit.Aspire.Hosting.Ollama` existe en **13.5.0** (support GPU et téléchargement des modèles au démarrage).

## Objective

Que le fournisseur IA soit choisi **par capacité** — chat d'un côté, embeddings de l'autre — et que, par défaut en développement et au banc, **tout le chat** (tags, résumé, assistant, aide à la rédaction) tourne **sur le GPU du poste** via Ollama pendant que **les embeddings restent sur OpenAI**, ce qui garde le corpus vectoriel du banc intact. Le passage des embeddings en local devient ensuite un changement de configuration, une fois la re-vectorisation livrée.

Ce que cette US change : la part dominante de la facture OpenAI disparaît, le contenu des mails ne sort plus du poste pour être étiqueté, résumé ou discuté, et un fournisseur mal orthographié fait échouer le démarrage au lieu de coûter en silence. Ce qu'elle **ne change pas** : les vecteurs (même modèle, même espace, mêmes recherches), les contrats (aucun DTO), les frontends, la logique des prompts, les flags Flagsmith.

### Périmètre

1. **Un sélecteur par capacité, validé au démarrage** : `AiProvider:Chat` et `AiProvider:Embedding`, chacun `OpenAI` ou `Ollama`, insensible à la casse. Toute autre valeur (dont `OpenIA`), ou une valeur manquante, **fait échouer le démarrage** avec un message clair — jamais de repli. L'ancienne clé `AiProvider:Provider` est **retirée** (pas d'alias : deux façons de dire la même chose, c'est une de trop). La clé `OpenAi__ApiKey` n'est exigée (`Require` côté AppHost, contrôle côté API) **que si au moins une capacité choisit OpenAI**. Défauts livrés : `Chat = Ollama`, `Embedding = OpenAI`.
2. **Un kernel composé** : `Kernel.CreateBuilder()` reçoit le connecteur de chat du fournisseur choisi pour le chat et le générateur d'embeddings du fournisseur choisi pour les embeddings, dans le même kernel. Les consommateurs actuels (`IChatCompletionService`, `IEmbeddingGenerator<string, Embedding<float>>`) ne bougent pas.
3. **Endpoint OpenAI honoré** : `OpenAi:Endpoint` est réellement passé aux connecteurs OpenAI (chat et embeddings). Conséquence : tout serveur **compatible OpenAI** (vLLM, LiteLLM, LocalAI) devient utilisable **sans code**, ce qui prépare la US débit du banc (hors périmètre ici).
4. **Ollama dans l'AppHost, sur GPU** : ressource Aspire (paquet communautaire ci-dessus, ou conteneur `ollama/ollama` équivalent si le paquet pose problème avec Aspire 13.5.3) avec **GPU exposé**, **volume persistant** pour les modèles, **modèle de chat tiré automatiquement** au premier lancement, `api-mail` en `WaitFor` sur la ressource. L'`Ollama:Endpoint` est injecté depuis la référence Aspire (fin du `localhost:7869` codé en dur ; attention au piège `localhost → ::1` documenté dans l'AppHost pour Postgres et Seq).
5. **Parité de la branche Ollama** : HttpClient nommé et poolé + `TimeoutSeconds`, comme la branche OpenAI depuis task-073 — **deux clients nommés**, un par fournisseur. `AiConversationService` utilise des `PromptExecutionSettings` **neutres** (le `FunctionChoiceBehavior` vit sur la classe de base) : le function calling en streaming doit passer par le connecteur Ollama natif.
6. **Modèle de chat local, avec ses exigences** : tenir dans **16 Go de VRAM**, être **bon en français**, supporter les **outils** en streaming, produire un **JSON exploitable** par `ParseTagsFromResponse`. Suggestion de départ : `qwen2.5:14b` (ou `qwen3:14b`), `mistral-nemo` en alternative. Le modèle d'embedding Ollama reste configuré (`bge-m3`, multilingue, plutôt que `nomic-embed-text`) mais **n'est pas actif par défaut** et n'est pas tiré au démarrage. Toutes ces valeurs sont des **défauts de configuration**, changeables sans code ; `mistral` et `nomic-embed-text` sont remplacés.
7. **Les tables savent ce qu'elles contiennent — colonne modèle d'embedding par ligne** : `MailContents` et `MailMedicalDocuments` reçoivent une colonne `EmbeddingModel` (chaîne courte, ex. `openai:text-embedding-3-small`) renseignée à chaque écriture de vecteur. Migration EF avec **rétro-remplissage** des lignes existantes à `openai:text-embedding-3-small` (elles n'ont jamais été produites par autre chose — constat § établi). La **recherche sémantique ne compare qu'aux lignes du modèle actif** : si un jour le modèle change, les anciens mails deviennent invisibles à la recherche au lieu de casser la requête ou de fausser les résultats, jusqu'à leur re-vectorisation (task-326). Audit de migration règle 7c obligatoire (fichier lu, `.Designer.cs` présent, pas d'opération fantôme, « has pending changes » vide).
8. **Ceinture en plus des bretelles** : au démarrage, `api-mail` journalise les deux fournisseurs, les modèles et la dimension d'embedding actifs. Une recherche dont le vecteur de requête n'a pas la dimension du corpus filtré rend une erreur métier explicite (`ProblemDetails`, règle 12, sans donnée de santé), jamais une erreur SQL en 500.
9. **Le coût devient mesurable** : compteur `mssante_ai_tokens_total{provider, model, kind=prompt|completion|embedding}` alimenté par l'`usage` renvoyé par les fournisseurs quand il existe ; métriques `mssante_ai_pipeline_*` étiquetées `provider`. Panneau « IA — fournisseur, appels, tokens » ajouté au tableau Grafana `mssante-mail-processing.json`. C'est ce qui prouvera, à la campagne suivante, que **plus aucun token de chat** ne part chez OpenAI.
10. **Code mort retiré** : `FlexibleEmbeddingService`, `IEmbeddingProviderService`, sa classe de base `BaseEmbeddingProviderService` et ses deux implémentations sont **supprimés**. La dimension et le nom du modèle actif ne sont déclarés qu'à un seul endroit (§ 7-8). Leurs tests suivent.
11. **Documentation d'exploitation** : page `Api/Mail/docs/` (ou section du README de l'AppHost) : choisir un fournisseur par capacité, modèles tirés, volume, retour au tout-OpenAI, ce qu'implique un changement de modèle d'embedding et le rôle de la colonne `EmbeddingModel`. Le skill `loadtest-skill` est mis à jour pour le défaut hybride.

### Décisions prises par le PO, à contredire si besoin

- **Hybride par défaut** (chat Ollama, embeddings OpenAI), en développement comme au banc. Motifs : le chat est la part dominante de la facture et la totalité de la donnée de santé « discutée » ; les embeddings sont bon marché et leur bascule casserait le corpus du banc. Le tout-OpenAI reste possible par deux variables d'environnement.
- **Les embeddings restent chez OpenAI pour l'instant, en connaissance de cause** : les 429 sous charge et la recherche rouge du banc restent attribuables à ce fournisseur tant que task-326 (re-vectorisation) n'est pas livrée. Cette US pose la colonne modèle qui rend cette bascule sûre.
- **Qualité non certifiée par cette US.** Un modèle 14B en Q4 étiquette et résume moins bien que `gpt-4o-mini`, et suit moins strictement le JSON. Cette US exige que le pipeline **fonctionne** (JSON parsé, assistant qui appelle un outil) ; la **mesure d'écart de qualité** sur un jeu de mails de référence est une US séparée de la même EPIC.

### Hors périmètre, explicitement

- **task-326 — re-vectorisation** : batch qui relit mails et documents et réécrit les vecteurs avec le modèle actif, base par base, puis bascule `AiProvider:Embedding = Ollama`. À rédiger ; dépend de la colonne `EmbeddingModel` posée ici. Partir de `EmbeddingReindexService` (task-196), qui re-vectorise déjà les documents médicaux sans vecteur, à étendre à `MailContents` et au critère « modèle différent du modèle actif ».
- **vLLM / TEI / LiteLLM** : débit et routage. Le § 3 les rend possibles sans code.
- **Banc de qualité** tagging / résumé / assistant, modèle local vs `gpt-4o-mini`.
- Tout changement des prompts, des flags Flagsmith, de `Dtos/`, des frontends.
- Le circuit partagé chat / embeddings et le `429 insufficient_quota` : le circuit n'a plus qu'un locataire (les embeddings) après cette US ; à instruire dans task-326 si la voie OpenAI subsiste.

### Mesure — après, sur la campagne suivante

Sur la prochaine campagne `terrain` après le merge, en défaut hybride : `mssante_ai_tokens_total{provider="OpenAI", kind=~"prompt|completion"}` **= 0** et `{provider="Ollama", kind=~"prompt|completion"}` **> 0** ; requêtes vers `api.openai.com` dans `http_client_request_duration_seconds_count` en **baisse d'au moins moitié** par rapport aux 15 jours de référence (il ne reste que les embeddings de pipeline et de recherche) ; `mssante_ai_pipeline_total{step="tagging", status="success"}` en proportion **≥** à la campagne du 19/09 ; utilisation GPU visible (`nvidia-smi`) pendant le tir ; **résultats de recherche identiques** avant/après sur une même requête et une même base (le corpus n'a pas bougé). La durée du tagging (2,0 s aujourd'hui) est **relevée, pas exigée** : un 14B sur un seul GPU peut être plus lent sous 1 000 praticiens ; c'est la donnée d'entrée de la US vLLM.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Preuve du ROUGE d'abord** : un test montre que `AiProvider:Provider = "OpenIA"` sélectionne aujourd'hui OpenAI en silence ; après correctif, la clé `Provider` n'existe plus et toute valeur inconnue ou manquante de `Chat` / `Embedding` fait échouer le démarrage avec un message explicite — ≥ 1 test par cas (`OpenAI`, `ollama` en minuscules, inconnue, vide, ancienne clé `Provider` seule)
- [ ] Kernel composé : `Chat = Ollama` + `Embedding = OpenAI` produit un `IChatCompletionService` Ollama et un `IEmbeddingGenerator` OpenAI dans le même kernel — test ; les trois autres combinaisons construisent aussi — test paramétré
- [ ] `OpenAi:Endpoint` transmis aux connecteurs OpenAI chat et embeddings — test (endpoint factice observé sur la requête)
- [ ] Clé OpenAI **exigée** dès qu'une capacité est OpenAI, **non exigée** en tout-Ollama — tests ; l'AppHost ne `Require` la clé que dans le même cas
- [ ] Deux HttpClients nommés et poolés avec `TimeoutSeconds`, un par fournisseur — test de configuration
- [ ] `AiConversationService` sans dépendance de type au connecteur OpenAI (`OpenAIPromptExecutionSettings` remplacé par `PromptExecutionSettings`) — `grep` dans la PR + tests existants verts
- [ ] Ressource Ollama dans l'AppHost avec GPU, volume persistant, modèle de chat tiré au démarrage, `api-mail` en `WaitFor`, `Ollama__Endpoint` injecté depuis la référence — démarrage observé, `ollama list` montre le modèle de chat
- [ ] Migration EF `EmbeddingModel` sur `MailContents` et `MailMedicalDocuments`, rétro-remplissage `openai:text-embedding-3-small`, **audit règle 7c** consigné dans le task file (fichier lu, `.Designer.cs`, pas d'opération fantôme, `has pending model changes` vide)
- [ ] Chaque écriture de vecteur renseigne `EmbeddingModel` avec le modèle actif — test ; la recherche sémantique (contenus et documents) **filtre sur le modèle actif** — ≥ 1 test par table, dont un cas « lignes d'un autre modèle ignorées, pas d'erreur »
- [ ] Vecteur de requête de dimension différente du corpus filtré → `ProblemDetails` métier (4xx), jamais 500 SQL — test
- [ ] Parcours bout en bout en défaut hybride : un mail seedé est **étiqueté par Ollama** (Seq montre `provider=Ollama` sur le tagging, tags persistés) et **vectorisé par OpenAI** (ligne pgvector avec `EmbeddingModel = openai:text-embedding-3-small`) ; une recherche rend les mêmes résultats qu'avant la branche sur la même base ; l'assistant répond en streaming et déclenche au moins un outil d'`EmailActionsPlugin` ; l'aide à la rédaction améliore un texte — consigné avec identifiants Seq
- [ ] Compteur `mssante_ai_tokens_total{provider,model,kind}` et étiquette `provider` sur `mssante_ai_pipeline_*` — tests sur `MailProcessingMetrics` ; panneau Grafana ajouté à `mssante-mail-processing.json`
- [ ] `FlexibleEmbeddingService`, `IEmbeddingProviderService`, `BaseEmbeddingProviderService` et implémentations supprimés, tests ajustés
- [ ] Documentation d'exploitation écrite ; `loadtest-skill` mis à jour pour le défaut hybride
- [ ] Aucune donnée de santé ni contenu de mail dans les nouveaux logs et métriques (étiquettes `provider`, `model`, `kind` uniquement)
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché, prompts inchangés, espace vectoriel inchangé
- [ ] Le body de la PR cite les chiffres Prometheus du 2026-09-20 (1 270 758 requêtes / 15 536 en 429 sur 15 j), la part du chat dans la facture, et l'objectif « 0 token de chat chez OpenAI à la campagne suivante »

## Manual Test Plan

- **Prérequis** : Docker Desktop avec intégration GPU active (`docker run --rm --gpus=all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi` affiche la RTX 5070 Ti). La clé OpenAI reste en place (embeddings).
- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` (avec les comptes seedés du banc : `MSS_TENANT_REGISTRY_DB=mss_registry_loadtest`, sinon 403 `MAILBOX_NOT_ATTACHED` partout). Dans le tableau de bord Aspire, la ressource Ollama passe en « Running » ; au premier lancement, les journaux montrent le téléchargement du modèle de chat (plusieurs minutes, une seule fois grâce au volume). `api-mail` démarre **après** et journalise `Chat=Ollama/{modèle}`, `Embedding=OpenAI/text-embedding-3-small (1536)`.
- **Pipeline** : seeder une boîte (`loadtest-skill`, quelques mails suffisent). Dans Seq (`seq-local`) : `[SuggestTagsAsync]` avec `provider=Ollama`, tags persistés ; dans Postgres (`mcp postgresql`) : ligne d'embedding du mail avec `EmbeddingModel = openai:text-embedding-3-small`. `nvidia-smi` montre le processus Ollama avec de la VRAM occupée pendant le tagging.
- **Recherche inchangée** : sur une base déjà hydratée (pas de purge — iso-conditions), lancer la même recherche sémantique avant et après la branche → mêmes résultats, même ordre.
- **Assistant** : ouvrir l'assistant sur la boîte, demander « propose une réponse à ce mail » → réponse en streaming, puis « appelle le patient » → l'action `call_patient` est capturée (log `[AiConversationService] Action captured from filter`).
- **Aide à la rédaction** : améliorer un texte depuis le composeur → texte réécrit.
- **Fournisseur invalide** : `AiProvider__Chat=OpenIA` → `api-mail` refuse de démarrer avec un message explicite dans Aspire. `AiProvider__Provider=Ollama` seul (ancienne clé) → même refus.
- **Tout-OpenAI** : `AiProvider__Chat=OpenAI` + clé → démarrage normal, tagging avec `provider=OpenAI`. **Tout-Ollama** sans clé → démarrage normal (l'embedding Ollama produit alors des lignes `ollama:bge-m3`, invisibles à la recherche filtrée sur le modèle actif OpenAI si on rebascule — c'est le comportement voulu).
- **Grafana** (`localhost:3000`, tableau mail processing) : le panneau IA montre des tokens `prompt`/`completion` uniquement sous `provider=Ollama`, des tokens `embedding` sous `provider=OpenAI`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — infrastructure des traitements IA, aucune exigence fonctionnelle nouvelle
- **Exigences DSR honorées** : non applicable — les fonctions IA (résumé, tags, recherche, assistant) sont hors référentiel Ségur ; aucun changement de leur périmètre fonctionnel
- **INS** : non applicable — aucun trait d'identité manipulé par l'US ; les contenus de mails soumis au chat peuvent contenir des traits patient, et c'est ce qui **cesse de quitter le poste** pour cette capacité
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées — les traitements IA restent exécutés dans le contexte du praticien connecté
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : événements techniques au démarrage (fournisseurs, modèles, dimension), compteurs de tokens par fournisseur, colonne `EmbeddingModel` en base (donnée technique, pas personnelle) ; aucun contenu de prompt ni de mail dans journaux et étiquettes. Conservation : celle de Seq / Prometheus existante
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — **amélioration partielle** : les contenus de mails (potentiellement DSCP) ne sont plus transmis à un sous-traitant hors périmètre HDS pour étiquetage, résumé et assistant ; ils le **restent pour la vectorisation** (embeddings OpenAI) jusqu'à task-326. Le modèle de chat et ses données transitoires vivent dans un volume Docker du poste (développement et banc, données synthétiques)
- **AIPD / impact RGPD** : **à mettre à jour** — OpenAI reste sous-traitant pour la vectorisation des contenus, ne l'est plus pour le chat en développement et au banc ; l'usage en production, s'il existe, reste à qualifier (fournisseur, localisation, clauses) dans une US de la même EPIC

## Branches
- `api-mail` (pushed) : feat/task-325-ia-locale-ollama — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-325-ia-locale-ollama (depuis `origin/develop` @ `a9ebaa50`)
- `dtos-mss` : aucune branche à `/start` (branche paresseuse, créée par `/develop` seulement si un contrat change)

## Develop log

**Repos touchés** : `api-mail` seul. **Aucun contrat modifié** : pas de `Dtos/`, pas de frontend, prompts inchangés ; donc aucune branche `dtos-mss` et aucune publication NuGet.

**Commits** (`feat/task-325-ia-locale-ollama`, poussée) :
- `4bb159bd` feat(ai) : un fournisseur IA par capacité, chat Ollama GPU et embeddings OpenAI
- `4380ee62` refactor(ai) : passe qualité `/simplify`
- `efdbb2bd` fix(ai) : 409 aussi sur la recherche par patient ; tirage des seuls modèles utiles
- `64a7b876` test(arch) : les scans d'architecture voient les fichiers pas encore ajoutés

**Preuves du rouge** :
- *Caractérisation.* `AiProviderStartupValidationTests` a d'abord échoué (« No exception was thrown ») : `OpenIA` sélectionnait OpenAI sans rien dire.
- *Mutations*, restaurées par `cp` puis rebuild (mémoire mtime) :
  - retirer le filtre du modèle actif fait passer `SemanticSearchEmbeddingModelTests` au rouge (les lignes d'un autre modèle remontent) ;
  - retirer le mappage de dimension fait passer au rouge le test 409 (une `PostgresException` brute remonte).
- *Garde d'architecture.* Un fichier de test non suivi qui capture des mesures sans collection fait échouer `MetricCaptureSerialisationScanTests` depuis `64a7b876`. Avant ce commit, il passait.

**Audit règle 7c (FluentMigrator, pas EF)** : migration `20260930180000_AddEmbeddingModelColumns` :
- Fichier lu : deux `ALTER TABLE … ADD "EmbeddingModel" varchar(128) NULL`, puis un `UPDATE … WHERE "Embedding" IS NOT NULL`. `Down` supprime les deux colonnes.
- Aucune opération fantôme.
- Pas de `.Designer.cs` ni de snapshot : FluentMigrator n'en a pas.
- Il n'existe pas de « pending model changes » ; ce contrôle est remplacé par `AddEmbeddingModelColumnsMigrationTests`, qui prouve le schéma et le rétro-remplissage sur un vrai Postgres.

**Passe qualité §Q** (4 revues : reuse, simplification, efficacité, altitude) :
- *Appliqué* :
  - le prédicat du modèle actif, recopié 13 fois, est ramené à deux racines de requête ;
  - un seul `ServiceOf<T>` pour les 4 connecteurs ;
  - le modèle de chat se lit en un seul endroit (`ChatModelOf`), le modèle d'embedding vient de `ActiveEmbeddingModel` ;
  - la borne d'embedding lit le fournisseur comme la sélection ;
  - le drapeau e2e est porté par le profil AppHost, et le doublon d'environnement e2e est retiré ;
  - un commentaire pointait vers un membre inexistant ; il est corrigé.
- *Écarts au DOD relevés et corrigés*, commit séparé `efdbb2bd` :
  - la recherche par patient masquait le 409 ;
  - `bge-m3` n'était jamais tiré en embeddings Ollama.
- *Écarté, noté* :
  - le filtre nul du constructeur de test de `SemanticSearchRepository` : le rendre obligatoire touche environ 28 appels de tests hérités ;
  - les requêtes de débogage `CountAsync` et les distances d'échantillon, déjà présentes dans `SemanticSearchRepository` ;
  - le helper de pas `RecordStep` du consumer ;
  - la copie de `TestAiProviders` dans les tests d'intégration (projets distincts).
- *Re-validation* : build à 0 erreur ; tests à 0 échec (domain 190, infrastructure 677, api 1148, application 3271, integration 673 dont 16 ignorés, les cas d'usage IA réels).

**Leçon capturée (règle d'or)** : `TrackedSourceScan` ne listait que les fichiers suivis.
- Deux nouvelles captures de mesures non sérialisées sont donc passées sous une suite verte. Elles n'étaient pas encore commitées au moment de la validation.
- Prévention : `git ls-files --cached --others --exclude-standard`, avec un rouge prouvé.

**Reste pour la HAG** (non automatisable ici) :
- démarrage de l'AppHost avec GPU, et `ollama list` ;
- parcours bout en bout avec identifiants Seq : étiquetage `provider=Ollama`, ligne `EmbeddingModel = openai:text-embedding-3-small` ;
- mêmes résultats de recherche qu'avant la branche ;
- assistant en streaming avec au moins un outil, et aide à la rédaction ;
- lecture du panneau Grafana.

**Taille** : la PR dépasse les ~30 fichiers de la règle 5. La suppression du code mort (§ 10) et l'adaptation mécanique des tests à la nouvelle signature des métriques en portent l'essentiel.

**Suite** : `/sonar task-325`.

## Sonar log

Serveur SonarQube 9.9.8.100196 (`sonar.login`). Le new code couvre 30 jours : il inclut du code d'autres tasks.

- **Phase 1 (new code)** : Quality Gate OK, `new_coverage` = 97,6 % (cible 95 %).
- **Phase 1, issues corrigées** : 3 code smells (0 bug, 0 vulnérabilité, 0 hotspot), commit `0f02113b` :
  - S3267 dans `AiProviderSelection` : écrit par la passe `/simplify`, c'est une récidive consignée ;
  - S3604 ×2 dans `ImapService` et `OfflineMailDataProvider` (code de task-342).
- **Phase 1, tests ajoutés** : aucun, la couverture du new code était déjà au-dessus de la cible.
- **Test rouge trouvé par la passe Release** : `AiDiagnosticsControllerIntegrationTests` échouait avec `different vector dimensions 3 and 1536`.
  - Cause : `SemanticSearchEmbeddingModelTests` (task-325) laissait ses vecteurs de 3 et 5 dimensions dans le conteneur partagé.
  - Le résultat dépendait de l'ordre des tests : vert en Debug, rouge en Release.
  - Correctif : nettoyage en `DisposeAsync`, commit `5eb86769`. Rouge deux fois sur deux avant, vert après (673 tests passés).
- **Phase 2 (legacy)** : non lancée. Les cibles projet sont déjà atteintes (0 bug, 0 vulnérabilité, notes A, couverture ≥ 95 %). Restent 8 code smells legacy.
- **Build / tests** : verts. La seconde analyse a rejoué les 5 projets en Release avec couverture, 0 échec.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98,1 % | 97,6 % | −0,5 pt |
| New code smells | 2 | 0 | −2 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 10 | 8 | −2 |
| Coverage (projet) | 98,2 % | 98,1 % | −0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

**Conventions** (`conventions/csharp.md`) :
- S3267 passe à 3 occurrences (récidive dans le code de la passe qualité) ;
- S3604 passe à 3 occurrences (repli d'horloge de task-342) ;
- nouvelle entrée `collection-postgresql-partagee`.

**Playbook** : le §Q de `agents/develop.md` impose désormais de relire les conventions avant d'appliquer les nettoyages de la passe.

## Timings

*(généré par `tools/timing/report.sh --task task-325 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 58 min 35 s | 11 (55 s) | 12 (10 min 09 s) | — | api-mail 11B/12T |
| /sonar | ok | 24 min 09 s | 5 (1 min 01 s) | 10 (9 min 31 s) | 4 (1 min 19 s) | 2 itération(s), api-mail 5B/10T |
| /lint-angular | skipped | 11 s | — | — | — | no angular change (WIP humain antérieur ignoré) |
| /lint-mobile | skipped | 0.5 s | — | — | — | no mobile change |
| /e2e | ok | 1 h 26 min | — | — | — | e2e ×3 (6 min 30 s) |
| /review | ok | 17 min 19 s | 2 (11 s) | 2 (5 min 08 s) | — | api-mail 2B/2T |
| /tech-writer | ok | 2 min 02 s | — | — | — | — |
| **Total cycle** | | **3 h 09 min** | **18 (2 min 08 s)** | **24 (24 min 50 s)** | **4 (1 min 19 s)** | |

## Lint log
- `/lint-angular` : skipped — no angular change. `client-angular` absent des `**Repos**`, aucun fichier Angular écrit par `/develop` ; les 7 fichiers non commités de `Client/Angular/front` sont du WIP humain antérieur à la task, laissé intact.

## Lint mobile log
- skipped — no mobile change : `client-mobile` absent des `**Repos**`, aucun commit sur `Client/Mobile` pour la task.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 24 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 24 s |
| angular | api-mail touché | ✅ verte | 24 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 7 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-325-ia-locale-ollama`)
- Backend e2e : construit depuis la branche de la task. Le profil e2e force `AiProvider__Chat=Ollama` et `AiProvider__Embedding=Ollama` vers le faux fournisseur ; E2E-AI-001 et E2E-LIVE-001 sont verts sur les deux clients.
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun frontend touché)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- Incident d'outillage évité : le port 4200 était tenu par le `nx serve` de l'humain, sur `[::1]` seul. L'humain l'a arrêté avant la voie Angular. Le garde de l'orchestrateur ne sonde que l'IPv4 (`conventions/e2e.md`, `garde-de-port-ipv4-seul`) ; son correctif reste à faire sur `client-angular`.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/265 (label `awaiting-human-merge`)
- `dtos-mss` : aucune branche, aucun contrat modifié
- Aucun frontend touché

## Code Review Summary

**APPROVED**, après correction d'un point bloquant (73 fichiers revus, 6 suggestions, 0 bloquant restant).

- **Bloquant, corrigé** (`89b34656`) : `appsettings.json` portait le défaut hybride. Prod et Staging, dont les configmaps ne posent aucun `AiProvider__*`, auraient envoyé le chat vers un Ollama `127.0.0.1` inexistant, sans échec au démarrage.
  - Décision de l'humain : `appsettings.json` est tout-OpenAI, le défaut hybride est celui de l'AppHost.
  - Garde : `EmbeddingOptionsConsistencyTests`, prouvé rouge.
  - Le DOD « Défauts livrés : Chat = Ollama » s'entend donc **sous l'AppHost**.
- **Suggestions** (non bloquantes, reportées dans la PR) :
  - `ollama pull` à chaque démarrage bloque l'API hors ligne ;
  - backfill `openai:` sur d'éventuelles bases e2e persistantes ;
  - `AiDiagnosticsController` sans filtre de modèle (500 attendu après task-326) ;
  - dimension déclarée jamais vérifiée ;
  - `Arg.Any<string>()` sur l'identifiant de modèle dans deux fichiers de tests ;
  - comptage des tokens en streaming non prouvé contre le connecteur Ollama réel.
- **Validation** : build à 0 erreur ; tests à 0 échec (domain 190, infrastructure 677, api 1148, application 3272, integration 673 dont 16 ignorés) ; e2e vert sur les deux voies ; Sonar QG OK.
- **DOD**, points vérifiés par commande :
  - `OpenAIPromptExecutionSettings` absent ;
  - aucun `Dtos/`, frontend ni prompt modifié ;
  - code mort supprimé ;
  - deux clients HTTP nommés ;
  - panneau Grafana présent, JSON valide ;
  - doc et `loadtest-skill` à jour ;
  - chiffres Prometheus dans la PR.
- **DOD, points observationnels renvoyés à la HAG** : démarrage GPU et `ollama list` ; parcours bout en bout avec identifiants Seq ; recherche identique ; assistant et aide à la rédaction ; Grafana.
