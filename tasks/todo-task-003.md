# todo-task-003.md — Opposition patient envoi MSS

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune

## Objectif

Le systeme doit permettre d'enregistrer et de respecter l'opposition d'un patient a la
reception de messages MSSante. Conformement aux articles R. 1111-26 et suivants du code
de la sante publique, un usager peut s'opposer a la creation de Mon Espace Sante ou
demander sa fermeture a tout moment. L'existence d'un compte MES et d'une BAL usager
n'est donc pas garantie.

Deux types d'opposition sont concernes :
- **Opposition envoi MSS patient** (MSS/va1.20) : le patient refuse de recevoir des
  documents de sante via sa BAL `@patient.mssante.fr`
- **Opposition envoi MSS professionnel** (MSS/va1.22) : le patient refuse que des
  documents le concernant soient transmis entre professionnels via MSSante

Le systeme doit egalement respecter les controles pre-envoi vers un usager definis
par le Ref#2 :
- **ECO.2.2.6** : l'adresse usager DOIT etre construite a partir d'une INS qualifiee
  uniquement
- **ECO.3.1.5** : selection de l'usager dans une liste + verification INS qualifiee +
  generation du `To:` a partir du matricule INS
  (`<matriculeINS>@patient.mssante.fr`, 15 caracteres alphanumeriques = NIR/NIA +
  cle de controle)
- **Controles pre-envoi (§3.4.2.2)** : verification de la cle de controle du matricule
  INS (alerte si saisie erronee) + message d'alerte demandant au professionnel de
  confirmer l'identite de l'usager en affichant date de naissance et sexe (deduits
  du matricule INS)

## Fiche patient — consentement

Sur la page `/patient` des deux frontends (Blazor et Angular), le professionnel doit :
- **Voir** l'etat actuel des deux consentements :
  - Opposition envoi vers Mon Espace Sante (oui/non + date si oppose)
  - Opposition envoi entre professionnels (oui/non + date si oppose)
- **Modifier** chaque consentement via un toggle (activer/desactiver l'opposition)
- La modification enregistre automatiquement la date du changement

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/OppositionPatientMss.feature`

## Exigences Segur couvertes

- MSS/va1.20 — Opposition envoi MSS patient
- MSS/va1.22 — Opposition envoi MSS professionnel
- ECO.2.2.6 — Adresses usagers construites a partir d'INS qualifiees
- ECO.3.1.5 — Selection usager + verification INS + generation To:

## References reglementaires

- Articles R. 1111-26 et suivants du code de la sante publique (droit d'opposition MES)
- Referentiel socle MSSante #2 v1.0.1 — §3.4.2 (Usager destinataire d'un courriel)
- ECO.2.2.6 — Adresses usagers construites a partir d'INS qualifiees
- ECO.3.1.5 — Selection usager + verification INS + generation To:
- §3.4.2.2 — Controles pre-envoi : cle de controle INS + confirmation identite

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Modele `MailPatient` enrichi avec :
  - `OppositionMssPatient` (bool) — opposition envoi vers BAL patient MES
  - `OppositionMssProfessionnel` (bool) — opposition envoi entre professionnels
  - `OppositionDate` (DateTime?) — date d'enregistrement de l'opposition
- [ ] Endpoint pour enregistrer/lever l'opposition d'un patient (les deux types)
- [ ] Avertissement affiche a l'envoi si le patient a exprime son opposition (non bloquant mais explicite)
- [ ] Envoi vers usager uniquement si INS qualifiee (ECO.2.2.6) — bloquant
- [ ] Adresse destinataire usager generee a partir du matricule INS : `<matriculeINS>@patient.mssante.fr` (ECO.3.1.5)
- [ ] Verification de la cle de controle du matricule INS avant envoi (alerte si erronee)
- [ ] Message de confirmation d'identite affichant date de naissance et sexe (deduits du matricule) avant envoi vers usager (§3.4.2.2)
- [ ] Blazor : page `/patient` affiche l'etat des deux consentements (MSS patient + MSS professionnel) avec date d'enregistrement si oppose
- [ ] Blazor : page `/patient` permet de modifier chaque consentement via un toggle
- [ ] Blazor : avertissements a la composition + confirmation identite pre-envoi
- [ ] Angular : page `/patient` affiche l'etat des deux consentements avec date
- [ ] Angular : page `/patient` permet de modifier chaque consentement via un toggle
- [ ] Angular : avertissements a la composition + confirmation identite pre-envoi
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Ouvrir la fiche d'un patient (`/patient`)
  - Verifier que l'etat des deux consentements est visible (par defaut : pas d'opposition)
  - Activer l'opposition MSS patient via le toggle → verifier l'enregistrement avec date
  - Recharger la page → verifier que l'etat persiste
- Composer un message vers ce patient
  - Verifier l'avertissement d'opposition affiche
  - Annuler l'envoi → verifier que le message n'est pas envoye
- Lever l'opposition sur la fiche patient
  - Verifier que l'envoi ne declenche plus d'avertissement
- Tester l'opposition MSS professionnel :
  - Activer sur la fiche patient
  - Composer un message a un confrere concernant ce patient → verifier l'avertissement
- Tester les controles pre-envoi usager :
  - Selectionner un patient avec INS qualifiee → verifier l'affichage date de naissance + sexe pour confirmation
  - Selectionner un patient sans INS qualifiee → verifier le refus d'envoi vers MES
- Repeter sur les deux frontends (Blazor et Angular)
