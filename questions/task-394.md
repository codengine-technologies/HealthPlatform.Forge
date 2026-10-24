# task-394 — /e2e rouge : E2E-COMPOSE-003 (mobile), test non adapté à la nouvelle règle

**Nature du blocage** : régression au sens de la porte (un test rouge après `retries: 1`), causée par la task : un
test e2e existant traverse le comportement que la task retire, et son geste n'a pas été adapté.

## Constat

- Test : `Client/Mobile/e2e/specs/functional.spec.ts:959` (E2E-COMPOSE-003, « un envoi refusé par la messagerie
  garde le brouillon et peut être renvoyé »). Rouge aux deux essais.
- Échec : `compose-draft-saved` jamais visible (« le brouillon est enregistré automatiquement », l. 993, 45 s).
- Cause : le parcours saisit un destinataire et un objet **sans texte dans le corps**, puis attend l'enregistrement
  automatique. Avec la règle de la task (décision humaine 1), aucun brouillon n'est enregistré sans texte du médecin.
  Le comportement attendu par COMPOSE-003 (envoi refusé, brouillon conservé, renvoi) n'est pas en cause.
- Voie Angular : verte (53/53, dont E2E-DRAFT-004 et DETAIL-001 adapté). Parité verte.

## Correctif attendu (reprise `/develop task-394`)

Dans le parcours mobile de E2E-COMPOSE-003, écrire un texte dans le corps (`editor-area`) avant d'attendre
l'enregistrement automatique, comme pour DRAFT-001 et 002. Ce qu'il vérifie ne change pas, donc pas de montée de
version. Puis rejouer la voie mobile.

Vérifié : c'est le seul test mobile restant qui attend un brouillon sans texte. Les autres occurrences de
`compose-draft-saved` sont DRAFT-002 (adapté) et DRAFT-003 (attente d'absence, inchangée).
