# todo-task-385.md — Identifier les usages de l'IA qui consomment le plus de tokens

**Repos**: api-mail
**Dependencies**: aucune
**Priorité**: 2 — optimisation des coûts IA : savoir où partent les tokens avant de décider quoi optimiser.

> **Origine.** Demande humaine du 2026-10-20 (`/po`), après l'état des lieux de la comptabilisation des tokens
> dans api-mail. Décisions prises au cadrage : attribution par **fonctionnalité + appel** (sans identité du
> praticien), **tokens seulement** (pas de conversion en euros), **pas d'alerte** pour l'instant (observer d'abord),
> tableau de bord en **développement + JSON pour la production**.

## Ce qui est établi (2026-10-20)

- Tous les appels IA passent par le `Kernel` Semantic Kernel singleton (`src/Api/Extensions/Ai/AiKernelFactory.cs`),
  dont les deux services sont enveloppés par `MeteredChatCompletionService` et `MeteredEmbeddingGenerator`. Ils lisent
  l'usage déclaré par le fournisseur (`AiTokenUsageReader`) et alimentent `mssante_ai_tokens_total{provider,model,kind}`
  (`src/Application/Telemetry/MailProcessingMetrics.cs`), exporté sur `/metrics` et en OTLP.
- **Aucune fonctionnalité dans les labels** : impossible de distinguer classement, résumé, assistant, correction.
- **Aucune trace ne contient l'usage réel** : seuls deux journaux parlent de tokens, et ce sont des estimations
  (`AiConversationService` « … estimated tokens », `EmailSummaryService` « ≈{Tokens} tokens » avant l'appel). Le
  journal d'usage intégré à Semantic Kernel n'est pas branché (noyau construit sans `ILoggerFactory`).
- Seul l'assistant tient un compteur par conversation (Redis `TotalTokensUsed`, SSE `final`), qui mélange usage réel et
  estimation char/4.
- Angles morts : un flux annulé ou en erreur avant son dernier fragment n'est pas compté ; l'usage en streaming
  OpenAI n'est couvert par aucun test.
- Points d'appel IA (12) : assistant — tour en streaming, résumé initial, résumé glissant (`AiConversationService`) ;
  `AiTextService` — correction de dictée (streaming), génération de modèle, amélioration de texte, détection de
  champs ; `SpellingCorrectionService` (`POST /api/v1/ai/correct-spelling`) ; `EmailSummaryService` (résumé de mail
  ou CDA) ; `EmailTaggingService` (classement automatique, à chaque mail reçu et en reprise) ;
  `BoundedEmbeddingInvoker` (embeddings des mails et documents) ; `SemanticSearchService` (embedding de recherche).
- Grafana : tableaux de bord de l'AppHost dans `src/AppHost/grafana/dashboards/` ; Grafana et Prometheus de
  production dans `DevOps/Prod` (dépôt géré manuellement).

## Objective

Aujourd'hui, on sait combien de tokens partent chez chaque fournisseur, mais pas **pour quelle fonctionnalité** ni
**à cause de quel appel**. Chaque appel IA d'api-mail devient attribuable à une fonctionnalité et traçable
individuellement. L'exploitation peut ainsi repérer les usages qui consomment le plus — en volume total comme par
appel — avant de décider des optimisations (traitées ensuite dans des US séparées, par ordre de coût mesuré).

### Règles métier

1. **Attribution** : chaque appel IA est rattaché à **une** fonctionnalité parmi `classement-auto`, `resume-mail`,
   `assistant-tour`, `assistant-resume-initial`, `assistant-resume-glissant`, `correction-dictee`,
   `generation-modele`, `amelioration-texte`, `detection-champs`, `correction-orthographe`, `embedding-document`,
   `embedding-recherche`. Un appel sans étiquette est compté sous `non-attribue`, jamais perdu.
2. **Mesures par fonctionnalité** : tokens consommés (entrée, sortie, embedding), nombre d'appels, et distribution
   des tokens par appel (médiane, 95ᵉ centile) — pour distinguer « cher parce que fréquent » de « cher parce que
   volumineux ».
3. **Trace par appel** : une ligne de journal par appel IA, avec fonctionnalité, fournisseur, modèle, tokens en
   entrée et en sortie, durée, issue (`ok`, `interrompu`, `erreur`) et identifiant technique du mail ou de la
   conversation. **Jamais** de contenu, d'objet, d'adresse, d'INS ni d'identité du praticien.
4. **Usage réel uniquement** : métriques et traces ne portent que les comptes déclarés par le fournisseur. Un appel
   sans usage déclaré (y compris un flux interrompu) est compté comme appel avec un usage « inconnu », sans
   estimation.
5. **Restitution** : un tableau de bord présente tokens par fonctionnalité, appels par fonctionnalité, tokens par
   appel (médiane et 95ᵉ centile) et part de chaque fonctionnalité. Livré dans le Grafana de développement (AppHost),
   avec le même JSON fourni pour l'import manuel en production.
6. **Hors périmètre** : conversion en euros, alertes de dérive, attribution par praticien, optimisations elles-mêmes.

## Gherkin

See `tests/Features/Mss/AiConsumptionObservability.feature`

## Definition of Done

- [ ] Build et tests d'api-mail verts (0 erreur)
- [ ] Les 12 points d'appel IA posent leur fonctionnalité ; un test d'architecture échoue si un nouvel appel IA n'en pose pas
- [ ] `mssante_ai_tokens_total` porte un label `feature` ; nouvel histogramme des tokens par appel `{feature, kind}` ; nouveau compteur d'appels `{feature, issue}`
- [ ] Une trace structurée par appel IA (niveau Information) ; un test vérifie qu'elle ne contient ni contenu ni adresse
- [ ] Un flux interrompu est compté (issue `interrompu`, usage inconnu) ; l'émission de l'usage en streaming OpenAI est couverte par un test
- [ ] Test d'intégration de bout en bout pour `POST /api/v1/ai/correct-spelling` (règle 1b), vu rouge : avec un fournisseur IA simulé déclarant 120 tokens en entrée et 40 en sortie, `/metrics` expose ces tokens sous `feature="correction-orthographe"` ; cas d'échec — sans usage déclaré, l'appel est compté (compteur d'appels) sans aucun token
- [ ] ≥ 1 test unitaire par branche de l'attribution (fonctionnalité posée, absente → `non-attribue`, portées imbriquées)
- [ ] Tableau de bord Grafana « Consommation IA par fonctionnalité » dans `src/AppHost/grafana/dashboards/` ; JSON livré pour l'import en production
- [ ] `docs/ia-fournisseurs.md` complété (métriques, labels, lecture du tableau de bord)
- [ ] Aucune donnée de santé ni donnée personnelle dans les traces

> Pas de scénario e2e : aucun parcours médecin n'est créé ni modifié (US d'observabilité interne).

## Manual Test Plan

1. Lancer l'AppHost, recevoir quelques mails (classement automatique et embeddings), demander un résumé, utiliser
   l'assistant et la correction orthographique.
2. Ouvrir le tableau de bord « Consommation IA par fonctionnalité » : chaque fonctionnalité utilisée apparaît avec
   ses tokens et ses appels ; rien sous `non-attribue`.
3. Dans Seq, filtrer les traces d'appels IA : une trace par appel, avec fonctionnalité, modèle, tokens, durée et
   identifiant ; aucun contenu.
4. Lancer une correction de dictée puis l'annuler en cours : l'appel apparaît avec l'issue « interrompu ».
5. Importer le JSON du tableau de bord dans le Grafana de recette : les panneaux s'affichent.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — observabilité interne, sans échange métier
- **Vague Ségur** : hors Ségur — aucune exigence de référencement concernée
- **Exigences DSR honorées** : non applicable — observabilité interne
- **INS** : non applicable — jamais présente dans les traces
- **Authentification PS** : inchangée — aucune route nouvelle exposée aux praticiens
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — aucun document ni échange métier
- **Tracé PGSSI-S** : nouvelles traces techniques par appel IA (fonctionnalité, modèle, tokens, durée, issue, identifiant technique) — sans donnée de santé ni donnée personnelle ; durée de conservation des journaux existants (Seq)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucune donnée de santé produite
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle ajoutée (identifiants techniques uniquement)

## Branches
- `api-mail` (pushed) : feat/task-385-consommation-ia-par-fonctionnalite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-385-consommation-ia-par-fonctionnalite

## Develop log

**Repo** : `api-mail` — commit `b0d933d1` poussé sur `feat/task-385-consommation-ia-par-fonctionnalite`.

### Livré
- `AiFeature` (12 fonctionnalités + `non-attribue`) et `AiFeatureScope` (AsyncLocal, la portée externe garde fonctionnalité et identifiant) — `src/Application/Telemetry/AiFeature.cs`.
- Métriques : label `feature` sur `mssante_ai_tokens_total` ; histogramme `mssante_ai_tokens_per_call{feature, kind}` (seaux 16 → 131 072) ; compteur `mssante_ai_calls_total{feature, provider, model, issue, usage}` (`issue` : `ok | interrompu | erreur`, `usage` : `connu | inconnu`).
- `AiCallRecorder` : métriques + une trace `[AiCall]` Information par appel (fonctionnalité, fournisseur, modèle, tokens, durée, issue, identifiant technique), sans contenu.
- Décorateurs réécrits : contexte lu au début de l'appel ; flux annulé → `interrompu`, abandonné par son lecteur → `interrompu`, en erreur → `erreur`, toujours enregistré (finally). `AiKernelFactory.Build(…, ILoggerFactory)`.
- 15 portées posées sur les 12 usages (AiTextService ×4, SpellingCorrection, EmailSummary, EmailTagging, AiConversationService ×3 avec `conversationId`, BoundedEmbeddingInvoker, SemanticSearch, EmbeddingReindex, AddNewMailConsumer ×3 avec `MailId`, AiDiagnosticsController ×2).
- Tableau de bord `src/AppHost/grafana/dashboards/mssante-ai-consumption.json` (16 panneaux, variable `feature`, même JSON pour l'import en prod) ; `docs/ia-fournisseurs.md` § « Consommation par fonctionnalité ».
- **Défaut pré-existant trouvé et corrigé** : `/metrics` vide depuis le 17/10/2026 (exportateur Prometheus 1.16.0-beta.1 sur OpenTelemetry 1.20.0 → `TypeLoadException: OpenTelemetry.Internal.MathHelper` à chaque collecte, réponse 200 sans série). Exportateur aligné en 1.20.0-beta.1. Leçon capturée : `conventions/csharp.md` § `exportateur-prometheus-aligne`.

### Tests (règle 1b) — comportement → test → preuve rouge
| Comportement | Test | Preuve rouge |
|---|---|---|
| Tokens exposés sur `/metrics` sous `feature="correction-orthographe"` (120/40) via `POST /api/v1/ai/correct-spelling` | `AiConsumptionMetricsEndpointIntegrationTests.CorrectSpelling_TheTokensReportedByTheProvider_AreExposedUnderItsFeature` (vrai kernel `AddSemanticKernel`, vrai connecteur OpenAI, `ConfigureOpenTelemetry` de prod, fournisseur simulé en HTTP) | Rouge (1) avec l'exportateur 1.16.0-beta.1 : `/metrics` vide ; (2) mutation « portée retirée de `SpellingCorrectionService` » → série absente |
| Sans usage déclaré : appel compté (`usage="inconnu"`), aucun token | `…_WithoutReportedUsage_TheCallIsCounted_WithoutAnyToken` | Mutation (2) → rouge |
| Le tableau de bord n'interroge que des séries exposées | `…TheConsumptionDashboard_OnlyQueriesSeriesThatTheApiExposes` | Rouge à la première écriture (extraction trop large, corrigée en lisant les `expr`) |
| Flux abandonné → `interrompu` | `MeteredAiServicesTests.AStreamAbandonedByItsReader_IsCountedAsInterrupted` | Mutation « issue par défaut = ok » → rouge |
| Appel en erreur compté `erreur` | `MeteredAiServicesTests.AFailingChatCall_IsCountedAsAnError_AndStillThrows` | Mutation « catch sans enregistrement » → rouge |
| Flux annulé → `interrompu`, usage inconnu ; trace sans contenu/adresse/INS ; hors portée → `non-attribue` ; embeddings | `MeteredAiServicesTests` (8 tests) | — |
| Usage en streaming OpenAI (`stream_options.include_usage`) compté | `AiKernelCompositionTests.AnOpenAiStream_AsksForItsUsage_AndItIsCounted` | — |
| Tout appel IA déclare sa fonctionnalité | `AiFeatureScopeScanTests` (+3 auto-tests de la garde) | Mutation « portée retirée » → rouge, désigne `SpellingCorrectionService.cs:108` |
| Attribution : posée, absente, imbriquée, flux async | `AiFeatureScopeTests` (7) ; `MailProcessingMetricsAiTests` (labels) | — |

### Validation
- Build : 0 erreur, 0 avertissement.
- `dotnet test HealthPlatform.Api.Mail.sln` : domain 195, infrastructure 690, application 3 670, api 1 272, integration 901 (+16 skipped pré-existants) — **0 échec**.
- §Q passe qualité : relecture du diff, aucun nettoyage supplémentaire (helper `OutcomeOf` déjà factorisé dans `AiCallRecorder`).

## Sonar log
- Serveur : SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`, période new code = 30 jours.
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,0 % ; fichiers de la task (`MeteredChatCompletionService`, `MeteredEmbeddingGenerator`, `AiCallRecorder`) à 0 ligne / 0 condition non couverte.
- Phase 1 — Issues fixées : 3 smells (S107 `AiCallRecorder` — trace par gabarit ; CA1861 et SYSLIB1045 dans les tests) — commits `9e935848`, `ea0b19e1`, `d1467e41`.
- Phase 1 — Tests ajoutés : 3 (somme d'usages d'une réponse multiple, embedding sans usage, attributs du décorateur) ; propriété `Inner` sans appelant retirée.
- Phase 2 (legacy) : 0 itération — aucune issue ouverte.
- Build / tests : ✓ green (domain 195, application 3 670, infrastructure 690, api 1 275, integration 901 + 16 skipped).
- Conventions : `conventions/csharp.md` — CA1861 (occurrence 4), nouvelles entrées S107 (`[LoggerMessage]` > 6 propriétés) et SYSLIB1045.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,6 % | 97,0 % | +0,4 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 (3 introduits puis corrigés) |
| Coverage (projet) | 97,9 % | 98,0 % | +0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log
- `/lint-angular` : skipped — `client-angular` absent de `**Repos**:` et non touché par task-385 (le fichier non commité `front/libs/mss/src/core/models/build-info.model.ts` relève de task-384, humain).

## Lint mobile log
- `/lint-mobile` : skipped — `client-mobile` absent de `**Repos**:` et non touché par task-385.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte (2ᵉ passage) | 38 verts, 0 flaky, 0 rouge, 0 quarantaine | 6,1 min (suite) |
| angular | api-mail touché | ✅ verte | 46 verts, 0 flaky, 0 rouge, 1 quarantaine (passée) | 6,2 min (suite) |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-385-consommation-ia-par-fonctionnalite`
- **1ᵉʳ passage mobile rouge — outillage, pas régression** : `mss.mail.e2e.runtimeconfig.json` a disparu de `bin/Debug` en cours de voie (build concurrent de Visual Studio, ouvert sur la solution) → 6 parcours rouges (`hostpolicy.dll not found`, et cascades : inbox vide, compte rendu absent). Outil reconstruit, voie rejouée : 38/38. Leçon : `conventions/e2e.md` § `outil-e2e-reecrit-en-cours-de-voie`.
- Quarantaines : E2E-COMPOSE-002 (angular, task-350, posée le 2026-10-09, 11 jours) — **verte** sur ce run.
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun client touché)
- Démontage : complet pour ce run (ports libres). Deux conteneurs `e2e-greenmail-gcgjbrzp` / `e2e-dovecot-kgrndjwd` arrêtés depuis le 2026-10-14 subsistent — antérieurs à ce run, non retirés (à nettoyer par l'humain).

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
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
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
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
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
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/303 — label `awaiting-human-merge`
- `client-angular`, `client-mobile` : non touchés
- `devops` : managed manually by the human — import du JSON `src/AppHost/grafana/dashboards/mssante-ai-consumption.json` dans le Grafana de production

## Code Review Summary

### Verdict : ✅ APPROVED — 29 fichiers relus, 0 bloquant, 2 suggestions

| Zone | Verdict |
|---|---|
| `Application/Telemetry/AiFeature.cs` — fonctionnalités, `AiFeatureScope` (AsyncLocal, l'externe l'emporte, restauration au dispose) | ✅ |
| `MailProcessingMetrics` — label `feature`, histogramme `mssante_ai_tokens_per_call` (seaux 16 → 131 072), compteur `mssante_ai_calls_total{feature, provider, model, issue, usage}` | ✅ cardinalité bornée (littéraux de code) |
| `Api/Extensions/Ai/AiCallRecorder.cs` — métriques + trace `[AiCall]` | ✅ aucune donnée de santé : littéraux, nombres, Guid techniques |
| `MeteredChatCompletionService` — issue sur chaque sortie (fin normale, exception, abandon du lecteur, exception du consommateur via `DisposeAsync`) | ✅ |
| `MeteredEmbeddingGenerator`, `AiKernelFactory(ILoggerFactory)` | ✅ |
| 15 portées sur les 12 usages | ✅ garde `AiFeatureScopeScanTests` |
| `Directory.Packages.props` — exportateur Prometheus 1.16.0-beta.1 → 1.20.0-beta.1 | ✅ corrige `/metrics` vide depuis le 17/10 |
| Tableau de bord Grafana + doc | ✅ chaque série interrogée vérifiée exposée |

**Règle 1b — comportement → test d'intégration → preuve rouge**

| Comportement | Test | Preuve rouge |
|---|---|---|
| Tokens d'un appel exposés sur `/metrics` sous leur fonctionnalité (`POST /api/v1/ai/correct-spelling`, 120 / 40) | `AiConsumptionMetricsEndpointIntegrationTests.CorrectSpelling_TheTokensReportedByTheProvider_AreExposedUnderItsFeature` | rouge sur l'exportateur 1.16 (`/metrics` vide) ; mutation « portée retirée » |
| Appel sans usage déclaré compté, sans token | `…_WithoutReportedUsage_TheCallIsCounted_WithoutAnyToken` | mutation « portée retirée » |
| Le tableau de bord n'interroge que des séries exposées | `…TheConsumptionDashboard_OnlyQueriesSeriesThatTheApiExposes` | rouge à la première écriture |

**Suggestions (non bloquantes)**
- ⚠️ La valeur de fonctionnalité de chaque point d'appel n'est prouvée de bout en bout que pour la correction orthographique ; la garde d'architecture prouve la *présence* d'une portée partout, pas la justesse de la constante. Un test d'intégration par famille (résumé, assistant) renforcerait le filet.
- ⚠️ Le résumé glissant de l'assistant est lancé en tâche détachée (`_ = UpdateRunningSummaryAsync`) après les `yield` du flux : il n'hérite pas de la portée `assistant-tour` et ouvre la sienne. Correct aujourd'hui, mais dépend de l'ordre du code ; à surveiller si `PersistTurnAsync` remonte avant le premier fragment.

## Timings

*(généré par `tools/timing/report.sh --task task-385 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 10 s | — | — | — | — |
| /develop | ok | 28 min 52 s | 10 (49 s) | 9 (4 min 06 s) | — | api-mail 10B/9T |
| /sonar | ok | 15 min 15 s | 3 (42 s) | 12 (10 min 16 s) | 4 (1 min 21 s) | 2 itération(s), api-mail 3B/12T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non listé dans Repos, non touché par task-385 |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non listé dans Repos, non touché par task-385 |
| /e2e | ok | 23 min 49 s | — | — | — | e2e ×4 (21 min 55 s) |
| /review | ok | 4 min 51 s | 1 (8.6 s) | 1 (3 min 50 s) | — | api-mail 1B/1T |
| **Total cycle** | | **1 h 13 min** | **14 (1 min 40 s)** | **22 (18 min 13 s)** | **4 (1 min 21 s)** | |

Autres commandes mesurées : restore ×1 (1.8 s)
