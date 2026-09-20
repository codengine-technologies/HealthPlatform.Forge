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
10. **Code mort retiré** : `FlexibleEmbeddingService`, `IEmbeddingProviderService` et ses deux implémentations sont **supprimés**. La dimension et le nom du modèle actif ne sont déclarés qu'à un seul endroit (§ 7-8). Leurs tests suivent.
11. **Documentation d'exploitation** : page `Api/Mail/docs/` (ou section du README de l'AppHost) : choisir un fournisseur par capacité, modèles tirés, volume, retour au tout-OpenAI, ce qu'implique un changement de modèle d'embedding et le rôle de la colonne `EmbeddingModel`. Le skill `loadtest-skill` est mis à jour pour le défaut hybride.

### Décisions prises par le PO, à contredire si besoin

- **Hybride par défaut** (chat Ollama, embeddings OpenAI), en développement comme au banc. Motifs : le chat est la part dominante de la facture et la totalité de la donnée de santé « discutée » ; les embeddings sont bon marché et leur bascule casserait le corpus du banc. Le tout-OpenAI reste possible par deux variables d'environnement.
- **Les embeddings restent chez OpenAI pour l'instant, en connaissance de cause** : les 429 sous charge et la recherche rouge du banc restent attribuables à ce fournisseur tant que task-326 (re-vectorisation) n'est pas livrée. Cette US pose la colonne modèle qui rend cette bascule sûre.
- **Qualité non certifiée par cette US.** Un modèle 14B en Q4 étiquette et résume moins bien que `gpt-4o-mini`, et suit moins strictement le JSON. Cette US exige que le pipeline **fonctionne** (JSON parsé, assistant qui appelle un outil) ; la **mesure d'écart de qualité** sur un jeu de mails de référence est une US séparée de la même EPIC.

### Hors périmètre, explicitement

- **task-326 — re-vectorisation** : batch qui relit mails et documents et réécrit les vecteurs avec le modèle actif, base par base, puis bascule `AiProvider:Embedding = Ollama`. À rédiger ; dépend de la colonne `EmbeddingModel` posée ici.
- **vLLM / TEI / LiteLLM** : débit et routage. Le § 3 les rend possibles sans code.
- **Banc de qualité** tagging / résumé / assistant, modèle local vs `gpt-4o-mini`.
- Tout changement des prompts, des flags Flagsmith, de `Dtos/`, des frontends.
- Le circuit partagé chat / embeddings et le `429 insufficient_quota` : le circuit n'a plus qu'un locataire (les embeddings) après cette US ; à instruire dans task-326 si la voie OpenAI subsiste.

### Mesure — après, sur la campagne suivante

Sur la prochaine campagne `terrain` (celle de task-323 ou toute autre) en défaut hybride : `mssante_ai_tokens_total{provider="OpenAI", kind=~"prompt|completion"}` **= 0** et `{provider="Ollama", kind=~"prompt|completion"}` **> 0** ; requêtes vers `api.openai.com` dans `http_client_request_duration_seconds_count` en **baisse d'au moins moitié** par rapport aux 15 jours de référence (il ne reste que les embeddings de pipeline et de recherche) ; `mssante_ai_pipeline_total{step="tagging", status="success"}` en proportion **≥** à la campagne du 19/09 ; utilisation GPU visible (`nvidia-smi`) pendant le tir ; **résultats de recherche identiques** avant/après sur une même requête et une même base (le corpus n'a pas bougé). La durée du tagging (2,0 s aujourd'hui) est **relevée, pas exigée** : un 14B sur un seul GPU peut être plus lent sous 1 000 praticiens ; c'est la donnée d'entrée de la US vLLM.

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
- [ ] `FlexibleEmbeddingService`, `IEmbeddingProviderService` et implémentations supprimés, tests ajustés
- [ ] Documentation d'exploitation écrite ; `loadtest-skill` mis à jour pour le défaut hybride
- [ ] Aucune donnée de santé ni contenu de mail dans les nouveaux logs et métriques (étiquettes `provider`, `model`, `kind` uniquement)
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché, prompts inchangés, espace vectoriel inchangé
- [ ] Le body de la PR cite les chiffres Prometheus du 2026-09-20 (1 270 758 requêtes / 15 536 en 429 sur 15 j), la part du chat dans la facture, et l'objectif « 0 token de chat chez OpenAI à la campagne suivante »

## Manual Test Plan

- **Prérequis** : Docker Desktop avec intégration GPU active (`docker run --rm --gpus=all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi` affiche la RTX 5070 Ti). La clé OpenAI reste en place (embeddings).
- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`. Dans le tableau de bord Aspire, la ressource Ollama passe en « Running » ; au premier lancement, les journaux montrent le téléchargement du modèle de chat (plusieurs minutes, une seule fois grâce au volume). `api-mail` démarre **après** et journalise `Chat=Ollama/{modèle}`, `Embedding=OpenAI/text-embedding-3-small (1536)`.
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
