# todo-task-099-mobile-message-actions.md — Actions message : lu/non-lu, flag, supprimer, déplacer

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: task-096
**Epic**: E012

## Objective

Apporter les **actions de base de messagerie** sur le client mobile, à parité
avec `client-angular` : **marquer lu / non-lu**, **flag / unflag**,
**supprimer**, et **déplacer vers un dossier**, depuis **la ligne inbox** et
**le détail**, avec **mise à jour optimiste** de l'état (parité
`MailStateService` : `updateMailInList`, `removeMailFromList`,
`moveMailFromList`, compteurs de dossiers).

### Périmètre

- **Lu / non-lu** : marquage automatique « lu » à l'ouverture (déjà partiel) +
  bascule explicite lu/non-lu depuis la ligne et le détail
  (`toggleReadStatus`).
- **Flag / unflag** : bascule depuis la ligne et le détail (`toggleFlagStatus`).
- **Supprimer** : depuis la ligne (swipe Ionic) et depuis le détail
  (`deleteEmail` / `deleteMail`). Confirmation légère.
- **Déplacer vers un dossier** : choisir un dossier de destination
  (`moveToFolder`) — réutilise la liste de dossiers de task-095.
- **MAJ optimiste** : la liste et les compteurs non-lus des dossiers se
  mettent à jour immédiatement, rollback si l'API échoue.

> Filtre inbox lu/non-lu/flaggé (`InboxFilter`) : inclure le filtre de base
> (Tous / Non lus / Flaggés) puisqu'il accompagne ces actions côté Angular.
> Bulk/multi-sélection : **hors scope** (mono-action mobile), à noter.

### Structure cible

Actions ajoutées **dans les composants existants** (pas de nouveau composant
majeur) : `mss-mail-header` (boutons/swipe de ligne), `mss-mail-list` (filtre +
orchestration), `mss-mail-detail` (barre d'actions), avec la logique d'état
dans `mail-state.service` et les appels dans `mss-api.service`.

### Périmètre API (mss-api.service — parité Angular)

`updateReadStatus(folderPath, uid)`, `updateUnreadStatus(folderPath, uid)`,
`updateFlagStatus(folderPath, uid)`, `updateUnflagStatus(folderPath, uid)`,
`deleteEmail(folderPath, uid)`, `moveEmail(folderPath, uid, dto)`. Aucun nouvel
endpoint backend.

> Rappel métier (mémoire `project_mail_trash_cascade_delete_patient_link`) :
> mettre un mail à la Corbeille **supprime côté backend** le lien patient et
> les documents rattachés (reconstruits à la restauration). Le mobile ne fait
> qu'appeler l'API — **ne pas** réimplémenter cette cascade côté client ;
> le message de confirmation peut mentionner cette conséquence.

## Scénarios d'acceptation

1. **Marquer lu/non-lu** — Depuis la ligne ou le détail, je bascule l'état
   lu/non-lu ; la liste et le compteur non-lus du dossier se mettent à jour.
2. **Flag** — Je bascule le flag d'un mail ; l'indicateur se met à jour.
3. **Supprimer** — Je supprime un mail (swipe sur la ligne ou bouton détail) ;
   il disparaît de la liste après confirmation.
4. **Déplacer** — Je déplace un mail vers un autre dossier ; il quitte le
   dossier courant et les compteurs s'ajustent.
5. **Filtre** — Je filtre la liste par Tous / Non lus / Flaggés.
6. **Rollback** — Si l'API échoue, l'état optimiste est annulé et un message
   d'erreur (ProblemDetails) est présenté.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreurs)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échecs)
- [ ] Bascule lu/non-lu depuis ligne **et** détail
- [ ] Bascule flag depuis ligne **et** détail
- [ ] Suppression depuis ligne (swipe) **et** détail, avec confirmation
- [ ] Déplacement vers un dossier (réutilise la liste de dossiers)
- [ ] Filtre inbox Tous / Non lus / Flaggés
- [ ] MAJ optimiste de la liste + compteurs non-lus, rollback sur échec API
- [ ] Erreurs API consommées au format `ProblemDetails` (title/detail/status)
- [ ] Libellés FR en dur ; `data-testid` sur boutons d'action et items de filtre
- [ ] Tests composant : `mss-mail-header` (émission des actions), `mss-mail-detail` (barre d'actions), filtre inbox
- [ ] Tests service : `mail-state` (updateMailInList / removeMailFromList / moveMailFromList + compteurs + rollback), `mss-api` (read/unread/flag/delete/move mockés)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC, ouvrir un répertoire
- Marquer un mail non-lu → la pastille et le compteur de dossier changent ; idem lu
- Flagger / déflagger un mail → l'indicateur change
- Swiper une ligne pour supprimer (confirmer) → le mail disparaît
- Ouvrir un mail puis supprimer depuis le détail → retour liste, mail absent
- Déplacer un mail vers un autre dossier → il quitte le dossier courant
- Appliquer le filtre Non lus / Flaggés → la liste se restreint
- Comparer le comportement avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté (gestion des messages — lu/non-lu, suppression, classement)
- **INS** : non manipulée directement ; la suppression peut affecter le lien patient (cascade backend)
- **Authentification PS** : PSC / e-CPS — la suppression/déplacement est une action tracée
- **Habilitations** : RPPS via claim PSC ; actions imputées au PS authentifié
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : lu/non-lu, flag, suppression, déplacement journalisés côté backend — imputabilité, conservation 6 ans
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — réplication mobile d'actions déjà tracées

## Branches
- `client-mobile` (pushed) : feat/task-099-mobile-message-actions — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-099-mobile-message-actions

> Single frontend (client-mobile only). Dépend de task-096 (mergé @c94fa90).

## Develop log
- Repos : client-mobile
- mail-actions.service (optimiste+rollback), swipe mss-mail-list, toolbar mss-mail-detail, mark-read on open, filtre statut inbox
- mss-api : read/unread/flag/unflag/delete/move ; ProblemDetails surfacing
- Build ✓ · Tests ✓ 63/63 (7 nouveaux) · Lint ✓
- Commits : a987f82 (+ fc281fe)

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/5 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 63/63 · Lint ✓
- Actions optimistes + rollback testées ; swipe + détail + filtre ; ProblemDetails ; FR + data-testid

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- client-mobile : develop @5086a82 (PR #5 closed)
- Local feature branch conservée
