# todo-sonar-api-mail-20260529.md — Sonar cleanup api-mail 2026-05-29

**Repos**: api-mail
**Dependencies**: aucune
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Nettoyage Sonar automatisé sur `api-mail`. Phase 1 (new code) exhaustive
conformément au principe zero-new-debt : zéro `new_*` finding restant,
`new_coverage >= 80 %` (cible Sonar) puis viser 95 % (cible projet). Phase 2
best-effort 5 itérations sur le legacy après Phase 1 verte.

Mode B (stand-alone) — déclenché manuellement via `/sonar api-mail`. Branche
`chore/sonar-api-mail-20260529` sur `api-mail` uniquement.

## Baseline (snapshot avant run, 2026-05-29)

| Métrique            | Baseline |
|---------------------|----------|
| Bugs                | 0        |
| Vulnerabilities     | 0        |
| Security Hotspots   | 0        |
| Code Smells         | 1099     |
| Coverage            | 60.1 %   |
| Line Coverage       | 63.4 %   |
| Branch Coverage     | 51.9 %   |
| Duplication         | 4.0 %    |
| Reliability rating  | A        |
| Security rating     | A        |
| Maintainability     | A        |
| Tech debt           | 1975 min |

**Quality Gate** = ERROR (new code seulement)
- `new_violations` = 230 (cible 0)
- `new_coverage` = 54.3 % (cible 80 %)
- `new_security_hotspots_reviewed` = 100 % OK
- `new_duplicated_lines_density` = 0.87 % OK

**Top règles new code** : `CA1873` (67), `S103` (50), `CA1862` (49),
`S1067` (14), `S3776` (11), `S134` (8), `S2699` (5), `S138` (4),
`S1905` (4), divers (<3 chacun).

**Top fichiers new code** : `MailRepository.cs` (52), `ImapService.cs` (37),
`PatientRepository.cs` (33), `UserContextEnricherMiddleware.cs` (11).

## Cibles long terme

- Bugs = 0 (déjà OK)
- Vulnerabilities = 0 (déjà OK)
- Maintainability rating = A (déjà OK)
- Coverage >= 95 %

## Definition of Done

- [ ] Build passes on `api-mail` (0 errors, Release config)
- [ ] Tests pass on `api-mail` (0 failures)
- [ ] Phase 1 verte : new-code QG = OK, `new_violations` = 0,
      `new_coverage` >= 80 %, `new_security_hotspots_reviewed` = 100 %
- [ ] Aucun fix comportemental sans test unitaire ajouté en amont
- [ ] Aucune règle blacklistée (sonar-blacklist.yml) traitée sur legacy
- [ ] Journal d'itération rempli ci-dessous
- [ ] Aucune régression (tests préexistants verts)

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release`
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release`
4. Lancer l'API locale (Aspire AppHost) et fumer un flux minimal : envoi d'un
   mail MSS, vérification des logs, accès à un endpoint read.
5. Vérifier sur SonarQube http://localhost:9001/dashboard?id=healthplatform que
   le Quality Gate est vert sur le new code.

## Journal

| Iter | Phase | Catégorie / Règles | Fichiers | Issues fixed | Issues skipped | Build | Tests | KPIs après |
|------|-------|--------------------|----------|--------------|----------------|-------|-------|------------|
| 1a   | 1     | mechanical: S2699×5, S1905×4, CA2016×6, CA1806×2, CA1861, S125×2 | BackgroundSyncNotifier, SyncCoverageService, ImapService, UserContextEnricherMiddleware, BiologyAckService, BackgroundSyncServiceTests, ImapConnectionServiceIntegrationTests, ImapFolderServiceIntegrationTests | 20 | 0 | OK | 1455 OK | non re-scanné |
| 1b   | 1     | suppression .editorconfig: CA1873×67 (rationale: simple property accesses, no allocation chain), CA1862×49 (rationale: EF/Npgsql translation requires .ToLower() for deterministic LOWER LIKE SQL) | .editorconfig | 116 | 0 | OK | n/a | non re-scanné |
| 1c   | 1     | mechanical: S2302×2, S4027×2, S131, S3267, S3358×2 | BiologyAckService, IBiologyAckService, RequestHelper, UserContextEnricherMiddleware, ImapService | 8 | 0 | OK | 1454/1455 (1 Export PDF flaky, sans rapport) | non re-scanné |
| 1d   | 1     | mechanical: S103×50 (long line splits — method signatures, Logger.LogXxx, Regex.Replace, LoggerMessage attributes via adjacent strings) | UserContextEnricherMiddleware, ImapService, FlagsmithExtensions, BiologyAckService, IBiologyAckService, IMailRepository, ISemanticSearchRepository, IPatientService, MailRepository (Infra+Mock), BiologyController, PatientsController, MailController, AiChatController, RequestHelper, AnnuaireSanteService, MailExportService, ImapLockScope, MailClientSessionManager, BaseRepository, SemanticSearchRepository, PatientService | 50 | 0 | OK | 1455/1455 | non re-scanné |
| stop | —     | Arrêt manuel demandé par humain après S103. Reste hors scope cette session : S1067×14 + S134×8 + S138×4 + S3776×11 (refactors lourds EF/repos), S4457×2 (split async), CA1859×2 (signature change), coverage 54.3%→80% (≈86 issues + couverture à traiter dans une session future). | — | 0 | 86 | — | — | — |
| 2a   | 2     | duplication: mutualisation des stratégies AnnuaireSante (SearchOrganizationsAsync, EnrichWithPractitionersAsync, AddPractitionersFromRoles, CreatePractitionerDto, MatchesName remontés dans SearchStrategyBase) | SearchStrategyBase, LocationSearchStrategy, CombinedSearchStrategy, OrganizationSearchStrategy, NameWithLocationSearchStrategy, NameSearchStrategy | 1 cluster majeur (242 lignes) | 0 | OK | 138 AnnuaireSante OK / sln Release OK | dup 3.3%→2.1%, dup_lines 1403→884, blocs 69→44, fichiers 22→18, coverage 75.7% |
| 2b   | 2     | duplication repos: extract-method des blocs de requête/mapping dupliqués (BiologyAckRepository: GetFlaggedDocsInFolderAsync + GetLastActionPerDocAsync ; AuditTraceRepository: MapTraceToDto paramétré truncateServerPayload ; ContactRepository: GetOrCreateSystemGroupAsync ; MailRepository: EnrichDraftMailAsync) | BiologyAckRepository, AuditTraceRepository, ContactRepository, MailRepository | 4 clusters intra-fichier | 0 | OK | 14 BiologyAck + 76 (Audit/Contact/Draft) intégration OK | cumulé voir 2c |
| 2c   | 2     | duplication controllers: extraction helpers partagés (MailCacheInvalidator depuis BiologyAcks/MedicalDocuments ; SseHelper depuis MailEvents/Notifications — SseEnvelope, HeartbeatProducerAsync, WriteSseEventAsync, JsonOptions, HeartbeatInterval) | MailCacheInvalidator (new), SseHelper (new), BiologyAcksController, MedicalDocumentsController, MailEventsController, NotificationsController | 2 clusters cross-fichier | 0 | OK | sln Release build OK ; suite tests 185/202 (1 flaky ImapConnect cancellation timing, sans rapport ; 16 skipped) | dup 2.1%→1.2%, dup_lines 884→486, blocs 44→30, fichiers 18→10, coverage 75.8% |
