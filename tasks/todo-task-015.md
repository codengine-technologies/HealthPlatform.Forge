# todo-task-015.md — Gestion messages suppression/modification documents

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: todo-task-006 (annule et remplace — cote expediteur)

## Objectif

Le systeme doit gerer les messages de suppression ou de modification de documents
medicaux deja integres. Lorsqu'un professionnel recoit un message indiquant qu'un
document precedemment transmis doit etre supprime ou modifie, le systeme doit
identifier le document concerne et informer le professionnel.

Cette US est le **cote recepteur** de l'US task-006 (annule et remplace, cote
expediteur). Elle couvre egalement les suppressions pures (sans remplacement).

## Detection des messages de gestion

Un message est identifie comme suppression/modification si :

### Message "annule et remplace" (lien avec US task-006)
- Objet contenant `[Annule et remplace]`
- En-tetes `In-Reply-To` / `References` pointant vers le `Message-ID` du message
  original (threading RFC 5322 — ECO.2.2.1/2.2.2)
- Presence d'un nouveau document CDA avec meme `DocumentId` ou meme combinaison
  patient+type+date

### Message de suppression pure
- En-tetes `In-Reply-To` / `References` pointant vers le message original
- Absence de nouveau document CDA en piece jointe
- Corps du message indiquant une demande de suppression

### Correspondance avec le document existant
- Par `DocumentId` exact (identifiant CDA `id@root` + `id@extension`)
- Par `MessageId` reference dans `In-Reply-To`
- Par correspondance fonctionnelle : meme `Ins` + `Category` + `Date`

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/GestionSuppressionModification.feature`

## Exigence Segur couverte

- LGC.MSS/UX.05 — Gerer messages de suppression/modification de documents integres

## References reglementaires

- REM Segur LGC.MSS/UX.05
- Referentiel socle MSSante #2 v1.0.1 — ECO.2.2.1, ECO.2.2.2 (threading RFC 5322)
- Referentiel socle MSSante #2 v1.0.1 — ECO.2.1.3 (format objet avec XDM/1.0/DDM+)

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Detection des messages de suppression/modification par analyse :
  - Objet contenant `[Annule et remplace]`
  - En-tetes `In-Reply-To` / `References` referencant le message original
  - Correspondance `DocumentId` ou `Ins` + `Category` + `Date`
- [ ] Lien entre le message de gestion et le `MailMedicalDocument` original
- [ ] Proprietes ajoutees au `MailMedicalDocument` :
  - `IsSuperseded` (bool) — document remplace ou supprime
  - `SupersededByDocumentId` (int?) — reference vers le nouveau document
  - `SuppressionRequestedAt` (DateTime?) — date de la demande
- [ ] Notification au professionnel lors de la reception d'un message de
  suppression/modification
- [ ] Le professionnel peut accepter ou refuser la suppression
- [ ] Le document supprime est masque de la timeline patient mais conserve en
  base pour tracabilite
- [ ] Le document modifie est lie a sa nouvelle version (navigation possible
  entre versions)
- [ ] Blazor : notification + indicateur sur le document + actions
  accepter/refuser + navigation entre versions
- [ ] Angular : notification + indicateur sur le document + actions
  accepter/refuser + navigation entre versions
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- **Test suppression :**
  - Recevoir un message avec un document CDA → verifier l'integration
  - Recevoir un second message referancant le premier (via `In-Reply-To`)
    sans nouveau document (demande de suppression)
    - Verifier : notification + signalement sur le document original
    - Accepter la suppression → verifier que le document disparait de la
      timeline mais est conserve en base (`IsSuperseded = true`)
- **Test modification (annule et remplace) :**
  - Recevoir un message avec un document CDA
  - Recevoir un message `[Annule et remplace]` avec un nouveau document
    - Verifier : le nouveau document est lie a l'original
    - Verifier : l'original est marque "remplace" (`SupersededByDocumentId`
      pointe vers le nouveau)
    - Verifier : navigation possible entre les deux versions
- **Test refus :**
  - Recevoir une demande de suppression → refuser
    - Verifier : le document reste visible dans la timeline
    - Verifier : le signalement est conserve pour tracabilite
- Repeter sur les deux frontends
