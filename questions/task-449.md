# task-449 — /review passage 5 : CHANGES REQUESTED, après la reprise 4

**Étape** : `/review`, 5ᵉ passe (revue indépendante, 2026-11-12), après la reprise 4 demandée par l'humain. Build, tests
(api-mail 7 970, mss-lib 1 650, weda2 2 683), Sonar (QG OK, 0 issue nouveau code) et `/e2e` (mobile 61, angular 84,
parité verte) sont verts. B1, B2 de la passe 4, l'arbitrage S1 et S2, S3, S4 sont livrés et prouvés rouges. La PR n'est
**pas** ouverte. La task reste en `wip-*` (`**Reprises**: 4`).

## Bloquants (passe 5) — corrigeables par la forge, tous deux introduits par la reprise 4

### B1 — Deux expressions entre guillemets voisines fusionnent

- La suppression des guillemets vides (correctif S4) est faite par une expression régulière qui prend aussi le guillemet
  fermant d'une expression, l'espace, et l'ouvrant de la suivante. Vérifié :
  `de : "Paul Martin" "compte rendu"` devient `de : "Paul Martin compte rendu"`. Le critère « De » exige alors
  4 mots dans l'ordre : 0 résultat, et la recherche exacte de « compte rendu » disparaît.
- Correctif : écarter les expressions vides après l'appariement des guillemets, pas avant. Tests à deux expressions
  voisines, vus rouges.

### B2 — Un correspondant choisi dans la liste ramène aussi ses homonymes

- Choisir un destinataire dans les suggestions, un contact dans « De », ou valider une adresse complète par Entrée écrit
  l'adresse dans le critère « À » / « De », qui se lit désormais mot à mot (S1). Choisir
  « paul.martin@cardio.example » ramène aussi « jean-paul.martin@cardio.example ». Vérifié dans le code.
- Correctif recommandé, sans changer le contrat : un critère qui est **entièrement une adresse bien formée** se compare
  exactement (casse ignorée). Tests vus rouges.

## Suggestions (même reprise)

- **S5** — un critère de plus de 10 mots est tronqué sans le dire : le refuser en 400 (« critère trop long »).
- **S6** — dire dans la PR le changement assumé : `%`, `_`, `\` séparent les mots, et `50` trouve « 500 ».

## Arbitrage humain

Aucun nouveau. Les arbitrages S1, S4/S5, S6, S7, S11 sont tranchés et livrés.

## Pourquoi la chaîne s'arrête

Quatre reprises faites (plafond de la règle 13 : 2 ; les 3ᵉ et 4ᵉ demandées par l'humain). Les deux bloquants sont
petits, localisés, et viennent des correctifs de la reprise 4 elle-même. La forge recommande une 5ᵉ reprise (`relance`).

## Reprise

`/develop task-449 --reprise` corrige B1, B2, S5, S6 (chaque correctif vu rouge), puis la chaîne reprend jusqu'à
`/review`.
