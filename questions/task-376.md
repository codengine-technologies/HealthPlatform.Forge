# questions/task-376.md — /review : CHANGES REQUESTED

**Étape** : `/review` (après `/develop`, `/sonar`, `/lint-angular`, `/lint-mobile`, `/e2e` verts).
**Nature** : revue de code — défauts bloquants dans le code de la task. Aucune PR ouverte, aucun commit ajouté par `/review`. Task laissée en `wip-task-376.md`.

## Verdicts par dépôt

| Dépôt | Verdict |
|---|---|
| api-mail | ✅ APPROVED — chaque comportement atteignable par un endpoint a son test d'intégration vu rouge (voir `## Develop log`) |
| client-mobile | ❌ CHANGES REQUESTED — 3 bloquants |
| client-angular (weda2) | ❌ CHANGES REQUESTED — 1 bloquant (le même que le n°2 mobile) |

## Bloquants

### B1 — Envoi pendant le premier enregistrement automatique : un brouillon orphelin du message parti (weda2 ET mobile)
- **Où** : weda2 `libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts` (`persistDraft`, `dispatchSend`, `saveDraftNow`) ; mobile `src/app/features/mail/components/mail-compose/mail-compose.component.ts` (`saveDraftOnce`, branche d'envoi `currentDraftId()`).
- **Scénario** : l'enregistrement automatique (`POST /drafts`) est en vol, le médecin clique Envoyer. `currentDraftId()` est encore nul (adopté seulement au retour du POST, c'est le correctif ANG-16) : le message part par `sendmail`. Le POST revient ensuite, l'identifiant est adopté, et **un brouillon complet du message déjà parti reste dans Brouillons** ; le rouvrir et l'envoyer fait partir le message deux fois. Variante weda2 : un `PUT` d'autosave en vol pendant l'envoi du brouillon reçoit 404 (brouillon consommé), et le repli `404 → POST` le recrée.
- **Correctif attendu** : une fois l'envoi engagé, ignorer la réponse d'un enregistrement en vol et ne plus jamais créer (pas de repli `404 → POST`), ou supprimer le brouillon qu'il vient de créer ; et/ou faire attendre l'envoi sur l'enregistrement en cours. Test unitaire : POST laissé en vol, envoi, puis POST terminé → aucun brouillon restant (rouge d'abord).

### B2 — Mobile : la seconde pièce homonyme reste illisible ; le correctif de lecture est du code mort (vert qui ment)
- **Où** : `mail-detail.component.ts:937-956` (`mergedAttachments`, non modifié par la task), avec `:971-979` et `mail-attachment.component.ts:55,69`.
- **Scénario** : `mergedAttachments` dédoublonne sur `guid || fileName`. Le backend ne renseigne jamais le `Guid` des pièces MIME : un message à deux « scan.pdf » n'affiche **qu'une ligne**, et le rang 1 n'est jamais demandé. ANG-18 (lecture) reste vrai sur mobile.
- **Pourquoi les tests passent** : ils alimentent le composant enfant directement (`attachments=[first, second]`) ou appellent `onAttachmentSelected(second)`, sans passer par `mergedAttachments` ; l'e2e DETAIL-001 v3 ne couvre que le transfert.
- **Correctif attendu** : dédoublonner sur une clé qui porte le rang (comme weda2 : `fileName|size|occurrence`) ; un spec qui passe par `mergedAttachments` et les lignes rendues, rouge sur le code actuel.

### B3 — Mobile : fermer par geste puis rouvrir vite laisse l'ancienne fermeture agir sur la nouvelle rédaction
- **Où** : `mail-compose.component.ts`, `closeCompose` (~1248-1277) avec `reset()` (~1468-1483).
- **Scénario** : fermeture par geste → `isOpen=false` avant `await persistDraft`. Une nouvelle ouverture (« Nouveau message », un brouillon) fait `reset()`. L'ancienne `closeCompose` reprend : si l'enregistrement réussit, elle **ferme la nouvelle rédaction** ; s'il échoue, la nouvelle rédaction vierge affiche « brouillon non enregistré » et **l'ancien contenu est perdu** — exactement ce que la task interdit.
- **Correctif attendu** : capturer la session de rédaction au début de `closeCompose` et s'arrêter si elle a changé après l'`await` ; `saveDraftOnce` rend un résultat « abandonné » distinct quand la session a changé. Test : rouge d'abord.

## Suggestions non bloquantes (à traiter dans la même reprise si possible)
- weda2 `compose-body.util.ts` : parser avec `DOMParser`/`<template>` (inerte) plutôt qu'un `div` du document vivant — défense en profondeur, le serveur assainit déjà `bodyHtml`.
- weda2 : deux enregistrements simultanés (`saveThen` pendant un autosave) peuvent arriver dans le désordre — chaîner ou sauter.
- weda2 modèles/signatures : vider `actionError` à la sélection ; comparer les champs plutôt que la référence dans `stillEditing`.
- Après une remise incertaine, le brouillon gardé perd l'état « peut-être parti » à la réouverture (weda2 et mobile) : porter l'information ou demander confirmation.
- weda2 e2e COMPOSE-004 : `waitForTimeout(2000)` avant `sends === 1` (délai fixe, cf. « negatif-a-delai-fixe » — admis ici pour un effet synchrone, à justifier en commentaire ou remplacer).
- api-mail : garder l'exception d'origine en `InnerException` (un envoi abandonné par le praticien rendrait 499 comme sendmail) ; une relecture du brouillon par `GET /drafts/{id}` sur le vrai cache fermerait la preuve « brouillon conservé ».

## Décision demandée
Relancer `/develop task-376` en reprise sur ces trois bloquants (code + tests rouges d'abord, sur weda2 et mobile), puis la chaîne `/lint-angular → /lint-mobile → /e2e → /review`. Les branches api-mail et mobile, et l'arbre weda2 non commité, sont dans l'état laissé par `/e2e` (verts).
