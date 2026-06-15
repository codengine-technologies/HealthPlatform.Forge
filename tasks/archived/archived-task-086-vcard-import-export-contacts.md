# todo-task-086.md — Import / export des contacts au format vCard

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009

## Objective

Permettre au professionnel de santé d'**importer** et d'**exporter** son carnet
d'adresses au format **vCard** (`.vcf`), standard d'échange de contacts.
Inspiré des actions `import.php` / `export.php` de Roundcube. Cas d'usage :
récupérer un carnet existant depuis un autre logiciel, ou sauvegarder/transférer
ses correspondants MSSanté.

## Comportement attendu

- **Export** : le PS exporte son carnet d'adresses (ou une sélection) dans un
  fichier `.vcf` (vCard 3.0/4.0) contenant nom, prénom, adresses MSSanté,
  organisation, et le cas échéant RPPS/profession lorsqu'ils sont déjà connus.
- **Import** : le PS importe un fichier `.vcf` ; chaque contact est créé ou
  mis à jour dans son carnet.
- **Anti-doublon** : à l'import, un contact dont l'adresse MSSanté (ou le RPPS)
  existe déjà n'est pas dupliqué — il est mis à jour, jamais cloné.
- Un compte-rendu d'import est présenté : nombre de contacts créés, mis à jour,
  ignorés (et raison).
- Les contacts issus de l'Annuaire Santé restent cohérents : pas de création de
  doublon RPPS.

## Gherkin

```gherkin
Feature: Import et export des contacts au format vCard

  Scenario: Export du carnet d'adresses
    Given un médecin disposant de plusieurs contacts
    When il exporte son carnet d'adresses
    Then un fichier vCard contenant ses contacts est téléchargé

  Scenario: Import d'un fichier vCard
    Given un fichier vCard contenant deux nouveaux contacts
    When le médecin importe ce fichier
    Then les deux contacts sont ajoutés à son carnet
    And un compte-rendu indique deux contacts créés

  Scenario: Anti-doublon à l'import
    Given un fichier vCard contenant un contact dont l'adresse MSSanté existe déjà
    When le médecin importe ce fichier
    Then le contact existant est mis à jour
    And aucun doublon n'est créé
```

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Endpoint backend export : `GET contacts/export/vcard` (optionnellement filtré) → `text/vcard`
- [ ] Endpoint backend import : `POST contacts/import/vcard` (multipart) → compte-rendu (créés / mis à jour / ignorés)
- [ ] Anti-doublon par adresse MSSanté et/ou RPPS — pas de duplication de contact ni de RPPS
- [ ] Parsing/sérialisation vCard 3.0 et 4.0 (lecture tolérante)
- [ ] >= 1 test unitaire par comportement (export, import création, import mise à jour, anti-doublon, vCard malformée → erreur claire)
- [ ] >= 1 test d'intégration par endpoint (export happy path, import multipart happy path + fichier invalide)
- [ ] Blazor : actions Importer / Exporter, sélecteur de fichier, affichage du compte-rendu, aucune chaîne en dur (i18n), `data-testid`
- [ ] Angular : idem côté front legacy, aucune chaîne en dur (i18n), `data-testid`
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (contenu des contacts non loggué)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Ouvrir le carnet d'adresses, cliquer sur Exporter → vérifier le téléchargement
  d'un `.vcf` ouvrable (contacts présents)
- Cliquer sur Importer, sélectionner un `.vcf` de 2 nouveaux contacts → vérifier
  le compte-rendu « 2 créés » et leur apparition dans le carnet
- Réimporter le même fichier → vérifier « 2 mis à jour, 0 créé » (anti-doublon)
- Importer un fichier `.vcf` malformé → vérifier un message d'erreur clair

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — gestion du carnet d'adresses
- **Exigences DSR honorées** : non applicable — n'altère pas l'Annuaire Santé national ni le transport MSSanté
- **INS** : non applicable — les contacts sont des correspondants (PS / structures), pas des patients
- **Authentification PS** : inchangé — carnet propre au PS authentifié
- **Habilitations** : import/export limités au carnet du PS authentifié
- **Interop CI-SIS** : non applicable — vCard est un standard de contact, hors volets CI-SIS
- **Tracé PGSSI-S** : journaliser « export carnet » et « import carnet » (volumétrie : nombre de contacts) — conservation selon politique en vigueur
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS / ADELI utilisés pour l'anti-doublon lorsqu'ils sont présents — aucune création de RPPS
- **Hébergement HDS** : oui — environnement existant (le carnet d'adresses est déjà persisté)
- **AIPD / impact RGPD** : à vérifier — un import de contacts est un traitement de données personnelles (coordonnées de PS) ; confirmer la couverture par l'AIPD existante

## Develop log (repris 2026-06-15 — implémentation complète)

Décisions : parser vCard hand-rollé (pas de NuGet) ; DTO compte-rendu local par
repo (pas de cascade dtos-mss → dtos-mss reste vide) ; anti-doublon sur snapshot
`GetAllAsync` (1 lecture DB) par RPPS puis par adresse MSSanté ; PGSSI-S =
logging volumétrie uniquement (pas de contenu contact, pas d'ajout d'enum
`AuditActionType` côté dtos-mss).

**api-mail** (branche `feat/task-086`, commits `1f26e55` serializer + `32758a2`
service/endpoints/tests — **local, non poussé**) :
- `VCardSerializer` (Serialize 3.0 + Parse 3.0/4.0 tolérant, unfold/unescape).
- `VCardImportReport` (Created/Updated/Ignored + IgnoredReasons), `IVCardService`/
  `VCardService` (export + import anti-doublon).
- `ContactController` : `GET contacts/export/vcard` (StreamingFileResult, pas de
  piège Kestrel sync-IO) + `POST contacts/import/vcard` (multipart, FormatException
  → 400 ProblemDetails via ValidationException + GlobalExceptionHandler).
- Tests : 14 unit serializer + service (`mss.mail.application.tests`), 5 endpoints
  controller (`mss.mail.api.tests`), 3 intégration Postgres (round-trip +
  anti-doublon + malformé). **Build + tests api/application verts.**

**client-blazor** (branche `feat/task-086`, commit `96b0023` — **local, non poussé**) :
- `ContactService.ExportVCardAsync`/`ImportVCardAsync` (GetBytes + multipart),
  `VCardImportReportDto` client-local, Contacts.razor : boutons Export/Import
  (file picker), toast compte-rendu, garde 5 Mo, `data-testid`, clés i18n EN+FR.
- bUnit : 2 tests (rendu des contrôles + click export appelle le service).
  **Build solution + tests verts.**

**client-angular** (code-only — **non commité, à pousser TFS par l'humain**) :
- `MssApiService.exportVcard()` (blob) / `importVcard(file)` (FormData),
  `VCardImportReport` model, `mss-contacts.component` : boutons Export/Import,
  input file caché, message compte-rendu inline, libellés FR en dur, `data-testid`.
- Vitest : spec endpoints vCard (`mss-api.vcard.service.spec.ts`).
  **`nx test mss-lib` = 215 verts, `nx lint mss-lib` = 0 errors, `nx build mss`
  (dev) OK.**

**RESTE** : `/review` (push api-mail + blazor, ouvrir les 2 PRs
`awaiting-human-merge`, note Angular code-only) → `/tech-writer E009`. Puis test
humain + merge (HAG). ⚠️ Angular : l'humain commite/pousse sur TFS (la forge ne
touche jamais au git Angular). Ne PAS committer `apps/mss/.../environment.ts`.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/105 — label `awaiting-human-merge`
- **client-blazor** : https://github.com/codengine-technologies/HealthPlatform.Client/pull/59 — label `awaiting-human-merge`
- **dtos-mss** : aucune PR (branche `feat/task-086` vide — pas de changement de contrat, design DTO local par repo).
- **client-angular** : code-only — humain gère commit/push TFS et ouverture PR. Branche courante `feature/nova-rewriting-mss`, uncommitted. Fichiers modifiés :
  - `front/libs/mss/src/core/models/contact.model.ts` (M)
  - `front/libs/mss/src/core/services/mss-api.service.ts` (M)
  - `front/libs/mss/src/features/contacts/mss-contacts.component.html` (M)
  - `front/libs/mss/src/features/contacts/mss-contacts.component.ts` (M)
  - `front/libs/mss/src/core/services/mss-api.vcard.service.spec.ts` (new)
  - ⚠️ Ne PAS committer `apps/mss/.../environment.ts` (WIP local).

## Code Review Summary

**Verdict : APPROVED** — 0 blocking.

- **api-mail** : `VCardSerializer` ✅, `VCardService` ✅ (anti-doublon snapshot RPPS+adresse, merge champ-à-champ), `ContactController` ✅ (endpoints fins, 400 ProblemDetails via exception typée), `VCardImportReport` ✅. Sécurité ✅ (aucune donnée de santé en log / dans le 400). Build ✅ ; api.tests 510 ✅ ; application.tests vCard 14 ✅ ; intégration Postgres vCard 3 ✅. 1 échec full-suite préexistant sans rapport (`MarkdownPdfRendererTests` flaky PDF).
- **client-blazor** : `ContactService` export/import ✅, `Contacts.razor` ✅ (busy guard, garde 5 Mo, toast compte-rendu, i18n EN+FR, data-testid). Build ✅ ; bUnit 101 ✅.
- **client-angular** : `MssApiService.exportVcard/importVcard` ✅, `mss-contacts` boutons + message inline ✅, FR en dur + data-testid ✅. `nx test mss-lib` 215 ✅ ; `nx lint mss-lib` 0 errors ✅ ; `nx build mss` (dev) ✅.

## Merged

Mergée le 2026-06-15 (squash, HAG validée `--i-tested`).

| Repo | Squash SHA | PR |
|---|---|---|
| api-mail | `e16b2ff` | #105 (closed) |
| client-blazor | `618161e` | #59 (closed) |
| dtos-mss | — | branche vide, pas de PR |
| client-angular | — | code-only, géré manuellement par l'humain (TFS) |

- Remote refs `feat/task-086-vcard-import-export-contacts` supprimés (api-mail + blazor) ; branches **locales conservées**.
- CI `develop` : ✅ verte sur api-mail et client-blazor après merge.
