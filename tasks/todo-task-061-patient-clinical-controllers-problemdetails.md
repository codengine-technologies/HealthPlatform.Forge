# todo-task-061-patient-clinical-controllers-problemdetails.md — Migration controllers patient/clinique vers le GlobalExceptionHandler

**Repos**: api-mail
**Dependencies**: task-055, task-059

## Objectif

Migrer le **cluster patient / clinique** sur le pattern RFC 7807 de task-055 :

- `PatientsController` (~372 lignes, ~10 actions, ~19 `catch`)
- `MedicalDocumentsController` (~281 lignes, ~5 actions, ~10 `catch`)
- `BiologyAcksController` (~177 lignes, ~3 actions, ~9 `catch`)

Pour chaque controller : retirer les `try/catch` boilerplate, lever les
exceptions métier typées (`NotFoundException`/`ValidationException`/
`ConflictException`/`UnavailableException`) pour les erreurs métier, retirer
`[ExcludeFromCodeCoverage]`, couvrir chaque action par ≥ 1 test unitaire.

**Vigilance données de santé** : ces controllers manipulent des INS, des
documents médicaux et des acquittements biologiques. Le `detail` exposé au
client doit rester **générique** sur les 5xx (jamais d'INS/NIR/contenu CDA dans
le message). Les exceptions typées ne doivent pas embarquer de donnée patient
dans leur message.

api-mail uniquement, aucun changement de contrat DTO, frontends inchangés.

## Gherkin

_Pas de `.feature` (BDD déprécié). Comportements couverts par tests unitaires._

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec hors échec pré-existant documenté)
- [ ] `try/catch` boilerplate retiré des 3 controllers
- [ ] Not-found / input invalide → exceptions métier typées (mapping par type)
- [ ] `OperationCanceledException` non ré-attrapée par action
- [ ] `[ExcludeFromCodeCoverage]` retiré des 3 controllers
- [ ] ≥ 1 test unitaire par action (happy path + ≥ 1 mode d'échec typé) pour
      chacun des 3 controllers
- [ ] Aucune string brute / `ErrorResponse` ne subsiste dans ces controllers
- [ ] **Aucune INS / NIR / contenu CDA / donnée patient** dans les `ProblemDetails`
      (vérification explicite sur le path 5xx et sur les messages d'exceptions typées)

## Manual Test Plan

- `cd Api/Mail/src/Api && dotnet run`
- `GET /api/v1/Patients/...` avec un INS inconnu → 404 `problem+json` sans INS dans le corps.
- `GET /api/v1/MedicalDocuments/{guid-inexistant}` → 404 `problem+json`.
- Forcer une erreur sur un acquittement biologie (`BiologyAcks`) → 5xx
  `problem+json` avec `traceId`, **aucun** détail clinique exposé.
- Vérifier en UI MSS que la vue patient / biologie / documents ne régresse pas.

## Conformité santé / Ségur / ANS

Hors couloir Ségur — refactor technique de controllers existants, iso-comportement
métier. **Point de vigilance RGPD renforcé** : non-fuite de DSCP (INS, contenu
CDA, valeurs biologiques) dans les messages d'erreur. Même posture que task-055.

### DOD santé (items applicables)
- [ ] Aucune donnée de santé en clair (INS, NIR, contenu CDA, valeurs bio) dans les `ProblemDetails`
- [ ] Aucune donnée de santé en clair dans les logs corrélés par `traceId`
- [ ] Détail technique réservé aux logs serveur ; message client générique
