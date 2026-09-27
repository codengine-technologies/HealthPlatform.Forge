# todo-task-328.md — L'assistant IA ne livre jamais à un médecin l'action préparée pour un autre : chaque conversation a son propre contexte d'exécution

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — fuite de données de santé entre praticiens : le médecin A peut recevoir le **nom et le téléphone d'un patient du médecin B**, ou un brouillon rédigé d'après les mails de B.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-04**, contre-vérifié ligne à ligne).

## Ce qui est établi (develop @ `14d58398`)

- `src/Api/Extensions/SemanticKernelExtensions.cs:81, 133` : le `Kernel` est **Singleton**.
- `src/Application/Services/Implementation/AiConversationService.cs` (Scoped,
  `Api/DependencyInjection.cs:134`) :
  - `:29` `private readonly AiActionFunctionFilter _actionFilter = new();` — une instance par requête ;
  - `:79-87` : `if (!_kernel.Plugins.Contains("EmailActionsPlugin")) AddFromType<…>()` puis
    `if (!_kernel.FunctionInvocationFilters.Contains(_actionFilter)) _kernel.FunctionInvocationFilters.Add(_actionFilter);`
    — `Contains` compare **par référence**, donc toujours faux : chaque requête **ajoute un filtre
    au Kernel partagé**, jamais retiré ;
  - `:216-222` : la requête lit `_actionFilter.LastAction`.
- `src/Application/Filters/AiActionFunctionFilter.cs` : à **chaque** appel de fonction, **chaque**
  filtre enregistré écrit `_lastAction`.

**Scénario** : B demande « appelle le patient » → le modèle de B appelle `call_patient(phoneNumber,
patientName)` → tous les filtres écrivent l'action → A, dont le flux se termine au même moment sur le
même pod, lit son filtre et reçoit l'événement SSE `Action` de B. Idem `compose_email`,
`contact_practitioner`.

**Effets secondaires** : liste de filtres qui grossit sans fin (fuite mémoire, chaque prompt de
tagging/résumé traverse N filtres) ; mutation concurrente non protégée d'une collection lue par
d'autres requêtes ; au premier appel concurrent sur un pod neuf, `AddFromType` en double lève
`ArgumentException` → 500.

## Objective

Que l'action produite par une fonction de l'assistant ne soit **visible que de la conversation qui l'a
déclenchée**, et que le Kernel partagé ne soit plus jamais modifié par une requête.

### Périmètre

1. Aucune mutation du Kernel singleton pendant une requête : plugin et filtre enregistrés **une fois**
   à la composition, ou **clone** du Kernel par requête (`kernel.Clone()`) portant plugin et filtre —
   choix de `/develop` après lecture du code, justifié dans le task file.
2. L'action capturée est portée par un état **propre à l'invocation** (arguments de l'invocation,
   état de requête), jamais par un champ partagé.
3. Tous les autres consommateurs du Kernel (tagging, résumé, rédaction, recherche) inchangés dans leur comportement.

### Hors périmètre

- Le stockage des conversations en mémoire d'un seul pod (task-336).
- Le comptage des tokens (task-342).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : deux `AiConversationService` construits sur le
      **même** Kernel ; la fonction invoquée pour la conversation B produit une action ; sur le code actuel la
      conversation A lit l'action de B ; après correctif A ne lit **rien**
- [ ] Test : N requêtes successives → le nombre de filtres du Kernel partagé est **constant**
- [ ] Test : deux premières requêtes concurrentes sur un Kernel neuf → aucune `ArgumentException`
- [ ] Test : l'action d'une conversation lui revient bien (chemin nominal `call_patient`, `compose_email`, `contact_practitioner`)
- [ ] Non-régression : tests existants du tagging, du résumé et de la rédaction verts
- [ ] Aucun nom, téléphone ni contenu de mail ajouté dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; deux comptes praticiens de test (A et B) sur deux navigateurs.
2. B ouvre l'assistant et demande « appelle le patient » sur un mail de test porteur d'un patient fictif.
3. Au même moment, A pose une question quelconque à l'assistant.
4. **Attendu** : A ne reçoit **aucune** proposition d'action ; B reçoit la sienne. Avant correctif : A peut recevoir la proposition d'appel du patient de B.
5. Répéter une vingtaine de fois : la mémoire du processus API reste stable (pas de croissance liée au nombre de conversations).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de confidentialité
- **Exigences DSR honorées** : non applicable — rétablit le cloisonnement entre praticiens (PGSSI-S)
- **INS** : non applicable — mais la US empêche la fuite de traits d'identité patient (nom, téléphone) entre praticiens
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : **au cœur** — une donnée patient d'un praticien ne doit jamais atteindre un autre praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; aucune donnée patient ajoutée aux logs
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : à informer le DPO — fuite potentielle entre praticiens avant correctif ; traitement inchangé après

## Branches
- `api-mail` (pushed) : fix/task-328-contexte-conversation-ia-isole — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-328-contexte-conversation-ia-isole

## Timings

*(généré par `tools/timing/report.sh --task task-328 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 6 min 42 s | 5 (22 s) | 5 (2 min 25 s) | — | api-mail 5B/5T |
| /sonar | ok | 4 min 59 s | 1 (18 s) | 5 (3 min 05 s) | 2 (34 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 0.4 s | — | — | — | repo non touché par task-328 |
| /lint-mobile | skipped | 0.4 s | — | — | — | repo non touché par task-328 |
| /verify-visual | skipped | 0.5 s | — | — | — | repo non touché par task-328 |
| /review | ok | 3 min 48 s | 1 (5.7 s) | 1 (1 min 57 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 4 min 31 s | — | — | — | — |
| **Total cycle** | | **20 min 17 s** | **7 (46 s)** | **11 (7 min 28 s)** | **2 (34 s)** | |

## Develop log

- Repos touched : api-mail (branche `fix/task-328-contexte-conversation-ia-isole`)
- DTOs published : no DTO change — Interop : no interop change
- **Choix d'implémentation (périmètre §1)** : **clone du Kernel par conversation** (`kernel.Clone()` dans le constructeur d'`AiConversationService`), plutôt qu'un enregistrement unique à la composition. Raisons : le filtre de capture est par nature propre à une conversation (il porte l'action à rendre à CETTE requête) ; un filtre unique au singleton aurait exigé de porter l'action dans un état d'invocation (AsyncLocal / arguments) avec le même risque de croisement sous concurrence ; `Clone()` copie la collection de plugins et les listes de filtres et **partage les services** (connecteur OpenAI, HttpClient), donc aucun coût de connexion. Plugin et filtre ne vivent que sur le clone — le singleton n'est plus jamais écrit par une requête (§1), l'action est portée par le filtre de la seule conversation qui l'a déclenchée (§2). Seul `AiConversationService` active l'appel de fonctions (`FunctionChoiceBehavior.Auto`) : les autres consommateurs du Kernel (tagging, résumé, rédaction, recherche) n'utilisaient jamais le plugin, leur comportement est inchangé (§3).
- Commits : api-mail `5a2355b0` fix(ai): chaque conversation de l'assistant a son propre Kernel
- **Run ROUGE d'abord** (code d'origine, `AiConversationIsolationTests`, Release) :
```
[xUnit.net 00:00:01.47]     mss.mail.application.tests.Services.Ai.AiConversationIsolationTests.ConcurrentFirstConversations_OnAFreshKernel_NeverThrow [FAIL]
[xUnit.net 00:00:01.54]     mss.mail.application.tests.Services.Ai.AiConversationIsolationTests.AnActionTriggeredForDoctorB_NeverReachesDoctorA_WhoseStreamEndsMeanwhile [FAIL]
[xUnit.net 00:00:01.55]     mss.mail.application.tests.Services.Ai.AiConversationIsolationTests.SuccessiveConversations_NeverChangeTheSharedKernel [FAIL]
   Assert.Null() Failure: Value is not null
Expected: null
   Assert.DoesNotContain() Failure: Filter matched in collection
   Assert.Equal() Failure: Values differ
Expected: 0
Failed!  - Failed:     3, Passed:     3, Skipped:     0, Total:     6, Duration: 239 ms - mss.mail.application.tests.dll (net10.0)
```
  → A reçoit l'action de B ; le nombre de filtres du Kernel partagé croît ; deux constructions concurrentes lèvent. Les 3 cas nominaux (`call_patient`, `compose_email`, `contact_practitioner`) passaient déjà.
- **Après correctif** : 6 / 6 verts. Deux tests existants figeaient l'ancien comportement et ont été corrigés : `StreamChatAsync_WhenModelCallsAnActionFunction…` invoquait la fonction sur le Kernel **partagé** tenu par le test (précisément le schéma de la fuite) — il passe désormais par le Kernel que le service remet au modèle, comme le connecteur réel ; `Constructor_OnAKernelAlreadyCarryingThePlugin_DoesNotRegisterItTwice` → `Constructor_NeverRegistersThePluginOrTheFilterOnTheSharedKernel`.
- Local build / test : ✓ api-mail **Release** — 5 632 passés, 16 ignorés, 0 échec (le build Debug est bloqué par une instance api-mail lancée par l'humain, qui verrouille `src/Api/bin/Debug`).
- Passe qualité (/simplify) : no simplification applied — diff de production réduit au constructeur, relu.
- Logs : aucun ajout (le log existant « Action captured from filter: {ActionType} » ne porte que le type).
- DOD self-check : 8 / 8 items vérifiables par commande vérifiés ; le Manual Test Plan (deux navigateurs, deux praticiens) reste au HAG.
- Next step : /sonar task-328

## Sonar log

- Serveur : SonarQube 9.9.8 (`sonar.login`) ; période « new code » = 30 jours (héritée)
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 98.8 %, 0 issue new-code, 0 hotspot ; lignes nouvelles d'`AiConversationService.cs` toutes couvertes
- Phase 1 — Issues fixées : 0 — Tests ajoutés : 0 (déjà couverts par `/develop`)
- **Au passage** : la branche part du `develop` qui porte tout task-320 ; cette analyse couvre donc aussi le commit task-320 `1ed9435c` (invalidation du statut de dossier dans `BackgroundEnrichmentProcessor`), mergé sans analyse Sonar — **0 issue, lignes nouvelles couvertes**. Le trou signalé par l'humain est comblé.
- Phase 2 (legacy) : skipped — baseline déjà bonne (8 code smells, notes A/A/A)
- Build / tests : ✓ green (Release + OpenCover : 5 632 passés, 16 ignorés, 0 échec)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 98.8 % | 98.8 % | 0 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 8 | 8 | 0 |
| Coverage (projet) | 98.0 % | 98.0 % | 0 pt |
| Duplication | 0.5 % | 0.5 % | 0 pt |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- skipped — client-angular non listé dans `**Repos**:` (le travail Angular non commité présent dans l'arbre appartient à task-320, pas à cette task)

## Lint mobile log

- skipped — client-mobile non listé, aucun changement mobile

## Visual verify log

- skipped — no mobile change

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/255 — label `awaiting-human-merge` (branche à jour de `develop`, task-189 inclus)

## Code Review Summary

- **APPROVED** (1 passage). Vérifié sur la sémantique de `Kernel.Clone()` (SK 1.80.1 : plugins et `Data` copiés, services partagés) et par recherche de toute écriture sur un `Kernel` dans `src` : seul le clone est écrit ; le filtre d'une conversation ne voit que ses propres appels ; le service est Scoped et n'exécute jamais deux flux à la fois ; les autres consommateurs du Kernel sont inchangés (aucun n'active l'appel de fonctions).
- Revalidation : api-mail Release 5 650 passés, 16 ignorés, 0 échec.
- Suggestions non bloquantes : plugin reconstruit par réflexion à chaque requête (sans état, pourrait être construit une fois) ; test de constructions concurrentes probabiliste (l'invariant est tenu par les tests déterministes) ; `ManualResetEventSlim` non disposé dans ce test.
- **AIPD** : informer le DPO de la fuite potentielle avant correctif.

