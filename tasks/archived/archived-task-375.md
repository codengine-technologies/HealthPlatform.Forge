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

## Sonar log

- Analyse complète de `fix/task-375-gestes-liste-bon-dossier` (2026-10-25) : build Release vert, 5 suites avec couverture vertes (6 783 réussis, 16 ignorés, 0 échec).
- Diff api-mail de la task : catalogue e2e + outil `tests/mss.mail.e2e` (code de test, analysé, hors couverture). **0 issue** sur `E2eMessage.cs` et `Program.cs` : rien à corriger, 0 itération.
- Quality Gate `ERROR` **hérité** : la période new-code inclut des tasks déjà mergées. Les 2 bugs (S2952, `src/Application/Session/MailClientSession.cs:909/914`) datent du 2026-09-28, et `new_security_hotspots_reviewed=0` / `new_violations=72` sont indépendants de cette task.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | = (hérité) |
| New coverage | 98,2 % | 98,2 % | = |
| New bugs / vulnérabilités / smells | 2 / 0 / 70 | 2 / 0 / 70 | = |
| Bugs / Vulnérabilités / Smells | 2 / 0 / 70 | 2 / 0 / 70 | = |
| Coverage projet / Duplication | 98,1 % / 0,3 % | 98,1 % / 0,3 % | = |
| Ratings (fiabilité / sécurité / maintenabilité) | D / A / A | D / A / A | = |

## Lint log

- `npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss` (13 projets) : **0 erreur** à la baseline, donc arrêt immédiat, 0 itération, aucun fichier modifié.
- Avertissements restants sur les fichiers touchés, tous antérieurs à la task : `max-lines` (`mail-list`, `mail-detail`, `mss-mail`, `mail-state`), et trois `@example` vides (`needsThreadCounts` de task-266, `tombstoneAdd`/`liveTombstones`).
- Build et tests weda2 : verts en /develop (`npm run build`, `npm test`, 12 projets), code inchangé depuis.

## Lint mobile log

- `npm run lint` sur `fix/task-375-gestes-liste-bon-dossier` : **All files pass linting** à la baseline. 0 itération, aucun commit. Build et tests mobiles verts en /develop, code inchangé depuis (`732cd08`).

## E2E log

| Voie | Rejouée | Résultat | Durée de la suite |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | oui (`api-mail` et `client-mobile` touchés) | 45 verts, 0 flaky, 0 rouge, parité verte | 7,6 min |
| angular (`npm run e2e:mss`) | oui (`api-mail` et `client-angular` touchés) | 53 verts, 1 flaky, 0 rouge, parité verte | 8,0 min |

Démontage vérifié : ports 4200/8100 libres, aucun conteneur e2e résiduel.
Écrans modifiés et spec e2e : `functional.e2e.ts` (Angular) porte E2E-MAIL-006 ; côté mobile, la sélection et les actions groupées sont couvertes par E2E-MAIL-002 (inchangé, vert).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/312 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/106 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR (branche `feature/nova-mss-weda-integration`). **À pousser avant le merge de la PR api-mail** (E2E-MAIL-006 `requis` côté Angular). Liste des fichiers modifiés :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/utils/mail-key.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-drag.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-pending-delete.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.gestures.spec.ts`
  - `front/libs/mss/src/features/mail/mss-mail.folder-switch.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-pending-delete.failures.spec.ts`

## Code Review Summary

**APPROVED** — 0 bloquant, 4 suggestions (détail dans le corps des PRs).

- Validation : api-mail build + 6 783 tests verts ; mobile build + 1268/1268 avant synchronisation, 1289/1289 après (deux passages rouges sur `MailComposeComponent`, ensembles différents, hors périmètre : flaky consigné dans `page-ionic-non-demontee`) ; weda2 build + tests verts (12 projets).
- DoD : tous les points cochables couverts par un test nommé (gestes, sélection, changement de dossier, suppression différée, non-lu), E2E-MAIL-006 au catalogue et implémenté côté Angular, trou du filet consigné, aucune donnée de santé ajoutée aux journaux.
- Règle 1b : sans objet pour api-mail (catalogue et outil e2e, aucun comportement atteignable par un endpoint). Parcours médecin → E2E-MAIL-006, rouge par mutation (`DELETE …/folders/INBOX/emails/1`), vert sur le correctif.
- E2E : vert (mobile 45/45, Angular 53 + 1 flaky E2E-SEARCH-001), parité verte, rejoué avant la synchronisation avec `develop`.
- Synchronisation : `develop` apporte task-394 (E2E-DRAFT-004 `requis` côté Angular, sans test weda2 dans l'arbre actuel). Le prochain `/e2e` Angular sera rouge en parité du fait de task-394.
- Suggestions : commentaire orphelin au-dessus de `perFolder` (mobile) ; regroupement par dossier écrit deux fois (mobile) ; brouillon réapparu sur échec partiel (weda2) ; `deleteDraft` sans épingle de boîte (weda2).

## Merged

- 2026-10-25, `/merge task-375 --i-tested` (test manuel attesté par l'humain).
- `api-mail` #312 → squash `989d8893` sur `develop` ; CI « Build and Publish » verte.
- `client-mobile` #106 → squash `6d890c2f` sur `develop` ; CI « Android Build » verte.
- Branches `fix/task-375-gestes-liste-bon-dossier` supprimées (distantes et locales).
- `client-angular` : code seul, géré par l'humain (TFS).

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
| /sonar | ok | 11 min 10 s | 1 (49 s) | 5 (6 min 27 s) | 2 (2 min 08 s) | api-mail 1B/5T |
| /lint-angular | ok | 1 min 25 s | — | — | — | — |
| /lint-mobile | ok | 1 min 06 s | — | — | — | — |
| /e2e | ok | 19 min 18 s | — | — | — | e2e ×5 (36 min 28 s) |
| /review | ok | 13 min 11 s | 4 (1 min 13 s) | 7 (8 min 03 s) | — | api-mail 1B/2T, client-mobile 2B/4T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 03 s | — | — | — | — |
| /merge | ok | 5 min 39 s | — | — | — | — |
| **Total cycle** | | **3 h 16 min** | **8 (3 min 25 s)** | **18 (19 min 53 s)** | **2 (2 min 08 s)** | |

Autres commandes mesurées : lint ×2 (1 min 42 s)
