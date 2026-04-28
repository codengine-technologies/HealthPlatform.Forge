# questions/task-011.md — scope ambiguity

**Task** : todo-task-011 — Indicateur document deja integre
**Halted at** : `/develop` Step 0 (pre-flight + initial exploration)
**Date** : 2026-04-28

## Probleme

Le DOD requiert :

> [ ] Critere d'integration : `MailMedicalDocument.PatientId` non null
> [ ] Indicateur visuel dans la liste des messages : distinguer les messages
>     dont tous les documents sont rattaches (integres) de ceux qui ont des
>     documents en attente
> [ ] Indicateur visuel par document dans le detail du message

Or :

1. **`MailMedicalDocumentDto`** (`Dtos/MailMedicalDocumentDto.cs`) **n'expose
   pas** le champ `PatientId`. L'entite domain `MailMedicalDocument`
   (`Api/Mail/src/Domain/Entities/MailMedicalDocument.cs:16`) a bien
   `PatientId` (peuple par `MailRepository.cs:116, :170` quand l'INS est
   qualifiee), mais il n'est jamais mappe vers le DTO.

2. **`MailDto`** (`Dtos/MailDto.cs`) n'a aucun aggregate type
   `AllDocumentsIntegrated` ou `PendingIntegrationsCount`. Pour afficher
   l'indicateur dans la **liste des messages**, le frontend devrait charger
   tous les documents de chaque mail (lourd) ou disposer d'un champ aggregate
   pre-calcule cote serveur.

3. **Le task file declare `**Repos**: client-blazor, client-angular`** —
   `api-mail` n'est pas liste. Or le mapping `entity → DTO` se fait dans
   3 sites de `Api/Mail/src/Infrastructure/Repository/MailRepository.cs`
   (lignes ~500, ~902, et `PatientRepository.cs:182`).

Per CLAUDE.md regle 6 (Isolated scopes) :

> A task only touches files in its module. If a cross-module need
> appears → stop, ask the PO.

## Options

### Option A — Etendre le scope (recommande)

Ajouter `api-mail` dans `**Repos**:` du task file et continuer le cycle.
Implementation :

- `dtos-mss` : `MailMedicalDocumentDto` gagne `public int? PatientId { get; set; }`. `MailDto` gagne un aggregate type `IntegrationStatus { Status: enum, IntegratedCount: int, PendingCount: int }` (ou plus simple : `bool? AllDocumentsIntegrated` + `int PendingIntegrationsCount`).
- `api-mail` : 3+ sites de mapping mis a jour pour set `PatientId` ; nouveau calcul de l'aggregate sur `MailDto` (depuis `MailMedicalDocuments.Where(d => d.MailId == ... ).All/Any(d => d.PatientId != null)`).
- `client-blazor` : composants liste + detail.
- `client-angular` : composants liste + detail (code-only, humain commit/push TFS).

Pas de changement de comportement backend — purement additif.

### Option B — Splitter en 2 tasks

- **task-011a** (backend, `api-mail` + `dtos-mss`) : expose `PatientId` sur le DTO document + aggregate sur `MailDto`.
- **task-011b** (frontend, `client-blazor` + `client-angular`) : depend de
  task-011a, affiche les indicateurs.

Plus de discipline (1 PR backend pure mergee avant la frontend), mais double
le tour de cycle et delaye la livraison fonctionnelle. Compose mal avec la
regle 11 US-complete merge gate (la PR backend ne peut merger sans la
frontend, donc finit par etre groupee de toute facon).

### Option C — Endpoint existant que j'aurais loupe

Verification negative :
- `MailMedicalDocumentDto` ne contient pas `PatientId` (lu integralement).
- `MailDto` ne contient pas d'aggregate d'integration (lu integralement).
- Le seul DTO qui expose `PatientId` cote document medical est
  `EmailContentWithEmbedding` (modele Application interne, pas un DTO de
  contrat) — utilise par `SemanticSearchService`, pas par les endpoints
  list/get.

Si je manque un endpoint, indique-le et je l'utilise sans toucher `api-mail`.

## Recommandation

**Option A** — j'ajoute `api-mail` au `**Repos**:` du task file (commit forge
control plane) puis je relance `/develop task-011`. C'est l'intent
probable du PO ; le scope reste petit (~5 fichiers backend, additif), et la
livraison est en une seule US comme prevu par la regle 11.

## State a la halt

- Task file : `tasks/wip-task-011.md` (deja en wip — `/start` execute)
- Branches creees :
  - `client-blazor` : `feat/task-011-indicateur-document-integre` (pushed)
  - `dtos-mss` : `feat/task-011-indicateur-document-integre` (pushed, auto-included)
- `client-angular` : code-only, snapshot branch `feature/nova-rewriting-mss-fixes-20260410` (clean tree)
- `api-mail` : sur `develop`, **aucune branche `feat/task-011-*` creee** (le repo n'etait pas dans `**Repos**:`). Si Option A retenue, je creerai la branche en relancant `/start` ou directement.

Aucun code n'a ete ecrit. Aucun commit n'a ete fait sur les feature branches.

## Decision attendue

- **A** : etendre `**Repos**:` du task file pour inclure `api-mail` ; je cree la branche manquante et relance `/develop`.
- **B** : decouper en 2 tasks (je rename `wip-task-011.md` → `todo-task-011a.md` + cree `todo-task-011b.md`, et tu relances `/start task-011a`).
- **C** : tu pointes l'endpoint existant que j'ai manque, je continue purement frontend.
