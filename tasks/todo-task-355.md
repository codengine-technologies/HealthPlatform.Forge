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

## Timings

*(généré par `tools/timing/report.sh --task task-355 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | failed | 4.5 s | — | — | — | pre-flight: api-mail sur chore/loadtest-report-ai-metrics |
| **Total cycle** | | **4.5 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
