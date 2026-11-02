# E021 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> Vue produit : [E021-analyse-des-pannes-en-production.md](E021-analyse-des-pannes-en-production.md).
> **Dernière mise à jour** : 2026-11-02 (v1.1)

---

## Historique détaillé des changelogs

### v1.1 — Chaque erreur d'api-mail porte un code catalogué, retrouvable en production — task-420

- **Task** : task-420, statut `done`. Run `/forge` 420-421. PR `api-mail` #338, label `awaiting-human-merge`.
  Staging `forge/staging-task-420-421-20261101` (api-mail).
- **Livré (api-mail)** :
  - catalogue `src/Application/Errors/ErrorCatalog.cs`, 57 codes (code, statut, famille, cause, impact, première
    action). Les 30 codes publiés sont repris sans renommage, et une liste figée les verrouille. `PSC_IDENTITY_CONFLICT`
    sort en 409 (middleware) et en 403 (jeton PSC) : `AlternateStatus`, contrat inchangé ;
  - `GlobalExceptionHandler.CodeOf` : code de l'exception, sinon de la branche (`DATABASE_UNAVAILABLE`,
    `OFFLINE_MODE`, `TENANT_REGISTRY_*`), sinon du statut (`UNEXPECTED_ERROR` pour un 500). Toujours écrit dans le
    problem+json ;
  - journal : contexte `ErrorCode`, `ErrorCategory`, `AppVersion`, `UpstreamCode` autour de `LogException` et des
    14 `LogError` de fond (synchronisation ×4, enrichissement, entretien IMAP, file de fond, consommateurs ×5,
    rétention d'audit ×2) ;
  - `PscTokenProvider` : `code` du proxy lu dans les branches d'échec seulement, filtré `[A-Za-z0-9_-]{1,64}`,
    porté par `Exception.Data` ;
  - compteur `mss_errors_total{code, category, status, route}` (meter `Mssante.Errors`) et `error.type` sur la
    span, aux cinq points d'écriture d'une réponse d'erreur ;
  - `docs/codes-erreur.md` généré par `ErrorCatalogDocumentTests` (`MSS_WRITE_ERROR_CATALOG_DOC=1`) ;
  - sink Console de Serilog retiré (`Program.cs`, `appsettings.json`), README « Journaux et erreurs ».
- **Tests** : +40. Intégration (règle 1b) `EnrichSync_AnUnexpectedFailure_Returns500WithTheUnexpectedErrorCode`
  (mutation M1) et `EnrichSync_MailServerUnreachable_KeepsItsPublishedCode`. Mutations M1-M9 toutes rouges.
  Validation /review : domaine 202, application 3 990, infrastructure 699, api 1 337, intégration 1 099 (+16
  ignorés). Les trois tests « du jour » ont été rejoués verts à 01:01, après la fenêtre UTC de minuit.
- **A/B au banc** (read, 50 praticiens, 300 req/s, 5 min) : CPU/requête 11,35 → 11,04 ms (−2,8 %), p95 57,9 →
  54,4 ms, 0 % d'erreur des deux côtés. Rapports `Docs/audits/api-mail-loadtest-ab-task420-{A-develop,B-branche}-2026-11-01.md`.
- **Qualité** : Quality Gate OK, new coverage 96,5 %, 0 issue (1 `CA1862` corrigé, consigne dans
  `conventions/csharp.md`). E2E vert : mobile 57, angular 69 + 1 flaky (E2E-COMPOSE-004, inscrit au registre).
- **Revue** : APPROVED, 2 suggestions — `SetStatus(Error)` posé aussi sur un 4xx (OTel le réserve au 5xx) ; choix
  du code par branche prouvé par test paramétré sur le vrai gestionnaire, sans test d'intégration par branche.
- **Dette / suivi** : l'intercepteur weda2 de task-381 retire le toast générique pour tout `code` d'api-mail ;
  avec task-420, les pannes techniques en portent un. **task-421 doit garder le toast pour les codes techniques
  avant toute livraison de la PR #338.**

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle |
|---|---|
| `Api/Mail/src/Application/Errors/ErrorCatalog.cs` | Catalogue des codes (source des fiches) |
| `Api/Mail/src/Application/Errors/PlatformErrorCodes.cs` | Codes génériques, de branche et de fond ; `ForStatus` |
| `Api/Mail/src/Application/Errors/ErrorReporting.cs` | Compteur, span, contexte de journal, code amont |
| `Api/Mail/src/Application/Telemetry/ErrorMetrics.cs` | Meter `Mssante.Errors`, `mss_errors_total` |
| `Api/Mail/src/Api/ErrorHandling/GlobalExceptionHandler.cs` | `CodeOf`, écriture du code dans le problem+json |
| `Api/Mail/src/Api/ErrorHandling/HttpErrorReporting.cs` | Comptage des réponses d'erreur hors gestionnaire |
| `Api/Mail/docs/codes-erreur.md` | Fiches par code, générées |

---

## Annexe B — Inventaire fonctionnel (2026-11-02)

- 57 codes catalogués, dont 30 publiés avant task-420 ; 9 familles.
- 5 points d'écriture d'une réponse d'erreur instrumentés, 14 journaux d'erreur de fond.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution |
|---|---|---|
| task-420 | done (PR api-mail #338) | Catalogue, code pour toute erreur, journal, compteur, span, cause amont, fiches, retrait de la console |
| task-421 | todo | Code et référence affichés au médecin (weda2, mobile, Blazor) ; E2E-ERROR-001 |
