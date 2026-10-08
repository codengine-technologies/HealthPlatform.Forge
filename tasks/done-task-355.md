# todo-task-355.md — L'étiquetage IA local tient la charge du terrain 1000 : Ollama traite plusieurs étiquetages à la fois, et le gabarit garde sa grille constante en tête pour profiter du cache de préfixe

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E017
**Priorité**: **2** — à traiter avant tout palier au-delà de 1000 praticiens inscrits en mode hybride. Aujourd'hui, la réserve de l'IA locale est **nulle**.

> **Origine.** Campagne de charge du 2026-10-07/08 (`Docs/audits/api-mail-loadtest-terrain-1000-ollama-ab-20261008.md`,
> défaut D1) puis micro-banc ciblé du 2026-10-08 (`Docs/audits/ollama-bench-20261008/`).
>
> - En défaut hybride (task-325), le chat tourne sur Ollama (`qwen2.5:14b`, RTX 5070 Ti 16 Go) avec
>   `OLLAMA_NUM_PARALLEL=1`, valeur par défaut que l'AppHost ne pose pas. Ollama étiquette **40 à 45 mails
>   par minute** ; il en arrive **~44 par minute** au terrain 1000. La plateforme tient, mais sans marge :
>   61 s d'attente moyenne par étiquetage, 42 timeouts à 180 s sur 3 h. Après une chauffe, la file
>   `add-new-mail-queue` atteint 94 000 messages, soit ~35 h de vidage. Les embeddings sont bridés de la
>   même façon, puisque le consommateur attend les deux.
> - **Le parallélisme seul ne suffit pas.** Micro-banc avec le gabarit réel, prompts de 2 548 tokens et
>   50 demandes simultanées : P=1 → 40,8/min, P=2 → 45,6, P=4 → 45,6, P=6 → 49,2, mais avec 15,2 Go de
>   VRAM sur 16, trop juste. Le goulet est le **calcul du prompt** (~2 550 tokens par mail).
> - **Cause trouvée dans le gabarit.** `TaggingPromptTemplate` (`EmailTaggingService`) place le bloc
>   « Contexte » (type de document, expéditeur) **avant** la grille de priorités (~1 000 tokens
>   identiques d'un mail à l'autre). La partie variable en tête empêche Ollama de réutiliser le calcul
>   déjà fait sur la grille (cache de préfixe).
> - **Bloc « Contexte » déplacé après la grille**, même micro-banc : P=1 → **51,7/min**, P=2 → **65,3**,
>   P=4 → **76,4** (+87 %, attente p50 36 s, VRAM 13,6 Go). Le calcul du prompt est divisé par deux
>   (0,71 → 0,37 s).

## Objective

Donner de la marge à l'étiquetage IA local au terrain 1000, par deux changements mesurés ensemble :

1. **Ollama traite plusieurs étiquetages à la fois.** L'AppHost pose `OLLAMA_NUM_PARALLEL` sur le
   conteneur `mss-mail-ollama`, avec une valeur par défaut de **4**. La valeur est surchargeable par
   `MSS_OLLAMA_NUM_PARALLEL` et validée au démarrage par `AiProviderProfile`, comme le modèle de chat.
2. **Le gabarit d'étiquetage commence par sa partie constante.** Introduction et grille de priorités
   d'abord ; type de document, expéditeur et contenu ensuite. Le texte de la grille et les consignes
   ne changent pas : seul l'ordre change.

**Single layer, justifié :** l'US ne touche que l'AppHost et un service applicatif d'api-mail. Aucun
écran, aucun contrat, aucun parcours médecin n'est modifié. Le médecin ne voit qu'un effet : son mail
est étiqueté plus vite. Pas de frontend, pas de scénario e2e : les parcours existants sont rejoués par
`/e2e` comme d'habitude.

**Effet attendu aussi en production (tout-OpenAI) :** OpenAI applique un cache de prompt aux préfixes
identiques d'au moins 1 024 tokens. Le nouvel ordre le rend applicable à la grille, ce qui devrait
réduire le coût d'entrée de l'étiquetage. **Non mesuré**, ce n'est pas un critère de cette US.

## Règles métier

- **Pas de changement de sens.** Les trois niveaux (Très urgent, Urgent, Important), leurs critères et
  la consigne de réponse JSON restent identiques, au mot près. Seul l'ordre des blocs bouge.
- **Garde qualité, bloquante (décision du responsable produit, 2026-10-08).** Sur un échantillon de
  mails synthétiques du banc, étiquetés avec l'ancien puis le nouveau gabarit (`qwen2.5:14b`) :
  - au moins **95 % de concordance** (même étiquette, ou même absence d'étiquette) ;
  - un taux de réponses illisibles qui n'augmente pas.

  Si la garde échoue, l'US ne livre pas le nouveau gabarit : elle s'arrête en `questions/task-355.md`.
- **Valeur invalide = refus de démarrer.** `MSS_OLLAMA_NUM_PARALLEL` hors de 1..8, ou non entier :
  l'AppHost refuse de démarrer, avec un message qui dit quoi écrire. Jamais de repli silencieux
  (même principe que task-325).
- **Aucune donnée de santé dans les journaux** : ni le prompt rendu, ni le contenu, ni l'expéditeur.
  C'est déjà le cas aujourd'hui (task-265, task-341), et la règle ne doit pas régresser.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] `AiProviderProfile` expose le parallélisme Ollama : défaut **4** ; `MSS_OLLAMA_NUM_PARALLEL` lu ; valeur non entière, ≤ 0 ou > 8 → `InvalidOperationException` au démarrage avec un message actionnable. Tests unitaires : défaut, surcharge valide, trois cas invalides.
- [ ] L'AppHost pose `OLLAMA_NUM_PARALLEL` sur `mss-mail-ollama` avec la valeur du profil. Test unitaire ou de modèle d'application qui lit la variable sur la ressource.
- [ ] **Conteneur persistant recréé** quand la valeur change : vérifié en lançant l'AppHost avec `MSS_OLLAMA_NUM_PARALLEL=2` puis 4, et en lisant `OLLAMA_NUM_PARALLEL` dans `docker logs mss-mail-ollama-*` (ligne de configuration du serveur). Constat consigné dans le `## Develop log`. Si Aspire ne recrée pas le conteneur, le dire et documenter le geste dans `docs/ia-fournisseurs.md`.
- [ ] `TaggingPromptTemplate` réordonné : introduction et grille d'abord ; `## Contexte` (type, expéditeur) puis `## Contenu du document` en fin. Texte de la grille inchangé.
- [ ] **Test de convention, vu rouge sur l'ancien gabarit** : deux mails de type, d'expéditeur et de contenu différents rendent deux prompts qui partagent un **préfixe identique** couvrant toute la grille de priorités. Rouge prouvé sur l'ancien ordre (preuve par mutation consignée dans le `## Develop log`).
- [ ] Tests existants d'étiquetage verts sans affaiblissement : `PromptTemplateInjectionTests` (les variables restent des arguments, jamais du gabarit), `EmailTaggingCaseInsensitiveTests`, `TaggingInvalidResponseLogHygieneTests`.
- [ ] **Garde qualité ≥ 95 % de concordance**, mesurée sur au moins 200 mails synthétiques du corpus du banc (`JEUX_TESTS_FULL`), ancien contre nouveau gabarit, `qwen2.5:14b` local. Taux de réponses illisibles non dégradé. Script et résultat consignés dans le `## Develop log` (aucun contenu de mail dans le journal, seulement les comptes).
- [ ] **Débit mesuré** : micro-banc `Docs/audits/ollama-bench-20261008/bench.py` rejoué avec le gabarit livré à P=4 → **≥ 70 étiquetages/min**, VRAM ≤ 14 Go. Résultat consigné dans le `## Develop log`.
- [ ] Aucune donnée de santé en clair dans les logs (prompt, contenu, expéditeur) — inchangé, vérifié par les tests d'hygiène existants.
- [ ] `docs/ia-fournisseurs.md` : section « Ollama dans l'AppHost » complétée (parallélisme, surcharge, VRAM mesurée, recréation du conteneur) et note sur l'ordre du gabarit (cache de préfixe).
- [ ] Test d'intégration de bout en bout (règle 1b) : **non applicable** — aucun comportement atteignable par un endpoint ne change. L'étiquetage n'est déclenché que depuis le bus (`AddNewMailConsumer`, reprise task-344), aucune route ne l'expose (vérifié : `AiDiagnosticsController` n'a pas de route d'étiquetage), et les étiquettes produites restent les mêmes (garde qualité).

## Manual Test Plan

1. **Démarrage du banc hybride** (depuis `Api/Mail`) :
   `MSS_TENANT_REGISTRY_DB=mss_registry_loadtest dotnet run --project src/AppHost --launch-profile https-load-test`
2. **Parallélisme effectif** : `docker logs mss-mail-ollama-<suffixe> 2>&1 | grep -o "OLLAMA_NUM_PARALLEL:[0-9]*"` doit afficher **4**.
3. **Surcharge** : arrêter l'AppHost, relancer avec `MSS_OLLAMA_NUM_PARALLEL=2` et refaire le point 2 : **2** attendu.
4. **Refus** : relancer avec `MSS_OLLAMA_NUM_PARALLEL=0`, puis `abc`. L'AppHost refuse de démarrer, avec un message qui cite la variable et les valeurs admises.
5. **Débit** : AppHost arrêté et conteneur `mss-mail-ollama` stoppé (pour libérer la VRAM), lancer
   `Docs/audits/ollama-bench-20261008/run-all.sh` avec `VALUES="4"` et le gabarit livré :
   **≥ 70/min** attendu (contre 40,8 avant).
6. **Étiquettes visibles** : ouvrir le client sur une boîte du banc après une synchronisation. Les mails
   portent les étiquettes Très urgent / Urgent / Important comme avant (pas de mail sans étiquette en
   masse).
7. Optionnel, si le banc est disponible : rejouer le tir A de la campagne
   (`terrain-1000`, tireur k6bench, mêmes paramètres). La section « IA » du rapport doit montrer une
   attente d'étiquetage nettement inférieure à 61 s et une file `add-new-mail-queue` qui ne grossit pas.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — réglage de capacité du traitement IA interne, sans échange ni fonctionnalité Ségur.
- **Vague Ségur** : hors Ségur — même raison.
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur l'étiquetage IA de priorité.
- **INS** : non applicable — l'étiquetage ne manipule pas l'identité patient.
- **Authentification PS** : non applicable — traitement de plateforme, sans geste du praticien. Inchangé.
- **Habilitations** : non applicable — inchangées.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR modifié. Le gabarit lit le contenu déjà extrait.
- **Tracé PGSSI-S** : inchangé — aucun nouvel évènement. Les métriques `mssante_ai_*` existantes suffisent.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : **non concerné par le changement** — Ollama ne tourne que sous l'AppHost (développement, banc) sur données synthétiques. La production reste en tout-OpenAI (`appsettings.json`, task-325), et le passage de la production en local reste une décision à qualifier (HDS, AIPD) hors de cette US.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, aucun nouveau destinataire. L'ordre du prompt ne change pas les données envoyées.

## Branches
- `api-mail` (pushed) : feat/task-355-ollama-parallele-gabarit-prefixe — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-355-ollama-parallele-gabarit-prefixe

## Arbitrage humain (2026-10-08) — option A : le parallélisme seul

Réponse du responsable produit à `questions/task-355.md` : **A**. La garde qualité a échoué :
89,5 à 94 % de concordance, et le nouvel ordre étiquetait moins (13 descentes, 0 montée à
température 0). **L'US ne livre donc pas le nouveau gabarit**, conformément à sa règle métier.

Conséquences sur la DOD, qui reste inchangée (propriété du PO) :
- **Non livrés par arbitrage** : le gabarit réordonné, son test de convention et la note sur l'ordre
  du gabarit. `EmailTaggingService.cs` est identique à `develop`, et `TaggingPromptPrefixTests` est
  retiré. La garde a été jouée : son résultat est la raison du retrait.
- **Débit ≥ 70/min : non atteignable sans le gabarit.** Valeur livrée à P=4 : **45,6/min**, contre
  40,8 à P=1, pour 13,6 Go de VRAM. Le point 5 du Manual Test Plan attend donc ~45/min, et non
  ≥ 70. La réserve de l'IA locale au terrain 1000 reste quasi nulle.
- **Livrés** : parallélisme (défaut 4, surcharge validée, refus de démarrer), variable posée sur le
  conteneur, recréation du conteneur constatée, documentation. La doc dit pourquoi le gabarit
  n'a pas été réordonné.

## Develop log

> **Arrêt sur la garde qualité, règle métier de la task.** Le nouveau gabarit concorde à
> **89,5 à 94,0 %** avec l'ancien, pour **95 %** exigés, et l'écart va dans un seul sens : il
> étiquette **moins**. Arbitrage demandé dans `questions/task-355.md`. Tout le reste de la DOD est
> traité.

- Repos touched : api-mail (branche poussée, 4 commits). Aucun DTO, aucun interop, aucun SDK.
- Commits (api-mail) :
  - `5a4b77dd` feat(apphost) : `OLLAMA_NUM_PARALLEL=4`, surcharge `MSS_OLLAMA_NUM_PARALLEL` (1..8)
  - `75e214c3` feat(ai) : gabarit d'étiquetage, grille constante en tête
  - `8e76759e` refactor(apphost) : passe qualité /simplify
  - `9a72ff6e` docs(ai) : `docs/ia-fournisseurs.md`
- Local build / test : ✓ 0 erreur. Suite complète 6 440 réussis, 16 ignorés, 0 échec (domain 190,
  infrastructure 683, application 3 554, api 1 183, integration 830 + 16). Mêmes totaux avant et
  après la passe qualité, donc aucun crash masqué.
- Passe qualité (/simplify), appliquée et commitée (`8e76759e`), re-validation verte :
  - la propriété `OllamaServerEnvironment` est retirée ; l'AppHost pose les deux variables en appels
    chaînés, et le profil n'expose que l'entier ;
  - le préfixe commun se calcule par `MemoryExtensions.CommonPrefixLength` au lieu d'une boucle ;
  - les commentaires de classe des tests sont raccourcis.
  - Écartés : un `BuildKernel` de test partagé (4 lignes, il aurait fallu toucher 4 autres
    fichiers) ; le même ordre « constante d'abord » pour le résumé (`AiPromptHelper` :
    `ALL + typePrompt + DONOT`). Le résumé est à la demande, pas par mail : hors périmètre.
  - Contrôles mécaniques (S125, xUnit1045, S4457, xUnit2032, S103) : aucun résultat.
- **Tests et preuves par mutation** :
  - `TaggingPromptPrefixTests` (2 tests) : **rouges sur l'ancien ordre**, le vrai code d'avant
    le correctif, sur l'assertion prévue (`Assert.Contains` de la grille dans le préfixe commun) ;
    verts après.
  - `AiProviderProfileTests`, 10 cas nouveaux : défaut 4 ; surcharges 1, 2 et « 8 » ; valeur
    vide = défaut ; refus de `abc`, `2.5`, `-1`, `0` et `9`, message cité.
    - Mutation « variable ignorée » : 8 rouges.
    - Mutation « bornes retirées » : seuls `0` et `9` rougissent. Chaque règle de refus a donc
      son cas propre (consigne test-de-rejet-attribuable).
  - `OllamaServerEnvironmentWiringTests` (lecture de la source de l'AppHost) : rouge quand la
    ligne `WithEnvironment("OLLAMA_NUM_PARALLEL", …)` est retirée. Preuve refaite après la passe
    qualité, puisque l'assertion avait changé.
  - Tests existants verts sans changement : `PromptTemplateInjectionTests`,
    `EmailTaggingCaseInsensitiveTests`, `TaggingInvalidResponseLogHygieneTests`,
    `TaggingFailureIsCountedTests`, `PromptInvocationShapeTests` (61 tests d'étiquetage).
- **Conteneur persistant recréé : ✓.** AppHost lancé avec `MSS_OLLAMA_NUM_PARALLEL=2` :
  `mss-mail-ollama-b6152948`, créé le 2026-10-07 18:24, est recréé le 2026-10-08 à 14:14:45, et
  `docker logs` affiche `OLLAMA_NUM_PARALLEL:2`. Relancé sans la variable, il est recréé à
  14:16:09, avec `OLLAMA_NUM_PARALLEL:4`. Aucun geste manuel. Refus de démarrer vérifié aussi en
  vrai : `0` et `abc` donnent « MSS_OLLAMA_NUM_PARALLEL invalide : « 0 ». Écrire un entier de 1 à 8
  (…), ou retirer la variable pour le défaut 4. »
- **Débit : ✓.** `run-all.sh`, `VALUES="4"`, `TPL=template-livre.txt` (régénéré depuis le code
  livré) : **79,3 étiquetages/min**, attente p50 35,5 s, calcul du prompt 0,52 s, 0 erreur, JSON
  lisible à 100 %. VRAM totale de la carte : 13 920 MiB, soit 13,6 Gio, affichage du poste compris
  (≤ 14 Go). Pour mémoire, P=4 avec l'ancien gabarit : 45,6/min.
- **Garde qualité : ✗ — sous le seuil.** Script `Docs/audits/ollama-bench-20261008/guard.py`,
  résultats `results-guard.txt` et `results-guard-2.txt`, comptes uniquement.
  - **Corpus** : 200 entrées de `JEUX_TESTS_FULL`. Le corpus ne contient que **125 documents CDA
    distincts** porteurs de texte narratif, XML et ZIP IHE_XDM confondus. Le reste est fait de
    8 suites de documents longs (au-delà des 5 000 caractères lus) et de 67 extraits « seconde
    moitié des sections » : 200 contenus distincts, tous cliniques. Le corps des mails du banc
    (`LoadTestPlanGenerator`) est du lorem ipsum et ne déclencherait aucune étiquette : il est
    écarté, la garde serait un vert qui ment.
  - **Conditions** : `qwen2.5:14b` sur le conteneur de banc à P=4, gabarits reconstruits depuis
    les littéraux C# (ancien : `origin/develop`). Options par défaut du serveur, comme en
    production, plus des passes à température 0 et graine fixe.
  - **Concordance** (même étiquette ou même absence d'étiquette) :

    | Comparaison | Paires | Concordance | Sens des écarts |
    |---|---|---|---|
    | ancien contre ancien rejoué (bruit) | 7 | 92,5 à 96,0 % (moy. ≈ 93,9) | équilibré |
    | nouveau contre nouveau rejoué (bruit) | 3 | 91,5 à 95,0 % | équilibré |
    | **ancien contre nouveau** | 14 | **89,5 à 94,0 % (moy. ≈ 91,9)** | **descentes ≫ montées** |
    | ancien contre nouveau, température 0 | 2 | 93,5 % | **13 descentes, 0 montée**, deux fois |

  - **Répartition** :
    - étiquettes posées : ancien 39 à 41 sur 200, nouveau 31 à 37 ;
    - « Urgent » : ancien 20 à 24, nouveau 15 à 17.
  - **Réponses illisibles** : 0 ou 1 par passe, des deux côtés. Non dégradé.
  - Lecture : le bruit du modèle à lui seul est déjà au niveau du seuil (93 à 96 %). Mais l'écart
    ancien/nouveau dépasse ce bruit et va **toujours dans le même sens**. Le nouvel ordre fait
    descendre ou disparaître une étiquette sur ~6 % des mails. Rien ne dit lequel des deux
    gabarits a raison : le corpus n'a pas de vérité terrain.
- DOD self-check :
  - ✓ build, tests, `AiProviderProfile`, variable sur la ressource, recréation du conteneur,
    gabarit réordonné, test de convention vu rouge, tests existants intacts, débit, hygiène des
    journaux, `docs/ia-fournisseurs.md`. Règle 1b non applicable : l'étiquetage n'est atteignable
    par aucun endpoint, comme la task le justifie.
  - ✗ garde qualité ≥ 95 %.
- Next step : **arrêt**, `questions/task-355.md`. Après arbitrage : `/sonar task-355`, qui reprend
  la chaîne.
- **Reprise après l'arbitrage A** (2026-10-08) : `EmailTaggingService.cs` remis à l'état de
  `develop`, `TaggingPromptPrefixTests` retiré. Les chiffres du commentaire de
  `DefaultOllamaNumParallel` et de `docs/ia-fournisseurs.md` sont ramenés à l'ancien gabarit
  (45,6/min à P=4). La doc explique le rejet. Commit `c456a028`, poussé.
  - Build : 0 erreur.
  - Suite : 6 438 réussis, 16 ignorés, 0 échec. Application à 3 552, soit exactement −2 (les tests
    retirés).
  - Diff final contre `develop` : 5 fichiers, AppHost, tests du profil et du câblage, doc.
  - Next step : `/sonar task-355`.

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), port 9000. Conteneurs `sonarqube_db` puis `sonarqube`
  redémarrés par le pré-flight.
- Une analyse de la branche, après l'arbitrage A : build Release, 5 passes OpenCover vertes
  (6 438 réussis, 16 ignorés, 0 échec), `EXECUTION SUCCESS`, traitement serveur `SUCCESS`.
- Phase 1 (code neuf) : ✓ Quality Gate OK, new_coverage = 97,5 %. 0 bug, 0 vulnérabilité,
  0 hotspot à revoir.
  - Un constat reste dans la période de code neuf, **hors code de la task** : S107 sur
    `SemanticSearchService.cs:395`, créé le 2026-10-02 par task-329. Il était déjà dans la
    baseline et a été laissé par task-351 à 354 pour le même motif.
  - Le diff de task-355 n'ajoute aucun constat : `src/AppHost/**` est exclu de l'analyse, et le
    reste est fait de tests et de documentation.
- Phase 1, issues fixées : 0. Tests ajoutés : 0.
- Phase 2 (legacy) : sautée, les cibles du projet sont tenues (0 bug, 0 vulnérabilité, A/A/A,
  couverture 97,9 % ≥ 95). 13 code smells legacy acceptés.
- `conventions/csharp.md` : rien à consigner, aucune règle corrigée à la main.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-10-05) | Final (branche, 2026-10-08) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,6 % | 97,5 % | −0,1 pt (fenêtre glissante de 30 jours, aucune ligne couvrable ajoutée par la task) |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 13 | 13 | 0 |
| Coverage (projet) | 97,9 % | 97,9 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `/lint-angular` : skipped. Aucun changement Angular de la task : `client-angular` n'est pas listé.
  L'arbre porte 2 fichiers de travail non commité de l'humain (`apps/mss/…/environment.ts`,
  `apps/weda2/…/environment.ts`), sans lien avec task-355. Ils ne sont pas touchés (règle 6).
- `/lint-mobile` : skipped. `client-mobile` n'est pas listé, et la task n'a aucun diff sur ce repo.

## E2E log

> **Flaky récurrent (4e occurrence)** : E2E-COMPOSE-002, côté Angular. Ce n'est pas un flaky :
> c'est le bug produit déjà établi (transfert parti avant le chargement du contenu), suivi par
> **task-350**, toujours en `todo`. Sa correction est due. Rien à voir avec task-355.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 31 verts, 0 flaky, 0 rouge, 0 quarantaine | 5 min 40 s |
| angular | api-mail touché | ✅ verte | 30 verts, 1 flaky, 0 rouge, 0 quarantaine | 5 min 23 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task. La task ne le modifie pas.
- Clone mobile : sur `develop`, déjà aligné sur `origin/develop` (`ff75eb9`). Angular : branche de
  l'humain `feature/nova-rewriting-mss`, avec son travail non commité (2 `environment.ts`).
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel). Le port 5052 reste à l'écoute
  sur `192.168.1.170` : c'est le relais `portproxy` du banc, préexistant, pas un résidu.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002)

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ⚠️ flaky | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
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
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/282, label
  `awaiting-human-merge`.
- Aucun autre repo. `client-angular` et `client-mobile` ne sont pas listés. Leur suite e2e a été
  rejouée contre l'api-mail de la branche, verte.

## Code Review Summary

**Verdict : APPROVED.** 4 fichiers de code relus et la doc ; 0 bloquant, 2 suggestions.

- Build : 0 erreur. Tests : 6 438 réussis, 16 ignorés, 0 échec (troisième validation complète,
  totaux identiques).
- DOD, compte tenu de l'**arbitrage A** (gabarit non livré) :

  | Item | État |
  |---|---|
  | Build, tests | ✓ |
  | `AiProviderProfile` : défaut 4, surcharge, 3 cas invalides | ✓ (5 cas de refus, mutations prouvées) |
  | `OLLAMA_NUM_PARALLEL` sur la ressource, test | ✓ (`OllamaServerEnvironmentWiringTests`, mutation prouvée) |
  | Conteneur persistant recréé | ✓ (constaté 2 puis 4, Develop log) |
  | Gabarit réordonné | ✗ **non livré par arbitrage A** (garde échouée) |
  | Test de convention vu rouge | ✗ écrit et vu rouge, puis **retiré avec le gabarit** |
  | Tests d'étiquetage existants intacts | ✓ (code d'étiquetage identique à `develop`) |
  | Garde qualité ≥ 95 % | ✗ **mesurée, échouée** (89,5 à 94 %, sens unique) : cause de l'arbitrage |
  | Débit ≥ 70/min | ✗ **sans objet sans le gabarit** : 45,6/min livrés à P=4 |
  | Aucune donnée de santé dans les logs | ✓ (inchangé) |
  | `docs/ia-fournisseurs.md` | ✓ parallélisme, VRAM, recréation, et pourquoi le gabarit n'est pas réordonné |
  | Règle 1b | sans objet (aucun comportement atteignable par un endpoint) |

- Règle 1b, comportement → test → preuve rouge : aucun comportement d'endpoint ne change. Le
  comportement livré, une variable d'infrastructure de l'AppHost, est prouvé par
  `AiProviderProfileTests` et `OllamaServerEnvironmentWiringTests` (mutations au Develop log),
  puis en vrai par `docker logs` (`OLLAMA_NUM_PARALLEL:2` puis `:4`).
- E2E : double verrou levé. `## E2E log` vert sur les deux voies, parité verte.
- Suggestions :
  - **Défaut 2 au lieu de 4** : même débit (45,6/min) avec le gabarit actuel, pour 1,4 Go de VRAM
    en moins. Le défaut 4 suit la DOD.
  - **Doc** : le paragraphe « `api-mail` joint Ollama par `127.0.0.1:11434` » se retrouve sous le
    sous-titre « Pourquoi le gabarit… ». Il serait mieux remonté dans la liste.

## Timings

*(généré par `tools/timing/report.sh --task task-355 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | — | 5 (31 s) | 7 (9 min 58 s) | — | api-mail 5B/7T, arbitrage A : gabarit retire, parallelisme seul; no start marker |
| /sonar | ok | 7 min 05 s | 1 (31 s) | 5 (4 min 09 s) | 2 (40 s) | 1 itération(s), api-mail 1B/5T, QG OK, 0 constat sur le code de la task, phase 2 sautee (cibles tenues) |
| /lint-angular | skipped | 11 s | — | — | — | client-angular non liste ; 2 fichiers de WIP humain (environment.ts) non touches |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non liste, aucun diff (branche develop, arbre propre) |
| /e2e | ok | 12 min 33 s | — | — | — | e2e ×3 (11 min 11 s), 2 voies vertes, parite verte, 1 flaky connu (E2E-COMPOSE-002 angular, task-350) |
| /review | ok | 4 min 36 s | 1 (9.7 s) | 1 (3 min 09 s) | — | api-mail 1B/1T, APPROVED, PR api-mail #282 |
| **Total cycle** | | **24 min 45 s** | **7 (1 min 12 s)** | **13 (17 min 17 s)** | **2 (40 s)** | |
