# todo-task-077.md — Perf exports et allocations : streaming EML/PDF et réduction des copies mémoire

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : optimisation mémoire backend pure (exports,
> sérialisation, allocations chaudes). Aucun changement de contrat ni d'UI.

## Objective

Supprimer le buffering complet en mémoire des exports EML/PDF (un export de
message volumineux alloue aujourd'hui l'intégralité du document en `byte[]`,
avec allocations LOH et risque d'OOM) et corriger les allocations chaudes
identifiées par l'audit (logs construisant des chaînes même quand le niveau est
désactivé, sérialisations redondantes, scopes DI créés un par un pour l'audit
trail).

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/MailExportService.cs:337-339` | Message écrit dans un `MemoryStream` puis `ToArray()` → export complet bufferisé en mémoire | Élevé |
| 2 | `src/Api/Controllers/V1/MailExportController.cs:85` | `File(byte[], ...)` au lieu d'un streaming vers `Response.Body` | Élevé |
| 3 | `src/Application/Services/Implementation/CdaParsingService.cs:459` | `Convert.FromBase64String` de documents complets en mémoire | Moyen |
| 4 | `src/Application/Services/Implementation/CdaParsingService.cs:403,434` | `Parallel.Invoke` + `ConcurrentBag` pour l'extraction de texte PDF — coût de coordination à réévaluer | Moyen |
| 5 | `src/Application/Consumers/AddNewMailConsumer.cs:293` | `string.Join(...Select(...))` évalué dans l'appel de log même si le niveau est désactivé | Moyen |
| 6 | `src/Application/Services/Implementation/AuditBackgroundService.cs:15-40` | Un scope DI + un `AddAsync` par trace d'audit, sans batching | Faible-Moyen |
| 7 | `src/Application/Services/Implementation/TokenValidationService.cs:20-22` | Double `Replace` + padding string par validation de token | Faible |

## Comportement attendu

- Les exports EML et PDF sont **streamés** vers la réponse HTTP (écriture
  directe dans `Response.Body` ou `FileStreamResult` sur un flux non bufferisé) ;
  plus de `ToArray()` du document complet.
- Les arguments de logs coûteux sont gardés derrière `IsEnabled` ou remplacés
  par du logging structuré paresseux.
- L'audit trail persiste par lots (drain du channel en batch, un scope par lot).
- Les manipulations base64/JWT évitent les allocations intermédiaires
  (`Span`/`Convert.TryFromBase64`) lorsque le gain est mesurable.
- Le parsing CDA conserve un résultat strictement identique (les documents CDA
  continuent de transiter par `interop-cda` et la validation Schematron — cette
  US n'en modifie que la mécanique d'allocation, pas la sémantique).

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Export EML : plus de `byte[]` complet — flux streamé (vérifiable : pas de `ToArray()` sur le chemin d'export)
- [ ] Export PDF : idem
- [ ] Fichier exporté strictement identique octet-à-octet à la version pré-US (test de non-régression sur un message de référence)
- [ ] Logs : plus d'évaluation d'arguments coûteux quand le niveau de log est désactivé sur les sites identifiés
- [ ] Audit trail : persistance par lots (test : N traces → << N `SaveChanges`)
- [ ] Unit tests : >= 1 test par service modifié (export, audit batching)
- [ ] Integration test : endpoint d'export EML via le pipeline DI complet (happy path + mail introuvable → ProblemDetails 404, règle 12)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Exporter en EML un mail de test avec pièce jointe volumineuse (>= 20 Mo,
  données anonymisées) : le téléchargement démarre immédiatement, le fichier
  s'ouvre dans un client mail et est identique à l'export pré-US.
- Exporter le même mail en PDF : document conforme.
- Observer le working set du process pendant 5 exports parallèles : pas de pic
  mémoire proportionnel à la taille des messages.
- Vérifier que les traces d'audit continuent d'être enregistrées en base après
  une session d'utilisation normale.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : CDA r2 — la mécanique d'allocation du parsing est optimisée mais la validation (interop-cda + Schematron) et le résultat métier sont strictement inchangés
- **Tracé PGSSI-S** : l'audit trail reste exhaustif — le batching ne doit perdre aucune trace, y compris à l'arrêt de l'application (drain au shutdown) ; durée de conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (inchangé)
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-077-exports-streaming
- `dtos-mss` (pushed, auto-incluse) : feat/task-077-exports-streaming — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `feat/task-077-exports-streaming`)** : `9fac915`

**Findings traités** :
1. ✅ EML : `BuildEmlAsync` retourne le `MimeMessage` (déjà matérialisé par MailKit) ; plus de `MemoryStream` + `ToArray` (2 copies supprimées). Streaming via `StreamingFileResult` → `WriteToAsync(Response.Body)`.
2. ✅ PDF : `WritePdf(..., Stream)` — QuestPDF `GeneratePdf(output)` directement dans `Response.Body`. `StreamingFileResult` gère RFC 5987 (accents).
3/4. ⏸ Évalués et différés (hors DOD) : `Convert.FromBase64String` — documents CDA bornés (MSS ≤ ~10 Mo) et l'API aval (parser interop) exige `byte[]` ; `Parallel.Invoke`/`ConcurrentBag` extraction PDF — coordination justifiée pour 2 extractions indépendantes. Sémantique CDA strictement inchangée.
5. ✅ `string.Join` du log de tagging gardé par `IsEnabled(LogLevel.Information)`.
6. ✅ Audit trail par lots : drain channel (`MaxBatchSize` 100), groupé par contexte de transport (1 scope + 1 `SaveChangesAsync` via `AddRangeAsync` par groupe), **drain final au shutdown** (PGSSI : aucune trace perdue), **fallback unitaire** si un lot échoue (pas de perte des voisines d'une trace empoisonnée).
7. ✅ `TokenValidationService` : `Base64Url.DecodeFromChars` — plus de padding/Replace intermédiaires.

**DOD octet-à-octet** : test EML — le flux streamé == `WriteTo` bufferisé (même API MimeKit). PDF : déviation documentée — QuestPDF horodate les métadonnées (non déterministe inter-générations) ; couvert par les tests de contenu existants (texte extrait, sections).

**Découverte .NET 10** : `BackgroundService` démarre `ExecuteAsync` de façon **asynchrone** — un `StopAsync` immédiat annule la tâche avant exécution du corps. Les tests s'alignent sur le log « started » avant d'agir.

**Validation** : build Release 0 erreur ; suite complète verte (2696+), seul échec = flaky IMAP pré-existante documentée. 9 tests nouveaux/adaptés.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/99 — label `awaiting-human-merge`
- `dtos-mss` : branche `feat/task-077-exports-streaming` sans commit — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante.
- Streaming EML/PDF sans byte[] (StreamingFileResult, RFC 5987) ; identité octet-à-octet EML testée ; déviation PDF documentée (métadonnées QuestPDF horodatées)
- Audit par lots + drain shutdown + fallback unitaire (PGSSI : exhaustivité préservée, testée)
- Findings 3/4 évalués-différés avec justification ; 5/7 corrigés
- Sonar : Quality Gate OK, 0 new-code (2 itérations)

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #99 squash-mergée — commit `930091b` sur `develop`
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27369409431
- Branches locales conservées pour inspection rétroactive (convention /merge)
