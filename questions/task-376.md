# questions/task-376.md — /review (2ᵉ passage) : CHANGES REQUESTED

**Étape** : `/review`, après la reprise des bloquants B1–B3 (`/develop` → `/lint-angular` → `/lint-mobile` → `/e2e`, tous verts : mobile 40/40, weda2 46 + 2 flaky, porte verte).
**Nature** : revue de code — un défaut neuf, introduit par le correctif B1, sur les deux clients. Aucune PR ouverte. Task laissée en `wip-task-376.md`.

## Ce qui est réglé

| Bloquant du 1ᵉʳ passage | weda2 | mobile |
|---|---|---|
| B1 — brouillon orphelin si Envoyer pendant l'autosave | ✅ | ✅ (`aa037b6`) |
| B2 — seconde pièce homonyme illisible | — | ✅ (`4c6a92f`) |
| B3 — fermeture par geste puis réouverture rapide | — | ✅ (`aa037b6`) |

api-mail : inchangé, ✅ APPROVED au 1ᵉʳ passage.

## Bloquant

### B4 — Après un envoi en échec, la suppression du brouillon orphelin peut effacer le brouillon que le médecin vient d'enregistrer (weda2 ET mobile)
- **Où** :
  - weda2 `libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`, branche « enregistrement dépassé » de `persistDraft` (`discardOrphanDraft(result.draftId)`, ~l. 2537) ; `proposedDraftId` n'y est pas remis à zéro.
  - mobile `src/app/features/mail/components/mail-compose/mail-compose.component.ts:675-681` (branche « abandoned » de `saveDraftOnce`) avec `draftIdToSave` (:586-596) ; `pendingDraftId` n'y est pas remis à zéro.
- **Scénario** :
  1. Le premier enregistrement automatique (`POST /drafts`, identifiant X) est en vol ; le médecin clique Envoyer.
  2. L'envoi échoue vite (5xx, 409) : la rédaction reste ouverte avec son contenu.
  3. Le POST revient : l'enregistrement est jugé dépassé, `DELETE X` part (non attendu).
  4. Le médecin quitte la rédaction (ou l'autosave suivant passe) : l'enregistrement repropose **le même X** → `POST X` en vol en même temps que `DELETE X`.
  5. Si le POST arrive en premier, la rédaction se ferme « enregistrée », puis le DELETE efface le brouillon : **le contenu est perdu**.
- **Correctif attendu** (une ligne par client) : dans la branche « dépassé », remettre à zéro l'identifiant proposé (`proposedDraftId = null` / `pendingDraftId = null`) pour que le prochain enregistrement prenne un nouvel identifiant ; ou ne supprimer l'orphelin qu'une fois l'envoi réussi. Test rouge d'abord : POST en vol, envoi en échec, POST revenu → l'enregistrement suivant propose un identifiant **différent** de celui qui est supprimé.

## Suggestions non bloquantes (relevées par la relecture)
- weda2 : l'autosave ne reprend pas après un envoi en échec (`failSend` ne rappelle pas `startAutoSave`, comportement antérieur à la task) ; le test « l'enregistrement automatique reprend normalement » appelle `saveDraftNow()` à la main et ne prouve pas la reprise du minuteur — le renommer ou le durcir.
- weda2 : un `saveThen` dépassé par un envoi termine sans valeur : une ouverture demandée pendant ce temps est perdue sans message (aucune donnée perdue).
- mobile B3 : quand l'enregistrement de fermeture échoue, l'ouverture en attente est abandonnée ; le commentaire (~l. 1307) dit qu'elle « attend » — à corriger.
- weda2 `compose-body.util.ts` (DOMParser) : un corps qui commencerait par `<style>`/`<meta>` le perdrait au réenregistrement (peu probable vu la construction du corps).

## Décision demandée
Relancer `/develop task-376` sur B4 (et, si possible, la reprise de l'autosave après échec côté weda2), puis `/lint-angular → /lint-mobile → /e2e → /review`.
