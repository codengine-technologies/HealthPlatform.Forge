# todo-task-190.md — Impression et export PDF : 500 systématique sous Kestrel, et tableaux de résultats illisibles

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes surface HTTP et
> métier MSSanté).

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | Écriture synchrone du PDF | `MailExportController.cs:126-131` | **`:132-137`** — `StreamingFileResult` dont l'écrivain appelle `mailExportService.WritePdf(…, output)` puis `return Task.CompletedTask` | inchangé |
> | Rendu synchrone QuestPDF | `MailExportService.cs:88` | **`:102`** (`document.GeneratePdf(output)`) | inchangé |
> | Flux = `Response.Body` nu | `StreamingFileResult.cs:40` | **`:48`** (`await _writer(response.Body, …)`) | inchangé |
> | `AllowSynchronousIO` jamais activé | — | **confirmé : 0 occurrence** dans tout le repo | inchangé |
> | Patron correct déjà en place ailleurs | `MailController.cs:534-541` | **`:646-650`** — `FileBufferingWriteStream` pour le ZIP, avec le commentaire qui explique le piège | inchangé |
> | `TD`/`TH` sans séparateur | `MailExportService.cs:416-460` | `AppendNodeText` **`:437`** et suivantes ; `ExtractPlainBody` **`:388`** (préfère `BodyHtml`) ; appel **`:71`** | inchangé |
>
> **À savoir avant de livrer** : deux tests PDF de la suite `application` sont des
> **flaky pré-existants documentés** (`MailExportServiceTests.BuildPdfWithoutAttachmentsOmitsAttachmentSection`,
> `MarkdownPdfRendererTests.RenderHeadingPreservesText` — verts en isolation). Ne
> pas les lire comme une régression de cette task, et ne pas les compter comme la
> preuve demandée au point 2 : ils tournent sur `MemoryStream`, donc ils ne
> prouvent rien sur le refus des écritures synchrones.

## Objective

Rendre l'impression et l'export PDF **fonctionnels** et le document produit
**lisible**. Deux défauts distincts sur la même fonctionnalité :

1. **La fonctionnalité est cassée en exécution réelle** : le rendu PDF écrit
   **synchronement** dans le flux de réponse, ce que Kestrel interdit. Les deux
   endpoints (impression et export PDF) répondent donc `500`. Les tests unitaires ne
   le voient pas parce qu'ils exécutent le résultat contre un `MemoryStream`, qui
   accepte les écritures synchrones.
2. **Quand il sortira, le PDF sera inexploitable pour les tableaux** : les cellules
   HTML sont concaténées sans séparateur. Un hémogramme s'imprime en
   `Hémoglobine7,2g/dL13,0-17,0` — valeur, unité et intervalle de référence
   indiscernables. C'est précisément l'artefact qui rend un résultat imprimé
   inutilisable, voire mal interprétable, au point de soin.

**US backend-only (justification)** : rendu et streaming côté serveur.

### Preuve (état actuel du code)

**Écriture synchrone sur le flux de réponse** —
`src/Api/Controllers/V1/MailExportController.cs:126-131` retourne un
`StreamingFileResult` dont l'écrivain est
`(output, _) => { mailExportService.WritePdf(mail, practitioner, intent, output); return Task.CompletedTask; }`,
et `src/Application/Services/Implementation/MailExportService.cs:88` se termine par
`document.GeneratePdf(output)`. `GeneratePdf(Stream)` (QuestPDF) écrit de façon
**synchrone**, et `src/Api/Results/StreamingFileResult.cs:40` lui passe directement
`response.Body`. Kestrel refuse les écritures synchrones sur le corps de réponse
(`AllowSynchronousIO` est à `false` par défaut et n'est activé nulle part dans ce
repo) : `InvalidOperationException: Synchronous operations are disallowed`.

Le repo connaît déjà ce piège et l'a corrigé **ailleurs** :
`src/Api/Controllers/V1/MailController.cs:534-541` bufferise via
`FileBufferingWriteStream` précisément parce que « ZipArchive.Dispose() flushes …
with *synchronous* writes, which Kestrel forbids on the response body ». Le chemin
PDF n'a pas reçu le même traitement. Les voisins sont sains : l'export EML utilise
`MimeMessage.WriteToAsync`, l'export vCard `StreamWriter.WriteAsync`.

**Tableaux collés** —
`src/Application/Services/Implementation/MailExportService.cs:416-460` :
`AppendNodeText` traite `BR`, `LI`, `P/DIV/H1-H6/UL/OL/TR` et envoie tout le reste
au `default:` **sans séparateur**. `TD` et `TH` versent donc leur texte brut bout à
bout ; seule la fin du `TR` produit un `\n`. Et `ExtractPlainBody` (`:374-377`)
préfère `BodyHtml` dès qu'il est présent — c'est donc le chemin **normal** pour tout
message HTML imprimé par le praticien.

### Contenu attendu

1. **Écriture asynchrone du PDF** : bufferiser le rendu puis drainer le tampon de
   façon asynchrone vers le corps de réponse, en réutilisant le patron
   `FileBufferingWriteStream` déjà en place pour le ZIP — ne pas inventer un second
   mécanisme, et ne **pas** activer `AllowSynchronousIO` (ce serait masquer le
   problème à l'échelle du serveur).
2. **Test représentatif** : le test doit exercer un flux qui **refuse** les
   écritures synchrones, sinon le défaut reste invisible. C'est l'enseignement
   principal de ce finding : un test sur `MemoryStream` ne prouve rien ici.
3. **Séparation des cellules** : `TD`/`TH` doivent produire un séparateur lisible
   (espacement ou tabulation), et les tableaux de résultats de biologie doivent
   rester déchiffrables — libellé, valeur, unité, intervalle de référence
   distinguables.
4. **Vérification sur cas réels** : valider le rendu sur un hémogramme et un bilan
   biologique complets, pas seulement sur un tableau jouet.
5. **Balayage des autres endpoints de téléchargement** : vérifier qu'aucun autre
   chemin n'écrit synchronement dans la réponse (le ZIP est traité, l'EML et la
   vCard sont sains — confirmer qu'il n'existe pas d'autre cas).

### Hors scope

- La refonte de la mise en page du PDF (typographie, en-têtes) au-delà de la
  lisibilité des tableaux.
- La journalisation des exports, déjà en place (voir task-186 pour les PJ).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : `GET …/print` retourne `200` `application/pdf` (ce test
      doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test d'intégration : `GET …/export/pdf` retourne `200` `application/pdf`
- [ ] Ces deux tests s'exécutent contre un flux **refusant les écritures
      synchrones** (pas un `MemoryStream` permissif) — exigence explicite
- [ ] Test unitaire : un corps HTML contenant un tableau produit un texte où les
      cellules sont **séparées** (cas hémogramme : libellé, valeur, unité,
      intervalle discernables)
- [ ] Test unitaire de non-régression sur le reste de l'extraction de texte
      (paragraphes, listes, sauts de ligne inchangés)
- [ ] Aucun autre endpoint de téléchargement n'écrit synchronement dans la réponse
      (revue documentée dans la task)
- [ ] `AllowSynchronousIO` reste désactivé
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Ouvrir un message contenant un **tableau de résultats de biologie** en HTML
   (données de test anonymisées) — idéalement un hémogramme complet.
3. **Impression** : déclencher l'impression du message. **Attendu** : un PDF
   s'ouvre. Avant correctif : erreur générique, et dans Seq une
   `InvalidOperationException: Synchronous operations are disallowed`.
4. **Export PDF** : même vérification sur l'export.
5. **Lisibilité** : dans le PDF produit, vérifier que chaque ligne du tableau reste
   déchiffrable — `Hémoglobine`, `7,2`, `g/dL`, `13,0-17,0` séparés. Avant
   correctif : tout est collé.
6. **Non-régression** : exporter le même message en EML et une fiche contact en
   vCard → toujours fonctionnels.
7. Vérifier qu'un export de message **volumineux** (nombreuses pièces jointes,
   corps long) aboutit sans saturer la mémoire du serveur.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — restitution fidèle et
  exploitable des documents de santé reçus (impression au point de soin)
- **INS** : non applicable — l'INS peut figurer dans le document imprimé, ce qui est
  normal et attendu dans un document destiné au dossier patient (à ne pas confondre
  avec l'interdiction dans les **logs**, cf. task-184)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : le repli d'extraction concerne aussi le contenu de documents
  **CDA r2** — la lisibilité des tableaux vaut donc aussi pour les comptes-rendus
  structurés
- **Tracé PGSSI-S** : impression et export PDF sont **déjà** journalisés
  (`MailExportController`) — vérifier que la trace est toujours produite après
  correctif (ne pas régresser)
- **Consentement patient** : non applicable
- **Référentiels métier** : les intervalles de référence et unités des résultats de
  biologie doivent rester lisibles — enjeu de sécurité d'interprétation clinique
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement. Signaler au humain
  que la fonctionnalité était **inopérante** en exécution réelle : les praticiens
  n'ont pas pu imprimer depuis la mise en place de ce chemin.
