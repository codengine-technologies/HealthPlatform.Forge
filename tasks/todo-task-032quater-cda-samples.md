# todo-task-032quater-cda-samples.md — Samples CDA zip files pour tester CdaParsingService

**Repos**: api-mail
**Dependencies**: done-task-032bis-fhir-mock + 5 zips IHE-XDM anonymisés fournis par le métier
**Epic**: E009

> **Status** : **GATED MÉTIER** — cette US est en attente de la livraison de 5 zips CDA samples anonymisés par le métier. Tant que les samples ne sont pas dans `tests/mss.mail.integration.tests/Resources/cda-samples/`, l'US ne peut pas démarrer.

## Objectif

Embarquer 5 à 10 zips IHE-XDM représentatifs dans le repo et les utiliser pour tester `CdaParsingService` + `IheXdmProcessingService`, afin de retirer 1 `[ExcludeFromCodeCoverage]` posée à task-032 :
- `application.Services.Implementation.CdaParsingService` (382 LOC)
- Indirectement `application.Services.Implementation.IheXdmProcessingService` (45 LOC)

→ Total potentiel : **~427 LOC** réintégrées au dénominateur de couverture.

US **technique / dette / outillage qualité** — aucun nouveau comportement métier.

## Demande métier (préalable à `/start`)

Pascal, peux-tu fournir 5 zips IHE-XDM anonymisés (1 par catégorie) dans le repo `tests/mss.mail.integration.tests/Resources/cda-samples/` :

1. **`biology.zip`** — un compte-rendu de biologie (LOINC biologie)
2. **`consultation.zip`** — un compte-rendu de consultation
3. **`imaging.zip`** — un compte-rendu d'imagerie
4. **`hospitalization.zip`** — un compte-rendu d'hospitalisation
5. **`prescription.zip`** — une prescription médicamenteuse

Optionnels (bonus, augmentent la couverture des paths edge) :
- `attachments.zip` — zip avec pièces jointes binaires (PDF encapsulé)
- `unstructured.zip` — zip avec UnStructuredDocument PDF
- `malformed.zip` — zip mal formé pour tester le parsing en erreur

**Sources possibles** :
1. ANS MOTCO2 (outil de test éditeurs) — peut générer des zips de test
2. Métier interne — Pascal a indiqué pouvoir fournir des samples anonymisés
3. Régénération synthétique via la lib `Interop.Cda.Parser` + un builder de test

Aucune donnée nominative dans les zips — anonymisation complète des INS, noms, dates de naissance, OIDs sensibles.

## Périmètre

### Refactor production (0 fichier — pas de refactor nécessaire)

`CdaParsingService.ParseIheXdmZip(byte[] zipBytes, CdaParseOptions options = All)` accepte déjà des `byte[]` — les tests peuvent passer le contenu du fichier zip directement. Pas de DI à modifier.

### Test harness (≥ 5 fichiers tests + 5 zips ressources)

- `tests/mss.mail.integration.tests/Resources/cda-samples/*.zip` — fichiers binaires marqués `<EmbeddedResource>` ou `<Content CopyToOutputDirectory="PreserveNewest">` dans le csproj.
- `CdaParsingTests.cs` — 1 test happy path par catégorie (biology / consultation / imaging / hospitalization / prescription) + 1 test edge (malformed → exception attendue) + 1 test `CdaParseOptions.Metadata` (skip transformation HTML XSLT, déjà introduit en task-014).
- Vérifier les fields critiques extraits : INS, codeCDA `<ClinicalDocument code>`, date document, titre, narratif HTML (présent ou skippé selon options).

## Cibles chiffrées

À l'issue de cette US :

- **1 `[ExcludeFromCodeCoverage]` retirée** (`CdaParsingService`)
- **≥ 70 % line coverage** sur `CdaParsingService` (mesure cobertura per-class)
- **0 régression** sur la suite api-mail
- **Tests d'intégration parsing CDA** : ≥ 7 tests (5 catégories + malformed + Metadata-only)

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure), incluant les nouveaux tests parsing CDA
- [ ] ≥ 5 zips CDA samples présents dans `tests/mss.mail.integration.tests/Resources/cda-samples/`
- [ ] Tous les zips sont anonymisés (pas d'INS / nom / date de naissance réels — vérification grep + lecture humaine au PR)
- [ ] csproj configuration : `<Content Include="Resources\\cda-samples\\*.zip" CopyToOutputDirectory="PreserveNewest" />` ou `<EmbeddedResource>`
- [ ] `[ExcludeFromCodeCoverage]` sur `CdaParsingService` retirée (et le commentaire `// reason: XML/zip parsing sans samples` supprimé)
- [ ] ≥ 70 % line coverage sur `CdaParsingService` (cobertura per-class report dans le body PR)
- [ ] ≥ 7 tests d'intégration parsing CDA (1 par catégorie + malformed + Metadata-only)
- [ ] Aucune régression Sonar (code_smells / hotspots / ratings) sur api-mail

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreur
3. `ls tests/mss.mail.integration.tests/Resources/cda-samples/` → ≥ 5 zips visibles
4. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release --collect:"XPlat Code Coverage" --settings:codecoverage.runsettings`
5. Vérifier le rapport cobertura : `CdaParsingService` ≥ 70 % line.
6. Smoke run : envoyer un mail avec une PJ CDA réelle sur l'API locale et vérifier que le parsing produit le résultat attendu (INS extraite, narratif rendu, etc.) — preuve que les samples sont représentatifs du runtime.

## Notes

- Issue du découpage **Option B (2026-05-07)** de la US d'origine `task-032bis-test-harness`. Le Chantier 2 (FhirClient mock) est livré dans `task-032bis-fhir-mock`.
- US sœur : `task-032ter-greenmail-fixture` (Chantier 1, mode `no-code`).
- Pas de `/start` tant que les samples ne sont pas dans le repo.
