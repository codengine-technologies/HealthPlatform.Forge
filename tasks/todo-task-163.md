# todo-task-163.md — Recherche annuaire santé FHIR : crash sur ressources dupliquées dans le bundle

**Repos**: api-mail
**Dependencies**: —

## Objective

Corriger un crash de la **recherche annuaire santé (Annuaire National des
Professionnels, MSSanté)** côté backend : dès qu'un bundle FHIR renvoyé par
l'annuaire contient **deux ressources de même `Id`** (cas normal — une même
structure `Organization` référencée par plusieurs `PractitionerRole`), le
parsing lève une `ArgumentException` et toute la recherche échoue en 500.

Reproduit depuis le client mobile (recherche annuaire), mais le défaut est
dans `mss.mail.application` et impacte **tous les frontends** (Blazor, Angular,
mobile) qui consomment `DirectoryController.SearchPractitionersAsync`.

### Cause racine (identifiée)

`FhirBundleParser` construit ses index de ressources avec `ToDictionary(id, …)`,
qui **jette `ArgumentException: An item with the same key has already been
added`** sur clé dupliquée. Trois sites fragiles :

- [FhirBundleParser.cs:79](../../Api/Mail/src/Application/Services/Implementation/AnnuaireSante/Parsers/FhirBundleParser.cs#L79) — `Organization/{Id}` (**site du crash observé**, clé `Organization/001-01-122550`)
- [FhirBundleParser.cs:73](../../Api/Mail/src/Application/Services/Implementation/AnnuaireSante/Parsers/FhirBundleParser.cs#L73) — `Practitioner/{Id}`
- [FhirBundleParser.cs:149](../../Api/Mail/src/Application/Services/Implementation/AnnuaireSante/Parsers/FhirBundleParser.cs#L149) — `Organization/{Id}` (2e méthode)

Trace : `AnnuaireSanteService.SearchAsync` → `CombinedSearchStrategy.ExecuteDirectAsync`
→ `FhirBundleParser.ParsePractitionerRoleBundle` → `ToDictionary` → `ArgumentException`.

Un doublon d'`Id` dans un bundle annuaire est **légitime** (plusieurs
`PractitionerRole` pointant la même `Organization`). Le parser doit être
tolérant, pas crasher.

## Comportement attendu

1. **Robustesse au doublon** : un bundle contenant plusieurs ressources
   `Practitioner`/`Organization` de même `Id` est parsé sans exception ; la
   déduplication retient une occurrence par `Id` (premier gagnant — les
   occurrences d'un même `Id` sont réputées équivalentes en données annuaire).
2. **Recherche fonctionnelle** : la recherche qui déclenchait le crash
   (`Organization/001-01-122550` dupliquée) renvoie désormais les praticiens
   attendus.
3. **Pas de fuite / mapping propre** : si une autre erreur FHIR imprévue
   survient, elle sort en `ProblemDetails` (RFC 7807, règle 12) via le
   `GlobalExceptionHandler`, sans stack trace ni détail technique côté client.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`) — 0 erreur
- [ ] Tests passent (`dotnet test HealthPlatform.Api.Mail.sln`) — 0 échec
- [ ] Les 3 `ToDictionary(id, …)` de `FhirBundleParser` (lignes 73, 79, 149) sont tolérants aux `Id` dupliqués (dédup premier-gagnant, ex. `GroupBy(...).ToDictionary(g => g.Key, g => g.First())` ou équivalent)
- [ ] Test unitaire `FhirBundleParser` : bundle avec **`Organization` de même `Id` en double** → parsing OK, 0 exception (reproduit puis couvre `An item with the same key has already been added`)
- [ ] Test unitaire : bundle avec **`Practitioner` de même `Id` en double** → parsing OK
- [ ] Test d'intégration `DirectoryController.SearchPractitionersAsync` : la recherche renvoie 200 sur un bundle à structures dupliquées (plus de 500)
- [ ] Aucune donnée en clair non nécessaire dans les logs ; erreur résiduelle éventuelle en `ProblemDetails` (règle 12)

## Manual Test Plan

- Lancer `api-mail` : `cd Api/Mail && dotnet run`
- Depuis un frontend (mobile ou Blazor), lancer une recherche annuaire MSSanté qui renvoie un praticien exerçant dans une structure référencée plusieurs fois (cas `Organization/001-01-122550`)
- Attendu : la liste des praticiens s'affiche, **aucune 500** « Erreur interne lors de la recherche FHIR »
- Vérifier les logs Seq : plus d'`ArgumentException` sur `FhirBundleParser`, la requête `SearchPractitioners` sort en 200

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (transversal — recherche annuaire partagée par tous les frontends)
- **Vague Ségur** : socle MSSanté — correctif de robustesse, pas de nouvelle exigence DSR
- **Exigences DSR honorées** : MSSanté (recherche Annuaire National des Professionnels) — fiabilisation ; pas de nouvelle exigence
- **INS** : non applicable — annuaire **professionnel** (Practitioner/Organization), aucune donnée patient ni INS
- **Authentification PS** : e-CPS / PSC — inchangée
- **Habilitations** : inchangées (recherche annuaire déjà autorisée)
- **Interop CI-SIS** : **FHIR R4** — ressources `Practitioner`, `PractitionerRole`, `Organization` (bundle Annuaire Santé ANS) ; parsing robustifié, aucun changement de contrat
- **Tracé PGSSI-S** : l'échec de recherche reste journalisé côté serveur (canal existant) ; corrélation `traceId`
- **Consentement patient** : non applicable
- **Référentiels métier** : identifiants annuaire ANS (RPPS/structure) — inchangés
- **Hébergement HDS** : non applicable — donnée annuaire professionnelle, pas de DSCP patient
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement
