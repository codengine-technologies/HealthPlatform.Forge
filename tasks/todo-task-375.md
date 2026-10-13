# todo-task-375.md — Un geste sur la liste porte sur les messages affichés et sélectionnés, dans leur propre dossier

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — glisser, supprimer ou déplacer peut toucher un message sans rapport, invisible à l'écran : celui de même numéro dans un autre dossier, ou des messages masqués par un filtre.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-12, ANG-13, ANG-30, ANG-34, ANG-36, ANG-74**).

## Ce qui est établi

- Les UID IMAP sont **propres à chaque dossier** (INBOX et Envoyés ont chacun leur séquence depuis 1) ; plusieurs chemins n'identifient un message que par son UID et prennent le dossier affiché.
- **ANG-12** — vue conversation : les enfants d'un fil viennent d'autres dossiers (Envoyés depuis task-268), mais glisser, sélectionner ou supprimer un enfant utilise `selectedFolder.path` (`mail-list.component.ts:860-907, 953-970, 1022-1028`) : glisser sa réponse Envoyés/340 vers Archives déplace INBOX/340.
- **ANG-13** — `mss-mail.component.ts:346-359, 491-566, 735-751`, `mail-list.component.ts:214-250` : réponses de dossier non annulées. Un rafraîchissement en vol de A réécrit `selectedFolder = A` pendant que la liste montre B ; « Supprimer » envoie `bulkDeleteEmails(A.path, UID de B)`. *Probable.*
- **ANG-30** — la sélection survit aux changements de page, de filtre et de recherche : « Tout », filtre « Non lus », « Supprimer » emporte aussi les lus masqués.
- **ANG-34** — `distinctUntilChanged` sur `folderChanged$` : après un échec, recliquer sur le dossier ne fait rien.
- **ANG-36** — `mail-pending-delete.service.ts:119-125` avale l'échec serveur ; un brouillon glissé à la Corbeille (UID synthétique négatif) n'est jamais supprimé, mais affiché comme tel.
- **ANG-74** — compteurs de non-lus décrémentés deux fois, minuteurs qui s'accumulent, dépliage d'un fil qui affiche les enfants d'un autre, étiquette lue ailleurs qui reste, renommage du dossier ouvert pris pour une suppression.

## Objective

Qu'une action de la liste (lire, signaler, déplacer, supprimer, glisser-déposer, action groupée) porte **exactement** sur les messages que le médecin voit sélectionnés, chacun **dans son propre dossier**, et que son résultat — réussite ou échec — soit fidèlement affiché.

### Périmètre

1. **Identité `(folderPath, uid)`** dans la sélection, le glisser-déposer, `removeMailFromList`, `updateMailInList` et le `track` des listes ; actions groupées regroupées par `mail.folderPath`.
2. **Un seul flux de chargement de dossier** (`switchMap`) qui annule aussi le rafraîchissement en vol ; `selectedFolder` jamais réécrit pour un dossier quitté ; même garde pour `loadEmails`.
3. **Sélection vidée** à chaque changement de page, de filtre ou de résultat, et nombre de messages sélectionnés affiché.
4. **Déduplication des clics de dossier** contre le dossier réellement affiché, toujours relâchée après une erreur.
5. **Suppression différée** : brouillons routés vers la suppression de brouillon ; en cas d'échec, messages remis en place et message affiché.
6. Corrections de **ANG-74**.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] glisser l'enfant Envoyés/340 d'un fil affiché dans INBOX vers Archives : la requête vise Envoyés/340
  - [ ] action groupée sur une sélection de deux dossiers : une requête par dossier, avec ses UID
  - [ ] rafraîchissement de A en vol puis clic sur B : `selectedFolder` reste B, la liste et les actions portent sur B
  - [ ] changement de filtre : la sélection est vidée ; le compteur de sélection s'affiche
  - [ ] chargement de B en échec puis nouveau clic sur B : le chargement repart
  - [ ] suppression différée en échec : les messages réapparaissent, un message s'affiche ; brouillon glissé à la Corbeille : `deleteDraft` est appelé
  - [ ] une suppression décrémente le compteur de non-lus une seule fois
- [ ] Scénario E2E-MAIL-006 « Glisser une réponse d'un fil vers Archives déplace cette réponse, et elle seule » ajouté (angular `requis` ; mobile : `non-applicable` — pas de vue conversation à glisser-déposer sur mobile, à confirmer au `/start`)
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

1. INBOX en mode Conversation, fil contenant une réponse envoyée de même numéro qu'un mail d'INBOX : glisser la réponse vers Archives → seule la réponse est déplacée ; le mail d'INBOX reste.
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
