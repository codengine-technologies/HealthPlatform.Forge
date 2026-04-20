# todo-task-010.md — Affichage prioritaire PDF encapsule

**Repos**: api-mail, client-blazor, client-angular
**Dependencies**: aucune

## Objectif

Lorsqu'un message contient un document CDA R2 niveau 3 avec un PDF associe dans
l'archive IHE_XDM, le systeme doit afficher preferentiellement le PDF. De plus, un
CDA R2 N3 accompagne de son PDF doit apparaitre sur une seule ligne dans la liste
des documents (et non deux lignes separees).

## Detail des exigences (Ref#2 v1.0.1)

### ECO.2.1.1 (§3.1.1, p.21)

> Un courriel MSSante utilise pour transmettre un (des) document(s) de sante DOIT :
> - Concerner qu'un seul et meme usager
> - Contenir en pieces jointes :
>   - une archive ZIP au format IHE_XDM contenant un ou plusieurs documents CDA R2
>     niveau 1 et/ou niveau 3
>   - les memes documents medicaux au format PDF/A-1

### ECO.2.1.5 (§3.1.1, p.21)

> Chaque PDF/A-1 rattache au courriel MSSante DOIT etre genere a partir du ou des
> documents CDA correspondants contenus dans l'archive ZIP au format IHE_XDM :
> - Cas d'un document CDA R2 N3 : le PDF/A-1 doit comporter les donnees de l'en-tete
>   CDA (Titre, Type, Date, Auteur, Organisation) + une transcription fidele du
>   contenu clinique porte dans la partie narrative.
> - Sinon : le PDF/A-1 doit etre identique au PDF encapsule dans le CDA R2 N1.

### ECO.2.1.6 (§3.1.1, p.22)

> Les fichiers au format PDF presents en piece jointe DOIVENT respecter la convention
> de nommage suivante :
> ```
> <date de l'acte>_<type document>_<NOM>_<prenom>_<numero de dossier>.pdf
> ```

Avec :
- `<date de l'acte>` : AAAAMMJJ, issu de `documentationOf/serviceEvent/effectiveTime/low`
  du CDA ou `serviceStartTime` XDS
- `<type document>` : `displayName` du code CDA ou `typeCodeDisplayName` XDS,
  tronque a 40 caracteres
- `<NOM>` : nom de naissance en **majuscules**
- `<prenom>` : prenom de l'usager
- `<numero de dossier>` : optionnel (numero d'enregistrement de la prescription
  initiale pour la biologie)

Exemples :
- `20150802_CR d'examens biologiques_VIAL_Paul_12150302014578.pdf`
- `20150802_Lettre de liaison a la sortie d'un etabl_VIAL_Paul.pdf`
- `20150802_CR d'anesthesie_VIAL_Paul.pdf`

## Structure IHE_XDM

L'archive IHE_XDM contient des fichiers separes pour le CDA et le PDF :
```
IHE_XDM/
  SUBSET01/
    DOC00001.XML          <- CDA R2 (N1 ou N3)
    DOC00001.PDF          <- PDF/A-1 genere depuis le CDA
    METADATA.XML          <- Metadonnees XDS (ExtrinsicObject)
```

Le lien entre CDA et PDF se fait par :
- Correspondance de nommage dans le dossier SUBSET (`DOC00001.XML` / `DOC00001.PDF`)
- Ou via les `ExtrinsicObject` du `METADATA.XML` (meme `patientId`, meme `typeCode`)

## Traitement backend

Le `IheXdmProcessingService` doit :
1. Identifier les paires CDA/PDF dans chaque SUBSET (correspondance par nom de
   fichier ou metadonnees METADATA.XML)
2. Creer **un seul** `MailMedicalDocument` pour la paire, avec :
   - Les metadonnees cliniques extraites du CDA (patient, praticien, LOINC, categorie)
   - Le PDF stocke comme piece jointe privilegiee (`MailAttachment`)
   - Le CDA XML conserve pour le rendu structure XSLT
3. Ne pas creer de `MailMedicalDocument` en doublon pour le PDF

## Affichage frontend

- Le PDF est affiche en priorite a l'ouverture du document
- Option pour basculer vers le rendu CDA structure (XSLT)
- Un document CDA + son PDF = une seule ligne dans la liste
- Lors du telechargement/export du PDF, le nom de fichier respecte la convention
  ECO.2.1.6

## Gherkin

See `tests/mss.mail.bdd.tests/Features/Mss/AffichagePrioritairePdf.feature`

## Exigences Segur couvertes

- SC.CDA/VISU.03 — Afficher preferentiellement le PDF encapsule
- SC.CDA/DD.15 — Une seule ligne pour CDA R2 N3 avec PDF encapsule

## References reglementaires

- Referentiel socle MSSante #2 v1.0.1 — §3.1.1 (ECO.2.1.1, ECO.2.1.5, ECO.2.1.6)
- SC.CDA/VISU.03
- SC.CDA/DD.15

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures)
- [ ] Le `IheXdmProcessingService` identifie les paires CDA/PDF dans l'archive
  IHE_XDM (par nommage SUBSET ou metadonnees METADATA.XML)
- [ ] Une seule entree `MailMedicalDocument` creee par paire CDA/PDF
- [ ] Le PDF est stocke comme piece jointe privilegiee, le CDA XML conserve pour
  le rendu XSLT
- [ ] Un document CDA R2 N3 + son PDF/A-1 apparaissent sur **une seule ligne**
  dans la liste des documents
- [ ] Le PDF est affiche en priorite a l'ouverture du document
- [ ] Option pour basculer vers le rendu CDA structure (XSLT) si le professionnel
  le souhaite
- [ ] Les documents CDA sans PDF encapsule affichent le rendu XSLT normalement
- [ ] Le PDF respecte la convention de nommage ECO.2.1.6 lors de
  l'export/telechargement : `<date>_<type>_<NOM>_<prenom>_<dossier>.pdf`
- [ ] Blazor : liste des documents sans doublons + affichage prioritaire PDF +
  bascule CDA/PDF
- [ ] Angular : liste des documents sans doublons + affichage prioritaire PDF +
  bascule CDA/PDF
- [ ] >= 1 test d'integration par scenario Gherkin
- [ ] Aucune regression

## Branches

- `api-mail` (pushed) : feat/task-010-pdf-encapsule-priorite — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-010-pdf-encapsule-priorite
- `client-blazor` (pushed) : feat/task-010-pdf-encapsule-priorite — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-010-pdf-encapsule-priorite
- `dtos-mss` (pushed, auto-included) : feat/task-010-pdf-encapsule-priorite — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-010-pdf-encapsule-priorite
- `client-angular` : managed manually by the human (TFS remote, excluded from forge automation)

## Manual Test Plan

- Lancer backend + Blazor + Angular
- Recevoir un message contenant un IHE_XDM avec un CDA R2 N3 + son PDF/A-1
  - Verifier dans la liste des documents : une seule ligne (pas deux)
  - Ouvrir le document → verifier que le PDF s'affiche en priorite
  - Cliquer sur "Voir le document structure" → verifier le rendu XSLT
  - Telecharger le PDF → verifier le nom de fichier conforme ECO.2.1.6
    (ex: `20150802_CR d'examens biologiques_VIAL_Paul.pdf`)
- Recevoir un message avec un CDA R2 N3 sans PDF
  - Verifier : une seule ligne, rendu XSLT a l'ouverture
- Recevoir un message avec 3 documents : 2 avec PDF, 1 sans
  - Verifier : 3 lignes (pas 5), priorite PDF sur les 2 premiers, XSLT sur le 3e
- Repeter sur les deux frontends
