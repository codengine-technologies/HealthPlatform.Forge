# todo-task-095-mobile-inbox-folders.md — Socle features/mail + parité Inbox + sélection de répertoire

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: none
**Epic**: E012
**EpicTitle**: Client mobile MSSanté

## Objective

Poser le **socle d'architecture miroir** du client mobile sur la base de
`client-angular` (lib `front/libs/mss`), puis livrer une première tranche
verticale démontrable : **sélectionner un répertoire** et **afficher la liste
des emails** d'un dossier avec **exactement le même contenu de ligne** que le
client Angular (aucune perte fonctionnelle d'affichage).

Le code mobile actuel est *page-based* (`inbox.page` fait tout). Cette US le
**refactore** vers la structure de composants/services d'Angular, en
reprenant **les mêmes noms et le même découpage** pour faciliter le travail
de l'IA et garantir la parité.

### Structure cible (miroir de `client-angular/front/libs/mss/src`)

```
Client/Mobile/src/app/
├── core/
│   ├── models/                       # split de l'actuel core/mss/models.ts
│   │   ├── mail.model.ts             # MailDto, MailAddressDto, AttachmentDto,
│   │   │                             #   MailContentDto, TagDto, MailEnrichmentStatus
│   │   ├── folder.model.ts           # FolderDto, FolderType, FolderSource, VIRTUAL_DRAFTS_PATH
│   │   ├── patient.model.ts          # MailPatientDto (identité + INS)
│   │   ├── biology-ack.model.ts      # (posé ici, exploité en task-098)
│   │   └── draft.model.ts            # (posé ici, exploité en task-100)
│   └── services/
│       └── mss-api.service.ts        # déplacé depuis core/mss/, périmètre élargi
├── features/
│   └── mail/
│       ├── components/
│       │   ├── mail-list/            # mss-mail-list (hôte de la liste)
│       │   ├── mail-header/          # mss-mail-header (1 ligne d'email)
│       │   ├── mail-folder-list/     # mss-mail-folder-list (arbre des dossiers)
│       │   └── mail-folder-item/     # mss-mail-folder-item (1 dossier, récursif)
│       └── services/
│           ├── mail-state.service.ts # signals : folders, selectedFolder, emails,
│           │                         #   pagination, selectedMail, selectedMailUids
│           └── mail-event.service.ts # bus RxJS : mailSelected$, folderChanged$,
│                                     #   refreshMailList$
```

Composants en **standalone Angular + primitives Ionic** (remplacent PrimeNG).
Sélecteurs miroir : `mss-mail-list`, `mss-mail-header`, `mss-mail-folder-list`,
`mss-mail-folder-item`. La page `inbox.page` devient un **hôte mince** qui
projette `mss-mail-folder-list` + `mss-mail-list`.

### Parité du contenu de ligne (mss-mail-header)

La ligne d'email doit afficher **le même contenu** que `MailHeaderComponent`
d'Angular (`features/mail/components/mail-header`) :

- Sujet d'affichage = **titre du document médical s'il existe**, sinon objet du mail (`displaySubject`)
- Nom de l'expéditeur (`senderName`) et **identité patient** si présente (`patientIdentityDisplay`)
- Date d'envoi
- Indicateur **pièces jointes** + compteur (`hasAttachments`, `attachmentCount`)
- Indicateur **documents médicaux** (`hasMedicalDocuments`)
- Indicateur **biologie flaggée** (`flaggedBiologyResults` — compteur visuel)
- **Tags** (pastilles couleur) en lecture seule
- État **lu / non-lu** (typo + pastille) et **flag**
- Indicateur **intégration patient en attente** si applicable (`pendingIntegrationsCount`)

> Le rendu utilise les composants Ionic (ion-item, ion-badge, ion-icon, ion-chip)
> mais **le contenu informationnel est identique** à Angular. Les *actions*
> (lu/non-lu, flag, suppression) arriveront en task-099 — ici la ligne est en
> lecture/sélection.

### Sélection de répertoire (mss-mail-folder-list + mss-mail-folder-item)

- Liste/arbre des dossiers IMAP avec **compteurs non-lus** (parité `MailFolderListComponent`)
- Sélection d'un dossier → recharge la liste d'emails du dossier sélectionné
- Présentation mobile : `ion-menu` latéral OU `ion-list` repliable (au choix
  du dev, mais composants nommés `mss-mail-folder-list`/`mss-mail-folder-item`)
- `mss-mail-folder-item` récursif pour les sous-dossiers (`level` pour l'indent)

### Périmètre API (mss-api.service)

Méthodes nécessaires ici (calquées sur `MssApiService` d'Angular) :
`getFolders()`, `getFolder(path)`, `getEmails(folderPath, uids)`,
`getEmailContent` (déjà présent, conservé). Aucune création d'endpoint backend
— ils existent déjà (consommés par `client-angular`).

## Scénarios d'acceptation

1. **Lister les répertoires** — Étant connecté en PSC, quand j'ouvre l'inbox,
   alors je vois la liste de mes répertoires avec leur nombre de non-lus.
2. **Sélectionner un répertoire** — Quand je sélectionne un répertoire,
   alors la liste affiche les emails de ce répertoire (les plus récents).
3. **Parité de ligne** — Pour un email donné, la ligne mobile affiche les
   mêmes informations que la ligne Angular (titre/doc médical, expéditeur,
   identité patient, date, badges PJ/doc médical/biologie, tags, lu-non-lu, flag).
4. **Ouvrir un email** — Quand je tape sur une ligne, alors je navigue vers le
   détail (route existante `mail/:folderPath/:uid`).
5. **Rafraîchir** — Le pull-to-refresh recharge le répertoire courant.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreurs)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échecs)
- [ ] Structure `features/mail/` + `core/models/` + `core/services/` en place (miroir Angular)
- [ ] Composants `mss-mail-list`, `mss-mail-header`, `mss-mail-folder-list`, `mss-mail-folder-item` créés (standalone)
- [ ] Services `mail-state.service` (signals) et `mail-event.service` (RxJS) créés
- [ ] `inbox.page` refactorée en hôte mince projetant les composants miroir
- [ ] La ligne `mss-mail-header` affiche **tous** les éléments de parité listés (titre doc médical, identité patient, badges PJ/doc médical/biologie, tags, lu-non-lu, flag)
- [ ] Sélection d'un répertoire recharge la liste ; compteurs non-lus affichés
- [ ] Aucune régression : login + navigation vers le détail fonctionnent toujours
- [ ] Libellés FR en dur (pas de ngx-translate — convention MSS)
- [ ] `data-testid` sur les éléments interactifs (ligne email, item dossier, bouton refresh)
- [ ] Tests composant : `mss-mail-header` (rendu d'une ligne avec doc médical + badges), `mss-mail-folder-item` (rendu + sélection)
- [ ] Tests service : `mail-state.service` (sélection dossier, MAJ liste), `mss-api.service` (getFolders/getEmails mockés)
- [ ] Types DTO mobile alignés sur les contrats backend (mêmes champs que `mail.model.ts`/`folder.model.ts` Angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, contenu, identité patient)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run` (expose l'API sur https://localhost:7012, cf. proxy.conf.json)
- Lancer le mobile : `cd Client/Mobile && npm start`
- Ouvrir l'app dans le navigateur (mode responsive mobile) et se connecter via PSC
- **Vérifier** : la liste des répertoires s'affiche avec les compteurs non-lus
- Sélectionner différents répertoires → la liste d'emails change
- **Comparer** une même boîte côte à côte avec `client-angular` (`cd Client/Angular && npm start`) :
  les lignes doivent montrer les **mêmes** titre, identité patient, badges, tags, état lu/non-lu
- Taper sur un email → arrive sur le détail
- Pull-to-refresh → la liste se recharge

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté (consultation), Identito-vigilance (affichage identité patient)
- **INS** : affichage de l'identité patient (INS incluse) au PS authentifié — jamais en clair dans logs/URL/sujets
- **Authentification PS** : PSC / e-CPS (déjà en place côté mobile), niveau eIDAS substantiel
- **Habilitations** : RPPS via claim PSC (back)
- **Interop CI-SIS** : non applicable directement — les métadonnées de document médical proviennent du CDA déjà parsé côté `interop-cda` (back)
- **Tracé PGSSI-S** : consultation de la liste et ouverture de répertoire journalisées côté backend — conservation 6 ans
- **Consentement patient** : non applicable (lecture de la boîte du PS)
- **Référentiels métier** : aucun à ce stade (LOINC arrive avec la biologie, task-098)
- **Hébergement HDS** : oui — l'app mobile ne stocke pas de DSCP en clair hors session
- **AIPD / impact RGPD** : inchangé — réplication mobile d'un affichage déjà tracé côté Angular/back

## Branches
- `client-mobile` (pushed) : feat/task-095-mobile-inbox-folders — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-095-mobile-inbox-folders

> Single frontend (`client-mobile` only). Pas de `dtos-mss` (ni api-mail ni client-blazor dans Repos). Aucun autre repo touché.

## Develop log

- Repos touched : client-mobile (pushable, full git automation)
- DTOs published : no DTO change (mobile consume les contrats via types TS)
- Structure miroir créée :
  - core/models/{mail,folder,patient,biology-ack,draft}.model.ts + index.ts
  - core/utils/xdm-subject.utils.ts
  - core/services/mss-api.service.ts (déplacé depuis core/mss/, élargi)
  - features/mail/services/{mail-state (signals), mail-event (RxJS)}.service.ts
  - features/mail/components/{mail-list, mail-header, mail-folder-list, mail-folder-item} (standalone)
  - inbox.page refactorée en hôte mince (split-pane dossiers + liste)
  - mail-detail.page : imports re-câblés vers core/models + core/services
  - core/mss/{models,mss-api.service}.ts supprimés
- Parité ligne (mss-mail-header) : displaySubject (titre doc médical), identité patient (nom+INS), badges PJ/document médical/biologie (drapeaux serveur), version CDA, tags, lu/non-lu, flag, annulé
- Local build : ✓ (npm run build, 0 erreurs ; 1 warning NG8107 pré-existant dans mail-detail.page.html, hors scope)
- Local tests : ✓ 20/20 (npm test --watch=false --browsers=ChromeHeadless) — 16 nouveaux + 4 pré-existants
- Commit : client-mobile @228b2e1 (pushed sur feat/task-095-mobile-inbox-folders)
- DOD self-check : tous les items vérifiables OK
- Next step : /forge-simplify task-095 → /lint-mobile → /review → /tech-writer E012

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/1 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED (quality-only, pas de chasse aux bugs)
- Build ✓ (npm run build) · Tests ✓ 20/20 (Karma headless) · Lint ✓ clean
- Parité structurelle Angular respectée ; composants standalone + services signals/RxJS
- FR en dur, data-testid présents, aucune donnée de santé en clair
- 1 warning NG8107 pré-existant dans mail-detail.page.html (hors scope, à traiter en task-096)

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- client-mobile : develop @f456a09 (PR #1 closed)
- develop CI : aucune CI configurée sur le repo (fresh) — N/A
- Local feature branch conservée (pas de --delete-branch)
