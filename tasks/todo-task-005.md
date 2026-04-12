# todo-task-005.md — Distinction messages pro/patient

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune

## Objectif

Dans la liste des messages recus, le systeme doit distinguer visuellement les messages
emis par des professionnels de sante de ceux emis par des usagers via Mon Espace Sante,
afficher l'identite complete de l'usager, et rattacher automatiquement le message au
dossier patient en creant un document medical de type `COURRIER`.

## Detail des exigences (Ref#2 v1.0.1)

### ECO.3.1.1 — Distinction pro/usager (§4.1, p.34)

> Dans la liste des messages recus, le systeme DOIT distinguer les messages emis par
> des professionnels, des messages emis par des usagers via MES.

- Le professionnel doit pouvoir distinguer les 2 types d'emetteurs **sans se referer
  au nom de domaine**
- Adresse `@patient.mssante.fr` → message usager MES
- Format adresse usager : `<matriculeINS>@patient.mssante.fr` (15 car. alphanumeriques)

### ECO.3.1.2 — Affichage identite usager (§4.2, p.34)

> Le systeme DOIT afficher le nom de naissance, le 1er prenom et le matricule INS
> d'usager (et pas uniquement l'adresse email `INS@patient.mssante.fr`).

- MES transmet le nom et le prenom dans le libelle du champ `From:`
- Exemple : `From: Leo Dupond <123456789012345@patient.mssante.fr>`

## Traitement backend a la reception d'un message patient

Lorsque le backend detecte un message dont `FromAddress` contient `@patient.mssante.fr` :

### Etape 1 — Extraction de l'INS

- Extraire le matricule INS depuis la partie locale de l'adresse :
  `123456789012345` de `123456789012345@patient.mssante.fr`
- Extraire nom et prenom depuis `FromName` (display name du champ `From:`)

### Etape 2 — Resolution ou creation du patient

- Rechercher dans `MailPatient` par `Ins = <INS extrait>`
- **Si le patient existe** → rattacher le message a ce patient
- **Si le patient n'existe pas** → creer un `MailPatient` avec :
  - `Ins` = matricule INS extrait
  - `LastName` = nom extrait du display name (si disponible)
  - `FirstName` = prenom extrait du display name (si disponible)
  - Les autres champs restent vides (enrichissement ulterieur possible)

### Etape 3 — Creation du document medical

Creer un `MailMedicalDocument` rattache au mail et au patient :

| Champ | Valeur |
|---|---|
| `MailId` | Id du mail recu |
| `PatientId` | Id du `MailPatient` (existant ou nouvellement cree) |
| `Category` | `COURRIER` (nouveau type, distinct de biologie, CR, VSM, etc.) |
| `Title` | Objet du message (`Subject`) |
| `Date` | Date d'envoi du message (`SentDate`) |
| `Ins` | Matricule INS extrait |
| `PatientFirstName` | Prenom extrait du display name |
| `PatientLastName` | Nom extrait du display name |
| `Format` | `EMAIL` (pas de CDA, pas de XDM) |

Cela garantit que :
- Le message apparait dans la vue patient (`/patient`)
- Le flag `HasMedicalDocuments` est positionne a `true` sur le `Mail`
- Le courrier patient est visible dans la timeline patient aux cotes des CDA et biologies

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/DistinctionMessagesProPatient.feature`

## Exigences Segur couvertes

- SC.MSS/UX.25 (ECO.3.1.1) — Distinguer messages pro vs usagers MES
- SC.MSS/UX.31 (ECO.3.1.2) — Afficher nom, prenom et matricule INS d'usager

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 — §4.1, §4.2
- ECO.3.1.1 — Distinguer messages pro vs usagers MES
- ECO.3.1.2 — Afficher nom, prenom et matricule INS d'usager

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Detection automatique des messages usagers par `@patient.mssante.fr` dans `FromAddress`
- [ ] Extraction du matricule INS (15 car.) depuis la partie locale de l'adresse
- [ ] Extraction du nom/prenom depuis le display name du champ `From:` (`FromName`)
- [ ] Recherche du patient par INS dans `MailPatient` :
  - Si existant → rattachement
  - Si inexistant → creation `MailPatient` avec INS, nom, prenom extraits
- [ ] Creation automatique d'un `MailMedicalDocument` de type `COURRIER` avec :
  - `Category` = `COURRIER`
  - `Format` = `EMAIL`
  - `Title` = sujet du message
  - `Date` = date d'envoi
  - `Ins`, `PatientFirstName`, `PatientLastName` renseignes
  - Rattachement au `Mail` et au `MailPatient`
- [ ] Flag `HasMedicalDocuments` positionne a `true` sur le `Mail`
- [ ] Les courriers patients apparaissent dans la vue `/patient` (timeline)
- [ ] Propriete `IsFromPatient` (bool) exposee dans le DTO
- [ ] Indicateur visuel distinct pro/patient dans la liste (sans lire le nom de domaine)
- [ ] Affichage pour les messages patients : `Nom Prenom (matricule INS)` au lieu de l'email brut
- [ ] Fallback si display name absent : afficher le matricule INS seul
- [ ] Blazor : distinction visuelle + identite patient dans liste et detail + courriers dans timeline patient
- [ ] Angular : distinction visuelle + identite patient dans liste et detail + courriers dans timeline patient
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- **Test 1 — Pro :** recevoir un message de `dr.martin@medecin.mssante.fr`
  - Verifier indicateur "professionnel" dans la liste
  - Verifier qu'aucun `MailMedicalDocument` de type COURRIER n'est cree
- **Test 2 — Patient existant :** creer un patient avec INS `123456789012345`,
  puis recevoir un message de `Leo Dupond <123456789012345@patient.mssante.fr>`
  - Verifier indicateur "patient" + affichage `Leo Dupond (123456789012345)`
  - Verifier en base : `MailMedicalDocument` cree avec `Category=COURRIER`,
    `Format=EMAIL`, rattache au patient existant
  - Ouvrir `/patient` → verifier que le courrier apparait dans la timeline
- **Test 3 — Patient inexistant :** recevoir un message de
  `Marie Martin <987654321012345@patient.mssante.fr>` sans patient pre-existant
  - Verifier en base : nouveau `MailPatient` cree
    (INS=`987654321012345`, Nom=`Martin`, Prenom=`Marie`)
  - Verifier en base : `MailMedicalDocument` de type COURRIER rattache au nouveau patient
- **Test 4 — Sans display name :** recevoir un message de
  `<111222333444555@patient.mssante.fr>` (pas de nom)
  - Verifier : patient cree avec INS seul, indicateur "patient", matricule affiche
- Repeter sur Blazor et Angular
