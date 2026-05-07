# todo-task-032bis-test-harness.md — Test harness pour retirer les [ExcludeFromCodeCoverage] de task-032

**Repos**: api-mail
**Dependencies**: done-task-032
**Epic**: E009

## Objectif

Monter l'infrastructure de test manquante pour retirer les 9
`[ExcludeFromCodeCoverage]` posés à task-032 (Option A du fork report
2026-05-06) et atteindre les seuils 80 % line / 70 % branch sur le
**dénominateur complet** (sans exclusions). C'est la suite naturelle de
task-032 et la finalisation du filet de sécurité avant `task-033`
(cleanup Sonar massif).

US purement **technique / dette** — aucun nouveau comportement métier.
Rattachée à E009 via la section "KPIs Sonar & Qualité".

## Périmètre — 3 chantiers harness

### 1. Mock IMAP server (GreenMail wrapper Aspire)

Stand-up un serveur GreenMail (ou équivalent : MailHog, embedded MailKit
test server) orchestré par Aspire dans la suite `mss.mail.integration.tests`.
Préparer un fixture qui seede des mailboxes connues (INBOX, Sent, Drafts,
Trash, Junk) avec des mails représentatifs (text-plain, multipart, avec
pièces jointes, avec entêtes MSSanté).

Couvre, après retrait des `[ExcludeFromCodeCoverage]` :
- `application.Services.Implementation.ImapService` (~1 233 LOC)
- `application.Services.Implementation.BackgroundImapService` (~415 LOC)
- `application.Services.Implementation.ImapFolderService` (~390 LOC)
- `application.Services.Implementation.ImapConnectionService` (~232 LOC)

→ Total potentiel : ~2 270 LOC à reprendre en couverture.

### 2. Mock FhirClient HTTP

Injecter un `HttpMessageHandler` dans le `FhirClient` instancié par
`AnnuaireSanteService` (refactor léger : passer le handler par DI ou via
factory). Le mock branche des fixtures FHIR JSON (Bundle Practitioner,
Bundle PractitionerRole, Bundle avec OperationOutcome erreur) sur les
URL attendues.

Couvre :
- Les 7 stratégies AnnuaireSante × `ExecuteAsync` (~900 LOC cumulé)
- `application.Services.Implementation.AnnuaireSante.AnnuaireSanteService.SearchAsync`
  paths complets (succès, erreur FHIR, exception générique)

→ Total potentiel : ~1 150 LOC à reprendre.

### 3. Samples CDA zip files

Embarquer 5 à 10 zips IHE-XDM représentatifs dans
`tests/mss.mail.integration.tests/Resources/cda-samples/` :
- 1 compte-rendu de biologie (LOINC biologie)
- 1 compte-rendu de consultation
- 1 compte-rendu d'imagerie
- 1 compte-rendu d'hospitalisation
- 1 prescription médicamenteuse
- (optionnel) 1 zip avec pièces jointes binaires (PDF encapsulé)
- (optionnel) 1 zip avec UnStructuredDocument PDF
- (optionnel) 1 zip mal formé pour tester le parsing en erreur

Source : à fournir par le métier OU récupérer depuis un MSSanté de test
(le métier a indiqué qu'il pouvait fournir des samples anonymisés).

Couvre :
- `application.Services.Implementation.CdaParsingService` (~382 LOC)
- Indirectement `application.Services.Implementation.IheXdmProcessingService` (~45 LOC)

→ Total potentiel : ~425 LOC à reprendre.

### Hors scope

- **OCSP responder mock** (X.509 chain validation pour OCSP/CRL) — gardé
  exclu (`OcspValidationService`, `CrlValidationService`). Faible enjeu et
  coût de mise en place élevé. À traiter en US séparée si nécessaire.
- **Mock OpenAI HTTP** (`AiTextService`, ~142 LOC) — couvert si on ajoute
  un `IHttpClientFactory` test infra ; à arbitrer pendant l'US.
- **PdfPig output validation** (`MarkdownPdfRenderer`, ~339 LOC) — gardé
  exclu sauf si une stratégie golden-PDF est validée par le métier.

## Cibles chiffrées

À l'issue de task-032bis (sur le dénominateur **complet**, sans exclusions
posées à task-032) :

- **Line coverage ≥ 80 %**
- **Branch coverage ≥ 70 %**

Au moins 8 des 9 `[ExcludeFromCodeCoverage]` posés à task-032 sont retirés
(`OcspValidationService` peut rester exclu — voir hors scope).

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure)
- [ ] GreenMail (ou équivalent) wrapper Aspire installé et orchestré dans
      `mss.mail.integration.tests` ; ≥ 1 fixture mailbox seedée
- [ ] Mock `HttpMessageHandler` pour `FhirClient` injectable et utilisé par
      les tests des 7 stratégies AnnuaireSante
- [ ] ≥ 5 zips CDA samples embarqués dans
      `tests/mss.mail.integration.tests/Resources/cda-samples/`
- [ ] ≥ 8 des 9 `[ExcludeFromCodeCoverage]` posés à task-032 retirés
      (`OcspValidationService` peut rester exclu)
- [ ] Line coverage ≥ 80 % (cobertura, pondérée par LOC) sur dénominateur complet
- [ ] Branch coverage ≥ 70 % (cobertura, pondérée par LOC) sur dénominateur complet
- [ ] Body de PR contient les KPIs avant/après (vs task-032 livré au moment
      du `done-`)
- [ ] Body de PR contient la liste des exclusions retirées + les exclusions
      restantes (avec raison)

## KPIs (à publier dans le body de PR — repris par `/tech-writer` pour E009)

```
### Test harness — task-032bis

| Catégorie                             | task-032 livré | task-032bis livré |
|---------------------------------------|----------------|-------------------|
| Line coverage (denom complet)         |     ~78 %      |     ≥ 80 %        |
| Branch coverage (denom complet)       |     ~?? %      |     ≥ 70 %        |
| Exclusions [ExcludeFromCodeCoverage]  |       9        |       ≤ 1         |
| Tests d'intégration IMAP              |     0          |     NN            |
| Tests d'intégration FhirClient HTTP   |     0          |     NN            |
| Tests parsing CDA                     |     0          |     NN            |
```

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur
3. `dotnet test HealthPlatform.Api.Mail.sln --collect:"XPlat Code Coverage"
   --settings:codecoverage.runsettings`
4. Vérifier line ≥ 80 % et branch ≥ 70 % sur le rapport mergé.
5. Smoke test : démarrer le backend en local (`dotnet run --project src/mss.mail.api`)
   et vérifier que rien n'est cassé par les refactors d'injection
   `HttpMessageHandler` (`GET /api/health` → 200, recherche Annuaire Santé
   sur prod → 200 sans dégradation).

## Notes

- Cette US est l'extension ingénierie naturelle de task-032 (Option B du fork
  report 2026-05-06).
- Si le métier ne fournit pas 5 zips CDA (chantier 3), l'US peut livrer
  partiellement : laisser `CdaParsingService` exclu et écrire `questions/`
  pour escalader la demande de samples.
- `task-033` (cleanup Sonar massif) bénéficie directement de ce harness :
  les classes IMAP / FhirClient / CDA seront alors couvertes et le critère
  "0 régression" sur 20 itérations Sonar sera plus solide.
