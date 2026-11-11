# task-446 — /review : CHANGES REQUESTED

**Étape** : `/review` (revue de code), 2026-11-11. La chaîne est arrêtée avant l'ouverture de la PR api-mail.

**Nature** : défaut de rendu introduit par la task (client-angular, code-only, non commité). Build, tests unitaires,
Sonar et parcours e2e sont verts : aucun test ne couvre ce cas.

## Bloquant

**A. `libs/mss/src/core/utils/text-highlight.util.ts`, `highlightHtml` (retour de fonction) — la mise en forme d'un
message est perdue quand un mot cherché y est trouvé.**

- Pour un corps HTML **sans** balise `<html>`, la fonction rend `doc.body.innerHTML`. `DOMParser` range un `<style>`,
  `<meta>`, `<title>` ou `<head>` placé en tête du fragment dans l'en-tête du document : ils disparaissent du rendu, tout
  comme les attributs de `<body>` (`bgcolor`, `style`).
- Constaté (jsdom) : `<style>p{color:red}</style><p>Hemoglobine</p>` surligné sur `hemoglobine` devient
  `<p><mark …>Hemoglobine</mark></p>`.
- Effet médecin : ouvrir un résultat pendant une recherche affiche le message sans sa mise en forme, dès qu'un mot
  cherché est dans le corps. Hors recherche, le message est intact.
- Le test de `text-highlight.util.spec.ts` ne le voit pas : son `<style>` est placé après le `<p>`.
- Correctif proposé : rendre `documentElement.outerHTML` dès que l'entrée porte `<head`, `<style`, `<meta`, `<title`
  ou `<body` (ou toujours), sans forcer `<!DOCTYPE html>` (il fait passer un message en mode standard). Test à ajouter :
  `<style>` en tête d'un fragment, et attribut de `<body>`, conservés ; vu rouge sur le code actuel.

## Non bloquant (à traiter avec le correctif)

- **B.** `mail-body.component.ts`, `plainSegments` : recalculé à chaque détection de changement pendant une recherche
  (repli caractère par caractère de tout le corps). Mémoïser comme `mailBodyHtml` (`{ text, terms }`).
- **C.** `text-highlight.util.ts`, `foldText` / `findTermRanges` : sur un texte décomposé (NFD), l'accent combinant qui
  suit la dernière lettre d'une correspondance reste hors du `<mark>`. Étendre la fin de plage aux caractères dont le
  repli est vide.

## État des dépôts

- `api-mail` : `feat/task-446-recherche-lire-un-resultat-extrait`, commit `783ff7e1` (scénario E2E-SEARCH-010) poussé,
  **aucune PR ouverte**.
- `client-angular` : code de la task non commité sur `feature/nova-mss-weda-integration` (voir `## Develop log`).
- Task : reste en `wip-*`.

## Décision attendue

Relancer `/develop task-446` (reprise : corriger A, puis B et C, tests vus rouges), puis la chaîne reprend jusqu'à
`/review`. Ou corriger à la main dans WindSurf puis lancer `/review task-446`.
