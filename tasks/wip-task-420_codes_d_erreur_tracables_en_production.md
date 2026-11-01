# todo-task-420.md — Chaque erreur d'api-mail porte un code catalogué, retrouvable en production sans coût sur le chemin nominal

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E021
**EpicTitle**: Analyse des pannes en production
**Priorité**: **2** — en production, une erreur se cherche aujourd'hui au texte libre : son code n'est pas dans le journal, un 500 imprévu n'en a aucun, et les tâches de fond n'en ont jamais.

> **Origine.** Demande humaine du 2026-11-01 : faciliter l'analyse des pannes en production **sans dégrader
> les performances**. Le catalogue d'erreurs du proxy PSC (`psc-auth-proxy`, `src/Api/Errors/ErrorCatalog.cs`)
> a servi d'exemple, pas de modèle à recopier : ses codes numériques (`PROXY-PSC-3010`) sont opaques sans la
> table. Ici, les noms lisibles déjà lus par les clients sont conservés.
>
> **Décision humaine (2026-11-01)** : il n'est **pas nécessaire de journaliser en console**. Le sink Console
> de Serilog est retiré ; les journaux partent vers Seq et OTLP.

## Ce qui est établi

- **Les codes existent mais sont dispersés** : `MailboxErrorCodes` (8 codes, dans `Dtos/MailboxDto.cs`),
  `PscSessionErrorCodes` (3), `MailNotFoundCodes`, `MailUnavailabilityCodes`, des constantes portées par les
  exceptions (`MAIL_DELIVERY_UNCERTAIN`, `IHE_XDM_*`, `MAIL_FROM_NOT_MAILBOX`, `DELEGATE_IDENTITY_UNAVAILABLE`),
  et des chaînes en dur dans le flux IA (`CONVERSATION_NOT_FOUND`, `GENERATION_ERROR`). Il n'en existe aucun
  inventaire. Ces noms sont le contrat que lisent weda2, le mobile et Blazor.
- **Le statut et le code sont choisis à deux endroits** : `GlobalExceptionHandler.Map` choisit le statut selon
  le type d'exception, et le `code` est ajouté à part via `IErrorCoded`.
- **Le code n'est pas dans le journal** : `GlobalExceptionHandler.LogException` écrit « Handled {Status} -
  {Method} {Path} » sans le code. Dans Seq, on ne peut pas filtrer une erreur par son code.
- **Un 500 imprévu n'a aucun code** : la branche `_ =>` de `Map` rend un problem+json sans `code`.
- **Les tâches de fond n'ont pas de code** : synchronisation, enrichissement, consommateurs du bus, envois
  différés journalisent en texte libre (9 `BackgroundService`, 3 consommateurs).
- **La cause amont se perd** : `PscTokenProvider.ReadAsync` ne lit que le statut HTTP du proxy (401, 403, sinon
  « indisponible »), alors que le proxy rend un `code` (`PROXY-PSC-2002`, `PROXY-PSC-4001`, `PROXY-KC-4031`…).
- **Les compteurs ont déjà un modèle** : `Application/Telemetry/AuditMetrics.cs` (Meter statique, compteurs
  `TracesDropped`, `TracesEmitted`…).
- **La version est connue** : `BuildInfoProvider` (task-384) lit `AssemblyInformationalVersionAttribute`.
- **Le sink Console est synchrone** : `Api/Program.cs`, `.WriteTo.Console(outputTemplate: …)`, dans tous les
  environnements. Seq (`SEQ_URL`) et OTLP (`OTEL_EXPORTER_OTLP_ENDPOINT`) sont déjà branchés.
- Le `traceId` est déjà posé sur chaque problem+json (`ProblemDetailsSetup`).

## Objective

Qu'une erreur vue en production — par le médecin, le support ou une alerte — se retrouve **par son code** dans
les journaux, les traces et les compteurs, avec sa catégorie, la version d'api-mail et sa cause amont, et
qu'une fiche dise quoi en penser et quoi faire. **Sans un cycle de plus sur une requête qui réussit.**

### Périmètre

1. **Catalogue unique** des codes d'erreur d'api-mail, en table statique : code (nom actuel conservé), statut
   HTTP, catégorie (session, messagerie, document, annuaire, IA, infrastructure, validation), sévérité, cause
   probable, impact pour le médecin, première action. Tous les codes existants y sont repris **sans
   renommage**. Les exceptions typées portent leur entrée de catalogue ; `GlobalExceptionHandler.Map` y lit le
   statut (règle 12 conservée : mapping par type, jamais par message).
2. **Un code pour toute erreur**, imprévue comprise : `UNEXPECTED_ERROR` pour la branche par défaut,
   `DATABASE_UNAVAILABLE` pour une base injoignable, `REQUEST_CANCELLED` pour le 499, et un code pour chaque
   mapping de `Map` qui n'en a pas aujourd'hui (validation, introuvable, conflit, indisponible, non autorisé…).
3. **Le code dans le journal d'erreur**, au point d'écriture unique (`LogException`) : propriétés structurées
   `ErrorCode`, `ErrorCategory`, `AppVersion`, et `UpstreamCode` quand elle est connue. Message en
   `[LoggerMessage]`.
4. **Les tâches de fond** : chaque `catch` qui journalise une erreur dans un `BackgroundService`, un
   consommateur du bus ou l'envoi différé porte le même `ErrorCode` (et `ErrorCategory`) que le catalogue.
5. **La cause amont, lue seulement en échec** : `PscTokenProvider` lit le `code` du corps du proxy **dans ses
   branches d'erreur uniquement** et le garde en `UpstreamCode`. Le verdict rendu aux clients reste celui
   d'api-mail (`PSC_SESSION_EXPIRED`, `PSC_PROXY_UNAVAILABLE`…) : **aucun `PROXY-…` n'est renvoyé aux clients**.
6. **Un compteur `mss_errors_total`** sur le modèle d'`AuditMetrics`, incrémenté **sur erreur seulement**,
   labels bornés : `code`, `category`, `status`, `route` (modèle de route, jamais le chemin brut).
   **Interdits en label** : boîte, personne, RPPS, identifiant de message ou de patient.
7. **L'attribut `error.type` = code** posé sur l'activité courante (span existante), et son statut mis en
   erreur — **seulement en cas d'erreur**, sans créer de span.
8. **Fiches par code générées** depuis le catalogue (un fichier dans `Docs/`, produit par un test ou un outil
   du build, pas à l'exécution) : code, statut, catégorie, cause probable, impact, première action, requête Seq
   type (`ErrorCode = '…'`).
9. **Retrait du sink Console** de Serilog dans tous les environnements (décision humaine). Les journaux partent
   vers Seq et OTLP comme aujourd'hui.

### Hors périmètre

- Événement « large » par requête réussie, nouvelles spans, échantillonnage : ils touchent le chemin nominal.
- Affichage du code et de la référence dans les clients : **task-421**.
- Reprise des codes du proxy pour affiner les verdicts d'api-mail : seule leur conservation en `UpstreamCode`
  fait partie de cette US.
- Alertes et tableaux de bord sur le compteur : configuration de l'outil de supervision, hors dépôt.

### Points d'attention pour /develop

- **Renommer un code existant casse les trois clients** : interdit. Le test de catalogue le verrouille.
- **Le catalogue ne pousse pas à lever des exceptions** pour des cas nominaux : les `Result` restent la voie
  normale.
- **Sans `SEQ_URL` ni `OTEL_EXPORTER_OTLP_ENDPOINT`**, l'API n'émet plus aucun journal une fois la console
  retirée. Le dire dans la fiche d'exploitation et le README d'api-mail ; vérifier que chaque environnement
  (dont le banc et l'AppHost, dont le tableau de bord lit l'OTLP) configure au moins l'un des deux.
- `MailboxErrorCodes` vit dans `dtos-mss` : le catalogue le **référence**, il ne le déplace pas (aucun
  changement de contrat, aucune publication NuGet).

## Definition of Done

- [ ] Build et tests api-mail verts
- [ ] Catalogue : tous les codes existants repris sans renommage ; test unitaire qui échoue sur un code en
      double, sur un code émis absent du catalogue (réflexion sur `IErrorCoded` et les constantes de codes), et
      sur un code existant renommé (liste figée des codes publiés)
- [ ] Tests unitaires de `GlobalExceptionHandler.Map` : chaque type d'exception rend le statut **et** le code de
      son entrée de catalogue ; la branche par défaut rend `UNEXPECTED_ERROR`
- [ ] Test d'intégration de bout en bout pour une route qui lève une exception imprévue : la réponse réelle est
      un 500 problem+json dont `code` vaut `UNEXPECTED_ERROR`, avec un `traceId` ; vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour un refus métier existant (403 `MAILBOX_PSC_MISMATCH`) : code et
      statut **inchangés** dans la réponse réelle (non-régression du contrat)
- [ ] Test : l'erreur journalisée par `LogException` porte `ErrorCode`, `ErrorCategory`, `AppVersion` en
      propriétés structurées (sink de test Serilog) ; vu rouge
- [ ] Test : un échec dans une tâche de fond (au moins la synchronisation et un consommateur du bus) journalise
      son `ErrorCode` ; vu rouge
- [ ] Test : `PscTokenProvider` garde le `code` du proxy en `UpstreamCode` sur un refus, et **ne lit pas** le
      corps sur un 200 ; le verdict rendu aux clients est inchangé
- [ ] Test : `mss_errors_total` s'incrémente sur erreur avec les labels `code`, `category`, `status`, `route`, et
      **ne s'incrémente pas** sur une réponse réussie ; aucun label hors de cette liste
- [ ] Test : `error.type` posé sur l'activité courante en cas d'erreur, absent sinon
- [ ] Fiches par code générées dans `Docs/` et à jour (le test échoue si une fiche manque ou diffère du catalogue)
- [ ] Sink Console retiré de `Program.cs` ; README d'api-mail : journaux par Seq et OTLP uniquement, au moins
      l'un des deux requis
- [ ] Aucune donnée de santé dans les propriétés ajoutées (INS, NIR, contenu de message, adresse en clair,
      RPPS) : test sur le gabarit et les propriétés
- [ ] **A/B de contrôle au banc** (même tir, même lignée, même base) : p95 et CPU par requête du chemin
      nominal dans le bruit mesuré (~1,4 %) ; résultat consigné dans le `## Develop log`

## Manual Test Plan

1. Lancer api-mail par l'AppHost avec Seq (`SEQ_URL` défini).
2. Provoquer un refus métier connu (carte d'un autre praticien sur la boîte → 403 `MAILBOX_PSC_MISMATCH`).
   Dans Seq, filtrer `ErrorCode = 'MAILBOX_PSC_MISMATCH'` : l'erreur est trouvée, avec sa catégorie et la version.
3. Couper la base (ou PgBouncer) et appeler une route : réponse 503 `DATABASE_UNAVAILABLE` ; Seq la retrouve par
   son code.
4. Arrêter le proxy PSC, ouvrir la boîte : le journal porte le code d'api-mail et, quand le proxy a répondu,
   son `UpstreamCode`.
5. Ouvrir la fiche du code dans `Docs/` : cause probable, impact, première action, requête Seq.
6. Vérifier que la console de l'API n'affiche plus de journaux applicatifs, et que Seq les reçoit toujours.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage d'exploitation de la plateforme
- **Vague Ségur** : hors Ségur — exploitabilité
- **Exigences DSR honorées** : non applicable — aucune fonctionnalité métier ; soutient la disponibilité et le
  diagnostic du service MSSanté
- **INS** : non applicable — aucune donnée patient manipulée ; l'INS reste interdite dans les journaux
- **Authentification PS** : inchangée (PSC / e-CPS) ; seuls les codes de refus sont mieux journalisés
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : le **journal d'audit PGSSI-S est inchangé** (actes imputés, 3 653 jours, règle 14). Cette US
  ne touche que les journaux **techniques** : code d'erreur, catégorie, version, cause amont, sans donnée de
  santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui pour la plateforme ; les journaux techniques ne portent aucune donnée de santé
  (pseudonymisation et masquage existants, task-184)
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle nouvelle ; la boîte n'apparaît jamais en label
  de métrique

## Branches
- `api-mail` (pushed) : feat/task-420-codes-d-erreur-tracables-en-production — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-420-codes-d-erreur-tracables-en-production

## Develop log

- Repos touched : `api-mail`. DTOs : aucun changement (`MailboxErrorCodes` est référencé, pas déplacé). Interop : aucun.
- Commits (branche `feat/task-420-codes-d-erreur-tracables-en-production`) :
  - `d8e8ead0` feat(errors): codes d'erreur catalogués, retrouvables en production
  - `e2b22e46` test(errors): catalogue, journal structuré, compteur, code amont, 500 imprévu de bout en bout
  - `a21b9289` refactor(errors): simplify pass (/simplify)
- Ce qui est livré :
  - **Catalogue** `src/Application/Errors/ErrorCatalog.cs` : 57 entrées (code, statut, famille, cause probable, impact pour
    le médecin, première action). Les 30 codes publiés sont repris **sans renommage** (liste figée par test).
    `PSC_IDENTITY_CONFLICT` sort en 409 (middleware de boîte) et en 403 (jeton PSC) : contrat existant, documenté par
    `AlternateStatus`, non modifié.
  - **Un code pour toute erreur** : `GlobalExceptionHandler.CodeOf` = code porté par l'exception, sinon celui de sa
    branche (`DATABASE_UNAVAILABLE`, `OFFLINE_MODE`, `TENANT_REGISTRY_*`), sinon celui de son statut
    (`UNEXPECTED_ERROR` pour un 500 imprévu). Toujours écrit dans le problem+json.
  - **Journal d'erreur** : contexte `ErrorCode`, `ErrorCategory`, `AppVersion` (normalisée comme `/build-info`),
    `UpstreamCode` autour de la ligne de `LogException`, et autour des 14 `LogError` de fond (synchronisation ×4,
    enrichissement, entretien IMAP, file de fond, consommateurs ×5, rétention d'audit ×2).
  - **Cause amont** : `PscTokenProvider` lit le `code` du corps du proxy **dans ses branches d'échec seulement** (401, 403,
    autres), filtré (`[A-Za-z0-9_-]{1,64}`), porté par `Exception.Data` jusqu'au journal ; jamais rendu au client.
  - **Compteur** `mss_errors_total{code, category, status, route}` (Meter `Mssante.Errors`, enregistré dans
    OpenTelemetry) et **`error.type`** sur la span courante : sur erreur seulement, aux cinq points d'écriture d'une
    réponse d'erreur (gestionnaire d'exceptions, `Problem()` / `IProblemDetailsService` via `Customize`, résultats
    Ardalis, middleware de boîte, limiteur de débit). Une réponse sans code est comptée sous le code de son statut,
    **sans** qu'on ajoute ce code à la réponse.
  - **Fiches** `docs/codes-erreur.md`, générées depuis le catalogue par `ErrorCatalogDocumentTests`
    (`MSS_WRITE_ERROR_CATALOG_DOC=1`), le test échoue si le document diffère.
  - **Sink Console retiré** (`Program.cs`, `appsettings.json`) ; README : Seq et/ou OTLP obligatoires.
- Tests (+40) : `ErrorCatalogTests`, `ErrorReportingTests`, `ErrorCodeReportingTests`, `ErrorCatalogDocumentTests`, cas
  ajoutés à `BackgroundSyncManagerCoverageTests`, `BackgroundTaskQueueTests`, `AddNewMailConsumerTests`,
  `PscTokenProviderTests`. Test d'intégration de bout en bout (règle 1b) dans `MailServerUnavailableEndpointIntegrationTests` :
  vrais contrôleurs et vrai pipeline d'erreurs, IMAP simulé (fournisseur externe) qui lève une exception imprévue → 500
  problem+json `code = UNEXPECTED_ERROR` + `traceId` ; et non-régression : 503 `MAIL_SERVER_UNAVAILABLE` inchangé.
  Capteur partagé `TaggedMeasurements` (testing.shared), classes rattachées à `MailMetricsCaptureCollection` (garde task-291).
- **Preuves par mutation** (code restauré par `cp`, vérifié par grep) — chaque mutation rouge sur le test visé :
  - M1 500 imprévu sans code (comportement d'avant) → `EnrichSync_AnUnexpectedFailure_Returns500WithTheUnexpectedErrorCode` (intégration) ;
  - M2 journal sans contexte d'erreur → 3 tests `TryHandle_*` ;
  - M3 synchronisation journalisée sous un autre code → `StartSyncAsync_WhenWorkerFails_LogsTheFailureWithItsErrorCode` ;
  - M4 refus hors gestionnaire non compté → 2 tests `Customize_*` ;
  - M5 code générique ajouté à la réponse → `Customize_AProblemWithoutException_…_WithoutAddingOneToTheResponse` ;
  - M6 code du proxy jamais lu → `GetAccessTokenAsync_WhenTheProxyRefusesWithACode_KeepsItAsUpstreamCode` ;
  - M7 texte libre accepté comme code amont → 5 tests (filtre, refus de texte libre, valeur trop longue) ;
  - M8 code publié renommé → `All_KeepsEveryPublishedCode_UnderItsName`, `All_ContainsEveryDeclaredCodeConstant` ;
  - M9 statut faux dans le compteur → 2 tests de compteur.
- Local build / test : build 0 erreur 0 avertissement ; api 1 337, application 3 990, intégration 1 099 (+16 ignorés),
  infrastructure 699, domaine 202 — 0 échec, aucun crash (FATAL filtré).
- Contrôles mécaniques 2b : S125 (1 commentaire réécrit), xUnit1045, S4457, xUnit2032 : rien ; S103 : 2 lignes de test scindées.
- **A/B de contrôle au banc** (DoD) — même tireur (poste), même banc mail (cluster `192.168.1.69`, `TOXIPROXY` cluster,
  `LATENCY_MS=96`, `UID_BASE=365`), même registre `mss_registry_loadtest`, scénario `read`, 50 praticiens, 300 req/s,
  5 min, smoke de chauffe identique avant chaque jambe ; jambe A = `origin/develop` `627a0e2e`, jambe B = branche `a21b9289` :

  | | develop | task-420 | Écart |
  |---|---|---|---|
  | CPU moyen par requête (Prometheus, 4 min de plateau) | 11,35 ms | 11,04 ms | −2,8 % |
  | p95 client | 57,9 ms | 54,4 ms | −6 % |
  | Latence moyenne | 37,0 ms | 35,4 ms | −4 % |
  | Débit plateau / erreurs | 300,0 req/s / 0 % | 300,1 req/s / 0 % | = |

  Aucune dégradation du chemin nominal ; l'écart, favorable, est compatible avec le retrait du sink Console mais reste
  proche du bruit. Rapports : `Docs/audits/api-mail-loadtest-ab-task420-{A-develop,B-branche}-2026-11-01.md`. Analyse Seq
  du skill non jouée sur ce contrôle (0 erreur sur les deux jambes).
- Passe qualité (/simplify, 4 relecteurs) — appliqué et re-validé (api 1 337, application 3 990, intégration 1 099) :
  code de branche déduit du statut sauf exception (`CodeOf`), `TagList`, version normalisée, `TaggedMeasurements`
  partagé, localisateur de racine `TrackedSourceScan.RepoRoot`, test tautologique retiré. **Écartés** : helper
  `LogBackgroundError` (gabarit non constant, CA2254) ; middleware unique / passage de tous les écrivains par
  `IProblemDetailsService` (refonte qui toucherait les corps de réponse — piste pour une task suivante) ; enrichisseur
  Serilog global (`AppVersion`, `UNCATALOGUED`) qui toucherait chaque événement ; unification des deux
  `CapturingLogger` (formes différentes) ; compteur dans le filtre MassTransit (double comptage).
- ⚠️ **À lire avec task-421 / task-381** : un 500 imprévu porte désormais `code = UNEXPECTED_ERROR` (exigence de cette DoD).
  L'intercepteur weda2 de task-381 traite tout `code` d'api-mail comme un refus métier expliqué par l'écran MSS : il ne
  notifierait plus ces pannes techniques. task-421 (client-angular) doit l'exclure pour les codes de la famille
  `Infrastructure` (ou la liste des codes génériques). Signalé dans la PR.
- Next step : /sonar task-420

## Sonar log

- Mode A (chaîné), SonarQube 9.9 local, projet `healthplatform-api-mail`, branche de la task.
- Phase 1 (new code) : ✓ **Quality Gate OK**, `new_coverage` = **96,5 %** (cible 95 %), **0 issue** sur le nouveau code.
- Phase 1 — itérations : 2. Itération 1 : 1 code smell `CA1862` (`ErrorCatalogTests`, `ToUpperInvariant() == value`)
  corrigé en `!value.Any(char.IsLower)` (`793ce5ac`) ; consigne créée dans `conventions/csharp.md` (CA1862,
  occurrence 1). Itération 2 : 0 issue.
- Phase 1 — tests ajoutés par /sonar : 0 (couverture déjà au-dessus de la cible).
- Phase 2 (legacy) : sans objet — dette projet à 0 (bugs, vulnérabilités, smells, hotspots).
- Tests des passes de couverture : domaine 202, application 3 990, infrastructure 699, api 1 337 verts ; intégration
  1 096 verts, **3 rouges hors task** : `FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`,
  `GetFolderTodayAsync_Inbox_ShouldReturnTheMessageOfTheDayAsync`, `GetFolderNotSeenTodayAsync_…` — les tests « du jour »,
  rouges entre 00:00 et 02:00 (filtre IMAP `SINCE` en UTC, mémoire du banc), analyses jouées à 00:0x et 00:2x. Verts sur
  la même branche à 23 h (1 099/1 099 en /develop). À rejouer après 02:00 en /review.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 96,2 % | 96,5 % | +0,3 |
| New bugs / vulnérabilités / smells / hotspots | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | = |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet | 97,8 % | 97,9 % | +0,1 |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | = |

## Timings

*(généré par `tools/timing/report.sh --task task-420 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 4.4 s | — | — | — | — |
| /develop | ok | 1 h 08 min | 3 (34 s) | 11 (15 min 51 s) | — | api-mail 3B/11T |
| /sonar | ok | 26 min 32 s | 2 (1 min 31 s) | 10 (16 min 03 s) | 4 (1 min 31 s) | 2 itération(s), api-mail 2B/10T |
| **Total cycle** | | **1 h 35 min** | **5 (2 min 06 s)** | **21 (31 min 55 s)** | **4 (1 min 31 s)** | |
