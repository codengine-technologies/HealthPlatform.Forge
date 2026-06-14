# todo-task-068-patient-courrier-utc-fix.md — Fix du crash `AddNewMail` sur les courriers patient avec INS (DateTime UTC → timestamp sans time zone)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009

## Objective

Corriger le **bug latent découvert par la campagne task-078** : dans
[MailRepository.cs](Api/Mail/src/Infrastructure/Repository/MailRepository.cs),
le chemin de promotion « courrier patient » (`AddPatientCourrierDocument`,
déclenché quand `MailDto.IsFromPatient == true` **et** `PatientInsMatricule`
est renseigné) stampe :

```csharp
CreatedAt = DateTime.UtcNow   // Kind=Utc
```

dans la colonne `MailMedicalDocuments.CreatedAt`, créée par FluentMigrator en
`AsDateTime()` → **`timestamp without time zone`**. Npgsql refuse d'écrire un
`DateTime` de `Kind=Utc` vers ce type de colonne :

```
System.ArgumentException : Cannot write DateTime with Kind=UTC to PostgreSQL
type 'timestamp without time zone'
```

**Conséquence** : tout `AddNewMail` d'un mail émis par un patient via Mon
Espace Santé et portant une INS lève `DbUpdateException` — le mail n'est
**pas persisté**, le document « COURRIER » n'est pas créé, le rattachement
patient automatique (valeur métier de la distinction pro/patient, task-005)
est silencieusement cassé sur ce chemin.

Cible :

1. **Corriger le stamp** : aligner sur la convention déjà en place dans le
   fichier (`NormalizeUtc` retourne `Kind=Unspecified` ; le reste du fichier
   utilise `DateTime.Now` ou des valeurs normalisées). Le fix attendu est
   minimal — produire un `DateTime` de `Kind` accepté par la colonne
   (Unspecified), sans changer la sémantique temporelle (heure UTC conservée
   si c'est l'intention du site).
2. **Balayer le même pattern** dans `MailRepository.cs` : toute autre
   écriture `DateTime.UtcNow` (Kind=Utc) vers une colonne
   `timestamp without time zone` du même chemin est corrigée à l'identique ;
   les sites hors périmètre sont listés dans la PR sans être modifiés
   (règle 6 — scopes isolés).
3. **Iso-comportement** : aucune autre logique modifiée ; le fix restaure le
   comportement métier prévu (promotion du courrier patient + création/
   réutilisation du `MailPatient`).

Périmètre **petit, mono-repo `api-mail`**, sans impact contrat ni frontend.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). Comportement couvert
par test d'intégration Postgres (le bug n'est reproductible que contre le
vrai type de colonne — le provider InMemory ne valide pas les Kind)._

## Definition of Done

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs hors
      les 3 rouges pré-existants documentés)
- [ ] **Test d'intégration RED → GREEN** (Postgres Testcontainers, écrit
      AVANT le fix — règle 1) : `AddNewMail` d'un `MailDto` avec
      `IsFromPatient = true` + `PatientInsMatricule` factice :
      - [ ] ne lève plus `DbUpdateException` et retourne un `MailId` valide
      - [ ] crée le document promu `Category = "COURRIER"` portant l'INS
      - [ ] crée le `MailPatient` au premier courrier et le **réutilise**
            (même `PatientId`) au second courrier du même patient
- [ ] Le stamp `CreatedAt` du chemin patient-courrier n'écrit plus de
      `DateTime` de `Kind=Utc` (vérifiable :
      `grep -n "DateTime.UtcNow" Api/Mail/src/Infrastructure/Repository/MailRepository.cs`
      → aucun site restant écrivant vers une colonne timestamp-sans-tz sur ce
      chemin)
- [ ] Aucune migration de schéma (le fix est côté code, pas côté colonne —
      la convention du repo est `timestamp without time zone` + Kind
      Unspecified, cf. SearchScenarioTests)
- [ ] Aucune régression : suppression/enrichissement/tags/threads de
      `MailRepository` inchangés (suites task-067 vertes)

## Manual Test Plan

- Lancer le backend via l'AppHost Aspire : `cd Api/Mail/src/AppHost && dotnet run`.
- Avec un compte MSSanté de test, injecter (ou simuler via la boîte de test)
  un mail émis par un **patient Mon Espace Santé** portant une INS de test
  (adresse `*@patient.mssante.fr`).
- Vérifier dans les logs qu'`AddNewMail` aboutit (aucune `DbUpdateException`),
  que le mail apparaît dans la BAL avec la **distinction visuelle patient**
  (task-005) et que le document « COURRIER » est rattaché au patient
  (pastille d'intégration verte).
- Renvoyer un second mail du même patient : vérifier qu'aucun doublon de
  patient n'est créé (même fiche patient rattachée).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — restaure le bon fonctionnement du
  classement des courriers patient MES (distinction pro/patient, task-005).
- **Vague Ségur** : V2 — correctif d'un comportement déjà couvert
  (SC.MSS/UX.25 · ECO.3.1.1, SC.MSS/UX.31 · ECO.3.1.2) ; aucune exigence
  nouvelle.
- **Exigences DSR honorées** : RG-E009-028 / RG-E009-030 (rétablies sur le
  chemin INS) — le fix ne crée pas de nouvelle exigence.
- **INS** : manipulée — l'INS du patient émetteur est déjà persistée comme
  trait du document promu (comportement existant task-005, inchangé) ; les
  tests utilisent exclusivement des **INS factices** (panne de l'écriture,
  pas du traitement).
- **Authentification PS** : inchangée.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR modifié.
- **Tracé PGSSI-S** : inchangé — aucun évènement ajouté ni retiré.
- **Consentement patient** : non applicable — réception, pas d'émission.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement existant ; le fix restaure la
  persistance fiable d'un flux de données de santé (courriers patient).
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, correction
  d'une écriture défaillante d'un traitement existant.

### DOD santé (items applicables)
- [ ] Aucune INS réelle dans les fixtures de test (INS factices uniquement,
      pattern `9xxxxxxxxxxxxxx` de test)
- [ ] Aucune donnée de santé ni INS en clair dans les logs ajoutés/modifiés
      (réutiliser les patterns existants)

## Branches
- `api-mail` (pushed) : fix/task-078-patient-courrier-utc
- `dtos-mss` (pushed, auto-incluse) : fix/task-078-patient-courrier-utc — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `fix/task-078-patient-courrier-utc`)** : `4626f36`

- **Test-first (règle 1)** : 2 tests d'intégration Postgres écrits AVANT le fix, RED confirmé avec l'exception exacte (`Cannot write DateTime with Kind=UTC to PostgreSQL type 'timestamp without time zone'`), GREEN après.
- **Fix** : `CreatedAt = NormalizeUtc(DateTime.UtcNow)` (Kind=Unspecified, heure UTC conservée — convention du fichier).
- **Balayage du pattern (objectif 2)** : `grep DateTime.UtcNow` → 1 seul autre site nu : `ReadReceiptSentAt` (L1465), colonne `AsDateTime()` = même classe de bug latent sur le chemin accusé de réception → corrigé à l'identique. Tous les autres sites passent déjà par `NormalizeUtc`. Aucun site hors périmètre restant.
- **Aucune migration** (fix côté code, conformément au DOD).
- **Dédup patient vérifiée** : 2e courrier du même INS → même `PatientId`, une seule fiche `MailPatients` (le SaveChanges immédiat du chemin patient rend le patient visible — comportement préservé).
- **Conflit anticipé** : la PR #93 (task-070, non mergée) modifie `MailRepository.cs` dans la zone adjacente (GetOrCreate patient) — hunks distincts, merge attendu propre ; à surveiller au squash.

**Validation** : build Release 0 erreur ; suite complète — échecs restants : flaky IMAP documentée + `PatientUseCaseTests.GetMailsByInsWithPagination` qui **échoue à l'identique sur develop pur** (vérifié par checkout develop) — dépendance à une boîte Gmail vivante dont le contenu a dérivé, PAS une régression de ce fix. À ajouter à la liste des rouges environnementaux documentés.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/100 — label `awaiting-human-merge`
- `dtos-mss` : branche `fix/task-078-patient-courrier-utc` sans commit — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante.
- Fix minimal 2 sites (`CreatedAt` patient-courrier + `ReadReceiptSentAt`, même classe de bug), convention `NormalizeUtc` du fichier respectée, aucune migration
- Test-first règle 1 : RED confirmé avec l'exception Npgsql exacte → GREEN ; dédup patient vérifiée ; INS factices
- Rouge environnemental documenté (Gmail pagination — échoue idem sur develop, vérifié)
- Sonar : Quality Gate OK premier scan, 0 new-code issue

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #100 squash-mergée — commit `703d459` sur `develop`
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27373363201
- Branches locales conservées pour inspection rétroactive (convention /merge)
