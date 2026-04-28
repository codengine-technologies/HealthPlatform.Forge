# todo-task-012.md — Rattachement patient par comparaison visuelle

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: todo-task-011 (indicateur document integre)
**Epic**: E009

## Objectif

Lorsqu'un document CDA recu contient des traits d'identite patient mais sans INS
qualifiee (matricule INS absent ou sans OID, traits incomplets), le systeme doit
proposer au professionnel un workflow de rattachement par comparaison visuelle :
afficher les traits d'identite extraits du CDA a cote des patients connus dans la
base pour que le professionnel confirme le rapprochement.
Dans la liste des email prévoir un visuel pour indiqué le rattachement et si aucun ratachement proposer une action pour déclencher le workflow. Cela doit être fait dans le client Angular et Blazor

## Contexte reglementaire

### Definition INS qualifiee (Ref#2 §3.8.2, p.33 — ECO.2.4.2)

> L'identite INS de l'usager est **qualifiee** par l'emetteur du courrier si le document
> recu en piece jointe contient le **matricule INS ET son OID ET les 4 traits d'identite**
> (nom de naissance, 1er prenom, date de naissance, sexe).

Une identite ou seuls les traits sont presents dans le CDA, sans le matricule INS et
l'OID, n'est pas qualifiee.

### Identification patient (Ref#2 §3.1.2, p.23 — ECO.2.1.2)

> Pour identifier l'usager concerne par un courriel, le systeme destinataire DOIT se
> referer a la metadonnee `patientId` (matricule INS) contenu dans le fichier
> METADATA.XML du document CDA contenu dans la piece jointe IHE_XDM.zip du courriel.

## Cas d'usage

1. **INS qualifiee** → rattachement automatique (deja implemente via `CdaParsingService`)
2. **INS non qualifiee** (traits d'identite presents mais sans matricule+OID) →
   **cette US : comparaison visuelle**
3. **Aucune info patient** → le document reste non rattache

## Comportement backend

### Recherche de patients candidats

Quand un document CDA a une identite non qualifiee, le backend expose un endpoint
de recherche de patients candidats :

```
GET /api/v1/patients/match?lastName={nom}&firstName={prenom}&birthDate={date}&gender={sexe}
```

Algorithme de correspondance :
- Recherche exacte par nom + prenom + date de naissance
- Recherche approchee par nom + date de naissance (prenom different possible)
- Recherche large par nom seul (si peu de resultats)
- Score de correspondance pour chaque candidat

### Endpoint de rattachement manuel

```
POST /api/v1/medical-documents/{documentId}/attach-patient
Body: { patientId: int }
```

## Interface frontend

Quand un document a `PatientId == null` et des traits d'identite disponibles
(`PatientFirstName`, `PatientLastName`, `PatientBirthDate`, `PatientGender` non vides) :

- Afficher un bandeau "Rattachement en attente — identite non qualifiee"
- Afficher les traits extraits du CDA : nom, prenom, date de naissance, sexe
- En dessous, liste des patients candidats avec score de correspondance
- Boutons : "Rattacher a ce patient" / "Creer un nouveau patient" / "Ignorer"

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/RattachementPatientVisuel.feature`

## Exigences Segur couvertes

- MSS/va1.27 — Rattachement patient par comparaison visuelle si INS sans identite
  qualifiee

## References reglementaires

- REM Segur MSS/va1.27
- Referentiel socle MSSante #2 v1.0.1 — §3.8.2 (definition INS qualifiee, ECO.2.4.2)
- Referentiel socle MSSante #2 v1.0.1 — §3.1.2 (identification patient, ECO.2.1.2)

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Endpoint `GET /api/v1/patients/match` de recherche de patients candidats par
  traits d'identite avec score de correspondance
- [ ] Endpoint `POST /api/v1/medical-documents/{documentId}/attach-patient` de
  rattachement manuel
- [ ] Les documents avec INS qualifiee sont toujours rattaches automatiquement
  (pas de regression)
- [ ] Les documents avec identite non qualifiee affichent un workflow de
  comparaison visuelle
- [ ] Le professionnel peut confirmer le rattachement, refuser, ou creer un
  nouveau patient
- [ ] Apres rattachement, le `PatientId` est mis a jour et l'indicateur
  d'integration se met a jour (lien avec US task-011)
- [ ] Blazor : bandeau + comparaison visuelle + actions de rattachement
- [ ] Angular : bandeau + comparaison visuelle + actions de rattachement
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Recevoir un message avec un CDA contenant nom/prenom/date naissance mais
  sans matricule INS + OID
  - Verifier : document non rattache, bandeau "identite non qualifiee"
  - Verifier : traits d'identite affiches + patients candidats proposes
  - Selectionner un patient → confirmer → verifier le rattachement
- Recevoir un message avec un CDA contenant une INS qualifiee
  - Verifier : rattachement automatique, pas de comparaison visuelle
- Recevoir un message avec un CDA dont le patient n'existe pas en base
  - Verifier : option "Creer un nouveau patient" disponible
  - Creer le patient → verifier le rattachement
- Repeter sur les deux frontends
