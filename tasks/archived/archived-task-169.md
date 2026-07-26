# todo-task-169.md — Logging des échecs de désérialisation / model binding (trace claire)

**Repos**: api-mail

## Objective

Quand un payload ne peut pas être désérialisé / lié à son `[FromBody]` (ex.
`"id":""` sur un `Guid` non-nullable — cf. task-168), le backend doit **produire
une trace d'erreur explicite** (champ + raison + exception) au lieu d'échouer
silencieusement.

Contexte : `Program.cs` a `SuppressModelStateInvalidFilter = true` (task-055),
donc une erreur de binding **ne renvoie pas** le 400 auto — l'action tourne avec
le DTO `null` → NRE 500 opaque, sans aucune trace de la cause réelle. Diagnostiquer
task-168 a pris des heures faute de cette trace. Un log clair l'aurait donné en
quelques secondes (« The JSON value could not be converted to System.Guid. Path: $.id »).

## Comportement attendu

1. À chaque requête dont le `ModelState` est invalide après binding, le backend
   **logue au niveau Warning** : action, champ en échec, message d'erreur et,
   si présente, l'exception de désérialisation (message + type) — corrélé par
   `traceId`.
2. **Aucun changement de comportement de réponse** (pas de 400 forcé) — on reste
   sur la décision task-055 ; seul le logging est ajouté. Le passage en **400
   `ProblemDetails`** sur échec de binding (règle 12) est une amélioration
   recommandée mais **hors scope** de cette task (à arbitrer séparément car
   elle modifie le comportement global de tous les controllers).
3. **Aucune donnée de santé en clair** dans le log : logger le **champ** et la
   **raison** de l'échec, jamais la valeur brute du payload (qui pourrait
   contenir INS/adresse/contenu).

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`) — 0 erreur
- [ ] Tests passent (`dotnet test HealthPlatform.Api.Mail.sln`)
- [ ] Un filtre global (`IActionFilter`) logue les entrées `ModelState` invalides (champ + message + exception) au Warning, avant l'exécution de l'action
- [ ] Enregistré globalement (`AddControllers(o => o.Filters.Add<…>())`)
- [ ] Ne logue **jamais** la valeur brute du champ (seulement clé + message d'erreur/exception) — pas de fuite de donnée de santé
- [ ] Test unitaire : un `ModelState` invalide → une entrée de log Warning avec le champ et la raison
- [ ] Non-régression : les tests existants (dont `Create_WithInvalidModelState_ReturnsBadRequest`) restent verts

## Manual Test Plan

- Lancer `api-mail` : `cd Api/Mail && dotnet run`
- Envoyer un `POST /api/v1/Contact` avec un payload invalide (ex. `{"id":""}`)
- Attendu : dans Seq, une entrée **Warning** « Model binding échoué — …CreateAsync champ 'id' : The JSON value could not be converted to System.Guid. Path: $.id … » corrélée au `traceId` de la requête
- Vérifier qu'aucune valeur de payload en clair n'apparaît dans le log

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (transversal)
- **Vague Ségur** : socle — observabilité/robustesse, pas de nouvelle exigence DSR
- **Exigences DSR honorées** : PGSSI-S (journalisation) — amélioration de traçabilité des erreurs
- **INS** : non applicable — on logue la cause technique, jamais la donnée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ajoute une trace d'échec de binding (Warning, corrélée traceId) ; **jamais** de payload en clair (INS/adresse/CDA)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable
- **AIPD / impact RGPD** : inchangé — log technique sans donnée personnelle

## Branches
- `api-mail` (pushed) : feat/task-169-model-binding-logging — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-169-model-binding-logging

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/117 — label `awaiting-human-merge`

## Develop log
- 2026-07-17 — `ModelStateDiagnosticsFilter` (global IActionFilter) logue au Warning les entrées ModelState invalides (action + champ + raison/exception), corrélé traceId, sans valeur brute. Enregistré dans `AddControllers`. Commit e1b7e46.
- Build ✓ 0/0 ; 36 tests ✓ (filtre + ContactController) ; hook ✓. Comportement de réponse inchangé (400 = follow-up séparé). PR #117 en attente merge humain (HAG).

## Merged
- 2026-07-17 — squash-merge sur `develop` (`--i-tested`)
- `api-mail` : 601dc40 (PR #117 fermée)
