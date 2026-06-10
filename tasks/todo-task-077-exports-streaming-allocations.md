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
