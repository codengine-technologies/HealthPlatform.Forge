# questions/task-376.md — /review (3ᵉ passage) : CHANGES REQUESTED (weda2 seul)

**Étape** : `/review`, après la reprise B4 (`/develop` → `/lint-angular` → `/lint-mobile` → `/e2e`, verts : mobile 40/40, weda2 47 + 1 flaky, porte verte).
**Nature** : revue de code — un ordre d'événements encore ouvert sur weda2, de la même famille que B4. Aucune PR ouverte. Task laissée en `wip-task-376.md`.

## Ce qui est réglé

| Bloquant | weda2 | mobile |
|---|---|---|
| B1 — brouillon orphelin si Envoyer pendant l'autosave | ✅ | ✅ |
| B2 — seconde pièce homonyme illisible | — | ✅ |
| B3 — fermeture par geste puis réouverture rapide | — | ✅ |
| B4 — l'orphelin supprimé efface le brouillon suivant (le POST revient **avant** l'enregistrement suivant) | ✅ | ✅ (`5583857`) |

Reprise de l'enregistrement automatique après un envoi en échec (weda2) : ✅ (pas pendant un envoi, jamais après une remise incertaine, pas de double minuteur).

## Bloquant

### B5 — weda2 : B4 dans l'autre ordre (l'enregistrement suivant part **avant** le retour de l'orphelin)
- **Où** : `libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts` — `dispatchSend` (~l. 1336-1338) ; `saveThen` (~l. 615-628) n'attend pas l'enregistrement en vol (seul `saveDraftNow` regarde `isSavingDraft`).
- **Scénario** :
  1. Autosave A : `POST X` en vol ; le médecin clique Envoyer.
  2. L'envoi échoue vite (5xx / 409).
  3. **Avant le retour de A**, le médecin change de dossier ou de message (`saveAndClose`) ou ouvre une autre rédaction : B part avec `proposedDraftId` toujours égal à X (il n'est remis à zéro qu'au retour de A), et B n'est pas « dépassé » (compteur lu après l'envoi) → `POST X`.
  4. A revient, dépassé → `DELETE X` ; le POST de B est passé avant : la rédaction se ferme « enregistrée », puis le DELETE efface le brouillon. **Contenu perdu.**
- Le mobile n'y est pas exposé : ses enregistrements s'attendent (`while (this.saving) await`).
- **Correctif attendu (une ligne)** : dans `dispatchSend`, abandonner l'identifiant proposé avant l'envoi (`if (!this.currentDraftId()) this.proposedDraftId = null`) ; tout enregistrement en vol porte alors un identifiant qu'aucun enregistrement suivant ne reproposera, quel que soit l'ordre. (Variante : faire attendre `saveThen` sur l'enregistrement en vol, comme le mobile.)
- **Test rouge d'abord** : POST en vol, envoi en échec, `requestComposeClose$.next()` **avant** `created$.next(…)`, puis l'identifiant du second `saveDraft` ≠ celui supprimé.

## Signal /e2e à traiter hors task
- E2E-SEARCH-001 (angular) : 3ᵉ occurrence flaky → task de stabilisation à ouvrir.

## Décision demandée
Relancer `/develop task-376` sur B5 (weda2 seul, code-only), puis `/lint-angular → /e2e (voie Angular) → /review`.
