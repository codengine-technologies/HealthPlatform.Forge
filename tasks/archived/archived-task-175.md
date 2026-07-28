# todo-task-175.md — Fuite inter-praticiens sur le flux SSE : le broker d'évènements mail est clé par dossier, pas par boîte

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe surface HTTP).
> Finding vérifié sur pièces par le PO — voir « Preuve » ci-dessous.

## Objective

Cloisonner par praticien le flux d'évènements mail Server-Sent Events. Aujourd'hui
**le contenu de la boîte MSSanté d'un praticien est diffusé aux flux SSE des autres
praticiens connectés** : `SseMailEventBroker` est un singleton dont la table
d'abonnés est indexée sur le **seul nom de dossier** (`INBOX`, `Sent`, …), qui est
identique pour tout le monde. L'isolation base-par-praticien qui protège le reste
de l'API n'intervient pas ici : le fan-out a lieu **en mémoire, après** la lecture
des données.

**US backend-only (justification)** : le défaut est entièrement côté serveur
(clé d'abonnement). Les frontends consomment le flux inchangé — aucun contrat,
aucune URL, aucun payload modifié. Correctif invisible côté client, hormis la
disparition des évènements qui ne les concernaient pas.

### Preuve (état actuel du code)

- `src/Api/Controllers/V1/MailEventsController.cs:89-93` — les deux premiers
  brokers sont abonnés sur l'identité JWT, le troisième sur la query string :
  ```csharp
  using var notifSub = _notificationBroker.Subscribe(email);   // mssEmail (OK)
  using var syncSub  = _syncProgressBroker.Subscribe(email);   // mssEmail (OK)
  ISseMailEventSubscription? mailSub = !string.IsNullOrWhiteSpace(folder)
      ? _mailEventBroker.Subscribe(folder)                     // <-- dossier seul
      : null;
  ```
- `src/Application/Services/Implementation/SseMailEventBroker.cs:17` — la table
  d'abonnés n'a pas de dimension utilisateur :
  `ConcurrentDictionary<string, ImmutableArray<Subscription>>` clé = `folder`.
- `src/Application/Services/Implementation/SseMailEventBroker.cs:64-85` —
  `PublishAsync(folder, …)` écrit l'évènement à **tous** les abonnés du bucket.
- `src/Application/Extensions/ServiceCollectionExtensions.cs:85` — broker
  enregistré en **singleton** : le bucket est partagé par tout le process.
- `src/Api/Hubs/MailEnrichmentNotifier.cs:20,27,40` — les publications ne
  transportent que `folder`, jamais l'identité de la boîte d'origine.

Le contraste interne est net : `SseNotificationBroker.Subscribe(string userEmail)`
est correctement clé par praticien. Seul le broker mail a été oublié.

### Contenu attendu

1. **Clé d'abonnement composite** : le bucket doit être `(mssEmail, folder)` — ou
   toute forme équivalente garantissant qu'aucun évènement ne franchit la
   frontière de boîte. `mssEmail` provient **exclusivement** du claim JWT validé
   (contrat de sécurité task-022 déjà en place dans ce controller : toute query
   string `?email=` est ignorée par construction — ne pas régresser).
2. **Propagation côté publication** : `PublishEmailsEnrichedAsync` /
   `PublishTagsUpdatedAsync` et leurs appelants (`MailEnrichmentNotifier`, chaîne
   d'enrichissement IMAP) doivent porter l'identité de la boîte dont les mails
   sont issus. L'identité doit venir du contexte de la boîte réellement
   synchronisée, **pas** d'un `IHttpContextAccessor` (l'enrichissement tourne en
   arrière-plan, hors requête HTTP).
3. **Fail-close** : si l'identité de boîte est absente au moment de publier, ne
   diffuser à **personne** et journaliser une alerte — jamais de repli sur une
   diffusion large.
4. **Non-régression du nettoyage** : `Remove` / `SubscriberCount` / la boucle CAS
   doivent rester corrects avec la nouvelle clé (pas de bucket orphelin après
   déconnexion).

### Hors scope

- Refonte du transport SSE, passage à SignalR, changement d'URL ou de payload.
- Les brokers notification et sync-progress (déjà correctement cloisonnés).
- Le durcissement des autres endpoints de l'exploration (tasks séparées).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire **de cloisonnement** sur `SseMailEventBroker` : deux abonnés
      de boîtes différentes sur le **même** nom de dossier ; une publication pour
      la boîte A n'écrit **rien** dans le canal de B (ce test doit échouer sur le
      code actuel — le vérifier explicitement)
- [ ] Test unitaire : deux abonnés de la **même** boîte et du même dossier
      reçoivent bien l'évènement (pas de sur-correction)
- [ ] Test unitaire : publication sans identité de boîte → aucun abonné servi,
      alerte journalisée
- [ ] Test unitaire : après `Dispose` du dernier abonné d'une boîte, le bucket est
      retiré (`SubscriberCount` = 0, pas de fuite mémoire par boîte)
- [ ] Test d'intégration sur `GET /api/v1/mail/events/stream` : l'identité
      d'abonnement est bien issue du claim `mssEmail` et une query string
      `?email=` reste ignorée (contrat task-022 préservé)
- [ ] Aucune donnée de santé en clair dans les logs du broker (le log de
      publication ne cite ni sujet, ni INS, ni contenu — compteur + dossier +
      identité pseudonymisée uniquement)
- [ ] Aucun changement de contrat : URL, noms d'évènements et forme du payload
      inchangés (les trois frontends ne sont pas modifiés)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir **deux navigateurs** (ou deux profils) authentifiés avec **deux
   praticiens MSSanté distincts** (deux `mssEmail` différents), chacun sur sa
   boîte de réception.
3. Sur chaque session, ouvrir les outils réseau et observer le flux
   `GET /api/v1/mail/events/stream?folder=INBOX` (type `text/event-stream`).
4. Envoyer un message MSSanté vers la boîte du **praticien A uniquement**, puis
   déclencher/attendre la synchronisation de A.
5. **Attendu** : le flux de A reçoit `EmailsEnriched` avec le message ; le flux de
   **B ne reçoit rien** (seuls ses heartbeats). Avant correctif, B reçoit
   l'évènement complet de A — sujet, expéditeur, contenu, documents CDA, INS.
6. Vérifier ensuite le fonctionnement nominal : chez A, l'arrivée d'un mail
   rafraîchit toujours la liste en temps réel (pas de régression d'UX), et un
   second onglet du **même** praticien A reçoit bien l'évènement.
7. Fermer les onglets, vérifier dans les logs le désabonnement propre
   (`remaining=0`) et l'absence de contenu médical dans les lignes de log.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité sur le cloisonnement des
  données de santé entre praticiens (exigences MSSanté et PGSSI-S
  confidentialité / contrôle d'accès) — aucune nouvelle exigence adressée
- **INS** : non applicable en tant que traitement nouveau — mais l'INS figure
  dans le payload fuité (`PatientInsMatricule`), ce qui qualifie l'incident
- **Authentification PS** : inchangée (PSC / e-CPS, claim `mssEmail` du JWT
  validé, niveau eIDAS substantiel) — le correctif **renforce** l'usage de cette
  identité comme clé de cloisonnement
- **Habilitations** : inchangées — aucun contrôle RPPS / profession ajouté
- **Interop CI-SIS** : non applicable — transport interne SSE, pas un échange
  CI-SIS ; les documents CDA transportés restent inchangés
- **Tracé PGSSI-S** : abonnement / désabonnement au flux et publication
  (compteurs) journalisés **sans donnée de santé** ; conservation selon la
  politique de journalisation existante du repo. Ajouter une alerte sur
  publication sans identité de boîte (fail-close)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS cible de `api-mail`
- **AIPD / impact RGPD** : **à mettre à jour** — le défaut constitue une
  divulgation de données de santé à des tiers non autorisés (praticiens tiers).
  Qualifier la portée réelle (environnements concernés, fenêtre d'exposition,
  nombre de praticiens simultanés) avec le DPO et statuer sur la notification
  CNIL au titre de la violation de données. **Cette qualification est un
  livrable de la task, distinct du correctif technique.**

## Branches

- `api-mail` (pushed) : `feat/task-175-sse-broker-mailbox-scoped` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-175-sse-broker-mailbox-scoped
- `dtos-mss` (pushed, auto-included) : `feat/task-175-sse-broker-mailbox-scoped` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-175-sse-broker-mailbox-scoped — aucun changement de contrat attendu (DOD : payload inchangé), branche créée proactivement

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` : branche créée par
  `/start` (auto-inclusion) mais **aucun commit** — le correctif ne touche
  aucun contrat partagé, donc pas de publication NuGet ni de bump consommateur.
  Les trois frontends ne sont pas modifiés (URL, noms d'évènements et forme du
  payload `SseMailEvent` inchangés).
- **DTOs published** : no DTO change
- **Interop published** : no interop change

### Ce qui a été fait

| Fichier | Changement |
|---|---|
| `src/Application/Services/Interfaces/ISseMailEventBroker.cs` | `Subscribe` / `Publish*` / `SubscriberCount` prennent la boîte propriétaire ; `ISseMailEventSubscription` expose `MailboxEmail` |
| `src/Application/Services/Implementation/SseMailEventBroker.cs` | clé de bucket = `MailboxFolderKey(mailbox, folder)` normalisée (trim + lowercase, donc l'insensibilité à la casse de l'ancienne clé `OrdinalIgnoreCase` est conservée) ; fail-close sur publication sans identité ; boucle CAS / `Remove` / `SubscriberCount` portés sur la nouvelle clé ; `[ExcludeFromCodeCoverage]` retiré (la classe est désormais testée) |
| `src/Application/Helpers/MailboxPseudonym.cs` *(nouveau)* | SHA-256 tronqué (8 hex) de l'adresse normalisée — identité journalisable sans donnée identifiante |
| `src/Api/Hubs/MailEnrichmentNotifier.cs` | propage la boîte au broker ; logs pseudonymisés |
| `src/Api/Controllers/V1/MailEventsController.cs` | `Subscribe(email, folder)` où `email` est le claim `mssEmail` validé — même identité que les deux autres brokers, contrat task-022 intact |
| `src/Application/Services/Implementation/ImapService.cs` | 3 sites d'appel passent `userContextInfo.Email` (la boîte réellement synchronisée) |
| `src/Application/Consumers/AddNewMailConsumer.cs` | passe `message.UserContext.Email` — le consumer tourne sur un scope MassTransit sans HTTP context |

**Provenance de l'identité** — vérifié que `UserContextInfo.Email` est bien
renseigné hors requête HTTP : `BackgroundSyncManager` l'initialise sur le scope
de sync (`userContextInfo.Email = userEmail`) et
`BackgroundEnrichmentProcessor.CopyUserContext` le recopie sur chaque scope
worker. Le fail-close ne coupe donc pas silencieusement les notifications de la
sync background.

### Commits

- `api-mail` : `0609b51` fix(sse): key the mail event broker by (mailbox, folder), not folder alone
- `api-mail` : `9e4cc7b` test(sse): cover cross-practitioner isolation of the mail event stream

### Build / tests

Build : **0 erreur, 0 avertissement**.

| Projet | Résultat |
|---|---|
| `mss.mail.application.tests` | 1852 ✓ / 0 ✗ |
| `mss.mail.api.tests` | 575 ✓ / 0 ✗ |
| `mss.mail.domain.tests` | 102 ✓ / 0 ✗ |
| `mss.mail.infrastructure.tests` | 370 ✓ / 0 ✗ |
| `mss.mail.integration.tests` | 262 ✓ / 0 ✗ / 24 ignorés (suite AI — service externe absent) |
| **Total** | **3161 ✓ / 0 ✗** |

> Note d'environnement : `src/Api/bin` était verrouillé par 5 réplicas
> `mss.mail.api` en cours d'exécution (AppHost lancé à 13:56) + Visual Studio.
> Build et tests ont donc été exécutés avec `--artifacts-path` vers un répertoire
> temporaire, sans toucher à l'environnement local du humain. Aucun impact sur le
> code produit.

### Preuve que le test de cloisonnement n'est pas vacuous

La clé de bucket a été temporairement remise en « dossier seul » (comportement
d'avant la task), puis restaurée. Sur ce code, **6 tests échouent** :

- `SseMailEventBrokerTests.Publish_ToAnotherMailboxOnTheSameFolder_ServesNothingToTheOtherMailbox`
- `SseMailEventBrokerTests.PublishTagsUpdated_ToAnotherMailboxOnTheSameFolder_ServesNothingToTheOtherMailbox`
- `SseMailEventBrokerTests.SubscriberCount_IsScopedToTheMailbox`
- `SseMailEventBrokerTests.Dispose_LastSubscriberOfAMailbox_RemovesTheBucket`
- 2 des 4 `MailEventsStreamIsolationIntegrationTests`

### DOD self-check

| Critère | État |
|---|---|
| Build 0 erreur | ✓ |
| Tests 0 échec | ✓ (3161 verts, aucun flaky rencontré sur ce run) |
| Test unitaire de cloisonnement (échoue sur le code actuel — vérifié) | ✓ |
| Test unitaire même boîte / même dossier → les deux reçoivent | ✓ `Publish_TwoSubscribersOfTheSameMailboxAndFolder_BothReceive` |
| Test unitaire publication sans identité → aucun abonné, alerte journalisée | ✓ `PublishEmailsEnriched_WithoutMailboxIdentity_ServesNobodyAndWarns` (+ variante TagsUpdated) |
| Test unitaire bucket retiré après `Dispose` du dernier abonné | ✓ `Dispose_LastSubscriberOfAMailbox_RemovesTheBucket` (assertion sur la table d'abonnés, pas seulement sur `SubscriberCount`) |
| Test d'intégration sur `GET /api/v1/mail/events/stream` (claim `mssEmail`, `?email=` ignoré) | ✓ `MailEventsStreamIsolationIntegrationTests` — 4 tests, assertions sur les octets réellement écrits dans le corps de réponse de chaque praticien |
| Aucune donnée de santé en clair dans les logs du broker | ✓ `BrokerLogs_CarryNeitherHealthDataNorTheMssanteAddress` |
| Aucun changement de contrat | ✓ `SseMailEvent`, noms d'évènements et route inchangés ; 0 fichier frontend modifié |

**Hors périmètre de la forge** — la qualification **AIPD / notification CNIL**
avec le DPO (portée réelle, environnements concernés, fenêtre d'exposition,
nombre de praticiens simultanés) est un livrable **humain** explicitement
distinct du correctif technique. Elle ne figure pas dans la checklist DOD, donc
`/review` ne la bloquera pas : elle reste à la charge du humain.

- **Next step** : /forge-simplify task-175

## Simplify log

- **Repos passed** : `api-mail` (12 fichiers de diff vs `develop`)
- **Applied & committed** : `api-mail` : 1 fichier (`63430f8`)
  - `SubscriberCount(mailbox, folder)` délègue à une surcharge privée
    `SubscriberCount(MailboxFolderKey)` — un seul chemin de comptage, et `Remove`
    réutilise la clé qu'il détient déjà pour sa ligne de log au lieu de
    re-normaliser la paire (double normalisation supprimée).
  - `Normalize` passe à la forme null-conditionnelle.
- **No change** : —
- **Rolled back (validation RED)** : —
- **Skipped (contract/excluded)** : `dtos-mss` (porteur de contrat **et** 0 diff),
  `interop-cda`, `devops`, `psc-proxy-*`, `client-angular`, `client-mobile`,
  `client-blazor`, `sdk`, `host` (non touchés)
- **Build / tests** : ✓ build 0 erreur / 0 avertissement ; SSE 23 ✓, api.tests
  575 ✓, domain 102 ✓, infrastructure 370 ✓

### Findings écartés (hors périmètre du diff)

1. **Duplication de la machinerie d'abonnement entre les trois brokers SSE** —
   `SseNotificationBroker`, `SseSyncProgressBroker` et `SseMailEventBroker`
   portent chacun la même boucle CAS + `ImmutableArray` avec un type de clé
   différent. Un `SubscriptionBroker<TKey, TPayload>` générique retirerait ~3× la
   même logique. Écarté : refactor de deux fichiers **explicitement hors scope**
   de la task (« Hors scope : les brokers notification et sync-progress »).
   Candidat pour une task dédiée.
2. **Journalisation en clair de l'adresse MSSanté par les deux autres brokers** —
   `SseNotificationBroker` et `SseSyncProgressBroker` logguent `userEmail` brut ;
   seul le broker mail est désormais pseudonymisé, ce qui crée une incohérence
   entre frères. Même raison d'écartement (hors scope task). À traiter avec le
   finding 1.
3. **Cinquième implémentation ad-hoc de « SHA-256 tronqué »** — le repo en compte
   déjà quatre (`PatientRepository`, `CrlValidationService`,
   `PatientOppositionGuard`, `UserContextInfo`). `MailboxPseudonym` ne duplique
   donc aucun helper partagé existant, mais consolider les cinq serait un
   nettoyage transverse — hors diff.
4. **SHA-256 évalué même quand le niveau `Information` est désactivé** —
   `MailboxPseudonym.Of` est appelé en argument de `LogInformation`, donc évalué
   systématiquement (le repo a une convention `logger.IsEnabled` pour ce motif,
   cf. task-077). Écarté comme optimisation prématurée : ~200 ns sur une entrée
   de 30 octets, négligeable devant l'écriture DB et l'IO IMAP du même chemin.

### Note d'environnement — flaky pré-existant confirmé

La suite complète `mss.mail.application.tests` sort à **1851 ✓ / 1 ✗** de façon
intermittente sur le flaky PDF export déjà documenté
(`MailExportServiceTests` / `MarkdownPdfRendererTests` — « Could not find the
font with name /F5 in the resource store »). Vérifié indépendant de cette task :
les tests d'export passent **31/31 en isolation**, et la suite complète échoue à
l'identique sur le code **sans** les éditions du simplify pass (2 runs). Couvert
par la formulation du DOD (« hors flaky pré-existants documentés »).

- **Next step** : /sonar task-175

## Sonar log

Projet `healthplatform` — `http://localhost:9001/dashboard?id=healthplatform`
(conteneurs `sonarqube_db` + `sonarqube` redémarrés au début du run : ils étaient
`Exited` depuis ~4 h).

### KPIs qualité (baseline → final)

| Métrique | Baseline (it. 1) | Final (it. 2) | Cible `sonar-targets.yml` | État |
|---|---|---|---|---|
| Bugs | 0 | **0** | 0 | ✓ |
| Vulnerabilities | 0 | **0** | 0 | ✓ |
| Security hotspots | 0 | **0** | (revue humaine) | ✓ |
| Code smells | 6 | **3** | — | ↓ 50 % |
| Reliability rating | A | **A** | — | ✓ |
| Security rating | A | **A** | — | ✓ |
| Maintainability rating | A | **A** | A | ✓ |
| Coverage | 86.6 % | **86.5 %** | 95.0 % | ✗ (cible long terme) |
| Line coverage | 90.3 % | **90.2 %** | — | — |
| Branch coverage | 77.0 % | **77.0 %** | — | — |
| New coverage | 86.2 % | **86.1 %** | — | QG OK |
| Duplication | 0.7 % | **0.7 %** | — | — |
| Dette technique | 14 min | **11 min** | — | ↓ |
| ncloc | 36 217 | 36 217 | — | — |

**Quality Gate : `ERROR`** — une seule condition en échec, `new_violations = 3`.
Les trois autres conditions sont `OK` (`new_coverage` 86.1, `new_duplicated_lines_density`
0.12 %, `new_security_hotspots_reviewed` 100 %).

### Itération 1 → 2 : ce qui a été corrigé

**Findings introduits par task-175 — tous corrigés (3/3, commit `3671229`)** :

| Règle | Fichier | Correction |
|---|---|---|
| `csharpsquid:S103` ×3 | `src/Api/Hubs/MailEnrichmentNotifier.cs` (l. 16, 29, 36) | l'ajout du paramètre `mailboxEmail` poussait les trois signatures au-delà de 150 caractères → un paramètre par ligne |

Une 4ᵉ ligne > 150 caractères a été corrigée de façon préventive dans
`tests/mss.mail.api.tests/.../MailEventsControllerTests.cs` (fabrique `Create`) —
non signalée par Sonar mais même cause.

→ **Zero-new-debt tenu sur le périmètre de cette task** : plus aucun finding
Sonar sur les fichiers du diff task-175.

### Findings restants — dette pré-existante, hors module de la task

| Règle | Fichier | Ligne |
|---|---|---|
| `python:S1481` | `tests/loadtest-k6/report.py` | 62 |
| `python:S1481` | `tests/loadtest-k6/report.py` | 64 |
| `python:S3457` | `tests/loadtest-k6/report.py` | 121 |

**Pourquoi acceptés et non corrigés** — ces trois issues ne sont **pas
introduites par task-175** : `report.py` n'est pas dans le diff
(`git diff --name-only origin/develop...HEAD` → absent) et son dernier commit
`134647b` (task-174, harnais de charge k6) est **déjà sur `develop`**. Elles
apparaissent dans la fenêtre « new code » uniquement parce que la new-code period
du projet a une baseline large (fait connu de cette instance Sonar). Ce sont donc
de la **dette legacy** au sens de la Phase 2 de `agents/sonar.md` → best-effort,
acceptation, hand-off.

Les corriger imposerait de toucher le harnais de test de charge, **un autre
module que celui de cette US** (règle 6 « Isolated scopes ») et d'élargir une PR
de correctif de sécurité avec des changements sans rapport (règle 5, hygiène de
PR). Sur une PR dont l'enjeu est la revue d'un cloisonnement de données de santé,
mélanger du lint Python dégrade la relecture.

→ **Proposition** : une task de housekeeping dédiée sur `tests/loadtest-k6/`
(3 fixes triviaux : 2 variables locales inutilisées + 1 f-string sans champ de
remplacement). À arbitrer par le humain.

### Couverture

86.5 % global contre une cible long terme de 95 %. `sonar-targets.yml` précise
explicitement qu'« un run `/sonar` n'est PAS censé atteindre ces cibles ». Cette
task pousse dans le bon sens : `SseMailEventBroker` passe de
`[ExcludeFromCodeCoverage]` (aucune couverture) à **23 tests unitaires** + 4 tests
d'intégration.

### Conventions alimentées

`conventions/csharp.md` : nouvelle entrée **S103 — Signature > 150 caractères ⇒
un paramètre par ligne** (4 occurrences, origine task-175), avec la commande
`awk` de vérification pré-commit.

- **Itérations** : 2 / 5 (arrêt : plus aucun finding corrigeable dans le
  périmètre de la task)
- **Next step** : /review task-175 (`client-angular` et `client-mobile` non
  touchés → `/lint-angular`, `/lint-mobile` et `/verify-visual` skip clean)

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/126 — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — branche `feat/task-175-sse-broker-mailbox-scoped` créée par `/start` (auto-inclusion) mais **0 commit** : le correctif ne touche aucun contrat partagé. Branche à supprimer au `/merge`.
- `client-angular` / `client-mobile` / `client-blazor` : non touchés (US backend-only, contrat SSE inchangé)
- `devops`, `psc-proxy-*` : managed manually by the human

## Code Review Summary

**Verdict : APPROVED** — 12 fichiers relus, 1 suggestion non bloquante, 0 blocage.

| Axe | Verdict |
|---|---|
| Correctness | ✅ casse/trim conservés sur les deux composants de la clé ; `Remove` réutilise la clé d'abonnement → pas de bucket orphelin |
| Sécurité | ✅ logs pseudonymisés (ni adresse, ni sujet, ni INS, ni contenu) ; validation d'entrée ; `?email=` ignoré (task-022) |
| Architecture | ✅ aligné sur `SseNotificationBroker` ; correctif au niveau de la clé, pas un filtre périphérique |
| Qualité | ✅ pas de code mort, pas de TODO ; `MailboxFolderKey` privé et cohérent |
| Performance | ⚠️ `ToLowerInvariant()` sur les 2 composants → 2 allocations de chaînes par publication (l'ancienne clé n'en allouait aucune via le comparateur `OrdinalIgnoreCase`). Un `IEqualityComparer<MailboxFolderKey>` custom les supprimerait. Déchet Gen0 par évènement — mineur, non bloquant |
| Tests | ✅ 23 unitaires + 4 intégration + 2 contrôleur ; non-vacuité prouvée (6 échecs sur la clé pré-fix) |

**Propriété héritée, non introduite** : le dossier est normalisé en minuscules
dans la clé — deux dossiers IMAP ne différant que par la casse partagent un
bucket. Identique à l'avant-PR (`StringComparer.OrdinalIgnoreCase` sur le
dossier).

**Pistes hors périmètre relevées** (fichiers explicitement « Hors scope » de la
task, candidats à une task dédiée) :
1. Les 3 brokers SSE dupliquent la même machinerie CAS + `ImmutableArray` → un
   `SubscriptionBroker<TKey, TPayload>` générique.
2. `SseNotificationBroker` / `SseSyncProgressBroker` journalisent encore
   l'adresse MSSanté **en clair** — portée conformité PGSSI-S, mérite un arbitrage.
3. Housekeeping `tests/loadtest-k6/report.py` : 3 issues Sonar Python
   pré-existantes (seule cause du Quality Gate `ERROR`).

## Validation finale

- Build : ✓ `api-mail` (0 erreur / 0 avertissement)
- Tests : ✓ `api-mail` — 3169 ✓ / 0 ✗ / 16 ignorés
- Sync `develop` : ✓ `Already up to date` (aucun conflit)
- DOD : ✓ tous les items vérifiables par commande sont satisfaits ; items
  observationnels reportés au Manual Test Plan de la PR
- Code review : ✓ APPROVED
- Quality Gate SonarQube : `ERROR` sur `new_violations = 3` — **3 violations
  antérieures** hors diff (`tests/loadtest-k6/report.py`, task-174, déjà sur
  `develop`). Aucun finding sur les fichiers de cette PR.

## Merged

- **2026-07-28 08:33 UTC** — squash-merge de la PR #126 sur `develop`.
- `api-mail` : merge commit `7cf10ba` (PR #126 fermée) ; branche distante
  `feat/task-175-sse-broker-mailbox-scoped` supprimée, **branche locale conservée**.
- `dtos-mss` : aucune PR (branche vide, 0 commit) ; branche distante supprimée,
  branche locale conservée.
- `client-angular` / `client-mobile` / `client-blazor` : non touchés.
- CI de la PR au moment du merge : `build` **pass** (1 m 32 s), `publish` skipped ;
  `mergeStateStatus: CLEAN`, aucune review non résolue, label `awaiting-human-merge`.

### ⚠️ Merge sans exécution du Manual Test Plan — décision humaine explicite

Le **HAG (CLAUDE.md règle 10) n'a pas été honoré dans sa substance** sur cette
task. Le `## Manual Test Plan` ci-dessus **n'a pas été joué** : le scénario à
**deux praticiens MSSanté distincts** (flux SSE de B silencieux pendant qu'un mail
arrive chez A, et second onglet du **même** praticien A toujours servi) n'a pas
été exécuté avant le merge.

La forge a soulevé le point et demandé l'attestation ; le humain a répondu
« non testé, merge quand même » — **décision assumée et consignée ici** plutôt que
le merge présenté comme validé.

**Ce qui couvre le correctif à ce stade** : build 0/0, suite complète 3169 ✓ / 0 ✗,
23 tests unitaires de cloisonnement + 4 tests d'intégration asserant sur les
**octets réellement écrits dans le corps de réponse** de chaque praticien, et la
**preuve de non-vacuité** (6 tests échouent si la clé redevient « dossier seul »).
Le risque résiduel est donc surtout celui que les tests ne peuvent pas voir :
comportement de bout en bout avec de vrais serveurs IMAP MSSanté, deux sessions
navigateur réelles, et non-régression d'UX temps réel côté client.

**Reste à faire, non couvert par le merge** :
- Rejouer le Manual Test Plan sur `develop` (ou en recette) pour confirmer le
  cloisonnement et l'absence de sur-correction en conditions réelles.
- **AIPD / notification CNIL avec le DPO** — livrable humain distinct, toujours
  ouvert (voir section Conformité).
