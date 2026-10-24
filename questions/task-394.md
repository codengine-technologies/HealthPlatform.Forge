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

---

## Revue de code (2026-10-25) — CHANGES REQUESTED : la règle telle qu'implémentée perd du texte écrit

La reprise a levé le blocage `/e2e` (voies vertes : mobile 45/45, Angular 53/53). Mais la relecture indépendante trouve
deux **pertes de texte du médecin**, au-delà de la règle demandée. Le critère « texte hors signature et hors
citation » repose sur la position du texte dans le HTML, et pas sur ce que le médecin a tapé.

### ❌ Mobile : nouveau message avec signature par défaut, le texte tapé est perdu

- `injectSignature` (`mail-compose.component.ts` ~l. 1574) produit, pour un nouveau message, un corps fait
  **seulement** du bloc `<!-- signature --><br/>{signature}<!-- /signature -->`. Il n'y a aucune zone libre hors des
  marqueurs.
- Le curseur est placé sur la première ligne, dans les marqueurs : le texte tapé y entre (constaté dans Chromium,
  moteur de la WebView Android). Résultat : `<!-- signature -->Bonjour<br>Dr Martin<!-- /signature -->`.
- `hasOwnText` retire le bloc signature : pas de brouillon automatique, et la croix ferme **sans enregistrer**. Le texte
  est perdu sans avertissement. Avant la task, il était sauvé.
- Les tests unitaires ne le voient pas : ils construisent un HTML où le texte est déjà hors des marqueurs. Le banc e2e
  n'a pas de signature par défaut.

### ❌ weda2 : texte écrit sous la citation ou sous la signature, ignoré

- `hasContent()` = `hasOwnText(body)`, qui ne garde que ce qui **précède** la première frontière (signature, en-tête
  « Le … a écrit : », citation).
- **Réponse** : le médecin écrit sous la citation, puis ferme par la croix. Pas de question, pas d'enregistrement
  automatique, texte perdu. Avant la task, une réponse (qui a toujours un destinataire) était enregistrée : c'est une
  **régression**.
- **Nouveau message** : Entrée en fin de signature, puis du texte. Ce texte ne compte pas non plus.
- Les deux clients ne jugent pas le même « texte du médecin » : le mobile compte le texte sous la signature, weda2 non.

### Ce que je te propose (décision à confirmer)

Remplacer « texte hors signature et hors citation » par :

> **Le corps compte dès qu'il diffère de ce que la rédaction a proposé à l'ouverture** : vide, signature, citation
> d'une réponse ou d'un transfert. Tout ajout du médecin compte, où qu'il soit : au-dessus, en dessous, dans la
> citation (réponse point par point), et une image collée aussi.

- C'est le sens littéral de ta demande (« rien saisi dans le corps ») : rien n'a changé dans le corps → ni brouillon ni
  question. Le reste de ta décision ne change pas : objet, destinataires et pièces jointes seuls ne suffisent pas.
- Mise en œuvre : chaque client garde le corps « proposé » à l'ouverture (et après un changement de signature), et
  compare le corps courant normalisé (espaces, `<br>` vides, `&nbsp;`) à ce corps proposé.
- Tests : de vrais tests d'éditeur (frappe dans le `contenteditable` / tiptap, signature par défaut, frappe sous la
  citation), et pas un HTML construit à la main. En e2e, une variante de E2E-DRAFT-004 avec signature par défaut, qui
  écrit puis ferme : le brouillon doit exister.

### Reprise

Si tu valides la règle, relance `/develop task-394`. Sinon, précise ce qui doit compter.
