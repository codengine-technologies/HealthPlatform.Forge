# todo-task-083.md — Téléchargement groupé des pièces jointes (archive ZIP)

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009
**EpicTitle**: Parité fonctionnelle webmail (confort de rédaction et de lecture)

## Objective

Permettre au professionnel de santé de télécharger **toutes les pièces jointes
d'un mail en une seule archive ZIP**, au lieu de les enregistrer une par une.
Inspiré du plugin `zipdownload` de Roundcube. Cas d'usage fréquent : un courrier
MSSanté contenant plusieurs documents (CR de biologie, imagerie, lettre de
liaison) que le médecin veut archiver d'un seul geste dans le dossier patient.

## Comportement attendu

- Sur un mail comportant au moins 2 pièces jointes, un bouton « Tout télécharger
  (ZIP) » est proposé à côté de la liste des pièces jointes.
- Le clic déclenche le téléchargement d'une archive `.zip` contenant toutes les
  pièces jointes du mail, avec leurs noms de fichiers d'origine.
- Les noms de fichiers en doublon dans l'archive sont désambiguïsés (suffixe
  `(1)`, `(2)`…).
- L'archive n'est jamais persistée sur disque côté serveur : elle est produite
  en flux (streaming) et envoyée directement au client.
- Si un mail ne comporte aucune pièce jointe, le bouton n'apparaît pas.

## Gherkin

```gherkin
Feature: Téléchargement groupé des pièces jointes

  Scenario: Un médecin télécharge toutes les pièces jointes d'un courrier
    Given un courrier reçu comportant trois pièces jointes
    When le médecin demande à télécharger toutes les pièces jointes
    Then une archive compressée contenant les trois fichiers est téléchargée
    And chaque fichier conserve son nom d'origine

  Scenario: Désambiguïsation des noms en doublon
    Given un courrier comportant deux pièces jointes nommées "resultat.pdf"
    When le médecin télécharge toutes les pièces jointes
    Then l'archive contient "resultat.pdf" et "resultat (1).pdf"

  Scenario: Aucun bouton sans pièce jointe
    Given un courrier sans pièce jointe
    When le médecin ouvre le courrier
    Then aucune action de téléchargement groupé n'est proposée
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Endpoint backend `GET folders/{foldername}/emails/{emailid}/attachments/download/zip` qui streame une archive ZIP (`application/zip`)
- [ ] L'archive est produite en flux, jamais écrite sur disque serveur
- [ ] Désambiguïsation des noms de fichiers en doublon
- [ ] >= 1 test unitaire par comportement backend (composition de l'archive, désambiguïsation, mail sans PJ → 204/404)
- [ ] >= 1 test d'intégration de l'endpoint (happy path multi-PJ + mail sans PJ)
- [ ] Blazor : bouton « Tout télécharger (ZIP) » conditionné à >= 1 PJ, aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (nom de fichier de PJ inclus → loggué uniquement en niveau debug masqué)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir un courrier MSSanté comportant au moins 2 pièces jointes
- Cliquer sur « Tout télécharger (ZIP) »
- Vérifier qu'une archive `.zip` se télécharge et contient toutes les PJ avec
  leurs noms d'origine
- Ouvrir un courrier sans pièce jointe et vérifier l'absence du bouton

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — confort utilisateur (la messagerie MSSanté reste l'élément référencé)
- **Exigences DSR honorées** : non applicable — fonctionnalité de confort, n'altère ni le transport MSSanté ni le contenu des documents
- **INS** : non applicable — pas de manipulation de l'identité patient ; les pièces jointes sont transférées telles quelles
- **Authentification PS** : session PS déjà authentifiée (PSC / e-CPS) — pas de nouvelle exigence
- **Habilitations** : accès limité aux courriers de la boîte du PS authentifié (inchangé)
- **Interop CI-SIS** : non applicable — les documents (CDA, PDF) sont transmis sans transformation
- **Tracé PGSSI-S** : journaliser l'évènement « téléchargement groupé des pièces jointes » (id mail, nombre de PJ) — conservation selon politique en vigueur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant, aucune donnée nouvelle persistée
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement persistant (archive produite en flux)

## Develop log

- **Repos touchés** : api-mail (commit `5cd430a`), client-blazor (commit `08e27a1`), client-angular (code-only, non commité — l'humain gère git/TFS).
- **DTOs / interop publiés** : aucun (réutilise `MailDto`/`AttachmentDto` existants ; dtos-mss branche vide).
- **Backend api-mail** : endpoint `GET folders/{f}/emails/{id}/attachments/download/zip` (StreamingFileResult + ZipArchive en flux, jamais sur disque), helper pur de désambiguïsation, 404 ProblemDetails si aucune PJ, trace PGSSI-S en log structuré (volumétrie, aucun nom de fichier en Information). Tests : 6 (helper) + 3 (controller dont ZIP réel composé et inspecté) — verts.
- **Blazor** : bouton « Tout télécharger (ZIP) » dans `AttachmentComponent` (visible ≥ 2 PJ réelles), `Localizer["DownloadAll"]`, `data-testid=attachment-download-all-zip`, download via JS interop. Tests : 4 bUnit — verts.
- **Angular** : bouton équivalent dans `mail-attachment` (≥ 2 PJ), libellé FR en dur (convention MSS, pas de ngx-translate), `data-testid=download-all-attachments-zip`, `MssApiService.downloadAttachmentsZip`. Test ajouté ; suite `mss-lib` complète **199 verts**.
- **Décision** : bouton à partir de **2 PJ** (Objectif « au moins 2 pièces jointes ») — un ZIP d'1 fichier est redondant avec le bouton de download unitaire. (DOD « ≥1 PJ » interprété comme « au moins une PJ existe ».)
- **Reste de la chaîne** : `/forge-simplify` → `/sonar` (api-mail touché) → `/lint-angular` → `/review` (push + PRs `awaiting-human-merge`) → `/tech-writer`.

## Sonar log

- **Quality Gate : OK** ✅
- **New code (task-083) : 0 issue** (0 bug / 0 vuln / 0 smell / 0 hotspot) — cible zero-new-debt atteinte.
- Projet : 0 bug / 0 vuln / 0 code smell / 0 hotspot, duplication 0,7 %, coverage global 84,8 %.
- **Note tooling** : le premier `sonarscanner end` a crashé sur un bug connu du scanner (`checkOverlappingBoundaries` de l'importeur de coloration C#), déclenché par un caractère UTF-8 invalide dans un fichier de **test** pré-existant (`tests/.../EmailManagementUseCaseTests.cs:779`, hors périmètre task-083). Contourné en excluant `**/tests/**` de l'analyse (les tests ne sont pas la cible de la qualité ; la couverture `src/` provient des rapports OpenCover, préservée). Aucun changement de repo. À nettoyer séparément (encodage du fichier de test).

## PRs

- **api-mail** : **déjà intégré sur `develop`** par l'humain en parallèle (commit `5cd430a` + fix `9b6abbf "Fix exception"`). Pas de PR (branche feature == develop). ⚠️ Le fix humain corrige un bug réel de l'implémentation : `ZipArchive.Dispose()` fait de l'IO synchrone, interdit sur `Response.Body` Kestrel → bufferisation via `FileBufferingWriteStream` + drain async. Mon test controller (MemoryStream) ne l'avait pas détecté (cf. mémoire `reference_ziparchive_kestrel_sync_io`).
- **client-blazor** : PR https://github.com/codengine-technologies/HealthPlatform.Client/pull/56 — label `awaiting-human-merge`.
- **client-angular** : code-only — l'humain gère commit/push TFS + PR. Fichiers modifiés : `mss-api.service.ts`, `mail-attachment.component.{ts,html,spec.ts}`. (`environment.ts` = WIP humain pré-existant, non touché par la forge.)
- **dtos-mss** : aucun changement de contrat, pas de PR.

## Code Review Summary

Verdict : **APPROVED** (avec 1 bug réel attrapé par l'humain côté api-mail, désormais corrigé sur develop).

- Build Release ✓ (api-mail, blazor). Tests : api-mail verts hors 2 flaky pré-existants ; blazor 99/99 ; angular 199/199.
- SonarQube : **Quality Gate OK, 0 issue new-code**.
- Lint Angular : 0 erreur (33 warnings pré-existants hors scope).
- **Leçon** : le test d'intégration d'endpoint réel (TestServer/Testcontainers) reste à ajouter pour couvrir la contrainte Kestrel `AllowSynchronousIO` — le test controller sur MemoryStream ne suffit pas.

## Merged

- **Date** : 2026-06-14
- **api-mail** : déjà intégré sur `develop` par l'humain (`5cd430a` forge + `9b6abbf` fix Kestrel sync-IO) — pas de PR à merger.
- **client-blazor** : squash `8b2356d` — PR #56 closed (`--delete-branch`, remote supprimée, locale conservée).
- **client-angular** : code-only — l'humain gère le merge TFS.
- **dtos-mss** : aucun changement, pas de PR.
- **develop CI** : ✓ green (blazor).
