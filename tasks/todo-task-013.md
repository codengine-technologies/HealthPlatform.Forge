# todo-task-013.md — Detection doublons CDA

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune

## Objectif

Le systeme doit detecter et signaler les documents CDA en doublon lors de la reception
d'un message MSSante, afin d'eviter l'integration multiple du meme document dans le
dossier patient. Le document doublon est recu et stocke normalement (pas de blocage)
mais signale au professionnel.

## Criteres de detection de doublon

Un document CDA est considere comme doublon si un `MailMedicalDocument` existant
partage :
- Meme `DocumentId` (identifiant unique du CDA : `id@root` + `id@extension`)
- **OU** meme combinaison fonctionnelle : `Ins` + `Category` + `Date` + `Title`

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/DetectionDoublonsCda.feature`

## Exigence Segur couverte

- SC.CDA/INT.18 — Verifier coherence de tout document CDA recu (detection doublons)

## References reglementaires

- SC.CDA/INT.18

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Detection automatique des doublons a la reception par `DocumentId` exact
- [ ] Detection des doublons fonctionnels par combinaison `Ins` + `Category` +
  `Date` + `Title`
- [ ] Proprietes `IsDuplicate` (bool) et `DuplicateOfId` (int?) ajoutees au
  `MailMedicalDocument`
- [ ] Le document doublon est recu et stocke normalement (pas de blocage) mais
  signale
- [ ] Indicateur visuel "doublon potentiel" dans la liste des documents et dans
  le detail
- [ ] Le professionnel peut consulter le document existant et comparer
- [ ] Le professionnel peut confirmer ou rejeter le signalement de doublon
- [ ] Blazor : indicateur doublon + lien vers le document existant + action
  confirmer/rejeter
- [ ] Angular : indicateur doublon + lien vers le document existant + action
  confirmer/rejeter
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Recevoir un message avec un document CDA (noter le `DocumentId`)
- Recevoir un second message contenant le meme `DocumentId`
  - Verifier : signalement "doublon potentiel" sur le second document
  - Cliquer sur le lien vers le document existant → verifier la navigation
  - Confirmer "pas un doublon" → verifier que le signalement disparait
- Recevoir un document du meme type, meme patient, meme date mais `DocumentId`
  different
  - Verifier : signalement "doublon potentiel" (correspondance fonctionnelle)
- Recevoir un document totalement nouveau
  - Verifier : pas de signalement
- Repeter sur les deux frontends
