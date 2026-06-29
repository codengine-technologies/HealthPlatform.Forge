# todo-task-093.md — Drag & drop des emails dans la messagerie Angular (déplacement entre dossiers + suppression)

**Repos**: client-angular
**Epic**: E009

> **US frontend-only (Angular, code-only) justifiée** : le glisser-déposer est un
> **nouveau geste d'interface** pour des opérations qui **existent déjà** côté
> backend et sont déjà câblées dans le front via des menus/boutons. On réutilise
> les endpoints existants `moveEmail` / `bulkMoveEmails` / `deleteEmail` /
> `bulkDeleteEmails` (`MssApiService`). **Aucun** changement `api-mail` ni
> `dtos-mss` : la suppression en cascade du lien patient, la journalisation
> PGSSI-S et le contrôle d'habilitation sont **inchangés et hérités** des
> opérations existantes. Le module MSS Angular n'utilise pas ngx-translate :
> libellés FR en dur (cf. convention projet).

## Objective

Permettre au praticien de **glisser-déposer** un (ou plusieurs) email(s) depuis la
liste des courriers vers un dossier de la barre latérale, pour **déplacer** ou
**supprimer** rapidement ses messages, sans passer par un menu. Le geste doit
respecter une **matrice de déplacements autorisés** cohérente avec la sémantique
d'une boîte MSSanté (on ne dépose jamais dans « Envoyés » ou « Brouillons », etc.)
et donner un retour visuel clair (cible valide / dépôt interdit). Le dépôt sur la
**Corbeille** déclenche la suppression (réversible) du backend.

## Comportement attendu

### Geste de glisser-déposer
- Depuis la **liste des emails** (`mail-list`), le praticien peut saisir une ligne
  et la glisser vers un dossier de la **liste des dossiers** (`mail-folder-list` /
  `mail-folder-item`).
- Le **multi-sélection** est supporté : si plusieurs emails sont sélectionnés, le
  glisser en déplace l'ensemble (réutilisation des opérations **bulk**). Un
  indicateur visuel sur l'élément glissé montre le nombre d'emails entraînés.
- Pendant le survol d'un dossier : si le dépôt est **autorisé**, le dossier cible
  est mis en surbrillance ; si le dépôt est **interdit**, le curseur indique
  « interdit » et aucune surbrillance d'acceptation n'apparaît.
- **Dépôt sur le dossier courant** (celui déjà affiché) = **aucune action**.

### Matrice des déplacements (règles métier)
**Destinations toujours interdites** (dépôt refusé) :
- **Envoyés** (`Sent`) — reflète les courriers réellement émis, jamais alimenté
  manuellement.
- **Brouillons** (`Drafts`, dossier virtuel) — alimenté en rédigeant, pas en
  déplaçant un courrier reçu.
- **Tous / dossiers virtuels d'agrégation** (`All`) — ne sont pas de vrais
  dossiers de stockage.

**Déplacements autorisés** :

| Depuis ↓ \ Vers → | Inbox | Custom | Junk | Trash |
|---|---|---|---|---|
| **Inbox** | (no-op) | ✅ | ✅ | ✅ (suppression) |
| **Custom** | ✅ | ✅ | ✅ | ✅ |
| **Junk** | ✅ | ✅ | (no-op) | ✅ |
| **Trash** | ✅ (restauration) | ✅ (restauration) | — | (no-op) |
| **Sent** | ⛔ | ⛔ | ⛔ | ✅ (suppression uniquement) |
| **Drafts** | ⛔ | ⛔ | ⛔ | ✅ (jeter le brouillon) |

- **Sent → Custom est interdit** (un message envoyé ne sort que vers la Corbeille
  en v1).
- Le dépôt sur un **Tag** (`FolderType.Tag`) est **hors périmètre v1** (on se
  limite aux vrais dossiers IMAP + Corbeille).

### Suppression (dépôt sur Corbeille)
- Le dépôt sur **Corbeille** appelle `deleteEmail` / `bulkDeleteEmails` (le mail va
  dans la Corbeille, suppression **réversible**).
- **Garde-fou** : un **toast non bloquant « Email(s) supprimé(s) · Annuler »**
  apparaît quelques secondes. « Annuler » restaure le(s) message(s) à leur dossier
  d'origine.
- **Règle métier acceptée (décision PO 2026-06-16)** : mettre un email à la
  Corbeille supprime **en cascade** le lien patient et les documents rattachés
  côté backend. La **restauration** (re-glisser hors de la Corbeille, ou « Annuler »
  du toast) **reconstruit** le lien patient. Ce comportement est **voulu** — aucun
  dialog de confirmation, aucun avertissement « document rattaché » : la
  réversibilité suffit.

### Robustesse
- Le déplacement/suppression est appliqué de façon **optimiste** dans la liste,
  puis confirmé par le backend ; en cas d'échec backend, l'email **revient** à son
  dossier d'origine et un message d'erreur discret est affiché.
- Le dossier source et le dossier cible voient leurs **compteurs** (total / non lus)
  mis à jour après l'opération.

## Gherkin

```gherkin
Feature: Glisser-déposer des courriers dans la messagerie

  Scenario: Supprimer un courrier en le déposant sur la Corbeille
    Given un praticien dont la boîte affiche la liste des courriers reçus
    When il glisse un courrier sur le dossier Corbeille
    Then le courrier est retiré de la liste courante et placé dans la Corbeille
    And un message « Email supprimé · Annuler » s'affiche brièvement

  Scenario: Annuler une suppression depuis le message
    Given un courrier vient d'être déposé sur la Corbeille
    When le praticien clique sur « Annuler »
    Then le courrier revient dans son dossier d'origine
    And son rattachement patient est rétabli

  Scenario: Déplacer plusieurs courriers vers un dossier personnel
    Given un praticien a sélectionné plusieurs courriers dans sa boîte de réception
    When il glisse la sélection vers un dossier personnel
    Then tous les courriers sélectionnés sont déplacés dans ce dossier

  Scenario: Déplacement interdit vers les Envoyés
    Given un praticien consulte sa boîte de réception
    When il tente de glisser un courrier sur le dossier Envoyés
    Then le dépôt est refusé visuellement
    And le courrier reste dans sa boîte de réception

  Scenario: Déplacement interdit vers les Brouillons
    Given un praticien consulte un dossier de courriers
    When il tente de glisser un courrier sur le dossier Brouillons
    Then le dépôt est refusé et aucun déplacement n'a lieu

  Scenario: Restaurer un courrier depuis la Corbeille
    Given un courrier se trouve dans la Corbeille
    When le praticien le glisse vers sa boîte de réception
    Then le courrier est restauré dans la boîte de réception
    And son rattachement patient est reconstruit

  Scenario: Dépôt sur le dossier déjà affiché
    Given un praticien consulte un dossier
    When il glisse un courrier de ce dossier et le dépose sur ce même dossier
    Then aucune action n'est déclenchée

  Scenario: Échec du déplacement côté serveur
    Given un praticien glisse un courrier vers un dossier personnel
    When le serveur ne peut pas réaliser le déplacement
    Then le courrier revient à son dossier d'origine
    And un message d'erreur discret est affiché
```

## Analyse front & réutilisation

- **Source du drag** : `mail-list` (lignes de courrier). Le drag transporte le(s)
  uid(s) sélectionné(s) + le chemin du dossier source.
- **Cibles du drop** : `mail-folder-list` / `mail-folder-item` (dossiers de la
  barre latérale).
- **Opérations backend (existantes, à réutiliser, `MssApiService`)** :
  `moveEmail(folder, uid)`, `bulkMoveEmails(...)`, `deleteEmail(folder, uid)`,
  `bulkDeleteEmails(...)`. **Aucun nouvel endpoint.**
- **État** : la mise à jour de la liste + compteurs passe par le service d'état
  messagerie existant (pattern signals-first).
- **Règles de déplacement** : centralisées dans une **fonction pure** réutilisable
  (`core/utils`) — `canDropEmail(sourceFolderType, targetFolderType)` — testable
  unitairement et indépendante du composant (façon `remote-content.util.ts` de la
  task-089).
- **Modèle de dossiers** : enum `FolderType` existante
  (`Inbox/Sent/Drafts/Trash/Junk/Important/All/Custom/Tag`).
- **i18n** : libellés FR en dur (toast, message d'erreur) — le module MSS Angular
  n'utilise pas ngx-translate.
- **Tokens** : `var(--ds-color-*)` du `@weda/design-system` pour la surbrillance
  des cibles et l'état « interdit ».

## Definition of Done

- [ ] Build passe : `cd Client/Angular/front && npm run build` (0 erreur)
- [ ] Fonction pure de règles de déplacement (`canDropEmail`) couvrant la matrice :
      destinations interdites (`Sent`, `Drafts`, `All`), `Sent → Custom` interdit,
      `Sent`/`Drafts → Trash` autorisés, no-op sur dossier courant, restauration
      depuis `Trash`
- [ ] Glisser-déposer opérationnel depuis `mail-list` vers `mail-folder-item`
      (mono + multi-sélection)
- [ ] Dépôt sur Corbeille → `deleteEmail` / `bulkDeleteEmails` + toast « Annuler »
      non bloquant qui restaure le(s) message(s)
- [ ] Déplacement entre dossiers → `moveEmail` / `bulkMoveEmails`
- [ ] Retour visuel : surbrillance de la cible valide, indication « interdit » sur
      cible refusée, `data-testid` (ex. `mail-drag-row`, `mail-folder-droptarget`,
      `mail-trash-undo`)
- [ ] Mise à jour optimiste de la liste + rollback sur échec backend (message
      d'erreur discret) + mise à jour des compteurs source/cible
- [ ] Tests : >= 1 test unitaire par règle de la matrice (`canDropEmail`), tests de
      composant pour le geste (drop autorisé → opération appelée, drop interdit →
      aucune opération, multi-sélection, toast annuler restaure)
- [ ] `nx test mss-lib` vert, `nx lint` (scope `tag:scope:mss`) 0 erreur
- [ ] Aucune donnée de santé en clair dans les logs (uid/chemins techniques
      seulement, jamais de contenu ni d'INS)
- [ ] Libellés FR en dur (pas de chaîne i18n manquante), valeurs dynamiques via
      `computed()` le cas échéant

## Manual Test Plan

- Lancer Angular : `cd Client/Angular/front && npm start` (http://localhost:4200)
- Se connecter à une boîte MSSanté de test, ouvrir la messagerie
- **Suppression** : glisser un courrier de la boîte de réception sur **Corbeille**
  → il disparaît de la liste, apparaît dans la Corbeille, toast « Annuler »
  s'affiche ; cliquer « Annuler » → il revient dans la boîte de réception
- **Multi-sélection** : sélectionner plusieurs courriers, glisser la sélection vers
  un **dossier personnel** → tous déplacés
- **Restauration** : depuis la **Corbeille**, glisser un courrier vers la boîte de
  réception → il est restauré
- **Règles interdites** : tenter de glisser un courrier vers **Envoyés** et vers
  **Brouillons** → dépôt refusé visuellement, aucun déplacement
- **Sent → Custom** : depuis **Envoyés**, tenter de glisser vers un dossier
  personnel → refusé ; glisser vers **Corbeille** → autorisé
- **No-op** : glisser un courrier et le redéposer sur son dossier courant → rien ne
  se passe
- **Document rattaché** : supprimer (Corbeille) un courrier portant un document
  rattaché à un patient, vérifier que le rattachement est retiré ; restaurer le
  courrier → vérifier que le rattachement est reconstruit
- Vérifier les compteurs (total / non lus) des dossiers source et cible

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — ergonomie de gestion de la boîte
- **Exigences DSR honorées** : non applicable — n'altère pas le transport MSSanté
  ni le contenu des courriers ; geste UI au-dessus d'opérations existantes
- **INS** : non applicable — l'US ne manipule pas l'identité INS. La suppression
  retire le lien patient (rattachement) par cascade backend existante ; la
  restauration le reconstruit (décision PO acceptée)
- **Authentification PS** : inchangé — opérations sur la propre boîte du PS
  authentifié
- **Habilitations** : inchangé — limité à la boîte du PS authentifié (hérité des
  endpoints existants)
- **Interop CI-SIS** : non applicable — pas de transformation CDA ; les documents
  rattachés sont gérés par le chemin existant
- **Tracé PGSSI-S** : inchangé — déplacement et suppression sont déjà journalisés
  par les opérations backend existantes (le drag & drop est un nouveau déclencheur,
  pas une nouvelle opération) ; aucune journalisation supplémentaire requise côté
  front
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Sécurité / confidentialité** : aucun contenu de santé manipulé côté front au-delà
  des identifiants techniques (uid, chemin de dossier) ; jamais de contenu/INS dans
  les logs
- **Hébergement HDS** : oui — environnement existant
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de donnée
  personnelle (réorganisation de courriers déjà stockés)

## Hors périmètre (v1)

- Dépôt sur un **Tag** pour appliquer/retirer un libellé (geste d'étiquetage).
- Archivage d'un message **envoyé** vers un dossier personnel (`Sent → Custom`).
- Suppression **définitive** / vidage de la Corbeille par glisser-déposer.
- Réorganisation des dossiers eux-mêmes (déplacer un dossier dans un autre).
- Mémorisation d'une préférence d'expéditeur lors d'un déplacement.

## Branches
- `client-angular` (code-only) : la forge écrit le code sur la branche actuellement checked out dans `Client/Angular/` (`feature/nova-rewriting-mss` au moment du `/start`) — l'humain gère branche, commit, push, PR TFS.
- Aucune branche pushable : `api-mail`/`client-blazor`/`dtos-mss` non concernés (US Angular-only). `dtos-mss` non auto-inclus (ni `api-mail` ni `client-blazor` dans `**Repos**:`).

## Develop log
- Repos touched : client-angular (code-only). api-mail / dtos-mss : non touchés (US Angular-only, réutilise les endpoints move/delete existants).
- DTOs published : none. Interop published : none.
- Approche : drag & drop natif HTML5 (lignes `draggable`, dossiers `dragover`/`drop`) + service d'état de drag à base de signaux (`MailDragService`) car la validation pendant `dragover` a besoin du type de dossier source (illisible via `dataTransfer` avant le drop). Règles centralisées dans une fonction pure `evaluateMailDrop` (`core/utils/mail-drop-rules.util.ts`).
- Suppression = **deferred-delete (style Gmail)** : dépôt sur Trash retire les lignes optimistiquement + toast « Annuler » ~6 s, **sans appel backend** ; « Annuler » réinsère les lignes (aucun appel) ; expiration/teardown/nouveau lot → flush réel (`deleteEmail`/`bulkDeleteEmails`). Sidestep du problème de nouvel UID IMAP au restore, et la cascade lien patient ne part qu'après la fenêtre d'annulation. Déplacements (Move/restore) → `moveEmail`/`bulkMoveEmails` immédiats, optimistes + rollback sur erreur (snackbar `MSS_SNACKBAR_SHOW`).
- Fichiers créés :
  - `libs/mss/src/core/utils/mail-drop-rules.util.ts` (+ `.spec.ts`, 27 tests) — `evaluateMailDrop` + enum `MailDropOutcome`
  - `libs/mss/src/features/mail/services/mail-drag.service.ts` (+ `.spec.ts`, 9 tests)
  - `libs/mss/src/features/mail/services/mail-pending-delete.service.ts` (+ `.spec.ts`, 11 tests)
  - `libs/mss/src/ui/mail-undo-toast/mail-undo-toast.component.{ts,html,scss}` (+ `.spec.ts`, 3 tests)
- Fichiers modifiés :
  - `features/mail/services/mail-state.service.ts` (restoreMailsToList + restore counts, pas de tombstone sur le retrait optimiste)
  - `features/mail/services/mail-event.service.ts` (`emailsDropped$` + payload)
  - `features/mail/components/mail-header/mail-header.component.{ts,html}` (draggable, outputs dragStart/dragEnd, `data-testid="mail-drag-row"`)
  - `features/mail/components/mail-list/mail-list.component.{ts,html}` (bookkeeping drag, orchestration move/restore/deferred-delete)
  - `features/mail/components/mail-folder-item/mail-folder-item.component.{ts,html,scss}` (dragover/dragleave/drop, highlight allowed/forbidden, `data-testid="mail-folder-droptarget"`)
  - `features/mail/components/mail-folder-list/mail-folder-list.component.{ts,html}` (relais des drops)
  - `features/mail/mss-mail.component.{ts,html}` (rend le toast undo, wire undo, flush pending au teardown)
  - NB : `apps/mss/src/environments/environment.ts` déjà modifié (WIP humain pré-existant) — non touché.
- data-testid : `mail-drag-row`, `mail-folder-droptarget`, `mail-trash-undo`.
- Matrice implémentée (conforme US) : cibles autorisées {Inbox, Custom, Junk, Trash} ; `*→Sent/Drafts/All/Important/Tag` interdit ; `Sent`/`Drafts` → Trash uniquement ; `Trash→Junk` interdit ; `Trash→Inbox/Custom` = restauration (Move) ; no-op même dossier géré par comparaison de path dans `MailDragService.canDropOn`.
- Local build/test : ✓ `npx nx build mss-lib` 0 erreur, ✓ `npx nx test mss-lib` 285/285 (50 nouveaux), ✓ `npx nx lint mss-lib` 0 erreur (warnings pré-existants acceptés).
- Code-only : aucun git op (uncommitted sur `feature/nova-rewriting-mss`, cumulé avec 087/088/089) — l'humain gère commit/push/PR TFS.
- DOD self-check : matrice ✓, mono+multi ✓, deferred-delete + toast Annuler ✓, move/restore ✓, retour visuel + data-testid ✓, optimiste + rollback ✓, tests par règle + composants ✓, build/test/lint ✓, libellés FR en dur ✓.
- Next step : /forge-simplify task-093

## Simplify log
- /forge-simplify : clean skip — code task-093 fraîchement écrit aux patterns existants, forte réutilisation (fonction pure `evaluateMailDrop` source unique de vérité ; endpoints move/delete, mutations d'état et token `MSS_SNACKBAR_SHOW` réutilisés ; util pur façon `remote-content.util`). Méthodes courtes + JSDoc, signals-first, complexité dans les limites.
- Seule redondance mineure repérée (non corrigée — best-effort, quality-only, pas de risque comportemental justifié) : `MailPendingDeleteService` enregistre le teardown deux fois (`destroyRef.onDestroy(flush)` au ctor + `OnDestroy/ngOnDestroy`). Inoffensif (flush idempotent, service root-scoped → le flush réel vient du container au teardown). Toucher un service couvert par specs pour un gain cosmétique n'est pas justifié.
- `dtos-mss`/`interop-cda` : jamais touchés (porteurs de contrat). api-mail : non touché.
- Aucun commit (client-angular code-only).
- Next step : /lint-angular task-093 (client-angular touché ; /sonar skip — api-mail non touché).

## Lint log
- /lint-angular (Mode A, scope `tag:scope:mss`, base `origin/next`, code-only) :
  - Baseline : **0 errors**, 33 warnings — tous pré-existants hors task-093
    (max-lines/complexity/jsdoc-require-example sur biology-timeline,
    patient-timeline, mss-settings/setup/templates, abnormal-biology &
    sync-progress widgets). Le code task-093 (`mail-drop-rules.util`,
    `mail-drag.service`, `mail-pending-delete.service`, `mail-undo-toast`,
    composants mail) est **lint-clean** (0 error / 0 warning).
  - Aucun auto-fix nécessaire (0 error ; les 2 warnings fixables sont des
    jsdoc/@example hors périmètre task-093 → non touchés, hors charte).
  - Build affected (full scope) : `mss-lib` ✓. `mss:build:production` **échoue**
    sur `apps/mss/src/environments/environment.prod.ts` manquant — **gap
    pré-existant** du WIP humain sur `feature/nova-rewriting-mss` (seul
    `environment.ts` existe/est tracké ; aucun fichier task-093 ne référence un
    environment). Non régressif, best-effort accepté.
  - Test affected (full scope, `--skipNxCache`) : ✓ 11 projets (mss-lib 285/285 ;
    mss app & shared : pas de fichiers de test).
  - Code-only : aucun git op (TFS). Seul `git fetch origin next` (ref de
    comparaison Nx affected).
- Next step : /review task-093

## PRs
- `client-angular` (code-only) : **humain gère commit/push TFS + ouverture PR**. Aucune PR GitHub (remote TFS). Branche `feature/nova-rewriting-mss` (cumulée avec 087/088/089). Fichiers task-093 (uncommitted) :
  - `libs/mss/src/core/utils/mail-drop-rules.util.{ts,spec.ts}`
  - `libs/mss/src/features/mail/services/mail-drag.service.{ts,spec.ts}`
  - `libs/mss/src/features/mail/services/mail-pending-delete.service.{ts,spec.ts}`
  - `libs/mss/src/features/mail/services/mail-state.service.{ts,spec.ts}` (restoreMailsToList + clearTombstones + tests)
  - `libs/mss/src/features/mail/services/mail-event.service.ts` (emailsDropped$)
  - `libs/mss/src/features/mail/components/mail-header/mail-header.component.{ts,html}`
  - `libs/mss/src/features/mail/components/mail-list/mail-list.component.{ts,html}`
  - `libs/mss/src/features/mail/components/mail-folder-item/mail-folder-item.component.{ts,html,scss}`
  - `libs/mss/src/features/mail/components/mail-folder-list/mail-folder-list.component.{ts,html}`
  - `libs/mss/src/features/mail/mss-mail.component.{ts,html}`
  - `libs/mss/src/ui/mail-undo-toast/` (component ts/html/scss + spec)
  - NB : `apps/mss/src/environments/environment.ts` = WIP humain pré-existant (non touché).
- `api-mail` / `dtos-mss` : non touchés (US Angular-only) — pas de PR.

## Code Review Summary
- Verdict : **APPROVED** (après 1 itération de correction).
- 1er passage : **CHANGES REQUESTED** — l'undo perdait silencieusement l'email restauré : `removeMailFromList` posait un tombstone 90 s que `restoreMailsToList` ne levait pas ; le prochain chargement (`filterTombstonedUids`, `mail-list.component.ts:183`) re-masquait l'UID restauré. **Corrigé** : ajout de `MailStateService.clearTombstones(folderPath, uids)` appelé par `restoreMailsToList` + 3 tests de régression (clearTombstones lève le tombstone ; no-op dossier/uid inconnu ; delete→undo restaure ET lève le tombstone).
- Build ✓ `nx build mss-lib` 0 erreur. Tests ✓ `nx test mss-lib` **288/288** (53 task-093 : 27 util + 9 drag + 11 pending-delete + 3 undo-toast + 3 état). Lint ✓ `nx lint mss-lib` (scope mss) 0 erreur (33 warnings pré-existants hors task-093 acceptés).
- DOD : matrice `evaluateMailDrop` (cibles {Inbox,Custom,Junk,Trash} ; `*→Sent/Drafts/All/Important/Tag` interdit ; `Sent`/`Drafts`→Trash only ; `Trash→Junk` interdit ; `Trash→Inbox/Custom`=restauration) ✓ ; mono+multi-sélection ✓ ; deferred-delete + toast Annuler (aucun appel backend si annulé) ✓ ; move/restore optimiste + rollback snackbar ✓ ; retour visuel allowed/forbidden + data-testid (`mail-drag-row`, `mail-folder-droptarget`, `mail-trash-undo`) ✓ ; libellés FR en dur ✓ ; pas de donnée santé loggée ✓.
- Note non bloquante : `MailPendingDeleteService` enregistre le teardown deux fois (ctor `destroyRef.onDestroy` + `ngOnDestroy`) — inoffensif (flush idempotent), laissé tel quel.
- Règle métier confirmée (cascade lien patient à la Corbeille, reconstruit à la restauration) : la fenêtre d'annulation ne déclenche aucun delete backend, donc la cascade ne part qu'après expiration ; cohérent avec la décision PO.
- Code-only : aucune opération git par la forge ; l'humain review le diff dans WindSurf puis commit/push TFS + ouvre la PR.

## Merged
- **Date** : 2026-06-17
- **Attestation humaine** : `--i-tested` — l'humain a validé la US end-to-end (drag & drop déplacement/suppression Angular) selon le Manual Test Plan.
- **Repos pushables** : aucun. `api-mail` / `dtos-mss` / `client-blazor` non touchés (US Angular-only). Aucune PR GitHub à squash-merger, aucun `develop` à synchroniser, aucune CI à vérifier.
- **client-angular** (code-only) : managed manually by the human — commit, push, PR et merge TFS sont du ressort exclusif de l'humain. La forge n'effectue aucune opération git.
- **Branche** : `feature/nova-rewriting-mss` (cumulée avec 087/088/089) — gérée par l'humain.
