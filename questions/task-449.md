# task-449 — /review : CHANGES REQUESTED (une suggestion masquée choisie par Entrée)

**Étape** : `/review` (revue indépendante, 2026-11-12). Build et tests verts (api-mail, weda2), Sonar QG OK, `/e2e` vert
(mobile 61, angular 82, parité verte). Règle 1b : chaque comportement d'endpoint a son test d'intégration vu rouge
(17 mutations). La PR n'est **pas** ouverte. La task reste en `wip-*`.

## Bloquant

### B1 — Après Échap, Entrée choisit encore la suggestion désignée (weda2)

- `MailSearchComponent.onKeyDown` lit `suggestions.activeEntry()` sans vérifier que la liste est ouverte, et
  `closeDropdown()` (Échap, clic ailleurs) ne remet pas la désignation à zéro. Les flèches déplacent aussi la
  désignation liste fermée.
- Scénario : taper `bern`, ↓ (Catherine BERNARD désignée), Échap, puis Entrée pour lancer une recherche ordinaire :
  l'application ouvre la vue « Mails du patient » de Catherine BERNARD. La consultation est tracée au journal alors
  que le médecin ne l'a pas choisie.
- Correctif attendu : flèches et Entrée-sur-désignation seulement liste ouverte ; `closeDropdown()` remet la
  désignation à -1. Test de composant vu rouge.

## À corriger dans la même reprise (non bloquant seul, défaut réel)

- **S2** — Pendant la pause de frappe et la requête, la liste montre encore la réponse précédente (`bern` pendant
  qu'on tape `bernx`). ↓ puis Entrée dans cet intervalle choisit une entrée périmée. Ne montrer une réponse que si elle
  correspond au texte affiché.
- **S3** — `distinctUntilChanged` après le debounce : `ab`, retour arrière, `b` retapé en moins de 250 ms → la liste
  reste vide (la réponse a été effacée, la nouvelle demande est supprimée comme doublon).
- **S9** — Recherche exacte : une expression rare faite de mots fréquents (`"résultat normal"`) fait vérifier jusqu'à
  25 000 messages, 100 par 100. Plafonner les candidats vérifiés et rendre la réponse tronquée au plafond.
- **S8** — Suggestions : pas de borne sur la saisie (un mot de plus = un `LIKE` de plus sur chaque ligne). Borner
  (≈ 100 caractères / 5 mots).
- **S10** — `SearchHistoryOwner` retombe sur la clé de la boîte seule quand la personne n'est pas connue : c'est
  l'ancienne clé partagée. Rendre un historique vide plutôt que celui de la boîte.
- **S12** — Une saisie de ponctuation seule (`--`) passe la règle des 2 caractères et rend les 5 dernières
  recherches ; Redis indisponible fait échouer toute la réponse de suggestions au lieu de vider la catégorie.

## Arbitrage humain (hors reprise sauf décision)

- **S11** — Effacer l'historique : le bouton « Effacer » partait avec le composant d'historique du formulaire, remplacé
  par la catégorie « Recherches récentes ». `DELETE /search/history` existe toujours mais rien ne l'appelle. Faut-il
  un « Effacer » dans la catégorie (poste partagé) ?
- **S4 / S5** — Les suggestions lisent nom **et** adresse, accents ignorés ; les critères tapés (`de :`, `à :`,
  `objet :` puis Entrée) restent ceux de task-443 : `à :` sur l'adresse seule, accents comptés (ILIKE). `à : dupont`
  propose « Dupont » mais Entrée sans choisir ne trouve rien si « dupont » n'est que dans le nom. La DoD dit
  « À / Cc contient le texte (RecipientAddress) » : faut-il aligner les critères sur les suggestions ?
- **S6 / S7** — Un préfixe remplace un critère déjà posé dans le formulaire ; `de : martin "compte rendu"` prend
  toute la fin comme expéditeur. À trancher : combiner, refuser, ou couper au guillemet.

## Reprise

`/develop task-449` corrige B1, S2, S3, S8, S9, S10, S12, chaque correctif vu rouge, puis la chaîne reprend jusqu'à
`/review`.
