Résolu — décision humaine du 2026-11-16 : reprise 2 autorisée (`/develop task-486 --reprise`).

# task-486 — revue anticipée, passage 2 : un bloquant revient après la reprise 1

**Étape** : `/review task-486 --code` (passage 2, après `/develop --reprise` n° 1).
**Raison de l'arrêt** : règle 13 — « un bloquant qui revient après une reprise arrête la chaîne ». Rien d'autre ne
bloque ; aucun envoi, aucune PR.

## Le constat qui revient (B2)

Entrée (weda2) ou ✓ (mobile) peut encore poser **un autre tag que celui tapé**, dans un cas que la reprise 1 n'a pas
couvert : le texte saisi est exactement le nom d'un tag **déjà posé** sur le message.

- Le message porte « Urgent ». Le médecin ouvre la saisie et tape « urgent ».
- « Urgent » est exclu de la liste (déjà posé) ; la ligne « Créer le tag » n'apparaît pas (le nom existe) ; la
  première ligne restante, « Très urgent », est désignée d'office.
- Entrée ou ✓ pose « Très urgent », que le médecin n'a pas demandé.

Le reste de la reprise est validé : B1 (refus et accents prouvés par la route), B4 (créations et poses concurrentes),
S1 (flèche haut), B3 (refus affiché, double envoi bloqué) — rien de cassé ailleurs.

## Correctif proposé par la forge (reprise 2, dans le plafond de 2)

Quand le texte saisi désigne exactement un tag déjà posé, ne désigner aucune ligne : Entrée et ✓ referment la saisie
sans rien envoyer (weda2 `tag-suggestions.util.ts` / `mail-tag.component.ts`, mobile `tag-suggestions.util.ts` /
`mail-detail.component.ts`). Test vu rouge dans les deux clients. Deux retouches non bloquantes dans la même passe :
l'erreur effacée à l'ouverture de la saisie (weda2), et le commentaire du test HTTP de concurrence qui renvoie à la
preuve déterministe.

## Décision attendue

1. **Autoriser la reprise 2** : `/develop task-486 --reprise` — la chaîne repart ensuite d'elle-même
   (revue anticipée, Sonar, lint, e2e, validation finale). *Recommandé.*
2. Ou trancher autrement le comportement voulu quand le nom tapé est celui d'un tag déjà posé.

Arbitrages déjà ouverts, à trancher au merge (non bloquants) : A1 (« Avis cardio » tapé quand « Avis cardiologie »
existe : Entrée pose l'existant, comme le plan de test), A2 (pose d'un tag existant par son nom ; contrat à fixer
avec task-456). Détail : `## Code Review Summary` du task file.
