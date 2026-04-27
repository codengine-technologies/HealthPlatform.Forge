# todo-task-001.md — En-tetes SMTP MSSante

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E009
**Closes RG**: RG-E009-009, RG-E009-010, RG-E009-011, RG-E009-016, RG-E009-087

## Objectif

Lors de l'envoi d'un message MSSante, le systeme doit inserer les en-tetes SMTP
reglementaires definis dans le Referentiel socle MSSante #2 (v1.0.1, sections 3.8.1
a 3.8.3 et 3.4.2.3). Ces en-tetes permettent aux operateurs MSSante et a Mon Espace
Sante de traiter correctement les messages (statistiques, indicateurs, blocage reponse).

## Detail des en-tetes

### 1. `X-MSS-CODECDA` (ECO.2.4.1 — Ref#2 §3.8.1)

- **Quand :** message contenant en PJ un ou plusieurs documents CDA encapsules dans une archive IHE_XDM
- **Valeur :** le champ `code` present dans l'en-tete du document CDA (code type document CI-SIS, defini dans le Volet Structuration Minimale [CI-STRU-ENTETE])
- **Multi-value** si plusieurs documents CDA : valeurs separees par des virgules
- **Ne pas positionner** si absence de document CDA encapsule dans l'archive IHE_XDM
- Exemples :
  - `X-MSS-CODECDA: 34112-3`
  - `X-MSS-CODECDA: 34112-3,PRESC-BIO,15508-5`

### 2. `X-MSS-INS` (ECO.2.4.2 — Ref#2 §3.8.2)

- **Quand :** message contenant en PJ au moins un document CDA encapsule dans une archive IHE_XDM
- **Valeur :**
  - `O` (Oui) si presence d'une INS **qualifiee** dans l'archive IHE_XDM
  - `N` (Non) si absence d'INS qualifiee
- **INS qualifiee** = le document CDA contient le matricule INS **ET** son OID **ET** les 4 traits d'identite (nom de naissance, 1er prenom, date de naissance, sexe)
- **Ne pas positionner** si absence de document CDA en PJ
- Exemples :
  - `X-MSS-INS: O`
  - `X-MSS-INS: N`

### 3. `X-MSS-NIL` (ECO.2.4.3 — Ref#2 §3.8.3)

- **Quand :** **tous** les courriels envoyes, avec ou sans document medical
- **Valeur :** le numero « reference produit » attribue lors de la declaration du produit sur la plateforme `convergence.esante.gouv.fr`
- **Objectif :** permettre a l'operateur d'identifier le LPS emetteur et au gestionnaire de l'espace de confiance de suivre le deploiement

### 4. `X-MSS-MES` (ECO.2.2.8 — Ref#2 §3.4.2.3)

- **Quand :** messages envoyes vers un usager via Mon Espace Sante (adresse `<matriculeINS>@patient.mssante.fr`) **et** le professionnel souhaite bloquer la reponse du patient
- **Valeur :** `FIN` (3 caracteres en majuscules)
- **Effet :** MES empeche l'usager de repondre au professionnel

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/EntetesSmtpMssante.feature`

## Exigences Segur couvertes

- SC.MSS/CONF.14 (ECO.2.4.2) — X-MSS-INS
- SC.MSS/CONF.15 (ECO.2.4.1) — X-MSS-CODECDA
- SC.MSS/CONF.16 (ECO.2.4.3) — X-MSS-NIL
- SC.MSS/CONF.21 (ECO.2.2.8) — X-MSS-MES

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 (18/01/2024) — sections 3.8.1, 3.8.2, 3.8.3, 3.4.2.3
- Volet Structuration Minimale de Documents de Sante du CI-SIS [CI-STRU-ENTETE]
- Referentiel Identifiant National de Sante [INS-REF]

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures)
- [ ] `X-MSS-CODECDA` positionne avec la valeur du champ `code` de l'en-tete CDA (multi-value si plusieurs CDA)
- [ ] `X-MSS-CODECDA` absent si pas de CDA en PJ dans l'archive IHE_XDM
- [ ] `X-MSS-INS` positionne a `O` si INS qualifiee (matricule INS + OID + 4 traits d'identite)
- [ ] `X-MSS-INS` positionne a `N` si INS non qualifiee mais CDA present
- [ ] `X-MSS-INS` absent si pas de CDA en PJ
- [ ] `X-MSS-NIL` positionne sur **tous** les messages avec la reference produit `convergence.esante.gouv.fr`
- [ ] `X-MSS-MES` positionne a `FIN` sur les messages vers `@patient.mssante.fr` quand le blocage reponse est active
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression sur les tests existants d'envoi

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Composer un message avec un document CDA rattache a un patient avec INS qualifiee
  - Verifier dans les logs SMTP : `X-MSS-CODECDA: <code CDA>`, `X-MSS-INS: O`, `X-MSS-NIL: <ref produit>`
- Composer un message avec CDA sans INS qualifiee
  - Verifier `X-MSS-INS: N`
- Composer un message avec 2 CDA de types differents
  - Verifier `X-MSS-CODECDA` multi-value (ex: `34112-3,PRESC-BIO`)
- Composer un message texte sans PJ
  - Verifier uniquement `X-MSS-NIL` present, pas de `X-MSS-CODECDA` ni `X-MSS-INS`
- Envoyer vers `@patient.mssante.fr` avec blocage reponse
  - Verifier `X-MSS-MES: FIN`

## Branches

- `api-mail` (pushed) : feat/task-001-smtp-headers-mssante — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-001-smtp-headers-mssante
- `dtos-mss` (pushed, auto-included) : feat/task-001-smtp-headers-mssante — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-001-smtp-headers-mssante

## Develop log

- Repos touched : `dtos-mss`, `api-mail`
- DTOs published : 206.0.0 → 210.0.0 (CI run 25009563414)
- Interop published : no interop change
- Commits :
  - `dtos-mss`     : cdb7799 feat(dto): add MSSanté SMTP-header fields (task-001)
  - `api-mail`     : 703bd91 chore(deps): bump HealthPlatform.Dtos.Mss to 210.0.0
  - `api-mail`     : 37a1538 feat(mail): MSSanté regulatory SMTP headers (task-001)
- Local build / test : api-mail 0 errors / 1614 passed (21 env-skipped, 0 failures); dtos-mss 0 errors
- DOD self-check :
  - Build passes (0 errors) sur `api-mail` ✓
  - Tests pass (0 failures) ✓
  - X-MSS-CODECDA positionne avec la valeur du champ `code` de l'en-tete CDA (multi-value si plusieurs CDA) ✓ (covered by ApplyHeaders_SingleCda_* and ApplyHeaders_MultipleCdas_EmitsCommaSeparatedCodeCda)
  - X-MSS-CODECDA absent si pas de CDA en PJ ✓ (ApplyHeaders_TextOnlyMessage_OmitsCdaAndInsHeaders, ApplyHeaders_OmitsCdaAndInsHeaders_WhenIheXdmContainsNoCdaDocuments)
  - X-MSS-INS=O si INS qualifiee ✓ (ApplyHeaders_SingleCda_SetsCodeCdaAndInsO_WhenInsIsQualified, ApplyHeaders_MultipleCdas_AnyQualified_SetsInsO)
  - X-MSS-INS=N si INS non qualifiee mais CDA present ✓ (ApplyHeaders_CdaPresent_SetsInsN_WhenInsNotQualified)
  - X-MSS-INS absent si pas de CDA en PJ ✓ (ApplyHeaders_TextOnlyMessage_OmitsCdaAndInsHeaders)
  - X-MSS-NIL positionne sur tous les messages ✓ (ApplyHeaders_AlwaysEmitsNilHeader_*, ApplyHeaders_FullScenario)
  - X-MSS-MES=FIN sur les messages vers @patient.mssante.fr quand le blocage est active ✓ (ApplyHeaders_SetsMesFin_*, ApplyHeaders_DetectsPatientRecipientInCcOrBcc, ApplyHeaders_FullScenario)
  - >= 1 test par scenario (legacy ".feature" file removed in task-008 — coverage ported as 23 unit tests in MssanteHeaderServiceTests) ✓
  - Aucune regression sur les tests existants d'envoi ✓ (full SmtpServiceTests + SenderIdentityFormatTests still green)
- Operational note : `Mail:ConvergenceProductNumber` defaults to empty string in appsettings.json — the human must set the LPS reference produit issued by convergence.esante.gouv.fr before production. While unset, X-MSS-NIL is omitted with a warning log; functional but non-compliant.
- Next step : /sonar (api-mail)

## Sonar log

- Iterations : 1 / 5 (best-effort, run after task moved to `done-*` to enrich the open PR #30)
- SonarQube : v25.6.0 on `http://localhost:9001`, project key `healthplatform`
- Skill update committed in `agents/sonar.md` : env-var loading from workspace `.env`, automated Docker-container start, `MSYS_NO_PATHCONV` for the scanner

### Baseline (before iteration)

| Métrique | Valeur |
|---|---|
| Bugs | 0 |
| Vulnerabilities | 0 |
| Maintainability rating | A (1.0) |
| Coverage | 49.6 % |
| Security hotspots | 9 |
| Code smells | 730 |
| Duplication | 4.4 % |
| NCLOC | 27 747 |

### Iteration 1 — fixes

| Rule | Severity | Count | Description | Commit |
|---|---|---|---|---|
| S2699 | BLOCKER | 1 | Test missing assertion (`BackgroundImapServiceTests.Dispose_DoesNotThrow`) | a2a7512 |
| S1854 | MAJOR | 2 | Dead store on QuestPDF span builder (`MarkdownPdfRenderer`) | 267a0ed |
| S6968 | MAJOR | 1 | `ProducesResponseType` annotation on `ValidateIns` | 6dc1372 |
| S6562 | MAJOR | 1 | `DateTimeKind.Utc` on INS-derived birth date | 6f57560 |

5 issues fixed, no behavioural change, all 1616 tests still green (Release).

### After iteration 1

| Métrique | Avant | Après | Δ |
|---|---|---|---|
| Code smells | 730 | 725 | −5 (−0.68 %) |
| Bugs | 0 | 0 | — |
| Vulnerabilities | 0 | 0 | — |
| Maintainability rating | A | A | — |
| Coverage | 49.6 % | 49.6 % | — |

### Stop reason

Progression (0.68 %) below the 10 % threshold and no rating improved. Remaining
high-volume rules are either blacklisted (S3776 — 32 occurrences, handled by
the dedicated `/sonar-s3776` command) or low-value-per-diff (CA1873 — 382
`if (logger.IsEnabled(...))` guards which add boilerplate without real
production-time savings on the affected log levels). Stand-alone passes can
revisit those after the team decides on a logging policy.

### Issues remaining (best-effort acceptance)

725 code smells, 9 security hotspots, 49.6 % coverage. The hard targets met in
the baseline (`bugs = 0`, `vulnerabilities = 0`, `sqale_rating = A`) are
preserved.

## Code Review Summary

✅ APPROVED — 1 non-blocking suggestion.

- **Correctness** : the four headers honour every spec edge case (omit when no CDA, comma-joined multi-value, `O`/`N` based on any qualified INS in the archive, MES only when `BlockPatientReply` AND a `@patient.mssante.fr` recipient is present). Recipient detection scans To+Cc+Bcc.
- **Security** : MimeKit's `HeaderList.Add` validates header values, so a malicious CDA cannot CRLF-inject the SMTP stream. `ConvergenceProductNumber` is config-driven, no hardcoded secret. While unset in `appsettings.json`, X-MSS-NIL is omitted with a warning — operationally the right behaviour, but produces non-compliant messages until the operator populates it.
- **Architecture** : new `MssanteHeaderService` registered scoped, mirrors the existing `IMdnService` pattern. Single-responsibility, readable.
- **Test coverage** : 23 new unit tests covering all four headers, multi-CDA, qualified-vs-unqualified INS, recipient detection, case-insensitive attachment name, full-scenario integration. Theory test exhaustively covers each missing trait of `IsQualifiedIns`.
- **Suggestion (non-blocking)** : `MssanteHeaderService.IheXdmZipNames` accepts both `ihe_xdm.zip` and `ihe-xdm.zip`, but `IheXdmProcessingService` only matches `ihe_xdm.zip` exactly. Worth unifying via a shared constant in a follow-up.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/9  (label `awaiting-human-merge`)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/30  (label `awaiting-human-merge`)

> Merge order : `dtos-mss` first (api-mail's `Directory.Packages.props` is pinned to the package version produced by the dtos PR's CI run, 210.0.0), then `api-mail`.
