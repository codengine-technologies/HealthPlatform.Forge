# todo-task-034.md — Conformite INT.18 : detection doublons CDA par id/setId/versionNumber

**Repos**: interop-cda, dtos-mss, api-mail, client-blazor, client-angular
**Dependencies**: archived-task-013
**Epic**: E009

## Objectif

Mettre en conformite la detection de doublons CDA avec l'exigence reglementaire
**SC.CDA/INT.18** qui impose de s'appuyer sur les balises `id`, `setId` et
`versionNumber` du document CDA.

La task-013 avait pose la plomberie (detection par `DocumentId` exact OU
combinaison fonctionnelle `Ins + Category + Date + Title`, indicateur visuel,
actions confirmer/rejeter). Cette task **remplace la logique de detection** par
l'algorithme normatif et ajoute la gestion des versions de document.

### Changements cles

1. **Ajout du champ `SetId`** — parsing CDA (`interop-cda`), entite
   `MailMedicalDocument`, migration BDD, DTO, fronts.
2. **Nouvelle logique de detection (INT.18)** :
   - Meme `DocumentId` (id root+extension) + meme `Version` (versionNumber)
     → **doublon exact** → ne pas integrer, signaler au professionnel.
   - Meme `SetId` + `Version` superieure → **nouvelle version** → integrer
     normalement, marquer le document precedent comme "version remplacee"
     (`SupersededByDocumentId`).
   - Meme `SetId` + `Version` inferieure ou egale → **version obsolete** →
     ne pas integrer, signaler au professionnel.
3. **Suppression de la detection fonctionnelle** (`Ins + Category + Date +
   Title`) — remplacee integralement par la detection normative ci-dessus.
4. **Indicateur "version remplacee"** cote UI — le document remplace affiche
   un badge "Remplace par doc #N" (ou "Superseded") avec lien vers la
   nouvelle version.

### Exigence Segur couverte

- SC.CDA/INT.18 — Verifier coherence de tout document CDA recu (detection
  doublons par id, setId, versionNumber)

### References reglementaires

- SC.CDA/INT.18

## Definition of Done

- [ ] Build passe (0 erreur) sur `interop-cda`, `dtos-mss`, `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests passent (0 failure)
- [ ] `SetId` extrait du CDA par `interop-cda` (balise `setId` du ClinicalDocument)
- [ ] `SetId` persiste en BDD (`MailMedicalDocuments.SetId`, migration FluentMigrator)
- [ ] `SetId` expose dans `MailMedicalDocumentDto`
- [ ] Detection doublon exact : meme `DocumentId` + meme `Version` → document rejete (non integre), signale
- [ ] Detection nouvelle version : meme `SetId` + `Version` superieure → document integre, ancien marque `SupersededByDocumentId`
- [ ] Detection version obsolete : meme `SetId` + `Version` inferieure ou egale → document rejete, signale
- [ ] Detection fonctionnelle (`Ins + Category + Date + Title`) supprimee
- [ ] Propriete `SupersededByDocumentId` (Guid?) ajoutee a `MailMedicalDocument`
- [ ] Indicateur visuel "doublon" conserve (task-013) pour les doublons exacts et versions obsoletes
- [ ] Indicateur visuel "version remplacee" pour les documents supercedes par une version plus recente
- [ ] Le professionnel peut toujours confirmer/rejeter le signalement de doublon (actions task-013 conservees)
- [ ] Blazor : badges doublon + version remplacee, lien vers la nouvelle/ancienne version
- [ ] Angular : badges doublon + version remplacee, lien vers la nouvelle/ancienne version
- [ ] >= 1 test unitaire par scenario de detection (doublon exact, nouvelle version, version obsolete, document nouveau, SetId absent)
- [ ] >= 1 test d'integration pour le round-trip SetId (parsing CDA → persistance → DTO)
- [ ] Exclusion self-action folders conservee (fix post-review task-013)
- [ ] Aucune regression

## Manual Test Plan

- Lancer backend + Blazor + Angular
- **Scenario 1 — doublon exact** :
  - Recevoir un message avec un CDA (noter `DocumentId` + `Version`)
  - Recevoir un second message avec le meme `DocumentId` et la meme `Version`
  - Verifier : le second document n'est PAS integre, signalement "doublon exact"
- **Scenario 2 — nouvelle version** :
  - Recevoir un CDA avec `SetId=X`, `VersionNumber=1`
  - Recevoir un CDA avec `SetId=X`, `VersionNumber=2` (nouveau `DocumentId`)
  - Verifier : le second est integre normalement
  - Verifier : le premier est marque "Remplace par doc #N"
  - Verifier : le badge "version remplacee" apparait sur le premier document
- **Scenario 3 — version obsolete** :
  - Recevoir un CDA avec `SetId=X`, `VersionNumber=2`
  - Recevoir un CDA avec `SetId=X`, `VersionNumber=1`
  - Verifier : le second (v1) n'est PAS integre, signalement "version obsolete"
- **Scenario 4 — document nouveau** :
  - Recevoir un CDA avec un `DocumentId` et `SetId` inedits
  - Verifier : integration normale, aucun signalement
- **Scenario 5 — SetId absent** :
  - Recevoir un CDA sans balise `setId`
  - Verifier : la detection par `SetId` est ignoree, seule la detection par
    `DocumentId` exact s'applique
- Repeter sur les deux frontends
