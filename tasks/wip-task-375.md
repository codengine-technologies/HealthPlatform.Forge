# todo-task-375.md — Un geste sur la liste porte sur les messages affichés et sélectionnés, dans leur propre dossier

**Repos**: client-angular, client-mobile, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: false — le mobile partage la sélection non vidée et la suppression groupée mono-dossier (revue du 2026-10-25, décision humaine)
**Priorité**: **1** — glisser, supprimer ou déplacer peut toucher un message sans rapport, invisible à l'écran : celui de même numéro dans un autre dossier, ou des messages masqués par un filtre.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-12, ANG-13, ANG-30, ANG-34, ANG-36, ANG-74**).

## Ce qui est établi

> **Revue du 2026-10-25** (avant `/start`), sur `feature/nova-mss-weda-integration` (arbre propre, task-378
> commitée). Les six défauts sont **toujours présents**. Trois points ont bougé depuis l'audit :
> - **déjà corrigé** : les actions unitaires d'une ligne (lu, signalé, supprimer, y compris sur un enfant de fil)
>   passent `mail.folderPath` ; `removeMailFromList` et `updateMailInList` acceptent le dossier (task-371) ; la
>   suppression différée est épinglée sur sa boîte (task-374). Le point 1 du périmètre se réduit donc à la
>   sélection, au glisser-déposer, aux actions groupées et au surlignage ;
> - **aggravé** : glisser un enfant de fil vers la **Corbeille** supprime le message de même numéro **du dossier
>   affiché** (`deleteDroppedEmails` cherche les UID dans la liste principale, où l'enfant ne figure pas) ;
> - **plus visible** : depuis task-352, l'échec de chargement affiche « Réessayez dans un instant », mais
>   recliquer sur le dossier ne fait toujours rien (ANG-34).
>
> Références de lignes mises à jour ci-dessous.

- Les UID IMAP sont **propres à chaque dossier** (INBOX et Envoyés ont chacun leur séquence depuis 1) ; plusieurs chemins n'identifient un message que par son UID et prennent le dossier affiché.
- **ANG-12** — vue conversation : les enfants d'un fil viennent d'autres dossiers (Envoyés depuis task-268). Le glisser-déposer d'un enfant passe par `onMailDragStart` (`mail-list.component.ts:877-888`), qui prend `selectedFolder.path` et les seuls UID. Glisser sa réponse Envoyés/340 vers Archives déplace INBOX/340 (`moveDroppedEmails`, l. 970) ; vers la Corbeille, `deleteDroppedEmails` (l. 1039-1045) supprime INBOX/340. Les actions groupées (`bulkMarkRead`, `bulkFlag`, `bulkDelete`, `openAiChat`, l. 508-627) envoient `selectedFolder.path` et les UID de la sélection. Surlignage par UID seul (`[selected]="selectedMail()?.uid === …"`, gabarit l. 147 et 166) : INBOX/340 et Envoyés/340 s'allument ensemble.
- **ANG-13** — `mss-mail.component.ts:338-390` : chaque changement de dossier ouvre un `subscribe` imbriqué jamais annulé ; une réponse tardive de A réécrit `selectedFolder`. Le rafraîchissement de 30 s (`refreshSelectedFolder`, l. 521-600) ne vérifie pas non plus que le dossier est toujours affiché : `updateFolderMetadata` (l. 765-781) pose `selectedFolder = A`, et les nouveaux messages de A sont ajoutés à la liste de B. « Supprimer » envoie alors `bulkDeleteEmails(A.path, UID de B)`. *Probable* (course), mais le chemin est confirmé par le code.
- **ANG-30** — la sélection survit aux changements de page (`goToPage`, l. 475), de filtre (`setFilter`, l. 453), de filtre biologie (l. 463) et de recherche (l. 644, 675) : aucun n'appelle `clearSelection`. « Tout », filtre « Non lus », « Supprimer » emporte aussi les lus masqués. Aucun compteur de sélection dans le gabarit.
- **ANG-34** — `distinctUntilChanged` sur `folderChanged$` (`mss-mail.component.ts:340-345`) : après un échec, le bandeau dit « Réessayez dans un instant » (task-352), mais recliquer sur le dossier ne fait rien.
- **ANG-36** — `mail-pending-delete.service.ts:159-172` (`commit`) avale l'échec serveur (`catchError(() => of(undefined))`). Un brouillon glissé à la Corbeille (Brouillons → Corbeille est autorisé, UID synthétique négatif) part vers la route IMAP, échoue en silence, puis revient au chargement suivant.
- **client-mobile, même famille de défauts** : `MailStateService.setInboxFilter` ne vide pas la sélection ; `inbox.page.ts` `selectedMails()` (l. 587-589) résout les UID cochés contre **tous** les messages chargés (`state.emails()`), pas seulement les affichés, donc « Supprimer » après un filtre emporte aussi les masqués (ANG-30) ; `bulkDelete` (l. 667-685) envoie tout le lot dans le dossier du **premier** message sélectionné (`mails[0].folderPath`). La sélection est indexée par UID seul (`selectedMailUids`). Pas de glisser-déposer sur le mobile.
- **ANG-74** — vérifiés : compteur de non-lus décrémenté deux fois sur une suppression (`deleteSingleEmail` décrémente, puis `removeMailFromList` → `forgetUidsInSelectedFolder` décrémente encore) ; dépliage d'un fil sans garde (`expandThread`, `mail-state.service.ts:992-1010` : la réponse est appliquée même si un autre fil a été déplié entre-temps). Non revérifiés : minuteurs, étiquette lue ailleurs, renommage du dossier ouvert.

## Objective

Qu'une action de la liste (lire, signaler, déplacer, supprimer, glisser-déposer, action groupée) porte **exactement** sur les messages que le médecin voit sélectionnés, chacun **dans son propre dossier**, et que son résultat — réussite ou échec — soit fidèlement affiché.

### Périmètre

1. **Identité `(folderPath, uid)`** dans la sélection, le glisser-déposer (déplacement **et** Corbeille), le surlignage et le `track` des listes ; actions groupées regroupées par `mail.folderPath`. (`removeMailFromList` et `updateMailInList` le font déjà depuis task-371.)
2. **Un seul flux de chargement de dossier** (`switchMap`) qui annule aussi le rafraîchissement en vol ; `selectedFolder` jamais réécrit pour un dossier quitté ; même garde pour `loadEmails`.
3. **Sélection vidée** à chaque changement de page, de filtre ou de résultat, et nombre de messages sélectionnés affiché — sur weda2 **et** sur le mobile (où la sélection se résout aussi contre les messages **affichés**).
4. **Déduplication des clics de dossier** contre le dossier réellement affiché, toujours relâchée après une erreur.
5. **Suppression différée** : brouillons routés vers la suppression de brouillon ; en cas d'échec, messages remis en place et message affiché.
6. Corrections de **ANG-74**.
7. **Mobile** : sélection indexée par `(folderPath, uid)`, actions groupées regroupées par dossier (plus de `mails[0].folderPath` pour tout le lot).

## Definition of Done

- [ ] Build et tests verts : weda2, client-mobile
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] glisser l'enfant Envoyés/340 d'un fil affiché dans INBOX vers Archives : la requête vise Envoyés/340
  - [ ] glisser l'enfant Envoyés/340 vers la Corbeille : la suppression vise Envoyés/340, INBOX/340 reste dans la liste
  - [ ] action groupée sur une sélection de deux dossiers : une requête par dossier, avec ses UID
  - [ ] rafraîchissement de A en vol puis clic sur B : `selectedFolder` reste B, la liste et les actions portent sur B
  - [ ] changement de filtre : la sélection est vidée ; le compteur de sélection s'affiche (weda2 **et** mobile)
  - [ ] mobile : sélection « Tout », filtre « Non lus », « Supprimer » → seuls les non-lus affichés partent
  - [ ] mobile : suppression groupée sur deux dossiers → une requête par dossier, avec ses UID
  - [ ] chargement de B en échec puis nouveau clic sur B : le chargement repart
  - [ ] suppression différée en échec : les messages réapparaissent, un message s'affiche ; brouillon glissé à la Corbeille : `deleteDraft` est appelé
  - [ ] une suppression décrémente le compteur de non-lus une seule fois
- [ ] Scénario E2E-MAIL-006 « Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul » ajouté (angular `requis` ; mobile : `non-applicable` — pas de glisser-déposer sur le mobile, vérifié à la revue du 2026-10-25)
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

Les étapes 2 et 3 se jouent aussi sur l'app mobile (`cd Client/Mobile && npm start`, http://localhost:8100).

1. INBOX en mode Conversation, fil contenant un message envoyé (Envoyés) de même numéro qu'un mail d'INBOX : le glisser sur la Corbeille → seul le message envoyé est supprimé ; le mail d'INBOX reste. Le glisser sur Archives est refusé (déplacer hors d'Envoyés est interdit depuis task-093) : rien ne bouge.
2. Tout sélectionner, appliquer « Non lus », supprimer → seuls les non-lus affichés sont supprimés.
3. Cliquer très vite sur deux dossiers successifs, puis « Supprimer » une sélection → les messages supprimés sont ceux affichés.
4. Glisser un brouillon vers la Corbeille → il disparaît pour de bon (et pas seulement jusqu'au prochain chargement).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : déplacements et suppressions tracés comme aujourd'hui, désormais sur le bon message
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Develop log

### Repos et commits
- `api-mail` — `1c17fab9`, `4e7d3997` (poussés) : catalogue E2E-MAIL-006 v1 ; outil e2e `message --create … --in-reply-to <objet> --in-reply-to-folder <dossier>` (réponse liée à un message d'un autre dossier, datée au moins une seconde après lui), dépôt dans Envoyés avec le praticien pour expéditeur, uid déposé imprimé. Aucun code `src/` touché.
- `client-mobile` — `732cd08` (poussé) : sélection par identité (dossier, UID), résolue contre les lignes affichées ; vidée au changement de filtre ; actions groupées et suppression différée une requête par dossier ; compteur de non-lus rétabli sur le dossier de chaque message à l'annulation.
- `client-angular` — **code-only, non commité** sur `feature/nova-mss-weda-integration` (l'humain commit/push TFS). ⚠️ `functional.e2e.ts` porte E2E-MAIL-006, `requis` côté Angular : **à pousser sur TFS avant le merge de la PR api-mail**, sinon la parité de la task suivante rougit (cf. task-340/332).
  - modifiés : `e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/support/e2e-backend.ts`, `libs/mss/src/core/utils/mail-key.util.ts`, `…/mail-detail/mail-detail.component.ts`, `…/mail-list/mail-list.component.{ts,html,scss}`, `…/mail/mss-mail.component.ts`, `…/services/mail-drag.service.ts`, `…/services/mail-pending-delete.service.ts`, `…/services/mail-state.service.{ts,spec.ts}`
  - nouveaux : `…/mail-list/mail-list.gestures.spec.ts`, `…/mail/mss-mail.folder-switch.spec.ts`, `…/services/mail-pending-delete.failures.spec.ts`
  - `front/.claude/compact-log.txt` (non suivi) n'est pas de cette task.

### Validation
- weda2 : `npm run build` vert ; `npm test` vert (12 projets, mss-lib 1257/1257) ; lint 0 erreur ; `tsc` du support e2e propre.
- client-mobile : build vert, lint propre ; Karma 1268/1268 sur un passage. Les autres passages ont montré les suites Ionic intermittentes déjà rouges sur `develop` (MailCompose task-388, MailboxSwitcher), vérifié sur `develop` après un stash : flaky préexistants, pas une régression.
- api-mail : build vert ; tests du catalogue e2e 109/109.

### Preuves rouges
- **E2E-MAIL-006** (weda2, contre le backend e2e) : mutation « le message glissé prend le dossier affiché » (`resolveDraggedMails` → `folderPath: selectedFolder().path`) → rouge sur « la requête de suppression vise Envoyés » (reçu `DELETE …/folders/INBOX/emails/1`, le message d'INBOX de même numéro). Restauré → vert. 9 passages verts d'affilée avant la mutation.
- Unitaires weda2, même mutation : les 3 tests de glisser (`mail-list.gestures.spec.ts`) rouges, 10/10 après restauration.
- Clé de sélection réduite à l'UID (`mailKeyString` → `${uid}`) : « cocher INBOX/7 ne coche pas Envoyés/7 » rouge.
- Suppression différée sans remise en place sur échec (`restore` retiré) : « une suppression en échec remet les messages en place et le dit » rouge.
- Les tests du compteur de non-lus et du filtre ont été resserrés pendant l'écriture : ils passaient d'abord pour une mauvaise raison (compteur borné à 0, re-sélection après filtre).

### Écarts au plan
- **E2E-MAIL-006 vise la Corbeille, pas Archives** : déplacer un message hors d'Envoyés est interdit (règle de dépôt de task-093). Le test unitaire « vers Archives » reste : il appelle le déplacement directement et protège le chemin de déplacement, mais en vrai, l'écran refuse ce geste depuis Envoyés. Plan de test manuel corrigé en conséquence.
- **Fil masqué en vue Conversation (banc)** : deux messages d'un fil déposés dans la même seconde sont à égalité, et le fil peut masquer la réponse (dernier message lu en base à la seconde). Corrigé dans l'outil e2e ; consigne `fil-depose-a-la-seconde` dans `conventions/e2e.md`.
- **Constat produit hors périmètre** : le dernier message d'un fil se lit en base. Une réponse que l'application n'a pas encore lue ne compte donc pas, et la vue Conversation montre l'ancien message en tête de fil jusqu'à ce que la réponse soit lue. Non corrigé ici ; à arbitrer.

### Passe qualité (§Q)
- weda2 et mobile : helpers déjà mutualisés (`groupByFolder` dans `core/utils`, `perFolder` partout), aucun nettoyage appliqué, donc pas de revalidation. api-mail : diff limité à l'outil e2e, rien à simplifier.

### Prévention (règle d'or)
- `conventions/e2e.md` : ligne « Trous du filet » (ANG-12 → E2E-MAIL-006) et consigne `fil-depose-a-la-seconde`.
- `conventions/angular.md` : `jsdoc/require-jsdoc` passe à 11 occurrences (`@returns` oublié sur un type de retour modifié).

### Parallélisme
- task-394 reste en `wip-*` dans une autre session, en pause (décision humaine du 2026-10-25). Aucun fichier commun constaté.

## Branches

> **Parallèle** : task-394 est en `wip-*` (autre session, arrêtée sur une question). Décision humaine du 2026-10-25 : lancer 375 quand même ; 394 est considérée en pause pendant ce cycle.

- `api-mail` (pushed) : fix/task-375-gestes-liste-bon-dossier — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-375-gestes-liste-bon-dossier (catalogue e2e)
- `client-mobile` (pushed) : fix/task-375-gestes-liste-bon-dossier — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-375-gestes-liste-bon-dossier
- `client-angular` (code-only) : la forge écrit le code sur la branche checkée dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`, arbre propre) — humain gère commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-375 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 min 39 s | — | — | — | — |
| /develop | ok | 2 h 01 min | 3 (1 min 22 s) | 6 (5 min 22 s) | — | client-angular 1B/2T, client-mobile 1B/2T, api-mail 1B/2T |
| **Total cycle** | | **2 h 23 min** | **3 (1 min 22 s)** | **6 (5 min 22 s)** | **0 (0.0 s)** | |
