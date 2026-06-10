# E011 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Vue produit** : [E011-performance-api-mail.md](E011-performance-api-mail.md)
> **Dernière mise à jour** : 2026-06-10

---

## Historique détaillé des changelogs

### v1.0 — task-068 — IMAP : fetch ciblé et streaming des pièces jointes (2026-06-10)

- **PR** : [HealthPlatform.Api.Mail#90](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/90) — label `awaiting-human-merge`. Branche `feat/task-068-imap-fetch-cible-streaming-pj`. `dtos-mss` : branche auto-incluse sans commit, pas de PR (contrats inchangés).
- **Implémentation** :
  - `ImapService.GetEmailContentAsync` : fetch `BODYSTRUCTURE` + `GetBodyPartAsync` ciblé text/html — plus de `GetMessageAsync` sur le chemin d'affichage.
  - `ImapService.GetAttachmentAsync` : téléchargement de la seule body part visée ; « introuvable » mappé `NotFound` (RFC 7807 → 404).
  - Nouveau `GetAttachmentStreamAsync` + `AttachmentStreamResult` (couche Application, volontairement hors NuGet de contrats) : DB-first, write-back DB ≤ 5 Mo (`MaxDbCacheableAttachmentBytes`), streaming pur sans buffer au-delà ; endpoint `DownloadAttachment` en `FileStreamResult`.
  - Suppressions : unitaire = UID SEARCH + `MoveToAsync`/`CopyToAsync` serveur ; bulk fallback sans capability MOVE = `CopyToAsync` batch (plus de boucle fetch + append).
  - Triple allocation décodage MIME corrigée (3 sites) : `EmailAddressHelper.GetBuffer`, délégation `BackgroundImapService`, refonte `ImapService` ; reste `MailExportService.GetMessageAsync` (périmètre task-077).
- **Tests** : 14 tests unitaires dédiés (`ImapServiceTests` région task-068, assertions comportementales `DidNotReceive GetMessageAsync`), 3 tests endpoint réécrits (`FileStreamResult`, 404, 500). Suites : 2463 unitaires verts ; intégration 230/231 — `ConnectAsyncWithCancellationShouldRespectTokenAsync` flaky **préexistant sur develop** (échoue en suite complète sur arbre propre, passe en isolation).
- **Sonar (zero-new-debt, 2 itérations)** : issues new-code 27 → 0. 18 fixées par le code (S3604 ×7, S3928 ×2, S125 ×2, S1643 ×2, S1905, S1168→try-pattern `[NotNullWhen]`, S3241, S107 ×3 via `BulkDeleteBatch` + `StartSyncAsync(UserContextInfo)`) ; 3 × S107 `[LoggerMessage]` **Accepted** (1 paramètre/placeholder imposé par le générateur, contrat d'audit PGSSI-S task-048/054, justification inline) ; 6 × S3925 **FP** (sérialisation binaire obsolète SYSLIB0051, analyseur 9.9 antérieur) ; 1 bug legacy S3887 **FP** (`StopWords` est un `FrozenSet`). Hotspots new-code : 0. Ratings new-code A/A/A, duplication 0,02 %.
- **Arbitrage humain** (`questions/task-068-sonar-newcoverage.md`) : `new_coverage` 75,8 % < gate 80 % — déficit porté par les merges antérieurs (période new-code figée à la 1ʳᵉ analyse). Option 1+2 : résidu accepté (mandat campagne task-067/E009) + période re-bornée `NUMBER_OF_DAYS=30` (niveau branche `main`).
- **Fixes embarqués hors périmètre strict** : assertion `UserDatabaseName` obsolète depuis PR #75 réalignée (test rouge sur develop) ; rotation token SonarQube + `SONAR_PROJECT_KEY` corrigé dans `.env` (incidents tooling documentés dans la task).
- **Commits** : b1f08ea (feature), 9f722b3 (test #75), 3b02fc2 / 27128d0 / 94eac45 / b2a721b / 33c3463 / dad045c (Sonar new-code), merge develop 8091e17.
- **Limites différées** : libellé d'audit « MOVE » affiché même en fallback COPY (suppression unitaire) ; body parts text+html récupérées en 2 allers-retours séquentiels (batch possible) ; write-back DB sauté pour PJ > 5 Mo (re-téléchargement IMAP au prochain accès).

---

## Annexe A — Cartographie des briques applicatives

| Brique | Chemins touchés (task-068) |
|---|---|
| Endpoint mail / pièces jointes | `src/Api/Controllers/V1/MailController.cs` (DownloadAttachment → FileStreamResult) |
| Service IMAP | `src/Application/Services/Implementation/ImapService.cs` (fetch ciblé, stream, deletes serveur, `BulkDeleteBatch`) |
| Sync background | `src/Application/Services/Implementation/BackgroundImapService.cs`, `BackgroundSyncManager.cs` (`StartSyncAsync(UserContextInfo)`) |
| Helpers MIME | `src/Application/Helpers/EmailAddressHelper.cs` (décodage sans copie supplémentaire) |
| Modèle de flux | `src/Application/Models/AttachmentStreamResult.cs` (nouveau) |
| Contrats internes | `src/Application/Services/Interfaces/IImapService.cs`, `IBackgroundSyncManager.cs` |

---

## Annexe B — Inventaire fonctionnel (2026-06-10)

- Projets de tests : 5 (domain 94, application 1539, infrastructure 346, api 484, integration 231) — 2694 tests au total sur la branche task-068 post-merge develop.
- Qualité projet (SonarQube `healthplatform-api-mail`) : bugs ouverts 0 (1 FP requalifié), vulnérabilités 0, smells 26 (legacy), coverage 79,2 %, duplication 0,6 %, hotspots legacy à revoir 4.
- Backlog EPIC : 9 tasks restantes (todo-task-069 → todo-task-077).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | État | Contribution | RG touchées |
|---|---|---|---|
| task-068 | archivée (PR #90 mergée, squash b686640) | Fetch IMAP ciblé (contenu + PJ), streaming des PJ vers HTTP, deletes MOVE/COPY côté serveur, suppression des triples allocations MIME, cleanup Sonar new-code 27→0 | RG-E011-01 ✅, RG-E011-02 ✅, RG-E011-03 ✅ |

---

*Vue ingénierie — la vue produit (vision, features, conformité) vit dans [E011-performance-api-mail.md](E011-performance-api-mail.md).*
