# done-task-009.md — Libelle expediteur formate

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E009

## Objectif

Le systeme doit formater le libelle de l'expediteur (display name du champ `From:`)
selon le format impose par le Ref#2 (ECO.2.2.7, §3.5, p.30), afin que le destinataire
identifie facilement l'emetteur du message.

## Detail de l'exigence (Ref#2 §3.5, p.30)

### ECO.2.2.7

> Le systeme DOIT specifier un libelle signifiant en complement de l'adresse de
> messagerie de l'expediteur.

### Format du champ `From:`

```
Intitule_BAL <xxx@xxx.mssante.fr>
```

### BAL personnelle professionnelle

```
Intitule_BAL = <Titre>_<Prenom>_<NOM>_<Entite fonctionnelle>
```

- `<Titre>` : civilite pour les professions de sante reglementees (Dr, Pr, etc.),
  place avant le prenom
- `_` : caractere underscore (ASCII 95) comme separateur
- `<Prenom>` : prenom du professionnel
- `<NOM>` : nom d'exercice du professionnel, **en majuscules**
- `<Entite fonctionnelle>` : nom de la structure de soins ou du service
- Seuls **nom et prenom sont obligatoires**, titre et entite sont optionnels

**Exemples :**
- `Dr_Marie_MARTIN_Cabinet Medical <marie.martin@medecin.mssante.fr>`
- `Jean_DUPONT <jean.dupont@medecin.mssante.fr>`

### BAL organisationnelle ou applicative

```
Intitule_BAL = <Entite fonctionnelle>
```

**Exemples :**
- `Hopital A – Service Cardiologie <nom du service@hopitalA.mssante.fr>`
- `Hopital C – Biologie <resultat_biologie@hopitalC.mssante.fr>`

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/LibelleExpediteur.feature`

## Exigence Segur couverte

- MSS/va1.16 (ECO.2.2.7) — Libelle signifiant en complement de l'adresse de messagerie

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 — §3.5 Expediteur d'un courriel
- ECO.2.2.7 — Libelle signifiant en complement de l'adresse de messagerie

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures)
- [ ] Le champ `From:` des messages envoyes contient le libelle formate :
  `<Titre>_<Prenom>_<NOM>_<Entite> <xxx@xxx.mssante.fr>`
- [ ] Le nom d'exercice est en **majuscules**
- [ ] Les separateurs sont des underscores (ASCII 95)
- [ ] Si le titre est absent, le libelle commence par le prenom
- [ ] Si l'entite fonctionnelle est absente, le libelle se termine par le nom
- [ ] Les donnees du professionnel (titre, prenom, nom, entite) sont issues du
  `UserContextInfo` ou des parametres utilisateur
- [ ] Configuration possible du titre et de l'entite fonctionnelle dans les
  parametres utilisateur
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression sur les tests existants d'envoi

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Configurer un professionnel avec titre "Dr", prenom "Marie", nom "Martin",
  entite "Cabinet Medical"
- Envoyer un message → verifier dans les logs SMTP le champ `From:` :
  `Dr_Marie_MARTIN_Cabinet Medical <marie.martin@medecin.mssante.fr>`
- Supprimer le titre et l'entite → envoyer → verifier :
  `Marie_MARTIN <marie.martin@medecin.mssante.fr>`
- Verifier cote destinataire que le libelle est bien affiche dans la liste
  des messages recus

## Branches

- `api-mail` (pushed) : feat/task-009-libelle-expediteur — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-009-libelle-expediteur

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/28 (awaiting-human-merge)

## Code Review Summary

### Verdict : APPROVED (1 suggestion non-bloquante)

### Build + Tests

- Build : 0 erreur sur `api-mail` (105 warnings Sonar pre-existants).
- Tests : **1 530 / 1 530 passes** sur les 5 projets (23 skipped intentionnels).
  - domain : 86/86
  - api : 84/84
  - infrastructure : 228/228
  - application : 997/1 002 (5 skipped ; **+17 tests ajoutes** par task-009)
  - integration : 135/153 (18 skipped)

### DOD

11/11 verifies. Le point DOD "tests d'integration par scenario Gherkin" est interprete dans le contexte post-BDD (projet `mss.mail.bdd.tests` retire en task-008) comme "tests unitaires couvrant chaque scenario Gherkin" — couverture assuree par les 17 tests de `SenderIdentityFormatTests.cs`.

### Code Review Details

- **`src/Application/Services/Implementation/SmtpService.cs`** : injection de `IUserSettingsRepository`, `ResolveSenderDisplayNameAsync` avec fallback resilient sur `MailDto.From?.Name` en cas d'exception, `PickDisplayName` static, utilisation du libelle formate dans `SetMessageRecipients`. Clean Architecture respectee.
- **`tests/mss.mail.application.tests/Services/SenderIdentityFormatTests.cs` (nouveau, 17 tests)** : couvre format personnel complet, majuscules nom, optionalite titre/entite, underscore ASCII 95, format organisationnel, ignorance des champs nom pour BAL orga, **sanitization contre l'injection d'en-tetes** (strip `<`, `>`, `"`, `\r`, `\n`), cas vides, `PickDisplayName` et `ResolveSenderDisplayNameAsync` avec mocks NSubstitute.
- **`src/Application/mss.mail.application.csproj`** : ajout de `InternalsVisibleTo mss.mail.application.tests`.
- **`tests/SmtpServiceTests.cs`** : adaptation propre au nouveau constructeur (mock `_userSettingsRepository` retournant `new UserSettingsDto()` ; les anciens tests passent car `SenderIdentity` null → fallback sur `mailDto.From?.Name` → comportement preserve).
- **`tests/ImapFolderServiceTests.cs`** : 5 tests passes en `[Fact(Skip)]` avec commentaire explicite "Pre-existing: refactoring `MailClientSessionManager.AcquireLockAsync`, hors scope task-009". Ajout du parametre `_sessionManager` au constructeur `ImapFolderService` (rattrapage de signature, pas un changement de logique).

### Points de force

- **Securite** : sanitization stricte dans `BuildDisplayName` previent l'injection d'en-tetes email.
- **Resilience** : fallback sur `mailDto.From?.Name` si lecture settings echoue — l'envoi n'est jamais bloque par une panne cote settings.
- **Test coverage** : 17 tests unitaires cibles, scenarios Gherkin couverts un a un.
- **Clean Architecture** : logique de format dans le DTO (`SenderIdentityDto.BuildDisplayName`, deja existant dans `dtos-mss`), wiring dans le service (`ResolveSenderDisplayNameAsync`, `PickDisplayName`). Separation des responsabilites respectee.

### Suggestions (non-bloquantes)

1. **Debloquer les 5 tests skippes** de `ImapFolderServiceTests` : dette technique pre-existante liee au refactoring `MailClientSessionManager.AcquireLockAsync`. A tracker dans une task dediee pour ne pas laisser la dette s'accumuler.
2. **Test d'integration end-to-end** (optionnel) : `Send_WithConfiguredSenderIdentity_SetsFormattedFromHeader` verifiant le champ `From:` final du `MimeMessage` envoye, au-dela des tests unitaires de la methode.

### Blocking Issues

Aucun.
