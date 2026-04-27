# todo-task-014.md — Options selectives de parsing CDA (CdaParseOptions)

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E009

## Objectif

Le service `CdaParsingService.ParseIheXdmZip(path)` execute aujourd'hui la
totalite du pipeline de parsing pour chaque appel : metadata CDA, biology
results, patient summary, transformation HTML (XSLT) du corps clinique,
extraction des PDF, et chargement des pieces jointes. Plusieurs callers n'ont
besoin que d'une fraction de ces resultats — typiquement
`MssanteHeaderService` (task-001) qui ne consulte que `CdaTypeCode` et les
champs de qualification INS pour positionner les en-tetes SMTP `X-MSS-CODECDA`
et `X-MSS-INS`.

Consequences observees en production (logs Seq, 27/04/2026) :

- chaque envoi de mail (`POST /api/v1/mail/sendmail`) declenche la
  transformation HTML via XSLT, alors que le resultat est jete par
  `MssanteHeaderService` ;
- la feuille XSL est actuellement defaillante (XSLT compile error), ce qui
  pollue les logs avec un `Error` `[CdaParsingService] HTML transform error:
  XSLT compile error.` a chaque envoi, alors que ce code path n'apporte aucune
  valeur fonctionnelle au cas d'usage `SendMail` ;
- le cout CPU (lecture XSL, parsing PDF en parallele via `Task.Run`) est paye
  pour rien.

Cette task introduit un mecanisme de selection des etapes de parsing — option A
discutee avec le PO — pour permettre a chaque caller de demander uniquement
les sections dont il a besoin.

> **Note** : cette task **ne traite pas** la cause racine du XSLT compile
> error. Elle supprime simplement le bruit log et le cout CPU pour les call
> sites qui n'ont pas besoin du body HTML. Une task separee couvrira le
> diagnostic et le fix de la feuille XSL.

## Design — `CdaParseOptions` (flags)

Ajouter un enum `[Flags]` dans `Application/Services/Interfaces` :

```csharp
[Flags]
public enum CdaParseOptions
{
    None        = 0,
    Metadata    = 1 << 0,  // header CDA + INS + patient + practitioner + category
    Biology     = 1 << 1,  // ProcessBiologyResults
    Summary     = 1 << 2,  // ProcessPatientSummary
    HtmlBody    = 1 << 3,  // ProcessCdaContent (XSLT + PDF -> texte, BodyHtml/Body)
    Attachments = 1 << 4,  // ProcessAttachments + ProcessAssociatedPdf
    All         = Metadata | Biology | Summary | HtmlBody | Attachments
}
```

Surcharge sur `ICdaParsingService` :

```csharp
List<MailMedicalDocumentDto> ParseIheXdmZip(
    string iheXdmZipPath,
    CdaParseOptions options = CdaParseOptions.All);
```

Dans `CdaParsingService.ParseCdaDocument`, gating de chaque etape :

```csharp
if (options.HasFlag(CdaParseOptions.Biology))     ProcessBiologyResults(cda, dto);
if (options.HasFlag(CdaParseOptions.Summary))     ProcessPatientSummary(cda, dto);
if (options.HasFlag(CdaParseOptions.HtmlBody))    ProcessCdaContent(cda, dto);
if (options.HasFlag(CdaParseOptions.Attachments))
{
    ProcessAttachments(cda, dto);
    ProcessAssociatedPdf(cda, dto);
}
```

Le bloc Metadata est inconditionnel (il s'agit du remplissage initial du
`MailMedicalDocumentDto` deja en place avant les `Process*`). Si un caller
passe `CdaParseOptions.None`, le service retourne quand meme la liste avec les
metadatas — c'est l'unite minimale utile.

### Migration des callers

- `MssanteHeaderService` : passe explicitement `CdaParseOptions.Metadata`.
- Tous les autres callers (pipeline d'enrichissement clinique, lecture email,
  etc.) : pas de changement — la valeur par defaut `CdaParseOptions.All`
  preserve le comportement actuel.

### Approche alternative non retenue

Methode dediee `ParseIheXdmZipMetadata(...)` retournant un sous-DTO :
expressive mais N x duplication de code et obligation de maintenir un DTO
parallele. L'enum `[Flags]` est plus extensible (futur caller voulant
`Metadata | HtmlBody` sans Attachments est trivial a ajouter).

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures)
- [ ] Enum `CdaParseOptions` cree dans `Application/Services/Interfaces` avec
      les valeurs `None`, `Metadata`, `Biology`, `Summary`, `HtmlBody`,
      `Attachments`, `All`
- [ ] `ICdaParsingService.ParseIheXdmZip` accepte le parametre
      `CdaParseOptions options = CdaParseOptions.All`
- [ ] `CdaParsingService` gate `ProcessBiologyResults`, `ProcessPatientSummary`,
      `ProcessCdaContent`, `ProcessAttachments`, `ProcessAssociatedPdf` selon
      le flag correspondant
- [ ] `MssanteHeaderService` appelle `ParseIheXdmZip(path,
      CdaParseOptions.Metadata)` (1 seul site d'appel, dans la branche
      d'extraction CDA pour les en-tetes)
- [ ] Unit test : `ParseIheXdmZip(path, CdaParseOptions.Metadata)` produit un
      `MailMedicalDocumentDto` avec `BodyHtml == null`, `Body` vide ou null,
      `Attachments` vide, et `CdaTypeCode`/`PatientIns`/`PatientOid`
      correctement remplis (>=1 test sur fixture XDM existante)
- [ ] Unit test : `ParseIheXdmZip(path)` (sans argument, defaut `All`)
      conserve strictement le comportement actuel sur la meme fixture
      (regression test — `BodyHtml` non null, `Attachments` non vide)
- [ ] Unit test : `ParseIheXdmZip(path, CdaParseOptions.Metadata)` ne produit
      **aucun** log `[CdaParsingService] HTML transform error: ...` (verifie
      via `ILogger` mock NSubstitute / `XUnit.LogCapture`)
- [ ] Unit test sur `MssanteHeaderService` : la verification existante que
      `ParseIheXdmZip` est appele est mise a jour pour valider que le 2e
      argument est `CdaParseOptions.Metadata` (et non `All`)
- [ ] Aucune regression sur les 1614 tests existants — en particulier les
      `MedicalDocumentsUseCaseTests` (pipeline d'enrichissement) doivent
      continuer a peupler `BodyHtml` et `Attachments` (ils utilisent le
      defaut `All`)

## Manual Test Plan

Pre-requis : feuille XSL actuelle (defaillante) inchangee — c'est le contexte
qui rend le test observable.

- Lancer le backend : `cd Api/Mail && dotnet run`
- Envoyer un message MSSante avec un document CDA (Manual Test Plan de
  task-001 reutilisable)
- **Verification 1 — bruit log elimine** : ouvrir Seq
  (`http://localhost:5341`), filtrer
  `SourceContext = 'mss.mail.application.Services.Implementation.CdaParsingService'`
  et `@Level = 'Error'` sur la derniere minute
  - Attendu : **aucun** evenement `HTML transform error: XSLT compile error.`
    pour le `TraceId` du `SendMail`
- **Verification 2 — en-tetes SMTP toujours emis** : verifier dans les logs
  SMTP que `X-MSS-CODECDA: <code>`, `X-MSS-INS: O` (ou `N`) et `X-MSS-NIL:
  <ref>` sont presents — le contrat de task-001 est preserve
- **Verification 3 — pipeline d'enrichissement non casse** : ouvrir l'email
  recu cote inbox via le frontend, declencher
  `POST /api/v1/mail/folders/INBOX/emails/enrich/sync`
  - Attendu : `BodyHtml` peuple (sauf XSLT defaillant — independant de cette
    task), attachments PDF presents dans le DTO
  - Le log `HTML transform error` peut **toujours** apparaitre sur ce call
    site — c'est normal, le fix XSLT est hors-scope (cf. task suivante)

## Hors scope

- Diagnostic et correction de la feuille XSL `CdaFormatTransformer`. Le
  symptome `XSLT compile error.` reste present sur les call sites qui ont
  reellement besoin du body HTML (pipeline d'enrichissement). Une task
  separee (a venir) couvrira :
  - le passage de `_logger.LogError("...{Error}", htmlError)` a un log avec
    `ex.ToString()` complet pour diagnostiquer
  - l'identification de la feuille XSL fautive (probablement chemin de
    ressource ou XSL invalide en Release)
  - le fix proprement dit
