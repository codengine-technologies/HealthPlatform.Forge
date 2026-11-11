> **Résolu** le 2026-11-11 par la 2ᵉ reprise de `/develop task-446` : A1 corrigé (`hasDocumentHead` partagé par le surlignage et le cadre), tests vus rouges (R5, R6).

# task-446 — /review (2ᵉ passage) : CHANGES REQUESTED

**Étape** : `/review` après la reprise de `/develop`, 2026-11-11. La chaîne est arrêtée avant l'ouverture de la PR
api-mail. Le premier blocage (A : style perdu en tête d'un fragment) est corrigé, ainsi que B et C. La revue
indépendante du correctif trouve **un défaut introduit par le correctif lui-même**.

## Bloquant

**A1. `libs/mss/src/core/utils/text-highlight.util.ts`, `highlightHtml` — test de forme désaligné sur celui du cadre.**

- `highlightHtml` rend un document complet dès que l'entrée contient `<html` (`/<(html|head)[\s>]/i`), et
  `documentElement.outerHTML` porte toujours `<head></head>`.
- Or `medical-html-frame` (`wrapWithDesignTokens`) n'enveloppe une entrée **que si** elle ne contient pas
  `/<head[^>]*>/i`. Une entrée `<html><body>…</body></html>` **sans `<head>`** était enveloppée avant task-446 ; une
  fois surlignée, elle ne l'est plus.
- Effet médecin, pendant une recherche, sur un message de cette forme : plus de `<base target="_blank">` (un lien
  cliqué remplace le message dans le cadre), plus de doctype (rendu en mode quirks), plus de `viewport`. Même effet
  quand `<html>` ou `<head>` n'apparaît que dans un commentaire (et le commentaire est perdu).
- Correctif proposé : rendre le document complet **seulement** quand l'entrée satisfait le test exact du cadre,
  `/<head[^>]*>/i` (partagé, une seule définition pour les deux), sinon la forme fragment (`head.innerHTML` +
  `body.outerHTML`/`innerHTML`). Seuls les attributs de `<html>` (`lang`) sont alors perdus.
- Test à ajouter, vu rouge sur le code actuel : `highlightHtml('<html><body><p>Hémoglobine</p></body></html>', …)`
  passé à l'enveloppe du cadre garde `<base target="_blank">` et le doctype de l'enveloppe.

## Confirmé correct (revue indépendante)

- A pour les fragments (style et `meta` de tête gardés, attributs de `<body>` fusionnés par le parseur dans l'enveloppe).
- B : mémo de `plainSegments` sur la référence des mots (`computed()` stable).
- C : accent décomposé gardé dans la plage, fusion des plages intacte.

## État des dépôts

- `api-mail` : `feat/task-446-recherche-lire-un-resultat-extrait`, `783ff7e1` poussé, aucune PR.
- `client-angular` : non commité sur `feature/nova-mss-weda-integration`.
- Task : reste en `wip-*`.

## Décision attendue

Relancer `/develop task-446` (reprise : A1, test vu rouge), puis la chaîne reprend jusqu'à `/review`.
