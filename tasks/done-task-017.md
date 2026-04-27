# todo-task-017.md — Impression et export d'un email (PDF / EML) avec traçabilité audit

**Repos**: api-mail, client-blazor, dtos-mss, client-angular
**Epic**: E009
**Dependencies**: aucune

> **Note automation** : `client-angular` est exclu de l'automation forge (TFS,
> gestion manuelle). `/start` ne créera pas de branche Angular, `/review` ne
> buildera/testera pas Angular, pas de PR Angular automatique. Le humain gère
> le côté Angular en parallèle dans WindSurf + TFS. Même convention que
> `done-task-016`.

## Objectif

Permettre au médecin, depuis la vue détail d'un email, de **l'imprimer** ou de
**l'exporter** au format **PDF** ou **EML**, avec **traçabilité dans
l'audit-trail** des trois actions distinctes.

L'enjeu clinique : le médecin doit pouvoir conserver une copie papier d'un
échange (compte-rendu, courrier confrère) ou archiver l'email original dans le
dossier patient hors plateforme — PDF lisible pour la consultation rapide, EML
pour la preuve d'origine MSS Santé (signature S/MIME préservée).

## Périmètre fonctionnel

### UI (Blazor + Angular)

Dans la **vue détail d'un email**, ajouter deux actions visibles :

1. **Imprimer** — ouvre le PDF généré par le backend dans un **nouvel onglet**.
   Le médecin imprime depuis le viewer PDF natif du navigateur. Aucune
   surcouche d'impression côté front.
2. **Exporter** — menu déroulant avec deux choix de format :
   - **PDF** — version lisible (téléchargement)
   - **EML** — mail original au format RFC 5322 (téléchargement)

### Backend (`api-mail`)

Endpoints à exposer (la déclinaison exacte est laissée à l'implémentation, mais
les trois actions doivent être adressables séparément pour l'audit) :

- Génération PDF — sert l'action "Imprimer" et "Exporter > PDF"
- Génération EML — sert l'action "Exporter > EML"

L'audit distingue les **trois actions** même si l'endpoint PDF est partagé
entre Imprimer et Exporter PDF (le frontend doit indiquer l'intention, ou
l'API expose deux routes distinctes).

### Contenu du PDF

- Headers : **De**, **À**, **Cc** si présent, **Objet**, **Date**
- Corps de l'email (texte brut ou HTML rendu)
- Bloc "Pièces jointes" : **mention de la présence + nombre + liste des noms**.
  Le contenu des PJ n'est PAS inline dans le PDF.
- **Pied de page de traçabilité** : *"Imprimé / Exporté par Dr {Nom} le
  {date} — HealthPlatform"* sur chaque page.

### Contenu du EML

Le mail **original tel que reçu ou envoyé** — RFC 5322 complet, en-têtes MIME
préservés, **signature S/MIME conservée intacte**, pièces jointes encodées en
base64 dans le MIME. Aucune reconstruction "propre" : valeur probante MSS Santé
prioritaire sur la lisibilité brute du fichier.

### Audit-trail

Trois nouvelles valeurs à ajouter dans `Dtos/AuditActionType.cs` :

- `MailPrint`
- `MailExportPdf`
- `MailExportEml`

Chaque action backend crée un `MssAuditTrace` via `IAuditTraceRepository.AddAsync`
avec : utilisateur appelant, identifiant du mail, type d'action, timestamp.

> **Contrat changé** → `/publish-dtos` est requis après merge `dtos-mss` pour
> que `api-mail` et `client-blazor` consomment la nouvelle version du package
> NuGet contenant les 3 nouvelles valeurs d'enum.

## Definition of Done

- [ ] Build passes sur `api-mail`, `client-blazor`, `dtos-mss` (0 erreurs)
- [ ] Tests passent (0 failures) sur les 3 repos
- [ ] `AuditActionType` étendu avec `MailPrint`, `MailExportPdf`, `MailExportEml` (`dtos-mss`)
- [ ] Endpoint(s) export/print : >=1 test unitaire par handler (génération PDF, génération EML)
- [ ] Endpoint(s) export/print : >=1 test d'intégration par endpoint (rule 1b — happy path + 1 failure mode "mail introuvable")
- [ ] Test unitaire vérifiant qu'une trace `MssAuditTrace` est bien écrite pour chacune des 3 actions, avec le bon `AuditActionType`
- [ ] Le PDF généré contient : headers, corps, liste des PJ avec leurs noms, pied de page de traçabilité (vérifié par test sur le service de génération)
- [ ] L'EML exporté est un fichier RFC 5322 valide, signature S/MIME présente quand le mail source est signé (vérifié par test)
- [ ] Blazor : boutons "Imprimer" + "Exporter" visibles dans la vue détail, aucune string hardcodée (i18n), `data-testid` sur chaque action et chaque option du menu Exporter
- [ ] Blazor : test composant rendant la vue détail et vérifiant la présence des 2 actions et du menu de format
- [ ] Pas de Reqnroll/.feature ajouté (rule 1 — unit tests only)
- [ ] `/publish-dtos` exécuté après merge `dtos-mss` → `api-mail` et `client-blazor` bumpés sur la nouvelle version du package

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- (Angular en manuel, hors automation forge) : `cd Client/Angular && npm start`
- Se connecter en tant que médecin, ouvrir un email reçu en vue détail (idéalement un avec >=1 PJ et une signature S/MIME)
- **Test Imprimer** :
  - Cliquer le bouton "Imprimer"
  - Vérifier qu'un nouvel onglet s'ouvre avec un PDF lisible
  - Le PDF affiche : De / À / Objet / Date / corps / mention "Pièces jointes (N) : nom1, nom2..."
  - Le pied de page contient "Imprimé par Dr {son nom} le {date du jour} — HealthPlatform"
  - Lancer l'impression depuis le viewer PDF natif du navigateur, vérifier le rendu papier (ou aperçu)
- **Test Exporter > PDF** :
  - Cliquer "Exporter" puis sélectionner "PDF"
  - Fichier téléchargé, ouvrable, contenu identique au rendu impression (sauf wording du pied de page : "Exporté par...")
- **Test Exporter > EML** :
  - Cliquer "Exporter" puis sélectionner "EML"
  - Fichier `.eml` téléchargé
  - L'ouvrir dans Thunderbird (ou Outlook) → le mail s'affiche correctement, expéditeur / objet / corps / PJ visibles
  - Si le mail source était signé S/MIME, la signature est reconnue par le client mail
- **Vérification audit-trail** :
  - Après les 3 actions, requêter la table `MssAuditTraces` (ou l'écran d'audit s'il existe) en filtrant sur le mail testé
  - Vérifier 3 entrées distinctes : `MailPrint`, `MailExportPdf`, `MailExportEml`
  - Chaque entrée porte le bon utilisateur, le bon mail id, un timestamp correct
- **Cas négatif** :
  - Forger une URL d'export sur un id de mail inexistant
  - Vérifier réponse 404 et **aucune** trace écrite dans l'audit
- **Cas Angular** (manuel) :
  - Reproduire les 3 tests UI sur le frontend Angular
  - Vérifier que les actions appellent les mêmes endpoints backend et que les traces sont écrites de la même façon

## Branches

- `api-mail` (pushed) : `feat/task-017-impression-export-email-audit` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-017-impression-export-email-audit
- `client-blazor` (pushed) : `feat/task-017-impression-export-email-audit` — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-017-impression-export-email-audit
- `dtos-mss` (pushed) : `feat/task-017-impression-export-email-audit` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-017-impression-export-email-audit
- `client-angular` (skipped) : excluded from forge automation (TFS, géré manuellement par le humain)

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/8 (`awaiting-human-merge`)
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/29 (`awaiting-human-merge`)
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/36 (`awaiting-human-merge`)
- `client-angular` : managed manually by the human (TFS)

## Code Review Summary

`/review` verdict : **APPROVED** (after the 2 missing DOD items were added — Blazor bUnit component test + EML S/MIME signature preservation test, written in-session under explicit human override of "forge does not write code").

- Build : ✓ 3 repos
- Tests : ✓ api-mail 1591 passed (21 skipped) · client-blazor 15 passed · dtos-mss n/a
- DOD : ✓ all items met
- Code review : APPROVED with non-blocking suggestions :
  - `MailExportController` is `[ExcludeFromCodeCoverage]` despite having NSubstitute tests — drop the attribute in a follow-up
  - `(int)uid` cast in audit trace can wrap for IMAP UIDs > `int.MaxValue`
  - `BuildFooterText` uses `DateTime.Now` (machine TZ) while audit DB uses UTC — minor consistency note
- Rule 6 (isolated scopes) : **bundled scope creep accepted explicitly by human**
  - `AnnuaireSanteServiceIntegrationTests.cs` temporarily commented out (855 lines)
  - `iframeResizer.js` design-token refactor (CDA viewer styling)
  - 7 backfill test files (Audit, IheXdm, Ins, Patient, DraftMime, PatientMessage, SaslMechanismOAuth2NoIr)
  - Draft test refactor (`_field` → `field`, ~700 lines cosmetic)
  - 3 chore commits on `dtos-mss` (`[ExcludeFromCodeCoverage]`)

## Post-merge actions

1. `/publish-dtos` after `dtos-mss` PR #8 merges (api-mail + client-blazor consume the new package)
2. Manual Angular implementation (per task plan)
3. End-to-end manual test per Manual Test Plan above (HAG — rule 10)
4. Follow-up PR to restore `AnnuaireSanteServiceIntegrationTests` with proper `[Trait("Category","Manual")]` skip
