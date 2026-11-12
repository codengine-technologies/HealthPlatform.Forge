# E024 — Messagerie premium : traiter, déléguer, boucler — Changelogs

> **Audience** : équipes techniques (ingénierie, backlog, dette)
> **Vue produit** : [E024-messagerie-premium-traiter-deleguer-bouc.md](E024-messagerie-premium-traiter-deleguer-bouc.md)
> **Dernière mise à jour** : 2026-11-12

---

## Historique détaillé des changelogs

### v0.1 — task-453 : un acquittement ne disparaît jamais (api-mail, dtos-mss, client-mobile, weda2)

- **État** : `done`, PRs en attente de merge humain (HAG).
- **PRs** : api-mail [#364](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/364),
  dtos-mss [#63](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/63),
  client-mobile [#123](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/123). client-angular en
  code-only : 4 fichiers non commités sur `feature/nova-mss-weda-integration` (`audit.model.ts` + spec,
  `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`), **à commiter sur TFS avant le merge de
  la PR api-mail**.
- **NuGet** : `HealthPlatform.Dtos.Mss` 588.0.0 → **591.0.0** (`AuditActionType.DocumentWorkStateRelinked = 70`,
  `DocumentWorkStateRelinkSkipped = 71`) ; bump `api-mail` seul.
- **Défaut** : `Mails` → `MailMedicalDocuments` → `BiologyAcks` en `CASCADE`. Un déplacement hors plateforme
  (`DeleteMailsByUidsAsync` puis ré-ingestion), une purge d'UIDVALIDITY (`FolderRepository.SyncUidValidityAsync`) ou
  une suppression/restauration détruisaient acquittements et rattachement manuel. Prouvé par 8 tests d'intégration
  rouges sur `aeee2ba2`.
- **Conception** (ADR `Docs/adr/ADR-2026-11-11-ancrage-etats-de-travail.md`) :
  - `Domain/Rules/DocumentAnchor` : `v1:` + SHA-256(`Message-ID` + `\n` + identité) ; identité = `fp:{empreinte}`
    (HPRIM) ou `cda:{DocumentId}|{SetId}|{Version}` ; pas de clé pour `EMAIL` ni sans `Message-ID` ;
  - `BiologyAcks.AnchorKey`, `MedicalDocumentId` nullable, FK `SET NULL` ; table `ManualPatientAttachments`
    (`UX_…_AnchorKey`, patient `CASCADE`, document `SET NULL`) ; `MailMedicalDocuments.AnchorKey` (index partiel) ;
  - `DocumentWorkStateRelinker` : re-liaison à l'identique à l'ingestion (insertion et promotion, dans la
    transaction) et après la purge de `DeleteMailsByUidsAsync` ; une requête dans le cas courant (union des clés en
    attente) ; > 1 candidat → rien, avertissement + trace `DocumentWorkStateRelinkSkipped` ;
  - traces système après validation (`MailRepository.TraceRelinks`) ; `AuditService.Impute` laisse système un acte
    déclaré système ; `IAuditService` optionnel dans le constructeur DI de `MailRepository` ;
  - migration `20261111120000_AnchorDocumentWorkStates` avec reprise SQL (clé identique à la clé C#, testée).
- **Tests** :
  - intégration `FolderOperationsEndToEndTests.WorkStateAnchoring` : 11 cas (déplacement, UIDVALIDITY,
    corbeille/restauration, destruction puis retour, ordre inverse purge/ingestion, CDA sans INS rattaché à la main,
    détachement, HPRIM, ambiguïté, délégataire) ;
  - migration `AnchorDocumentWorkStatesMigrationTests` (reprise, `confdeltype = 'n'`, aller-retour) ;
  - unitaires `DocumentAnchorTests` (11), `DocumentWorkStateRelinkerTests` (6), `AuditServiceSystemActTests`, contrat
    et rétention d'audit ;
  - mutations M1 à M7, toutes rouges sur l'assertion prévue (M7, détachement, faite à `/review`).
- **Suite complète api-mail** (état fusionné avec `develop`) : domain 221, infrastructure 749, application 4 197, api
  1 376, integration 1 263 — 0 rouge.
- **Sonar** : 1 issue imputable (S3776 sur `RelinkAsync`, complexité 16), corrigée (`RelinkKeyAsync`) ; aucune
  restante. QG projet ERROR inchangé dans ses causes (dette antérieure de la période « new code »).
- **Lint** : weda2 0 erreur sur les fichiers de la task ; mobile hors portée de `ng lint` (fichiers e2e seuls).
- **E2E** : E2E-BIO-004 v1 (mobile, angular) ajouté ; prouvé rouge sur le backend sans re-liaison (mutation M6),
  vert sur le correctif. `/e2e` : mobile 61 verts, angular 78 verts (3 flaky), porte verte sur le catalogue du merge
  à venir. Outil e2e : `message --move`, `message --create --kind bio-hprim`.
- **Limites différées** (suggestions de revue) : re-liaison après purge seulement sur `DeleteMailsByUidsAsync` ;
  re-liaison après purge hors transaction ; unicité `ManualPatientAttachments.AnchorKey` sans upsert SQL ; surcharge
  `IAuditService.TraceSystem` plutôt qu'un `IsSystemAct` posé par l'appelant.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle | Task |
|---|---|---|
| `api-mail/src/Domain/Rules/DocumentAnchor.cs` | identité stable d'un document reçu | task-453 |
| `api-mail/src/Domain/Entities/MailDb/ManualPatientAttachment.cs` | rattachement manuel ancré | task-453 |
| `api-mail/src/Infrastructure/Repositories/MailDb/DocumentWorkStateRelinker.cs` | re-liaison des états orphelins | task-453 |
| `api-mail/src/Infrastructure/Repositories/MailDb/MailRepository.WorkStates.cs` | clé à l'ingestion, re-liaison, traces | task-453 |
| `api-mail/src/Infrastructure/Migrations/MailDb/20261111120000_AnchorDocumentWorkStates.cs` | schéma et reprise | task-453 |
| `dtos-mss/AuditActionType.cs` (70, 71) | actes système de re-liaison | task-453 |
| `api-mail/tests/mss.mail.e2e/E2eMessage.cs` | `message --move`, `--kind bio-hprim` | task-453 |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-12)

- Tasks de l'EPIC : 13 (1 `done`, 12 `todo`).
- Scénarios e2e de l'EPIC au catalogue : 1 (E2E-BIO-004).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | État |
|---|---|---|
| task-453 | Ancrage des acquittements et du rattachement manuel à l'identité stable du document ; re-liaison ; modèle imposé aux tasks 454 à 463 | `done` (PRs #364, #63, #123) |
| task-454 | Marquer un message traité | `todo` |
| task-455 | « À revoir le… » | `todo` |
| task-456 | Vues par nature | `todo` |
| task-457 | « À traiter par » | `todo` |
| task-458 | Notes internes | `todo` |
| task-459 | Bandeau « Vous avez répondu… » | `todo` |
| task-460 | Suivi d'acheminement | `todo` |
| task-461 | Adresse déjà en échec | `todo` |
| task-462 | Relance sans réponse | `todo` |
| task-463 | Suivi de biologie | `todo` |
| task-464 | Mon espace santé complet | `todo` |
| task-465 | Mesurer la charge de la boîte | `todo` |
